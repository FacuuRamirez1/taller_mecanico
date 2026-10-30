"""Carga idempotente del estado inicial conocido (design §D9).

Vacía las 13 tablas con `TRUNCATE ... RESTART IDENTITY CASCADE` (el disparador
de sólo agregado rechaza `DELETE`) y las vuelve a cargar en orden de
dependencias. Dos corridas seguidas dejan exactamente el mismo estado.

Asume que `alembic upgrade head` ya creó el esquema: no crea tablas.
Las contraseñas son ficticias y viven sólo en este archivo.
"""

import asyncio
from decimal import Decimal

from sqlalchemy import text

from app.core.config import Settings
from app.core.database import crear_engine, crear_sessionmaker
from app.core.security import hash_password
from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.ordenes.models import (
    EstadoOrden,
    HistorialEstadoOrden,
    ItemOrden,
    OrdenTrabajo,
)
from app.modules.repuestos.models import (
    HistorialPrecioRepuesto,
    MovimientoStock,
    Repuesto,
)
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, Usuario

PASSWORD_FICTICIA = "demo-taller-2026"

TRUNCAR = (
    "TRUNCATE TABLE historial_estado_orden, item_orden, movimiento_stock, "
    "historial_precio_repuesto, orden_trabajo, vehiculo, cliente, repuesto, "
    "asignacion_rol, intento_acceso, evento_seguridad, usuario, estado_orden "
    "RESTART IDENTITY CASCADE"
)

ESTADOS = (
    ("PENDIENTE", "Pendiente de reparación", 1, False),
    ("EN_REPARACION", "En reparación", 2, False),
    ("TERMINADA", "Terminada", 3, True),
    ("CANCELADA", "Cancelada", 4, True),
)

USUARIOS = (
    ("admin@example.com", "Administrador", "ADMIN", False),
    ("admin2@example.com", "Segundo Administrador", "ADMIN", False),
    ("recepcion@example.com", "Recepción", "RECEPCION", False),
    ("mecanico@example.com", "Mecánico", "MECANICO", False),
    ("mecanico2@example.com", "Segundo Mecánico", "MECANICO", False),
    ("cliente@example.com", "Laura Gómez", "CLIENTE", False),
    ("nuevo@example.com", "Usuario Nuevo", "MECANICO", True),
)

REPUESTOS = (
    ("FIL-001", "Filtro de aceite", Decimal("8500.00"), 10),
    ("FRE-010", "Pastillas de freno", Decimal("45000.00"), 4),
    ("BUJ-001", "Bujía", Decimal("3200.00"), 2),
    ("ACE-530", "Aceite por litro", Decimal("9000.00"), 20),
)


