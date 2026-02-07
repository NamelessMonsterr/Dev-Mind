"""
FastAPI dependencies for workspace permissions.

Provides dependency injection for workspace access control.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from devmind.workspaces.service import WorkspaceService
from devmind.auth.models import User
from devmind.auth.dependencies import get_current_user
from devmind.core.database import get_db


async def get_workspace_service(db: Session = Depends(get_db)) -> WorkspaceService:
    """
    Get workspace service dependency.
    
    Args:
        db: Database session
        
    Returns:
        WorkspaceService instance
    """
    return WorkspaceService(db)


async def verify_workspace_access(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service)
) -> uuid.UUID:
    """
    Verify user has access to workspace.
    
    Args:
        workspace_id: Workspace ID
        current_user: Current authenticated user
        workspace_service: Workspace service
        
    Returns:
        Workspace ID if access granted
        
    Raises:
        HTTPException: If access denied
    """
    if not workspace_service.can_access_workspace(current_user.id, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this workspace"
        )
    
    return workspace_id


async def verify_workspace_management(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service)
) -> uuid.UUID:
    """
    Verify user can manage workspace.
    
    Args:
        workspace_id: Workspace ID
        current_user: Current authenticated user
        workspace_service: Workspace service
        
    Returns:
        Workspace ID if permission granted
        
    Raises:
        HTTPException: If permission denied
    """
    if not workspace_service.can_manage_workspace(current_user.id, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage this workspace"
        )
    
    return workspace_id
