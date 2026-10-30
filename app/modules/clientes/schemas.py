"""Schemas de entrada/salida del módulo `clientes` (design §D4).

`ClienteCreate` no acepta `usuario_id` (Q-11). El año del vehículo se valida
entre 1950 y 2100. Las entradas rechazan campos no declarados.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

ANIO_MINIMO = 1950
ANIO_MAXIMO = 2100


class ClienteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str
    documento: str
    telefono: str


class ClienteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int | None = None
    nombre: str
    documento: str
    telefono: str


class VehiculoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patente: str
    marca: str
    modelo: str
    anio: int = Field(ge=ANIO_MINIMO, le=ANIO_MAXIMO)

    @field_validator("patente")
    @classmethod
    def _normalizar_patente(cls, valor: str) -> str:
        return valor.strip().upper()


class VehiculoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    patente: str
    marca: str
    modelo: str
    anio: int


class ClienteDetalleRead(ClienteRead):
    vehiculos: list[VehiculoRead] = Field(default_factory=list)
