"""Schemas de entrada/salida del módulo `usuarios` (design §D4).

Separados de los modelos de tabla. Toda entrada rechaza campos no declarados;
ninguna salida expone el hash de contraseña. Las contraseñas exigen al menos
8 caracteres y no superan 72 bytes en UTF-8.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator

PASSWORD_LARGO_MINIMO = 8
PASSWORD_BYTES_MAXIMO = 72


def validar_password(valor: str) -> str:
    """Mínimo 8 caracteres y máximo 72 bytes UTF-8 (límite de bcrypt)."""
    if len(valor) < PASSWORD_LARGO_MINIMO:
        raise ValueError(f"La contraseña debe tener al menos {PASSWORD_LARGO_MINIMO} caracteres")
    if len(valor.encode("utf-8")) > PASSWORD_BYTES_MAXIMO:
        raise ValueError(f"La contraseña no puede superar {PASSWORD_BYTES_MAXIMO} bytes en UTF-8")
    return valor


def validar_password_max_bytes(valor: str) -> str:
    """Máximo 72 bytes UTF-8 (límite de bcrypt)."""
    if len(valor.encode("utf-8")) > PASSWORD_BYTES_MAXIMO:
        raise ValueError(f"La contraseña no puede superar {PASSWORD_BYTES_MAXIMO} bytes en UTF-8")
    return valor


class RolEnum(str, Enum):
    ADMIN = "ADMIN"
    RECEPCION = "RECEPCION"
    MECANICO = "MECANICO"
    CLIENTE = "CLIENTE"


class UsuarioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    nombre: str
    password: str
    rol: RolEnum | None = None

    _validar_password = field_validator("password")(validar_password)


class RegistroRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str
    nombre: str
    documento: str
    telefono: str

    _validar_password = field_validator("password")(validar_password)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str

    _validar_password = field_validator("password")(validar_password_max_bytes)


class LoginResponse(BaseModel):
    mensaje: str
    debe_cambiar_password: bool
    expira_en_segundos: int


class UsuarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nombre: str
    activo: bool
    debe_cambiar_password: bool
    password_cambiada_en: datetime | None = None


class UsuarioYoResponse(BaseModel):
    id: int
    email: str
    nombre: str
    activo: bool
    debe_cambiar_password: bool
    roles: list[str]
    roles_token: list[str]


class AsignacionRolCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rol: RolEnum


class AsignacionRolRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    rol: RolEnum
    desde: datetime | None = None
    vence_en: datetime | None = None
    revocada_en: datetime | None = None
    otorgada_por: int | None = None


class CambioPassword(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password_actual: str
    password_nueva: str

    _validar_password_actual = field_validator("password_actual")(validar_password_max_bytes)
    _validar_password_nueva = field_validator("password_nueva")(validar_password)


class MensajeResponse(BaseModel):
    mensaje: str
