"""
Metadata Filtering for DevMind Retrieval Engine.
Filters search results based on metadata criteria.
"""

from typing import List, Optional, Callable, Set
from pathlib import Path
from dataclasses import dataclass
import logging

from devmind.retrieval.reranker import RerankedResult

logger = logging.getLogger(__name__)


@dataclass
class FilterCriteria:
    """Criteria for filtering results."""
    file_types: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    path_prefix: Optional[str] = None
    path_excludes: Optional[List[str]] = None
    min_score: float = 0.0
    max_results: Optional[int] = None
    line_range: Optional[tuple] = None  # (min_line, max_line)
    section_types: Optional[List[str]] = None
    
    def __repr__(self) -> str:
        active_filters = []
        if self.file_types:
            active_filters.append(f"types={len(self.file_types)}")
        if self.languages:
            active_filters.append(f"langs={len(self.languages)}")
        if self.min_score > 0:
            active_filters.append(f"min_score={self.min_score}")
        return f"FilterCriteria({', '.join(active_filters)})"


class ResultFilter:
    """
    Filters search results based on metadata.
    
    Supports filtering by:
    - File type
    - Programming language
    - Path patterns
    - Score threshold
    - Line number range
    - Section type
    """
    
    def __init__(self):
        """Initialize result filter."""
        logger.info("ResultFilter initialized")
    
    def filter(
        self,
        results: List[RerankedResult],
        criteria: FilterCriteria
    ) -> List[RerankedResult]:
        """
        Filter results based on criteria.
        
        Args:
            results: Results to filter
            criteria: Filter criteria
            
        Returns:
            Filtered results
        """
        logger.info(f"Filtering {len(results)} results with {criteria}")
        
        filtered = results
        
        # Filter by score
        if criteria.min_score > 0:
            filtered = self._filter_by_score(filtered, criteria.min_score)
        
        # Filter by file type
        if criteria.file_types:
            filtered = self._filter_by_file_type(filtered, criteria.file_types)
        
        # Filter by language
        if criteria.languages:
            filtered = self._filter_by_language(filtered, criteria.languages)
        
        # Filter by path
        if criteria.path_prefix:
            filtered = self._filter_by_path_prefix(filtered, criteria.path_prefix)
        
        if criteria.path_excludes:
            filtered = self._filter_by_path_exclude(filtered, criteria.path_excludes)
        
        # Filter by line range
        if criteria.line_range:
            filtered = self._filter_by_line_range(filtered, criteria.line_range)
        
        # Filter by section type
        if criteria.section_types:
            filtered = self._filter_by_section_type(filtered, criteria.section_types)
        
        # Limit results
        if criteria.max_results and len(filtered) > criteria.max_results:
            filtered = filtered[:criteria.max_results]
        
        logger.info(f"Filtered to {len(filtered)} results")
        return filtered
    
    def _filter_by_score(
        self,
        results: List[RerankedResult],
        min_score: float
    ) -> List[RerankedResult]:
        """Filter by minimum score."""
        return [r for r in results if r.score >= min_score]
    
    def _filter_by_file_type(
        self,
        results: List[RerankedResult],
        file_types: List[str]
    ) -> List[RerankedResult]:
        """Filter by file type (extension)."""
        filtered = []
        
        for result in results:
            file_path = result.metadata.get("source_file", "")
            if file_path:
                ext = Path(file_path).suffix.lower()
                if ext in file_types or ext.lstrip('.') in file_types:
                    filtered.append(result)
        
        return filtered
    
    def _filter_by_language(
        self,
        results: List[RerankedResult],
        languages: List[str]
    ) -> List[RerankedResult]:
        """Filter by programming language."""
        return [
            r for r in results
            if r.metadata.get("language", "").lower() in [l.lower() for l in languages]
        ]
    
    def _filter_by_path_prefix(
        self,
        results: List[RerankedResult],
        path_prefix: str
    ) -> List[RerankedResult]:
        """Filter by path prefix."""
        filtered = []
        
        for result in results:
            file_path = str(result.metadata.get("source_file", ""))
            if file_path.startswith(path_prefix):
                filtered.append(result)
        
        return filtered
    
    def _filter_by_path_exclude(
        self,
        results: List[RerankedResult],
        path_excludes: List[str]
    ) -> List[RerankedResult]:
        """Exclude results matching path patterns."""
        filtered = []
        
        for result in results:
            file_path = str(result.metadata.get("source_file", ""))
            
            # Check if path matches any exclude pattern
            excluded = False
            for exclude_pattern in path_excludes:
                if exclude_pattern in file_path:
                    excluded = True
                    break
            
            if not excluded:
                filtered.append(result)
        
        return filtered
    
    def _filter_by_line_range(
        self,
        results: List[RerankedResult],
        line_range: tuple
    ) -> List[RerankedResult]:
        """Filter by line number range."""
        min_line, max_line = line_range
        
        filtered = []
        for result in results:
            start_line = result.metadata.get("start_line", 0)
            end_line = result.metadata.get("end_line", 0)
            
            # Check if range overlaps
            if start_line <= max_line and end_line >= min_line:
                filtered.append(result)
        
        return filtered
    
    def _filter_by_section_type(
        self,
        results: List[RerankedResult],
        section_types: List[str]
    ) -> List[RerankedResult]:
        """Filter by section type (function, class, paragraph, etc.)."""
        return [
            r for r in results
            if r.metadata.get("section_type", "") in section_types
        ]
    
    def create_custom_filter(
        self,
        filter_fn: Callable[[RerankedResult], bool]
    ) -> Callable[[List[RerankedResult]], List[RerankedResult]]:
        """
        Create a custom filter function.
        
        Args:
            filter_fn: Function that takes RerankedResult and returns bool
            
        Returns:
            Filter function
        """
        def custom_filter(results: List[RerankedResult]) -> List[RerankedResult]:
            return [r for r in results if filter_fn(r)]
        
        return custom_filter
    
    def deduplicate(
        self,
        results: List[RerankedResult],
        by_content: bool = False
    ) -> List[RerankedResult]:
        """
        Remove duplicate results.
        
        Args:
            results: Results to deduplicate
            by_content: If True, deduplicate by content; else by chunk_id
            
        Returns:
            Deduplicated results
        """
        if by_content:
            seen = set()
            deduped = []
            
            for result in results:
                content_hash = hash(result.content)
                if content_hash not in seen:
                    seen.add(content_hash)
                    deduped.append(result)
            
            logger.info(f"Deduplicated {len(results)} -> {len(deduped)} by content")
            return deduped
        else:
            seen = set()
            deduped = []
            
            for result in results:
                if result.chunk_id not in seen:
                    seen.add(result.chunk_id)
                    deduped.append(result)
            
            logger.info(f"Deduplicated {len(results)} -> {len(deduped)} by chunk_id")
            return deduped


def create_language_filter(languages: List[str]) -> FilterCriteria:
    """Helper to create language filter."""
    return FilterCriteria(languages=languages)


def create_path_filter(path_prefix: str) -> FilterCriteria:
    """Helper to create path filter."""
    return FilterCriteria(path_prefix=path_prefix)


def create_score_filter(min_score: float) -> FilterCriteria:
    """Helper to create score filter."""
    return FilterCriteria(min_score=min_score)
