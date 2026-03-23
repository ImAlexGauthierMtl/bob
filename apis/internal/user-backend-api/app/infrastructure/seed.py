"""Seed script — creates default admin user."""
from shared.infrastructure import get_logger
from shared.config import get_settings
from sqlalchemy.orm import Session
from app.domain.entities.user import User
from app.infrastructure.persistence.user_repository import UserRepository

logger = get_logger(__name__)
settings = get_settings("user-backend")

def seed_admin_user(db: Session) -> None:
    repo = UserRepository(db)
    existing = repo.get_by_email(settings.admin_email.lower())
    if existing:
        logger.info("admin_exists", email=settings.admin_email)
        return
    admin = User(
        email=settings.admin_email.lower(),
        password_hash=User.hash_password(settings.admin_password or "changeme123"),
        first_name=settings.admin_first_name,
        last_name=settings.admin_last_name,
        role="admin",
        created_by="system-seed",
    )
    repo.create(admin)
    logger.info("admin_created", email=admin.email, id=admin.id)

def run_seed(db: Session) -> None:
    seed_admin_user(db)
