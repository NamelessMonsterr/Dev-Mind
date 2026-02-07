"""
Security middleware for DevMind API.

Implements security headers and protections.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    
    Headers included:
    - X-Content-Type-Options: Prevent MIME sniffing
    - X-Frame-Options: Prevent clickjacking
    - X-XSS-Protection: Legacy XSS protection
    - Strict-Transport-Security: Force HTTPS (production only)
    - Content-Security-Policy: Restrict resource loading
    """
    
    def __init__(self, app: ASGIApp, enable_hsts: bool = False):
        """
        Initialize security headers middleware.
        
        Args:
            app: ASGI application
            enable_hsts: Enable HSTS (only in production over HTTPS)
        """
        super().__init__(app)
        self.enable_hsts = enable_hsts
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Legacy XSS protection (for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy - restrictive for API
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy (disable unnecessary features)
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS - only enable in production over HTTPS
        if self.enable_hsts:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all requests for security auditing.
    
    Logs:
    - Request method, path, client IP
    - Response status code
    - Request duration
    - Authentication status
    """
    
    async def dispatch(self, request: Request, call_next):
        """Log request and response."""
        start_time = time.time()
        
        # Extract client IP (handle proxies)
        client_ip = request.client.host if request.client else "unknown"
        if "x-forwarded-for" in request.headers:
            client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
        
        # Check if authenticated
        is_authenticated = "authorization" in request.headers
        
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            
            # Log request details
            logger.info(
                f"{request.method} {request.url.path} - "
                f"Status: {response.status_code} - "
                f"Duration: {duration_ms:.2f}ms - "
                f"Client: {client_ip} - "
                f"Authenticated: {is_authenticated}"
            )
            
            return response
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"{request.method} {request.url.path} - "
                f"Error: {str(e)} - "
                f"Duration: {duration_ms:.2f}ms - "
                f"Client: {client_ip}"
            )
            raise
