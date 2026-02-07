"""
Document Processors for DevMind Ingestion System.
Parse documents (MD, PDF, HTML) into sections.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
import logging

from devmind.ingestion.file_scanner import FileInfo

logger = logging.getLogger(__name__)


@dataclass
class DocSection:
    """A logical section of a document."""
    content: str
    metadata: dict
    heading: Optional[str] = None
    heading_level: Optional[int] = None
    section_number: int = 0
    section_type: str = "document"  # paragraph, heading, list, table
    
    def __repr__(self) -> str:
        return f"DocSection(heading={self.heading}, level={self.heading_level})"


class DocumentProcessor(ABC):
    """Abstract base class for document processors."""
    
    def __init__(self, file_extension: str):
        """
        Initialize processor.
        
        Args:
            file_extension: File extension this processor handles
        """
        self.file_extension = file_extension
    
    def can_process(self, file_info: FileInfo) -> bool:
        """Check if file extension matches."""
        return file_info.path.suffix.lower() == self.file_extension
    
    @abstractmethod
    def process(self, file_info: FileInfo) -> List[DocSection]:
        """
        Process document file into sections.
        
        Args:
            file_info: File to process
            
        Returns:
            List of document sections
        """
        pass
    
    @abstractmethod
    def extract_sections(self, content: str) -> List[DocSection]:
        """
        Extract sections from document content.
        
        Args:
            content: Document content
            
        Returns:
            List of sections
        """
        pass
    
    def read_file(self, path: Path) -> str:
        """Read file content as text."""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()


class MarkdownProcessor(DocumentProcessor):
    """
    Processes Markdown documents.
    
    Extracts:
    - Headings (h1-h6)
    - Paragraphs
    - Code blocks
    - Lists
    - Tables
    """
    
    def __init__(self):
        super().__init__(file_extension=".md")
    
    def can_process(self, file_info: FileInfo) -> bool:
        """Also accept .markdown extension."""
        suffix = file_info.path.suffix.lower()
        return suffix in {".md", ".markdown"}
    
    def process(self, file_info: FileInfo) -> List[DocSection]:
        """
        Process Markdown file.
        
        Returns:
            List of DocSection objects
        """
        logger.info(f"Processing Markdown file: {file_info.path}")
        
        try:
            content = self.read_file(file_info.path)
            sections = self.extract_sections(content)
            
            # Add file path to metadata
            for section in sections:
                section.metadata["file_path"] = str(file_info.path)
            
            logger.info(f"Extracted {len(sections)} sections from {file_info.path}")
            return sections
            
        except Exception as e:
            logger.error(f"Error processing {file_info.path}: {e}")
            return []
    
    def extract_sections(self, content: str) -> List[DocSection]:
        """
        Extract sections from Markdown.
        """
        import re
        
        sections = []
        lines = content.split('\n')
        
        current_heading = None
        current_level = 0
        current_content = []
        section_number = 0
        
        for i, line in enumerate(lines):
            # Check for heading
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            
            if heading_match:
                # Save previous section if exists
                if current_content:
                    section = DocSection(
                        content='\n'.join(current_content).strip(),
                        metadata={
                            "start_line": section_number * 10,  # Approximate
                        },
                        heading=current_heading,
                        heading_level=current_level,
                        section_number=section_number,
                        section_type="paragraph"
                    )
                    sections.append(section)
                    current_content = []
                    section_number += 1
                
                # Start new section with heading
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()
                
                current_heading = heading_text
                current_level = level
                current_content = [line]
                
            else:
                current_content.append(line)
        
        # Save last section
        if current_content:
            section = DocSection(
                content='\n'.join(current_content).strip(),
                metadata={},
                heading=current_heading,
                heading_level=current_level,
                section_number=section_number,
                section_type="paragraph"
            )
            sections.append(section)
        
        return sections
    
    def extract_heading_hierarchy(self, content: str) -> dict:
        """
        Extract heading structure.
        """
        import re
        
        hierarchy = {
            "headings": [],
            "levels": []
        }
        
        for line in content.split('\n'):
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if heading_match:
                level = len(heading_match.group(1))
                text = heading_match.group(2).strip()
                hierarchy["headings"].append(text)
                hierarchy["levels"].append(level)
        
        return hierarchy


class TextProcessor(DocumentProcessor):
    """
    Processes plain text files.
    
    Simpler processing:
    - Split by paragraphs (empty lines)
    - No special formatting
    """
    
    def __init__(self):
        super().__init__(file_extension=".txt")
    
    def process(self, file_info: FileInfo) -> List[DocSection]:
        """
        Process text file.
        
        TODO: Split by paragraphs
        """
        raise NotImplementedError("TextProcessor.process() not yet implemented")
    
    def extract_sections(self, content: str) -> List[DocSection]:
        """
        Extract sections from plain text.
        
        TODO: Split on double newlines
        """
        raise NotImplementedError()


class PDFProcessor(DocumentProcessor):
    """
    Processes PDF documents.
    
    Extracts:
    - Text content
    - Page boundaries
    - Basic structure
    
    TODO: Requires pdfplumber or PyPDF2
    """
    
    def __init__(self):
        super().__init__(file_extension=".pdf")
    
    def process(self, file_info: FileInfo) -> List[DocSection]:
        """
        Process PDF file.
        
        TODO: Use pdfplumber to extract text
        TODO: Preserve page numbers in metadata
        """
        raise NotImplementedError("PDFProcessor.process() not yet implemented")
    
    def extract_sections(self, content: str) -> List[DocSection]:
        """Extract sections from PDF text."""
        raise NotImplementedError()


class HTMLProcessor(DocumentProcessor):
    """
    Processes HTML documents.
    
    Extracts:
    - Headings (h1-h6)
    - Paragraphs (p)
    - Lists (ul, ol)
    - Code blocks (pre, code)
    
    TODO: Use BeautifulSoup for parsing
    """
    
    def __init__(self):
        super().__init__(file_extension=".html")
    
    def can_process(self, file_info: FileInfo) -> bool:
        """Also accept .htm extension."""
        suffix = file_info.path.suffix.lower()
        return suffix in {".html", ".htm"}
    
    def process(self, file_info: FileInfo) -> List[DocSection]:
        """
        Process HTML file.
        
        TODO: Parse with BeautifulSoup
        TODO: Extract semantic structure
        """
        raise NotImplementedError("HTMLProcessor.process() not yet implemented")
    
    def extract_sections(self, content: str) -> List[DocSection]:
        """Extract sections from HTML."""
        raise NotImplementedError()


class DocumentProcessorFactory:
    """Factory for document processors."""
    
    _processors: List[DocumentProcessor] = []
    
    @classmethod
    def register(cls, processor: DocumentProcessor):
        """Register a document processor."""
        cls._processors.append(processor)
        logger.info(f"Registered document processor: {processor.file_extension}")
    
    @classmethod
    def get_processor(cls, file_info: FileInfo) -> Optional[DocumentProcessor]:
        """
        Get appropriate processor for a file.
        
        Args:
            file_info: File information
            
        Returns:
            Processor instance or None
        """
        for processor in cls._processors:
            if processor.can_process(file_info):
                return processor
        return None
    
    @classmethod
    def initialize_defaults(cls):
        """Initialize default document processors."""
        cls.register(MarkdownProcessor())
        cls.register(TextProcessor())
        cls.register(PDFProcessor())
        cls.register(HTMLProcessor())
        logger.info("Initialized default document processors")


# Initialize default processors
DocumentProcessorFactory.initialize_defaults()
