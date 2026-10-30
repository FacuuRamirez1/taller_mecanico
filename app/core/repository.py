"""Clases base de repositorios (design §D1, C-06).

`BaseRepository[T]` recibe en su constructor la sesión de SQLAlchemy/SQLModel y
la clase del modelo en runtime (`model_cls`).
Sus métodos de escritura (`add`, `update`, `delete`, `soft_delete`) ejecutan
exclusivamente `flush()` y NUNCA `commit()`. La transacción la gestiona el UnitOfWork.

`SoftDeleteRepository[T]` especializa para entidades con borrado lógico (`vehiculo`, `repuesto`),
filtrando en lecturas normales las filas con `borrado_en IS NULL` y proveyendo
`soft_delete` y `get_by_id_including_deleted`.
"""

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.errores import traducir_integrity_error
from app.core.paginacion import Pagina, paginar

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Repositorio genérico base para operaciones CRUD sobre una entidad."""

    def __init__(self, session: AsyncSession, model_cls: type[T]) -> None:
        self.session = session
        self.model_cls = model_cls

    async def _flush(self) -> None:
        """`flush` propio: traduce `IntegrityError` a un código de negocio, nunca 500.

        Las restricciones (UNIQUE, CHECK, FK) se validan en el `flush`, no sólo en el
        `commit`; por eso la traducción vive acá y no únicamente en el UnitOfWork.
        Quien llame debe dejar que la excepción salga del `async with` del UoW para
        que la transacción se revierta.
        """
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise traducir_integrity_error(exc) from None

    async def get_by_id(self, id: int) -> T | None:
        """Obtiene una entidad por su clave primaria."""
        sentencia = select(self.model_cls).where(getattr(self.model_cls, "id") == id)
        res = await self.session.execute(sentencia)
        return res.scalar_one_or_none()

    async def get_all(self) -> list[T]:
        """Obtiene todas las entidades."""
        sentencia = select(self.model_cls).order_by(getattr(self.model_cls, "id").asc())
        res = await self.session.execute(sentencia)
        return list(res.scalars().all())

    async def count(self) -> int:
        """Cuenta el total de filas de la entidad."""
        sentencia = select(func.count()).select_from(self.model_cls)
        total = await self.session.scalar(sentencia)
        return int(total or 0)

    async def paginar(
        self,
        sentencia: Select[Any],
        page: int,
        size: int,
    ) -> Pagina[Any]:
        """Pagina una consulta sin exponer la sesión al servicio.

        El servicio arma la sentencia con un método `consulta_*` del repositorio
        y le pide al mismo repositorio el envoltorio `{items, total, page, size, pages}`.
        """
        return await paginar(self.session, sentencia, page, size)

    async def add(self, entity: T) -> T:
        """Añade la entidad a la sesión y hace flush para generar IDs y validar constraints."""
        self.session.add(entity)
        await self._flush()
        return entity

    async def update(self, entity: T) -> T:
        """Marca la entidad para actualización y hace flush."""
        self.session.add(entity)
        await self._flush()
        return entity

    async def delete(self, entity: T) -> None:
        """Elimina físicamente la entidad de la sesión y hace flush."""
        await self.session.delete(entity)
        await self._flush()


class SoftDeleteRepository(BaseRepository[T]):
    """Repositorio base para entidades que implementan borrado lógico con `borrado_en`."""

    async def get_by_id(self, id: int) -> T | None:
        """Obtiene una entidad por su ID sólo si no está borrada lógicamente."""
        sentencia = select(self.model_cls).where(
            getattr(self.model_cls, "id") == id,
            getattr(self.model_cls, "borrado_en").is_(None),
        )
        res = await self.session.execute(sentencia)
        return res.scalar_one_or_none()

    async def get_by_id_including_deleted(self, id: int) -> T | None:
        """Obtiene una entidad por su ID incluso si fue borrada lógicamente."""
        sentencia = select(self.model_cls).where(getattr(self.model_cls, "id") == id)
        res = await self.session.execute(sentencia)
        return res.scalar_one_or_none()

    async def get_all(self) -> list[T]:
        """Obtiene todas las entidades activas (borrado_en IS NULL)."""
        sentencia = (
            select(self.model_cls)
            .where(getattr(self.model_cls, "borrado_en").is_(None))
            .order_by(getattr(self.model_cls, "id").asc())
        )
        res = await self.session.execute(sentencia)
        return list(res.scalars().all())

    async def count(self) -> int:
        """Cuenta el total de entidades activas (borrado_en IS NULL)."""
        sentencia = (
            select(func.count())
            .select_from(self.model_cls)
            .where(getattr(self.model_cls, "borrado_en").is_(None))
        )
        total = await self.session.scalar(sentencia)
        return int(total or 0)

    async def soft_delete(self, entity: T) -> None:
        """Aplica la baja lógica marcando `borrado_en` con la hora UTC actual."""
        setattr(entity, "borrado_en", datetime.now(timezone.utc))
        self.session.add(entity)
        await self._flush()

    async def delete(self, entity: T) -> None:
        """Por defecto en entidades con borrado lógico, delete delega a soft_delete."""
        await self.soft_delete(entity)

