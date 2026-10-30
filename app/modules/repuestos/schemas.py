"""Schemas de entrada/salida del módulo `repuestos` (design §D4).

El alta acepta `stock_inicial` y no `stock` (RN-14). `PATCH` sólo admite
descripción y precio. Las entradas rechazan campos no declarados.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RepuestoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str
    descripcion: str
    precio: Decimal = Field(gt=0)
    stock_inicial: int = Field(ge=0)

    @field_validator("codigo")
    @classmethod
    def _normalizar_codigo(cls, valor: str) -> str:
        return valor.strip().upper()


class RepuestoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    descripcion: str | None = None
    precio: Decimal | None = Field(default=None, gt=0)


class RepuestoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    descripcion: str
    precio: Decimal
    stock: int


class ReponerStock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cantidad: int = Field(gt=0)


class MovimientoStockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repuesto_id: int
    orden_id: int | None = None
    usuario_id: int
    cantidad: int
    motivo: str
    cuando: datetime | None = None


class HistorialPrecioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repuesto_id: int
    usuario_id: int
    precio_anterior: Decimal
    precio_nuevo: Decimal
    cuando: datetime | None = None
