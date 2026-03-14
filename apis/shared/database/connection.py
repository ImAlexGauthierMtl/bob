"""Database connection management for shared library."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Optional
from ..config import get_settings


_engines = {}
_session_factories = {}


def create_db_engine(api_name: Optional[str] = None):
    """Create or return cached database engine from settings."""
    cache_key = api_name or "__default__"
    if cache_key not in _engines:
        settings = get_settings(api_name)
        database_url = settings.database_url
        if not database_url:
            raise ValueError(f"DATABASE_URL not configured for {api_name or 'default'}")

        connect_args = {}
        if "sqlite" in database_url:
            connect_args["check_same_thread"] = False

        _engines[cache_key] = create_engine(
            database_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args=connect_args,
        )
    return _engines[cache_key]


def create_session_factory(api_name: Optional[str] = None):
    """Create or return cached session factory."""
    cache_key = api_name or "__default__"
    if cache_key not in _session_factories:
        engine = create_db_engine(api_name)
        _session_factories[cache_key] = sessionmaker(
            autocommit=False, autoflush=False, bind=engine
        )
    return _session_factories[cache_key]


def get_db(api_name: Optional[str] = None) -> Generator[Session, None, None]:
    """FastAPI dependency to get a database session."""
    SessionLocal = create_session_factory(api_name)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
