"""Servicio de usuarios y autenticación (design §D1).

Deuda declarada de C-03/C-04: el servicio usa `AsyncSession` directa y confirma
al final. C-06 mueve las consultas a repositorios y el `commit` al UnitOfWork
sin cambiar las firmas públicas ni los schemas.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import Settings
from app.core.errores import traducir_integrity_error
from app.core.security import crear_token_acceso, hash_password, verify_password
from app.modules.clientes.models import Cliente
from app.modules.usuarios import schemas
from app.modules.usuarios.models import (
    AsignacionRol,
    EventoSeguridad,
    IntentoAcceso,
    Usuario,
)

# TODO C-06: mover consultas a repositorios y `commit` al UnitOfWork (firmas estables).


class UsuarioService:
    def __init__(self, session: AsyncSession, sessionmaker: Any) -> None:
        self.session = session
        self.sessionmaker = sessionmaker

    async def login(
        self,
        datos: schemas.LoginRequest,
        ip: str,
        settings: Settings,
        app_hash_ficticio: str,
    ) -> tuple[Usuario, str, list[str]]:
        # 1. Límite de intentos primero (RN-08) sin calcular ningún hash
        hace_60s = datetime.now(timezone.utc) - timedelta(seconds=60)
        sentencia_fallos = select(func.count()).select_from(IntentoAcceso).where(
            IntentoAcceso.email == datos.email,
            IntentoAcceso.ip == ip,
            IntentoAcceso.exito.is_(False),
            IntentoAcceso.cuando >= hace_60s,
            IntentoAcceso.cuando > func.coalesce(
                select(func.max(IntentoAcceso.cuando)).where(
                    IntentoAcceso.email == datos.email,
                    IntentoAcceso.ip == ip,
                    IntentoAcceso.exito.is_(True),
                ).scalar_subquery(),
                datetime(1970, 1, 1, tzinfo=timezone.utc),
            ),
        )
        fallos = int(await self.session.scalar(sentencia_fallos) or 0)
        if fallos >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos fallidos. Intente nuevamente más tarde",
                headers={"Retry-After": "60"},
            )

        # 2. Verificación contra hash de usuario o hash ficticio precalculado
        usuario = await self.session.scalar(
            select(Usuario).where(Usuario.email == datos.email)
        )
        if usuario is not None and usuario.activo:
            password_valida = await verify_password(datos.password, usuario.password_hash)
        else:
            await verify_password(datos.password, app_hash_ficticio)
            password_valida = False

        # 3. Anotar intento_acceso en sesión y transacción propias (se confirma siempre)
        async with self.sessionmaker() as ses_intento:
            intento = IntentoAcceso(
                email=datos.email,
                ip=ip,
                exito=password_valida,
            )
            ses_intento.add(intento)
            await ses_intento.commit()

        if not password_valida or usuario is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas",
            )

        # 4. Emisión del token con roles vigentes al emitir
        roles_res = await self.session.execute(
            select(AsignacionRol.rol).where(
                AsignacionRol.usuario_id == usuario.id,
                AsignacionRol.revocada_en.is_(None),
                (
                    AsignacionRol.vence_en.is_(None)
                    | (AsignacionRol.vence_en > datetime.now(timezone.utc))
                ),
            )
        )
        roles_vigentes = [
            r.value if hasattr(r, "value") else str(r)
            for r in roles_res.scalars().all()
        ]
        token = crear_token_acceso(
            usuario_id=usuario.id,
            roles=roles_vigentes,
            settings=settings,
        )
        return usuario, token, roles_vigentes

    async def registro(
        self, datos: schemas.RegistroRequest, settings: Settings
    ) -> Usuario:
        # Hash antes de abrir la transacción
        hash_pw = await hash_password(datos.password, settings.BCRYPT_COST)

        usuario = Usuario(
            email=datos.email,
            nombre=datos.nombre,
            password_hash=hash_pw,
            activo=True,
            debe_cambiar_password=False,
        )
        self.session.add(usuario)
        try:
            await self.session.flush()
            self.session.add(
                AsignacionRol(
                    usuario_id=usuario.id,
                    rol=schemas.RolEnum.CLIENTE,
                    otorgada_por=None,
                )
            )
            self.session.add(
                Cliente(
                    usuario_id=usuario.id,
                    nombre=datos.nombre,
                    documento=datos.documento,
                    telefono=datos.telefono,
                )
            )
            self.session.add(
                EventoSeguridad(
                    actor=usuario.email,
                    accion="Auto-registro de cliente",
                )
            )
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise traducir_integrity_error(exc) from None
        return usuario

    async def cambiar_password(
        self,
        usuario: Usuario,
        datos: schemas.CambioPassword,
        settings: Settings,
    ) -> str:
        valida = await verify_password(datos.password_actual, usuario.password_hash)
        if not valida:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Contraseña actual incorrecta",
            )

        nuevo_hash = await hash_password(datos.password_nueva, settings.BCRYPT_COST)
        ahora = datetime.now(timezone.utc)
        usuario.password_hash = nuevo_hash
        usuario.password_cambiada_en = ahora
        usuario.debe_cambiar_password = False
        self.session.add(usuario)
        self.session.add(
            EventoSeguridad(actor=usuario.email, accion="Cambio de contraseña")
        )
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise traducir_integrity_error(exc) from None

        # Emitir el token nuevo estrictamente posterior a password_cambiada_en
        iat_nuevo = datetime.now(timezone.utc)
        if iat_nuevo <= ahora:
            iat_nuevo = ahora + timedelta(microseconds=1000)

        roles_res = await self.session.execute(
            select(AsignacionRol.rol).where(
                AsignacionRol.usuario_id == usuario.id,
                AsignacionRol.revocada_en.is_(None),
                (
                    AsignacionRol.vence_en.is_(None)
                    | (AsignacionRol.vence_en > datetime.now(timezone.utc))
                ),
            )
        )
        roles = [
            r.value if hasattr(r, "value") else str(r)
            for r in roles_res.scalars().all()
        ]
        return crear_token_acceso(
            usuario_id=usuario.id,
            roles=roles,
            settings=settings,
            iat=iat_nuevo,
        )

    async def obtener_yo(self, usuario: Usuario) -> schemas.UsuarioYoResponse:
        roles_res = await self.session.execute(
            select(AsignacionRol.rol).where(
                AsignacionRol.usuario_id == usuario.id,
                AsignacionRol.revocada_en.is_(None),
                (
                    AsignacionRol.vence_en.is_(None)
                    | (AsignacionRol.vence_en > datetime.now(timezone.utc))
                ),
            )
        )
        roles_vigentes = [
            r.value if hasattr(r, "value") else str(r)
            for r in roles_res.scalars().all()
        ]
        roles_token = getattr(usuario, "_roles_token", [])
        return schemas.UsuarioYoResponse(
            id=usuario.id,  # type: ignore[arg-type]
            email=usuario.email,
            nombre=usuario.nombre,
            activo=usuario.activo,
            debe_cambiar_password=usuario.debe_cambiar_password,
            roles=roles_vigentes,
            roles_token=roles_token,
        )

