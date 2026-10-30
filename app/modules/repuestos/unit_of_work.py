"""Unit of Work del módulo repuestos (design §D1, C-06)."""

from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import SessionDep
from app.core.unit_of_work import AbstractUnitOfWork
from app.modules.repuestos.repository import (
    HistorialPrecioRepository,
    MovimientoStockRepository,
    RepuestoRepository,
)
from app.modules.usuarios.repository import UsuarioRepository


class RepuestosUnitOfWork(AbstractUnitOfWork):
    """Agrupa los repositorios de repuestos, movimientos y precios sobre la misma sesión."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.repuestos = RepuestoRepository(session)
        self.movimientos = MovimientoStockRepository(session)
        self.precios = HistorialPrecioRepository(session)
        self.usuarios = UsuarioRepository(session)


def get_repuestos_uow(session: SessionDep) -> RepuestosUnitOfWork:
    """Dependencia FastAPI: el router construye el UoW y se lo inyecta al servicio sin abrirlo."""
    return RepuestosUnitOfWork(session)


RepuestosUoWDep = Annotated[RepuestosUnitOfWork, Depends(get_repuestos_uow)]

