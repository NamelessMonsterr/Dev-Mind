"""
Retrieval Pipeline for DevMind.
Main entry point for semantic + keyword search.
"""

from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass, asdict
import logging

from devmind.embeddings import Encoder
from devmind.vectorstore import IndexManager
from devmind.retrieval.vector_search import VectorSearchEngine, VectorSearchResult
from devmind.retrieval.keyword_search import KeywordSearchEngine, KeywordSearchResult
from devmind.retrieval.reranker import RuleBasedReranker, RerankedResult
from devmind.retrieval.filters import ResultFilter, FilterCriteria

logger = logging.getLogger(__name__)


@dataclass
class RetrievalConfig:
    """Configuration for retrieval pipeline."""
    # Search settings
    top_k: int = 10
    use_keyword_search: bool = True
    use_multi_index: bool = True
    
    # Index weights (for multi-index search)
    index_weights: Optional[Dict[str, float]] = None
    
    # Reranking
    vector_weight: float = 0.7
    keyword_weight: float = 0.3
    
    # Filtering
    min_score: float = 0.0
    max_results: Optional[int] = None
    
    def __post_init__(self):
        if self.index_weights is None:
            self.index_weights = {
                "code": 1.0,
                "docs": 0.8,
                "notes": 0.5
            }


@dataclass
class RetrievalResult:
    """Final retrieval result returned to user."""
    score: float
    content: str
    file_path: str
    start_line: int
    end_line: int
    section_type: str
    language: str
    chunk_id: str
    index_name: str
    matched_terms: Optional[List[str]] = None
    vector_score: float = 0.0
    keyword_score: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    def __repr__(self) -> str:
        return (
            f"RetrievalResult(score={self.score:.4f}, "
            f"file={Path(self.file_path).name}, "
            f"type={self.section_type})"
        )


