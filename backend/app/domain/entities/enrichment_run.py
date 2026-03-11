"""EnrichmentRun entity — tracks enrichment pipeline executions."""

from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import Session

from app.domain.entities.base import Base, TenantMixin, AuditMixin, generate_uuid, utc_now


class EnrichmentRun(Base, TenantMixin, AuditMixin):
    """Tracks a single enrichment pipeline execution for auditability."""

    __tablename__ = "enrichment_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    status = Column(String(20), default="running", nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    fields_updated = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    result_summary = Column(JSON, nullable=True)

    def complete(self, status: str, fields_updated: int = 0, error: str | None = None, summary: dict | None = None):
        self.status = status
        self.completed_at = utc_now()
        self.fields_updated = fields_updated
        self.error = error
        self.result_summary = summary
