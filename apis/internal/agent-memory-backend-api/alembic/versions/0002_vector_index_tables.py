"""vector index tables

Revision ID: 0002_vector_index
Revises: 0001_agent_memory
Create Date: 2026-06-19 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_vector_index"
down_revision: Union[str, None] = "0001_agent_memory"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SCHEMA_NAME = "agent_memory"


def upgrade() -> None:
    op.create_table(
        "vector_index_jobs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("collection", sa.String(length=120), nullable=False),
        sa.Column("shadow_collection", sa.String(length=180), nullable=False),
        sa.Column("scope_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("embedding_model", sa.String(length=120), nullable=False),
        sa.Column("embedding_version", sa.String(length=80), nullable=False),
        sa.Column("source_ref", sa.String(length=512), nullable=True),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("rollback_of_job_id", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key", sa.String(length=180), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_agent_memory_vector_jobs_tenant_id", "vector_index_jobs", ["tenant_id"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_vector_jobs_user_id", "vector_index_jobs", ["user_id"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_vector_jobs_collection", "vector_index_jobs", ["collection"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_vector_jobs_scope_type", "vector_index_jobs", ["scope_type"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_vector_jobs_status", "vector_index_jobs", ["status"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_vector_jobs_trace_id", "vector_index_jobs", ["trace_id"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_vector_jobs_requested_at", "vector_index_jobs", ["requested_at"], schema=SCHEMA_NAME)
    op.create_index(
        "ix_agent_memory_vector_jobs_rollback_of_job_id",
        "vector_index_jobs",
        ["rollback_of_job_id"],
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_agent_memory_vector_jobs_idempotency_key",
        "vector_index_jobs",
        ["idempotency_key"],
        schema=SCHEMA_NAME,
    )
    op.create_unique_constraint(
        "uq_agent_memory_vector_jobs_scope_idempotency",
        "vector_index_jobs",
        ["tenant_id", "user_id", "idempotency_key"],
        schema=SCHEMA_NAME,
    )

    op.create_table(
        "vector_index_records",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.String(length=40), nullable=False),
        sa.Column("source_table", sa.String(length=80), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("collection", sa.String(length=120), nullable=False),
        sa.Column("vector_id", sa.String(length=120), nullable=False),
        sa.Column("index_status", sa.String(length=40), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("embedding_model", sa.String(length=120), nullable=False),
        sa.Column("embedding_version", sa.String(length=80), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_agent_memory_vector_records_tenant_id", "vector_index_records", ["tenant_id"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_vector_records_scope_type", "vector_index_records", ["scope_type"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_vector_records_source_id", "vector_index_records", ["source_id"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_vector_records_collection", "vector_index_records", ["collection"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_vector_records_vector_id", "vector_index_records", ["vector_id"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_vector_records_index_status", "vector_index_records", ["index_status"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_vector_records_trace_id", "vector_index_records", ["trace_id"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_vector_records_created_at", "vector_index_records", ["created_at"], schema=SCHEMA_NAME)


def downgrade() -> None:
    op.drop_index("ix_agent_memory_vector_records_created_at", table_name="vector_index_records", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_vector_records_trace_id", table_name="vector_index_records", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_vector_records_index_status", table_name="vector_index_records", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_vector_records_vector_id", table_name="vector_index_records", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_vector_records_collection", table_name="vector_index_records", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_vector_records_source_id", table_name="vector_index_records", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_vector_records_scope_type", table_name="vector_index_records", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_vector_records_tenant_id", table_name="vector_index_records", schema=SCHEMA_NAME)
    op.drop_table("vector_index_records", schema=SCHEMA_NAME)
    op.drop_constraint(
        "uq_agent_memory_vector_jobs_scope_idempotency",
        "vector_index_jobs",
        schema=SCHEMA_NAME,
        type_="unique",
    )
    op.drop_index("ix_agent_memory_vector_jobs_idempotency_key", table_name="vector_index_jobs", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_vector_jobs_rollback_of_job_id", table_name="vector_index_jobs", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_vector_jobs_requested_at", table_name="vector_index_jobs", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_vector_jobs_trace_id", table_name="vector_index_jobs", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_vector_jobs_status", table_name="vector_index_jobs", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_vector_jobs_scope_type", table_name="vector_index_jobs", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_vector_jobs_collection", table_name="vector_index_jobs", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_vector_jobs_user_id", table_name="vector_index_jobs", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_vector_jobs_tenant_id", table_name="vector_index_jobs", schema=SCHEMA_NAME)
    op.drop_table("vector_index_jobs", schema=SCHEMA_NAME)
