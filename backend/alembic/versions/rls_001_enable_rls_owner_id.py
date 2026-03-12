"""Alembic migration — Enable RLS + add owner_id to business entities.

This migration:
1. Adds owner_id (FK to users) to key business tables
2. Enables RLS on all tenant-scoped tables
3. Creates tenant isolation policies
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "rls_001"
down_revision = "dd9035e68051"
branch_labels = None
depends_on = None

# Tables that have tenant_id and need RLS
TENANT_TABLES = [
    "organizations",
    "contacts",
    "opportunities",
    "quotes",
    "activities",
    "departments",
    "capabilities",
    "workflows",
    "workflow_executions",
    "bcc_departments",
    "bcc_teams",
    "bcc_roles",
    "bcc_skills",
    "bcc_tasks",
    "training_templates",
    "training_sessions",
    "roles",
]

# Tables that get owner_id for multi-user isolation
OWNER_TABLES = [
    "organizations",
    "contacts",
    "opportunities",
    "quotes",
    "activities",
]


def upgrade() -> None:
    """Add owner_id, enable RLS, create policies."""

    # 1. Add owner_id to business tables
    for table in OWNER_TABLES:
        op.add_column(
            table,
            sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        )
        op.create_index(f"ix_{table}_owner_id", table, ["owner_id"])

    # 2. Enable RLS on all tenant tables
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

        # Create tenant isolation policy
        op.execute(f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
            USING (tenant_id = current_setting('app.current_tenant_id', true))
        """)

    # 3. Also enable RLS on user_roles (scoped via role -> tenant)
    op.execute("ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE user_roles FORCE ROW LEVEL SECURITY")

    # Create a permissive policy for user_roles (user can see their own roles)
    op.execute("""
        CREATE POLICY user_roles_isolation ON user_roles
        USING (user_id = current_setting('app.current_user_id', true))
    """)

    # 4. Ensure the superuser/app role bypasses RLS
    # (The app connects with a role that has BYPASSRLS, so this is for safety)
    op.execute("""
        DO $$
        BEGIN
            -- Create the app configuration namespace if it doesn't exist
            PERFORM set_config('app.current_tenant_id', '', false);
            PERFORM set_config('app.current_user_id', '', false);
        EXCEPTION
            WHEN OTHERS THEN NULL;
        END $$;
    """)


def downgrade() -> None:
    """Remove RLS and owner_id."""

    # Remove user_roles RLS
    op.execute("DROP POLICY IF EXISTS user_roles_isolation ON user_roles")
    op.execute("ALTER TABLE user_roles DISABLE ROW LEVEL SECURITY")

    # Remove tenant RLS
    for table in reversed(TENANT_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Remove owner_id columns
    for table in reversed(OWNER_TABLES):
        op.drop_index(f"ix_{table}_owner_id", table_name=table)
        op.drop_column(table, "owner_id")
