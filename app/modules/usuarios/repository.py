"""Repositorios del módulo de usuarios y seguridad (design §D1, C-06).

`UsuarioRepository`, `AsignacionRolRepository`, `IntentoAccesoRepository` y `EventoSeguridadRepository`.
Todos los métodos de escritura ejecutan flush() y NUNCA commit().
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import Select, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.repository import BaseRepository
from app.modules.usuarios import schemas
from app.modules.usuarios.models import (
    AsignacionRol,
    EventoSeguridad,
    IntentoAcceso,
    Usuario,
)

ACTOR_INTERNO_EMAIL = "admin@example.com"


class UsuarioRepository(BaseRepository[Usuario]):
    """Repositorio para entidad Usuario."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Usuario)

    async def get_by_email(self, email: str) -> Usuario | None:
        """Busca usuario por correo electrónico."""
        sentencia = select(Usuario).where(Usuario.email == email)
        res = await self.session.execute(sentencia)
        return res.scalar_one_or_none()

    async def obtener_actor_por_defecto(self) -> Usuario | None:
        """Administrador vigente usado como actor cuando el servicio no recibió uno.

        Prefiere la cuenta interna fija del seed y, si no existe, el primer ADMIN
        activo con asignación vigente (no revocada y no vencida).
        """
        ahora = datetime.now(timezone.utc)
        sentencia = (
            select(Usuario)
            .join(AsignacionRol, AsignacionRol.usuario_id == Usuario.id)
            .where(
                AsignacionRol.rol == schemas.RolEnum.ADMIN,
                AsignacionRol.revocada_en.is_(None),
                AsignacionRol.vence_en.is_(None) | (AsignacionRol.vence_en > ahora),
                Usuario.activo.is_(True),
            )
            .order_by((Usuario.email == ACTOR_INTERNO_EMAIL).desc(), Usuario.id.asc())
            .limit(1)
        )
        res = await self.session.execute(sentencia)
        return res.scalar_one_or_none()


class AsignacionRolRepository(BaseRepository[AsignacionRol]):
    """Repositorio para asignaciones de rol."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AsignacionRol)

    async def listar_por_usuario(self, usuario_id: int) -> list[AsignacionRol]:
        """Obtiene todas las asignaciones históricas y vigentes de un usuario."""
        sentencia = (
            select(AsignacionRol)
            .where(AsignacionRol.usuario_id == usuario_id)
            .order_by(AsignacionRol.id.asc())
        )
        res = await self.session.execute(sentencia)
        return list(res.scalars().all())

    async def listar_vigentes_por_usuario(self, usuario_id: int) -> list[str]:
        """Obtiene la lista de nombres de roles vigentes para el usuario."""
        ahora = datetime.now(timezone.utc)
        sentencia = select(AsignacionRol.rol).where(
            AsignacionRol.usuario_id == usuario_id,
            AsignacionRol.revocada_en.is_(None),
            (
                AsignacionRol.vence_en.is_(None)
                | (AsignacionRol.vence_en > ahora)
            ),
        )
        res = await self.session.execute(sentencia)
        return [
            r.value if hasattr(r, "value") else str(r)
            for r in res.scalars().all()
        ]

    async def obtener_vigente(
        self, usuario_id: int, rol: schemas.RolEnum | str
    ) -> AsignacionRol | None:
        """Busca una asignación vigente para un rol y usuario específico."""
        ahora = datetime.now(timezone.utc)
        sentencia = select(AsignacionRol).where(
            AsignacionRol.usuario_id == usuario_id,
            AsignacionRol.rol == rol,
            AsignacionRol.revocada_en.is_(None),
            (
                AsignacionRol.vence_en.is_(None)
                | (AsignacionRol.vence_en > ahora)
            ),
        )
        res = await self.session.execute(sentencia)
        return res.scalar_one_or_none()

    async def obtener_vencida_abierta(
        self, usuario_id: int, rol: schemas.RolEnum | str
    ) -> AsignacionRol | None:
        """Busca una asignación vencida que no ha sido marcada como revocada."""
        ahora = datetime.now(timezone.utc)
        sentencia = select(AsignacionRol).where(
            AsignacionRol.usuario_id == usuario_id,
            AsignacionRol.rol == rol,
            AsignacionRol.revocada_en.is_(None),
            AsignacionRol.vence_en <= ahora,
        )
        res = await self.session.execute(sentencia)
        return res.scalar_one_or_none()

    async def contar_admins_vigentes(self) -> int:
        """Cuenta la cantidad de administradores vigentes en el sistema (RN-05)."""
        ahora = datetime.now(timezone.utc)
        sentencia = select(func.count(AsignacionRol.id)).where(
            AsignacionRol.rol == schemas.RolEnum.ADMIN,
            AsignacionRol.revocada_en.is_(None),
            (
                AsignacionRol.vence_en.is_(None)
                | (AsignacionRol.vence_en > ahora)
            ),
        )
        total = await self.session.scalar(sentencia)
        return int(total or 0)


class IntentoAccesoRepository(BaseRepository[IntentoAcceso]):
    """Repositorio para control de intentos de acceso y rate limiting (RN-08)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, IntentoAcceso)

    async def contar_fallos_recientes(
        self, email: str, ip: str, ventana_segundos: int = 60
    ) -> int:
        """Cuenta fallos en la ventana temporal posteriores al último éxito."""
        hace_ventana = datetime.now(timezone.utc) - timedelta(seconds=ventana_segundos)
        sentencia = select(func.count()).select_from(IntentoAcceso).where(
            IntentoAcceso.email == email,
            IntentoAcceso.ip == ip,
            IntentoAcceso.exito.is_(False),
            IntentoAcceso.cuando >= hace_ventana,
            IntentoAcceso.cuando > func.coalesce(
                select(func.max(IntentoAcceso.cuando)).where(
                    IntentoAcceso.email == email,
                    IntentoAcceso.ip == ip,
                    IntentoAcceso.exito.is_(True),
                ).scalar_subquery(),
                datetime(1970, 1, 1, tzinfo=timezone.utc),
            ),
        )
        fallos = await self.session.scalar(sentencia)
        return int(fallos or 0)


class EventoSeguridadRepository(BaseRepository[EventoSeguridad]):
    """Repositorio para auditoría de eventos de seguridad (sólo agregado)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EventoSeguridad)

    def consulta_listar(self) -> Select:
        """Construye la sentencia para listar eventos por fecha descendente."""
        return select(EventoSeguridad).order_by(
            EventoSeguridad.cuando.desc(), EventoSeguridad.id.desc()
        )

