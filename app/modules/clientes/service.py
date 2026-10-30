"""Servicio de clientes y vehículos (design §D7, C-06).

Arquitectura: Router -> Service -> UoW -> Repository -> Model.
El servicio opera sobre `ClientesUnitOfWork` y no accede directamente a la sesión.
"""

from fastapi import HTTPException, status

from app.modules.clientes import schemas
from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.clientes.unit_of_work import ClientesUnitOfWork


class ClienteService:
    def __init__(self, uow: ClientesUnitOfWork) -> None:
        self.uow = uow

    async def crear_cliente(self, datos: schemas.ClienteCreate) -> Cliente:
        async with self.uow:
            cliente = Cliente(
                nombre=datos.nombre,
                documento=datos.documento,
                telefono=datos.telefono,
                usuario_id=None,
            )
            await self.uow.clientes.add(cliente)
        return cliente

    async def obtener_cliente(self, cliente_id: int) -> schemas.ClienteDetalleRead:
        cliente = await self.uow.clientes.get_by_id_con_vehiculos(cliente_id)
        if cliente is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente no encontrado",
            )
        vehiculos_vigentes = [
            schemas.VehiculoRead.model_validate(v)
            for v in cliente.vehiculos
            if v.borrado_en is None
        ]
        return schemas.ClienteDetalleRead(
            id=cliente.id,  # type: ignore[arg-type]
            usuario_id=cliente.usuario_id,
            nombre=cliente.nombre,
            documento=cliente.documento,
            telefono=cliente.telefono,
            vehiculos=vehiculos_vigentes,
        )

    async def crear_vehiculo(
        self, cliente_id: int, datos: schemas.VehiculoCreate
    ) -> Vehiculo:
        async with self.uow:
            cliente = await self.uow.clientes.get_by_id(cliente_id)
            if cliente is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cliente no encontrado",
                )

            vehiculo = Vehiculo(
                cliente_id=cliente_id,
                patente=datos.patente,
                marca=datos.marca,
                modelo=datos.modelo,
                anio=datos.anio,
            )
            await self.uow.vehiculos.add(vehiculo)
        return vehiculo

    async def dar_baja_vehiculo(self, vehiculo_id: int) -> None:
        async with self.uow:
            vehiculo = await self.uow.vehiculos.get_by_id(vehiculo_id)
            if vehiculo is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Vehículo no encontrado",
                )

            if await self.uow.vehiculos.tiene_ordenes_abiertas(vehiculo_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No se puede dar de baja un vehículo con órdenes abiertas",
                )

            await self.uow.vehiculos.soft_delete(vehiculo)

    async def mis_vehiculos(self, usuario_id: int) -> list[Vehiculo]:
        cliente = await self.uow.clientes.get_by_usuario_id(usuario_id)
        if cliente is None:
            return []
        return await self.uow.vehiculos.listar_vigentes_por_cliente(cliente.id)  # type: ignore[arg-type]
