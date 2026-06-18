"""Database connection management for shared library."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Optional
from ..config import get_settings


_engines = {}
_session_factories = {}
MAX_POOL_SIZE = 5
DEFAULT_POOL_SIZE = 3
DEFAULT_MAX_OVERFLOW = 5


def _bounded_int_from_env(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(value, maximum))


def _connect_args_for_database_url(database_url: str) -> dict:
    connect_args = {}
    if "sqlite" in database_url:
        connect_args["check_same_thread"] = False
    if database_url.startswith("postgresql+psycopg://"):
        connect_args["prepare_threshold"] = None
    return connect_args


def create_db_engine(api_name: Optional[str] = None):
    """Create or return cached database engine from settings."""
    cache_key = api_name or "__default__"
    if cache_key not in _engines:
        settings = get_settings(api_name)
        database_url = settings.database_url
        if not database_url:
            raise ValueError(f"DATABASE_URL not configured for {api_name or 'default'}")

        connect_args = _connect_args_for_database_url(database_url)
        pool_size = _bounded_int_from_env(
            "DB_POOL_SIZE", DEFAULT_POOL_SIZE, 1, MAX_POOL_SIZE
        )
        max_overflow = _bounded_int_from_env(
            "DB_MAX_OVERFLOW", DEFAULT_MAX_OVERFLOW, 0, MAX_POOL_SIZE
        )

        _engines[cache_key] = create_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
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
