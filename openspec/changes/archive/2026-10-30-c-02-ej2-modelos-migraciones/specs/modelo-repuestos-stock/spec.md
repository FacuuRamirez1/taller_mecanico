# Spec Delta

## Purpose

Define el esquema relacional del catálogo de repuestos y de sus dos historiales de sólo agregado (movimientos de stock y cambios de precio), con dinero exacto y las restricciones de precio, stock y aumento de precio garantizadas por la base.

## ADDED Requirements

### Requirement: Tabla `repuesto` con precio y stock válidos

La base SHALL tener la tabla `repuesto` con `id`, `codigo`, `descripcion` (texto, no nulos), `precio` (`NUMERIC(10,2)`, no nulo), `stock` (entero, no nulo) y `borrado_en` (`timestamptz`, nula). MUST existir `CHECK precio > 0` y `CHECK stock >= 0`. En la aplicación `precio` MUST representarse como `Decimal`, nunca `float`.

#### Scenario: Precio no positivo

- **WHEN** se inserta un repuesto con `precio = 0`
- **THEN** la inserción falla por violación del `CHECK` (`23514`)

#### Scenario: Stock negativo

- **WHEN** se actualiza un repuesto a `stock = -1`
- **THEN** la sentencia falla por violación del `CHECK`

#### Scenario: Stock en cero

- **WHEN** se inserta un repuesto con `stock = 0` y `precio = 8500.00`
- **THEN** la inserción se acepta y `precio` se lee como `Decimal('8500.00')`

#### Scenario: Tipo exacto

- **WHEN** se inspecciona `\d repuesto`
- **THEN** `precio` es `numeric(10,2)`

### Requirement: Código único entre repuestos vigentes

La base MUST tener un índice único **parcial** sobre `repuesto (codigo) WHERE borrado_en IS NULL`. El código MUST NOT tener un `UNIQUE` común.

#### Scenario: Dos vigentes con el mismo código

- **WHEN** existe un repuesto vigente `FIL-001` y se inserta otro vigente `FIL-001`
- **THEN** la inserción falla con violación de unicidad

#### Scenario: Reuso de código tras la baja

- **WHEN** el repuesto `FIL-001` tiene `borrado_en` no nulo y se inserta otro vigente `FIL-001`
- **THEN** la inserción se acepta

#### Scenario: Índice parcial visible

- **WHEN** se inspecciona `\d repuesto`
- **THEN** aparece un índice único sobre `(codigo)` con `WHERE borrado_en IS NULL`

### Requirement: Tabla `movimiento_stock`

La base SHALL tener la tabla `movimiento_stock` con `id`, `repuesto_id` (FK a `repuesto.id`, no nula), `orden_id` (FK a `orden_trabajo.id`, nula), `usuario_id` (FK a `usuario.id`, no nula), `cantidad` (entero, no nulo, `CHECK cantidad > 0`), `motivo` (texto, no nulo) y `cuando` (`timestamptz`, por defecto el instante actual). Cada FK MUST tener índice propio.

#### Scenario: Cantidad no positiva

- **WHEN** se inserta un movimiento con `cantidad = 0`
- **THEN** la inserción falla por violación del `CHECK`

#### Scenario: Movimiento sin orden

- **WHEN** se inserta un movimiento con `motivo = 'Stock inicial'` y `orden_id` nulo
- **THEN** la inserción se acepta

### Requirement: Tabla `historial_precio_repuesto` sólo con aumentos

La base SHALL tener la tabla `historial_precio_repuesto` con `id`, `repuesto_id` y `usuario_id` (FKs no nulas e indexadas), `precio_anterior` y `precio_nuevo` (`NUMERIC(10,2)`, no nulos) y `cuando` (`timestamptz`, por defecto el instante actual). MUST existir `CHECK precio_nuevo > 0` y `CHECK precio_nuevo > precio_anterior`.

#### Scenario: Aumento registrado

- **WHEN** se inserta una línea con `precio_anterior = 8000.00` y `precio_nuevo = 8500.00`
- **THEN** la inserción se acepta

#### Scenario: Baja de precio rechazada por la base

- **WHEN** se inserta una línea con `precio_anterior = 8500.00` y `precio_nuevo = 8000.00`
- **THEN** la inserción falla por violación del `CHECK` con un nombre de restricción estable que la aplicación pueda reconocer

#### Scenario: Precio igual rechazado

- **WHEN** se inserta una línea con `precio_anterior = precio_nuevo`
- **THEN** la inserción falla por violación del `CHECK`

### Requirement: Navegación de repuestos

El modelo SHALL declarar navegación en los dos extremos: `Repuesto.movimientos` ↔ `MovimientoStock.repuesto`, `Repuesto.historial_precios` ↔ `HistorialPrecioRepuesto.repuesto`, y de cada historial hacia el `Usuario` que lo produjo. Ninguna relación MUST cargarse en forma perezosa.

#### Scenario: Historiales desde el repuesto

- **WHEN** se inspecciona el mapeo de `Repuesto`
- **THEN** expone sus movimientos y su historial de precios como colecciones con inversa declarada
