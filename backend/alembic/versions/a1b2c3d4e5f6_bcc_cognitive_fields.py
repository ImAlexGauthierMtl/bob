"""Add cognitive fields to BCC intents and intent_tasks.

Revision ID: a1b2c3d4e5f6
Revises: dd9035e68051
Create Date: 2026-03-09
"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "dd9035e68051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bcc_intents", sa.Column("workflow_key", sa.String(100), nullable=True))
    op.add_column("bcc_intents", sa.Column("pipeline_key", sa.String(100), nullable=True))
    op.add_column("bcc_intent_tasks", sa.Column("tool_name", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("bcc_intent_tasks", "tool_name")
    op.drop_column("bcc_intents", "pipeline_key")
    op.drop_column("bcc_intents", "workflow_key")
