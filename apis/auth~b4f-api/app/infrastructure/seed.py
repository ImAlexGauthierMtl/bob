"""Seed script — creates default admin user."""

from shared.infrastructure import get_logger
from sqlalchemy.orm import Session

from app.config import settings
from app.domain.entities.user import User
from app.infrastructure.persistence.user_repository import UserRepository

logger = get_logger(__name__)


def seed_admin_user(db: Session) -> None:
    """Create default admin user if it doesn't exist."""
    repo = UserRepository(db)
    existing = repo.get_by_email(settings.admin_email.lower())
    if existing:
        logger.info("admin_exists", email=settings.admin_email)
        return

    admin = User(
        email=settings.admin_email.lower(),
        password_hash=User.hash_password(settings.admin_password),
        first_name=settings.admin_first_name,
        last_name=settings.admin_last_name,
        role="admin",
        created_by="system-seed",
    )
    created = repo.create(admin)
    logger.info("admin_created", email=created.email, id=created.id)


def run_seed(db: Session) -> None:
    """Run all seed operations."""
    seed_admin_user(db)
