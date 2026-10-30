"""Router de autenticación, personal, roles y eventos (design §D1, C-04, C-05, C-06).

El router construye UsuariosUnitOfWork y lo pasa a UsuarioService sin abrirlo.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.core.dependencies import (
    SettingsDep,
    UsuarioActualDep,
    requiere_rol,
)
from app.core.paginacion import Pagina, PaginacionDep
from app.modules.usuarios import schemas
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.service import UsuarioService
from app.modules.usuarios.unit_of_work import UsuariosUoWDep

router = APIRouter(prefix="/auth", tags=["auth"])
usuarios_router = APIRouter(prefix="/usuarios", tags=["usuarios"])
eventos_router = APIRouter(prefix="/eventos", tags=["eventos"])


def get_service(uow: UsuariosUoWDep, request: Request) -> UsuarioService:
    return UsuarioService(uow=uow, sessionmaker=request.app.state.sessionmaker)


ServiceDep = Annotated[UsuarioService, Depends(get_service)]
AdminDep = Annotated[Usuario, Depends(requiere_rol("ADMIN"))]


# --- Rutas de /auth (Grupo abierto en cuanto al bloqueo de cambio obligatorio) ---


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


# --- Rutas de /usuarios (Grupo protegido, ADMIN) ---


@usuarios_router.post(
    "",
    response_model=schemas.UsuarioRead,
    status_code=status.HTTP_201_CREATED,
)
async def crear_personal(
    datos: schemas.UsuarioPersonalCreate,
    admin: AdminDep,
    service: ServiceDep,
    settings: SettingsDep,
) -> schemas.UsuarioRead:
    return await service.crear_personal(
        datos=datos,
        admin_id=admin.id,  # type: ignore[arg-type]
        admin_email=admin.email,
        settings=settings,
    )


@usuarios_router.get(
    "/{usuario_id}/roles",
    response_model=list[schemas.AsignacionRolRead],
)
async def listar_roles_usuario(
    usuario_id: int,
    _admin: AdminDep,
    service: ServiceDep,
) -> list[schemas.AsignacionRolRead]:
    return await service.listar_roles_usuario(usuario_id=usuario_id)


@usuarios_router.post(
    "/{usuario_id}/roles",
    response_model=schemas.AsignacionRolRead,
    status_code=status.HTTP_201_CREATED,
)
async def asignar_rol(
    usuario_id: int,
    datos: schemas.AsignacionRolCreate,
    admin: AdminDep,
    service: ServiceDep,
) -> schemas.AsignacionRolRead:
    return await service.asignar_rol(
        usuario_id=usuario_id,
        datos=datos,
        admin_id=admin.id,  # type: ignore[arg-type]
        admin_email=admin.email,
    )


@usuarios_router.delete(
    "/{usuario_id}/roles/{rol}",
    response_model=schemas.MensajeResponse,
)
async def revocar_rol(
    usuario_id: int,
    rol: schemas.RolEnum,
    admin: AdminDep,
    service: ServiceDep,
) -> schemas.MensajeResponse:
    return await service.revocar_rol(
        usuario_id=usuario_id,
        rol=rol,
        admin_id=admin.id,  # type: ignore[arg-type]
        admin_email=admin.email,
    )


# --- Rutas de /eventos (Grupo protegido, ADMIN) ---


@eventos_router.get(
    "",
    response_model=Pagina[schemas.EventoSeguridadRead],
)
async def listar_eventos(
    _admin: AdminDep,
    service: ServiceDep,
    paginacion: PaginacionDep,
) -> Pagina[schemas.EventoSeguridadRead]:
    return await service.listar_eventos(
        page=paginacion.page,
        size=paginacion.size,
    )
