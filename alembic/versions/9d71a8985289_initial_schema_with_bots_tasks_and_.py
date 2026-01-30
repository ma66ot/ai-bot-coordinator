"""Initial schema with bots, tasks, and workflows

Revision ID: 9d71a8985289
Revises: 
Create Date: 2026-01-30 09:06:50.344897

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d71a8985289'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial schema with bots, workflows, and tasks tables."""
    # Create bots table
    op.create_table(
        'bots',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('capabilities', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='offline'),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bots_name'), 'bots', ['name'])
    op.create_index(op.f('ix_bots_status'), 'bots', ['status'])
    # PostgreSQL-specific GIN index for JSON array searching
    op.create_index(
        'ix_bots_status_capabilities',
        'bots',
        ['status', 'capabilities'],
        postgresql_using='gin',
    )

    # Create workflows table
    op.create_table(
        'workflows',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('task_ids', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_workflows_created_at'), 'workflows', ['created_at'])
    op.create_index(op.f('ix_workflows_name'), 'workflows', ['name'])
    op.create_index(op.f('ix_workflows_status'), 'workflows', ['status'])

    # Create tasks table
    op.create_table(
        'tasks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workflow_id', sa.UUID(), nullable=False),
        sa.Column('bot_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='300'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['bot_id'], ['bots.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_tasks_bot_id'), 'tasks', ['bot_id'])
    op.create_index(op.f('ix_tasks_created_at'), 'tasks', ['created_at'])
    op.create_index(op.f('ix_tasks_status'), 'tasks', ['status'])
    op.create_index(op.f('ix_tasks_workflow_id'), 'tasks', ['workflow_id'])
    # Composite index for common query patterns
    op.create_index('ix_tasks_status_created', 'tasks', ['status', 'created_at'])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index('ix_tasks_status_created', table_name='tasks')
    op.drop_index(op.f('ix_tasks_workflow_id'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_status'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_created_at'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_bot_id'), table_name='tasks')
    op.drop_table('tasks')

    op.drop_index(op.f('ix_workflows_status'), table_name='workflows')
    op.drop_index(op.f('ix_workflows_name'), table_name='workflows')
    op.drop_index(op.f('ix_workflows_created_at'), table_name='workflows')
    op.drop_table('workflows')

    op.drop_index('ix_bots_status_capabilities', table_name='bots')
    op.drop_index(op.f('ix_bots_status'), table_name='bots')
    op.drop_index(op.f('ix_bots_name'), table_name='bots')
    op.drop_table('bots')
