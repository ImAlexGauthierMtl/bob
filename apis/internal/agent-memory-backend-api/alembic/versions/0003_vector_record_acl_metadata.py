"""vector record acl metadata

Revision ID: 0003_vector_acl
Revises: 0002_vector_index
Create Date: 2026-06-19 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_vector_acl"
down_revision: Union[str, None] = "0002_vector_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SCHEMA_NAME = "agent_memory"


def upgrade() -> None:
    op.add_column("vector_index_records", sa.Column("user_id", sa.String(length=64), nullable=True), schema=SCHEMA_NAME)
    op.add_column("vector_index_records", sa.Column("scope_key", sa.String(length=80), nullable=True), schema=SCHEMA_NAME)
    op.add_column(
        "vector_index_records",
        sa.Column("shadow_collection", sa.String(length=180), nullable=True),
        schema=SCHEMA_NAME,
    )
    op.add_column("vector_index_records", sa.Column("job_id", sa.String(length=64), nullable=True), schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_vector_records_user_id", "vector_index_records", ["user_id"], schema=SCHEMA_NAME)
    op.create_index("ix_agent_memory_vector_records_scope_key", "vector_index_records", ["scope_key"], schema=SCHEMA_NAME)
    op.create_index(
        "ix_agent_memory_vector_records_shadow_collection",
        "vector_index_records",
        ["shadow_collection"],
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_agent_memory_vector_records_job_id", "vector_index_records", ["job_id"], schema=SCHEMA_NAME)
    op.create_unique_constraint(
        "uq_agent_memory_vector_records_job_source",
        "vector_index_records",
        ["tenant_id", "job_id", "source_id"],
        schema=SCHEMA_NAME,
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_agent_memory_vector_records_job_source",
        "vector_index_records",
        schema=SCHEMA_NAME,
        type_="unique",
    )
    op.drop_index("ix_agent_memory_vector_records_job_id", table_name="vector_index_records", schema=SCHEMA_NAME)
    op.drop_index(
        "ix_agent_memory_vector_records_shadow_collection",
        table_name="vector_index_records",
        schema=SCHEMA_NAME,
    )
    op.drop_index("ix_agent_memory_vector_records_scope_key", table_name="vector_index_records", schema=SCHEMA_NAME)
    op.drop_index("ix_agent_memory_vector_records_user_id", table_name="vector_index_records", schema=SCHEMA_NAME)
    op.drop_column("vector_index_records", "job_id", schema=SCHEMA_NAME)
    op.drop_column("vector_index_records", "shadow_collection", schema=SCHEMA_NAME)
    op.drop_column("vector_index_records", "scope_key", schema=SCHEMA_NAME)
    op.drop_column("vector_index_records", "user_id", schema=SCHEMA_NAME)
