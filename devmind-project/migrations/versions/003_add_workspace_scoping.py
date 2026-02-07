"""
Add workspace_id to jobs and sessions

Revision ID: 003_add_workspace_scoping
Revises: 002_add_workspaces
Create Date: 2026-02-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = '003_add_workspace_scoping'
down_revision = '002_add_workspaces'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add workspace_id to existing tables for workspace scoping.
    
    Note: This makes workspace_id nullable initially for backward compatibility.
    In production, you may want to:
    1. Create a default workspace
    2. Migrate existing data to the default workspace
    3. Make workspace_id NOT NULL
    """
    
    # Add workspace_id to ingestion_jobs (if table exists)
    try:
        op.add_column('ingestion_jobs', 
            sa.Column('workspace_id', postgresql.UUID(as_uuid=True), 
                     sa.ForeignKey('workspaces.id', ondelete='CASCADE'), 
                     nullable=True))
        op.create_index('idx_ingestion_jobs_workspace', 'ingestion_jobs', ['workspace_id'])
    except Exception as e:
        print(f"Skipping ingestion_jobs: {e}")
    
    # Add workspace_id to chat_sessions (if table exists)
    try:
        op.add_column('chat_sessions', 
            sa.Column('workspace_id', postgresql.UUID(as_uuid=True), 
                     sa.ForeignKey('workspaces.id', ondelete='CASCADE'), 
                     nullable=True))
        op.create_index('idx_chat_sessions_workspace', 'chat_sessions', ['workspace_id'])
    except Exception as e:
        print(f"Skipping chat_sessions: {e}")


def downgrade():
    """Remove workspace scoping."""
    
    try:
        op.drop_index('idx_chat_sessions_workspace', 'chat_sessions')
        op.drop_column('chat_sessions', 'workspace_id')
    except Exception:
        pass
    
    try:
        op.drop_index('idx_ingestion_jobs_workspace', 'ingestion_jobs')
        op.drop_column('ingestion_jobs', 'workspace_id')
    except Exception:
        pass
