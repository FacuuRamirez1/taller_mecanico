"""Modelos de tabla del módulo `clientes`: `cliente` y `vehiculo`.

Sólo tablas (C-02). Relaciones `lazy="raise_on_sql"`; la precarga la declara el repositorio.
"""

import app.core.metadata  # noqa: F401  (convención de nombres; antes de las tablas)

from datetime import datetime
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.ordenes.models import OrdenTrabajo
    from app.modules.usuarios.models import Usuario


class Cliente(SQLModel, table=True):
    __tablename__ = "cliente"
    __mapper_args__ = {"eager_defaults": True}

    id: int | None = Field(default=None, primary_key=True)
    # El índice de esta FK es el del UNIQUE (1:1 opcional); nulo permitido.
    usuario_id: int | None = Field(default=None, foreign_key="usuario.id", unique=True)
    nombre: str = Field(sa_type=sa.Text)
    documento: str = Field(sa_type=sa.Text, unique=True)
    telefono: str = Field(sa_type=sa.Text)

    usuario: Optional["Usuario"] = Relationship(
        back_populates="cliente", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
    vehiculos: list["Vehiculo"] = Relationship(
        back_populates="cliente", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )


class Vehiculo(SQLModel, table=True):
    __tablename__ = "vehiculo"
    __mapper_args__ = {"eager_defaults": True}
    __table_args__ = (
        sa.CheckConstraint("anio BETWEEN 1950 AND 2100", name="anio_rango"),
        sa.Index(
            "ux_vehiculo_patente_vigente",
            "patente",
            unique=True,
            postgresql_where=sa.text("borrado_en IS NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id", index=True)
    patente: str = Field(sa_type=sa.Text)
    marca: str = Field(sa_type=sa.Text)
    modelo: str = Field(sa_type=sa.Text)
    anio: int
    borrado_en: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True), nullable=True
    )

    cliente: Cliente = Relationship(
        back_populates="vehiculos", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
    ordenes: list["OrdenTrabajo"] = Relationship(
        back_populates="vehiculo", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
