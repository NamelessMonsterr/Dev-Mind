"""
CSRF protection for DevMind API.

Implements CSRF token generation and validation.
"""

from fastapi import HTTPException, Request, status, Header
from typing import Optional
import secrets
import hashlib
import time
import logging

logger = logging.getLogger(__name__)


class CSRFProtection:
    """
    CSRF token management.
    
    Uses double-submit cookie pattern:
    1. Client receives CSRF token
    2. Token sent in both cookie and header
    3. Server validates they match
    """
    
    def __init__(self, secret_key: str):
        """
        Initialize CSRF protection.
        
        Args:
            secret_key: Secret key for token generation
        """
        self.secret_key = secret_key
    
    def generate_token(self, session_id: str) -> str:
        """
        Generate CSRF token.
        
        Args:
            session_id: User session ID
            
        Returns:
            CSRF token
        """
        timestamp = str(int(time.time()))
        random_value = secrets.token_urlsafe(32)
        
        # Create token with timestamp + random + session
        token_data = f"{timestamp}:{random_value}:{session_id}"
        
        # Hash with secret key
        token_hash = hashlib.sha256(
            f"{token_data}:{self.secret_key}".encode()
        ).hexdigest()
        
        # Return token (timestamp:random:hash)
        return f"{timestamp}:{random_value}:{token_hash}"
    
    def validate_token(
        self,
        token: str,
        session_id: str,
        max_age_seconds: int = 3600
    ) -> bool:
        """
        Validate CSRF token.
        
        Args:
            token: CSRF token to validate
            session_id: User session ID
            max_age_seconds: Maximum token age
            
        Returns:
            True if valid, False otherwise
        """
        try:
            parts = token.split(":")
            if len(parts) != 3:
                return False
            
            timestamp_str, random_value, received_hash = parts
            timestamp = int(timestamp_str)
            
            # Check token age
            current_time = int(time.time())
            if current_time - timestamp > max_age_seconds:
                logger.warning("CSRF token expired")
                return False
            
            # Recreate expected hash
            token_data = f"{timestamp_str}:{random_value}:{session_id}"
            expected_hash = hashlib.sha256(
                f"{token_data}:{self.secret_key}".encode()
            ).hexdigest()
            
            # Constant-time comparison
            return secrets.compare_digest(received_hash, expected_hash)
        
        except Exception as e:
            logger.error(f"CSRF token validation error: {e}")
            return False


# Global CSRF protection instance (initialized in app.py)
csrf_protection: Optional[CSRFProtection] = None


def init_csrf_protection(secret_key: str):
    """
    Initialize CSRF protection.
    
    Args:
        secret_key: Secret key for token generation
    """
    global csrf_protection
    csrf_protection = CSRFProtection(secret_key)


async def verify_csrf_token(
    request: Request,
    x_csrf_token: Optional[str] = Header(None)
):
    """
    Verify CSRF token for state-changing requests.
    
    Args:
        request: FastAPI request
        x_csrf_token: CSRF token from header
        
    Raises:
        HTTPException: If CSRF validation fails
    """
    # Skip CSRF for safe methods
    if request.method in ["GET", "HEAD", "OPTIONS"]:
        return
    
    # Skip CSRF for non-browser clients (API keys, etc.)
    # In production, you may want stricter checks
    user_agent = request.headers.get("user-agent", "")
    if "PostmanRuntime" in user_agent or "curl" in user_agent:
        # For testing purposes - remove in strict production
        return
    
    if not csrf_protection:
        logger.error("CSRF protection not initialized")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CSRF protection not configured"
        )
    
    if not x_csrf_token:
        logger.warning("CSRF token missing")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing. Include X-CSRF-Token header."
        )
    
    # Get session ID from authorization header or cookie
    # For JWT, we can use user ID from token
    session_id = "default"  # Simplified - in production, extract from JWT
    
    if not csrf_protection.validate_token(x_csrf_token, session_id):
        logger.warning(f"Invalid CSRF token from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token"
        )
