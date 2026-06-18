"""Bob settings repository."""
from typing import Any

from app.infrastructure.persistence.models.bob_settings import BobUserSettings


class BobSettingsRepository:
    def __init__(self, db: Any) -> None:
        self.db = db

    def get_or_create(self, user_id: str, tenant_id: str) -> BobUserSettings:
        return BobUserSettings.get_or_create(self.db, user_id, tenant_id)

    def save(self, settings: BobUserSettings) -> BobUserSettings:
        self.db.commit()
        self.db.refresh(settings)
        return settings

    def reset(self, user_id: str) -> None:
        settings = self.db.query(BobUserSettings).filter(BobUserSettings.user_id == user_id).first()
        if settings:
            self.db.delete(settings)
            self.db.commit()
