"""User use cases — business logic layer."""

from typing import Optional
from sqlalchemy.orm import Session

from app.domain.entities.user import User
from app.infrastructure.persistence.user_repository import UserRepository


class UpdateProfileUseCase:
    """Update current user's own profile."""

    def __init__(self, db: Session):
        self.user_repository = UserRepository(db)

    def execute(self, user_id: str, **fields) -> User:
        """Update profile fields — raises ValueError if user not found."""
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        for key, value in fields.items():
            if value is not None and hasattr(user, key):
                setattr(user, key, value)

        return self.user_repository.update(user)


class ListUsersUseCase:
    """List all users in a tenant."""

    def __init__(self, db: Session):
        self.user_repository = UserRepository(db)

    def execute(
        self, tenant_id: str, skip: int = 0, limit: int = 50
    ) -> tuple[list[User], int]:
        """Return (users, total_count)."""
        return self.user_repository.list_by_tenant(tenant_id, skip, limit)


class CreateUserByAdminUseCase:
    """Create a user — admin action."""

    def __init__(self, db: Session):
        self.user_repository = UserRepository(db)

    def execute(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        tenant_id: str = "default",
        role: str = "member",
        job_title: Optional[str] = None,
        phone: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> User:
        """Create user — raises ValueError if email already exists."""
        email_normalized = email.strip().lower()
        existing = self.user_repository.get_by_email(email_normalized)
        if existing:
            raise ValueError("A user with this email already exists")

        user = User(
            email=email_normalized,
            password_hash=User.hash_password(password),
            first_name=first_name,
            last_name=last_name,
            tenant_id=tenant_id,
            role=role,
            job_title=job_title,
            phone=phone,
            created_by=created_by or "admin",
        )
        return self.user_repository.create(user)
