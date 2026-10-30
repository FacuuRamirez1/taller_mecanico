"""Repositorios del módulo de repuestos (design §D1, C-06).

`RepuestoRepository` hereda de `SoftDeleteRepository` y gestiona repuestos vigentes.
`MovimientoStockRepository` y `HistorialPrecioRepository` gestionan los históricos.
Todos los métodos de escritura ejecutan flush() y NUNCA commit().
"""

from sqlalchemy import Select, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.repository import BaseRepository, SoftDeleteRepository
from app.modules.repuestos.models import (
    HistorialPrecioRepuesto,
    MovimientoStock,
    Repuesto,
)


class RepuestoRepository(SoftDeleteRepository[Repuesto]):
    """Repositorio para entidad Repuesto con soporte de borrado lógico."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Repuesto)

    def consulta_listar(self, q: str | None = None) -> Select:
        """Construye la sentencia select para listar y buscar repuestos vigentes."""
        sentencia = (
            select(Repuesto)
            .where(Repuesto.borrado_en.is_(None))
            .order_by(Repuesto.id.desc())
        )
        if q:
            # Parámetro ligado para prevenir inyección SQL (RN-18, C-16)
            sentencia = sentencia.where(Repuesto.descripcion.ilike(f"%{q}%"))
        return sentencia

    async def get_by_codigo(self, codigo: str) -> Repuesto | None:
        """Busca repuesto vigente por código."""
        sentencia = select(Repuesto).where(
            Repuesto.codigo == codigo,
            Repuesto.borrado_en.is_(None),
        )
        res = await self.session.execute(sentencia)
        return res.scalar_one_or_none()

    async def ajustar_stock(self, repuesto: Repuesto, delta: int) -> Repuesto:
        """Punto único de modificación de stock (RN-14)."""
        repuesto.stock += delta
        self.session.add(repuesto)
        await self._flush()
        return repuesto


class MovimientoStockRepository(BaseRepository[MovimientoStock]):
    """Repositorio para movimientos de stock (sólo agregado)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MovimientoStock)

    async def listar_por_repuesto(self, repuesto_id: int) -> list[MovimientoStock]:
        """Obtiene el historial de movimientos de un repuesto."""
        sentencia = (
            select(MovimientoStock)
            .where(MovimientoStock.repuesto_id == repuesto_id)
            .order_by(MovimientoStock.cuando.desc(), MovimientoStock.id.desc())
        )
        res = await self.session.execute(sentencia)
        return list(res.scalars().all())


class HistorialPrecioRepository(BaseRepository[HistorialPrecioRepuesto]):
    """Repositorio para historial de cambios de precio (sólo agregado)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, HistorialPrecioRepuesto)

    async def listar_por_repuesto(self, repuesto_id: int) -> list[HistorialPrecioRepuesto]:
        """Obtiene el historial de precios de un repuesto."""
        sentencia = (
            select(HistorialPrecioRepuesto)
            .where(HistorialPrecioRepuesto.repuesto_id == repuesto_id)
            .order_by(HistorialPrecioRepuesto.cuando.desc(), HistorialPrecioRepuesto.id.desc())
        )
        res = await self.session.execute(sentencia)
        return list(res.scalars().all())

