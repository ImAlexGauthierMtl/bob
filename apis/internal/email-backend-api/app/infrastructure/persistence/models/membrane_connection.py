"""Membrane Connection entity — tracks a Membrane-backed connection for a user/tenant."""

from sqlalchemy import Column, String, Text, DateTime, Boolean
from sqlalchemy.orm import relationship

from shared.database import Base, TenantMixin, AuditMixin, SoftDeleteMixin, generate_uuid


class MembraneConnection(Base, TenantMixin, AuditMixin, SoftDeleteMixin):
    """Maps a Croo user/tenant to a Membrane connection ID.

    Membrane stores the actual OAuth tokens and provider state. We only keep
    a lightweight reference so we know which users have which integrations
    connected, and can route webhook payloads to the correct tenant/user.
    """

    __tablename__ = "membrane_connections"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Owner
    user_id = Column(String(36), nullable=False, index=True,
                     comment="Soft ref to user service users.id")

    # Membrane identifiers
    membrane_connection_id = Column(
        String(255), nullable=False, index=True,
        comment="Connection ID returned by Membrane API",
    )
    integration_key = Column(
        String(100), nullable=False, index=True,
        comment="Membrane integration key, e.g. 'microsoft-outlook'",
    )
    connection_name = Column(
        String(255), nullable=True,
        comment="Human-readable connection label from Membrane",
    )

    # State
    is_active = Column(Boolean, default=True, nullable=False)
    last_email_sync = Column(DateTime(timezone=True), nullable=True)
    last_calendar_sync = Column(DateTime(timezone=True), nullable=True)

    # JSON blob for Membrane-specific metadata (raw webhook state, etc.)
    metadata_json = Column(Text, nullable=True)
