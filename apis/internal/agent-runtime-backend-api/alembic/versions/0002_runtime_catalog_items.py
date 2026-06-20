"""runtime catalog items

Revision ID: 0002_runtime_catalog_items
Revises: 0001_agent_runtime
Create Date: 2026-06-20 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_runtime_catalog_items"
down_revision: Union[str, None] = "0001_agent_runtime"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SCHEMA_NAME = "agent_runtime"


def upgrade() -> None:
    op.create_table(
        "runtime_catalog_items",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("collection", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=180), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_agent_runtime_catalog_tenant_id",
        "runtime_catalog_items",
        ["tenant_id"],
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_agent_runtime_catalog_user_id",
        "runtime_catalog_items",
        ["user_id"],
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_agent_runtime_catalog_collection",
        "runtime_catalog_items",
        ["collection"],
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_agent_runtime_catalog_name",
        "runtime_catalog_items",
        ["name"],
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_agent_runtime_catalog_idempotency_key",
        "runtime_catalog_items",
        ["idempotency_key"],
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_agent_runtime_catalog_created_at",
        "runtime_catalog_items",
        ["created_at"],
        schema=SCHEMA_NAME,
    )
    op.create_unique_constraint(
        "uq_agent_runtime_catalog_scope_idempotency",
        "runtime_catalog_items",
        ["tenant_id", "user_id", "collection", "idempotency_key"],
        schema=SCHEMA_NAME,
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_agent_runtime_catalog_scope_idempotency",
        "runtime_catalog_items",
        schema=SCHEMA_NAME,
        type_="unique",
    )
    op.drop_index("ix_agent_runtime_catalog_created_at", table_name="runtime_catalog_items", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_runtime_catalog_idempotency_key", table_name="runtime_catalog_items", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_runtime_catalog_name", table_name="runtime_catalog_items", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_runtime_catalog_collection", table_name="runtime_catalog_items", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_runtime_catalog_user_id", table_name="runtime_catalog_items", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_runtime_catalog_tenant_id", table_name="runtime_catalog_items", schema=SCHEMA_NAME)
    op.drop_table("runtime_catalog_items", schema=SCHEMA_NAME)
