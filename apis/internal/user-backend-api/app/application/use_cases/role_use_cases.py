"""Role application use cases."""
from dataclasses import dataclass
from typing import Any, Callable, Optional, Protocol

from app.domain.exceptions import RoleAlreadyExistsError, RoleNotFoundError, SystemRoleDeletionError


PermissionEntity = Any
RoleEntity = Any
RoleFactory = Callable[..., RoleEntity]
RoleRefresher = Callable[[RoleEntity], None]


class RoleRepositoryPort(Protocol):
    def list_permissions(self) -> list[PermissionEntity]:
        ...

    def create_role(self, role: RoleEntity) -> RoleEntity:
        ...

    def get_role_by_id(self, role_id: str, tenant_id: str) -> Optional[RoleEntity]:
        ...

    def get_role_by_name(self, name: str, tenant_id: str) -> Optional[RoleEntity]:
        ...

    def list_roles(self, tenant_id: str) -> list[RoleEntity]:
        ...

    def update_role(self, role: RoleEntity) -> RoleEntity:
        ...

    def delete_role(self, role: RoleEntity) -> bool:
        ...

    def set_role_permissions(self, role_id: str, permission_ids: list[str]) -> None:
        ...

    def get_user_roles(self, user_id: str) -> list[RoleEntity]:
        ...

    def get_user_permissions(self, user_id: str) -> list[str]:
        ...

    def assign_role_to_user(self, user_id: str, role_id: str) -> None:
        ...

    def remove_role_from_user(self, user_id: str, role_id: str) -> None:
        ...


@dataclass(frozen=True)
class RoleListResult:
    items: list[RoleEntity]
    total: int


class RoleUseCases:
    def __init__(
        self,
        repo: RoleRepositoryPort,
        create_role_entity: RoleFactory,
        refresh_role: RoleRefresher,
    ) -> None:
        self.repo = repo
        self.create_role_entity = create_role_entity
        self.refresh_role = refresh_role

    async def list_permissions(self) -> list[PermissionEntity]:
        return self.repo.list_permissions()

    async def list_roles(self, tenant_id: str) -> RoleListResult:
        roles = self.repo.list_roles(tenant_id)
        return RoleListResult(items=roles, total=len(roles))

    async def create_role(self, data: dict[str, Any], tenant_id: str) -> RoleEntity:
        existing = self.repo.get_role_by_name(data["name"], tenant_id)
        if existing:
            raise RoleAlreadyExistsError
        role = self.create_role_entity(
            name=data["name"],
            description=data.get("description"),
            tenant_id=tenant_id,
            is_system=False,
        )
        return self.repo.create_role(role)

    async def get_role(self, role_id: str, tenant_id: str) -> RoleEntity:
        role = self.repo.get_role_by_id(role_id, tenant_id)
        if not role:
            raise RoleNotFoundError
        return role

    async def update_role(
        self,
        role_id: str,
        data: dict[str, Any],
        tenant_id: str,
    ) -> RoleEntity:
        role = await self.get_role(role_id, tenant_id)
        if data.get("name") is not None:
            role.name = data["name"]
        if data.get("description") is not None:
            role.description = data["description"]
        return self.repo.update_role(role)

    async def delete_role(self, role_id: str, tenant_id: str) -> None:
        role = await self.get_role(role_id, tenant_id)
        if not self.repo.delete_role(role):
            raise SystemRoleDeletionError

    async def set_role_permissions(
        self,
        role_id: str,
        permission_ids: list[str],
        tenant_id: str,
    ) -> RoleEntity:
        role = await self.get_role(role_id, tenant_id)
        self.repo.set_role_permissions(role_id, permission_ids)
        self.refresh_role(role)
        return role

    async def get_user_roles(self, user_id: str) -> list[RoleEntity]:
        return self.repo.get_user_roles(user_id)

    async def get_user_permissions(self, user_id: str) -> list[str]:
        return self.repo.get_user_permissions(user_id)

    async def assign_role(self, user_id: str, role_id: str) -> dict[str, str]:
        self.repo.assign_role_to_user(user_id, role_id)
        return {"message": "Role assigned"}

    async def remove_role(self, user_id: str, role_id: str) -> None:
        self.repo.remove_role_from_user(user_id, role_id)
