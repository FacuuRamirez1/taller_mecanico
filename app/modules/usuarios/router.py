"""Router de autenticación (design §D1).

Rutas bajo el prefijo `/auth`:
- POST /auth/registro
- POST /auth/login
- POST /auth/logout
- GET /auth/yo
- POST /auth/cambiar-password
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.core.database import SessionDep
from app.core.dependencies import SettingsDep, UsuarioActualDep
from app.modules.usuarios import schemas
from app.modules.usuarios.service import UsuarioService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_service(session: SessionDep, request: Request) -> UsuarioService:
    return UsuarioService(session=session, sessionmaker=request.app.state.sessionmaker)


ServiceDep = Annotated[UsuarioService, Depends(get_service)]


@router.post(
    "/registro",
    response_model=schemas.UsuarioRead,
    status_code=status.HTTP_201_CREATED,
)
async def registro(
    datos: schemas.RegistroRequest,
    service: ServiceDep,
    settings: SettingsDep,
) -> schemas.UsuarioRead:
    return await service.registro(datos=datos, settings=settings)


@router.post("/login", response_model=schemas.LoginResponse)
async def login(
    datos: schemas.LoginRequest,
    request: Request,
    response: Response,
    service: ServiceDep,
    settings: SettingsDep,
) -> schemas.LoginResponse:
    ip = request.client.host if request.client else "127.0.0.1"
    usuario, token, _roles = await service.login(
        datos=datos,
        ip=ip,
        settings=settings,
        app_hash_ficticio=request.app.state.hash_ficticio,
    )
    response.set_cookie(
        key="access_token",
        value=token,
        max_age=settings.JWT_EXPIRE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
    )
    return schemas.LoginResponse(
        mensaje="Inicio de sesión exitoso",
        debe_cambiar_password=usuario.debe_cambiar_password,
        expira_en_segundos=settings.JWT_EXPIRE_SECONDS,
    )


@router.post("/logout", response_model=schemas.MensajeResponse)
async def logout(response: Response) -> schemas.MensajeResponse:
    response.delete_cookie(key="access_token", httponly=True, samesite="lax")
    return schemas.MensajeResponse(mensaje="Sesión cerrada exitosamente")


@router.get("/yo", response_model=schemas.UsuarioYoResponse)
async def obtener_yo(
    usuario: UsuarioActualDep,
    service: ServiceDep,
) -> schemas.UsuarioYoResponse:
    return await service.obtener_yo(usuario)


@router.post("/cambiar-password", response_model=schemas.MensajeResponse)
async def cambiar_password(
    datos: schemas.CambioPassword,
    usuario: UsuarioActualDep,
    response: Response,
    service: ServiceDep,
    settings: SettingsDep,
) -> schemas.MensajeResponse:
    nuevo_token = await service.cambiar_password(
        usuario=usuario, datos=datos, settings=settings
    )
    response.set_cookie(
        key="access_token",
        value=nuevo_token,
        max_age=settings.JWT_EXPIRE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
    )
    return schemas.MensajeResponse(mensaje="Contraseña actualizada exitosamente")

