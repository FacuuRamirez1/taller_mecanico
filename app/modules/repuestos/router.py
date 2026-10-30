"""Router de repuestos (design §D5).

El router recibe `SessionDep`, construye el servicio y traduce los modelos a
los schemas de salida. Sin lógica de negocio ni consultas acá.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.database import SessionDep
from app.core.paginacion import Pagina, PaginacionDep
from app.modules.repuestos import schemas
from app.modules.repuestos.service import RepuestoService

router = APIRouter(prefix="/repuestos", tags=["repuestos"])


def get_service(session: SessionDep) -> RepuestoService:
    return RepuestoService(session)


ServiceDep = Annotated[RepuestoService, Depends(get_service)]


@router.get("", response_model=Pagina[schemas.RepuestoRead])
async def listar_repuestos(
    service: ServiceDep,
    paginacion: PaginacionDep,
    q: str | None = None,
) -> Pagina[schemas.RepuestoRead]:
    return await service.listar(q=q, page=paginacion.page, size=paginacion.size)


@router.get("/{repuesto_id}", response_model=schemas.RepuestoRead)
async def obtener_repuesto(repuesto_id: int, service: ServiceDep) -> schemas.RepuestoRead:
    return await service.obtener(repuesto_id)


@router.post("", response_model=schemas.RepuestoRead, status_code=status.HTTP_201_CREATED)
async def crear_repuesto(
    datos: schemas.RepuestoCreate, service: ServiceDep
) -> schemas.RepuestoRead:
    return await service.crear(datos)


@router.patch("/{repuesto_id}", response_model=schemas.RepuestoRead)
async def actualizar_repuesto(
    repuesto_id: int, datos: schemas.RepuestoUpdate, service: ServiceDep
) -> schemas.RepuestoRead:
    return await service.actualizar(repuesto_id, datos)


@router.delete("/{repuesto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dar_baja_repuesto(repuesto_id: int, service: ServiceDep) -> None:
    await service.dar_baja(repuesto_id)


@router.post("/{repuesto_id}/reponer", response_model=schemas.RepuestoRead)
async def reponer_stock(
    repuesto_id: int, datos: schemas.ReponerStock, service: ServiceDep
) -> schemas.RepuestoRead:
    return await service.reponer(repuesto_id, datos.cantidad)


@router.get("/{repuesto_id}/movimientos", response_model=list[schemas.MovimientoStockRead])
async def listar_movimientos(
    repuesto_id: int, service: ServiceDep
) -> list[schemas.MovimientoStockRead]:
    return await service.movimientos(repuesto_id)


@router.get("/{repuesto_id}/precios", response_model=list[schemas.HistorialPrecioRead])
async def listar_precios(
    repuesto_id: int, service: ServiceDep
) -> list[schemas.HistorialPrecioRead]:
    return await service.precios(repuesto_id)
