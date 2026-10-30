"""Base del patrón Unit of Work (design §D1, C-06).

El Unit of Work coordina las transacciones atómicas.
- Se utiliza como gestor de contexto asincrónico (`async with uow:`).
- Al salir del bloque sin excepciones, confirma (`commit`).
- Si ocurre cualquier excepción dentro del bloque, revierte (`rollback`).
- NO construye la sesión (la recibe del router/dependencia).
- NO cierra la sesión (el cierre corresponde a `get_session`).
- Captura `IntegrityError` en el commit y lo traduce mediante `traducir_integrity_error`.
"""

from types import TracebackType
from typing import Self

from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.errores import traducir_integrity_error


class AbstractUnitOfWork:
    """Clase base de Unit of Work asincrónico para SQLAlchemy/SQLModel."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._committed = False

    async def __aenter__(self) -> Self:
        self._committed = False
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
        elif not self._committed:
            await self.commit()

    async def commit(self) -> None:
        """Confirma la transacción actual. Traduce IntegrityError a HTTPException 409."""
        try:
            await self.session.commit()
            self._committed = True
        except IntegrityError as exc:
            await self.session.rollback()
            raise traducir_integrity_error(exc) from None

    async def rollback(self) -> None:
        """Revierte la transacción actual."""
        await self.session.rollback()

