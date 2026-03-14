from app.infrastructure.database import SessionLocal
from app.domain.entities.base import Base
from app.domain.entities import user, organization, contact, opportunity, quote, activity, department, capability, bob_settings, tenant
from app.domain.entities import workflow, workflow_execution
from app.domain.entities import bcc_entities
from app.domain.entities import ms365_connection, synced_email, synced_event
from app.domain.entities import training_models
from app.domain.entities import role as role_entities
from app.domain.entities import product as product_entity
from app.domain.entities import opportunity_product as opp_product_entity
from app.domain.entities import usage_transaction as usage_transaction_entity
from app.domain.entities import kb_article
from app.domain.entities import smart_label
from app.infrastructure.seed_workflows import seed_workflows
from sqlalchemy import distinct

db = SessionLocal()
try:
    wfs = db.query(workflow.Workflow).filter(workflow.Workflow.name.in_(['Smart Email Prioritization', 'Inbox AI Triaging'])).all()
    for w in wfs:
        db.delete(w)
    db.commit()
    print('Deleted old workflows, re-seeding...')
    all_tenants = [r[0] for r in db.query(distinct(user.User.tenant_id)).all()]
    for tid in all_tenants:
        seed_workflows(db, tenant_id=tid)
    print('Done!')
finally:
    db.close()
