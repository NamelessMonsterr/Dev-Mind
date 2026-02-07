"""
Prometheus metrics endpoints for DevMind.
"""

from fastapi import APIRouter
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])

# Define metrics
total_searches = Counter(
    'devmind_searches_total',
    'Total number of searches performed'
)

search_latency = Histogram(
    'devmind_search_latency_seconds',
    'Search operation latency in seconds',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

llm_latency = Histogram(
    'devmind_llm_latency_seconds',
    'LLM generation latency in seconds',
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0]
)

ingestion_jobs_total = Counter(
    'devmind_ingestion_jobs_total',
    'Total number of ingestion jobs',
    ['status']
)

vector_index_size = Gauge(
    'devmind_vector_index_size',
    'Number of vectors in index',
    ['index_name']
)

embedding_operations = Counter(
    'devmind_embedding_operations_total',
    'Total embedding operations',
    ['model_type']
)

chat_messages = Counter(
    'devmind_chat_messages_total',
    'Total chat messages',
    ['role', 'provider']
)

@router.get("")
@router.get("/")
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus text format.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


def record_search(latency_seconds: float):
    """Record a search operation."""
    total_searches.inc()
    search_latency.observe(latency_seconds)


def record_llm_generation(latency_seconds: float, provider: str):
    """Record an LLM generation."""
    llm_latency.observe(latency_seconds)
    chat_messages.labels(role='assistant', provider=provider).inc()


def record_ingestion_job(status: str):
    """Record an ingestion job."""
    ingestion_jobs_total.labels(status=status).inc()


def update_index_size(index_name: str, size: int):
    """Update vector index size."""
    vector_index_size.labels(index_name=index_name).set(size)


def record_embedding(model_type: str):
    """Record an embedding operation."""
    embedding_operations.labels(model_type=model_type).inc()
