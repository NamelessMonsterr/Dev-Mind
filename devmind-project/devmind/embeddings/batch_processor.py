"""
Batch Processor for DevMind Embedding Service.
Handles efficient batch processing of large text datasets.
"""

from typing import List, Generator, Tuple, Optional
import numpy as np
from tqdm import tqdm
import logging

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Processes large batches of texts for embedding."""
    
    def __init__(self, encoder, batch_size: int = 32):
        """
        Initialize BatchProcessor.
        
        Args:
            encoder: Encoder instance to use
            batch_size: Number of texts to process at once
        """
        self.encoder = encoder
        self.batch_size = batch_size
        logger.info(f"BatchProcessor initialized with batch_size: {batch_size}")
        
    def process_batches(
        self, 
        texts: List[str],
        metadatas: Optional[List[dict]] = None,
        show_progress: bool = True
    ) -> Generator[Tuple[np.ndarray, List[dict]], None, None]:
        """
        Process texts in batches, yielding (embeddings, metadata).
        
        Args:
            texts: List of texts to encode
            metadatas: Optional list of metadata dicts (same length as texts)
            show_progress: Whether to show progress bar
            
        Yields:
            Tuple of (batch_embeddings, batch_metadatas)
        """
        if metadatas is not None and len(metadatas) != len(texts):
            raise ValueError(
                f"Metadatas length ({len(metadatas)}) must match "
                f"texts length ({len(texts)})"
            )
        
        total_batches = (len(texts) + self.batch_size - 1) // self.batch_size
        logger.info(
            f"Processing {len(texts)} texts in {total_batches} batches "
            f"of size {self.batch_size}"
        )
        
        iterator = range(0, len(texts), self.batch_size)
        if show_progress:
            iterator = tqdm(
                iterator, 
                total=total_batches, 
                desc="Encoding batches",
                unit="batch"
            )
        
        for i in iterator:
            batch_texts = texts[i:i + self.batch_size]
            batch_meta = (
                metadatas[i:i + self.batch_size] 
                if metadatas is not None 
                else [{}] * len(batch_texts)
            )
            
            try:
                embeddings = self.encoder.encode_batch(
                    batch_texts,
                    batch_size=self.batch_size,
                    show_progress=False  # We're already showing progress
                )
                yield embeddings, batch_meta
                
            except Exception as e:
                logger.error(f"Error processing batch starting at index {i}: {e}")
                # Yield empty batch or skip
                continue
    
    def process_all(
        self,
        texts: List[str],
        metadatas: Optional[List[dict]] = None,
        show_progress: bool = True
    ) -> Tuple[np.ndarray, List[dict]]:
        """
        Process all texts and return all embeddings and metadata.
        
        Args:
            texts: List of texts to encode
            metadatas: Optional list of metadata dicts
            show_progress: Whether to show progress bar
            
        Returns:
            Tuple of (all_embeddings, all_metadatas)
        """
        all_embeddings = []
        all_metadatas = []
        
        for embeddings, batch_meta in self.process_batches(
            texts, metadatas, show_progress
        ):
            all_embeddings.append(embeddings)
            all_metadatas.extend(batch_meta)
        
        if not all_embeddings:
            logger.warning("No embeddings generated")
            return (
                np.array([], dtype=np.float32).reshape(
                    0, self.encoder.get_embedding_dim()
                ),
                []
            )
        
        return np.vstack(all_embeddings), all_metadatas
