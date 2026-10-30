"""Unit of Work del módulo órdenes (design §D1, C-06)."""

from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import SessionDep
from app.core.unit_of_work import AbstractUnitOfWork
from app.modules.clientes.repository import ClienteRepository, VehiculoRepository
from app.modules.ordenes.repository import (
    EstadoOrdenRepository,
    HistorialEstadoOrdenRepository,
    ItemOrdenRepository,
    OrdenTrabajoRepository,
)
from app.modules.repuestos.repository import (
    MovimientoStockRepository,
    RepuestoRepository,
)
from app.modules.usuarios.repository import AsignacionRolRepository


class OrdenesUnitOfWork(AbstractUnitOfWork):
    """Agrupa los repositorios necesarios para el ciclo de vida completo de órdenes."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.ordenes = OrdenTrabajoRepository(session)
        self.items = ItemOrdenRepository(session)
        self.estados = EstadoOrdenRepository(session)
        self.historial = HistorialEstadoOrdenRepository(session)
        self.repuestos = RepuestoRepository(session)
        self.movimientos = MovimientoStockRepository(session)
        self.vehiculos = VehiculoRepository(session)
        self.clientes = ClienteRepository(session)
        self.roles = AsignacionRolRepository(session)


def get_ordenes_uow(session: SessionDep) -> OrdenesUnitOfWork:
    """Dependencia FastAPI: el router construye el UoW y se lo inyecta al servicio sin abrirlo."""
    return OrdenesUnitOfWork(session)


OrdenesUoWDep = Annotated[OrdenesUnitOfWork, Depends(get_ordenes_uow)]
