"""
Pydantic schemas for authentication.

Request and response models for auth endpoints.
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from devmind.auth.models import UserRole


class UserRegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100, pattern="^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=12)
    full_name: Optional[str] = Field(None, max_length=255)
    
    @validator("username")
    def username_must_not_be_reserved(cls, v):
        """Prevent reserved usernames."""
        reserved = {"admin", "root", "system", "devmind", "api"}
        if v.lower() in reserved:
            raise ValueError("Username is reserved")
        return v


class UserLoginRequest(BaseModel):
    """User login request."""
    username_or_email: str
    password: str


class UserResponse(BaseModel):
    """User response model (excludes sensitive data)."""
    id: str
    email: str
    username: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    is_email_verified: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Authentication token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Password change request."""
    current_password: str
    new_password: str = Field(..., min_length=12)


class ForgotPasswordRequest(BaseModel):
    """Password reset request."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Password reset with token."""
    token: str
    new_password: str = Field(..., min_length=12)
