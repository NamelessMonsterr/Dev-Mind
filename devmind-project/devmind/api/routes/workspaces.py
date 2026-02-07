"""
Workspace API routes.

Endpoints for workspace management and member operations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from devmind.workspaces import schemas
from devmind.workspaces.service import (
    WorkspaceService,
    WorkspaceNotFoundError,
    WorkspaceSlugExistsError,
    PermissionDeniedError
)
from devmind.workspaces.dependencies import (
    get_workspace_service,
    verify_workspace_access,
    verify_workspace_management
)
from devmind.auth.models import User
from devmind.auth.dependencies import get_current_user
from devmind.core.database import get_db
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=schemas.WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: schemas.WorkspaceCreateRequest,
    current_user: User = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service)
):
    """
    Create a new workspace.
    
    Current user becomes the owner.
    """
    try:
        workspace = workspace_service.create_workspace(current_user.id, request)
        return schemas.WorkspaceResponse.from_orm(workspace)
    except WorkspaceSlugExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.get("", response_model=List[schemas.WorkspaceResponse])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service)
):
    """
    List all workspaces where current user is a member.
    """
    workspaces = workspace_service.get_user_workspaces(current_user.id)
    return [schemas.WorkspaceResponse.from_orm(w) for w in workspaces]


@router.get("/{workspace_id}", response_model=schemas.WorkspaceDetailResponse)
async def get_workspace(
    workspace_id: uuid.UUID = Depends(verify_workspace_access),
    workspace_service: WorkspaceService = Depends(get_workspace_service)
):
    """
    Get workspace details including members.
    """
    workspace = workspace_service.get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Build response with members
    members = []
    for member in workspace.members:
        members.append(schemas.WorkspaceMemberResponse(
            id=str(member.id),
            user_id=str(member.user_id),
            username=member.user.username,
            email=member.user.email,
            role=member.role,
            joined_at=member.joined_at
        ))
    
    response_data = schemas.WorkspaceResponse.from_orm(workspace).dict()
    response_data['members'] = members
    
    return schemas.WorkspaceDetailResponse(**response_data)


@router.put("/{workspace_id}", response_model=schemas.WorkspaceResponse)
async def update_workspace(
    request: schemas.WorkspaceUpdateRequest,
    workspace_id: uuid.UUID = Depends(verify_workspace_management),
    current_user: User = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service)
):
    """
    Update workspace settings.
    
    Requires admin or owner role.
    """
    try:
        workspace = workspace_service.update_workspace(workspace_id, current_user.id, request)
        return schemas.WorkspaceResponse.from_orm(workspace)
    except WorkspaceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service)
):
    """
    Delete workspace.
    
    Only the owner can delete a workspace.
    """
    try:
        workspace_service.delete_workspace(workspace_id, current_user.id)
        return None
    except WorkspaceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.post("/{workspace_id}/members", response_model=schemas.WorkspaceMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    workspace_id: uuid.UUID,
    request: schemas.WorkspaceInviteRequest,
    current_user: User = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    db: Session = Depends(get_db)
):
    """
    Add a member to the workspace.
    
    Requires admin or owner role.
    """
    # Find user by email
    from devmind.auth.models import User as UserModel
    user = db.query(UserModel).filter(UserModel.email == request.user_email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {request.user_email} not found"
        )
    
    try:
        member = workspace_service.add_member(workspace_id, current_user.id, user.id, request.role)
        
        return schemas.WorkspaceMemberResponse(
            id=str(member.id),
            user_id=str(member.user_id),
            username=member.user.username,
            email=member.user.email,
            role=member.role,
            joined_at=member.joined_at
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service)
):
    """
    Remove a member from the workspace.
    
    Requires admin or owner role.
    """
    try:
        workspace_service.remove_member(workspace_id, current_user.id, user_id)
        return None
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
