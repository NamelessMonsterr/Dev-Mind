"""
Chunking Strategies for DevMind Ingestion System.
Splits sections into embeddings-ready chunks.
"""

from abc import ABC, abstractmethod
from typing import List, Union
from dataclasses import dataclass, field
from pathlib import Path
import uuid
import logging

from devmind.processing.code_processor import CodeSection
from devmind.processing.doc_processor import DocSection

logger = logging.getLogger(__name__)


@dataclass
class ChunkMetadata:
    """Metadata for a chunk."""
    source_file: Path
    chunk_index: int
    total_chunks: int
    section_type: str  # function, class, paragraph, etc.
    language: str = ""
    start_line: int = 0
    end_line: int = 0
    extra: dict = field(default_factory=dict)


@dataclass
class Chunk:
    """A chunk of text ready for embedding."""
    chunk_id: str
    content: str
    metadata: ChunkMetadata
    
    def __repr__(self) -> str:
        return f"Chunk(id={self.chunk_id[:8]}..., size={len(self.content)})"
    
    def __len__(self) -> int:
        return len(self.content)


class BaseChunker(ABC):
    """Abstract base class for chunking strategies."""
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Target size of chunks (in characters)
            chunk_overlap: Overlap between chunks (in characters)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        logger.info(
            f"Initialized {self.__class__.__name__} "
            f"(size={chunk_size}, overlap={chunk_overlap})"
        )
    
    @abstractmethod
    def chunk(self, sections: List[Union[CodeSection, DocSection]]) -> List[Chunk]:
        """
        Chunk sections into embeddings-ready pieces.
        
        Args:
            sections: List of sections to chunk
            
        Returns:
            List of Chunk objects
        """
        pass
    
    def create_chunk(
        self, 
        content: str, 
        source_file: Path,
        chunk_index: int,
        total_chunks: int,
        section_type: str,
        **kwargs
    ) -> Chunk:
        """
        Create a Chunk object.
        
        Args:
            content: Chunk content
            source_file: Source file path
            chunk_index: Index of this chunk
            total_chunks: Total number of chunks
            section_type: Type of section
            **kwargs: Additional metadata
            
        Returns:
            Chunk object
        """
        metadata = ChunkMetadata(
            source_file=source_file,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            section_type=section_type,
            **kwargs
        )
        
        return Chunk(
            chunk_id=str(uuid.uuid4()),
            content=content,
            metadata=metadata
        )


class FixedSizeChunker(BaseChunker):
    """
    Simple fixed-size chunking strategy.
    
    Splits text into chunks of approximately chunk_size characters.
    """
    
    def chunk(self, sections: List[Union[CodeSection, DocSection]]) -> List[Chunk]:
        """
        Chunk sections using fixed-size strategy.
        
        Returns:
            List of Chunk objects
        """
        logger.info(f"Chunking {len(sections)} sections with FixedSizeChunker")
        
        all_chunks = []
        
        for section in sections:
            content = section.content
            
            # Skip empty sections
            if not content or not content.strip():
                continue
            
            # Split into words for token approximation
            words = content.split()
            
            # If section fits in one chunk, create single chunk
            if len(words) <= self.chunk_size:
                chunk = self._create_chunk_from_section(
                    section, 
                    content, 
                    chunk_index=0,
                    total_chunks=1
                )
                all_chunks.append(chunk)
                continue
            
            # Otherwise, split into multiple chunks with overlap
            section_chunks = []
            start_idx = 0
            chunk_index = 0
            
            while start_idx < len(words):
                # Get chunk words
                end_idx = min(start_idx + self.chunk_size, len(words))
                chunk_words = words[start_idx:end_idx]
                chunk_content = ' '.join(chunk_words)
                
                section_chunks.append((chunk_content, chunk_index))
                chunk_index += 1
                
                # Move start with overlap
                start_idx += (self.chunk_size - self.chunk_overlap)
                
                # Break if we've covered all words
                if end_idx >= len(words):
                    break
            
            # Create Chunk objects
            total_chunks = len(section_chunks)
            for chunk_content, idx in section_chunks:
                chunk = self._create_chunk_from_section(
                    section,
                    chunk_content,
                    chunk_index=idx,
                    total_chunks=total_chunks
                )
                all_chunks.append(chunk)
        
        logger.info(f"Generated {len(all_chunks)} chunks")
        return all_chunks
    
    def _create_chunk_from_section(
        self,
        section: Union[CodeSection, DocSection],
        content: str,
        chunk_index: int,
        total_chunks: int
    ) -> Chunk:
        """Create a Chunk from a section."""
        from devmind.processing.code_processor import CodeSection
        
        # Extract common metadata
        if isinstance(section, CodeSection):
            metadata = ChunkMetadata(
                source_file=Path(section.metadata.get("file_path", "")),
                chunk_index=chunk_index,
                total_chunks=total_chunks,
                section_type=section.section_type,
                language=section.language,
                start_line=section.start_line,
                end_line=section.end_line,
                extra={
                    "function_name": section.function_name,
                    "class_name": section.class_name,
                    "docstring": section.metadata.get("docstring", ""),
                }
            )
        else:  # DocSection
            metadata = ChunkMetadata(
                source_file=Path(section.metadata.get("file_path", "")),
                chunk_index=chunk_index,
                total_chunks=total_chunks,
                section_type=section.section_type,
                extra={
                    "heading": section.heading,
                    "heading_level": section.heading_level,
                    "section_number": section.section_number,
                }
            )
        
        return self.create_chunk(
            content=content,
            source_file=metadata.source_file,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            section_type=metadata.section_type,
            language=metadata.language,
            start_line=metadata.start_line,
            end_line=metadata.end_line,
            extra=metadata.extra
        )


