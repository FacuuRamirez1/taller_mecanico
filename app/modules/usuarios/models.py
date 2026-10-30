"""Modelos de tabla del módulo `usuarios` (seguridad y personal).

Tablas: `usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad`.
Sólo tablas: nada de schemas de entrada/salida ni enums de API (C-03).
Todas las relaciones son `lazy="raise_on_sql"`: la precarga (`selectinload`)
se declara en el repositorio, nunca carga perezosa.
"""

import app.core.metadata  # noqa: F401  (convención de nombres; antes de las tablas)

from datetime import datetime
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.clientes.models import Cliente
    from app.modules.ordenes.models import HistorialEstadoOrden, OrdenTrabajo
    from app.modules.repuestos.models import HistorialPrecioRepuesto, MovimientoStock

_TZ = sa.DateTime(timezone=True)
_AHORA = sa.text("now()")


class Usuario(SQLModel, table=True):
    __tablename__ = "usuario"
    __mapper_args__ = {"eager_defaults": True}

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(sa_type=sa.Text, unique=True)
    nombre: str = Field(sa_type=sa.Text)
    password_hash: str = Field(sa_type=sa.Text)
    activo: bool = Field(default=True, sa_column_kwargs={"server_default": sa.true()})
    debe_cambiar_password: bool = Field(
        default=False, sa_column_kwargs={"server_default": sa.false()}
    )
    password_cambiada_en: datetime | None = Field(default=None, sa_type=_TZ, nullable=True)

    asignaciones: list["AsignacionRol"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={
            "lazy": "raise_on_sql",
            "foreign_keys": "[AsignacionRol.usuario_id]",
        },
    )
    asignaciones_otorgadas: list["AsignacionRol"] = Relationship(
        back_populates="otorgante",
        sa_relationship_kwargs={
            "lazy": "raise_on_sql",
            "foreign_keys": "[AsignacionRol.otorgada_por]",
        },
    )
    cliente: Optional["Cliente"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={"lazy": "raise_on_sql", "uselist": False},
    )
    ordenes_asignadas: list["OrdenTrabajo"] = Relationship(
        back_populates="mecanico", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
    transiciones: list["HistorialEstadoOrden"] = Relationship(
        back_populates="usuario", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
    movimientos_stock: list["MovimientoStock"] = Relationship(
        back_populates="usuario", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
    cambios_precio: list["HistorialPrecioRepuesto"] = Relationship(
        back_populates="usuario", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )


class AsignacionRol(SQLModel, table=True):
    __tablename__ = "asignacion_rol"
    __mapper_args__ = {"eager_defaults": True}
    __table_args__ = (
        sa.CheckConstraint(
            "rol IN ('ADMIN','RECEPCION','MECANICO','CLIENTE')", name="rol_valido"
        ),
        sa.Index(
            "ux_asignacion_rol_usuario_id_rol_abierta",
            "usuario_id",
            "rol",
            unique=True,
            postgresql_where=sa.text("revocada_en IS NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    rol: str = Field(sa_type=sa.Text)
    desde: datetime | None = Field(
        default=None, sa_type=_TZ, nullable=False, sa_column_kwargs={"server_default": _AHORA}
    )
    vence_en: datetime | None = Field(default=None, sa_type=_TZ, nullable=True)
    revocada_en: datetime | None = Field(default=None, sa_type=_TZ, nullable=True)
    otorgada_por: int | None = Field(default=None, foreign_key="usuario.id", index=True)

    usuario: Usuario = Relationship(
        back_populates="asignaciones",
        sa_relationship_kwargs={
            "lazy": "raise_on_sql",
            "foreign_keys": "[AsignacionRol.usuario_id]",
        },
    )
    otorgante: Optional[Usuario] = Relationship(
        back_populates="asignaciones_otorgadas",
        sa_relationship_kwargs={
            "lazy": "raise_on_sql",
            "foreign_keys": "[AsignacionRol.otorgada_por]",
        },
    )


class IntentoAcceso(SQLModel, table=True):
    __tablename__ = "intento_acceso"
    __mapper_args__ = {"eager_defaults": True}
    __table_args__ = (sa.Index("ix_intento_acceso_email_ip_cuando", "email", "ip", "cuando"),)

    id: int | None = Field(default=None, primary_key=True)
    cuando: datetime | None = Field(
        default=None, sa_type=_TZ, nullable=False, sa_column_kwargs={"server_default": _AHORA}
    )
    email: str = Field(sa_type=sa.Text)
    ip: str = Field(sa_type=sa.Text)
    exito: bool


class EventoSeguridad(SQLModel, table=True):
    __tablename__ = "evento_seguridad"
    __mapper_args__ = {"eager_defaults": True}

    id: int | None = Field(default=None, primary_key=True)
    cuando: datetime | None = Field(
        default=None, sa_type=_TZ, nullable=False, sa_column_kwargs={"server_default": _AHORA}
    )
    actor: str = Field(sa_type=sa.Text)
    accion: str = Field(sa_type=sa.Text)
