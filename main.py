"""Aplicación FastAPI. El lifespan es el único lugar donde se construyen recursos."""

import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import Settings
from app.core.database import crear_engine, crear_sessionmaker
from app.core.security import hash_password
from app.modules.health.router import router as health_router


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
