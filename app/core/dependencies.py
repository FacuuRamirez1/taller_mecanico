"""Dependencias transversales de seguridad y sesión (design §D1).

`get_usuario_actual` lee la cookie `access_token` y rechaza con 401:
- Si no hay cookie
- Si viene encabezado Authorization
- Si el token está mal firmado, vencido o inválido
- Si el usuario no existe o está inactivo
- Si el token fue emitido antes de `password_cambiada_en` (iat sin truncar)
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select

from app.core.config import Settings
from app.core.database import SessionDep
from app.core.security import decodificar_token_acceso
from app.modules.usuarios.models import Usuario


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

