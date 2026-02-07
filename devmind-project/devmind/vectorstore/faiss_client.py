"""
FAISS Client for DevMind Vector Store.
Handles vector database operations using FAISS.
"""

import faiss
import numpy as np
from typing import Tuple, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class FAISSClient:
    """FAISS vector database client."""
    
    def __init__(
        self, 
        dimension: int, 
        index_path: Optional[Path] = None,
        index_type: str = "flat"
    ):
        """
        Initialize FAISS Client.
        
        Args:
            dimension: Dimension of vectors
            index_path: Optional path to load existing index
            index_type: Type of index ('flat', 'ivf', 'hnsw')
        """
        self.dimension = dimension
        self.index_path = index_path
        self.index_type = index_type
        
        # Create or load index
        if index_path and index_path.exists():
            logger.info(f"Loading existing index from {index_path}")
            self.index = faiss.read_index(str(index_path))
            logger.info(f"Loaded index with {self.index.ntotal} vectors")
        else:
            logger.info(f"Creating new {index_type} index with dimension {dimension}")
            self.index = self._create_index(dimension, index_type)
    
    def _create_index(self, dimension: int, index_type: str) -> faiss.Index:
        """
        Create a FAISS index based on type.
        
        Args:
            dimension: Vector dimension
            index_type: Type of index to create
            
        Returns:
            FAISS index
        """
        if index_type == "flat":
            # IndexFlatIP for inner product (cosine similarity with normalized vectors)
            return faiss.IndexFlatIP(dimension)
        
        elif index_type == "ivf":
            # IVF index for larger datasets (requires training)
            quantizer = faiss.IndexFlatIP(dimension)
            return faiss.IndexIVFFlat(quantizer, dimension, 100)  # 100 clusters
        
        elif index_type == "hnsw":
            # HNSW index for fast approximate search
            return faiss.IndexHNSWFlat(dimension, 32)  # 32 neighbors
        
        else:
            raise ValueError(f"Unknown index type: {index_type}")
    
    def add(self, embeddings: np.ndarray) -> None:
        """
        Add embeddings to index.
        
        Args:
            embeddings: Array of embeddings to add, shape (n, dimension)
        """
        if embeddings.ndim != 2:
            raise ValueError(
                f"Embeddings must be 2D array, got shape {embeddings.shape}"
            )
        
        if embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"Embedding dimension {embeddings.shape[1]} doesn't match "
                f"index dimension {self.dimension}"
            )
        
        # Ensure float32
        embeddings = embeddings.astype('float32')
        
        # For IVF index, train if not trained
        if isinstance(self.index, faiss.IndexIVFFlat) and not self.index.is_trained:
            logger.info(f"Training IVF index with {len(embeddings)} vectors")
            self.index.train(embeddings)
        
        self.index.add(embeddings)
        logger.debug(f"Added {len(embeddings)} vectors to index")
    
    def search(
        self, 
        query_embedding: np.ndarray, 
        k: int = 10
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k most similar vectors.
        
        Args:
            query_embedding: Query vector, shape (dimension,) or (1, dimension)
            k: Number of results to return
            
        Returns:
            Tuple of (distances, indices)
            - distances: array of shape (k,) with similarity scores
            - indices: array of shape (k,) with vector indices
        """
        # Ensure correct shape
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        if query_embedding.shape[1] != self.dimension:
            raise ValueError(
                f"Query embedding dimension {query_embedding.shape[1]} "
                f"doesn't match index dimension {self.dimension}"
            )
        
        # Ensure float32
        query_embedding = query_embedding.astype('float32')
        
        # Search
        k = min(k, self.index.ntotal)  # Don't search for more than we have
        distances, indices = self.index.search(query_embedding, k)
        
        return distances[0], indices[0]
    
    def save(self, path: Optional[Path] = None) -> None:
        """
        Save index to disk.
        
        Args:
            path: Path to save to (uses self.index_path if None)
        """
        save_path = path or self.index_path
        
        if save_path is None:
            raise ValueError("No save path specified")
        
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Saving index to {save_path}")
        faiss.write_index(self.index, str(save_path))
        logger.info(f"Saved index with {self.index.ntotal} vectors")
    
    def get_size(self) -> int:
        """
        Get number of vectors in index.
        
        Returns:
            Number of vectors
        """
        return self.index.ntotal
    
    def reset(self) -> None:
        """Reset the index (remove all vectors)."""
        logger.info("Resetting index")
        self.index = self._create_index(self.dimension, self.index_type)
