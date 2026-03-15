"""Smart Label entity — AI classification labels for emails."""

from sqlalchemy import Column, String, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship

from shared.database import Base, TenantMixin, AuditMixin, generate_uuid


class SmartLabel(Base, TenantMixin, AuditMixin):
    """Tenant-scoped classification label for AI email tagging.

    Supports hierarchical labels via parent_id.
    """

    __tablename__ = "smart_labels"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, index=True)
    color = Column(String(20), nullable=True, default="#000000")
    description = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True, comment="List of keywords for matching")
    prompt_hint = Column(Text, nullable=True, comment="LLM hint for classification")
    parent_id = Column(String(36), ForeignKey("smart_labels.id", ondelete="CASCADE"), nullable=True, index=True)

    sub_labels = relationship(
        "SmartLabel",
        back_populates="parent",
        foreign_keys=[parent_id],
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    parent = relationship(
        "SmartLabel",
        back_populates="sub_labels",
        remote_side="SmartLabel.id",
        foreign_keys=[parent_id],
        lazy="selectin",
    )
