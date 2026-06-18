"""Smart label use cases."""
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from app.domain.exceptions import SmartLabelDeleteError, SmartLabelDuplicateError, SmartLabelNotFoundError


SmartLabelFactory = Callable[..., Any]


class SmartLabelRepositoryPort(Protocol):
    def get_by_name(self, name: str, tenant_id: str, parent_id: str | None = None) -> Any:
        ...

    def create(self, label: Any) -> Any:
        ...

    def list_all(self, tenant_id: str, skip: int = 0, limit: int = 50) -> list[Any]:
        ...

    def count(self, tenant_id: str) -> int:
        ...

    def get_by_id(self, label_id: str, tenant_id: str) -> Any:
        ...

    def update(self, label: Any) -> Any:
        ...

    def delete(self, label: Any) -> None:
        ...


@dataclass(frozen=True)
class SmartLabelListResult:
    items: list[Any]
    total: int
    skip: int
    limit: int


class SmartLabelUseCases:
    def __init__(self, repo: SmartLabelRepositoryPort, create_label: SmartLabelFactory) -> None:
        self.repo = repo
        self.create_label = create_label

    async def create_smart_label(self, data: dict[str, Any], user: dict[str, Any]) -> Any:
        existing = self.repo.get_by_name(data["name"], user["tenant_id"], data.get("parent_id"))
        if existing:
            raise SmartLabelDuplicateError
        label = self.create_label(
            name=data["name"].strip(),
            color=data["color"].strip(),
            description=data.get("description"),
            keywords=data.get("keywords") or [],
            prompt_hint=data.get("prompt_hint"),
            parent_id=data.get("parent_id"),
            tenant_id=user["tenant_id"],
            created_by=user["email"],
        )
        return self.repo.create(label)

    async def list_smart_labels(self, tenant_id: str, skip: int, limit: int) -> SmartLabelListResult:
        return SmartLabelListResult(
            items=self.repo.list_all(tenant_id, skip, limit),
            total=self.repo.count(tenant_id),
            skip=skip,
            limit=limit,
        )

    async def get_smart_label(self, label_id: str, tenant_id: str) -> Any:
        label = self.repo.get_by_id(label_id, tenant_id)
        if not label:
            raise SmartLabelNotFoundError
        return label

    async def update_smart_label(self, label_id: str, data: dict[str, Any], user: dict[str, Any]) -> Any:
        label = await self.get_smart_label(label_id, user["tenant_id"])
        if "name" in data:
            new_parent_id = data.get("parent_id", label.parent_id)
            existing = self.repo.get_by_name(data["name"], user["tenant_id"], new_parent_id)
            if existing and existing.id != label_id:
                raise SmartLabelDuplicateError
        for key, value in data.items():
            setattr(label, key, value)
        label.updated_by = user["email"]
        return self.repo.update(label)

    async def delete_smart_label(self, label_id: str, tenant_id: str) -> None:
        label = await self.get_smart_label(label_id, tenant_id)
        try:
            self.repo.delete(label)
        except ValueError as exc:
            raise SmartLabelDeleteError(str(exc)) from exc
