"""Modelos de tabla del módulo `repuestos`: `repuesto`, `movimiento_stock`,
`historial_precio_repuesto` (los dos últimos de sólo agregado: disparador en `0002`).

Sólo tablas (C-02). Relaciones `lazy="raise_on_sql"`; la precarga la declara el repositorio.
"""

import app.core.metadata  # noqa: F401  (convención de nombres; antes de las tablas)

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.ordenes.models import ItemOrden, OrdenTrabajo
    from app.modules.usuarios.models import Usuario

_TZ = sa.DateTime(timezone=True)
_AHORA = sa.text("now()")


class Repuesto(SQLModel, table=True):
    __tablename__ = "repuesto"
    __mapper_args__ = {"eager_defaults": True}
    __table_args__ = (
        sa.CheckConstraint("precio > 0", name="precio_positivo"),
        sa.CheckConstraint("stock >= 0", name="stock_no_negativo"),
        sa.Index(
            "ux_repuesto_codigo_vigente",
            "codigo",
            unique=True,
            postgresql_where=sa.text("borrado_en IS NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    codigo: str = Field(sa_type=sa.Text)
    descripcion: str = Field(sa_type=sa.Text)
    precio: Decimal = Field(max_digits=10, decimal_places=2)
    stock: int
    borrado_en: datetime | None = Field(default=None, sa_type=_TZ, nullable=True)

    movimientos: list["MovimientoStock"] = Relationship(
        back_populates="repuesto", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
    historial_precios: list["HistorialPrecioRepuesto"] = Relationship(
        back_populates="repuesto", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
    items: list["ItemOrden"] = Relationship(
        back_populates="repuesto", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )


class MovimientoStock(SQLModel, table=True):
    __tablename__ = "movimiento_stock"
    __mapper_args__ = {"eager_defaults": True}
    __table_args__ = (sa.CheckConstraint("cantidad > 0", name="cantidad_positiva"),)

    id: int | None = Field(default=None, primary_key=True)
    repuesto_id: int = Field(foreign_key="repuesto.id", index=True)
    orden_id: int | None = Field(default=None, foreign_key="orden_trabajo.id", index=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    cantidad: int
    motivo: str = Field(sa_type=sa.Text)
    cuando: datetime | None = Field(
        default=None, sa_type=_TZ, nullable=False, sa_column_kwargs={"server_default": _AHORA}
    )

    repuesto: Repuesto = Relationship(
        back_populates="movimientos", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
    orden: Optional["OrdenTrabajo"] = Relationship(
        back_populates="movimientos", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
    usuario: "Usuario" = Relationship(
        back_populates="movimientos_stock", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )


class HistorialPrecioRepuesto(SQLModel, table=True):
    __tablename__ = "historial_precio_repuesto"
    __mapper_args__ = {"eager_defaults": True}
    __table_args__ = (
        sa.CheckConstraint("precio_nuevo > 0", name="precio_nuevo_positivo"),
        sa.CheckConstraint("precio_nuevo > precio_anterior", name="precio_nuevo_mayor_anterior"),
    )

    id: int | None = Field(default=None, primary_key=True)
    repuesto_id: int = Field(foreign_key="repuesto.id", index=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    precio_anterior: Decimal = Field(max_digits=10, decimal_places=2)
    precio_nuevo: Decimal = Field(max_digits=10, decimal_places=2)
    cuando: datetime | None = Field(
        default=None, sa_type=_TZ, nullable=False, sa_column_kwargs={"server_default": _AHORA}
    )

    repuesto: Repuesto = Relationship(
        back_populates="historial_precios", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
    usuario: "Usuario" = Relationship(
        back_populates="cambios_precio", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
