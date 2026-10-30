"""Aplicación FastAPI. El lifespan es el único lugar donde se construyen recursos."""

import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import Settings
from app.core.database import crear_engine, crear_sessionmaker
from app.core.security import hash_password
from app.modules.clientes import models as clientes_models  # noqa: F401
from app.modules.clientes.router import (
    clientes_router,
    mis_vehiculos_router,
    vehiculos_router,
)
from app.modules.health.router import router as health_router
from app.modules.ordenes import models as ordenes_models  # noqa: F401
from app.modules.repuestos import models as repuestos_models  # noqa: F401
from app.modules.repuestos.router import router as repuestos_router
from app.modules.usuarios import models as usuarios_models  # noqa: F401
from app.modules.usuarios.router import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings()
    engine = crear_engine(settings)
    app.state.settings = settings
    app.state.engine = engine
    app.state.sessionmaker = crear_sessionmaker(engine)
    app.state.hash_ficticio = await hash_password(secrets.token_urlsafe(32), settings.BCRYPT_COST)
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="Taller Mecánico", lifespan=lifespan)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(repuestos_router)
app.include_router(clientes_router)
app.include_router(vehiculos_router)
app.include_router(mis_vehiculos_router)
