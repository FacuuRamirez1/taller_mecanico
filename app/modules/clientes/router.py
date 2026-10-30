"""Router de clientes y vehículos (design §D5).

El router recibe `SessionDep`, construye el servicio y traduce los modelos a
los schemas de salida. Sin lógica de negocio ni consultas acá.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.database import SessionDep
from app.modules.clientes import schemas
from app.modules.clientes.service import ClienteService

clientes_router = APIRouter(prefix="/clientes", tags=["clientes"])
vehiculos_router = APIRouter(prefix="/vehiculos", tags=["vehiculos"])
mis_vehiculos_router = APIRouter(tags=["vehiculos"])


def get_service(session: SessionDep) -> ClienteService:
    return ClienteService(session)


ServiceDep = Annotated[ClienteService, Depends(get_service)]


@clientes_router.post(
    "",
    response_model=schemas.ClienteRead,
    status_code=status.HTTP_201_CREATED,
)
async def crear_cliente(
    datos: schemas.ClienteCreate, service: ServiceDep
) -> schemas.ClienteRead:
    return await service.crear_cliente(datos)


@clientes_router.get("/{cliente_id}", response_model=schemas.ClienteDetalleRead)
async def obtener_cliente(
    cliente_id: int, service: ServiceDep
) -> schemas.ClienteDetalleRead:
    return await service.obtener_cliente(cliente_id)


@clientes_router.post(
    "/{cliente_id}/vehiculos",
    response_model=schemas.VehiculoRead,
    status_code=status.HTTP_201_CREATED,
)
async def crear_vehiculo(
    cliente_id: int, datos: schemas.VehiculoCreate, service: ServiceDep
) -> schemas.VehiculoRead:
    return await service.crear_vehiculo(cliente_id, datos)


@vehiculos_router.delete("/{vehiculo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dar_baja_vehiculo(vehiculo_id: int, service: ServiceDep) -> None:
    await service.dar_baja_vehiculo(vehiculo_id)


@mis_vehiculos_router.get("/mis-vehiculos", response_model=list[schemas.VehiculoRead])
async def mis_vehiculos(service: ServiceDep) -> list[schemas.VehiculoRead]:
    return await service.mis_vehiculos()

