"""Database connection — delegates to shared library."""

from shared.database import create_db_engine, create_session_factory, get_db as _get_db
from sqlalchemy.orm import Session
from typing import Generator

_API_NAME = "auth"

engine = create_db_engine(_API_NAME)
SessionLocal = create_session_factory(_API_NAME)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — get DB session."""
    yield from _get_db(_API_NAME)
