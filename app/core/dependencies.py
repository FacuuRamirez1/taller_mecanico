"""Dependencias transversales de seguridad y sesión (design §D1, C-05).

`get_usuario_actual` lee la cookie `access_token` y rechaza con 401:
- Si no hay cookie
- Si viene encabezado Authorization
- Si el token está mal firmado, vencido o inválido
- Si el usuario no existe o está inactivo
- Si el token fue emitido antes de `password_cambiada_en` (iat sin truncar)

`requiere_rol(*roles)` rechaza con 403 si:
- El usuario tiene `debe_cambiar_password = true`
- El usuario no tiene al menos uno de los roles solicitados vigente en `asignacion_rol`
"""

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select

from app.core.config import Settings
from app.core.database import SessionDep
from app.core.security import decodificar_token_acceso
from app.modules.usuarios.models import AsignacionRol, Usuario


def get_settings(request: Request) -> Settings:
    return request.app.state.settings  # type: ignore[no-any-return]


SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_usuario_actual(
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
) -> Usuario:
    if "authorization" in request.headers:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se admite autenticación por encabezado Authorization",
        )

    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
        )

    payload = decodificar_token_acceso(token, settings)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )

    usuario = await session.scalar(select(Usuario).where(Usuario.id == int(sub)))
    if usuario is None or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )

    if usuario.password_cambiada_en is not None:
        iat_float = float(payload.get("iat", 0))
        cambiada_en_float = usuario.password_cambiada_en.timestamp()
        if iat_float < cambiada_en_float:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sesión invalidada por cambio de contraseña",
            )

    setattr(usuario, "_roles_token", payload.get("roles", []))
    return usuario


UsuarioActualDep = Annotated[Usuario, Depends(get_usuario_actual)]


async def get_usuario_activo(
    usuario: UsuarioActualDep,
) -> Usuario:
    """Verifica que el usuario autenticado no tenga pendiente el cambio de contraseña."""
    if usuario.debe_cambiar_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debe cambiar su contraseña antes de continuar",
        )
    return usuario


UsuarioActivoDep = Annotated[Usuario, Depends(get_usuario_activo)]


def requiere_rol(*roles: str) -> Callable[..., Usuario]:
    """Dependencia que valida que el usuario tenga al menos uno de los roles solicitados vigente.

    Roles vigentes en asignacion_rol:
    - revocada_en IS NULL
    - (vence_en IS NULL OR vence_en > now())
    Rechaza con 403 si el usuario tiene `debe_cambiar_password` o si carece del rol vigente.
    """
    roles_esperados = set(roles)

    async def _verificar_rol(
        usuario: UsuarioActivoDep,
        session: SessionDep,
    ) -> Usuario:
        ahora = datetime.now(timezone.utc)
        sentencia = select(AsignacionRol.rol).where(
            AsignacionRol.usuario_id == usuario.id,
            AsignacionRol.revocada_en.is_(None),
            (
                AsignacionRol.vence_en.is_(None)
                | (AsignacionRol.vence_en > ahora)
            ),
        )
        res = await session.execute(sentencia)
        roles_vigentes = {
            r.value if hasattr(r, "value") else str(r)
            for r in res.scalars().all()
        }

        if not roles_esperados.intersection(roles_vigentes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permiso denegado",
            )
        return usuario

    return _verificar_rol
