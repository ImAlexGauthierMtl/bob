# Template: Configuration Database (Infrastructure)

> Recette pour configurer la connexion à la base de données.
> **Zéro décision** : suivre exactement ce pattern.

## Fichier à créer

`app/infrastructure/database.py`

## Code exact

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import os

# SQLite pour développement, PostgreSQL pour production
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency pour obtenir une session de base de données."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## Variante shared library (multi-API)

`shared/database/connection.py`

```python
"""Database connection management for shared library."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from ..config.settings import get_settings


def create_db_engine(api_name: str = None):
    """Create database engine from settings."""
    settings = get_settings(api_name)
    database_url = settings.database_url or f"sqlite:///./{api_name or 'app'}.db"
    connect_args = {"check_same_thread": False} if "sqlite" in database_url else {}
    return create_engine(database_url, connect_args=connect_args)


def create_session_factory(api_name: str = None):
    """Create session factory."""
    engine = create_db_engine(api_name)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db(api_name: str = None) -> Generator[Session, None, None]:
    """Dependency pour obtenir une session DB."""
    SessionLocal = create_session_factory(api_name)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

`shared/database/base.py`

```python
"""Declarative base for all models."""

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
```

## Règles NON-NÉGOCIABLES

1. `check_same_thread=False` uniquement pour SQLite
2. `autocommit=False, autoflush=False` TOUJOURS
3. `get_db()` est un generator (yield) pour cleanup automatique
4. URL depuis variable d'environnement `DATABASE_URL`
5. Base déclarative dans `shared/database/base.py` (partagée entre APIs)
