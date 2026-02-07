"""
DevMind Retrieval Engine.

Provides semantic + keyword search with reranking and filtering.
"""

from devmind.retrieval.vector_search import VectorSearchEngine, VectorSearchResult
from devmind.retrieval.keyword_search import KeywordSearchEngine, KeywordSearchResult, BM25Index
from devmind.retrieval.reranker import RuleBasedReranker, RerankedResult
from devmind.retrieval.filters import ResultFilter, FilterCriteria
from devmind.retrieval.retrieval_pipeline import (
    RetrievalPipeline,
    RetrievalConfig,
    RetrievalResult
)

__all__ = [
    # Main pipeline
    "RetrievalPipeline",
    "RetrievalConfig",
    "RetrievalResult",
    
    # Vector search
    "VectorSearchEngine",
    "VectorSearchResult",
    
    # Keyword search
    "KeywordSearchEngine",
    "KeywordSearchResult",
    "BM25Index",
    
    # Reranking
    "RuleBasedReranker",
    "RerankedResult",
    
    # Filtering
    "ResultFilter",
    "FilterCriteria",
]
