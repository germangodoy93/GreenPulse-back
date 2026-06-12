"""Alembic environment configuration with async SQLAlchemy support.

Reads DATABASE_URL from application settings so the same .env file is the
single source of truth for all connection strings.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ── Model registry ────────────────────────────────────────────────────────────
# Import Base first, then the central registry that imports all models.
# This populates Base.metadata so Alembic can detect schema changes.
from src.infrastructure.database.base import Base  # noqa: E402
import src.infrastructure.database.registry  # noqa: E402, F401

# ── Settings ──────────────────────────────────────────────────────────────────
from config.settings import get_settings  # noqa: E402

_app_settings = get_settings()

# ── Alembic config ────────────────────────────────────────────────────────────
alembic_config = context.config
alembic_config.set_main_option("sqlalchemy.url", _app_settings.DATABASE_URL)

if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

target_metadata = Base.metadata


# ── Migration runners ─────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """Generate SQL scripts without a live DB connection (CI / review)."""
    url = alembic_config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Connect to the DB asynchronously and run pending migrations."""
    connectable = async_engine_from_config(
        alembic_config.get_section(alembic_config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
