# modelo-ordenes Specification

## Purpose
Define el esquema relacional de las órdenes de trabajo: el catálogo `estado_orden` como fuente de los estados válidos por clave foránea, la orden con sus ítems como composición y el historial de estados.

## Requirements

### Requirement: Catálogo `estado_orden`

La base SHALL tener la tabla `estado_orden` con `codigo` (texto, **clave primaria**), `descripcion` (texto), `posicion` (entero) y `es_final` (booleano), todas no nulas, sin columna `id`. `posicion` MUST ser única.

#### Scenario: PK textual

- **WHEN** se inspecciona `\d estado_orden`
- **THEN** la clave primaria es `codigo` y no existe columna `id`

#### Scenario: Posición repetida

- **WHEN** se insertan dos estados con la misma `posicion`
- **THEN** la segunda inserción falla con violación de unicidad

### Requirement: Estados de orden por clave foránea al catálogo

`orden_trabajo.estado`, `historial_estado_orden.desde_estado` y `historial_estado_orden.hasta_estado` MUST ser claves foráneas a `estado_orden.codigo`. La lista de estados MUST NOT estar escrita en un `CHECK`.

#### Scenario: Estado inexistente rechazado por la FK

- **WHEN** se inserta una `orden_trabajo` con `estado = 'INEXISTENTE'`
- **THEN** la inserción falla por violación de clave foránea (`23503`), no de `CHECK`

#### Scenario: Catálogo vacío impide crear órdenes

- **WHEN** `estado_orden` no tiene filas y se inserta una orden con `estado = 'PENDIENTE'`
- **THEN** la inserción falla por violación de clave foránea

#### Scenario: Sin CHECK con la lista

- **WHEN** se inspeccionan las restricciones de `orden_trabajo` e `historial_estado_orden`
- **THEN** no hay ningún `CHECK` que mencione `PENDIENTE`, `EN_REPARACION`, `TERMINADA` o `CANCELADA`

### Requirement: Tabla `orden_trabajo`

La base SHALL tener la tabla `orden_trabajo` con `id`, `vehiculo_id` (FK a `vehiculo.id`, no nula), `mecanico_id` (FK a `usuario.id`, nula), `estado` (texto, no nulo), `falla` (texto, no nulo), `creada_en` (`timestamptz`, no nula, por defecto el instante actual) y `total` (`NUMERIC(12,2)`, no nulo, `CHECK total >= 0`). `vehiculo_id`, `mecanico_id` y `estado` MUST tener índice propio.

#### Scenario: Total negativo

- **WHEN** se inserta una orden con `total = -0.01`
- **THEN** la inserción falla por violación del `CHECK`

#### Scenario: Orden sin mecánico

- **WHEN** se inserta una orden válida con `mecanico_id` nulo y un estado existente en el catálogo
- **THEN** la inserción se acepta y `creada_en` queda con el instante actual

### Requirement: Tabla `item_orden` sin repuestos repetidos

La base SHALL tener la tabla `item_orden` con `id`, `orden_id` (FK a `orden_trabajo.id`, no nula), `repuesto_id` (FK a `repuesto.id`, no nula), `cantidad` (entero, `CHECK cantidad > 0`) y `precio_unitario` (`NUMERIC(10,2)`, `CHECK precio_unitario > 0`), no nulos. MUST existir `UNIQUE (orden_id, repuesto_id)` e índice en cada FK.

#### Scenario: Repuesto repetido en la misma orden

- **WHEN** se insertan dos ítems con el mismo `orden_id` y `repuesto_id`
- **THEN** la segunda inserción falla con violación de unicidad

#### Scenario: Cantidad o precio no positivos

- **WHEN** se inserta un ítem con `cantidad = 0` o `precio_unitario = 0`
- **THEN** la inserción falla por violación del `CHECK`

### Requirement: Tabla `historial_estado_orden`

La base SHALL tener la tabla `historial_estado_orden` con `id`, `orden_id` (FK, no nula), `desde_estado` (FK, nula), `hasta_estado` (FK, no nula), `usuario_id` (FK a `usuario.id`, no nula) y `cuando` (`timestamptz`, por defecto el instante actual). Cada una de sus cuatro FK MUST tener índice propio.

#### Scenario: Primera línea sin estado de origen

- **WHEN** se inserta una línea con `desde_estado` nulo y `hasta_estado = 'PENDIENTE'` existente en el catálogo
- **THEN** la inserción se acepta

#### Scenario: Línea sin usuario

- **WHEN** se inserta una línea con `usuario_id` nulo
- **THEN** la inserción falla por violación de `NOT NULL`

### Requirement: Composición orden–ítems y navegación

El modelo SHALL declarar `OrdenTrabajo.items` (colección) ↔ `ItemOrden.orden` como composición: un ítem agregado a la colección de una orden nueva se persiste con ella y un ítem quitado de la colección se elimina. También SHALL declarar en los dos extremos: orden ↔ vehículo, orden ↔ mecánico, orden ↔ estado del catálogo, orden ↔ historial, ítem ↔ repuesto. Ninguna relación MUST cargarse en forma perezosa.

#### Scenario: Ítems persistidos con la orden

- **WHEN** se crea una orden en memoria, se le agregan dos ítems a `items` y se confirma la transacción
- **THEN** la orden y sus dos ítems quedan insertados con el `orden_id` de la orden

#### Scenario: Dos FK al catálogo sin ambigüedad

- **WHEN** se configuran los mapeos de `HistorialEstadoOrden`
- **THEN** las relaciones hacia el estado de origen y el de destino se resuelven cada una por su columna, sin error de ambigüedad
