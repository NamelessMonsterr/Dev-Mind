"""
Dependency Injection Container for DevMind.
Manages singleton instances of core components.
"""

from pathlib import Path
from typing import Optional
import logging

from devmind.embeddings import Encoder, ModelManager
from devmind.vectorstore import IndexManager
from devmind.retrieval import RetrievalPipeline, RetrievalConfig
from devmind.ingestion import (
    FileScanner,
    IngestionPipeline,
    PipelineConfig,
    JobManager
)

logger = logging.getLogger(__name__)


class DIContainer:
    """
    Dependency Injection Container.
    
    Provides singleton instances of all core components.
    Initialized once at application startup.
    """
    
    def __init__(
        self,
        index_base_path: Path,
        job_state_path: Path,
        embedding_model: str = "mvp",
        embedding_dimension: int = 384
    ):
        """
        Initialize DI Container.
        
        Args:
            index_base_path: Base path for vector indices
            job_state_path: Path for job state persistence
            embedding_model: Default embedding model
            embedding_dimension: Vector embedding dimension
        """
        self.index_base_path = Path(index_base_path)
        self.job_state_path = Path(job_state_path)
        self.embedding_model = embedding_model
        self.embedding_dimension = embedding_dimension
        
        # Singleton instances
        self._model_manager: Optional[ModelManager] = None
        self._encoder: Optional[Encoder] = None
        self._index_manager: Optional[IndexManager] = None
        self._retrieval_pipeline: Optional[RetrievalPipeline] = None
        self._job_manager: Optional[JobManager] = None
        self._llm_manager: Optional = None  # LLMProviderManager
        self._chat_engine: Optional = None  # ChatEngine
        
        # Statistics
        self.total_searches = 0
        self.search_times = []
        
        logger.info(f"DIContainer initialized (model={embedding_model}, dim={embedding_dimension})")
    
    def get_model_manager(self) -> ModelManager:
        """Get ModelManager singleton."""
        if self._model_manager is None:
            from devmind.embeddings import get_model_manager
            self._model_manager = get_model_manager(device="auto")
            logger.info("ModelManager initialized")
        return self._model_manager
    
    def get_encoder(self, model_type: Optional[str] = None) -> Encoder:
        """
        Get Encoder singleton.
        
        Args:
            model_type: Model type to use (overrides default)
            
        Returns:
            Encoder instance
        """
        if self._encoder is None or (model_type and model_type != self._encoder.model_type):
            model_manager = self.get_model_manager()
            model_type = model_type or self.embedding_model
            self._encoder = Encoder(model_type=model_type, model_manager=model_manager)
            logger.info(f"Encoder initialized with model={model_type}")
        return self._encoder
    
    def get_index_manager(self) -> IndexManager:
        """Get IndexManager singleton."""
        if self._index_manager is None:
            self._index_manager = IndexManager(
                base_path=self.index_base_path,
                dimension=self.embedding_dimension
            )
            logger.info(f"IndexManager initialized at {self.index_base_path}")
        return self._index_manager
    
    def get_retrieval_pipeline(self) -> RetrievalPipeline:
        """Get RetrievalPipeline singleton."""
        if self._retrieval_pipeline is None:
            encoder = self.get_encoder()
            index_manager = self.get_index_manager()
            
            config = RetrievalConfig(
                top_k=10,
                use_keyword_search=True,
                vector_weight=0.7,
                keyword_weight=0.3
            )
            
            self._retrieval_pipeline = RetrievalPipeline(
                index_manager=index_manager,
                encoder=encoder,
                config=config
            )
            logger.info("RetrievalPipeline initialized")
        return self._retrieval_pipeline
    
    def get_job_manager(self) -> JobManager:
        """Get JobManager singleton."""
        if self._job_manager is None:
            self._job_manager = JobManager(state_dir=self.job_state_path)
            logger.info(f"JobManager initialized at {self.job_state_path}")
        return self._job_manager
    
    def create_ingestion_pipeline(self, config: PipelineConfig) -> IngestionPipeline:
        """
        Create a new IngestionPipeline instance.
        
        Note: Not a singleton - each ingestion job gets its own pipeline.
        
        Args:
            config: Pipeline configuration
            
        Returns:
            IngestionPipeline instance
        """
        return IngestionPipeline(config)
    
    def get_llm_manager(self):
        """Get LLMProviderManager singleton."""
        if self._llm_manager is None:
            from devmind.llm import get_llm_manager
            self._llm_manager = get_llm_manager()
            logger.info("LLMProviderManager initialized")
        return self._llm_manager
    
    def get_chat_engine(self):
        """Get ChatEngine singleton."""
        if self._chat_engine is None:
            from devmind.llm import ChatEngine
            
            retrieval_pipeline = self.get_retrieval_pipeline()
            llm_manager = self.get_llm_manager()
            
            self._chat_engine = ChatEngine(
                retrieval_pipeline=retrieval_pipeline,
                llm_manager=llm_manager,
                max_context_tokens=8000
            )
            logger.info("ChatEngine initialized")
        return self._chat_engine
    
    def record_search(self, search_time_ms: float) -> None:
        """Record search statistics."""
        self.total_searches += 1
        self.search_times.append(search_time_ms)
        
        # Keep only last 1000 search times
        if len(self.search_times) > 1000:
            self.search_times = self.search_times[-1000:]
    
    def get_avg_search_latency(self) -> Optional[float]:
        """Get average search latency in ms."""
        if not self.search_times:
            return None
        return sum(self.search_times) / len(self.search_times)
    
    def get_stats(self) -> dict:
        """Get container statistics."""
        return {
            "total_searches": self.total_searches,
            "avg_search_latency_ms": self.get_avg_search_latency(),
            "components_initialized": {
                "model_manager": self._model_manager is not None,
                "encoder": self._encoder is not None,
                "index_manager": self._index_manager is not None,
                "retrieval_pipeline": self._retrieval_pipeline is not None,
                "job_manager": self._job_manager is not None,
            }
        }
    
    async def shutdown(self) -> None:
        """
        Gracefully shutdown container with data persistence.
        
        Ensures:
        - All job states are persisted
        - Indices are saved
        - Resources are cleaned up properly
        """
        logger.info("Starting graceful shutdown of DIContainer...")
        
        shutdown_errors = []
        
        # 1. Explicitly persist all job states
        if self._job_manager:
            try:
                logger.info("Persisting job states...")
                # Explicitly call save_all to ensure all job states are written
                await self._job_manager.save_all_states()
                logger.info(f"Job states persisted successfully")
            except Exception as e:
                error_msg = f"Error persisting job states: {e}"
                logger.error(error_msg)
                shutdown_errors.append(error_msg)
        
        # 2. Save vector indices
        if self._index_manager:
            try:
                logger.info("Saving vector indices...")
                self._index_manager.save_all()
                logger.info("Vector indices saved successfully")
            except Exception as e:
                error_msg = f"Error saving indices: {e}"
                logger.error(error_msg)
                shutdown_errors.append(error_msg)
        
        # 3. Close any open connections/resources
        # (Add more cleanup as needed for future resources)
        
        if shutdown_errors:
            logger.warning(f"Shutdown completed with {len(shutdown_errors)} error(s)")
            for error in shutdown_errors:
                logger.warning(f"  - {error}")
        else:
            logger.info("DIContainer shutdown completed successfully")



# Global container instance
_container: Optional[DIContainer] = None


def initialize_container(
    index_base_path: Path,
    job_state_path: Path,
    embedding_model: str = "mvp",
    embedding_dimension: int = 384
) -> DIContainer:
    """Initialize global container."""
    global _container
    
    if _container is not None:
        logger.warning("Container already initialized, returning existing instance")
        return _container
    
    _container = DIContainer(
        index_base_path=index_base_path,
        job_state_path=job_state_path,
        embedding_model=embedding_model,
        embedding_dimension=embedding_dimension
    )
    
    logger.info("Global DIContainer initialized")
    return _container


def get_container() -> DIContainer:
    """Get global container instance."""
    if _container is None:
        raise RuntimeError("Container not initialized. Call initialize_container() first.")
    return _container
