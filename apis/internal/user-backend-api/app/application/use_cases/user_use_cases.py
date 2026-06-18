"""User application use cases."""
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Protocol

from app.domain.exceptions import UserAlreadyExistsError, UserNotFoundError


UserEntity = Any
RoleEntity = Any
UserFactory = Callable[..., UserEntity]
PasswordHasher = Callable[[str], str]
UserPublisher = Callable[[str, dict[str, Any]], Awaitable[None]]
UserDeletedPublisher = Callable[[str], Awaitable[None]]


class UserRepositoryPort(Protocol):
    def create(self, user: UserEntity) -> UserEntity:
        ...

    def get_by_id(self, user_id: str) -> Optional[UserEntity]:
        ...

    def get_by_email(self, email: str) -> Optional[UserEntity]:
        ...

    def update(self, user: UserEntity) -> UserEntity:
        ...

    def list_by_tenant(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[UserEntity], int]:
        ...

    def soft_delete(self, user_id: str) -> bool:
        ...


class RoleRepositoryPort(Protocol):
    def get_role_by_name(self, name: str, tenant_id: str) -> Optional[RoleEntity]:
        ...

    def assign_role_to_user(self, user_id: str, role_id: str) -> None:
        ...


@dataclass(frozen=True)
class UserListResult:
    items: list[UserEntity]
    total: int
    skip: int
    limit: int


class UserUseCases:
    def __init__(
        self,
        user_repo: UserRepositoryPort,
        role_repo: RoleRepositoryPort,
        create_user_entity: UserFactory,
        hash_password: PasswordHasher,
        publish_created: UserPublisher,
        publish_updated: UserPublisher,
        publish_deleted: UserDeletedPublisher,
    ) -> None:
        self.user_repo = user_repo
        self.role_repo = role_repo
        self.create_user_entity = create_user_entity
        self.hash_password = hash_password
        self.publish_created = publish_created
        self.publish_updated = publish_updated
        self.publish_deleted = publish_deleted

    async def list_users(self, tenant_id: str, skip: int, limit: int) -> UserListResult:
        users, total = self.user_repo.list_by_tenant(tenant_id, skip, limit)
        return UserListResult(items=users, total=total, skip=skip, limit=limit)

    async def get_user(self, user_id: str) -> UserEntity:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError
        return user

    async def get_user_by_email(self, email: str) -> UserEntity:
        user = self.user_repo.get_by_email(email)
        if not user:
            raise UserNotFoundError
        return user

    async def create_user(self, data: dict[str, Any]) -> UserEntity:
        email = data["email"].lower()
        existing = self.user_repo.get_by_email(email)
        if existing:
            raise UserAlreadyExistsError

        role_name = data.get("role") or "member"
        tenant_id = data.get("tenant_id") or "default"
        user = self.create_user_entity(
            email=email,
            password_hash=self.hash_password(data["password"]),
            first_name=data["first_name"],
            last_name=data["last_name"],
            tenant_id=tenant_id,
            role=role_name,
            is_super_admin=data.get("is_super_admin") or False,
            job_title=data.get("job_title"),
            phone=data.get("phone"),
            created_by=data.get("created_by") or "system",
            active_organization_id=data.get("active_organization_id"),
        )
        created = self.user_repo.create(user)

        matching_role = self.role_repo.get_role_by_name(role_name, tenant_id)
        if matching_role:
            self.role_repo.assign_role_to_user(created.id, matching_role.id)

        await self.publish_created(
            created.id,
            {"email": created.email, "tenant_id": created.tenant_id},
        )
        return created

    async def update_user(
        self,
        user_id: str,
        updates: dict[str, Any],
        current_user: dict[str, Any],
    ) -> UserEntity:
        user = await self.get_user(user_id)
        password_raw = updates.pop("password", None)
        for key, value in updates.items():
            if hasattr(user, key):
                setattr(user, key, value)
        if password_raw:
            user.password_hash = self.hash_password(password_raw)
        user.updated_by = current_user.get("email")
        updated = self.user_repo.update(user)
        await self.publish_updated(
            updated.id,
            {"email": updated.email, "fields": list(updates.keys())},
        )
        return updated

    async def delete_user(self, user_id: str) -> None:
        deleted = self.user_repo.soft_delete(user_id)
        if not deleted:
            raise UserNotFoundError
        await self.publish_deleted(user_id)

    async def verify_password(self, email: str, password: str) -> dict[str, bool]:
        user = self.user_repo.get_by_email(email.lower())
        if not user:
            return {"valid": False}
        return {"valid": user.verify_password(password)}
