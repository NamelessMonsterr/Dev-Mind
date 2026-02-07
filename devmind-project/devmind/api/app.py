"""
DevMind FastAPI Application.
Main application factory and router configuration.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path

from devmind.core.container import initialize_container, get_container
from devmind.api import routes_ingest, routes_search, routes_embed, routes_system, routes_chat

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown.
    
    Handles:
    - Container initialization on startup
    - Resource cleanup on shutdown
    """
    # Startup
    logger.info("Starting DevMind API...")
    
    # Initialize DI container with configurable settings
    index_path = Path(os.getenv("INDEX_PATH", "./data/indices"))
    job_path = Path(os.getenv("JOB_STATE_PATH", "./data/jobs"))
    embedding_model = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    embedding_dimension = int(os.getenv("EMBEDDING_DIMENSION", "384"))
    
    index_path.mkdir(parents=True, exist_ok=True)
    job_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Using embedding model: {embedding_model} (dimension: {embedding_dimension})")
    
    initialize_container(
        index_base_path=index_path,
        job_state_path=job_path,
        embedding_model=embedding_model,
        embedding_dimension=embedding_dimension
    )
    
    logger.info("DevMind API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down DevMind API...")
    
    container = get_container()
    await container.shutdown()
    
    logger.info("DevMind API shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="DevMind API",
        description="Semantic code search and knowledge retrieval for developers",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # CORS middleware - configurable for production
    allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
    allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]
    
    logger.info(f"CORS allowed origins: {allowed_origins}")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc),
                "path": str(request.url)
            }
        )
    
    # Include routers
    app.include_router(routes_ingest.router)
    app.include_router(routes_search.router)
    app.include_router(routes_embed.router)
    app.include_router(routes_system.router)
    app.include_router(routes_chat.router)
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "service": "DevMind API",
            "version": "0.1.0",
            "status": "operational",
            "docs": "/docs",
            "health": "/health"
        }
    
    logger.info("FastAPI app created")
    return app
