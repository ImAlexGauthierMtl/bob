"""agent memory tables

Revision ID: 0001_agent_memory
Revises:
Create Date: 2026-06-19 00:00:00.000000

"""

from typing import Sequence, Union
import os

from alembic import op
import sqlalchemy as sa


revision: str = "0001_agent_memory"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SCHEMA_NAME = "agent_memory"


def _quoted_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _grant_schema_privileges() -> None:
    db_user = os.environ.get("DB_USERNAME")
    if not db_user:
        return
    schema = _quoted_identifier(SCHEMA_NAME)
    user = _quoted_identifier(db_user)
    op.execute(f"GRANT USAGE, CREATE ON SCHEMA {schema} TO {user}")
    op.execute(f"GRANT ALL ON ALL TABLES IN SCHEMA {schema} TO {user}")
    op.execute(f"GRANT ALL ON ALL SEQUENCES IN SCHEMA {schema} TO {user}")
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT ALL ON TABLES TO {user}")
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT ALL ON SEQUENCES TO {user}")


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {_quoted_identifier(SCHEMA_NAME)}")
    _grant_schema_privileges()
    op.create_table(
        "memory_entries",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.String(length=40), nullable=False),
        sa.Column("memory_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_ref", sa.String(length=512), nullable=False),
        sa.Column("sensitivity", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=180), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_agent_memory_entries_tenant_id", "memory_entries", ["tenant_id"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_entries_user_id", "memory_entries", ["user_id"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_entries_scope_type", "memory_entries", ["scope_type"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_entries_memory_type", "memory_entries", ["memory_type"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_entries_sensitivity", "memory_entries", ["sensitivity"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_entries_status", "memory_entries", ["status"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_entries_trace_id", "memory_entries", ["trace_id"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_entries_created_at", "memory_entries", ["created_at"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_entries_expires_at", "memory_entries", ["expires_at"], schema=SCHEMA_NAME)
    op.create_index(
        "ix_agent_memory_entries_idempotency_key",
        "memory_entries",
        ["idempotency_key"],
        schema=SCHEMA_NAME,
    )
    op.create_unique_constraint(
        "uq_agent_memory_entries_scope_idempotency",
        "memory_entries",
        ["tenant_id", "user_id", "scope_type", "idempotency_key"],
        schema=SCHEMA_NAME,
    )

    op.create_table(
        "memory_journal",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("request_summary", sa.String(length=500), nullable=False),
        sa.Column("actions_taken", sa.Text(), nullable=False),
        sa.Column("sources_checked", sa.Text(), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("next_step", sa.String(length=500), nullable=False),
        sa.Column("sensitivity", sa.String(length=40), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=180), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_agent_memory_journal_tenant_id", "memory_journal", ["tenant_id"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_journal_user_id", "memory_journal", ["user_id"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_journal_sensitivity", "memory_journal", ["sensitivity"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_journal_trace_id", "memory_journal", ["trace_id"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_journal_created_at", "memory_journal", ["created_at"], schema=SCHEMA_NAME)
    op.create_index(
        "ix_agent_memory_journal_idempotency_key",
        "memory_journal",
        ["idempotency_key"],
        schema=SCHEMA_NAME,
    )
    op.create_unique_constraint(
        "uq_agent_memory_journal_scope_idempotency",
        "memory_journal",
        ["tenant_id", "user_id", "idempotency_key"],
        schema=SCHEMA_NAME,
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_agent_memory_journal_scope_idempotency",
        "memory_journal",
        schema=SCHEMA_NAME,
        type_="unique",
    )
    op.drop_index("ix_agent_memory_journal_idempotency_key", table_name="memory_journal", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_journal_created_at", table_name="memory_journal", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_journal_trace_id", table_name="memory_journal", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_journal_sensitivity", table_name="memory_journal", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_journal_user_id", table_name="memory_journal", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_journal_tenant_id", table_name="memory_journal", schema=SCHEMA_NAME)
    op.drop_table("memory_journal", schema=SCHEMA_NAME)
    op.drop_constraint(
        "uq_agent_memory_entries_scope_idempotency",
        "memory_entries",
        schema=SCHEMA_NAME,
        type_="unique",
    )
    op.drop_index("ix_agent_memory_entries_idempotency_key", table_name="memory_entries", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_entries_expires_at", table_name="memory_entries", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_entries_created_at", table_name="memory_entries", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_entries_trace_id", table_name="memory_entries", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_entries_status", table_name="memory_entries", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_entries_sensitivity", table_name="memory_entries", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_entries_memory_type", table_name="memory_entries", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_entries_scope_type", table_name="memory_entries", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_entries_user_id", table_name="memory_entries", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_entries_tenant_id", table_name="memory_entries", schema=SCHEMA_NAME)
    op.drop_table("memory_entries", schema=SCHEMA_NAME)
    op.execute(f"DROP SCHEMA IF EXISTS {_quoted_identifier(SCHEMA_NAME)} CASCADE")
