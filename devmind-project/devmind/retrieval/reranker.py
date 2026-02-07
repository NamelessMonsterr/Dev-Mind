"""
Reranker Module for DevMind Retrieval Engine.
Implements rule-based result reranking (MVP).
"""

from typing import List, Union, Dict
from dataclasses import dataclass
import logging

from devmind.retrieval.vector_search import VectorSearchResult
from devmind.retrieval.keyword_search import KeywordSearchResult

logger = logging.getLogger(__name__)


@dataclass
class RerankedResult:
    """Unified result after reranking."""
    score: float
    chunk_id: str
    content: str
    metadata: dict
    vector_score: float
    keyword_score: float
    index_name: str = ""
    matched_terms: List[str] = None
    
    def __repr__(self) -> str:
        return f"RerankedResult(score={self.score:.4f}, chunk_id={self.chunk_id[:16]}...)"


class RuleBasedReranker:
    """
    Rule-based reranker (MVP).
    
    Combines vector and keyword scores with configurable weights.
    Future versions will use cross-encoder models.
    """
    
    def __init__(
        self,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ):
        """
        Initialize reranker.
        
        Args:
            vector_weight: Weight for vector search scores
            keyword_weight: Weight for keyword search scores
        """
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        
        # Validate weights
        total = vector_weight + keyword_weight
        if abs(total - 1.0) > 0.01:
            logger.warning(f"Weights sum to {total}, normalizing...")
            self.vector_weight = vector_weight / total
            self.keyword_weight = keyword_weight / total
        
        logger.info(
            f"RuleBasedReranker initialized "
            f"(vector={self.vector_weight:.2f}, keyword={self.keyword_weight:.2f})"
        )
    
    def rerank(
        self,
        vector_results: List[VectorSearchResult],
        keyword_results: List[KeywordSearchResult]
    ) -> List[RerankedResult]:
        """
        Rerank combined results.
        
        Args:
            vector_results: Results from vector search
            keyword_results: Results from keyword search
            
        Returns:
            List of RerankedResult objects, sorted by combined score
        """
        logger.info(
            f"Reranking {len(vector_results)} vector + "
            f"{len(keyword_results)} keyword results"
        )
        
        # Create chunk_id -> result mapping
        vector_map = {r.chunk_id: r for r in vector_results}
        keyword_map = {r.chunk_id: r for r in keyword_results}
        
        # Get all unique chunk IDs
        all_chunk_ids = set(vector_map.keys()) | set(keyword_map.keys())
        
        # Combine scores
        reranked = []
        
        for chunk_id in all_chunk_ids:
            vector_result = vector_map.get(chunk_id)
            keyword_result = keyword_map.get(chunk_id)
            
            # Get individual scores (default to 0 if missing)
            vector_score = vector_result.score if vector_result else 0.0
            keyword_score = keyword_result.score if keyword_result else 0.0
            
            # Calculate combined score
            combined_score = (
                self.vector_weight * vector_score +
                self.keyword_weight * keyword_score
            )
            
            # Use vector result as primary source if available
            primary_result = vector_result or keyword_result
            
            reranked_result = RerankedResult(
                score=combined_score,
                chunk_id=chunk_id,
                content=primary_result.content,
                metadata=primary_result.metadata,
                vector_score=vector_score,
                keyword_score=keyword_score,
                index_name=getattr(primary_result, 'index_name', ''),
                matched_terms=getattr(keyword_result, 'matched_terms', None) if keyword_result else None
            )
            
            reranked.append(reranked_result)
        
        # Sort by combined score
        reranked.sort(key=lambda r: r.score, reverse=True)
        
        logger.info(f"Reranked to {len(reranked)} unique results")
        return reranked
    
    def rerank_vector_only(
        self,
        vector_results: List[VectorSearchResult]
    ) -> List[RerankedResult]:
        """
        Rerank vector-only results (no keyword search).
        
        Args:
            vector_results: Results from vector search
            
        Returns:
            List of RerankedResult objects
        """
        logger.info(f"Reranking {len(vector_results)} vector-only results")
        
        reranked = [
            RerankedResult(
                score=r.score,
                chunk_id=r.chunk_id,
                content=r.content,
                metadata=r.metadata,
                vector_score=r.score,
                keyword_score=0.0,
                index_name=r.index_name,
                matched_terms=None
            )
            for r in vector_results
        ]
        
        return reranked
    
    def boost_by_recency(
        self,
        results: List[RerankedResult],
        recency_weight: float = 0.1
    ) -> List[RerankedResult]:
        """
        Boost scores based on file modification time.
        
        Args:
            results: Reranked results
            recency_weight: Weight for recency boost
            
        Returns:
            Results with recency-boosted scores
        """
        # MVP: Skip recency for now
        # Future: Extract last_modified from metadata and boost recent files
        logger.debug("Recency boosting not implemented in MVP")
        return results
    
    def boost_by_type(
        self,
        results: List[RerankedResult],
        type_boosts: Dict[str, float]
    ) -> List[RerankedResult]:
        """
        Boost scores based on section type.
        
        Args:
            results: Reranked results
            type_boosts: Boost multipliers by type (e.g., {"function": 1.2})
            
        Returns:
            Results with type-boosted scores
        """
        logger.debug(f"Applying type boosts: {type_boosts}")
        
        for result in results:
            section_type = result.metadata.get("section_type", "")
            if section_type in type_boosts:
                boost = type_boosts[section_type]
                result.score *= boost
                logger.debug(f"Boosted {section_type} by {boost}x")
        
        # Re-sort after boosting
        results.sort(key=lambda r: r.score, reverse=True)
        
        return results


class CrossEncoderReranker:
    """
    Cross-encoder based reranker (Placeholder for future).
    
    Will use sentence-transformers cross-encoder models
    for more accurate reranking.
    """
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """Initialize cross-encoder reranker."""
        self.model_name = model_name
        logger.info(f"CrossEncoderReranker placeholder initialized")
        raise NotImplementedError(
            "CrossEncoderReranker not implemented in MVP. "
            "Use RuleBasedReranker instead."
        )
