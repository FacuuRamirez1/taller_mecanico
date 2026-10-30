"""Salud del servicio. Excepción documentada: sin service/UoW/repository."""

import asyncio

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionDep

router = APIRouter(prefix="/health", tags=["health"])

TIMEOUT_READY_SEGUNDOS = 3


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(session: SessionDep) -> dict[str, str]:
    try:
        await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=TIMEOUT_READY_SEGUNDOS)
    except (SQLAlchemyError, OSError, TimeoutError):
        raise HTTPException(status_code=503, detail="La base de datos no responde") from None
    return {"status": "ok"}
