"""Smart Label entity — custom AI classification tags."""

from sqlalchemy import Column, String, Text, JSON, ForeignKey
from sqlalchemy.orm import validates, relationship, backref

from shared.database import Base, TenantMixin, AuditMixin, generate_uuid


class SmartLabel(Base, TenantMixin, AuditMixin):
    """Custom category created by the user for AI to map emails to."""

    __tablename__ = "smart_labels"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(50), nullable=False)
    color = Column(String(20), nullable=False, default="blue")

    # LLM context fields — help the AI understand what this label means
    description = Column(Text, nullable=True, comment="Human-readable description of this category")
    keywords = Column(JSON, nullable=True, default=list, comment="Keywords/phrases the AI should look for")
    prompt_hint = Column(Text, nullable=True, comment="Custom instruction for the LLM when matching this label")

    # Hierarchy
    parent_id = Column(String(36), ForeignKey("smart_labels.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Relationships — self-referential: parent_id points to id
    sub_labels = relationship(
        "SmartLabel",
        cascade="all, delete-orphan",
        backref=backref("parent", remote_side="SmartLabel.id"),
        foreign_keys=[parent_id],
        lazy="selectin",
    )

    @validates("name")
    def validate_name(self, key, value):
        if not value or not value.strip():
            raise ValueError("SmartLabel name cannot be empty")
        return value.strip()

