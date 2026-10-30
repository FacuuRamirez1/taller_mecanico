"""Entorno de Alembic — plantilla ASINCRÓNICA.

TODO C-01: `app/core/config.py` todavía NO existe. Este módulo importa
`Settings` desde allí a propósito: cualquier comando de Alembic que cargue
este archivo falla fuerte con `ModuleNotFoundError: No module named
'app.core.config'` hasta que C-01 cree ese módulo. Es el comportamiento
esperado y documentado (design.md §D1, env.example, tasks.md 4.2).

No agregar fallbacks, URLs por defecto ni lecturas directas de os.environ:
la URL sale siempre de Settings.DATABASE_URL, igual que en la aplicación.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel

from app.core.config import Settings  # TODO C-01: crear app/core/config.py

# TODO C-02: importar los modelos de cada módulo para que `SQLModel.metadata`
# los conozca (p. ej. `from app.modules.usuarios import models  # noqa: F401`).
# Sin esos imports, `alembic revision --autogenerate` genera una migración vacía.

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = Settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

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
