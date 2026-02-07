"""
Pydantic schemas for workspaces.

Request and response models for workspace endpoints.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from devmind.workspaces.models import WorkspaceRole
import re


class WorkspaceCreateRequest(BaseModel):
    """Workspace creation request."""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=3, max_length=100, pattern="^[a-z0-9-]+$")
    description: Optional[str] = Field(None, max_length=1000)
    
    @validator("slug")
    def slug_must_not_be_reserved(cls, v):
        """Prevent reserved slugs."""
        reserved = {"admin", "api", "new", "settings", "billing"}
        if v.lower() in reserved:
            raise ValueError("Slug is reserved")
        return v.lower()


class WorkspaceUpdateRequest(BaseModel):
    """Workspace update request."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class WorkspaceMemberResponse(BaseModel):
    """Workspace member response."""
    id: str
    user_id: str
    username: str
    email: str
    role: WorkspaceRole
    joined_at: datetime
    
    class Config:
        from_attributes = True


class WorkspaceResponse(BaseModel):
    """Workspace response model."""
    id: str
    name: str
    slug: str
    description: Optional[str]
    owner_id: str
    created_at: datetime
    updated_at: datetime
    member_count: int
    
    class Config:
        from_attributes = True


class WorkspaceDetailResponse(WorkspaceResponse):
    """Detailed workspace response with members."""
    members: List[WorkspaceMemberResponse]


class WorkspaceInviteRequest(BaseModel):
    """Workspace member invitation request."""
    user_email: str
    role: WorkspaceRole = WorkspaceRole.MEMBER


class WorkspaceMemberUpdateRequest(BaseModel):
    """Update workspace member role."""
    role: WorkspaceRole
