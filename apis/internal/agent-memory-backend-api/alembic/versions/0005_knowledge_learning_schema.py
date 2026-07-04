"""knowledge learning schema

Revision ID: 0005_knowledge_learning_schema
Revises: 0004_knowledge_registry
Create Date: 2026-06-20 00:00:01.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_knowledge_learning_schema"
down_revision: Union[str, None] = "0004_knowledge_registry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SCHEMA_NAME = "agent_memory"


def upgrade() -> None:
    op.create_table(
        "knowledge_ingestion_runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("trigger_type", sa.String(length=80), nullable=False),
        sa.Column("external_event_id", sa.String(length=180), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("raw_items_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("normalized_items_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candidate_procedures_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_foreign_key(
        "fk_agent_memory_knowledge_ingestion_run_source",
        "knowledge_ingestion_runs",
        "knowledge_sources",
        ["source_id"],
        ["id"],
        source_schema=SCHEMA_NAME,
        referent_schema=SCHEMA_NAME,
        ondelete="CASCADE",
    )
    for column in ("tenant_id", "source_id", "trigger_type", "external_event_id", "status", "started_at"):
        op.create_index(
            f"ix_agent_memory_knowledge_ingestion_run_{column}",
            "knowledge_ingestion_runs",
            [column],
            schema=SCHEMA_NAME,
        )

    op.create_table(
        "knowledge_items",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("external_id", sa.String(length=180), nullable=False),
        sa.Column("item_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_unique_constraint(
        "uq_agent_memory_knowledge_item_source_external",
        "knowledge_items",
        ["tenant_id", "source_id", "external_id"],
        schema=SCHEMA_NAME,
    )
    op.create_foreign_key(
        "fk_agent_memory_knowledge_item_source",
        "knowledge_items",
        "knowledge_sources",
        ["source_id"],
        ["id"],
        source_schema=SCHEMA_NAME,
        referent_schema=SCHEMA_NAME,
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_agent_memory_knowledge_item_run",
        "knowledge_items",
        "knowledge_ingestion_runs",
        ["run_id"],
        ["id"],
        source_schema=SCHEMA_NAME,
        referent_schema=SCHEMA_NAME,
        ondelete="SET NULL",
    )
    for column in ("tenant_id", "source_id", "run_id", "external_id", "item_type", "status", "content_hash", "created_at"):
        op.create_index(f"ix_agent_memory_knowledge_item_{column}", "knowledge_items", [column], schema=SCHEMA_NAME)

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("collection_id", sa.String(length=64), nullable=False),
        sa.Column("item_id", sa.String(length=64), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("vector_id", sa.String(length=120), nullable=False),
        sa.Column("embedding_model", sa.String(length=160), nullable=False),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False),
        sa.Column("milvus_collection", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_unique_constraint(
        "uq_agent_memory_knowledge_chunk_vector",
        "knowledge_chunks",
        ["tenant_id", "vector_id"],
        schema=SCHEMA_NAME,
    )
    op.create_foreign_key(
        "fk_agent_memory_knowledge_chunk_collection",
        "knowledge_chunks",
        "knowledge_collections",
        ["collection_id"],
        ["id"],
        source_schema=SCHEMA_NAME,
        referent_schema=SCHEMA_NAME,
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_agent_memory_knowledge_chunk_item",
        "knowledge_chunks",
        "knowledge_items",
        ["item_id"],
        ["id"],
        source_schema=SCHEMA_NAME,
        referent_schema=SCHEMA_NAME,
        ondelete="CASCADE",
    )
    for column in ("tenant_id", "collection_id", "item_id", "vector_id", "milvus_collection", "status", "created_at"):
        op.create_index(f"ix_agent_memory_knowledge_chunk_{column}", "knowledge_chunks", [column], schema=SCHEMA_NAME)

    op.create_table(
        "knowledge_procedures",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("collection_id", sa.String(length=64), nullable=False),
        sa.Column("source_item_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("intent_key", sa.String(length=160), nullable=False),
        sa.Column("trigger_summary", sa.Text(), nullable=False),
        sa.Column("procedure_markdown", sa.Text(), nullable=False),
        sa.Column("tool_plan_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("generated_by_model", sa.String(length=160), nullable=False),
        sa.Column("approved_by", sa.String(length=64), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_foreign_key(
        "fk_agent_memory_knowledge_procedure_collection",
        "knowledge_procedures",
        "knowledge_collections",
        ["collection_id"],
        ["id"],
        source_schema=SCHEMA_NAME,
        referent_schema=SCHEMA_NAME,
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_agent_memory_knowledge_procedure_source_item",
        "knowledge_procedures",
        "knowledge_items",
        ["source_item_id"],
        ["id"],
        source_schema=SCHEMA_NAME,
        referent_schema=SCHEMA_NAME,
        ondelete="SET NULL",
    )
    for column in ("tenant_id", "collection_id", "source_item_id", "intent_key", "status", "created_at", "approved_at"):
        op.create_index(f"ix_agent_memory_knowledge_procedure_{column}", "knowledge_procedures", [column], schema=SCHEMA_NAME)


def downgrade() -> None:
    for column in ("approved_at", "created_at", "status", "intent_key", "source_item_id", "collection_id", "tenant_id"):
        op.drop_index(f"ix_agent_memory_knowledge_procedure_{column}", table_name="knowledge_procedures", schema=SCHEMA_NAME)
    op.drop_constraint("fk_agent_memory_knowledge_procedure_source_item", "knowledge_procedures", schema=SCHEMA_NAME, type_="foreignkey")
    op.drop_constraint("fk_agent_memory_knowledge_procedure_collection", "knowledge_procedures", schema=SCHEMA_NAME, type_="foreignkey")
    op.drop_table("knowledge_procedures", schema=SCHEMA_NAME)

    for column in ("created_at", "status", "milvus_collection", "vector_id", "item_id", "collection_id", "tenant_id"):
        op.drop_index(f"ix_agent_memory_knowledge_chunk_{column}", table_name="knowledge_chunks", schema=SCHEMA_NAME)
    op.drop_constraint("fk_agent_memory_knowledge_chunk_item", "knowledge_chunks", schema=SCHEMA_NAME, type_="foreignkey")
    op.drop_constraint("fk_agent_memory_knowledge_chunk_collection", "knowledge_chunks", schema=SCHEMA_NAME, type_="foreignkey")
    op.drop_constraint("uq_agent_memory_knowledge_chunk_vector", "knowledge_chunks", schema=SCHEMA_NAME, type_="unique")
    op.drop_table("knowledge_chunks", schema=SCHEMA_NAME)

    for column in ("created_at", "content_hash", "status", "item_type", "external_id", "run_id", "source_id", "tenant_id"):
        op.drop_index(f"ix_agent_memory_knowledge_item_{column}", table_name="knowledge_items", schema=SCHEMA_NAME)
    op.drop_constraint("fk_agent_memory_knowledge_item_run", "knowledge_items", schema=SCHEMA_NAME, type_="foreignkey")
    op.drop_constraint("fk_agent_memory_knowledge_item_source", "knowledge_items", schema=SCHEMA_NAME, type_="foreignkey")
    op.drop_constraint("uq_agent_memory_knowledge_item_source_external", "knowledge_items", schema=SCHEMA_NAME, type_="unique")
    op.drop_table("knowledge_items", schema=SCHEMA_NAME)

    for column in ("started_at", "status", "external_event_id", "trigger_type", "source_id", "tenant_id"):
        op.drop_index(f"ix_agent_memory_knowledge_ingestion_run_{column}", table_name="knowledge_ingestion_runs", schema=SCHEMA_NAME)
    op.drop_constraint("fk_agent_memory_knowledge_ingestion_run_source", "knowledge_ingestion_runs", schema=SCHEMA_NAME, type_="foreignkey")
    op.drop_table("knowledge_ingestion_runs", schema=SCHEMA_NAME)
