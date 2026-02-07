"""
Vector Search Layer for DevMind Retrieval Engine.
Uses FAISS indices via IndexManager for semantic search.
"""

from pathlib import Path
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
import numpy as np
import logging

from devmind.vectorstore import IndexManager
from devmind.embeddings import Encoder

logger = logging.getLogger(__name__)


@dataclass
class VectorSearchResult:
    """Result from vector search."""
    score: float
    chunk_id: str
    content: str
    metadata: dict
    index_name: str
    
    def __repr__(self) -> str:
        return f"VectorSearchResult(score={self.score:.4f}, index={self.index_name})"


class VectorSearchEngine:
    """
    Semantic search using FAISS vector indices.
    
    Responsibilities:
    - Query embedding generation
    - Single-index search
    - Multi-index search with weighting
    - Result normalization
    """
    
    def __init__(
        self,
        index_manager: IndexManager,
        encoder: Encoder
    ):
        """
        Initialize Vector Search Engine.
        
        Args:
            index_manager: IndexManager instance with loaded indices
            encoder: Encoder for query embedding
        """
        self.index_manager = index_manager
        self.encoder = encoder
        
        logger.info("VectorSearchEngine initialized")
    
    def search(
        self,
        query: str,
        index_name: str,
        top_k: int = 10,
        filter_fn: Optional[callable] = None
    ) -> List[VectorSearchResult]:
        """
        Search a single index.
        
        Args:
            query: Query text
            index_name: Index to search ('code', 'docs', 'notes')
            top_k: Number of results to return
            filter_fn: Optional metadata filter function
            
        Returns:
            List of VectorSearchResult objects
        """
        logger.info(f"Searching {index_name} index for: '{query[:50]}...'")
        
        # Encode query
        query_embedding = self.encoder.encode(query, normalize=True)
        
        # Search index
        results = self.index_manager.search(
            index_name,
            query_embedding,
            k=top_k,
            filter_fn=filter_fn
        )
        
        # Convert to VectorSearchResult objects
        search_results = []
        for score, metadata in results:
            # Generate or retrieve chunk_id
            chunk_id = metadata.get("chunk_id", f"{index_name}_{len(search_results)}")
            
            result = VectorSearchResult(
                score=float(score),
                chunk_id=chunk_id,
                content=metadata.get("content", ""),
                metadata=metadata,
                index_name=index_name
            )
            search_results.append(result)
        
        logger.info(f"Found {len(search_results)} results from {index_name}")
        return search_results
    
    def search_multi(
        self,
        query: str,
        top_k: int = 10,
        index_weights: Optional[Dict[str, float]] = None,
        filter_fn: Optional[callable] = None
    ) -> List[VectorSearchResult]:
        """
        Search across multiple indices with weighted scoring.
        
        Args:
            query: Query text
            top_k: Total number of results to return
            index_weights: Weight for each index (default: code=1.0, docs=0.8, notes=0.5)
            filter_fn: Optional metadata filter function
            
        Returns:
            List of VectorSearchResult objects, sorted by weighted score
        """
        if index_weights is None:
            index_weights = {
                "code": 1.0,
                "docs": 0.8,
                "notes": 0.5
            }
        
        logger.info(f"Multi-index search for: '{query[:50]}...'")
        logger.info(f"Index weights: {index_weights}")
        
        # Encode query once
        query_embedding = self.encoder.encode(query, normalize=True)
        
        # Search all indices
        all_results = self.index_manager.search_all(
            query_embedding,
            k=top_k * 2,  # Get more results for better reranking
            weights=index_weights
        )
        
        # Convert to VectorSearchResult objects
        search_results = []
        for score, metadata, index_name in all_results:
            chunk_id = metadata.get("chunk_id", f"{index_name}_{len(search_results)}")
            
            result = VectorSearchResult(
                score=float(score),
                chunk_id=chunk_id,
                content=metadata.get("content", ""),
                metadata=metadata,
                index_name=index_name
            )
            search_results.append(result)
        
        # Sort by score and limit to top_k
        search_results.sort(key=lambda r: r.score, reverse=True)
        search_results = search_results[:top_k]
        
        logger.info(f"Multi-index search returned {len(search_results)} results")
        return search_results
    
    def search_with_context(
        self,
        query: str,
        context_weight: float = 0.3,
        top_k: int = 10
    ) -> List[VectorSearchResult]:
        """
        Search with query expansion using context.
        
        Args:
            query: Query text
            context_weight: Weight for context vs. query
            top_k: Number of results
            
        Returns:
            List of VectorSearchResult objects
            
        Note: MVP implementation just uses query; future versions will add context
        """
        # MVP: Just use regular search
        # Future: Expand query with context, use multiple embeddings
        return self.search_multi(query, top_k=top_k)
    
    def batch_search(
        self,
        queries: List[str],
        index_name: str,
        top_k: int = 10
    ) -> List[List[VectorSearchResult]]:
        """
        Search multiple queries in batch.
        
        Args:
            queries: List of query texts
            index_name: Index to search
            top_k: Results per query
            
        Returns:
            List of result lists (one per query)
        """
        logger.info(f"Batch searching {len(queries)} queries")
        
        # Encode all queries
        query_embeddings = self.encoder.encode_batch(queries, normalize=True)
        
        # Search for each
        all_results = []
        for i, query_embedding in enumerate(query_embeddings):
            results = self.index_manager.search(
                index_name,
                query_embedding,
                k=top_k
            )
            
            search_results = [
                VectorSearchResult(
                    score=float(score),
                    chunk_id=metadata.get("chunk_id", f"{index_name}_{j}"),
                    content=metadata.get("content", ""),
                    metadata=metadata,
                    index_name=index_name
                )
                for j, (score, metadata) in enumerate(results)
            ]
            
            all_results.append(search_results)
        
        return all_results
    
    def get_stats(self) -> dict:
        """Get search engine statistics."""
        index_stats = self.index_manager.get_stats()
        
        return {
            "encoder_model": self.encoder.get_model_info(),
            "indices": index_stats,
            "total_vectors": sum(index_stats.values())
        }
