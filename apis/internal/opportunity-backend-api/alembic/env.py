import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text
from alembic import context

# Add parent paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', '..'))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url from environment
database_url = os.environ.get("DATABASE_URL", "")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# Import your models' MetaData here for autogenerate support
# from app.infrastructure.database import Base
# target_metadata = Base.metadata
target_metadata = None

# Schema name derived from API directory name
SCHEMA_NAME = os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))).replace("-backend-api", "")


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=SCHEMA_NAME,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.execute(f"CREATE SCHEMA IF NOT EXISTS \"{SCHEMA_NAME}\"")
        context.execute(f'SET search_path TO "{SCHEMA_NAME}"')
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS \"{SCHEMA_NAME}\""))
        connection.execute(text(f'SET search_path TO "{SCHEMA_NAME}"'))
        connection.commit()
        
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=SCHEMA_NAME,
            include_schemas=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
