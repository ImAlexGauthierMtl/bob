"""Capability application use cases."""
from typing import Any, Optional, Protocol

from app.domain.exceptions import CapabilityNotFoundError


class CapabilityRepositoryPort(Protocol):
    def list_catalog(self) -> list[Any]:
        ...

    def get_user_capabilities(self, user_id: str, tenant_id: str) -> dict[str, Any]:
        ...

    def assign_capability(
        self,
        user_id: str,
        capability_code: str,
        granted: bool,
        tenant_id: str,
        granted_by: str,
    ) -> Optional[dict[str, Any]]:
        ...

    def check_capability(self, user_id: str, capability_code: str, tenant_id: str) -> dict[str, Any]:
        ...


class CapabilityUseCases:
    def __init__(self, repo: CapabilityRepositoryPort) -> None:
        self.repo = repo

    async def list_catalog(self) -> list[Any]:
        return self.repo.list_catalog()

    async def get_user_capabilities(self, user_id: str, tenant_id: str) -> dict[str, Any]:
        return self.repo.get_user_capabilities(user_id, tenant_id)

    async def assign_capability(
        self,
        user_id: str,
        data: dict[str, Any],
        user: dict[str, Any],
    ) -> dict[str, Any]:
        result = self.repo.assign_capability(
            user_id=user_id,
            capability_code=data["capability_code"],
            granted=data["granted"],
            tenant_id=user["tenant_id"],
            granted_by=user["email"],
        )
        if result is None:
            raise CapabilityNotFoundError
        return result

    async def check_capability(self, capability_code: str, user: dict[str, Any]) -> dict[str, Any]:
        return self.repo.check_capability(user["user_id"], capability_code, user["tenant_id"])
