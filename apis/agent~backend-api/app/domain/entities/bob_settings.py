"""Bob user settings entity — persisted per-user Bob configuration."""

from sqlalchemy import Column, String, Float, Boolean, Text, ForeignKey
from sqlalchemy.orm import Session

from shared.database import Base, TenantMixin, AuditMixin, generate_uuid


class BobUserSettings(Base, TenantMixin, AuditMixin):
    """Per-user Bob personality and voice settings.

    Stores user preferences for Bob's behavior (tone, formality, creativity,
    response length) and voice parameters (TTS voice, speed).
    One row per user — upserted on save.
    """

    __tablename__ = "bob_user_settings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Personality
    tone = Column(String(20), default="professional", nullable=False)
    formality = Column(Float, default=0.5, nullable=False)
    response_length = Column(String(20), default="balanced", nullable=False)
    language = Column(String(10), default="auto", nullable=False)
    creativity = Column(Float, default=0.3, nullable=False)
    emoji_usage = Column(Boolean, default=False, nullable=False)

    # Voice
    voice = Column(String(30), default="autumn", nullable=False)
    speed = Column(Float, default=1.0, nullable=False)
    auto_listen = Column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<BobUserSettings user={self.user_id} tone={self.tone} voice={self.voice}>"

    @classmethod
    def get_or_create(cls, db: Session, user_id: str, tenant_id: str = "default") -> "BobUserSettings":
        """Get existing settings or create defaults for a user."""
        settings = db.query(cls).filter(cls.user_id == user_id).first()
        if not settings:
            settings = cls(user_id=user_id, tenant_id=tenant_id)
            db.add(settings)
            db.commit()
            db.refresh(settings)
        return settings
