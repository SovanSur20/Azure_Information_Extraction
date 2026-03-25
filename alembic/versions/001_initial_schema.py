"""Initial schema for logging tables

Revision ID: 001
Revises: 
Create Date: 2024-03-25 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mssql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'pipeline_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.String(255), nullable=False),
        sa.Column('document_name', sa.String(500), nullable=False),
        sa.Column('stage', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', mssql.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_document_stage', 'pipeline_logs', ['document_id', 'stage'])
    op.create_index('idx_status_timestamp', 'pipeline_logs', ['status', 'timestamp'])
    op.create_index('ix_pipeline_logs_document_id', 'pipeline_logs', ['document_id'])
    op.create_index('ix_pipeline_logs_stage', 'pipeline_logs', ['stage'])
    op.create_index('ix_pipeline_logs_status', 'pipeline_logs', ['status'])
    op.create_index('ix_pipeline_logs_timestamp', 'pipeline_logs', ['timestamp'])

    op.create_table(
        'chunk_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.String(255), nullable=False),
        sa.Column('chunk_id', sa.String(255), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('chunk_type', sa.String(50), nullable=False),
        sa.Column('extraction_confidence', sa.Float(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', mssql.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_document_chunk', 'chunk_logs', ['document_id', 'chunk_id'])
    op.create_index('ix_chunk_logs_chunk_id', 'chunk_logs', ['chunk_id'])
    op.create_index('ix_chunk_logs_document_id', 'chunk_logs', ['document_id'])

    op.create_table(
        'field_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.String(255), nullable=False),
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('field_value', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('source_chunks', mssql.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('validation_status', sa.String(20), nullable=True),
        sa.Column('metadata', mssql.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_confidence', 'field_logs', ['confidence'])
    op.create_index('idx_document_field', 'field_logs', ['document_id', 'field_name'])
    op.create_index('ix_field_logs_document_id', 'field_logs', ['document_id'])
    op.create_index('ix_field_logs_field_name', 'field_logs', ['field_name'])

    op.create_table(
        'retry_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.String(255), nullable=False),
        sa.Column('stage', sa.String(50), nullable=False),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('success', sa.String(20), nullable=True),
        sa.Column('metadata', mssql.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_retry_logs_document_id', 'retry_logs', ['document_id'])

    op.create_table(
        'cost_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.String(255), nullable=False),
        sa.Column('service', sa.String(50), nullable=False),
        sa.Column('operation', sa.String(100), nullable=False),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('pages_processed', sa.Integer(), nullable=True),
        sa.Column('queries_executed', sa.Integer(), nullable=True),
        sa.Column('estimated_cost_usd', sa.Float(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('metadata', mssql.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_cost_logs_document_id', 'cost_logs', ['document_id'])
    op.create_index('ix_cost_logs_service', 'cost_logs', ['service'])
    op.create_index('ix_cost_logs_timestamp', 'cost_logs', ['timestamp'])

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.String(255), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('user_email', sa.String(255), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('template_version', sa.String(50), nullable=True),
        sa.Column('metadata', mssql.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_document_id', 'audit_logs', ['document_id'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])


def downgrade() -> None:
    op.drop_index('ix_audit_logs_timestamp', 'audit_logs')
    op.drop_index('ix_audit_logs_document_id', 'audit_logs')
    op.drop_index('ix_audit_logs_action', 'audit_logs')
    op.drop_table('audit_logs')
    
    op.drop_index('ix_cost_logs_timestamp', 'cost_logs')
    op.drop_index('ix_cost_logs_service', 'cost_logs')
    op.drop_index('ix_cost_logs_document_id', 'cost_logs')
    op.drop_table('cost_logs')
    
    op.drop_index('ix_retry_logs_document_id', 'retry_logs')
    op.drop_table('retry_logs')
    
    op.drop_index('ix_field_logs_field_name', 'field_logs')
    op.drop_index('ix_field_logs_document_id', 'field_logs')
    op.drop_index('idx_document_field', 'field_logs')
    op.drop_index('idx_confidence', 'field_logs')
    op.drop_table('field_logs')
    
    op.drop_index('ix_chunk_logs_document_id', 'chunk_logs')
    op.drop_index('ix_chunk_logs_chunk_id', 'chunk_logs')
    op.drop_index('idx_document_chunk', 'chunk_logs')
    op.drop_table('chunk_logs')
    
    op.drop_index('ix_pipeline_logs_timestamp', 'pipeline_logs')
    op.drop_index('ix_pipeline_logs_status', 'pipeline_logs')
    op.drop_index('ix_pipeline_logs_stage', 'pipeline_logs')
    op.drop_index('ix_pipeline_logs_document_id', 'pipeline_logs')
    op.drop_index('idx_status_timestamp', 'pipeline_logs')
    op.drop_index('idx_document_stage', 'pipeline_logs')
    op.drop_table('pipeline_logs')
