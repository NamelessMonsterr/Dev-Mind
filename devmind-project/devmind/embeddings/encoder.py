"""
Encoder for DevMind Embedding Service.
Converts text to vector embeddings.
"""

from typing import List, Union
import numpy as np
import logging
from .model_manager import get_model_manager, ModelManager

logger = logging.getLogger(__name__)


class Encoder:
    """Encodes text into vector embeddings."""
    
    def __init__(
        self, 
        model_type: str = "mvp",
        model_manager: ModelManager = None
    ):
        """
        Initialize Encoder.
        
        Args:
            model_type: Type of model to use (mvp, production_doc, production_code)
            model_manager: Optional ModelManager instance (uses global if None)
        """
        self.model_type = model_type
        self.model_manager = model_manager or get_model_manager()
        self.model = self.model_manager.get_model(model_type)
        
        logger.info(
            f"Encoder initialized with model_type: {model_type}, "
            f"dimension: {self.get_embedding_dim()}"
        )
        
    def encode(self, text: str, normalize: bool = True) -> np.ndarray:
        """
        Encode single text to vector.
        
        Args:
            text: Text to encode
            normalize: Whether to normalize embeddings
            
        Returns:
            numpy array of shape (embedding_dim,)
        """
        if not text or not text.strip():
            logger.warning("Empty text provided to encode(), returning zero vector")
            return np.zeros(self.get_embedding_dim(), dtype=np.float32)
            
        embedding = self.model.encode(
            [text], 
            normalize_embeddings=normalize,
            convert_to_numpy=True
        )[0]
        
        return embedding.astype(np.float32)
    
    def encode_batch(
        self, 
        texts: List[str], 
        batch_size: int = 32,
        show_progress: bool = False,
        normalize: bool = True
    ) -> np.ndarray:
        """
        Encode multiple texts to vectors.
        
        Args:
            texts: List of texts to encode
            batch_size: Batch size for encoding
            show_progress: Whether to show progress bar
            normalize: Whether to normalize embeddings
            
        Returns:
            numpy array of shape (num_texts, embedding_dim)
        """
        if not texts:
            logger.warning("Empty texts list provided to encode_batch()")
            return np.array([], dtype=np.float32).reshape(0, self.get_embedding_dim())
        
        # Filter out empty texts but keep track of indices
        valid_texts = []
        valid_indices = []
        
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
                valid_indices.append(i)
        
        if not valid_texts:
            logger.warning("No valid texts in batch, returning zero vectors")
            return np.zeros((len(texts), self.get_embedding_dim()), dtype=np.float32)
        
        # Encode valid texts
        embeddings = self.model.encode(
            valid_texts,
            batch_size=batch_size,
            normalize_embeddings=normalize,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        ).astype(np.float32)
        
        # If all texts were valid, return directly
        if len(valid_texts) == len(texts):
            return embeddings
        
        # Otherwise, create result array with zero vectors for invalid texts
        result = np.zeros((len(texts), self.get_embedding_dim()), dtype=np.float32)
        result[valid_indices] = embeddings
        
        return result
    
    def get_embedding_dim(self) -> int:
        """
        Get dimensionality of embeddings.
        
        Returns:
            Embedding dimension
        """
        return self.model.get_sentence_embedding_dimension()
    
    def get_model_info(self) -> dict:
        """
        Get information about the current model.
        
        Returns:
            Dictionary with model information
        """
        return {
            "model_type": self.model_type,
            "embedding_dim": self.get_embedding_dim(),
            "device": self.model_manager.get_device(),
            "max_seq_length": self.model.max_seq_length,
        }
