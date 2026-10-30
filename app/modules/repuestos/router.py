"""Router de repuestos (design §D5, C-05, C-06).

El router construye el UnitOfWork mediante la dependencia RepuestosUoWDep
y se lo inyecta a RepuestoService sin abrirlo.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.dependencies import requiere_rol
from app.core.paginacion import Pagina, PaginacionDep
from app.modules.repuestos import schemas
from app.modules.repuestos.service import RepuestoService
from app.modules.repuestos.unit_of_work import RepuestosUoWDep
from app.modules.usuarios.models import Usuario

router = APIRouter(prefix="/repuestos", tags=["repuestos"])


def get_service(uow: RepuestosUoWDep) -> RepuestoService:
    return RepuestoService(uow)


ServiceDep = Annotated[RepuestoService, Depends(get_service)]
AdminDep = Annotated[Usuario, Depends(requiere_rol("ADMIN"))]


@router.get(
    "",
    response_model=Pagina[schemas.RepuestoRead],
    dependencies=[Depends(requiere_rol("ADMIN", "RECEPCION", "MECANICO"))],
)
async def listar_repuestos(
    service: ServiceDep,
    paginacion: PaginacionDep,
    q: str | None = None,
) -> Pagina[schemas.RepuestoRead]:
    return await service.listar(q=q, page=paginacion.page, size=paginacion.size)


@router.get(
    "/{repuesto_id}",
    response_model=schemas.RepuestoRead,
    dependencies=[Depends(requiere_rol("ADMIN", "RECEPCION", "MECANICO"))],
)
async def obtener_repuesto(
    repuesto_id: int, service: ServiceDep
) -> schemas.RepuestoRead:
    return await service.obtener(repuesto_id)


@router.post(
    "",
    response_model=schemas.RepuestoRead,
    status_code=status.HTTP_201_CREATED,
)
async def crear_repuesto(
    datos: schemas.RepuestoCreate,
    service: ServiceDep,
    admin: AdminDep,
) -> schemas.RepuestoRead:
    service.actor_actual = admin
    return await service.crear(datos)


@router.patch(
    "/{repuesto_id}",
    response_model=schemas.RepuestoRead,
)
async def actualizar_repuesto(
    repuesto_id: int,
    datos: schemas.RepuestoUpdate,
    service: ServiceDep,
    admin: AdminDep,
) -> schemas.RepuestoRead:
    service.actor_actual = admin
    return await service.actualizar(repuesto_id, datos)


@router.delete(
    "/{repuesto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def dar_baja_repuesto(
    repuesto_id: int,
    service: ServiceDep,
    _admin: AdminDep,
) -> None:
    await service.dar_baja(repuesto_id)


@router.post(
    "/{repuesto_id}/reponer",
    response_model=schemas.RepuestoRead,
)
async def reponer_stock(
    repuesto_id: int,
    datos: schemas.ReponerStock,
    service: ServiceDep,
    admin: AdminDep,
) -> schemas.RepuestoRead:
    service.actor_actual = admin
    return await service.reponer(repuesto_id, datos.cantidad)


@router.get(
    "/{repuesto_id}/movimientos",
    response_model=list[schemas.MovimientoStockRead],
)
async def listar_movimientos(
    repuesto_id: int,
    service: ServiceDep,
    _admin: AdminDep,
) -> list[schemas.MovimientoStockRead]:
    return await service.movimientos(repuesto_id)


@router.get(
    "/{repuesto_id}/precios",
    response_model=list[schemas.HistorialPrecioRead],
)
async def listar_precios(
    repuesto_id: int,
    service: ServiceDep,
    _admin: AdminDep,
) -> list[schemas.HistorialPrecioRead]:
    return await service.precios(repuesto_id)
