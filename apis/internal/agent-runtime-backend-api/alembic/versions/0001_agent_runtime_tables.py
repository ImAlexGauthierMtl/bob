"""agent runtime tables

Revision ID: 0001_agent_runtime
Revises:
Create Date: 2026-06-19 00:00:00.000000

"""

from typing import Sequence, Union
import os

from alembic import op
import sqlalchemy as sa


revision: str = "0001_agent_runtime"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SCHEMA_NAME = "agent_runtime"


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
        "runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("input_message_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("mode", sa.String(length=60), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("assistant_content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("narration_steps", sa.JSON(), nullable=False),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("artifacts", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=180), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_agent_runtime_runs_tenant_id", "runs", ["tenant_id"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_runtime_runs_user_id", "runs", ["user_id"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_runtime_runs_session_id", "runs", ["session_id"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_runtime_runs_input_message_id", "runs", ["input_message_id"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_runtime_runs_status", "runs", ["status"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_runtime_runs_trace_id", "runs", ["trace_id"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_runtime_runs_idempotency_key", "runs", ["idempotency_key"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_runtime_runs_created_at", "runs", ["created_at"], schema=SCHEMA_NAME)
    op.create_unique_constraint(
        "uq_agent_runtime_runs_scope_idempotency",
        "runs",
        ["tenant_id", "user_id", "idempotency_key"],
        schema=SCHEMA_NAME,
    )

    op.create_table(
        "confirmations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], [f"{SCHEMA_NAME}.runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_agent_runtime_confirmations_run_id", "confirmations", ["run_id"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_runtime_confirmations_tenant_id", "confirmations", ["tenant_id"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_runtime_confirmations_user_id", "confirmations", ["user_id"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_runtime_confirmations_status", "confirmations", ["status"], schema=SCHEMA_NAME)


def downgrade() -> None:
    op.drop_index("ix_agent_runtime_confirmations_status", table_name="confirmations", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_runtime_confirmations_user_id", table_name="confirmations", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_runtime_confirmations_tenant_id", table_name="confirmations", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_runtime_confirmations_run_id", table_name="confirmations", schema=SCHEMA_NAME)
    op.drop_table("confirmations", schema=SCHEMA_NAME)
    op.drop_constraint(
        "uq_agent_runtime_runs_scope_idempotency",
        "runs",
        schema=SCHEMA_NAME,
        type_="unique",
    )
    op.drop_index("ix_agent_runtime_runs_created_at", table_name="runs", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_runtime_runs_idempotency_key", table_name="runs", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_runtime_runs_trace_id", table_name="runs", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_runtime_runs_status", table_name="runs", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_runtime_runs_input_message_id", table_name="runs", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_runtime_runs_session_id", table_name="runs", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_runtime_runs_user_id", table_name="runs", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_runtime_runs_tenant_id", table_name="runs", schema=SCHEMA_NAME)
    op.drop_table("runs", schema=SCHEMA_NAME)
    op.execute(f"DROP SCHEMA IF EXISTS {_quoted_identifier(SCHEMA_NAME)} CASCADE")