class OverlappingChunker(BaseChunker):
    """
    Sliding window chunking with overlap.
    
    Creates overlapping chunks to preserve context across boundaries.
    """
    
    def chunk(self, sections: List[Union[CodeSection, DocSection]]) -> List[Chunk]:
        """
        Chunk sections with overlapping windows.
        
        TODO: Implement overlapping chunking:
        1. Use sliding window approach
        2. Ensure overlap preserves sentence/line boundaries
        3. Add special markers for continued chunks
        
        Returns:
            List of Chunk objects
        """
        raise NotImplementedError("OverlappingChunker.chunk() not yet implemented")


class CodeAwareChunker(BaseChunker):
    """
    Code-aware chunking strategy.
    
    Respects code boundaries:
    - Functions as atomic units (don't split)
    - Classes kept together
    - Include imports/dependencies in context
    """
    
    def chunk(self, sections: List[Union[CodeSection, DocSection]]) -> List[Chunk]:
        """
        Chunk sections with code awareness.
        
        TODO: Implement code-aware chunking:
        1. For CodeSections:
           - Keep functions/methods intact
           - Include class context
           - Add import statements to chunk metadata
        2. For DocSections:
           - Fall back to fixed-size or semantic chunking
        
        Returns:
            List of Chunk objects
        """
        logger.info(f"Chunking {len(sections)} sections with CodeAwareChunker")
        
        # TODO: Implement code-aware logic
        # chunks = []
        # for section in sections:
        #     if isinstance(section, CodeSection):
        #         if len(section.content) < chunk_size:
        #             # Function/class fits in one chunk
        #             chunks.append(create_chunk(section.content, ...))
        #         else:
        #             # Large function - need to split intelligently
        #             # Strategy: split at method boundaries or logical blocks
        #             pass
        
        raise NotImplementedError("CodeAwareChunker.chunk() not yet implemented")
    
    def extract_imports(self, section: CodeSection) -> List[str]:
        """
        Extract import statements relevant to a section.
        
        TODO: Parse imports from source file
        """
        raise NotImplementedError()
    
    def should_split_function(self, section: CodeSection) -> bool:
        """
        Determine if a large function should be split.
        
        TODO: Check size against threshold
        """
        return len(section.content) > self.chunk_size * 2


class ChunkerFactory:
    """Factory for creating chunkers."""
    
    @staticmethod
    def create(strategy: str, **kwargs) -> BaseChunker:
        """
        Create a chunker based on strategy name.
        
        Args:
            strategy: Chunking strategy ('fixed', 'overlap', 'code_aware')
            **kwargs: Arguments for chunker initialization
            
        Returns:
            Chunker instance
        """
        if strategy == "fixed":
            return FixedSizeChunker(**kwargs)
        elif strategy == "overlap":
            return OverlappingChunker(**kwargs)
        elif strategy == "code_aware":
            return CodeAwareChunker(**kwargs)
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy}")
