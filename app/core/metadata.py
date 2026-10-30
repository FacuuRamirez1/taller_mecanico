"""Convención de nombres de restricciones e índices (Alembic/PostgreSQL).

Módulo sin I/O: sólo asigna la convención a `SQLModel.metadata`. Cada
`models.py` lo importa ANTES de declarar tablas para que rija sin importar
el orden de importación. Sin convención, PostgreSQL inventa nombres y
`autogenerate` no puede nombrar las restricciones en el `downgrade`.
"""

from sqlmodel import SQLModel

NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "ix": "ix_%(column_0_label)s",
}

SQLModel.metadata.naming_convention = NAMING_CONVENTION
