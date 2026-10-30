"""Repositorios del módulo de clientes y vehículos (design §D1, C-06).

`ClienteRepository` gestiona la entidad Cliente con precarga explícita (`selectinload`).
`VehiculoRepository` hereda de `SoftDeleteRepository` y gestiona vehículos vigentes.
Todos los métodos de escritura ejecutan flush() y NUNCA commit().
"""

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.repository import BaseRepository, SoftDeleteRepository
from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.ordenes.models import EstadoOrden, OrdenTrabajo


class ClienteRepository(BaseRepository[Cliente]):
    """Repositorio para entidad Cliente."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Cliente)

    async def get_by_id_con_vehiculos(self, cliente_id: int) -> Cliente | None:
        """Obtiene cliente con precarga explícita de sus vehículos (evita N+1)."""
        sentencia = (
            select(Cliente)
            .where(Cliente.id == cliente_id)
            .options(selectinload(Cliente.vehiculos))
        )
        res = await self.session.execute(sentencia)
        return res.scalar_one_or_none()

    async def get_by_usuario_id(self, usuario_id: int) -> Cliente | None:
        """Obtiene la ficha de cliente asociada a un usuario del sistema."""
        sentencia = select(Cliente).where(Cliente.usuario_id == usuario_id)
        res = await self.session.execute(sentencia)
        return res.scalar_one_or_none()

    async def get_by_documento(self, documento: str) -> Cliente | None:
        """Busca cliente por número de documento."""
        sentencia = select(Cliente).where(Cliente.documento == documento)
        res = await self.session.execute(sentencia)
        return res.scalar_one_or_none()


class VehiculoRepository(SoftDeleteRepository[Vehiculo]):
    """Repositorio para entidad Vehiculo con soporte de borrado lógico."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Vehiculo)

    async def get_by_patente(self, patente: str) -> Vehiculo | None:
        """Busca vehículo vigente por patente."""
        sentencia = select(Vehiculo).where(
            Vehiculo.patente == patente,
            Vehiculo.borrado_en.is_(None),
        )
        res = await self.session.execute(sentencia)
        return res.scalar_one_or_none()

    async def listar_vigentes_por_cliente(self, cliente_id: int) -> list[Vehiculo]:
        """Lista vehículos vigentes asociados a un cliente."""
        sentencia = (
            select(Vehiculo)
            .where(
                Vehiculo.cliente_id == cliente_id,
                Vehiculo.borrado_en.is_(None),
            )
            .order_by(Vehiculo.id.asc())
        )
        res = await self.session.execute(sentencia)
        return list(res.scalars().all())

    async def tiene_ordenes_abiertas(self, vehiculo_id: int) -> bool:
        """Verifica si el vehículo tiene órdenes de trabajo no finalizadas (es_final = false)."""
        sentencia = (
            select(OrdenTrabajo.id)
            .join(EstadoOrden, EstadoOrden.codigo == OrdenTrabajo.estado)
            .where(
                OrdenTrabajo.vehiculo_id == vehiculo_id,
                EstadoOrden.es_final.is_(False),
            )
            .limit(1)
        )
        res = await self.session.execute(sentencia)
        return res.scalar_one_or_none() is not None

