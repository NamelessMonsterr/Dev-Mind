"""
System routes for DevMind API.
Health checks, statistics, and configuration endpoints.
"""

from fastapi import APIRouter, Depends
from datetime import datetime
import logging

from devmind.api.models import (
    HealthResponse,
    HealthStatus,
    SystemStats,
    IndexStats,
    ConfigResponse
)
from devmind.core.container import get_container, DIContainer

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])


def get_di_container() -> DIContainer:
    """Dependency injection for container."""
    return get_container()


@router.get("/health", response_model=HealthResponse)
async def health_check(container: DIContainer = Depends(get_di_container)):
    """
    Health check endpoint.
    
    Returns status of all subsystems.
    """
    logger.debug("Health check requested")
    
    subsystems = {}
    overall_status = "healthy"
    
    # Check embedding subsystem
    try:
        encoder = container.get_encoder()
        model_info = encoder.get_model_info()
        subsystems["embedding"] = HealthStatus(
            status="healthy",
            message=f"Model: {model_info['model_name']}",
            details=model_info
        )
    except Exception as e:
        subsystems["embedding"] = HealthStatus(
            status="down",
            message=str(e)
        )
        overall_status = "degraded"
    
    # Check vector store subsystem
    try:
        index_manager = container.get_index_manager()
        stats = index_manager.get_stats()
        subsystems["vector_store"] = HealthStatus(
            status="healthy",
            message=f"Indices: {len(stats)}",
            details=stats
        )
    except Exception as e:
        subsystems["vector_store"] = HealthStatus(
            status="down",
            message=str(e)
        )
        overall_status = "degraded"
    
    # Check retrieval subsystem
    try:
        pipeline = container.get_retrieval_pipeline()
        pipeline_stats = pipeline.get_stats()
        subsystems["retrieval"] = HealthStatus(
            status="healthy",
            message="Pipeline operational",
            details={"keyword_index_built": pipeline_stats["keyword_index_built"]}
        )
    except Exception as e:
        subsystems["retrieval"] = HealthStatus(
            status="down",
            message=str(e)
        )
        overall_status = "degraded"
    
    # Check ingestion subsystem
    try:
        job_manager = container.get_job_manager()
        jobs_stats = job_manager.get_stats()
        subsystems["ingestion"] = HealthStatus(
            status="healthy",
            message=f"Jobs: {jobs_stats['total_jobs']}",
            details=jobs_stats
        )
    except Exception as e:
        subsystems["ingestion"] = HealthStatus(
            status="down",
            message=str(e)
        )
        overall_status = "degraded"
    
    return HealthResponse(
        status=overall_status,
        version="0.1.0",
        subsystems=subsystems,
        timestamp=datetime.now().isoformat()
    )


@router.get("/stats", response_model=SystemStats)
async def get_stats(container: DIContainer = Depends(get_di_container)):
    """
    Get system statistics.
    
    Returns indexed chunk counts, search stats, etc.
    """
    logger.debug("Stats requested")
    
    try:
        # Get index stats
        index_manager = container.get_index_manager()
        index_stats_dict = index_manager.get_stats()
        
        indices = [
            IndexStats(
                name=name,
                num_vectors=count,
                dimension=container.embedding_dimension
            )
            for name, count in index_stats_dict.items()
        ]
        
        total_chunks = sum(index_stats_dict.values())
        
        # Get embedding model info
        encoder = container.get_encoder()
        model_info = encoder.get_model_info()
        
        # Get search stats
        avg_latency = container.get_avg_search_latency()
        
        # Get ingestion stats
        job_manager = container.get_job_manager()
        job_stats = job_manager.get_stats()
        
        return SystemStats(
            indices=indices,
            total_chunks=total_chunks,
            embedding_model=model_info["model_name"],
            avg_search_latency_ms=avg_latency,
            total_searches=container.total_searches,
            total_ingestion_jobs=job_stats["total_jobs"]
        )
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        # Return partial stats
        return SystemStats(
            indices=[],
            total_chunks=0,
            embedding_model="unknown",
            total_searches=container.total_searches,
            total_ingestion_jobs=0
        )


@router.get("/config", response_model=ConfigResponse)
async def get_config(container: DIContainer = Depends(get_di_container)):
    """
    Get system configuration.
    
    Returns model names, dimensions, and default parameters.
    """
    logger.debug("Config requested")
    
    # Get retrieval config
    pipeline = container.get_retrieval_pipeline()
    retrieval_config = pipeline.config
    
    return ConfigResponse(
        embedding_model_mvp="sentence-transformers/all-MiniLM-L6-v2",
        embedding_model_prod_doc="BAAI/bge-large-en-v1.5",
        embedding_model_prod_code="BAAI/bge-code-large",
        embedding_dimension=container.embedding_dimension,
        default_chunk_size=512,
        default_chunk_overlap=50,
        max_search_results=100,
        vector_weight=retrieval_config.vector_weight,
        keyword_weight=retrieval_config.keyword_weight
    )


@router.get("/ping")
async def ping():
    """Simple ping endpoint for connectivity tests."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
