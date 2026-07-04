"""knowledge registry

Revision ID: 0004_knowledge_registry
Revises: 0003_vector_acl
Create Date: 2026-06-20 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_knowledge_registry"
down_revision: Union[str, None] = "0003_vector_acl"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SCHEMA_NAME = "agent_memory"


def upgrade() -> None:
    op.create_table(
        "knowledge_databases",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("milvus_database", sa.String(length=120), nullable=False),
        sa.Column("embedding_provider", sa.String(length=80), nullable=False),
        sa.Column("embedding_model", sa.String(length=160), nullable=False),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=180), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_unique_constraint(
        "uq_agent_memory_knowledge_db_tenant_name",
        "knowledge_databases",
        ["tenant_id", "name"],
        schema=SCHEMA_NAME,
    )
    op.create_unique_constraint(
        "uq_agent_memory_knowledge_db_idempotency",
        "knowledge_databases",
        ["tenant_id", "created_by", "idempotency_key"],
        schema=SCHEMA_NAME,
    )
    for column in ("tenant_id", "name", "status", "created_by", "created_at", "idempotency_key"):
        op.create_index(f"ix_agent_memory_knowledge_db_{column}", "knowledge_databases", [column], schema=SCHEMA_NAME)

    op.create_table(
        "knowledge_collections",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("database_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("theme", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("milvus_collection", sa.String(length=120), nullable=False),
        sa.Column("scope_type", sa.String(length=40), nullable=False),
        sa.Column("source_kind", sa.String(length=80), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=180), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_unique_constraint(
        "uq_agent_memory_knowledge_collection_tenant_name",
        "knowledge_collections",
        ["tenant_id", "name"],
        schema=SCHEMA_NAME,
    )
    op.create_foreign_key(
        "fk_agent_memory_knowledge_collection_database",
        "knowledge_collections",
        "knowledge_databases",
        ["database_id"],
        ["id"],
        source_schema=SCHEMA_NAME,
        referent_schema=SCHEMA_NAME,
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_agent_memory_knowledge_collection_idempotency",
        "knowledge_collections",
        ["tenant_id", "created_by", "idempotency_key"],
        schema=SCHEMA_NAME,
    )
    for column in (
        "tenant_id",
        "database_id",
        "name",
        "theme",
        "status",
        "milvus_collection",
        "scope_type",
        "source_kind",
        "created_by",
        "created_at",
        "idempotency_key",
    ):
        op.create_index(
            f"ix_agent_memory_knowledge_collection_{column}",
            "knowledge_collections",
            [column],
            schema=SCHEMA_NAME,
        )

    op.create_table(
        "knowledge_sources",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("collection_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("pipedream_app", sa.String(length=120), nullable=False),
        sa.Column("pipedream_source_id", sa.String(length=180), nullable=True),
        sa.Column("sync_mode", sa.String(length=80), nullable=False),
        sa.Column("ingestion_strategy", sa.String(length=80), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=180), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_unique_constraint(
        "uq_agent_memory_knowledge_source_idempotency",
        "knowledge_sources",
        ["tenant_id", "created_by", "idempotency_key"],
        schema=SCHEMA_NAME,
    )
    op.create_foreign_key(
        "fk_agent_memory_knowledge_source_collection",
        "knowledge_sources",
        "knowledge_collections",
        ["collection_id"],
        ["id"],
        source_schema=SCHEMA_NAME,
        referent_schema=SCHEMA_NAME,
        ondelete="CASCADE",
    )
    for column in (
        "tenant_id",
        "collection_id",
        "provider",
        "source_type",
        "status",
        "created_by",
        "created_at",
        "idempotency_key",
    ):
        op.create_index(f"ix_agent_memory_knowledge_source_{column}", "knowledge_sources", [column], schema=SCHEMA_NAME)


def downgrade() -> None:
    for column in (
        "idempotency_key",
        "created_at",
        "created_by",
        "status",
        "source_type",
        "provider",
        "collection_id",
        "tenant_id",
    ):
        op.drop_index(f"ix_agent_memory_knowledge_source_{column}", table_name="knowledge_sources", schema=SCHEMA_NAME)
    op.drop_constraint("fk_agent_memory_knowledge_source_collection", "knowledge_sources", schema=SCHEMA_NAME, type_="foreignkey")
    op.drop_constraint("uq_agent_memory_knowledge_source_idempotency", "knowledge_sources", schema=SCHEMA_NAME, type_="unique")
    op.drop_table("knowledge_sources", schema=SCHEMA_NAME)

    for column in (
        "idempotency_key",
        "created_at",
        "created_by",
        "source_kind",
        "scope_type",
        "milvus_collection",
        "status",
        "theme",
        "name",
        "database_id",
        "tenant_id",
    ):
        op.drop_index(f"ix_agent_memory_knowledge_collection_{column}", table_name="knowledge_collections", schema=SCHEMA_NAME)
    op.drop_constraint("fk_agent_memory_knowledge_collection_database", "knowledge_collections", schema=SCHEMA_NAME, type_="foreignkey")
    op.drop_constraint("uq_agent_memory_knowledge_collection_idempotency", "knowledge_collections", schema=SCHEMA_NAME, type_="unique")
    op.drop_constraint("uq_agent_memory_knowledge_collection_tenant_name", "knowledge_collections", schema=SCHEMA_NAME, type_="unique")
    op.drop_table("knowledge_collections", schema=SCHEMA_NAME)

    for column in ("idempotency_key", "created_at", "created_by", "status", "name", "tenant_id"):
        op.drop_index(f"ix_agent_memory_knowledge_db_{column}", table_name="knowledge_databases", schema=SCHEMA_NAME)
    op.drop_constraint("uq_agent_memory_knowledge_db_idempotency", "knowledge_databases", schema=SCHEMA_NAME, type_="unique")
    op.drop_constraint("uq_agent_memory_knowledge_db_tenant_name", "knowledge_databases", schema=SCHEMA_NAME, type_="unique")
    op.drop_table("knowledge_databases", schema=SCHEMA_NAME)
