"""
Keyword Search Layer for DevMind Retrieval Engine.
Implements BM25-like scoring using inverted index.
"""

from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter
import math
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class KeywordSearchResult:
    """Result from keyword search."""
    score: float
    chunk_id: str
    content: str
    metadata: dict
    matched_terms: List[str]
    
    def __repr__(self) -> str:
        return f"KeywordSearchResult(score={self.score:.4f}, terms={len(self.matched_terms)})"


class BM25Index:
    """
    BM25-based keyword search index.
    
    Implements simplified BM25 scoring for keyword matching.
    """
    
    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75
    ):
        """
        Initialize BM25 index.
        
        Args:
            k1: Term frequency saturation parameter
            b: Length normalization parameter
        """
        self.k1 = k1
        self.b = b
        
        # Index structures
        self.documents: Dict[str, str] = {}  # chunk_id -> content
        self.metadata: Dict[str, dict] = {}  # chunk_id -> metadata
        self.inverted_index: Dict[str, Set[str]] = defaultdict(set)  # term -> chunk_ids
        self.doc_lengths: Dict[str, int] = {}  # chunk_id -> word count
        self.term_frequencies: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))  # chunk_id -> term -> count
        
        self.avg_doc_length: float = 0.0
        self.num_docs: int = 0
        
        logger.info(f"BM25Index initialized (k1={k1}, b={b})")
    
    def add_documents(
        self,
        chunks: List[Tuple[str, str, dict]]
    ) -> None:
        """
        Add documents to index.
        
        Args:
            chunks: List of (chunk_id, content, metadata) tuples
        """
        logger.info(f"Indexing {len(chunks)} documents")
        
        total_length = 0
        
        for chunk_id, content, metadata in chunks:
            # Store document
            self.documents[chunk_id] = content
            self.metadata[chunk_id] = metadata
            
            # Tokenize
            tokens = self._tokenize(content)
            self.doc_lengths[chunk_id] = len(tokens)
            total_length += len(tokens)
            
            # Build inverted index
            for token in tokens:
                self.inverted_index[token].add(chunk_id)
                self.term_frequencies[chunk_id][token] += 1
            
            self.num_docs += 1
        
        # Calculate average document length
        if self.num_docs > 0:
            self.avg_doc_length = total_length / self.num_docs
        
        logger.info(
            f"Indexed {self.num_docs} documents, "
            f"avg_length={self.avg_doc_length:.1f}, "
            f"vocab_size={len(self.inverted_index)}"
        )
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into terms.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tokens
        """
        # Lowercase and split on non-alphanumeric
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        
        # Simple stopword removal
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'this',
            'that', 'these', 'those', 'it', 'its', 'will', 'would', 'should'
        }
        
        tokens = [t for t in tokens if t not in stopwords and len(t) > 1]
        
        return tokens
    
    def search(
        self,
        query: str,
        top_k: int = 10
    ) -> List[KeywordSearchResult]:
        """
        Search using BM25 scoring.
        
        Args:
            query: Query text
            top_k: Number of results to return
            
        Returns:
            List of KeywordSearchResult objects
        """
        logger.info(f"Keyword search for: '{query[:50]}...'")
        
        # Tokenize query
        query_tokens = self._tokenize(query)
        
        if not query_tokens:
            logger.warning("No valid query tokens")
            return []
        
        # Find candidate documents
        candidates = set()
        for token in query_tokens:
            candidates.update(self.inverted_index.get(token, set()))
        
        if not candidates:
            logger.info("No documents match query terms")
            return []
        
        # Calculate BM25 scores
        scores = {}
        matched_terms_map = {}
        
        for doc_id in candidates:
            score = 0.0
            matched_terms = []
            
            for token in query_tokens:
                if token in self.term_frequencies[doc_id]:
                    # Term frequency in document
                    tf = self.term_frequencies[doc_id][token]
                    
                    # Document frequency (number of docs containing term)
                    df = len(self.inverted_index[token])
                    
                    # Inverse document frequency
                    idf = math.log((self.num_docs - df + 0.5) / (df + 0.5) + 1.0)
                    
                    # Document length normalization
                    doc_len = self.doc_lengths[doc_id]
                    norm = 1.0 - self.b + self.b * (doc_len / self.avg_doc_length)
                    
                    # BM25 score component
                    score += idf * (tf * (self.k1 + 1.0)) / (tf + self.k1 * norm)
                    
                    matched_terms.append(token)
            
            if score > 0:
                scores[doc_id] = score
                matched_terms_map[doc_id] = matched_terms
        
        # Sort by score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        # Normalize scores to [0, 1]
        if ranked:
            max_score = ranked[0][1]
            if max_score > 0:
                ranked = [(doc_id, score / max_score) for doc_id, score in ranked]
        
        # Create results
        results = [
            KeywordSearchResult(
                score=score,
                chunk_id=doc_id,
                content=self.documents[doc_id],
                metadata=self.metadata[doc_id],
                matched_terms=matched_terms_map[doc_id]
            )
            for doc_id, score in ranked
        ]
        
        logger.info(f"Found {len(results)} keyword matches")
        return results
    
    def get_stats(self) -> dict:
        """Get index statistics."""
        return {
            "num_documents": self.num_docs,
            "vocabulary_size": len(self.inverted_index),
            "avg_doc_length": self.avg_doc_length,
            "parameters": {
                "k1": self.k1,
                "b": self.b
            }
        }


class KeywordSearchEngine:
    """
    Keyword search engine wrapper.
    
    Provides interface for building and searching keyword index.
    """
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """Initialize keyword search engine."""
        self.index = BM25Index(k1=k1, b=b)
        logger.info("KeywordSearchEngine initialized")
    
    def index_chunks(
        self,
        chunks: List[Tuple[str, str, dict]]
    ) -> None:
        """
        Index chunks for keyword search.
        
        Args:
            chunks: List of (chunk_id, content, metadata) tuples
        """
        self.index.add_documents(chunks)
    
    def search(
        self,
        query: str,
        top_k: int = 10
    ) -> List[KeywordSearchResult]:
        """
        Search for query.
        
        Args:
            query: Query text
            top_k: Number of results
            
        Returns:
            List of KeywordSearchResult objects
        """
        return self.index.search(query, top_k=top_k)
    
    def get_stats(self) -> dict:
        """Get search statistics."""
        return self.index.get_stats()
