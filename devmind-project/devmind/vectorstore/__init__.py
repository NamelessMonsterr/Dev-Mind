# DevMind Vector Store
"""
Vector storage and retrieval using FAISS.
"""

from .index_manager import IndexManager
from .faiss_client import FAISSClient

__all__ = ["IndexManager", "FAISSClient"]

__version__ = "0.1.0"
