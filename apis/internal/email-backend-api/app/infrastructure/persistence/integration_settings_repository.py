"""Integration Settings repository — data access for per-tenant integration config."""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.domain.entities.integration_setting import IntegrationSetting


class IntegrationSettingsRepository:
    """Repository for tenant-level integration configuration."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_setting(
        self, tenant_id: str, integration_key: str
    ) -> Optional[IntegrationSetting]:
        return (
            self.db.query(IntegrationSetting)
            .filter(
                IntegrationSetting.tenant_id == tenant_id,
                IntegrationSetting.integration_key == integration_key,
            )
            .first()
        )

    def list_settings(self, tenant_id: str) -> List[IntegrationSetting]:
        return (
            self.db.query(IntegrationSetting)
            .filter(IntegrationSetting.tenant_id == tenant_id)
            .order_by(IntegrationSetting.integration_key)
            .all()
        )

    def upsert_setting(self, tenant_id: str, integration_key: str, data: dict) -> IntegrationSetting:
        existing = self.get_setting(tenant_id, integration_key)
        if existing:
            for key, value in data.items():
                if hasattr(existing, key) and key not in {"id", "tenant_id", "integration_key", "created_at"}:
                    setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        setting = IntegrationSetting(tenant_id=tenant_id, integration_key=integration_key, **data)
        self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        return setting

    def delete_setting(self, tenant_id: str, integration_key: str) -> bool:
        setting = self.get_setting(tenant_id, integration_key)
        if setting:
            self.db.delete(setting)
            self.db.commit()
            return True
        return False
