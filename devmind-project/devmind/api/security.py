"""
Security middleware for DevMind API.
Includes JWT auth, API key auth, and rate limiting.
"""

from fastapi import HTTPException, Security, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import os
import logging

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "dev_secret_key_change_in_production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
API_KEY = os.getenv("API_KEY")

# Security schemes
security_bearer = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"]
)


def create_jwt_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    return encoded_jwt


def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Security(security_bearer)) -> dict:
    """Verify JWT token."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authentication token")
    
    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.error(f"JWT verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify API key."""
    if not API_KEY:
        # API key auth disabled
        return "disabled"
    
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return api_key


def optional_auth(
    jwt_credentials: HTTPAuthorizationCredentials = Security(security_bearer),
    api_key: str = Security(api_key_header)
) -> Optional[dict]:
    """
    Optional authentication.
    Accepts either JWT or API key. Returns None if neither provided.
    """
    # Try JWT first
    if jwt_credentials:
        try:
            return verify_jwt_token(jwt_credentials)
        except HTTPException:
            pass
    
    # Try API key
    if api_key and API_KEY:
        try:
            verify_api_key(api_key)
            return {"auth_type": "api_key"}
        except HTTPException:
            pass
    
    return None


def get_rate_limiter() -> Limiter:
    """Get rate limiter instance."""
    return limiter


# Prometheus metrics integration
try:
    from prometheus_client import Counter, Histogram
    
    request_count = Counter(
        'devmind_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status']
    )
    
    request_latency = Histogram(
        'devmind_request_latency_seconds',
        'HTTP request latency',
        ['method', 'endpoint']
    )
    
except ImportError:
    logger.warning("Prometheus client not installed, metrics disabled")
    request_count = None
    request_latency = None
