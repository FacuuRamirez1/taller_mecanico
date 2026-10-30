"""Router de órdenes de trabajo (design §D1, C-06).

Construye OrdenesUnitOfWork y lo pasa a OrdenService sin abrirlo.
Maneja los permisos declarados en la matriz RBAC de la consigna.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.dependencies import UsuarioActivoDep, requiere_rol
from app.core.paginacion import Pagina, PaginacionDep
from app.modules.ordenes import schemas
from app.modules.ordenes.service import OrdenService
from app.modules.ordenes.unit_of_work import OrdenesUoWDep
from app.modules.usuarios.models import Usuario

ordenes_router = APIRouter(prefix="/ordenes", tags=["ordenes"])
estados_router = APIRouter(tags=["ordenes"])
mis_ordenes_router = APIRouter(tags=["ordenes"])


def get_service(uow: OrdenesUoWDep) -> OrdenService:
    return OrdenService(uow)


ServiceDep = Annotated[OrdenService, Depends(get_service)]


@estados_router.get("/estados-orden", response_model=list[schemas.EstadoOrdenRead])
async def listar_estados(service: ServiceDep) -> list[schemas.EstadoOrdenRead]:
    """Catálogo público de estados ordenado por posición."""
    return await service.listar_estados()


@mis_ordenes_router.get("/mis-ordenes", response_model=Pagina[schemas.OrdenRead])
async def mis_ordenes(
    usuario: UsuarioActivoDep,
    service: ServiceDep,
    paginacion: PaginacionDep,
) -> Pagina[schemas.OrdenRead]:
    """Listado de órdenes propias del cliente autenticado."""
    return await service.mis_ordenes(
        usuario_id=usuario.id,  # type: ignore[arg-type]
        page=paginacion.page,
        size=paginacion.size,
    )


@ordenes_router.post(
    "",
    response_model=schemas.OrdenDetalleRead,
    status_code=status.HTTP_201_CREATED,
)
async def crear_orden(
    datos: schemas.OrdenCreate,
    usuario: Annotated[Usuario, Depends(requiere_rol("RECEPCION", "ADMIN"))],
    service: ServiceDep,
) -> schemas.OrdenDetalleRead:
    return await service.crear(datos=datos, usuario=usuario)


@ordenes_router.get(
    "",
    response_model=Pagina[schemas.OrdenRead],
    dependencies=[Depends(requiere_rol("ADMIN", "RECEPCION", "MECANICO"))],
)
async def listar_ordenes(
    service: ServiceDep,
    paginacion: PaginacionDep,
    estado: str | None = None,
) -> Pagina[schemas.OrdenRead]:
    return await service.listar(
        estado=estado,
        page=paginacion.page,
        size=paginacion.size,
    )


@ordenes_router.get(
    "/{orden_id}",
    response_model=schemas.OrdenDetalleRead,
)
async def obtener_orden(
    orden_id: int,
    usuario: UsuarioActivoDep,
    service: ServiceDep,
) -> schemas.OrdenDetalleRead:
    return await service.obtener(orden_id=orden_id, usuario=usuario)


@ordenes_router.post(
    "/{orden_id}/iniciar",
    response_model=schemas.OrdenRead,
)
async def iniciar_orden(
    orden_id: int,
    usuario: Annotated[Usuario, Depends(requiere_rol("MECANICO"))],
    service: ServiceDep,
) -> schemas.OrdenRead:
    return await service.iniciar(orden_id=orden_id, usuario=usuario)


@ordenes_router.post(
    "/{orden_id}/terminar",
    response_model=schemas.OrdenRead,
)
async def terminar_orden(
    orden_id: int,
    usuario: Annotated[Usuario, Depends(requiere_rol("ADMIN", "MECANICO"))],
    service: ServiceDep,
) -> schemas.OrdenRead:
    return await service.terminar(orden_id=orden_id, usuario=usuario)


@ordenes_router.post(
    "/{orden_id}/cancelar",
    response_model=schemas.OrdenRead,
)
async def cancelar_orden(
    orden_id: int,
    usuario: UsuarioActivoDep,
    service: ServiceDep,
) -> schemas.OrdenRead:
    return await service.cancelar(orden_id=orden_id, usuario=usuario)

