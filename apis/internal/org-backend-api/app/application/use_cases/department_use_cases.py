"""Department application use cases."""
from typing import Any, Callable, Optional, Protocol

from app.domain.exceptions import DepartmentNotFoundError


DepartmentEntity = Any
DepartmentFactory = Callable[..., DepartmentEntity]


class DepartmentRepositoryPort(Protocol):
    def create(self, dept: DepartmentEntity) -> DepartmentEntity:
        ...

    def get_by_id(self, dept_id: str, tenant_id: str) -> Optional[DepartmentEntity]:
        ...

    def list_all(self, tenant_id: str) -> list[DepartmentEntity]:
        ...

    def update(self, dept: DepartmentEntity) -> DepartmentEntity:
        ...

    def soft_delete(self, dept: DepartmentEntity, deleted_by: str) -> DepartmentEntity:
        ...


class DepartmentUseCases:
    def __init__(
        self,
        repo: DepartmentRepositoryPort,
        create_department_entity: DepartmentFactory,
    ) -> None:
        self.repo = repo
        self.create_department_entity = create_department_entity

    async def list_departments(self, tenant_id: str) -> list[DepartmentEntity]:
        return self.repo.list_all(tenant_id)

    async def create_department(
        self,
        data: dict[str, Any],
        user: dict[str, Any],
    ) -> DepartmentEntity:
        dept = self.create_department_entity(
            **data,
            tenant_id=user["tenant_id"],
            created_by=user["email"],
        )
        return self.repo.create(dept)

    async def get_department(self, dept_id: str, tenant_id: str) -> DepartmentEntity:
        dept = self.repo.get_by_id(dept_id, tenant_id)
        if not dept:
            raise DepartmentNotFoundError
        return dept

    async def update_department(
        self,
        dept_id: str,
        updates: dict[str, Any],
        user: dict[str, Any],
    ) -> DepartmentEntity:
        dept = await self.get_department(dept_id, user["tenant_id"])
        for key, value in updates.items():
            setattr(dept, key, value)
        return self.repo.update(dept)

    async def delete_department(self, dept_id: str, user: dict[str, Any]) -> None:
        dept = await self.get_department(dept_id, user["tenant_id"])
        self.repo.soft_delete(dept, user["email"])
