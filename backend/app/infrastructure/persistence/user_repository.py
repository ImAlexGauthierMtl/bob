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
