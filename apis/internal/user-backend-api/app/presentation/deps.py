"""Presentation dependencies for User API."""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.use_cases.role_use_cases import RoleUseCases
from app.application.use_cases.tenant_use_cases import TenantUseCases
from app.application.use_cases.user_use_cases import UserUseCases
from app.events.publishers import publish_user_created, publish_user_deleted, publish_user_updated
from app.infrastructure.database import get_db
from app.infrastructure.persistence.models.role import Role
from app.infrastructure.persistence.models.user import User
from app.infrastructure.persistence.role_repository import RoleRepository
from app.infrastructure.persistence.tenant_repository import TenantRepository
from app.infrastructure.persistence.user_repository import UserRepository


def get_user_use_cases(db: Session = Depends(get_db)) -> UserUseCases:
    return UserUseCases(
        user_repo=UserRepository(db),
        role_repo=RoleRepository(db),
        create_user_entity=User,
        hash_password=User.hash_password,
        publish_created=publish_user_created,
        publish_updated=publish_user_updated,
        publish_deleted=publish_user_deleted,
    )


def get_tenant_use_cases(db: Session = Depends(get_db)) -> TenantUseCases:
    return TenantUseCases(repo=TenantRepository(db))


def get_role_use_cases(db: Session = Depends(get_db)) -> RoleUseCases:
    return RoleUseCases(
        repo=RoleRepository(db),
        create_role_entity=Role,
        refresh_role=db.refresh,
    )
