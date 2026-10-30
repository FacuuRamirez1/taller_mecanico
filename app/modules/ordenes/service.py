"""Servicio del dominio de órdenes de trabajo (design §D1, C-06).

Arquitectura: Router -> Service -> UoW -> Repository -> Model.
El servicio opera sobre `OrdenesUnitOfWork` asegurando transaccionalidad atómica.
"""

import asyncio
from decimal import Decimal
import logging

from fastapi import BackgroundTasks, HTTPException, status

logger = logging.getLogger("taller_mecanico.ordenes")


async def notificar_terminacion_orden(orden_id: int, cliente_nombre: str | None) -> None:
    """Aviso al cliente en segundo plano al terminar la orden (US-036, RN-13).
    
    Se ejecuta después de enviar la respuesta y sólo si la transacción se confirmó.
    """
    await asyncio.sleep(0.5)
    destinatario = cliente_nombre or "cliente"
    logger.info(
        f"[AVISO_SEGUNDO_PLANO] Orden #{orden_id} TERMINADA: Notificación enviada exitosamente a {destinatario}."
    )

from app.core.paginacion import Pagina
from app.modules.ordenes import schemas
from app.modules.ordenes.models import (
    EstadoOrden,
    HistorialEstadoOrden,
    ItemOrden,
    OrdenTrabajo,
)
from app.modules.ordenes.unit_of_work import OrdenesUnitOfWork
from app.modules.repuestos.models import MovimientoStock, Repuesto
from app.modules.usuarios.models import Usuario

ROLES_PERSONAL = {"ADMIN", "RECEPCION", "MECANICO"}
ESTADO_INICIAL = "PENDIENTE"


