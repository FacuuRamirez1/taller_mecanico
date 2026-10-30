"""Repositorios del módulo de órdenes de trabajo (design §D1, C-06).

`EstadoOrdenRepository`: de sólo lectura, NO hereda de BaseRepository (US-030).
`OrdenTrabajoRepository`: precarga explícita para evitar N+1 (selectinload).
`ItemOrdenRepository` e `HistorialEstadoOrdenRepository`.
Todos los métodos de escritura ejecutan flush() y NUNCA commit().
"""

from sqlalchemy import Select, select
from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.repository import BaseRepository
from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.ordenes.models import (
    EstadoOrden,
    HistorialEstadoOrden,
    ItemOrden,
    OrdenTrabajo,
)


class EstadoOrdenRepository:
    """Repositorio de sólo lectura para el catálogo de estados de orden (US-030).

    NO hereda de BaseRepository para no ofrecer métodos de escritura ni borrado.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def listar_por_posicion(self) -> list[EstadoOrden]:
        """Devuelve el catálogo completo de estados ordenado por su posición."""
        sentencia = select(EstadoOrden).order_by(EstadoOrden.posicion.asc())
        res = await self.session.execute(sentencia)
        return list(res.scalars().all())

    async def get_by_codigo(self, codigo: str) -> EstadoOrden | None:
        """Obtiene un estado de orden por su código (PK)."""
        sentencia = select(EstadoOrden).where(EstadoOrden.codigo == codigo)
        res = await self.session.execute(sentencia)
        return res.scalar_one_or_none()


class OrdenTrabajoRepository(BaseRepository[OrdenTrabajo]):
    """Repositorio para órdenes de trabajo."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OrdenTrabajo)

    async def get_by_id_con_relaciones(self, orden_id: int) -> OrdenTrabajo | None:
        """Obtiene una orden con todas sus relaciones precargadas sin N+1."""
        sentencia = (
            select(OrdenTrabajo)
            .where(OrdenTrabajo.id == orden_id)
            .options(
                selectinload(OrdenTrabajo.vehiculo).selectinload(Vehiculo.cliente),
                selectinload(OrdenTrabajo.items).selectinload(ItemOrden.repuesto),
                selectinload(OrdenTrabajo.historial),
            )
        )
        res = await self.session.execute(sentencia)
        return res.scalar_one_or_none()

    def consulta_listar(self, estado: str | None = None) -> Select:
        """Construye consulta paginada de órdenes, opcionalmente filtrada por estado."""
        sentencia = select(OrdenTrabajo).order_by(OrdenTrabajo.id.desc())
        if estado:
            sentencia = sentencia.where(OrdenTrabajo.estado == estado)
        return sentencia

    def consulta_mis_ordenes(self, usuario_id: int) -> Select:
        """Construye consulta paginada de órdenes asociadas al cliente del usuario."""
        return (
            select(OrdenTrabajo)
            .join(Vehiculo, Vehiculo.id == OrdenTrabajo.vehiculo_id)
            .join(Cliente, Cliente.id == Vehiculo.cliente_id)
            .where(Cliente.usuario_id == usuario_id)
            .order_by(OrdenTrabajo.id.desc())
        )


class ItemOrdenRepository(BaseRepository[ItemOrden]):
    """Repositorio para ítems de órdenes de trabajo."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ItemOrden)

    async def listar_por_orden(self, orden_id: int) -> list[ItemOrden]:
        """Lista los ítems de una orden."""
        sentencia = (
            select(ItemOrden)
            .where(ItemOrden.orden_id == orden_id)
            .options(selectinload(ItemOrden.repuesto))
            .order_by(ItemOrden.id.asc())
        )
        res = await self.session.execute(sentencia)
        return list(res.scalars().all())


class HistorialEstadoOrdenRepository(BaseRepository[HistorialEstadoOrden]):
    """Repositorio para historial de transiciones de estado de orden (sólo agregado)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, HistorialEstadoOrden)

    async def listar_por_orden(self, orden_id: int) -> list[HistorialEstadoOrden]:
        """Lista las transiciones de estado de una orden."""
        sentencia = (
            select(HistorialEstadoOrden)
            .where(HistorialEstadoOrden.orden_id == orden_id)
            .order_by(HistorialEstadoOrden.cuando.asc(), HistorialEstadoOrden.id.asc())
        )
        res = await self.session.execute(sentencia)
        return list(res.scalars().all())

