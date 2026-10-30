"""Hash de contraseñas con bcrypt y manejo de tokens JWT HS256.

bcrypt es CPU-bound: corre en `asyncio.to_thread` bajo un semáforo.
El semáforo se crea perezosamente (dentro del bucle), nunca al importar.
La longitud máxima de la contraseña (72 bytes) la validan los schemas.
El token JWT viaja sólo en cookie HttpOnly, con iat sin truncar a segundos.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import HTTPException, status

from app.core.config import Settings

MAX_BCRYPT_CONCURRENTES = 4

_semaforo_bcrypt: asyncio.Semaphore | None = None


def _semaforo() -> asyncio.Semaphore:
    global _semaforo_bcrypt
    if _semaforo_bcrypt is None:
        _semaforo_bcrypt = asyncio.Semaphore(MAX_BCRYPT_CONCURRENTES)
    return _semaforo_bcrypt


def _hashear(password: str, cost: int) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=cost)).decode("ascii")


def _verificar(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


async def hash_password(password: str, cost: int) -> str:
    async with _semaforo():
        return await asyncio.to_thread(_hashear, password, cost)


async def verify_password(password: str, password_hash: str) -> bool:
    async with _semaforo():
        return await asyncio.to_thread(_verificar, password, password_hash)


def crear_token_acceso(
    usuario_id: int,
    roles: list[str],
    settings: Settings,
    iat: datetime | None = None,
) -> str:
    """Emite un token JWT HS256 con iat de precisión completa (con fracciones)."""
    ahora = iat if iat is not None else datetime.now(timezone.utc)
    exp = ahora + timedelta(seconds=settings.JWT_EXPIRE_SECONDS)
    payload: dict[str, Any] = {
        "sub": str(usuario_id),
        "roles": roles,
        "iat": ahora.timestamp(),
        "exp": exp.timestamp(),
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


def decodificar_token_acceso(token: str, settings: Settings) -> dict[str, Any]:
    """Valida la firma y vigencia del token. Devuelve el payload o lanza 401."""
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY.get_secret_value(),
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_iat": False},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        ) from exc
