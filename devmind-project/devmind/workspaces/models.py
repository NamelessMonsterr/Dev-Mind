"""
Workspace models for multi-tenancy.

Enables teams to organize indices and jobs into isolated workspaces.
"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, UniqueConstraint, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from devmind.core.database import Base


class WorkspaceRole(str, enum.Enum):
    """Workspace member roles."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Workspace(Base):
    """
    Workspace model for organizing projects and teams.
    
    Each workspace contains its own indices, jobs, and members.
    """
    __tablename__ = "workspaces"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Ownership
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    members = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Workspace {self.name} ({self.slug})>"
    
    @property
    def member_count(self) -> int:
        """Get number of members in workspace."""
        return len(self.members)


class WorkspaceMember(Base):
    """
    Workspace membership with role-based permissions.
    
    Links users to workspaces with specific roles.
    """
    __tablename__ = "workspace_members"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Role
    role = Column(SQLEnum(WorkspaceRole), default=WorkspaceRole.MEMBER, nullable=False)
    
    # Timestamps
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('workspace_id', 'user_id', name='uq_workspace_user'),
    )
    
    def __repr__(self):
        return f"<WorkspaceMember user={self.user_id} workspace={self.workspace_id} role={self.role.value}>"
    
    @property
    def can_manage_members(self) -> bool:
        """Check if member can manage other members."""
        return self.role in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN)
    
    @property
    def can_delete_workspace(self) -> bool:
        """Check if member can delete workspace."""
        return self.role == WorkspaceRole.OWNER
