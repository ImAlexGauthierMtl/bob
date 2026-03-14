import sys
import os

# Ensure `app` is in sys.path
sys.path.insert(0, os.path.abspath('.'))

from app.domain.entities.base import Base

# By importing the modules directly, we mimic what `alembic/env.py` does:
from app.domain.entities import (
    user, organization, contact, opportunity, quote,
    activity, department, capability, bob_settings,
    workflow, workflow_execution, bcc_entities, training_models,
    role, ms365_connection, synced_email, synced_event, 
    smart_label, kb_article, product, usage_transaction,
    opportunity_product, enrichment_run, tenant
)

print(Base.metadata.tables.keys())
