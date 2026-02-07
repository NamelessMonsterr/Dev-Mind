"""
DevMind API Server.
Main entry point for running the FastAPI application.
"""

import uvicorn
import logging
from pathlib import Path

from devmind.api.app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Run the FastAPI server."""
    logger.info("Starting DevMind API server...")
    
    # Create app
    app = create_app()
    
    # Run with uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()
