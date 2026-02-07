"""
Workspace service.

Business logic for workspace management and permissions.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import uuid
import logging

from devmind.workspaces.models import Workspace, WorkspaceMember, WorkspaceRole
from devmind.workspaces.schemas import WorkspaceCreateRequest, WorkspaceUpdateRequest
from devmind.auth.models import User

logger = logging.getLogger(__name__)


class WorkspaceServiceError(Exception):
    """Base exception for workspace errors."""
    pass


class WorkspaceNotFoundError(WorkspaceServiceError):
    """Workspace not found."""
    pass


class WorkspaceSlugExistsError(WorkspaceServiceError):
    """Workspace slug already exists."""
    pass


class PermissionDeniedError(WorkspaceServiceError):
    """User doesn't have permission."""
    pass


class WorkspaceService:
    """
    Workspace service for managing multi-tenant workspaces.
    """
    
    def __init__(self, db: Session):
        """Initialize workspace service."""
        self.db = db
    
    def create_workspace(self, user_id: uuid.UUID, request: WorkspaceCreateRequest) -> Workspace:
        """
        Create a new workspace.
        
        Args:
            user_id: User creating the workspace
            request: Workspace creation request
            
        Returns:
            Created workspace
            
        Raises:
            WorkspaceSlugExistsError: If slug already exists
        """
        workspace = Workspace(
            id=uuid.uuid4(),
            name=request.name,
            slug=request.slug.lower(),
            description=request.description,
            owner_id=user_id
        )
        
        try:
            self.db.add(workspace)
            self.db.flush()  # Get workspace ID
            
            # Add owner as member
            member = WorkspaceMember(
                workspace_id=workspace.id,
                user_id=user_id,
                role=WorkspaceRole.OWNER
            )
            self.db.add(member)
            
            self.db.commit()
            self.db.refresh(workspace)
            
            logger.info(f"Workspace created: {workspace.slug} by user {user_id}")
            return workspace
        except IntegrityError:
            self.db.rollback()
            raise WorkspaceSlugExistsError(f"Workspace slug '{request.slug}' already exists")
    
    def get_user_workspaces(self, user_id: uuid.UUID) -> List[Workspace]:
        """
        Get all workspaces where user is a member.
        
        Args:
            user_id: User ID
            
        Returns:
            List of workspaces
        """
        return self.db.query(Workspace).join(WorkspaceMember).filter(
            WorkspaceMember.user_id == user_id
        ).all()
    
    def get_workspace(self, workspace_id: uuid.UUID) -> Optional[Workspace]:
        """
        Get workspace by ID.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            Workspace or None
        """
        return self.db.query(Workspace).filter(Workspace.id == workspace_id).first()
    
    def update_workspace(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        request: WorkspaceUpdateRequest
    ) -> Workspace:
        """
        Update workspace.
        
        Args:
            workspace_id: Workspace ID
            user_id: User making the update
            request: Update request
            
        Returns:
            Updated workspace
            
        Raises:
            WorkspaceNotFoundError: If workspace not found
            PermissionDeniedError: If user doesn't have permission
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError("Workspace not found")
        
        # Check permission
        if not self.can_manage_workspace(user_id, workspace_id):
            raise PermissionDeniedError("You don't have permission to update this workspace")
        
        # Update fields
        if request.name:
            workspace.name = request.name
        if request.description is not None:
            workspace.description = request.description
        
        self.db.commit()
        self.db.refresh(workspace)
        
        return workspace
    
    def delete_workspace(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        Delete workspace.
        
        Args:
            workspace_id: Workspace ID
            user_id: User deleting the workspace
            
        Raises:
            WorkspaceNotFoundError: If workspace not found
            PermissionDeniedError: If user doesn't have permission
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError("Workspace not found")
        
        # Only owner can delete
        if workspace.owner_id != user_id:
            raise PermissionDeniedError("Only the owner can delete this workspace")
        
        self.db.delete(workspace)
        self.db.commit()
        
        logger.info(f"Workspace deleted: {workspace.slug}")
    
    def add_member(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        new_user_id: uuid.UUID,
        role: WorkspaceRole = WorkspaceRole.MEMBER
    ) -> WorkspaceMember:
        """
        Add member to workspace.
        
        Args:
            workspace_id: Workspace ID
            user_id: User adding the member (must have permission)
            new_user_id: User to add
            role: Role to assign
            
        Returns:
            Created workspace member
            
        Raises:
            WorkspaceNotFoundError: If workspace not found
            PermissionDeniedError: If user doesn't have permission
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError("Workspace not found")
        
        # Check permission
        member = self.get_member(workspace_id, user_id)
        if not member or not member.can_manage_members:
            raise PermissionDeniedError("You don't have permission to add members")
        
        # Create new member
        new_member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=new_user_id,
            role=role
        )
        
        try:
            self.db.add(new_member)
            self.db.commit()
            self.db.refresh(new_member)
            
            logger.info(f"Member added to workspace {workspace_id}: {new_user_id}")
            return new_member
        except IntegrityError:
            self.db.rollback()
            raise WorkspaceServiceError("User is already a member of this workspace")
    
    def remove_member(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        member_user_id: uuid.UUID
    ) -> None:
        """
        Remove member from workspace.
        
        Args:
            workspace_id: Workspace ID
            user_id: User removing the member
            member_user_id: User to remove
            
        Raises:
            PermissionDeniedError: If user doesn't have permission
        """
        # Check permission
        acting_member = self.get_member(workspace_id, user_id)
        if not acting_member or not acting_member.can_manage_members:
            raise PermissionDeniedError("You don't have permission to remove members")
        
        # Cannot remove owner
        workspace = self.get_workspace(workspace_id)
        if workspace and workspace.owner_id == member_user_id:
            raise PermissionDeniedError("Cannot remove workspace owner")
        
        # Remove member
        member = self.get_member(workspace_id, member_user_id)
        if member:
            self.db.delete(member)
            self.db.commit()
            logger.info(f"Member removed from workspace {workspace_id}: {member_user_id}")
    
    def get_member(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> Optional[WorkspaceMember]:
        """
        Get workspace member.
        
        Args:
            workspace_id: Workspace ID
            user_id: User ID
            
        Returns:
            Workspace member or None
        """
        return self.db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id
        ).first()
    
    def can_access_workspace(self, user_id: uuid.UUID, workspace_id: uuid.UUID) -> bool:
        """
        Check if user has access to workspace.
        
        Args:
            user_id: User ID
            workspace_id: Workspace ID
            
        Returns:
            True if user has access
        """
        return self.get_member(workspace_id, user_id) is not None
    
    def can_manage_workspace(self, user_id: uuid.UUID, workspace_id: uuid.UUID) -> bool:
        """
        Check if user can manage workspace settings.
        
        Args:
            user_id: User ID
            workspace_id: Workspace ID
            
        Returns:
            True if user can manage
        """
        member = self.get_member(workspace_id, user_id)
        return member is not None and member.role in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN)
