"""Modelos de tabla del módulo `ordenes`: `estado_orden` (catálogo), `orden_trabajo`,
`item_orden`, `historial_estado_orden` (de sólo agregado: disparador en `0002`).

Los estados NO van en un CHECK: son filas del catálogo apuntadas por FK. El catálogo
nace vacío; lo carga `seed.py` (C-03). Sólo tablas (C-02). Relaciones `lazy="raise_on_sql"`.
"""

import app.core.metadata  # noqa: F401  (convención de nombres; antes de las tablas)

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.clientes.models import Vehiculo
    from app.modules.repuestos.models import MovimientoStock, Repuesto
    from app.modules.usuarios.models import Usuario

_TZ = sa.DateTime(timezone=True)
_AHORA = sa.text("now()")


class EstadoOrden(SQLModel, table=True):
    __tablename__ = "estado_orden"
    __mapper_args__ = {"eager_defaults": True}

    codigo: str = Field(sa_type=sa.Text, primary_key=True)
    descripcion: str = Field(sa_type=sa.Text)
    posicion: int = Field(unique=True)
    es_final: bool

    ordenes: list["OrdenTrabajo"] = Relationship(
        back_populates="estado_catalogo", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
    transiciones_desde: list["HistorialEstadoOrden"] = Relationship(
        back_populates="estado_desde",
        sa_relationship_kwargs={
            "lazy": "raise_on_sql",
            "foreign_keys": "[HistorialEstadoOrden.desde_estado]",
        },
    )
    transiciones_hasta: list["HistorialEstadoOrden"] = Relationship(
        back_populates="estado_hasta",
        sa_relationship_kwargs={
            "lazy": "raise_on_sql",
            "foreign_keys": "[HistorialEstadoOrden.hasta_estado]",
        },
    )


class OrdenTrabajo(SQLModel, table=True):
    __tablename__ = "orden_trabajo"
    __mapper_args__ = {"eager_defaults": True}
    __table_args__ = (sa.CheckConstraint("total >= 0", name="total_no_negativo"),)

    id: int | None = Field(default=None, primary_key=True)
    vehiculo_id: int = Field(foreign_key="vehiculo.id", index=True)
    mecanico_id: int | None = Field(default=None, foreign_key="usuario.id", index=True)
    estado: str = Field(foreign_key="estado_orden.codigo", sa_type=sa.Text, index=True)
    falla: str = Field(sa_type=sa.Text)
    creada_en: datetime | None = Field(
        default=None, sa_type=_TZ, nullable=False, sa_column_kwargs={"server_default": _AHORA}
    )
    total: Decimal = Field(max_digits=12, decimal_places=2)

    vehiculo: "Vehiculo" = Relationship(
        back_populates="ordenes", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
    mecanico: Optional["Usuario"] = Relationship(
        back_populates="ordenes_asignadas", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
    estado_catalogo: EstadoOrden = Relationship(
        back_populates="ordenes", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
    items: list["ItemOrden"] = Relationship(
        back_populates="orden",
        sa_relationship_kwargs={"lazy": "raise_on_sql", "cascade": "all, delete-orphan"},
    )
    historial: list["HistorialEstadoOrden"] = Relationship(
        back_populates="orden", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
    movimientos: list["MovimientoStock"] = Relationship(
        back_populates="orden", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )


class ItemOrden(SQLModel, table=True):
    __tablename__ = "item_orden"
    __mapper_args__ = {"eager_defaults": True}
    __table_args__ = (
        sa.UniqueConstraint("orden_id", "repuesto_id"),
        sa.CheckConstraint("cantidad > 0", name="cantidad_positiva"),
        sa.CheckConstraint("precio_unitario > 0", name="precio_unitario_positivo"),
    )

    id: int | None = Field(default=None, primary_key=True)
    orden_id: int = Field(foreign_key="orden_trabajo.id", index=True)
    repuesto_id: int = Field(foreign_key="repuesto.id", index=True)
    cantidad: int
    precio_unitario: Decimal = Field(max_digits=10, decimal_places=2)

    orden: OrdenTrabajo = Relationship(
        back_populates="items", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
    repuesto: "Repuesto" = Relationship(
        back_populates="items", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )


class HistorialEstadoOrden(SQLModel, table=True):
    __tablename__ = "historial_estado_orden"
    __mapper_args__ = {"eager_defaults": True}

    id: int | None = Field(default=None, primary_key=True)
    orden_id: int = Field(foreign_key="orden_trabajo.id", index=True)
    desde_estado: str | None = Field(
        default=None, foreign_key="estado_orden.codigo", sa_type=sa.Text, index=True
    )
    hasta_estado: str = Field(foreign_key="estado_orden.codigo", sa_type=sa.Text, index=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    cuando: datetime | None = Field(
        default=None, sa_type=_TZ, nullable=False, sa_column_kwargs={"server_default": _AHORA}
    )

    orden: OrdenTrabajo = Relationship(
        back_populates="historial", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
    estado_desde: Optional[EstadoOrden] = Relationship(
        back_populates="transiciones_desde",
        sa_relationship_kwargs={
            "lazy": "raise_on_sql",
            "foreign_keys": "[HistorialEstadoOrden.desde_estado]",
        },
    )
    estado_hasta: EstadoOrden = Relationship(
        back_populates="transiciones_hasta",
        sa_relationship_kwargs={
            "lazy": "raise_on_sql",
            "foreign_keys": "[HistorialEstadoOrden.hasta_estado]",
        },
    )
    usuario: "Usuario" = Relationship(
        back_populates="transiciones", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
