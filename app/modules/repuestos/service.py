"""Servicio de repuestos (design §D6, C-06).

Arquitectura: Router -> Service -> UoW -> Repository -> Model.
El servicio recibe el UnitOfWork (construido por el router vía inyección de dependencias)
y lo abre con `async with self.uow:`. NUNCA construye el UoW ni ejecuta commit() directo.
"""

from decimal import Decimal

from fastapi import HTTPException, status

from app.core.paginacion import Pagina
from app.modules.repuestos.models import (
    HistorialPrecioRepuesto,
    MovimientoStock,
    Repuesto,
)
from app.modules.repuestos.schemas import RepuestoCreate, RepuestoUpdate
from app.modules.repuestos.unit_of_work import RepuestosUnitOfWork
from app.modules.usuarios.models import Usuario


class RepuestoService:
    def __init__(self, uow: RepuestosUnitOfWork, actor_actual: Usuario | None = None) -> None:
        self.uow = uow
        self.actor_actual = actor_actual

    async def _actor(self) -> Usuario:
        """Actor que firma el movimiento o la línea de historial.

        El router lo inyecta cuando la ruta es de ADMIN; si no llegó, se resuelve
        por el repositorio de usuarios (el servicio nunca toca la sesión).
        """
        if self.actor_actual is not None:
            return self.actor_actual

        usuario = await self.uow.usuarios.obtener_actor_por_defecto()
        if usuario is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No hay un usuario administrador para registrar la operación",
            )
        return usuario

    async def _obtener_vigente(self, repuesto_id: int) -> Repuesto:
        repuesto = await self.uow.repuestos.get_by_id(repuesto_id)
        if repuesto is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repuesto no encontrado",
            )
        return repuesto

    async def listar(self, q: str | None, page: int, size: int) -> Pagina[Repuesto]:
        sentencia = self.uow.repuestos.consulta_listar(q=q)
        return await self.uow.repuestos.paginar(sentencia, page, size)

    async def obtener(self, repuesto_id: int) -> Repuesto:
        return await self._obtener_vigente(repuesto_id)

    async def crear(self, datos: RepuestoCreate) -> Repuesto:
        actor = await self._actor()
        async with self.uow:
            repuesto = Repuesto(
                codigo=datos.codigo,
                descripcion=datos.descripcion,
                precio=datos.precio,
                stock=datos.stock_inicial,
            )
            await self.uow.repuestos.add(repuesto)
            if datos.stock_inicial > 0:
                movimiento = MovimientoStock(
                    repuesto_id=repuesto.id,
                    orden_id=None,
                    usuario_id=actor.id,
                    cantidad=datos.stock_inicial,
                    motivo="Stock inicial",
                )
                await self.uow.movimientos.add(movimiento)
        return repuesto

    async def actualizar(self, repuesto_id: int, datos: RepuestoUpdate) -> Repuesto:
        async with self.uow:
            repuesto = await self._obtener_vigente(repuesto_id)
            cambios = datos.model_dump(exclude_unset=True)

            precio_nuevo: Decimal | None = cambios.get("precio")
            if precio_nuevo is not None and precio_nuevo != repuesto.precio:
                # Regla IN-05 / Q-10: baja de precio -> 422
                if precio_nuevo < repuesto.precio:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="El precio no puede ser menor que el actual",
                    )
                actor = await self._actor()
                historial = HistorialPrecioRepuesto(
                    repuesto_id=repuesto.id,
                    usuario_id=actor.id,
                    precio_anterior=repuesto.precio,
                    precio_nuevo=precio_nuevo,
                )
                await self.uow.precios.add(historial)
                repuesto.precio = precio_nuevo

            descripcion = cambios.get("descripcion")
            if descripcion is not None:
                repuesto.descripcion = descripcion

            await self.uow.repuestos.update(repuesto)
        return repuesto

    async def dar_baja(self, repuesto_id: int) -> None:
        async with self.uow:
            repuesto = await self._obtener_vigente(repuesto_id)
            await self.uow.repuestos.soft_delete(repuesto)

    async def reponer(self, repuesto_id: int, cantidad: int) -> Repuesto:
        async with self.uow:
            repuesto = await self._obtener_vigente(repuesto_id)
            actor = await self._actor()
            await self.uow.repuestos.ajustar_stock(repuesto, delta=cantidad)
            movimiento = MovimientoStock(
                repuesto_id=repuesto.id,
                orden_id=None,
                usuario_id=actor.id,
                cantidad=cantidad,
                motivo="Reposición",
            )
            await self.uow.movimientos.add(movimiento)
        return repuesto

    async def movimientos(self, repuesto_id: int) -> list[MovimientoStock]:
        await self._obtener_vigente(repuesto_id)
        return await self.uow.movimientos.listar_por_repuesto(repuesto_id)

    async def precios(self, repuesto_id: int) -> list[HistorialPrecioRepuesto]:
        await self._obtener_vigente(repuesto_id)
        return await self.uow.precios.listar_por_repuesto(repuesto_id)