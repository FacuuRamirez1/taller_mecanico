"""solo_agregado

Disparador de sólo agregado sobre `historial_estado_orden`, `movimiento_stock` y
`historial_precio_repuesto` (RN-15): cualquier UPDATE o DELETE se rechaza, venga de
donde venga. TRUNCATE no se bloquea (la consigna pide UPDATE y DELETE).

Leída antes de aplicarla (C-02) — revisó: Facundo Ramírez. Escrita a mano (sin autogenerate); SQL constante, sin datos externos.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-30 00:54:29.193959

"""

from typing import Sequence, Union

from alembic import op


# Identificadores de la revisión, usados por Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Leída antes de aplicarla (C-02) — revisó: agente OPSX apply (Claude).
def upgrade() -> None:
    # SQLSTATE por defecto de RAISE EXCEPTION (P0001): no se confunde con una
    # violación de integridad (clase 23) que la app traduce a 409. Sin datos de la fila.
    op.execute(
        """
        CREATE FUNCTION rechazar_cambio_solo_agregado() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'La tabla % es de sólo agregado: % no permitido', TG_TABLE_NAME, TG_OP;
        END;
        $$
        """
    )
    # FOR EACH ROW: un UPDATE/DELETE que no afecta filas no falla.
    op.execute(
        "CREATE TRIGGER trg_historial_estado_orden_solo_agregado "
        "BEFORE UPDATE OR DELETE ON historial_estado_orden "
        "FOR EACH ROW EXECUTE FUNCTION rechazar_cambio_solo_agregado()"
    )
    op.execute(
        "CREATE TRIGGER trg_movimiento_stock_solo_agregado "
        "BEFORE UPDATE OR DELETE ON movimiento_stock "
        "FOR EACH ROW EXECUTE FUNCTION rechazar_cambio_solo_agregado()"
    )
    op.execute(
        "CREATE TRIGGER trg_historial_precio_repuesto_solo_agregado "
        "BEFORE UPDATE OR DELETE ON historial_precio_repuesto "
        "FOR EACH ROW EXECUTE FUNCTION rechazar_cambio_solo_agregado()"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_historial_precio_repuesto_solo_agregado "
        "ON historial_precio_repuesto"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_movimiento_stock_solo_agregado ON movimiento_stock"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_historial_estado_orden_solo_agregado "
        "ON historial_estado_orden"
    )
    op.execute("DROP FUNCTION IF EXISTS rechazar_cambio_solo_agregado()")
