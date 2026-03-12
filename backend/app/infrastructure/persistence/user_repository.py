"""User repository — data access layer."""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.domain.entities.user import User


class UserRepository:
    """Repository for user data access."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, user: User) -> User:
        """Create a new user."""
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(
            User.id == user_id,
            User.is_deleted == False,
        ).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email (case-insensitive)."""
        return self.db.query(User).filter(
            func.lower(User.email) == func.lower(email),
            User.is_deleted == False,
        ).first()

    def update(self, user: User) -> User:
        """Update a user."""
        user.version += 1
        self.db.commit()
        self.db.refresh(user)
        return user

    def list_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 50
    ) -> tuple[List[User], int]:
        """List users for a tenant with pagination."""
        query = self.db.query(User).filter(
            User.tenant_id == tenant_id,
            User.is_deleted == False,
        )
        total = query.count()
        users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
        return users, total

    def soft_delete(self, user_id: str) -> bool:
        """Soft-delete a user. Returns True if found."""
        user = self.get_by_id(user_id)
        if not user:
            return False
        user.is_deleted = True
        user.version += 1
        self.db.commit()
        return True
