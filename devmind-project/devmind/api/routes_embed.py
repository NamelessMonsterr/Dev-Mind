"""
Embedding routes for DevMind API.
Endpoints for generating text embeddings.
"""

from fastapi import APIRouter, HTTPException, Depends
import time
import logging
import numpy as np

from devmind.api.models import (
    EmbedRequest,
    EmbedBatchRequest,
    EmbedResponse,
    EmbedBatchResponse
)
from devmind.core.container import get_container, DIContainer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/embed", tags=["embedding"])


def get_di_container() -> DIContainer:
    """Dependency injection for container."""
    return get_container()


@router.post("", response_model=EmbedResponse)
@router.post("/", response_model= EmbedResponse)
async def embed_text(
    request: EmbedRequest,
    container: DIContainer = Depends(get_di_container)
):
    """
    Generate embedding for a single text.
    
    Args:
        request: Embed request with text and model type
        
    Returns:
        Embedding vector and metadata
    """
    logger.info(f"Embed request (model={request.model_type}, len={len(request.text)})")
    
    start_time = time.time()
    
    try:
        # Get encoder
        encoder = container.get_encoder(model_type=request.model_type)
        
        # Generate embedding
        embedding = encoder.encode(request.text, normalize=request.normalize)
        
        # Convert to list
        embedding_list = embedding.tolist()
        
        processing_time_ms = (time.time() - start_time) * 1000
        
        logger.info(f"Generated embedding in {processing_time_ms:.2f}ms")
        
        return EmbedResponse(
            embedding=embedding_list,
            dimension=len(embedding_list),
            model_type=request.model_type,
            processing_time_ms=processing_time_ms
        )
        
    except Exception as e:
        logger.error(f"Embedding error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")


@router.post("/batch", response_model=EmbedBatchResponse)
async def embed_batch(
    request: EmbedBatchRequest,
    container: DIContainer = Depends(get_di_container)
):
    """
    Generate embeddings for multiple texts in batch.
    
    More efficient than multiple single requests.
    
    Args:
        request: Batch embed request with texts and model type
        
    Returns:
        List of embedding vectors and metadata
    """
    logger.info(
        f"Batch embed request (model={request.model_type}, "
        f"count={len(request.texts)})"
    )
    
    start_time = time.time()
    
    try:
        # Get encoder
        encoder = container.get_encoder(model_type=request.model_type)
        
        # Generate embeddings in batch
        embeddings = encoder.encode_batch(
            request.texts,
            batch_size=request.batch_size,
            normalize=request.normalize
        )
        
        # Convert to list of lists
        embeddings_list = embeddings.tolist()
        
        processing_time_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"Generated {len(embeddings_list)} embeddings in {processing_time_ms:.2f}ms "
            f"({processing_time_ms/len(embeddings_list):.2f}ms per embedding)"
        )
        
        return EmbedBatchResponse(
            embeddings=embeddings_list,
            count=len(embeddings_list),
            dimension=len(embeddings_list[0]) if embeddings_list else 0,
            model_type=request.model_type,
            processing_time_ms=processing_time_ms
        )
        
    except Exception as e:
        logger.error(f"Batch embedding error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch embedding failed: {str(e)}")
