"""Alembic environment configuration for the auth_service.

This module configures Alembic to run migrations in both offline and online
modes. It reads the database URL from the environment variable
``DATABASE_URL`` (optionally loaded from a ``.env`` file).

The module exposes two helper functions used by the Alembic command
dispatcher: :func:`run_migrations_offline` and :func:`run_migrations_online`.
"""

from __future__ import annotations

import os

from models import Base
from dotenv import load_dotenv
from alembic import context
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool

load_dotenv()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = Base.metadata

ENV_DB_KEY = "DATABASE_URL"

database_url = os.getenv(ENV_DB_KEY)
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)
else:
    raise ValueError(f"{ENV_DB_KEY} is not set in the environment variables.")


def run_migrations_offline() -> None:
    """Run Alembic migrations in offline mode.

    Offline mode generates SQL statements without an active database
    connection. The database URL is taken from the Alembic configuration.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run Alembic migrations in online mode.

    Online mode establishes a database connection and applies migrations
    directly against that connection.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
