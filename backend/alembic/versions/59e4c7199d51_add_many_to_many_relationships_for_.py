"""Add many to many relationships for activities

Revision ID: 59e4c7199d51
Revises: b3beb7dfdaf3
Create Date: 2026-03-09 22:42:06.288971

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '59e4c7199d51'
down_revision: Union[str, Sequence[str], None] = 'b3beb7dfdaf3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create junction tables
    op.create_table(
        "activity_organizations",
        sa.Column("activity_id", sa.String(36), sa.ForeignKey("activities.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "activity_contacts",
        sa.Column("activity_id", sa.String(36), sa.ForeignKey("activities.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("contact_id", sa.String(36), sa.ForeignKey("contacts.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "activity_opportunities",
        sa.Column("activity_id", sa.String(36), sa.ForeignKey("activities.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("opportunity_id", sa.String(36), sa.ForeignKey("opportunities.id", ondelete="CASCADE"), primary_key=True),
    )

    # 2. Migrate existing data
    conn = op.get_bind()
    conn.execute(sa.text("""
        INSERT INTO activity_organizations (activity_id, organization_id)
        SELECT id, organization_id FROM activities WHERE organization_id IS NOT NULL
    """))
    conn.execute(sa.text("""
        INSERT INTO activity_contacts (activity_id, contact_id)
        SELECT id, contact_id FROM activities WHERE contact_id IS NOT NULL
    """))
    conn.execute(sa.text("""
        INSERT INTO activity_opportunities (activity_id, opportunity_id)
        SELECT id, opportunity_id FROM activities WHERE opportunity_id IS NOT NULL
    """))

    # 3. Drop old columns and foreign keys from activities table
    with op.batch_alter_table("activities") as batch_op:
        batch_op.drop_constraint("activities_organization_id_fkey", type_="foreignkey")
        batch_op.drop_constraint("activities_contact_id_fkey", type_="foreignkey")
        batch_op.drop_constraint("activities_opportunity_id_fkey", type_="foreignkey")
        batch_op.drop_index("ix_activities_organization_id")
        batch_op.drop_index("ix_activities_contact_id")
        batch_op.drop_index("ix_activities_opportunity_id")
        batch_op.drop_column("organization_id")
        batch_op.drop_column("contact_id")
        batch_op.drop_column("opportunity_id")


def downgrade() -> None:
    # 1. Add back columns to activities
    with op.batch_alter_table("activities") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True))
        batch_op.add_column(sa.Column("contact_id", sa.String(36), sa.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True))
        batch_op.add_column(sa.Column("opportunity_id", sa.String(36), sa.ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True))
        batch_op.create_index(batch_op.f("ix_activities_organization_id"), ["organization_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_activities_contact_id"), ["contact_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_activities_opportunity_id"), ["opportunity_id"], unique=False)

    # 2. Migrate data back (only max 1 per activity supported in old schema)
    # Using window function to reliably get just one
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE activities SET organization_id = subquery.organization_id
        FROM (
            SELECT activity_id, organization_id, ROW_NUMBER() OVER(PARTITION BY activity_id) as rn
            FROM activity_organizations
        ) AS subquery
        WHERE activities.id = subquery.activity_id AND subquery.rn = 1
    """))
    conn.execute(sa.text("""
        UPDATE activities SET contact_id = subquery.contact_id
        FROM (
            SELECT activity_id, contact_id, ROW_NUMBER() OVER(PARTITION BY activity_id) as rn
            FROM activity_contacts
        ) AS subquery
        WHERE activities.id = subquery.activity_id AND subquery.rn = 1
    """))
    conn.execute(sa.text("""
        UPDATE activities SET opportunity_id = subquery.opportunity_id
        FROM (
            SELECT activity_id, opportunity_id, ROW_NUMBER() OVER(PARTITION BY activity_id) as rn
            FROM activity_opportunities
        ) AS subquery
        WHERE activities.id = subquery.activity_id AND subquery.rn = 1
    """))

    # 3. Drop junction tables
    op.drop_table("activity_opportunities")
    op.drop_table("activity_contacts")
    op.drop_table("activity_organizations")
