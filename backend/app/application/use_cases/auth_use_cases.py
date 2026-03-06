"""Authentication use cases."""

from typing import Optional
from sqlalchemy.orm import Session

from app.domain.entities.user import User
from app.infrastructure.persistence.user_repository import UserRepository


class AuthenticateUserUseCase:
    """Authenticate a user with email and password."""

    def __init__(self, db: Session):
        self.user_repository = UserRepository(db)

    def execute(self, email: str, password: str) -> Optional[User]:
        """Authenticate — returns User if valid, None otherwise."""
        user = self.user_repository.get_by_email(email.strip().lower())
        if not user:
            return None
        if not user.verify_password(password):
            return None
        return user


class RegisterUserUseCase:
    """Register a new user."""

    def __init__(self, db: Session):
        self.user_repository = UserRepository(db)

    def execute(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        tenant_id: str = "default",
        created_by: Optional[str] = None,
    ) -> User:
        """Register — raises ValueError if email exists."""
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
            created_by=created_by or "system",
        )
        return self.user_repository.create(user)
