---
name: dx_base_create_alembic_first_revision_with_schema
description: Génère la première révision Alembic d'un Backend : create_schema + grants + tables initiales en upgrade, DROP SCHEMA CASCADE en downgrade.
metadata:
  reference: § 2.6 + § 2.7.5
---

# dx_base_create_alembic_first_revision_with_schema

## Template à générer
```python
\"\"\"create schema <svc> and initial tables\"\"\"
from alembic import op
import sqlalchemy as sa

revision = "0001_create_schema_and_initial_tables"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA = "<svc>"

def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
    op.execute(f'GRANT USAGE, CREATE ON SCHEMA "{SCHEMA}" TO CURRENT_USER')
    op.create_table(
        "<entity>",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema=SCHEMA,
    )

def downgrade() -> None:
    op.drop_table("<entity>", schema=SCHEMA)
    op.execute(f'DROP SCHEMA "{SCHEMA}" CASCADE')
```
