"""Unit of Work del módulo clientes (design §D1, C-06)."""

from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import SessionDep
from app.core.unit_of_work import AbstractUnitOfWork
from app.modules.clientes.repository import ClienteRepository, VehiculoRepository


class ClientesUnitOfWork(AbstractUnitOfWork):
    """Agrupa los repositorios de clientes y vehículos sobre la misma sesión."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.clientes = ClienteRepository(session)
        self.vehiculos = VehiculoRepository(session)


def get_clientes_uow(session: SessionDep) -> ClientesUnitOfWork:
    """Dependencia FastAPI: el router construye el UoW y se lo inyecta al servicio sin abrirlo."""
    return ClientesUnitOfWork(session)


ClientesUoWDep = Annotated[ClientesUnitOfWork, Depends(get_clientes_uow)]

