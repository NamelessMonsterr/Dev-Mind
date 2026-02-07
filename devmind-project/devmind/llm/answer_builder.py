"""
Answer Builder for DevMind.
Assembles context from retrieval results into structured prompts.
"""

from typing import List, Dict, Any
from dataclasses import dataclass
import logging

from devmind.retrieval import RetrievalResult

logger = logging.getLogger(__name__)


@dataclass
class ContextBlock:
    """Single context block for LLM."""
    file_path: str
    start_line: int
    end_line: int
    section_type: str
    language: str
    content: str
    score: float


@dataclass
class AssembledContext:
    """Assembled context ready for LLM."""
    formatted_context: str
    context_blocks: List[ContextBlock]
    total_tokens: int
    sources_count: int


class AnswerBuilder:
    """
    Builds structured context from retrieval results.
    
    Assembles context in a format optimized for LLM consumption.
    """
    
    def __init__(self, max_context_tokens: int = 8000):
        """
        Initialize answer builder.
        
        Args:
            max_context_tokens: Maximum tokens for context
        """
        self.max_context_tokens = max_context_tokens
        logger.info(f"AnswerBuilder initialized (max_tokens={max_context_tokens})")
    
    def assemble_context(
        self,
        results: List[RetrievalResult],
        include_metadata: bool = True
    ) -> AssembledContext:
        """
        Assemble retrieval results into structured context.
        
        Args:
            results: Retrieval results
            include_metadata: Whether to include metadata headers
            
        Returns:
            AssembledContext with formatted text
        """
        logger.info(f"Assembling context from {len(results)} results")
        
        context_blocks = []
        formatted_parts = []
        total_tokens = 0
        
        for i, result in enumerate(results, 1):
            # Create context block
            block = ContextBlock(
                file_path=result.file_path,
                start_line=result.start_line,
                end_line=result.end_line,
                section_type=result.section_type,
                language=result.language,
                content=result.content,
                score=result.score
            )
            
            # Format as structured block
            if include_metadata:
                formatted = self._format_block_with_metadata(block, i)
            else:
                formatted = self._format_block_simple(block)
            
            # Estimate tokens (rough: 1 token ≈ 4 chars)
            block_tokens = len(formatted) // 4
            
            # Check token limit
            if total_tokens + block_tokens > self.max_context_tokens:
                logger.warning(
                    f"Context limit reached at block {i}, "
                    f"total_tokens={total_tokens}"
                )
                break
            
            context_blocks.append(block)
            formatted_parts.append(formatted)
            total_tokens += block_tokens
        
        # Join all formatted blocks
        formatted_context = "\n\n".join(formatted_parts)
        
        logger.info(
            f"Assembled {len(context_blocks)} blocks, "
            f"~{total_tokens} tokens"
        )
        
        return AssembledContext(
            formatted_context=formatted_context,
            context_blocks=context_blocks,
            total_tokens=total_tokens,
            sources_count=len(context_blocks)
        )
    
    def _format_block_with_metadata(self, block: ContextBlock, index: int) -> str:
        """Format context block with metadata."""
        return f"""[Source {index}]
File: {block.file_path}
Lines: {block.start_line}-{block.end_line}
Type: {block.section_type}
Language: {block.language}
Relevance: {block.score:.2f}

```{block.language}
{block.content}
```"""
    
    def _format_block_simple(self, block: ContextBlock) -> str:
        """Format context block without metadata."""
        return f"""# {block.file_path}:{block.start_line}-{block.end_line}

```{block.language}
{block.content}
```"""
    
    def build_citations(
        self,
        context_blocks: List[ContextBlock]
    ) -> List[Dict[str, Any]]:
        """
        Build citation list from context blocks.
        
        Args:
            context_blocks: Context blocks used in answer
            
        Returns:
            List of citation dictionaries
        """
        citations = []
        
        for i, block in enumerate(context_blocks, 1):
            citation = {
                "id": i,
                "file_path": block.file_path,
                "start_line": block.start_line,
                "end_line": block.end_line,
                "section_type": block.section_type,
                "language": block.language,
                "score": block.score
            }
            citations.append(citation)
        
        return citations
    
    def merge_overlapping_blocks(
        self,
        blocks: List[ContextBlock]
    ) -> List[ContextBlock]:
        """
        Merge overlapping blocks from the same file.
        
        Args:
            blocks: List of context blocks
            
        Returns:
            Merged blocks
        """
        if not blocks:
            return []
        
        # Group by file
        by_file: Dict[str, List[ContextBlock]] = {}
        for block in blocks:
            if block.file_path not in by_file:
                by_file[block.file_path] = []
            by_file[block.file_path].append(block)
        
        merged = []
        
        for file_path, file_blocks in by_file.items():
            # Sort by start line
            file_blocks.sort(key=lambda b: b.start_line)
            
            current = file_blocks[0]
            
            for next_block in file_blocks[1:]:
                # Check if overlapping or adjacent
                if next_block.start_line <= current.end_line + 5:
                    # Merge
                    current = ContextBlock(
                        file_path=current.file_path,
                        start_line=current.start_line,
                        end_line=max(current.end_line, next_block.end_line),
                        section_type=current.section_type,
                        language=current.language,
                        content=current.content + "\n\n" + next_block.content,
                        score=max(current.score, next_block.score)
                    )
                else:
                    merged.append(current)
                    current = next_block
            
            merged.append(current)
        
        logger.info(f"Merged {len(blocks)} -> {len(merged)} blocks")
        return merged
