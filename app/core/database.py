"""Motor y sesión asincrónicos.

Sólo fábricas puras y el alias `SessionDep`: nada se construye al importar.
El engine y el sessionmaker los crea el lifespan (main.py) y viven en `app.state`.
`get_session` no confirma ni revierte: la confirmación de la transacción es del UoW.
"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import Settings


def crear_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        echo=settings.SQL_ECHO,
        pool_pre_ping=True,
    )


def crear_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
