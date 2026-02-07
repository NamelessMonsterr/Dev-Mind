"""
Create workspaces and workspace_members tables

Revision ID: 002_add_workspaces
Revises: 001_add_auth_tables
Create Date: 2026-02-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = '002_add_workspaces'
down_revision = '001_add_auth_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create workspaces table
    op.create_table(
        'workspaces',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    # Create indices for workspaces
    op.create_index('idx_workspaces_slug', 'workspaces', ['slug'])
    op.create_index('idx_workspaces_owner', 'workspaces', ['owner_id'])
    
    # Create workspace_members table
    op.create_table(
        'workspace_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.Enum('owner', 'admin', 'member', 'viewer', name='workspacerole'), nullable=False, server_default='member'),
        sa.Column('joined_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('workspace_id', 'user_id', name='uq_workspace_user'),
    )
    
    # Create indices for workspace_members
    op.create_index('idx_workspace_members_workspace', 'workspace_members', ['workspace_id'])
    op.create_index('idx_workspace_members_user', 'workspace_members', ['user_id'])
    
    # Add workspace_id to ingestion_jobs (if table exists)
    # Note: This is optional based on whether you've already created these tables
    # Uncomment these lines if you have these tables and want to add workspace scoping
    """
    op.add_column('ingestion_jobs', sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=True))
    op.create_index('idx_ingestion_jobs_workspace', 'ingestion_jobs', ['workspace_id'])
    
    op.add_column('chat_sessions', sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=True))
    op.create_index('idx_chat_sessions_workspace', 'chat_sessions', ['workspace_id'])
    """


def downgrade():
    # Drop workspace scoping from other tables (if added)
    """
    op.drop_index('idx_chat_sessions_workspace', 'chat_sessions')
    op.drop_column('chat_sessions', 'workspace_id')
    
    op.drop_index('idx_ingestion_jobs_workspace', 'ingestion_jobs')
    op.drop_column('ingestion_jobs', 'workspace_id')
    """
    
    # Drop workspace_members table
    op.drop_index('idx_workspace_members_user', 'workspace_members')
    op.drop_index('idx_workspace_members_workspace', 'workspace_members')
    op.drop_table('workspace_members')
    
    # Drop workspaces table
    op.drop_index('idx_workspaces_owner', 'workspaces')
    op.drop_index('idx_workspaces_slug', 'workspaces')
    op.drop_table('workspaces')
    
    # Drop enum type
    op.execute('DROP TYPE workspacerole')
