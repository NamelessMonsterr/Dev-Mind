"""
Model Manager for DevMind Embedding Service.
Handles loading, caching, and managing embedding models.
"""

from sentence_transformers import SentenceTransformer
from typing import Dict, Optional
import torch
import logging

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages loading and caching of embedding models."""
    
    # Model configurations
    MODEL_MAP = {
        "mvp": "sentence-transformers/all-MiniLM-L6-v2",
        "production_doc": "BAAI/bge-large-en-v1.5",
        "production_code": "BAAI/bge-code-large",
    }
    
    def __init__(self, device: str = "auto"):
        """
        Initialize Model Manager.
        
        Args:
            device: Device to use ('auto', 'cpu', 'cuda')
        """
        self._models: Dict[str, SentenceTransformer] = {}
        
        if device == "auto":
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self._device = device
            
        logger.info(f"ModelManager initialized with device: {self._device}")
        
    def load_model(self, model_name: str) -> SentenceTransformer:
        """
        Load model from cache or download.
        
        Args:
            model_name: Name or path of the model
            
        Returns:
            Loaded SentenceTransformer model
        """
        if model_name not in self._models:
            logger.info(f"Loading model: {model_name} on {self._device}")
            self._models[model_name] = SentenceTransformer(
                model_name, 
                device=self._device
            )
            logger.info(f"Model loaded: {model_name}")
        else:
            logger.debug(f"Using cached model: {model_name}")
            
        return self._models[model_name]
    
    def get_model(self, model_type: str) -> SentenceTransformer:
        """
        Get model by type (mvp, production_doc, production_code).
        
        Args:
            model_type: Type of model to load
            
        Returns:
            Loaded SentenceTransformer model
            
        Raises:
            ValueError: If model_type is not recognized
        """
        if model_type not in self.MODEL_MAP:
            raise ValueError(
                f"Unknown model type: {model_type}. "
                f"Available types: {list(self.MODEL_MAP.keys())}"
            )
            
        model_name = self.MODEL_MAP[model_type]
        return self.load_model(model_name)
    
    def get_device(self) -> str:
        """Get the current device being used."""
        return self._device
    
    def clear_cache(self) -> None:
        """Clear all cached models and free GPU memory."""
        logger.info("Clearing model cache")
        self._models.clear()
        
        if self._device == "cuda":
            torch.cuda.empty_cache()
            logger.info("GPU cache cleared")
    
    def get_loaded_models(self) -> list:
        """Get list of currently loaded model names."""
        return list(self._models.keys())


# Singleton instance for global use
_global_manager: Optional[ModelManager] = None


def get_model_manager(device: str = "auto") -> ModelManager:
    """
    Get or create the global ModelManager instance.
    
    Args:
        device: Device to use if creating new manager
        
    Returns:
        Global ModelManager instance
    """
    global _global_manager
    
    if _global_manager is None:
        _global_manager = ModelManager(device=device)
        
    return _global_manager
