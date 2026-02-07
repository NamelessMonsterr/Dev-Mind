"""
Request/Response Logging Middleware for DevMind.
Provides structured logging of all HTTP requests and responses.
"""

import time
import json
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests and responses.
    Tracks latency, status codes, and request details.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        log_body: bool = False,
        max_body_length: int = 1000
    ):
        super().__init__(app)
        self.log_body = log_body
        self.max_body_length = max_body_length
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process request and log details."""
        start_time = time.time()
        
        # Generate request ID
        request_id = f"{int(start_time * 1000)}-{id(request)}"
        
        # Log request
        request_log = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_host": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }
        
        # Optionally log request body
        if self.log_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if len(body) <= self.max_body_length:
                    request_log["body"] = body.decode()[:self.max_body_length]
                else:
                    request_log["body"] = f"<truncated {len(body)} bytes>"
            except Exception as e:
                request_log["body_error"] = str(e)
        
        logger.info(f"Request started", extra=request_log)
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log exception
            duration = time.time() - start_time
            error_log = {
                **request_log,
                "status_code": 500,
                "duration_ms": duration * 1000,
                "error": str(e),
                "error_type": type(e).__name__
            }
            logger.error(f"Request failed", extra=error_log)
            raise
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        response_log = {
            **request_log,
            "status_code": response.status_code,
            "duration_ms": duration * 1000,
        }
        
        # Log level based on status code
        if response.status_code >= 500:
            logger.error(f"Request completed with error", extra=response_log)
        elif response.status_code >= 400:
            logger.warning(f"Request completed with client error", extra=response_log)
        else:
            logger.info(f"Request completed", extra=response_log)
        
        # Add custom headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration * 1000:.2f}ms"
        
        return response


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to catch and log unexpected errors.
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Catch and log errors."""
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Log full error with stack trace
            logger.exception(
                f"Unhandled exception in {request.method} {request.url.path}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            
            # Return 500 error
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                    "type": type(e).__name__
                }
            )