async def main() -> None:
    settings = Settings()
    engine = crear_engine(settings)
    sessionmaker = crear_sessionmaker(engine)
    try:
        hash_ficticio = await hash_password(PASSWORD_FICTICIA, settings.BCRYPT_COST)
        async with sessionmaker() as session:
            await session.execute(text(TRUNCAR))

            for codigo, descripcion, posicion, es_final in ESTADOS:
                session.add(
                    EstadoOrden(
                        codigo=codigo,
                        descripcion=descripcion,
                        posicion=posicion,
                        es_final=es_final,
                    )
                )
            await session.flush()

            usuarios: dict[str, Usuario] = {}
            for email, nombre, _rol, debe_cambiar in USUARIOS:
                usuario = Usuario(
                    email=email,
                    nombre=nombre,
                    password_hash=hash_ficticio,
                    debe_cambiar_password=debe_cambiar,
                )
                session.add(usuario)
                usuarios[email] = usuario
            await session.flush()

            admin = usuarios["admin@example.com"]
            for email, _nombre, rol, _debe_cambiar in USUARIOS:
                session.add(
                    AsignacionRol(
                        usuario_id=usuarios[email].id,
                        rol=rol,
                        otorgada_por=admin.id,
                    )
                )

            laura = Cliente(
                usuario_id=usuarios["cliente@example.com"].id,
                nombre="Laura Gómez",
                documento="30111222",
                telefono="11-5555-0101",
            )
            jorge = Cliente(
                usuario_id=None,
                nombre="Jorge Pérez",
                documento="27888999",
                telefono="11-5555-0202",
            )
            session.add(laura)
            session.add(jorge)
            await session.flush()

            corolla = Vehiculo(
                cliente_id=laura.id,
                patente="AC456EF",
                marca="Toyota",
                modelo="Corolla",
                anio=2020,
            )
            focus = Vehiculo(
                cliente_id=laura.id,
                patente="AB123CD",
                marca="Ford",
                modelo="Focus",
                anio=2018,
            )
            cronos = Vehiculo(
                cliente_id=jorge.id,
                patente="AA111AA",
                marca="Fiat",
                modelo="Cronos",
                anio=2021,
            )
            session.add(corolla)
            session.add(focus)
            session.add(cronos)
            await session.flush()

            repuestos: dict[str, Repuesto] = {}
            for codigo, descripcion, precio, stock in REPUESTOS:
                repuesto = Repuesto(
                    codigo=codigo,
                    descripcion=descripcion,
                    precio=precio,
                    stock=stock,
                )
                session.add(repuesto)
                repuestos[codigo] = repuesto
            await session.flush()

            for codigo, _descripcion, _precio, stock in REPUESTOS:
                session.add(
                    MovimientoStock(
                        repuesto_id=repuestos[codigo].id,
                        orden_id=None,
                        usuario_id=admin.id,
                        cantidad=stock,
                        motivo="Stock inicial",
                    )
                )

            recepcion = usuarios["recepcion@example.com"]
            mecanico = usuarios["mecanico@example.com"]

            orden_1 = OrdenTrabajo(
                vehiculo_id=corolla.id,
                mecanico_id=None,
                estado="PENDIENTE",
                falla="Ruido en el motor",
                total=Decimal("8500.00"),
            )
            orden_2 = OrdenTrabajo(
                vehiculo_id=cronos.id,
                mecanico_id=mecanico.id,
                estado="EN_REPARACION",
                falla="Cambio de bujías",
                total=Decimal("12800.00"),
            )
            session.add(orden_1)
            session.add(orden_2)
            await session.flush()

            session.add(
                ItemOrden(
                    orden_id=orden_1.id,
                    repuesto_id=repuestos["FIL-001"].id,
                    cantidad=1,
                    precio_unitario=Decimal("8500.00"),
                )
            )
            session.add(
                ItemOrden(
                    orden_id=orden_2.id,
                    repuesto_id=repuestos["BUJ-001"].id,
                    cantidad=4,
                    precio_unitario=Decimal("3200.00"),
                )
            )

            session.add(
                HistorialEstadoOrden(
                    orden_id=orden_1.id,
                    desde_estado=None,
                    hasta_estado="PENDIENTE",
                    usuario_id=recepcion.id,
                )
            )
            session.add(
                HistorialEstadoOrden(
                    orden_id=orden_2.id,
                    desde_estado=None,
                    hasta_estado="PENDIENTE",
                    usuario_id=recepcion.id,
                )
            )
            session.add(
                HistorialEstadoOrden(
                    orden_id=orden_2.id,
                    desde_estado="PENDIENTE",
                    hasta_estado="EN_REPARACION",
                    usuario_id=mecanico.id,
                )
            )

            session.add(
                HistorialPrecioRepuesto(
                    repuesto_id=repuestos["FIL-001"].id,
                    usuario_id=admin.id,
                    precio_anterior=Decimal("8000.00"),
                    precio_nuevo=Decimal("8500.00"),
                )
            )

            session.add(
                EventoSeguridad(actor="SISTEMA", accion="Carga de los datos iniciales")
            )

            await session.commit()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
