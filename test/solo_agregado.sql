-- ============================================================================
-- Evidencia Caso C-14: Garantías de Integridad y Sólo Agregado (Ej. 7, US-033)
-- ============================================================================
-- Este script verifica directamente en PostgreSQL (vía psql) que el disparador
-- 'trg_*_solo_agregado' instalado en la migración 0002_solo_agregado.py
-- rechaza cualquier sentencia UPDATE o DELETE sobre las 3 tablas de sólo agregado:
--   1. historial_estado_orden
--   2. movimiento_stock
--   3. historial_precio_repuesto
-- Además, verifica que la integridad referencial (Foreign Key) rechaza la inserción
-- de una orden con un estado fuera del catálogo (estado_orden).
--
-- Ejecución recomendada:
--   psql -U postgres -d taller_mecanico -f test/solo_agregado.sql
-- ============================================================================

\echo '--- 1. UPDATE sobre historial_estado_orden (Debe fallar por disparador) ---'
UPDATE historial_estado_orden SET hasta_estado = 'CANCELADA' WHERE id = 1;
-- ERROR:  La tabla historial_estado_orden es de sólo agregado: UPDATE no permitido
-- CONTEXT:  función PL/pgSQL rechazar_cambio_solo_agregado() línea 3 en RAISE

\echo '--- 2. DELETE sobre historial_estado_orden (Debe fallar por disparador) ---'
DELETE FROM historial_estado_orden WHERE id = 1;
-- ERROR:  La tabla historial_estado_orden es de sólo agregado: DELETE no permitido
-- CONTEXT:  función PL/pgSQL rechazar_cambio_solo_agregado() línea 3 en RAISE

\echo '--- 3. UPDATE sobre movimiento_stock (Debe fallar por disparador) ---'
UPDATE movimiento_stock SET cantidad = 999 WHERE id = 1;
-- ERROR:  La tabla movimiento_stock es de sólo agregado: UPDATE no permitido
-- CONTEXT:  función PL/pgSQL rechazar_cambio_solo_agregado() línea 3 en RAISE

\echo '--- 4. DELETE sobre movimiento_stock (Debe fallar por disparador) ---'
DELETE FROM movimiento_stock WHERE id = 1;
-- ERROR:  La tabla movimiento_stock es de sólo agregado: DELETE no permitido
-- CONTEXT:  función PL/pgSQL rechazar_cambio_solo_agregado() línea 3 en RAISE

\echo '--- 5. UPDATE sobre historial_precio_repuesto (Debe fallar por disparador) ---'
UPDATE historial_precio_repuesto SET precio_nuevo = 50000.00 WHERE id = 1;
-- ERROR:  La tabla historial_precio_repuesto es de sólo agregado: UPDATE no permitido
-- CONTEXT:  función PL/pgSQL rechazar_cambio_solo_agregado() línea 3 en RAISE

\echo '--- 6. DELETE sobre historial_precio_repuesto (Debe fallar por disparador) ---'
DELETE FROM historial_precio_repuesto WHERE id = 1;
-- ERROR:  La tabla historial_precio_repuesto es de sólo agregado: DELETE no permitido
-- CONTEXT:  función PL/pgSQL rechazar_cambio_solo_agregado() línea 3 en RAISE

\echo '--- 7. INSERT en orden_trabajo con estado no existente (Debe fallar por FK, no por disparador) ---'
INSERT INTO orden_trabajo (vehiculo_id, estado, falla, total)
VALUES (1, 'ESTADO_INVENTADO', 'Prueba integridad FK', 1000.00);
-- ERROR:  inserción o actualización en la tabla «orden_trabajo» viola la llave foránea «fk_orden_trabajo_estado_orden»
-- DETAIL:  La llave (estado)=(ESTADO_INVENTADO) no está presente en la tabla «estado_orden».

