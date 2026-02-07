"""
Rate limiting utilities for DevMind API.

Implements rate limiting to prevent abuse and brute force attacks.
"""

from fastapi import HTTPException, Request, status
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple in-memory rate limiter.
    
    For production, use Redis-backed rate limiting with slowapi or similar.
    """
    
    def __init__(self):
        """Initialize rate limiter."""
        self.requests = defaultdict(list)
        self.cleanup_interval = 60  # Clean up old entries every 60 seconds
        asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self):
        """Periodically clean up old rate limit entries."""
        while True:
            await asyncio.sleep(self.cleanup_interval)
            now = datetime.utcnow()
            keys_to_delete = []
            
            for key, timestamps in self.requests.items():
                # Remove timestamps older than 1 hour
                cutoff = now - timedelta(hours=1)
                self.requests[key] = [ts for ts in timestamps if ts > cutoff]
                
                # Mark empty keys for deletion
                if not self.requests[key]:
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del self.requests[key]
    
    def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> bool:
        """
        Check if request is within rate limit.
        
        Args:
            key: Unique identifier (e.g., IP address or user ID)
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            True if within limit, False if exceeded
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)
        
        # Get requests within window
        recent_requests = [ts for ts in self.requests[key] if ts > cutoff]
        
        if len(recent_requests) >= max_requests:
            return False
        
        # Add current request
        recent_requests.append(now)
        self.requests[key] = recent_requests
        
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


def get_client_ip(request: Request) -> str:
    """
    Get client IP address, handling proxies.
    
    Args:
        request: FastAPI request
        
    Returns:
        Client IP address
    """
    # Check X-Forwarded-For header (proxy)
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"].split(",")[0].strip()
    
    # Check X-Real-IP header
    if "x-real-ip" in request.headers:
        return request.headers["x-real-ip"]
    
    # Fallback to direct connection
    return request.client.host if request.client else "unknown"


async def rate_limit_check(
    request: Request,
    max_requests: int,
    window_seconds: int,
    key_prefix: str = "ip"
):
    """
    Rate limit dependency for FastAPI endpoints.
    
    Args:
        request: FastAPI request
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds
        key_prefix: Prefix for rate limit key
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    client_ip = get_client_ip(request)
    key = f"{key_prefix}:{client_ip}"
    
    if not rate_limiter.check_rate_limit(key, max_requests, window_seconds):
        logger.warning(f"Rate limit exceeded for {key}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Max {max_requests} requests per {window_seconds} seconds.",
            headers={"Retry-After": str(window_seconds)}
        )


# Predefined rate limit dependencies
async def rate_limit_login(request: Request):
    """Rate limit for login endpoint: 5 requests per minute."""
    await rate_limit_check(request, max_requests=5, window_seconds=60, key_prefix="login")


async def rate_limit_register(request: Request):
    """Rate limit for register endpoint: 3 requests per hour."""
    await rate_limit_check(request, max_requests=3, window_seconds=3600, key_prefix="register")


async def rate_limit_refresh(request: Request):
    """Rate limit for token refresh: 10 requests per minute."""
    await rate_limit_check(request, max_requests=10, window_seconds=60, key_prefix="refresh")


async def rate_limit_search(request: Request):
    """Rate limit for search endpoint: 30 requests per minute."""
    await rate_limit_check(request, max_requests=30, window_seconds=60, key_prefix="search")


async def rate_limit_ingest(request: Request):
    """Rate limit for ingest endpoint: 5 requests per hour."""
    await rate_limit_check(request, max_requests=5, window_seconds=3600, key_prefix="ingest")