class RetrievalPipeline:
    """
    Main retrieval pipeline for DevMind.
    
    Orchestrates:
    1. Query embedding
    2. Vector search (single or multi-index)
    3. Optional keyword search
    4. Result merging and reranking
    5. Metadata filtering
    6. Result formatting
    """
    
    def __init__(
        self,
        index_manager: IndexManager,
        encoder: Encoder,
        config: Optional[RetrievalConfig] = None
    ):
        """
        Initialize retrieval pipeline.
        
        Args:
            index_manager: IndexManager with loaded indices
            encoder: Encoder for query embedding
            config: Retrieval configuration
        """
        self.index_manager = index_manager
        self.encoder = encoder
        self.config = config or RetrievalConfig()
        
        # Initialize search engines
        self.vector_search = VectorSearchEngine(index_manager, encoder)
        self.keyword_search = KeywordSearchEngine()
        
        # Initialize reranker and filter
        self.reranker = RuleBasedReranker(
            vector_weight=self.config.vector_weight,
            keyword_weight=self.config.keyword_weight
        )
        self.filter = ResultFilter()
        
        # Track if keyword index is built
        self._keyword_index_built = False
        
        logger.info("RetrievalPipeline initialized")
    
    def build_keyword_index(self, chunks: List[tuple]) -> None:
        """
        Build keyword search index from chunks.
        
        Args:
            chunks: List of (chunk_id, content, metadata) tuples
        """
        logger.info("Building keyword search index...")
        self.keyword_search.index_chunks(chunks)
        self._keyword_index_built = True
        logger.info("Keyword index built successfully")
    
    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_criteria: Optional[FilterCriteria] = None,
        use_keyword: Optional[bool] = None,
        index_name: Optional[str] = None
    ) -> List[RetrievalResult]:
        """
        Search for query.
        
        Args:
            query: Query text
            top_k: Number of results (overrides config)
            filter_criteria: Optional filter criteria
            use_keyword: Whether to use keyword search (overrides config)
            index_name: Specific index to search (None for multi-index)
            
        Returns:
            List of RetrievalResult objects
        """
        logger.info(f"Searching for: '{query[:100]}...'")
        
        # Use config defaults if not specified
        top_k = top_k or self.config.top_k
        use_keyword = use_keyword if use_keyword is not None else self.config.use_keyword_search
        
        # Step 1: Vector search
        if index_name:
            # Single index search
            logger.info(f"Searching single index: {index_name}")
            vector_results = self.vector_search.search(
                query,
                index_name=index_name,
                top_k=top_k * 2  # Get more for reranking
            )
        else:
            # Multi-index search
            logger.info("Searching multiple indices")
            vector_results = self.vector_search.search_multi(
                query,
                top_k=top_k * 2,
                index_weights=self.config.index_weights
            )
        
        # Step 2: Optional keyword search
        keyword_results = []
        if use_keyword and self._keyword_index_built:
            logger.info("Performing keyword search")
            keyword_results = self.keyword_search.search(
                query,
                top_k=top_k * 2
            )
        
        # Step 3: Rerank
        if keyword_results:
            logger.info("Reranking with vector + keyword scores")
            reranked = self.reranker.rerank(vector_results, keyword_results)
        else:
            logger.info("Reranking with vector scores only")
            reranked = self.reranker.rerank_vector_only(vector_results)
        
        # Step 4: Apply filters
        if filter_criteria:
            logger.info(f"Applying filters: {filter_criteria}")
            reranked = self.filter.filter(reranked, filter_criteria)
        
        # Apply default min_score and max_results from config
        if self.config.min_score > 0:
            reranked = [r for r in reranked if r.score >= self.config.min_score]
        
        # Step 5: Deduplicate
        reranked = self.filter.deduplicate(reranked, by_content=False)
        
        # Step 6: Limit to top_k
        reranked = reranked[:top_k]
        
        # Step 7: Convert to RetrievalResult
        final_results = self._convert_to_retrieval_results(reranked)
        
        logger.info(f"Returning {len(final_results)} results")
        return final_results
    
    def search_by_file(
        self,
        query: str,
        file_path: str,
        top_k: int = 5
    ) -> List[RetrievalResult]:
        """
        Search within a specific file.
        
        Args:
            query: Query text
            file_path: File to search in
            top_k: Number of results
            
        Returns:
            List of RetrievalResult objects from that file
        """
        logger.info(f"Searching in file: {file_path}")
        
        filter_criteria = FilterCriteria(
            path_prefix=file_path,
            max_results=top_k
        )
        
        return self.search(
            query,
            top_k=top_k * 3,  # Get more, then filter
            filter_criteria=filter_criteria
        )
    
    def search_by_language(
        self,
        query: str,
        language: str,
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """
        Search within a specific programming language.
        
        Args:
            query: Query text
            language: Programming language (e.g., 'python')
            top_k: Number of results
            
        Returns:
            List of RetrievalResult objects in that language
        """
        logger.info(f"Searching in language: {language}")
        
        filter_criteria = FilterCriteria(
            languages=[language],
            max_results=top_k
        )
        
        return self.search(
            query,
            top_k=top_k * 2,
            filter_criteria=filter_criteria
        )
    
    def search_functions(
        self,
        query: str,
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """
        Search for functions only.
        
        Args:
            query: Query text
            top_k: Number of results
            
        Returns:
            List of RetrievalResult objects with section_type='function'
        """
        filter_criteria = FilterCriteria(
            section_types=["function", "method"],
            max_results=top_k
        )
        
        return self.search(
            query,
            top_k=top_k * 2,
            filter_criteria=filter_criteria
        )
    
    def search_classes(
        self,
        query: str,
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """
        Search for classes only.
        
        Args:
            query: Query text
            top_k: Number of results
            
        Returns:
            List of RetrievalResult objects with section_type='class'
        """
        filter_criteria = FilterCriteria(
            section_types=["class"],
            max_results=top_k
        )
        
        return self.search(
            query,
            top_k=top_k * 2,
            filter_criteria=filter_criteria
        )
    
    def _convert_to_retrieval_results(
        self,
        reranked: List[RerankedResult]
    ) -> List[RetrievalResult]:
        """Convert RerankedResult to RetrievalResult."""
        results = []
        
        for r in reranked:
            result = RetrievalResult(
                score=r.score,
                content=r.content,
                file_path=str(r.metadata.get("source_file", "")),
                start_line=r.metadata.get("start_line", 0),
                end_line=r.metadata.get("end_line", 0),
                section_type=r.metadata.get("section_type", ""),
                language=r.metadata.get("language", ""),
                chunk_id=r.chunk_id,
                index_name=r.index_name,
                matched_terms=r.matched_terms,
                vector_score=r.vector_score,
                keyword_score=r.keyword_score
            )
            results.append(result)
        
        return results
    
    def get_stats(self) -> dict:
        """Get pipeline statistics."""
        return {
            "config": asdict(self.config),
            "vector_search": self.vector_search.get_stats(),
            "keyword_search": self.keyword_search.get_stats() if self._keyword_index_built else None,
            "keyword_index_built": self._keyword_index_built
        }
