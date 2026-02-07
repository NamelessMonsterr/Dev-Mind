"""
Summarizer for DevMind.
Code and documentation summarization.
"""

from typing import Optional
import logging

from devmind.llm.provider import LLMProviderManager
from devmind.llm.prompts import build_summary_prompt

logger = logging.getLogger(__name__)


class Summarizer:
    """
    Code and documentation summarization.
    """
    
    def __init__(self, llm_manager: LLMProviderManager):
        """
        Initialize summarizer.
        
        Args:
            llm_manager: LLM provider manager
        """
        self.llm_manager = llm_manager
        logger.info("Summarizer initialized")
    
    async def summarize_code(
        self,
        code: str,
        language: str = "python",
        max_length: int = 200
    ) -> str:
        """
        Summarize code snippet.
        
        Args:
            code: Code to summarize
            language: Programming language
            max_length: Max summary length
            
        Returns:
            Summary text
        """
        logger.info(f"Summarizing {language} code ({len(code)} chars)")
        
        prompt = build_summary_prompt(f"```{language}\n{code}\n```")
        
        try:
            summary = await self.llm_manager.generate(
                prompt,
                context_size=len(code) // 4,
                query_complexity="simple",
                temperature=0.5,
                max_tokens=max_length
            )
            
            return summary.strip()
            
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            return "Error generating summary"
    
    async def summarize_file(
        self,
        file_content: str,
        file_path: str
    ) -> str:
        """
        Summarize entire file.
        
        Args:
            file_content: File content
            file_path: File path
            
        Returns:
            File summary
        """
        logger.info(f"Summarizing file: {file_path}")
        
        prompt = f"""Summarize this file in 3-4 sentences:

File: {file_path}

{file_content}

Summary:"""
        
        try:
            summary = await self.llm_manager.generate(
                prompt,
                context_size=len(file_content) // 4,
                query_complexity="simple",
                temperature=0.5,
                max_tokens=300
            )
            
            return summary.strip()
            
        except Exception as e:
            logger.error(f"File summarization error: {e}")
            return "Error generating file summary"


class CitationExtractor:
    """Extract and format citations from LLM responses."""
    
    def __init__(self):
        """Initialize citation extractor."""
        logger.info("CitationExtractor initialized")
    
    def extract_file_references(self, text: str) -> list:
        """
        Extract file references from text.
        
        Args:
            text: Text to extract from
            
        Returns:
            List of file references
        """
        import re
        
        # Pattern: file paths with optional line numbers
        pattern = r'([/\w.-]+\.[\w]+)(?::(\d+)(?:-(\d+))?)?'
        
        matches = re.findall(pattern, text)
        
        references = []
        for match in matches:
            file_path = match[0]
            start_line = int(match[1]) if match[1] else None
            end_line = int(match[2]) if match[2] else start_line
            
            references.append({
                "file": file_path,
                "start_line": start_line,
                "end_line": end_line
            })
        
        return references
    
    def format_citation(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        description: str = None
    ) -> str:
        """Format a single citation."""
        if start_line and end_line:
            citation = f"[{file_path}:{start_line}-{end_line}]"
        else:
            citation = f"[{file_path}]"
        
        if description:
            citation += f" - {description}"
        
        return citation
