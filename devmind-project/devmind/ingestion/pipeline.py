"""
Ingestion Pipeline for DevMind.
Orchestrates the flow from files to chunks.
"""

from pathlib import Path
from typing import List, Optional, Union, Callable
from dataclasses import dataclass
import logging
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
            "errors": []
        }
        
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
        Process a single file into sections.
        
        Args:
            file_info: File to process
            
        Returns:
            List of sections
        """
        logger.debug(f"Processing file: {file_info.path}")
        
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
            return sections
            
        except Exception as e:
            logger.error(f"Error processing {file_info.path}: {e}")
            self.stats["errors"].append({
                "file": str(file_info.path),
                "error": str(e),
                "stage": "processing"
            })
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


class IncrementalPipeline(IngestionPipeline):
    """
    Incremental ingestion pipeline.
    
    Only processes changed files based on:
    - File modification time
    - File hash
    - Previous ingestion state
    
    TODO: Implement incremental logic
    """
    
    def __init__(self, config: PipelineConfig, state_file: Path):
        """
        Initialize incremental pipeline.
        
        Args:
            config: Pipeline configuration
            state_file: Path to state file tracking processed files
        """
        super().__init__(config)
        self.state_file = state_file
        self.previous_state = self._load_state()
    
    def _load_state(self) -> dict:
        """
        Load previous ingestion state.
        
        TODO: Read from state_file (JSON)
        """
        raise NotImplementedError()
    
    def _save_state(self, state: dict):
        """
        Save current ingestion state.
        
        TODO: Write to state_file (JSON)
        """
        raise NotImplementedError()
    
    def should_process_file(self, file_info: FileInfo) -> bool:
        """
        Check if file needs processing.
        
        TODO: Compare with previous state
        - Check if file exists in state
        - Compare modification time
        - Compare hash
        
        Returns:
            True if file should be processed
        """
        raise NotImplementedError()
