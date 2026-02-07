"""
Job Manager for DevMind Ingestion System.
Manages ingestion jobs, progress tracking, and state persistence.
"""

from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import json
import uuid
import logging

from devmind.ingestion.pipeline import PipelineConfig, PipelineResult

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Status of an ingestion job."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobProgress:
    """Progress information for a job."""
    files_scanned: int = 0
    files_processed: int = 0
    sections_extracted: int = 0
    chunks_generated: int = 0
    current_file: str = ""
    errors_count: int = 0
    progress_percentage: float = 0.0


@dataclass
class IngestJob:
    """A complete ingestion job."""
    job_id: str
    config: PipelineConfig
    status: JobStatus
    progress: JobProgress
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[PipelineResult] = None
    errors: List[dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert job to dictionary."""
        data = asdict(self)
        # Convert enums and datetimes
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        if self.started_at:
            data["started_at"] = self.started_at.isoformat()
        if self.completed_at:
            data["completed_at"] = self.completed_at.isoformat()
        return data
    
    def duration_seconds(self) -> Optional[float]:
        """Get job duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class JobManager:
    """
    Manages ingestion jobs.
    
    Responsibilities:
    - Create and track ingestion jobs
    - Persist job state (for resume-ability)
    - Provide job status and progress
    - Handle job lifecycle (start, pause, resume, cancel)
    """
    
    def __init__(self, state_dir: Path):
        """
        Initialize Job Manager.
        
        Args:
            state_dir: Directory for persisting job state
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        self.jobs: dict[str, IngestJob] = {}
        self._load_jobs()
        
        logger.info(f"JobManager initialized with {len(self.jobs)} existing jobs")
    
    def create_job(
        self, 
        config: PipelineConfig,
        job_id: Optional[str] = None
    ) -> IngestJob:
        """
        Create a new ingestion job.
        
        Args:
            config: Pipeline configuration
            job_id: Optional job ID (generated if None)
            
        Returns:
            Created IngestJob
        """
        if job_id is None:
            job_id = str(uuid.uuid4())
        
        job = IngestJob(
            job_id=job_id,
            config=config,
            status=JobStatus.PENDING,
            progress=JobProgress(),
            created_at=datetime.now()
        )
        
        self.jobs[job_id] = job
        self._save_job(job)
        
        logger.info(f"Created job {job_id} for {config.source_path}")
        return job
    
    def get_job(self, job_id: str) -> Optional[IngestJob]:
        """
        Get job by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            IngestJob or None
        """
        return self.jobs.get(job_id)
    
    def update_progress(
        self, 
        job_id: str, 
        progress: JobProgress
    ) -> None:
        """
        Update job progress.
        
        Args:
            job_id: Job ID
            progress: Updated progress information
        """
        job = self.jobs.get(job_id)
        if job:
            job.progress = progress
            self._save_job(job)
            logger.debug(f"Updated progress for job {job_id}: {progress.progress_percentage}%")
    
    def start_job(self, job_id: str) -> None:
        """
        Mark job as started.
        
        Args:
            job_id: Job ID
        """
        job = self.jobs.get(job_id)
        if job:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now()
            self._save_job(job)
            logger.info(f"Started job {job_id}")
    
    def complete_job(
        self, 
        job_id: str, 
        result: PipelineResult
    ) -> None:
        """
        Mark job as completed.
        
        Args:
            job_id: Job ID
            result: Pipeline result
        """
        job = self.jobs.get(job_id)
        if job:
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()
            job.result = result
            self._save_job(job)
            
            duration = job.duration_seconds()
            logger.info(
                f"Completed job {job_id} in {duration:.2f}s "
                f"({result.total_chunks_generated} chunks)"
            )
    
    def fail_job(self, job_id: str, error: str) -> None:
        """
        Mark job as failed.
        
        Args:
            job_id: Job ID
            error: Error message
        """
        job = self.jobs.get(job_id)
        if job:
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now()
            job.errors.append({
                "timestamp": datetime.now().isoformat(),
                "error": error
            })
            self._save_job(job)
            logger.error(f"Job {job_id} failed: {error}")
    
    def pause_job(self, job_id: str) -> None:
        """Pause a running job."""
        job = self.jobs.get(job_id)
        if job and job.status == JobStatus.RUNNING:
            job.status = JobStatus.PAUSED
            self._save_job(job)
            logger.info(f"Paused job {job_id}")
    
    def resume_job(self, job_id: str) -> None:
        """Resume a paused job."""
        job = self.jobs.get(job_id)
        if job and job.status == JobStatus.PAUSED:
            job.status = JobStatus.RUNNING
            self._save_job(job)
            logger.info(f"Resumed job {job_id}")
    
    def cancel_job(self, job_id: str) -> None:
        """Cancel a job."""
        job = self.jobs.get(job_id)
        if job:
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now()
            self._save_job(job)
            logger.info(f"Cancelled job {job_id}")
    
    def list_jobs(
        self, 
        status: Optional[JobStatus] = None
    ) -> List[IngestJob]:
        """
        List all jobs, optionally filtered by status.
        
        Args:
            status: Optional status filter
            
        Returns:
            List of jobs
        """
        jobs = list(self.jobs.values())
        
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)
    
    def get_stats(self) -> dict:
        """
        Get aggregate statistics across all jobs.
        
        Returns:
            Dictionary with stats
        """
        stats = {
            "total_jobs": len(self.jobs),
            "by_status": {},
            "total_chunks": 0,
            "total_errors": 0
        }
        
        for job in self.jobs.values():
            status = job.status.value
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            if job.result:
                stats["total_chunks"] += job.result.total_chunks_generated
                stats["total_errors"] += len(job.result.errors)
        
        return stats
    
    def _save_job(self, job: IngestJob) -> None:
        """
        Save job state to disk.
        
        Args:
            job: Job to save
        """
        job_file = self.state_dir / f"{job.job_id}.json"
        
        try:
            # Create a serializable dict
            job_data = {
                "job_id": job.job_id,
                "status": job.status.value,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "config": {
                    "source_path": str(job.config.source_path),
                    "file_types": [ft.value for ft in job.config.file_types],
                    "languages": job.config.languages,
                    "chunking_strategy": job.config.chunking_strategy,
                    "chunk_size": job.config.chunk_size,
                    "chunk_overlap": job.config.chunk_overlap,
                },
                "progress": asdict(job.progress),
                "errors": job.errors
            }
            
            with open(job_file, "w") as f:
                json.dump(job_data, f, indent=2)
            logger.debug(f"Saved job {job.job_id} to {job_file}")
        except Exception as e:
            logger.error(f"Failed to save job {job.job_id}: {e}")
    
    def _load_jobs(self) -> None:
        """
        Load all jobs from state directory.
        """
        if not self.state_dir.exists():
            return
        
        for job_file in self.state_dir.glob("*.json"):
            try:
                with open(job_file, "r") as f:
                    data = json.load(f)
                
                # Reconstruct job from saved data
                from devmind.ingestion.file_scanner import FileType
                
                config = PipelineConfig(
                    source_path=Path(data["config"]["source_path"]),
                    file_types=[FileType(ft) for ft in data["config"]["file_types"]],
                    languages=data["config"]["languages"],
                    chunking_strategy=data["config"]["chunking_strategy"],
                    chunk_size=data["config"]["chunk_size"],
                    chunk_overlap=data["config"]["chunk_overlap"],
                )
                
                job = IngestJob(
                    job_id=data["job_id"],
                    config=config,
                    status=JobStatus(data["status"]),
                    progress=JobProgress(**data["progress"]),
                    created_at=datetime.fromisoformat(data["created_at"]),
                    started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
                    completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
                    errors=data.get("errors", [])
                )
                
                self.jobs[job.job_id] = job
                logger.debug(f"Loaded job {job.job_id} from {job_file}")
                
            except Exception as e:
                logger.error(f"Failed to load job from {job_file}: {e}")
    
    def cleanup_old_jobs(self, days: int = 30) -> int:
        """
        Remove job state for old completed jobs.
        
        Args:
            days: Delete jobs older than this many days
            
        Returns:
            Number of jobs deleted
            
        TODO: Implement cleanup logic
        """
        raise NotImplementedError()
