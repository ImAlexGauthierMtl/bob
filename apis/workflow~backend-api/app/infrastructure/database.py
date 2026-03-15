"""Database connection — delegates to shared library (lazy init)."""
from shared.database import create_db_engine, create_session_factory, get_db as _get_db
from sqlalchemy.orm import Session
from typing import Generator

_API_NAME = None

def init(api_name: str):
    global _API_NAME
    _API_NAME = api_name

def get_engine():
    return create_db_engine(_API_NAME)

def get_session_factory():
    return create_session_factory(_API_NAME)

def get_db() -> Generator[Session, None, None]:
    yield from _get_db(_API_NAME)