class OrdenService:
    def __init__(self, uow: OrdenesUnitOfWork) -> None:
        self.uow = uow

    async def _roles_vigentes(self, usuario_id: int) -> list[str]:
        """Roles vigentes del usuario, consultados en cada petición (RBAC)."""
        return await self.uow.roles.listar_vigentes_por_usuario(usuario_id)

    @staticmethod
    def _a_detalle(orden: OrdenTrabajo) -> schemas.OrdenDetalleRead:
        """Arma la forma de detalle (patente, cliente, ítems con subtotal, historial)."""
        vehiculo = orden.vehiculo
        cliente = vehiculo.cliente if vehiculo is not None else None
        items = sorted(orden.items, key=lambda item: item.id or 0)
        historial = sorted(orden.historial, key=lambda linea: (linea.cuando, linea.id or 0))
        return schemas.OrdenDetalleRead(
            id=orden.id,  # type: ignore[arg-type]
            vehiculo_id=orden.vehiculo_id,
            mecanico_id=orden.mecanico_id,
            estado=orden.estado,
            falla=orden.falla,
            creada_en=orden.creada_en,
            total=orden.total,
            patente=vehiculo.patente if vehiculo is not None else None,
            cliente=cliente.nombre if cliente is not None else None,
            items=[
                schemas.ItemOrdenRead(
                    id=item.id,  # type: ignore[arg-type]
                    orden_id=item.orden_id,
                    repuesto_id=item.repuesto_id,
                    cantidad=item.cantidad,
                    precio_unitario=item.precio_unitario,
                    codigo=item.repuesto.codigo if item.repuesto is not None else None,
                    descripcion=(
                        item.repuesto.descripcion if item.repuesto is not None else None
                    ),
                    subtotal=item.precio_unitario * item.cantidad,
                )
                for item in items
            ],
            historial=[
                schemas.HistorialEstadoOrdenRead.model_validate(linea)
                for linea in historial
            ],
        )

    async def listar_estados(self) -> list[EstadoOrden]:
        """Obtiene el catálogo completo de estados de orden ordenado por posición."""
        return await self.uow.estados.listar_por_posicion()

    async def crear(
        self, datos: schemas.OrdenCreate, usuario: Usuario
    ) -> schemas.OrdenDetalleRead:
        """Alta de orden de trabajo (RN-10, Flujo 3).

        - Nace en PENDIENTE.
        - Copia precios de repuestos vigentes y calcula total en el servidor.
        - Vehículo inexistente o dado de baja: 409 (la ruta no tiene `{id}`, no aplica 404).
        - Si el catálogo está vacío responde 409 (RN-19).
        - Si un repuesto no existe o está dado de baja, responde 409 y NO crea la orden (C-10).
        - Escribe la 1.ª línea de historial (null -> PENDIENTE, usuario_id = creador).
        """
        # Verificar catálogo existente (repositorio de sólo lectura del catálogo)
        if await self.uow.estados.get_by_codigo(ESTADO_INICIAL) is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El catálogo de estados no está inicializado",
            )

        # Verificar vehículo vigente (RN-16): 409, no 404, porque el id viene del cuerpo
        vehiculo = await self.uow.vehiculos.get_by_id(datos.vehiculo_id)
        if vehiculo is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El vehículo no existe o está dado de baja",
            )

        # Validar repuestos duplicados en el cuerpo (RN-10)
        repuesto_ids = [item.repuesto_id for item in datos.items]
        if len(repuesto_ids) != len(set(repuesto_ids)):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No se admiten repuestos repetidos en la misma orden",
            )

        # Consultar y validar cada repuesto antes de abrir la transacción de orden
        repuestos_map: dict[int, Repuesto] = {}
        subtotales: list[Decimal] = []
        for item in datos.items:
            rep = await self.uow.repuestos.get_by_id(item.repuesto_id)
            if rep is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"El repuesto con ID {item.repuesto_id} no existe o está dado de baja",
                )
            repuestos_map[item.repuesto_id] = rep
            subtotales.append(Decimal(item.cantidad) * rep.precio)

        total_calculado = sum(subtotales, Decimal("0.00"))

        async with self.uow:
            orden = OrdenTrabajo(
                vehiculo_id=datos.vehiculo_id,
                mecanico_id=None,
                estado=ESTADO_INICIAL,
                falla=datos.falla,
                total=total_calculado,
            )
            await self.uow.ordenes.add(orden)

            for item in datos.items:
                rep = repuestos_map[item.repuesto_id]
                item_orden = ItemOrden(
                    orden_id=orden.id,
                    repuesto_id=item.repuesto_id,
                    cantidad=item.cantidad,
                    precio_unitario=rep.precio,
                )
                await self.uow.items.add(item_orden)

            historial_inicial = HistorialEstadoOrden(
                orden_id=orden.id,
                desde_estado=None,
                hasta_estado=ESTADO_INICIAL,
                usuario_id=usuario.id,  # type: ignore[arg-type]
            )
            await self.uow.historial.add(historial_inicial)

        creada = await self.uow.ordenes.get_by_id_con_relaciones(orden.id)  # type: ignore[arg-type]
        if creada is None:  # pragma: no cover - la orden acaba de confirmarse
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La orden no pudo recuperarse después del alta",
            )
        return self._a_detalle(creada)

    async def obtener(
        self,
        orden_id: int,
        usuario: Usuario,
    ) -> schemas.OrdenDetalleRead:
        """Detalle de una orden con relaciones precargadas sin N+1.

        Permisos: El personal (ADMIN, RECEPCION, MECANICO) o el dueño del vehículo (RN-17).
        """
        roles_vigentes = await self._roles_vigentes(usuario.id)  # type: ignore[arg-type]
        orden = await self.uow.ordenes.get_by_id_con_relaciones(orden_id)
        if orden is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orden de trabajo no encontrada",
            )

        es_personal = bool(ROLES_PERSONAL.intersection(roles_vigentes))
        es_duenio = (
            orden.vehiculo is not None
            and orden.vehiculo.cliente is not None
            and orden.vehiculo.cliente.usuario_id == usuario.id
        )

        if not (es_personal or es_duenio):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permiso denegado: no tiene acceso a esta orden",
            )

        return self._a_detalle(orden)

    async def iniciar(self, orden_id: int, usuario: Usuario) -> OrdenTrabajo:
        """Transición PENDIENTE -> EN_REPARACION asignando mecánico (RN-11)."""
        async with self.uow:
            orden = await self.uow.ordenes.get_by_id(orden_id)
            if orden is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Orden de trabajo no encontrada",
                )

            if orden.estado != "PENDIENTE":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Solo se puede iniciar una orden en estado PENDIENTE (estado actual: {orden.estado})",
                )

            orden.estado = "EN_REPARACION"
            orden.mecanico_id = usuario.id
            await self.uow.ordenes.update(orden)

            historial = HistorialEstadoOrden(
                orden_id=orden.id,
                desde_estado="PENDIENTE",
                hasta_estado="EN_REPARACION",
                usuario_id=usuario.id,  # type: ignore[arg-type]
            )
            await self.uow.historial.add(historial)

        return orden

    async def terminar(
        self,
        orden_id: int,
        usuario: Usuario,
        background_tasks: BackgroundTasks | None = None,
    ) -> OrdenTrabajo:
        """Transición EN_REPARACION -> TERMINADA (RN-11, RN-13).

        - Permiso: Solo mecánico asignado o ADMIN (otro mecánico -> 403).
        - Todo o nada: Valida stock suficiente para cada ítem. Si alguno no alcanza, 409 y nada cambia (C-11).
        - Descuenta stock en punto único (RN-14) y genera un movimiento_stock por ítem.
        - Registra línea en historial y cambia estado a TERMINADA.
        """
        roles_vigentes = await self._roles_vigentes(usuario.id)  # type: ignore[arg-type]
        orden = await self.uow.ordenes.get_by_id_con_relaciones(orden_id)
        if orden is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orden de trabajo no encontrada",
            )

        # Verificación de permisos de actor
        es_admin = "ADMIN" in roles_vigentes
        es_mecanico_asignado = orden.mecanico_id == usuario.id

        if not (es_admin or es_mecanico_asignado):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el mecánico asignado o un administrador pueden terminar la orden",
            )

        if orden.estado != "EN_REPARACION":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Solo se puede terminar una orden en estado EN_REPARACION (estado actual: {orden.estado})",
            )

        # Verificación de stock para TODOS los ítems antes de modificar (RN-13, C-11)
        repuestos_actualizados: list[tuple[Repuesto, int]] = []
        for item in orden.items:
            repuesto = await self.uow.repuestos.get_by_id(item.repuesto_id)
            if repuesto is None or repuesto.stock < item.cantidad:
                disp = repuesto.stock if repuesto is not None else 0
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Stock insuficiente para el repuesto {repuesto.codigo if repuesto else item.repuesto_id}: "
                        f"disponible {disp}, requerido {item.cantidad}"
                    ),
                )
            repuestos_actualizados.append((repuesto, item.cantidad))

        async with self.uow:
            # Descontar stock y registrar movimiento por ítem
            for repuesto, cantidad in repuestos_actualizados:
                await self.uow.repuestos.ajustar_stock(repuesto, delta=-cantidad)
                movimiento = MovimientoStock(
                    repuesto_id=repuesto.id,
                    orden_id=orden.id,
                    usuario_id=usuario.id,  # type: ignore[arg-type]
                    cantidad=cantidad,
                    motivo="Consumo en orden",
                )
                await self.uow.movimientos.add(movimiento)

            orden.estado = "TERMINADA"
            await self.uow.ordenes.update(orden)

            historial = HistorialEstadoOrden(
                orden_id=orden.id,
                desde_estado="EN_REPARACION",
                hasta_estado="TERMINADA",
                usuario_id=usuario.id,  # type: ignore[arg-type]
            )
            await self.uow.historial.add(historial)

        # Aviso en segundo plano (US-036, C-12): agendado después de confirmar la transacción
        if background_tasks is not None:
            cliente_nombre = (
                orden.vehiculo.cliente.nombre
                if orden.vehiculo is not None and orden.vehiculo.cliente is not None
                else None
            )
            background_tasks.add_task(notificar_terminacion_orden, orden.id, cliente_nombre)

        return orden

    async def cancelar(
        self,
        orden_id: int,
        usuario: Usuario,
    ) -> OrdenTrabajo:
        """Cancelación de orden (RN-12).

        Evaluación estricta de orden: 403 antes que 409.
        1. Existe? -> 404
        2. Es RECEPCION, ADMIN o el dueño del vehículo? -> Si no, 403
        3. Está en PENDIENTE? -> Si no, 409
        """
        roles_vigentes = await self._roles_vigentes(usuario.id)  # type: ignore[arg-type]
        orden = await self.uow.ordenes.get_by_id_con_relaciones(orden_id)
        if orden is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orden de trabajo no encontrada",
            )

        es_personal = bool({"ADMIN", "RECEPCION"}.intersection(roles_vigentes))
        es_duenio = (
            orden.vehiculo is not None
            and orden.vehiculo.cliente is not None
            and orden.vehiculo.cliente.usuario_id == usuario.id
        )

        # 403 antes que 409 (RN-12, C-13)
        if not (es_personal or es_duenio):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permiso denegado: no puede cancelar esta orden",
            )

        if orden.estado != "PENDIENTE":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Solo se puede cancelar una orden en estado PENDIENTE (estado actual: {orden.estado})",
            )

        async with self.uow:
            orden.estado = "CANCELADA"
            await self.uow.ordenes.update(orden)

            historial = HistorialEstadoOrden(
                orden_id=orden.id,
                desde_estado="PENDIENTE",
                hasta_estado="CANCELADA",
                usuario_id=usuario.id,  # type: ignore[arg-type]
            )
            await self.uow.historial.add(historial)

        return orden

    async def listar(
        self,
        estado: str | None,
        page: int,
        size: int,
    ) -> Pagina[OrdenTrabajo]:
        """Listado paginado de órdenes filtrado opcionalmente por estado."""
        if estado is not None:
            estados_validos = {e.value for e in schemas.EstadoOrdenEnum}
            if estado not in estados_validos:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Estado inválido: {estado}. Debe ser uno de {sorted(estados_validos)}",
                )

        sentencia = self.uow.ordenes.consulta_listar(estado=estado)
        return await self.uow.ordenes.paginar(sentencia, page, size)

    async def mis_ordenes(
        self,
        usuario_id: int,
        page: int,
        size: int,
    ) -> Pagina[OrdenTrabajo]:
        """Listado paginado de órdenes del cliente autenticado."""
        sentencia = self.uow.ordenes.consulta_mis_ordenes(usuario_id=usuario_id)
        return await self.uow.ordenes.paginar(sentencia, page, size)

