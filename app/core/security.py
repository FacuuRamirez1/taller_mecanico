"""Hash de contraseñas con bcrypt, fuera del bucle de eventos.

bcrypt es CPU-bound: corre en `asyncio.to_thread` bajo un semáforo.
El semáforo se crea perezosamente (dentro del bucle), nunca al importar.
La longitud máxima de la contraseña (72 bytes) la valida el schema de C-04.
"""

import asyncio

import bcrypt

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
