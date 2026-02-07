"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2026-02-07 15:58:12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial schema."""
    
    # Ingestion jobs table
    op.create_table(
        'ingestion_jobs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('source_path', sa.String(500), nullable=False),
        sa.Column('total_files', sa.Integer, default=0),
        sa.Column('processed_files', sa.Integer, default=0),
        sa.Column('failed_files', sa.Integer, default=0),
        sa.Column('total_chunks', sa.Integer, default=0),
        sa.Column('languages', postgresql.ARRAY(sa.String), default=[]),
        sa.Column('file_types', postgresql.ARRAY(sa.String), default=[]),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('completed_at', sa.DateTime, nullable=True),
    )
    
    # Create index on status for filtering
    op.create_index('idx_ingestion_jobs_status', 'ingestion_jobs', ['status'])
    op.create_index('idx_ingestion_jobs_created', 'ingestion_jobs', ['created_at'])
    
    # File metadata table
    op.create_table(
        'file_metadata',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('file_path', sa.String(1000), nullable=False, unique=True),
        sa.Column('file_hash', sa.String(64), nullable=False),
        sa.Column('language', sa.String(50)),
        sa.Column('file_type', sa.String(50)),
        sa.Column('size_bytes', sa.Integer),
        sa.Column('num_chunks', sa.Integer, default=0),
        sa.Column('last_indexed', sa.DateTime, server_default=sa.func.now()),
        sa.Column('job_id', sa.String(36), sa.ForeignKey('ingestion_jobs.id')),
    )
    
    op.create_index('idx_file_metadata_path', 'file_metadata', ['file_path'])
    op.create_index('idx_file_metadata_hash', 'file_metadata', ['file_hash'])
    op.create_index('idx_file_metadata_language', 'file_metadata', ['language'])
    
    # Search history table
    op.create_table(
        'search_history',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('query', sa.Text, nullable=False),
        sa.Column('num_results', sa.Integer),
        sa.Column('search_type', sa.String(20)),  # 'vector', 'keyword', 'hybrid'
        sa.Column('latency_ms', sa.Float),
        sa.Column('timestamp', sa.DateTime, server_default=sa.func.now()),
    )
    
    op.create_index('idx_search_history_timestamp', 'search_history', ['timestamp'])
    
    # Chat sessions table
    op.create_table(
        'chat_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Chat messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.String(36), sa.ForeignKey('chat_sessions.id')),
        sa.Column('role', sa.String(20), nullable=False),  # 'user', 'assistant'
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('llm_provider', sa.String(50)),
        sa.Column('num_citations', sa.Integer, default=0),
        sa.Column('latency_ms', sa.Float),
        sa.Column('timestamp', sa.DateTime, server_default=sa.func.now()),
    )
    
    op.create_index('idx_chat_messages_session', 'chat_messages', ['session_id'])
    op.create_index('idx_chat_messages_timestamp', 'chat_messages', ['timestamp'])
    
    # System metrics table
    op.create_table(
        'system_metrics',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('metric_value', sa.Float, nullable=False),
        sa.Column('labels', postgresql.JSONB),
        sa.Column('timestamp', sa.DateTime, server_default=sa.func.now()),
    )
    
    op.create_index('idx_system_metrics_name', 'system_metrics', ['metric_name'])
    op.create_index('idx_system_metrics_timestamp', 'system_metrics', ['timestamp'])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('system_metrics')
    op.drop_table('chat_messages')
    op.drop_table('chat_sessions')
    op.drop_table('search_history')
    op.drop_table('file_metadata')
    op.drop_table('ingestion_jobs')
