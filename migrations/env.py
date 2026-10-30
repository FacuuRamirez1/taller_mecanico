"""Entorno de Alembic — plantilla ASINCRÓNICA.

La URL sale siempre de `Settings.DATABASE_URL`, igual que en la aplicación:
sin fallbacks, URLs por defecto ni lecturas directas de os.environ. Si faltan
secretos, Alembic falla con el mismo `ValidationError` que uvicorn.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel

from app.core.config import Settings

# TODO C-02: importar los modelos de cada módulo para que `SQLModel.metadata`
# los conozca (p. ej. `from app.modules.usuarios import models  # noqa: F401`).
# Sin esos imports, `alembic revision --autogenerate` genera una migración vacía.

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = Settings()
# configparser interpola `%`: se duplica para conservar la URL escapada (%40, etc.)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Corre las migraciones en modo 'offline' (genera SQL sin conectar)."""
    url = config.get_main_option("sqlalchemy.url")
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
    """Configura el contexto sobre una conexión ya abierta."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Crea un motor asincrónico y corre las migraciones dentro de él."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Punto de entrada del modo 'online': delega en el motor asincrónico."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
