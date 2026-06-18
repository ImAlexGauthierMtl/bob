"""Integration settings use cases."""
from typing import Any, Protocol

from app.domain.exceptions import IntegrationSettingNotFoundError


class IntegrationSettingsRepositoryPort(Protocol):
    def list_settings(self, tenant_id: str) -> list[Any]:
        ...

    def upsert_setting(self, tenant_id: str, integration_key: str, data: dict[str, Any]) -> Any:
        ...

    def get_setting(self, tenant_id: str, integration_key: str) -> Any:
        ...

    def delete_setting(self, tenant_id: str, integration_key: str) -> bool:
        ...


class IntegrationSettingsUseCases:
    def __init__(self, repo: IntegrationSettingsRepositoryPort) -> None:
        self.repo = repo

    async def list_settings(self, tenant_id: str) -> list[Any]:
        return self.repo.list_settings(tenant_id)

    async def create_or_update_setting(self, data: dict[str, Any], tenant_id: str) -> Any:
        return self.repo.upsert_setting(tenant_id, data["integration_key"], data)

    async def update_setting(self, integration_key: str, data: dict[str, Any], tenant_id: str) -> Any:
        existing = self.repo.get_setting(tenant_id, integration_key)
        if not existing:
            raise IntegrationSettingNotFoundError
        return self.repo.upsert_setting(tenant_id, integration_key, data)

    async def delete_setting(self, integration_key: str, tenant_id: str) -> None:
        if not self.repo.delete_setting(tenant_id, integration_key):
            raise IntegrationSettingNotFoundError
