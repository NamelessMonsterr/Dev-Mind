"""
Index Manager for DevMind Vector Store.
Manages multiple FAISS indices with metadata.
"""

from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
import logging
from .faiss_client import FAISSClient

logger = logging.getLogger(__name__)


class IndexManager:
    """Manages multiple FAISS indices with metadata."""
    
    def __init__(self, base_path: str | Path, dimension: int = 384):
        """
        Initialize Index Manager.
        
        Args:
            base_path: Base directory for storing indices
            dimension: Embedding dimension
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.dimension = dimension
        
        logger.info(f"IndexManager initialized at {self.base_path}")
        
        # Initialize indices for different content types
        self.indices: Dict[str, FAISSClient] = {}
        self._init_indices()
        
        # Metadata storage (in-memory for MVP, PostgreSQL for production)
        self.metadata: Dict[str, List[dict]] = {
            "code": [],
            "docs": [],
            "notes": [],
        }
        
        # Load metadata if exists
        self._load_metadata()
    
    def _init_indices(self) -> None:
        """Initialize FAISS indices for each content type."""
        for name in ["code", "docs", "notes"]:
            index_path = self.base_path / f"{name}_index.faiss"
            self.indices[name] = FAISSClient(
                dimension=self.dimension,
                index_path=index_path if index_path.exists() else None
            )
            logger.info(
                f"Initialized '{name}' index with {self.indices[name].get_size()} vectors"
            )
    
    def add_to_index(
        self, 
        index_name: str, 
        embeddings, 
        metadata: List[dict]
    ) -> None:
        """
        Add embeddings and metadata to specified index.
        
        Args:
            index_name: Name of index (code, docs, notes)
            embeddings: Array of embeddings to add
            metadata: List of metadata dicts (same length as embeddings)
        """
        if index_name not in self.indices:
            raise ValueError(
                f"Unknown index: {index_name}. "
                f"Available: {list(self.indices.keys())}"
            )
        
        if len(embeddings) != len(metadata):
            raise ValueError(
                f"Embeddings count ({len(embeddings)}) must match "
                f"metadata count ({len(metadata)})"
            )
        
        # Add to FAISS index
        self.indices[index_name].add(embeddings)
        
        # Add metadata
        self.metadata[index_name].extend(metadata)
        
        logger.info(
            f"Added {len(embeddings)} vectors to '{index_name}' index "
            f"(total: {self.indices[index_name].get_size()})"
        )
    
    def search(
        self, 
        index_name: str, 
        query_embedding, 
        k: int = 10,
        filter_fn: Optional[callable] = None
    ) -> List[Tuple[float, dict]]:
        """
        Search index and return results with metadata.
        
        Args:
            index_name: Name of index to search
            query_embedding: Query vector
            k: Number of results to return
            filter_fn: Optional function to filter metadata
            
        Returns:
            List of (score, metadata) tuples
        """
        if index_name not in self.indices:
            raise ValueError(
                f"Unknown index: {index_name}. "
                f"Available: {list(self.indices.keys())}"
            )
        
        # Search FAISS index
        distances, indices = self.indices[index_name].search(query_embedding, k)
        
        # Retrieve metadata
        results = []
        for dist, idx in zip(distances, indices):
            if idx < len(self.metadata[index_name]):
                meta = self.metadata[index_name][idx]
                
                # Apply filter if provided
                if filter_fn is None or filter_fn(meta):
                    results.append((float(dist), meta))
        
        logger.debug(f"Search in '{index_name}' returned {len(results)} results")
        return results
    
    def search_all(
        self, 
        query_embedding, 
        k: int = 10,
        weights: Optional[Dict[str, float]] = None
    ) -> List[Tuple[float, dict, str]]:
        """
        Search across all indices and merge results.
        
        Args:
            query_embedding: Query vector
            k: Number of results per index
            weights: Optional weights for each index (e.g., {'code': 1.5, 'docs': 1.0})
            
        Returns:
            List of (score, metadata, index_name) tuples, sorted by score
        """
        all_results = []
        weights = weights or {name: 1.0 for name in self.indices.keys()}
        
        for name in self.indices.keys():
            results = self.search(name, query_embedding, k)
            
            # Apply weight and add index name
            for score, meta in results:
                weighted_score = score * weights.get(name, 1.0)
                all_results.append((weighted_score, meta, name))
        
        # Sort by score (descending)
        all_results.sort(key=lambda x: x[0], reverse=True)
        
        return all_results[:k]
    
    def save_all(self) -> None:
        """Save all indices and metadata."""
        logger.info("Saving all indices and metadata")
        
        # Save FAISS indices
        for name, index in self.indices.items():
            index_path = self.base_path / f"{name}_index.faiss"
            index.save(index_path)
        
        # Save metadata
        self._save_metadata()
        
        logger.info("All indices and metadata saved")
    
    def _save_metadata(self) -> None:
        """Save metadata to JSON file."""
        metadata_path = self.base_path / "metadata.json"
        
        with open(metadata_path, "w") as f:
            json.dump(self.metadata, f, indent=2)
        
        logger.debug(f"Metadata saved to {metadata_path}")
    
    def _load_metadata(self) -> None:
        """Load metadata from JSON file if exists."""
        metadata_path = self.base_path / "metadata.json"
        
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                self.metadata = json.load(f)
            
            logger.info(f"Loaded metadata from {metadata_path}")
        else:
            logger.debug("No existing metadata found")
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics for all indices.
        
        Returns:
            Dictionary mapping index name to vector count
        """
        return {
            name: index.get_size() 
            for name, index in self.indices.items()
        }
    
    def clear_index(self, index_name: str) -> None:
        """
        Clear a specific index.
        
        Args:
            index_name: Name of index to clear
        """
        if index_name not in self.indices:
            raise ValueError(f"Unknown index: {index_name}")
        
        self.indices[index_name].reset()
        self.metadata[index_name] = []
        
        logger.info(f"Cleared '{index_name}' index")
    
    def clear_all(self) -> None:
        """Clear all indices."""
        for name in self.indices.keys():
            self.clear_index(name)
        
        logger.info("Cleared all indices")
