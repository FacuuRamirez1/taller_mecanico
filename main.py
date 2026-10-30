"""Aplicación FastAPI. El lifespan es el único lugar donde se construyen recursos."""

import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI

from app.core.config import Settings
from app.core.database import crear_engine, crear_sessionmaker
from app.core.dependencies import get_usuario_activo
from app.core.security import hash_password
from app.modules.clientes import models as clientes_models  # noqa: F401
from app.modules.clientes.router import (
    clientes_router,
    mis_vehiculos_router,
    vehiculos_router,
)
from app.modules.health.router import router as health_router
from app.modules.ordenes import models as ordenes_models  # noqa: F401
from app.modules.ordenes.router import (
    estados_router,
    mis_ordenes_router,
    ordenes_router,
)
from app.modules.repuestos import models as repuestos_models  # noqa: F401
from app.modules.repuestos.router import router as repuestos_router
from app.modules.usuarios import models as usuarios_models  # noqa: F401
from app.modules.usuarios.router import (
    eventos_router,
    router as auth_router,
    usuarios_router,
)


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

# Grupo abierto: salud y autenticación
app.include_router(health_router)
app.include_router(auth_router)

# Grupo protegido: requiere sesión válida y que no tenga cambio de contraseña pendiente (RN-06)
protegido_router = APIRouter(dependencies=[Depends(get_usuario_activo)])
protegido_router.include_router(usuarios_router)
protegido_router.include_router(eventos_router)
protegido_router.include_router(repuestos_router)
protegido_router.include_router(clientes_router)
protegido_router.include_router(vehiculos_router)
protegido_router.include_router(mis_vehiculos_router)
protegido_router.include_router(ordenes_router)
protegido_router.include_router(estados_router)
protegido_router.include_router(mis_ordenes_router)

app.include_router(protegido_router)
