import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from services.telemetry.app.config import get_settings
from services.telemetry.app.db import Base
from services.telemetry.app import models  # noqa: F401  (register models on Base.metadata)

config = context.config

config.set_main_option("sqlalchemy.url", get_settings().database_url)

# path to the .ini that Alembic loaded
# ex. services/telemetry/alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    # "offline" means without real connection to db
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool, # do not need a connection pool for one-time migrations
    )

    async with connectable.connect() as connection:
        # migration cannot be async yet, so we run it sync
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    # "online" means with real connection to db
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    # for ex. `alembic upgrade head --sql`
    run_migrations_offline()
else:
    run_migrations_online()
