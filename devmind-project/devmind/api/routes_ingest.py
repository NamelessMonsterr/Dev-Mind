"""
Ingestion routes for DevMind API.
Endpoints for starting and monitoring ingestion jobs.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from datetime import datetime
import logging

from devmind.api.models import (
    IngestRequest,
    IngestResponse,
    JobStatusResponse,
    JobProgressModel
)
from devmind.core.container import get_container, DIContainer
from devmind.ingestion import PipelineConfig, FileType
from devmind.ingestion.job_manager import JobStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


def get_di_container() -> DIContainer:
    """Dependency injection for container."""
    return get_container()


async def run_ingestion_job(job_id: str, config: PipelineConfig, container: DIContainer):
    """
    Background task for running ingestion.
    
    Args:
        job_id: Job ID
        config: Pipeline configuration
        container: DI container
    """
    logger.info(f"Starting ingestion job {job_id}")
    
    job_manager = container.get_job_manager()
    
    try:
        # Start job
        job_manager.start_job(job_id)
        
        # Create pipeline
        pipeline = container.create_ingestion_pipeline(config)
        
        # Run ingestion
        result = pipeline.run()
        
        # Mark complete
        job_manager.complete_job(job_id, result)
        
        logger.info(f"Ingestion job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Ingestion job {job_id} failed: {e}")
        job_manager.fail_job(job_id, str(e))


@router.post("/start", response_model=IngestResponse)
async def start_ingestion(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    container: DIContainer = Depends(get_di_container)
):
    """
    Start a new ingestion job.
    
    Runs ingestion in the background and returns immediately with job ID.
    """
    logger.info(f"Received ingestion request for: {request.source_path}")
    
    try:
        # Parse file types
        file_types = None
        if request.file_types:
            file_types = [FileType(ft.upper()) for ft in request.file_types]
        
        # Create pipeline config
        config = PipelineConfig(
            source_path=request.source_path,
            file_types=file_types,
            languages=request.languages,
            chunking_strategy=request.chunking_strategy,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap
        )
        
        # Create job
        job_manager = container.get_job_manager()
        job = job_manager.create_job(config)
        
        # Add background task
        background_tasks.add_task(
            run_ingestion_job,
            job_id=job.job_id,
            config=config,
            container=container
        )
        
        logger.info(f"Created ingestion job {job.job_id}")
        
        return IngestResponse(
            job_id=job.job_id,
            status="PENDING",
            message="Ingestion job created and queued",
            created_at=job.created_at.isoformat()
        )
        
    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating ingestion job: {e}")
        raise HTTPException(status_code=500, detail="Failed to create ingestion job")


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    container: DIContainer = Depends(get_di_container)
):
    """
    Get status of an ingestion job.
    
    Args:
        job_id: Job ID to query
        
    Returns:
        Job status and progress
    """
    logger.info(f"Querying status for job {job_id}")
    
    try:
        job_manager = container.get_job_manager()
        job = job_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Convert progress to model
        progress = JobProgressModel(
            files_scanned=job.progress.files_scanned,
            files_processed=job.progress.files_processed,
            sections_extracted=job.progress.sections_extracted,
            chunks_generated=job.progress.chunks_generated,
            current_stage=job.progress.current_stage
        )
        
        return JobStatusResponse(
            job_id=job.job_id,
            status=job.status.value,
            progress=progress,
            created_at=job.created_at.isoformat(),
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            errors=job.errors
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get job status")


@router.get("/jobs", response_model=list[JobStatusResponse])
async def list_jobs(
    status: str = None,
    limit: int = 20,
    container: DIContainer = Depends(get_di_container)
):
    """
    List ingestion jobs.
    
    Args:
        status: Filter by status (PENDING, RUNNING, COMPLETED, FAILED)
        limit: Maximum number of jobs to return
        
    Returns:
        List of job statuses
    """
    try:
        job_manager = container.get_job_manager()
        
        # Filter by status if provided
        if status:
            try:
                job_status = JobStatus(status.upper())
                jobs = job_manager.list_jobs(status=job_status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        else:
            jobs = job_manager.list_jobs()
        
        # Limit results
        jobs = jobs[:limit]
        
        # Convert to response models
        results = []
        for job in jobs:
            progress = JobProgressModel(
                files_scanned=job.progress.files_scanned,
                files_processed=job.progress.files_processed,
                sections_extracted=job.progress.sections_extracted,
                chunks_generated=job.progress.chunks_generated,
                current_stage=job.progress.current_stage
            )
            
            results.append(JobStatusResponse(
                job_id=job.job_id,
                status=job.status.value,
                progress=progress,
                created_at=job.created_at.isoformat(),
                started_at=job.started_at.isoformat() if job.started_at else None,
                completed_at=job.completed_at.isoformat() if job.completed_at else None,
                errors=job.errors
            ))
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to list jobs")
