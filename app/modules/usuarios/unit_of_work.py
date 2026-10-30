"""Unit of Work del módulo usuarios (design §D1, C-06)."""

from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import SessionDep
from app.core.unit_of_work import AbstractUnitOfWork
from app.modules.clientes.repository import ClienteRepository
from app.modules.usuarios.repository import (
    AsignacionRolRepository,
    EventoSeguridadRepository,
    IntentoAccesoRepository,
    UsuarioRepository,
)


class UsuariosUnitOfWork(AbstractUnitOfWork):
    """Agrupa los repositorios de usuarios, roles, eventos e intentos sobre la misma sesión."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.usuarios = UsuarioRepository(session)
        self.roles = AsignacionRolRepository(session)
        self.intentos = IntentoAccesoRepository(session)
        self.eventos = EventoSeguridadRepository(session)
        self.clientes = ClienteRepository(session)


def get_usuarios_uow(session: SessionDep) -> UsuariosUnitOfWork:
    """Dependencia FastAPI: el router construye el UoW y se lo inyecta al servicio sin abrirlo."""
    return UsuariosUnitOfWork(session)


UsuariosUoWDep = Annotated[UsuariosUnitOfWork, Depends(get_usuarios_uow)]

