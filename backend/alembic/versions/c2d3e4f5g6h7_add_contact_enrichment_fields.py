"""Add contact_profile and seniority to contacts table.

Revision ID: c2d3e4f5g6h7
Revises: b3beb7dfdaf3
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa

revision = "c2d3e4f5g6h7"
down_revision = "62ce284533ec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contacts", sa.Column("seniority", sa.String(50), nullable=True))
    op.add_column("contacts", sa.Column("contact_profile", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("contacts", "contact_profile")
    op.drop_column("contacts", "seniority")
