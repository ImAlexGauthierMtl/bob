from app.domain.entities.base import Base

# Auth & Identity
from app.domain.entities.user import User
from app.domain.entities.role import Role

# Settings & Automation
from app.domain.entities.department import Department
from app.domain.entities.capability import CapabilityDefinition, UserCapability, DeptCapability
from app.domain.entities.bob_settings import BobUserSettings
from app.domain.entities.workflow import Workflow, WorkflowStep
from app.domain.entities.workflow_execution import WorkflowExecution, WorkflowStepExecution
from app.domain.entities.bcc_entities import BccOrganization, BccTeam, BccRole, BccUserRole
from app.domain.entities.training_models import TrainingSession, TrainingNote, TrainingMissingElement
from app.domain.entities.tenant import Tenant

# Feature Modules
from app.domain.entities.contact import Contact
from app.domain.entities.organization import Organization
from app.domain.entities.opportunity import Opportunity
from app.domain.entities.quote import Quote
from app.domain.entities.product import Product
from app.domain.entities.opportunity_product import OpportunityProduct
from app.domain.entities.activity import Activity
from app.domain.entities.client_map import ClientMap, GoldenNote, InsightTriple
from app.domain.entities.kb_article import KBArticle, KBCategory
from app.domain.entities.usage_transaction import UsageTransaction
from app.domain.entities.enrichment_run import EnrichmentRun

# Microsoft 365 Integration
from app.domain.entities.ms365_connection import MS365Connection
from app.domain.entities.synced_email import SyncedEmail
from app.domain.entities.synced_event import SyncedEvent
from app.domain.entities.smart_label import SmartLabel
