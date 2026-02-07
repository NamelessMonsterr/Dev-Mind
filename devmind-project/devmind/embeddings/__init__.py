# DevMind Embedding Service
"""
Core embedding service for DevMind RAG system.
Handles text-to-vector transformation using sentence-transformers.
"""

from .model_manager import get_model_manager, ModelManager
from .encoder import Encoder

__all__ = ["get_model_manager", "ModelManager", "Encoder"]

__version__ = "0.1.0"
