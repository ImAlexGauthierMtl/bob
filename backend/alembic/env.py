"""Alembic env.py — configured for Croo Digital Experience."""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from app.config import settings
from app.domain.entities.base import Base

from app.domain.entities.user import User
from app.domain.entities.role import Role
from app.domain.entities.department import Department
from app.domain.entities.capability import CapabilityDefinition
from app.domain.entities.bob_settings import BobUserSettings
from app.domain.entities.workflow import Workflow, WorkflowStep
from app.domain.entities.workflow_execution import WorkflowExecution, WorkflowStepExecution
from app.domain.entities.bcc_entities import BccOrganization, BccTeam, BccRole, BccUserRole
from app.domain.entities.training_models import TrainingSession, TrainingNote, TrainingMissingElement
from app.domain.entities.tenant import Tenant
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
from app.domain.entities.ms365_connection import MS365Connection
from app.domain.entities.synced_email import SyncedEmail
from app.domain.entities.synced_event import SyncedEvent
from app.domain.entities.smart_label import SmartLabel
import app.domain.entities.activity  # ensure M:N tables are loaded

config = context.config

# Override sqlalchemy.url from app settings
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
