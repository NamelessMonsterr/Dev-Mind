"""
Ingestion Pipeline for DevMind.
Orchestrates the flow from files to chunks.
"""

from pathlib import Path
from typing import List, Optional, Union, Callable
from dataclasses import dataclass
import logging
import asyncio
import time
import hashlib
import json
from enum import Enum

from devmind.ingestion.file_scanner import FileScanner, FileInfo, FileType
from devmind.processing.code_processor import ProcessorFactory, CodeSection
from devmind.processing.doc_processor import DocumentProcessorFactory, DocSection
from devmind.chunking.chunker import ChunkerFactory, Chunk, BaseChunker

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Stages of the ingestion pipeline."""
    SCANNING = "scanning"
    PROCESSING = "processing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"  # Future: not implemented yet
    INDEXING = "indexing"    # Future: not implemented yet


@dataclass
class PipelineConfig:
    """Configuration for ingestion pipeline."""
    source_path: Path
    file_types: List[FileType] = None
    languages: List[str] = None
    chunking_strategy: str = "fixed"
    chunk_size: int = 512
    chunk_overlap: int = 50
    ignored_patterns: List[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10 MB
    
    def __post_init__(self):
        if self.file_types is None:
            self.file_types = [FileType.CODE, FileType.DOCUMENT]
        if self.languages is None:
            self.languages = ["python", "javascript", "typescript"]
        if self.ignored_patterns is None:
            self.ignored_patterns = []


@dataclass
class PipelineResult:
    """Result of pipeline execution."""
    total_files_scanned: int
    total_files_processed: int
    total_sections_extracted: int
    total_chunks_generated: int
    chunks: List[Chunk]
    errors: List[dict]


class IngestionPipeline:
    """
    Main ingestion pipeline.
    
    Orchestrates: Files → Scan → Process → Chunk → (Embed) → (Index)
    
    Responsibilities:
    - Run complete ingestion workflow
    - Coordinate scanner, processors, chunker
    - Handle errors gracefully
    - Emit progress events
    - Collect statistics
    """
    
    def __init__(
        self, 
        config: PipelineConfig,
        progress_callback: Optional[Callable] = None
    ):
        """
        Initialize pipeline.
        
        Args:
            config: Pipeline configuration
            progress_callback: Optional callback for progress updates
        """
        self.config = config
        self.progress_callback = progress_callback
        
        # Initialize components
        self.scanner = FileScanner(ignored_patterns=config.ignored_patterns)
        self.chunker = ChunkerFactory.create(
            config.chunking_strategy,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap
        )
        
        # Statistics
        self.stats = {
            "files_scanned": 0,
            "files_processed": 0,
            "sections_extracted": 0,
            "chunks_generated": 0,
            "errors": [],
            "retries": 0,
            "dlq_files": []  # Dead-letter queue for persistently failing files
        }
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay_base = 1.0  # seconds
        
        logger.info(f"Initialized IngestionPipeline for {config.source_path}")
    
    def run(self) -> PipelineResult:
        """
        Run the complete ingestion pipeline.
        
        Returns:
            PipelineResult with chunks and statistics
        """
        logger.info("Starting ingestion pipeline")
        
        try:
            # Step 1: Scan files
            self.emit_progress(PipelineStage.SCANNING, 0, 1, "Scanning directory...")
            file_infos = self.scan_files()
            self.stats["files_scanned"] = len(file_infos)
            
            # Step 2: Process files
            self.emit_progress(PipelineStage.PROCESSING, 0, len(file_infos), "Processing files...")
            all_sections = []
            
            for i, file_info in enumerate(file_infos):
                sections = self.process_file(file_info)
                all_sections.extend(sections)
                self.stats["files_processed"] += 1
                self.stats["sections_extracted"] += len(sections)
                
                self.emit_progress(
                    PipelineStage.PROCESSING, 
                    i + 1, 
                    len(file_infos),
                    f"Processed {file_info.path.name}"
                )
            
            # Step 3: Chunk sections
            self.emit_progress(
                PipelineStage.CHUNKING, 
                0, 
                len(all_sections),
                "Chunking sections..."
            )
            chunks = self.chunk_sections(all_sections)
            self.stats["chunks_generated"] = len(chunks)
            
            logger.info(
                f"Pipeline complete: {self.stats['files_processed']} files, "
                f"{self.stats['sections_extracted']} sections, "
                f"{self.stats['chunks_generated']} chunks"
            )
            
            return PipelineResult(
                total_files_scanned=self.stats["files_scanned"],
                total_files_processed=self.stats["files_processed"],
                total_sections_extracted=self.stats["sections_extracted"],
                total_chunks_generated=self.stats["chunks_generated"],
                chunks=chunks,
                errors=self.stats["errors"]
            )
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            self.stats["errors"].append({
                "error": str(e),
                "stage": "pipeline"
            })
            raise
    
    def scan_files(self) -> List[FileInfo]:
        """
        Scan for files to process.
        
        Returns:
            List of FileInfo objects
        """
        logger.info(f"Scanning {self.config.source_path}")
        
        # Scan directory
        file_infos = self.scanner.scan(self.config.source_path)
        
        # Filter by file types
        if self.config.file_types:
            file_infos = [
                f for f in file_infos 
                if f.file_type in self.config.file_types
            ]
        
        # Filter by languages
        if self.config.languages:
            file_infos = [
                f for f in file_infos
                if f.language in self.config.languages or f.file_type == FileType.DOCUMENT
            ]
        
        # Filter by file size
        file_infos = [
            f for f in file_infos
            if f.size <= self.config.max_file_size
        ]
        
        logger.info(f"Found {len(file_infos)} files to process")
        return file_infos
    
    def process_file(self, file_info: FileInfo) -> List[Union[CodeSection, DocSection]]:
        """
        Process a single file into sections with retry logic.
        
        Args:
            file_info: File to process
            
        Returns:
            List of sections
        """
        return self._process_file_with_retry(file_info)
    
    def _process_file_with_retry(
        self, 
        file_info: FileInfo,
        attempt: int = 0
    ) -> List[Union[CodeSection, DocSection]]:
        """
        Process file with exponential backoff retry.
        
        Args:
            file_info: File to process
            attempt: Current retry attempt (0-indexed)
            
        Returns:
            List of sections
        """
        logger.debug(f"Processing file: {file_info.path} (attempt {attempt + 1}/{self.max_retries + 1})")
        
        try:
            # Determine processor type
            if file_info.file_type == FileType.CODE:
                processor = ProcessorFactory.get_processor(file_info)
            elif file_info.file_type == FileType.DOCUMENT:
                processor = DocumentProcessorFactory.get_processor(file_info)
            else:
                logger.warning(f"No processor for {file_info.file_type}")
                return []
            
            if processor is None:
                logger.warning(f"No processor found for {file_info.path}")
                return []
            
            # Process file
            sections = processor.process(file_info)
            
            # Log retry success if this was a retry
            if attempt > 0:
                logger.info(f"✓ Successfully processed {file_info.path} after {attempt} retries")
            
            return sections
            
        except Exception as e:
            # Check if we should retry
            if attempt < self.max_retries:
                # Calculate exponential backoff delay
                delay = self.retry_delay_base * (2 ** attempt)
                logger.warning(
                    f"Error processing {file_info.path} (attempt {attempt + 1}/{self.max_retries + 1}): {e}. "
                    f"Retrying in {delay}s..."
                )
                
                # Sleep before retry
                time.sleep(delay)
                self.stats["retries"] += 1
                
                # Retry
                return self._process_file_with_retry(file_info, attempt + 1)
            else:
                # All retries exhausted - add to dead-letter queue
                logger.error(
                    f"✗ Failed to process {file_info.path} after {self.max_retries + 1} attempts. "
                    f"Adding to dead-letter queue."
                )
                
                dlq_entry = {
                    "file": str(file_info.path),
                    "error": str(e),
                    "attempts": self.max_retries + 1,
                    "stage": "processing",
                    "file_type": file_info.file_type.value,
                    "language": file_info.language
                }
                
                self.stats["errors"].append(dlq_entry)
                self.stats["dlq_files"].append(dlq_entry)
                
                return []
    
    def chunk_sections(
        self, 
        sections: List[Union[CodeSection, DocSection]]
    ) -> List[Chunk]:
        """
        Chunk sections into embeddings-ready pieces.
        
        Args:
            sections: Sections to chunk
            
        Returns:
            List of chunks
        """
        logger.info(f"Chunking {len(sections)} sections")
        
        try:
            chunks = self.chunker.chunk(sections)
            logger.info(f"Generated {len(chunks)} chunks")
            return chunks
        except Exception as e:
            logger.error(f"Error during chunking: {e}")
            self.stats["errors"].append({
                "error": str(e),
                "stage": "chunking"
            })
            return []
    
    def process_directory(self, path: Path) -> List[Chunk]:
        """
        Process an entire directory.
        
        Args:
            path: Directory path
            
        Returns:
            List of chunks from all files
        """
        logger.info(f"Processing directory: {path}")
        
        # Update config and run
        self.config.source_path = path
        result = self.run()
        return result.chunks
    
    def emit_progress(
        self, 
        stage: PipelineStage, 
        current: int, 
        total: int,
        message: str = ""
    ):
        """
        Emit progress update.
        
        Args:
            stage: Current pipeline stage
            current: Current item number
            total: Total items
            message: Optional message
        """
        if self.progress_callback:
            self.progress_callback({
                "stage": stage.value,
                "current": current,
                "total": total,
                "message": message,
                "stats": self.stats
            })
    
    def get_stats(self) -> dict:
        """Get pipeline statistics."""
        return self.stats.copy()
    
    def get_dead_letter_queue(self) -> List[dict]:
        """
        Get list of files that failed after all retries.
        
        Returns:
            List of DLQ entries with file info and error details
        """
        return self.stats["dlq_files"].copy()
    
    def get_error_summary(self) -> dict:
        """
        Get summary of errors and retries.
        
        Returns:
            Dictionary with error statistics
        """
        return {
            "total_errors": len(self.stats["errors"]),
            "total_retries": self.stats["retries"],
            "dlq_files_count": len(self.stats["dlq_files"]),
            "dlq_files": self.get_dead_letter_queue()
        }


class IncrementalPipeline(IngestionPipeline):
    """
    Incremental ingestion pipeline.
    
    Only processes changed files based on:
    - File modification time
    - File hash (SHA-256)
    - Previous ingestion state
    
    This significantly speeds up re-ingestion by skipping unchanged files.
    """
    
    def __init__(
        self, 
        config: PipelineConfig, 
        state_file: Path,
        progress_callback: Optional[Callable] = None
    ):
        """
        Initialize incremental pipeline.
        
        Args:
            config: Pipeline configuration
            state_file: Path to state file tracking processed files
            progress_callback: Optional callback for progress updates
        """
        super().__init__(config, progress_callback)
        self.state_file = Path(state_file)
        self.previous_state = self._load_state()
        
        logger.info(f"Initialized IncrementalPipeline with state file: {state_file}")
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """
        Compute SHA-256 hash of file contents.
        
        Args:
            file_path: Path to file
            
        Returns:
            Hex digest of file hash
        """
        sha256 = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                # Read in chunks to handle large files
                while chunk := f.read(8192):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.warning(f"Could not hash {file_path}: {e}")
            return ""
    
    def _load_state(self) -> dict:
        """
        Load previous ingestion state from JSON file.
        
        Returns:
            Dictionary mapping file paths to metadata
        """
        if not self.state_file.exists():
            logger.info("No previous state file found, will process all files")
            return {}
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            logger.info(f"Loaded state for {len(state)} previously processed files")
            return state
        except Exception as e:
            logger.error(f"Failed to load state file: {e}")
            return {}
    
    def _save_state(self, state: dict):
        """
        Save current ingestion state to JSON file.
        
        Args:
            state: Dictionary mapping file paths to metadata
        """
        try:
            # Ensure parent directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            logger.info(f"Saved state for {len(state)} files to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state file: {e}")
    
    def should_process_file(self, file_info: FileInfo) -> bool:
        """
        Check if file needs processing based on hash comparison.
        
        Args:
            file_info: File information
            
        Returns:
            True if file should be processed (new or modified)
        """
        file_path_str = str(file_info.path)
        
        # File not in previous state - must process
        if file_path_str not in self.previous_state:
            logger.debug(f"New file: {file_info.path}")
            return True
        
        # Compute current hash
        current_hash = self._compute_file_hash(file_info.path)
        previous_hash = self.previous_state[file_path_str].get("hash", "")
        
        # Hash mismatch - file was modified
        if current_hash != previous_hash:
            logger.debug(f"Modified file: {file_info.path}")
            return True
        
        # File unchanged
        logger.debug(f"Skipping unchanged file: {file_info.path}")
        return False
    
    def run(self) -> PipelineResult:
        """
        Run incremental ingestion, processing only changed files.
        
        Returns:
            PipelineResult with chunks and statistics
        """
        logger.info("Starting incremental ingestion pipeline")
        
        try:
            # Step 1: Scan files
            self.emit_progress(PipelineStage.SCANNING, 0, 1, "Scanning directory...")
            all_file_infos = self.scan_files()
            self.stats["files_scanned"] = len(all_file_infos)
            
            # Step 2: Filter to only changed files
            file_infos = [f for f in all_file_infos if self.should_process_file(f)]
            
            skipped_count = len(all_file_infos) - len(file_infos)
            logger.info(
                f"Processing {len(file_infos)} changed files "
                f"(skipped {skipped_count} unchanged)"
            )
            
            if len(file_infos) == 0:
                logger.info("No files to process, all files are up to date")
                return PipelineResult(
                    total_files_scanned=self.stats["files_scanned"],
                    total_files_processed=0,
                    total_sections_extracted=0,
                    total_chunks_generated=0,
                    chunks=[],
                    errors=[]
                )
            
            # Step 3: Process changed files
            self.emit_progress(PipelineStage.PROCESSING, 0, len(file_infos), "Processing files...")
            all_sections = []
            new_state = self.previous_state.copy()
            
            for i, file_info in enumerate(file_infos):
                sections = self.process_file(file_info)
                all_sections.extend(sections)
                self.stats["files_processed"] += 1
                self.stats["sections_extracted"] += len(sections)
                
                # Update state for this file
                file_hash = self._compute_file_hash(file_info.path)
                new_state[str(file_info.path)] = {
                    "hash": file_hash,
                    "last_processed": datetime.now().isoformat(),
                    "size": file_info.size,
                    "file_type": file_info.file_type.value,
                    "language": file_info.language
                }
                
                self.emit_progress(
                    PipelineStage.PROCESSING, 
                    i + 1, 
                    len(file_infos),
                    f"Processed {file_info.path.name}"
                )
            
            # Step 4: Chunk sections
            self.emit_progress(
                PipelineStage.CHUNKING, 
                0, 
                len(all_sections),
                "Chunking sections..."
            )
            chunks = self.chunk_sections(all_sections)
            self.stats["chunks_generated"] = len(chunks)
            
            # Step 5: Save updated state
            self._save_state(new_state)
            
            logger.info(
                f"Incremental pipeline complete: {self.stats['files_processed']}/{self.stats['files_scanned']} files, "
                f"{self.stats['sections_extracted']} sections, "
                f"{self.stats['chunks_generated']} chunks"
            )
            
            return PipelineResult(
                total_files_scanned=self.stats["files_scanned"],
                total_files_processed=self.stats["files_processed"],
                total_sections_extracted=self.stats["sections_extracted"],
                total_chunks_generated=self.stats["chunks_generated"],
                chunks=chunks,
                errors=self.stats["errors"]
            )
            
        except Exception as e:
            logger.error(f"Incremental pipeline failed: {e}")
            self.stats["errors"].append({
                "error": str(e),
                "stage": "pipeline"
            })
            raise
