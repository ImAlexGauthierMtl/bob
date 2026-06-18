"""Integration Setting entity — admin-configurable per-tenant integration scope."""

from sqlalchemy import Column, String, Boolean, Text, Enum as SAEnum, UniqueConstraint

from shared.database import Base, TenantMixin, AuditMixin, generate_uuid
import enum


class ScopeMode(str, enum.Enum):
    """How an integration is scoped within a tenant."""
    PER_USER = "per-user"
    PER_ORGANIZATION = "per-organization"
    PER_TENANT = "per-tenant"


class IntegrationSetting(Base, TenantMixin, AuditMixin):
    """Per-tenant configuration for each available integration.

    Allows tenant admins to choose whether an integration (e.g. Outlook,
    HubSpot) is scoped per-user, per-organization, or per-tenant.
    This drives the tenantKey resolution in the Membrane JWT token generation.
    """

    __tablename__ = "integration_settings"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Integration identifier (matches Membrane integration key, e.g. 'microsoft-outlook', 'hubspot')
    integration_key = Column(String(100), nullable=False, index=True)

    # Scope mode for this integration within the tenant
    scope_mode = Column(
        String(20),
        nullable=False,
        default=ScopeMode.PER_USER.value,
        comment="per-user | per-organization | per-tenant",
    )

    # Is this integration enabled for the tenant?
    is_enabled = Column(Boolean, default=True, nullable=False)

    # Optional: override the integration display name for this tenant
    display_name = Column(String(200), nullable=True)

    # Optional: admin notes
    notes = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "integration_key", name="uix_integration_setting_tenant_key"),
    )
