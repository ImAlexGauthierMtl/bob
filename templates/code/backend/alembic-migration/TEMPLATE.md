# Template: Migration Alembic

> Recette pour configurer et créer des migrations Alembic.
> **Zéro décision** : suivre exactement ce pattern.

## Input requis

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `API_NAME` | Nom de l'API (kebab-case) | `clients-backend-api` |
| `TABLE` | Nom de la table à migrer | `clients` |

## Fichiers à créer/modifier

### 1. `alembic.ini`

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = sqlite:///./app.db

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### 2. `alembic/env.py`

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# Ajouter le répertoire racine au path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)

# Import de la base et des modèles
from shared.database.base import Base
# IMPORTANT: importer TOUS les modèles pour autogenerate
from app.domain.entities.{resource} import {Resource}

# Alembic Config
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Définir l'URL depuis l'environnement
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))

# Detect database type
is_postgresql = "postgresql" in DATABASE_URL

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        version_table="alembic_version_{api_name_snake}",
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table="alembic_version_{api_name_snake}",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### 3. `migrate.sh`

```bash
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate 2>/dev/null || true

if [ "$1" == "create" ]; then
    alembic revision --autogenerate -m "$2"
elif [ "$1" == "up" ]; then
    alembic upgrade head
elif [ "$1" == "down" ]; then
    alembic downgrade -1
else
    echo "Usage: ./migrate.sh [create 'message' | up | down]"
fi
```

## Commandes courantes

```bash
# Créer une migration
alembic revision --autogenerate -m "add {table} table"

# Appliquer les migrations
alembic upgrade head

# Rollback 1 migration
alembic downgrade -1

# Voir l'historique
alembic history
```

## Règles NON-NÉGOCIABLES

1. TOUJOURS importer tous les modèles dans `env.py` pour que autogenerate fonctionne
2. `version_table` unique par API pour éviter les conflits en base partagée
3. Escape `%` en `%%` dans l'URL pour configparser
4. Convention de nommage : `YYYYMMDD_NNNNNN_description.py`
5. Tester la migration sur SQLite avant de déployer sur PostgreSQL
