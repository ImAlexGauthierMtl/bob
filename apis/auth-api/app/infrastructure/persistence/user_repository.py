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
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(
            User.id == user_id,
            User.is_deleted == False,
        ).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(
            func.lower(User.email) == func.lower(email),
            User.is_deleted == False,
        ).first()

    def update(self, user: User) -> User:
        user.version += 1
        self.db.commit()
        self.db.refresh(user)
        return user

    def list_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 50
    ) -> tuple[List[User], int]:
        query = self.db.query(User).filter(
            User.tenant_id == tenant_id,
            User.is_deleted == False,
        )
        total = query.count()
        users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
        return users, total

    def soft_delete(self, user_id: str) -> bool:
        user = self.get_by_id(user_id)
        if not user:
            return False
        user.is_deleted = True
        user.version += 1
        self.db.commit()
        return True
