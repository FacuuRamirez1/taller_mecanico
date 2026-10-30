"""Schemas de entrada/salida del módulo `ordenes` (design §D4, C-06).

`OrdenCreate` no acepta `precio`, `total`, `estado` ni `creada_en`: los asigna
el servidor. Las entradas rechazan campos no declarados.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class EstadoOrdenEnum(str, Enum):
    PENDIENTE = "PENDIENTE"
    EN_REPARACION = "EN_REPARACION"
    TERMINADA = "TERMINADA"
    CANCELADA = "CANCELADA"


class ItemOrdenCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repuesto_id: int
    cantidad: int = Field(gt=0)


class OrdenCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vehiculo_id: int
    falla: str
    items: list[ItemOrdenCreate] = Field(min_length=1)


class ItemOrdenRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    orden_id: int
    repuesto_id: int
    cantidad: int
    precio_unitario: Decimal
    codigo: str | None = None
    descripcion: str | None = None
    subtotal: Decimal | None = None


class OrdenRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehiculo_id: int
    mecanico_id: int | None = None
    estado: str
    falla: str
    creada_en: datetime | None = None
    total: Decimal


class EstadoOrdenRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    descripcion: str
    posicion: int
    es_final: bool


class HistorialEstadoOrdenRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    orden_id: int
    desde_estado: str | None = None
    hasta_estado: str
    usuario_id: int
    cuando: datetime | None = None


class OrdenDetalleRead(OrdenRead):
    """Forma del detalle (y del 201 del alta): datos del vehículo, ítems e historial."""

    patente: str | None = None
    cliente: str | None = None
    items: list[ItemOrdenRead] = []
    historial: list[HistorialEstadoOrdenRead] = []
