"""
File Scanner for DevMind Ingestion System.
Recursively scans directories and detects file types and languages.
"""

from pathlib import Path
from typing import List, Optional, Set
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib
import logging

logger = logging.getLogger(__name__)


class FileType(Enum):
    """Types of files that can be processed."""
    CODE = "code"
    DOCUMENT = "document"
    BINARY = "binary"
    SKIP =  "skip"


@dataclass
class FileInfo:
    """Information about a discovered file."""
    path: Path
    size: int
    hash: str
    file_type: FileType
    language: Optional[str]
    last_modified: datetime
    
    def __repr__(self) -> str:
        return (
            f"FileInfo(path={self.path.name}, "
            f"type={self.file_type.value}, "
            f"language={self.language})"
        )


class FileScanner:
    """
    Scans directories recursively and generates FileInfo objects.
    
    Responsibilities:
    - Walk directory tree
    - Filter ignored paths
    - Detect file types (code, document, binary)
    - Detect programming languages
    - Calculate file hashes
    """
    
    # Directories to ignore
    DEFAULT_IGNORED_DIRS = {
        ".git", ".svn", ".hg",
        "node_modules", "venv", "env", ".venv",
        "__pycache__", ".pytest_cache",
        "build", "dist", "target",
        ".idea", ".vscode",
    }
    
    # Code file extensions mapped to languages
    CODE_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".go": "go",
        ".java": "java",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".hpp": "cpp",
        ".h": "cpp",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".cs": "csharp",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
    }
    
    # Document file extensions
    DOC_EXTENSIONS = {
        ".md", ".markdown",
        ".txt",
        ".rst",
        ".html", ".htm",
        ".pdf",
        ".docx",
        ".org",
    }
    
    def __init__(
        self, 
        ignored_dirs: Optional[Set[str]] = None,
        ignored_patterns: Optional[List[str]] = None
    ):
        """
        Initialize File Scanner.
        
        Args:
            ignored_dirs: Set of directory names to skip
            ignored_patterns: List of glob patterns to skip
        """
        self.ignored_dirs = ignored_dirs or self.DEFAULT_IGNORED_DIRS
        self.ignored_patterns = ignored_patterns or []
        logger.info(f"FileScanner initialized with {len(self.ignored_dirs)} ignored dirs")
    
    def scan(self, directory: Path, recursive: bool = True) -> List[FileInfo]:
        """
        Scan directory and return list of FileInfo objects.
        
        Args:
            directory: Directory to scan
            recursive: Whether to scan subdirectories
            
        Returns:
            List of FileInfo objects
        """
        logger.info(f"Scanning directory: {directory}")
        
        directory = Path(directory)
        if not directory.exists():
            raise ValueError(f"Directory does not exist: {directory}")
        if not directory.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")
        
        file_infos = []
        
        # Walk directory tree
        if recursive:
            paths = directory.rglob("*")
        else:
            paths = directory.glob("*")
        
        for path in paths:
            # Skip directories
            if path.is_dir():
                continue
            
            # Skip ignored paths
            if self.should_skip(path):
                logger.debug(f"Skipping {path}")
                continue
            
            # Detect file type
            file_type = self.detect_file_type(path)
            
            if file_type == FileType.SKIP:
                logger.debug(f"Skipping file type: {path}")
                continue
            
            # Detect language for code files
            language = None
            if file_type == FileType.CODE:
                language = self.detect_language(path)
            
            # Get file info
            try:
                stats = path.stat()
                file_hash = self.calculate_hash(path)
                
                file_info = FileInfo(
                    path=path,
                    size=stats.st_size,
                    hash=file_hash,
                    file_type=file_type,
                    language=language,
                    last_modified=datetime.fromtimestamp(stats.st_mtime)
                )
                
                file_infos.append(file_info)
                logger.debug(f"Added: {file_info}")
                
            except Exception as e:
                logger.warning(f"Error processing {path}: {e}")
                continue
        
        logger.info(f"Scanned {len(file_infos)} files from {directory}")
        return file_infos
    
    def should_skip(self, path: Path) -> bool:
        """
        Check if a path should be skipped.
        
        Args:
            path: Path to check
            
        Returns:
            True if should skip, False otherwise
        """
        # Check if any parent directory is in ignored_dirs
        for parent in path.parents:
            if parent.name in self.ignored_dirs:
                return True
        
        # Check if path itself is ignored
        if path.name in self.ignored_dirs:
            return True
        
        # Check ignored patterns (simple glob matching)
        for pattern in self.ignored_patterns:
            if path.match(pattern):
                return True
        
        # Skip hidden files (starting with .)
        if path.name.startswith('.') and path.name not in {'.gitignore', '.env'}:
            return True
        
        return False
    
    def detect_file_type(self, path: Path) -> FileType:
        """
        Detect the type of a file.
        
        Args:
            path: File path
            
        Returns:
            FileType enum value
        """
        extension = path.suffix.lower()
        
        # Check code extensions
        if extension in self.CODE_EXTENSIONS:
            return FileType.CODE
        
        # Check document extensions
        if extension in self.DOC_EXTENSIONS:
            return FileType.DOCUMENT
        
        # Check for known binary extensions
        binary_extensions = {
            '.bin', '.exe', '.dll', '.so', '.dylib',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico',
            '.mp3', '.mp4', '.avi', '.mov', '.wav',
            '.zip', '.tar', '.gz', '.rar', '.7z',
            '.pyc', '.pyo', '.o', '.a',
        }
        
        if extension in binary_extensions:
            return FileType.BINARY
        
        # For unknown extensions, try to detect binary by reading first bytes
        if not extension:
            return FileType.SKIP
        
        try:
            # Try to read as text
            with open(path, 'r', encoding='utf-8') as f:
                f.read(512)  # Read first 512 bytes
            # If successful, might be a text file - default to SKIP unless whitelisted
            return FileType.SKIP
        except (UnicodeDecodeError, PermissionError):
            return FileType.BINARY
    
    def detect_language(self, path: Path) -> Optional[str]:
        """
        Detect programming language from file.
        
        Args:
            path: File path
            
        Returns:
            Language name or None
        """
        extension = path.suffix.lower()
        
        # Check extension mapping
        language = self.CODE_EXTENSIONS.get(extension)
        if language:
            return language
        
        # Check shebang for scripts without extension
        if not extension or extension in {'.sh', ''}:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line.startswith('#!'):
                        # Parse shebang
                        if 'python' in first_line:
                            return 'python'
                        elif 'node' in first_line or 'javascript' in first_line:
                            return 'javascript'
                        elif 'bash' in first_line or 'sh' in first_line:
                            return 'shell'
            except Exception:
                pass
        
        return None
    
    def calculate_hash(self, path: Path) -> str:
        """
        Calculate SHA-256 hash of file content.
        
        Args:
            path: File path
            
        Returns:
            Hex digest of file hash
        """
        try:
            sha256_hash = hashlib.sha256()
            
            # Read in chunks for large files
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.warning(f"Failed to hash {path}: {e}")
            return ""
    
    def get_stats(self, file_infos: List[FileInfo]) -> dict:
        """
        Get statistics about scanned files.
        
        Args:
            file_infos: List of FileInfo objects
            
        Returns:
            Dictionary with stats (counts by type, language, etc.)
            
        TODO: Implement stats aggregation
        """
        stats = {
            "total": len(file_infos),
            "by_type": {},
            "by_language": {},
            "total_size": 0,
        }
        
        for info in file_infos:
            # Count by type
            type_name = info.file_type.value
            stats["by_type"][type_name] = stats["by_type"].get(type_name, 0) + 1
            
            # Count by language
            if info.language:
                stats["by_language"][info.language] = (
                    stats["by_language"].get(info.language, 0) + 1
                )
            
            stats["total_size"] += info.size
        
        return stats
