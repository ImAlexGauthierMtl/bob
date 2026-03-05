# Template: Seed Data (données initiales)

> Recette pour créer un script de seed idempotent.
> **Zéro décision** : suivre exactement ce pattern.

## Input requis

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `API_NAME` | Nom de l'API | `auth-api` |
| `DEFAULT_ADMIN_EMAIL` | Email admin | `admin@company.com` |

## Fichier à créer

`app/infrastructure/seed.py`

```python
"""Seed script — creates default data."""
import os
import logging
from sqlalchemy.orm import Session
from app.domain.entities.user import User
from app.infrastructure.persistence.user_repository import UserRepository

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "{DEFAULT_ADMIN_EMAIL}")
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin123!")
DEFAULT_ADMIN_FIRST_NAME = os.getenv("ADMIN_FIRST_NAME", "Admin")
DEFAULT_ADMIN_LAST_NAME = os.getenv("ADMIN_LAST_NAME", "System")


def seed_admin_user(db: Session) -> None:
    """Create default admin user if it doesn't exist (idempotent)."""
    repo = UserRepository(db)
    existing = repo.get_by_email(DEFAULT_ADMIN_EMAIL.lower())
    if existing:
        logger.info(f"Admin user {DEFAULT_ADMIN_EMAIL} already exists, skipping.")
        return

    admin = User(
        email=DEFAULT_ADMIN_EMAIL.lower(),
        password_hash=User.hash_password(DEFAULT_ADMIN_PASSWORD),
        first_name=DEFAULT_ADMIN_FIRST_NAME,
        last_name=DEFAULT_ADMIN_LAST_NAME,
        created_by="system-seed"
    )
    created = repo.create(admin)
    logger.info(f"Admin user created: {created.email} (id={created.id})")


def run_seed(db: Session) -> None:
    """Run all seed operations."""
    seed_admin_user(db)
    # Ajouter d'autres seeds ici
```

## Appeler le seed dans `main.py`

```python
# In main.py, after database init
from app.infrastructure.seed import run_seed
db = SessionLocal()
try:
    run_seed(db)
finally:
    db.close()
```

## Règles NON-NÉGOCIABLES

1. Seed TOUJOURS idempotent — vérifier si l'objet existe avant de créer
2. Credentials admin via variables d'environnement
3. Password hashé avec bcrypt — jamais en clair dans le code
4. `created_by="system-seed"` pour la traçabilité
5. Un seul point d'entrée `run_seed()` qui appelle toutes les fonctions
