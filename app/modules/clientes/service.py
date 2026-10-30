"""Servicio de clientes y vehículos (design §D7).

Deuda declarada de C-03: el servicio usa `AsyncSession` directa y confirma al
final. C-06 mueve las consultas a repositorios y el `commit` al UnitOfWork sin
cambiar las firmas públicas ni los schemas.
"""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.errores import traducir_integrity_error
from app.modules.clientes import schemas
from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.ordenes.models import EstadoOrden, OrdenTrabajo

# TODO C-06: mover consultas a repositorios y `commit` al UnitOfWork (firmas estables).


class ClienteService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def crear_cliente(self, datos: schemas.ClienteCreate) -> Cliente:
        cliente = Cliente(
            nombre=datos.nombre,
            documento=datos.documento,
            telefono=datos.telefono,
            usuario_id=None,
        )
        self.session.add(cliente)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise traducir_integrity_error(exc) from None
        return cliente

    async def obtener_cliente(self, cliente_id: int) -> schemas.ClienteDetalleRead:
        sentencia = (
            select(Cliente)
            .options(selectinload(Cliente.vehiculos))
            .where(Cliente.id == cliente_id)
        )
        cliente = await self.session.scalar(sentencia)
        if cliente is None:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
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
        cliente = await self.session.scalar(
            select(Cliente).where(Cliente.id == cliente_id)
        )
        if cliente is None:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        vehiculo = Vehiculo(
            cliente_id=cliente_id,
            patente=datos.patente,
            marca=datos.marca,
            modelo=datos.modelo,
            anio=datos.anio,
        )
        self.session.add(vehiculo)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise traducir_integrity_error(exc) from None
        return vehiculo

    async def dar_baja_vehiculo(self, vehiculo_id: int) -> None:
        vehiculo = await self.session.scalar(
            select(Vehiculo).where(
                Vehiculo.id == vehiculo_id,
                Vehiculo.borrado_en.is_(None),
            )
        )
        if vehiculo is None:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado")

        orden_abierta = await self.session.scalar(
            select(OrdenTrabajo.id)
            .join(EstadoOrden, OrdenTrabajo.estado == EstadoOrden.codigo)
            .where(
                OrdenTrabajo.vehiculo_id == vehiculo_id,
                EstadoOrden.es_final.is_(False),
            )
            .limit(1)
        )
        if orden_abierta is not None:
            raise HTTPException(
                status_code=409,
                detail="No se puede dar de baja un vehículo con órdenes abiertas",
            )

        vehiculo.borrado_en = datetime.now(timezone.utc)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise traducir_integrity_error(exc) from None

    async def mis_vehiculos(self) -> list[schemas.VehiculoRead]:
        # TODO C-05: inyectar el usuario autenticado y filtrar por su cliente.
        return []

