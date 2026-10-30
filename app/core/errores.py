"""Traducción de `IntegrityError` a respuestas propias (design §D3).

El nombre de la constraint se lee del error original (con respaldo en `diag`)
y se busca en el mapa. Nunca se expone el texto interno de PostgreSQL ni la
traza: sólo el mensaje propio. Una constraint desconocida cae en un 409
genérico.
"""

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

MENSAJE_GENERICO = "No se pudo completar la operación por un conflicto de datos"

MAPA_CONSTRAINTS: dict[str, tuple[int, str]] = {
    "uq_usuario_email": (409, "Ya existe un usuario con ese email"),
    "uq_cliente_documento": (409, "Ya existe un cliente con ese documento"),
    "uq_cliente_usuario_id": (409, "Ese usuario ya tiene una ficha de cliente"),
    "ux_vehiculo_patente_vigente": (409, "Ya existe un vehículo vigente con esa patente"),
    "ux_repuesto_codigo_vigente": (409, "Ya existe un repuesto vigente con ese código"),
    "ck_repuesto_precio_positivo": (422, "El precio debe ser mayor que cero"),
    "ck_repuesto_stock_no_negativo": (422, "El stock no puede ser negativo"),
    "ck_movimiento_stock_cantidad_positiva": (422, "La cantidad debe ser mayor que cero"),
    "ck_historial_precio_repuesto_precio_nuevo_mayor_anterior": (
        422,
        "El nuevo precio debe ser mayor que el anterior",
    ),
    "ck_vehiculo_anio_rango": (422, "El año del vehículo debe estar entre 1950 y 2100"),
    "fk_orden_trabajo_estado_estado_orden": (409, "El estado indicado no existe en el catálogo"),
}


def _nombre_constraint(exc: IntegrityError) -> str | None:
    orig = exc.orig
    causa = getattr(orig, "__cause__", None)
    nombre = getattr(causa, "constraint_name", None)
    if nombre:
        return nombre
    diag = getattr(orig, "diag", None)
    if diag is not None:
        return getattr(diag, "constraint_name", None)
    return None


def traducir_integrity_error(exc: IntegrityError) -> HTTPException:
    """Devuelve la `HTTPException` que corresponde a la constraint violada."""
    nombre = _nombre_constraint(exc)
    status, mensaje = MAPA_CONSTRAINTS.get(nombre, (409, MENSAJE_GENERICO))
    return HTTPException(status_code=status, detail=mensaje)
