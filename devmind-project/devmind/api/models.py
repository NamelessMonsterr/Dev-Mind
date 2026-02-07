"""
Pydantic models for DevMind API.
Request and response schemas for all endpoints.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from pathlib import Path


# ========================================
# SEARCH MODELS
# ========================================

class FilterCriteriaModel(BaseModel):
    """Filter criteria for search results."""
    file_types: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    path_prefix: Optional[str] = None
    path_excludes: Optional[List[str]] = None
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)
    max_results: Optional[int] = Field(default=None, gt=0)
    line_range: Optional[tuple] = None
    section_types: Optional[List[str]] = None


class SearchRequest(BaseModel):
    """Request model for search endpoints."""
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=10, gt=0, le=100)
    use_keyword_search: bool = Field(default=True)
    filters: Optional[FilterCriteriaModel] = None
    
    @validator('query')
    def query_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty or whitespace only')
        return v.strip()


class SearchResultModel(BaseModel):
    """Single search result."""
    score: float
    content: str
    file_path: str
    start_line: int
    end_line: int
    section_type: str
    language: str
    chunk_id: str
    index_name: str
    matched_terms: Optional[List[str]] = None
    vector_score: float = 0.0
    keyword_score: float = 0.0


class SearchResponse(BaseModel):
    """Response model for search endpoints."""
    query: str
    results: List[SearchResultModel]
    total_results: int
    search_time_ms: float
    filters_applied: bool = False


# ========================================
# INGESTION MODELS
# ========================================

class IngestRequest(BaseModel):
    """Request model for ingestion."""
    source_path: str = Field(..., min_length=1)
    languages: Optional[List[str]] = Field(default=None)
    file_types: Optional[List[str]] = Field(default=None)
    chunk_size: int = Field(default=512, gt=0, le=2000)
    chunk_overlap: int = Field(default=50, ge=0)
    chunking_strategy: str = Field(default="fixed")
    
    @validator('source_path')
    def validate_path(cls, v):
        path = Path(v)
        if not path.exists():
            raise ValueError(f'Path does not exist: {v}')
        if not path.is_dir():
            raise ValueError(f'Path is not a directory: {v}')
        return str(path.absolute())
    
    @validator('chunk_overlap')
    def overlap_less_than_size(cls, v, values):
        if 'chunk_size' in values and v >= values['chunk_size']:
            raise ValueError('chunk_overlap must be less than chunk_size')
        return v


class IngestResponse(BaseModel):
    """Response model for ingestion start."""
    job_id: str
    status: str
    message: str
    created_at: str


class JobProgressModel(BaseModel):
    """Job progress information."""
    files_scanned: int = 0
    files_processed: int = 0
    sections_extracted: int = 0
    chunks_generated: int = 0
    current_stage: str = "PENDING"


class JobStatusResponse(BaseModel):
    """Response model for job status."""
    job_id: str
    status: str
    progress: JobProgressModel
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    errors: List[Dict[str, Any]] = []


# ========================================
# EMBEDDING MODELS
# ========================================

class EmbedRequest(BaseModel):
    """Request model for single embedding."""
    text: str = Field(..., min_length=1, max_length=10000)
    model_type: str = Field(default="mvp")
    normalize: bool = Field(default=True)
    
    @validator('model_type')
    def validate_model_type(cls, v):
        valid_types = ["mvp", "production_doc", "production_code"]
        if v not in valid_types:
            raise ValueError(f'model_type must be one of {valid_types}')
        return v


class EmbedBatchRequest(BaseModel):
    """Request model for batch embeddings."""
    texts: List[str] = Field(..., min_items=1, max_items=1000)
    model_type: str = Field(default="mvp")
    normalize: bool = Field(default=True)
    batch_size: int = Field(default=32, gt=0, le=128)
    
    @validator('texts')
    def validate_texts(cls, v):
        if not all(t.strip() for t in v):
            raise ValueError('All texts must be non-empty')
        return v


class EmbedResponse(BaseModel):
    """Response model for single embedding."""
    embedding: List[float]
    dimension: int
    model_type: str
    processing_time_ms: float


class EmbedBatchResponse(BaseModel):
    """Response model for batch embeddings."""
    embeddings: List[List[float]]
    count: int
    dimension: int
    model_type: str
    processing_time_ms: float


# ========================================
# SYSTEM MODELS
# ========================================

class HealthStatus(BaseModel):
    """Health status for a subsystem."""
    status: str  # "healthy", "degraded", "down"
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str  # "healthy", "degraded", "down"
    version: str = "0.1.0"
    subsystems: Dict[str, HealthStatus]
    timestamp: str


class IndexStats(BaseModel):
    """Statistics for a single index."""
    name: str
    num_vectors: int
    dimension: int


class SystemStats(BaseModel):
    """System statistics."""
    indices: List[IndexStats]
    total_chunks: int
    embedding_model: str
    avg_search_latency_ms: Optional[float] = None
    total_searches: int = 0
    total_ingestion_jobs: int = 0


class ConfigResponse(BaseModel):
    """System configuration."""
    embedding_model_mvp: str
    embedding_model_prod_doc: str
    embedding_model_prod_code: str
    embedding_dimension: int
    default_chunk_size: int
    default_chunk_overlap: int
    max_search_results: int
    vector_weight: float
    keyword_weight: float


# ========================================
# ERROR MODELS
# ========================================

class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
    error_type: Optional[str] = None
    timestamp: str
