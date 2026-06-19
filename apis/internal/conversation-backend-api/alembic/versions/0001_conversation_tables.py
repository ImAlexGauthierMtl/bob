"""conversation tables

Revision ID: 0001_conversation
Revises:
Create Date: 2026-06-19 00:00:00.000000

"""

from typing import Sequence, Union
import os

from alembic import op
import sqlalchemy as sa


revision: str = "0001_conversation"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SCHEMA_NAME = "conversation"


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
        "sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("turn_count", sa.Integer(), nullable=False),
        sa.Column("mission", sa.JSON(), nullable=True),
        sa.Column("client_context", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_conversation_sessions_tenant_id", "sessions", ["tenant_id"], schema=SCHEMA_NAME)
    op.create_index("ix_conversation_sessions_user_id", "sessions", ["user_id"], schema=SCHEMA_NAME)
    op.create_index("ix_conversation_sessions_status", "sessions", ["status"], schema=SCHEMA_NAME)
    op.create_index("ix_conversation_sessions_is_deleted", "sessions", ["is_deleted"], schema=SCHEMA_NAME)
    op.create_index(
        "ix_conversation_sessions_scope_updated",
        "sessions",
        ["tenant_id", "user_id", "updated_at"],
        schema=SCHEMA_NAME,
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], [f"{SCHEMA_NAME}.sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_conversation_messages_session_id", "messages", ["session_id"], schema=SCHEMA_NAME)
    op.create_index("ix_conversation_messages_tenant_id", "messages", ["tenant_id"], schema=SCHEMA_NAME)
    op.create_index("ix_conversation_messages_user_id", "messages", ["user_id"], schema=SCHEMA_NAME)
    op.create_index("ix_conversation_messages_created_at", "messages", ["created_at"], schema=SCHEMA_NAME)
    op.create_index(
        "ix_conversation_messages_idempotency_key",
        "messages",
        ["idempotency_key"],
        schema=SCHEMA_NAME,
    )
    op.create_unique_constraint(
        "uq_conversation_messages_scope_idempotency",
        "messages",
        ["tenant_id", "user_id", "idempotency_key"],
        schema=SCHEMA_NAME,
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_conversation_messages_scope_idempotency",
        "messages",
        schema=SCHEMA_NAME,
        type_="unique",
    )
    op.drop_index("ix_conversation_messages_idempotency_key", table_name="messages", schema=SCHEMA_NAME)
    op.drop_index("ix_conversation_messages_created_at", table_name="messages", schema=SCHEMA_NAME)
    op.drop_index("ix_conversation_messages_user_id", table_name="messages", schema=SCHEMA_NAME)
    op.drop_index("ix_conversation_messages_tenant_id", table_name="messages", schema=SCHEMA_NAME)
    op.drop_index("ix_conversation_messages_session_id", table_name="messages", schema=SCHEMA_NAME)
    op.drop_table("messages", schema=SCHEMA_NAME)
    op.drop_index("ix_conversation_sessions_scope_updated", table_name="sessions", schema=SCHEMA_NAME)
    op.drop_index("ix_conversation_sessions_is_deleted", table_name="sessions", schema=SCHEMA_NAME)
    op.drop_index("ix_conversation_sessions_status", table_name="sessions", schema=SCHEMA_NAME)
    op.drop_index("ix_conversation_sessions_user_id", table_name="sessions", schema=SCHEMA_NAME)
    op.drop_index("ix_conversation_sessions_tenant_id", table_name="sessions", schema=SCHEMA_NAME)
    op.drop_table("sessions", schema=SCHEMA_NAME)
    op.execute(f"DROP SCHEMA IF EXISTS {_quoted_identifier(SCHEMA_NAME)} CASCADE")
