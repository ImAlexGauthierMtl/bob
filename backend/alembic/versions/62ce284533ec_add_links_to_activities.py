"""Add links to activities

Revision ID: 62ce284533ec
Revises: 59e4c7199d51
Create Date: 2026-03-09 23:19:10.823447

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '62ce284533ec'
down_revision: Union[str, Sequence[str], None] = '59e4c7199d51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('activities', sa.Column('organization_id', sa.String(length=36), nullable=True))
    op.add_column('activities', sa.Column('contact_id', sa.String(length=36), nullable=True))
    op.add_column('activities', sa.Column('opportunity_id', sa.String(length=36), nullable=True))
    op.create_index(op.f('ix_activities_contact_id'), 'activities', ['contact_id'], unique=False)
    op.create_index(op.f('ix_activities_opportunity_id'), 'activities', ['opportunity_id'], unique=False)
    op.create_index(op.f('ix_activities_organization_id'), 'activities', ['organization_id'], unique=False)
    op.create_foreign_key(None, 'activities', 'opportunities', ['opportunity_id'], ['id'])
    op.create_foreign_key(None, 'activities', 'organizations', ['organization_id'], ['id'])
    op.create_foreign_key(None, 'activities', 'contacts', ['contact_id'], ['id'])

def downgrade() -> None:
    op.drop_constraint(None, 'activities', type_='foreignkey')
    op.drop_constraint(None, 'activities', type_='foreignkey')
    op.drop_constraint(None, 'activities', type_='foreignkey')
    op.drop_index(op.f('ix_activities_organization_id'), table_name='activities')
    op.drop_index(op.f('ix_activities_opportunity_id'), table_name='activities')
    op.drop_index(op.f('ix_activities_contact_id'), table_name='activities')
    op.drop_column('activities', 'opportunity_id')
    op.drop_column('activities', 'contact_id')
    op.drop_column('activities', 'organization_id')
