"""Configuración de la aplicación (pydantic-settings).

Una sola fuente de verdad: la comparten uvicorn (lifespan) y Alembic (env.py).
Ningún `Settings()` a nivel de módulo: se instancia en el lifespan.
Los secretos no tienen valor por defecto y nunca aparecen en repr/errores.
"""

from pydantic import Field, SecretStr, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

PLACEHOLDER_SECRETO = "CAMBIAR_EN_TU_.env"
JWT_LARGO_MINIMO = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    POSTGRES_USER: str
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    JWT_SECRET_KEY: SecretStr
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_SECONDS: int = 1800

    BCRYPT_COST: int = Field(default=12, ge=4, le=31)
    DB_POOL_SIZE: int = Field(default=5, ge=1)
    SQL_ECHO: bool = False
    COOKIE_SECURE: bool = False

    @field_validator("POSTGRES_PASSWORD", "JWT_SECRET_KEY")
    @classmethod
    def _validar_secreto(cls, v: SecretStr, info) -> SecretStr:
        nombre = info.field_name
        valor = v.get_secret_value()
        if not valor.strip():
            raise ValueError(f"{nombre} no puede estar vacío")
        if valor == PLACEHOLDER_SECRETO:
            raise ValueError(f"{nombre} sigue con el valor de ejemplo; completalo en tu .env")
        if nombre == "JWT_SECRET_KEY" and len(valor) < JWT_LARGO_MINIMO:
            raise ValueError(f"{nombre} debe tener al menos {JWT_LARGO_MINIMO} caracteres")
        return v

    @computed_field(repr=False)  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        return URL.create(
            "postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD.get_secret_value(),
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        ).render_as_string(hide_password=False)
