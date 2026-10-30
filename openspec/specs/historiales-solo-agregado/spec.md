# historiales-solo-agregado Specification

## Purpose
Garantiza en la propia base (no en la aplicación) que los tres historiales del sistema sean de sólo agregado: sus filas se insertan y se leen, pero nunca se modifican ni se borran, venga de donde venga la sentencia.

## Requirements

### Requirement: Rechazo de modificaciones en tablas de sólo agregado

La base MUST rechazar toda sentencia `UPDATE` y `DELETE` que afecte filas de `historial_estado_orden`, `movimiento_stock` o `historial_precio_repuesto`, sea cual sea el cliente (API, `psql` o script). El rechazo MUST abortar la sentencia sin modificar ninguna fila.

#### Scenario: UPDATE rechazado

- **WHEN** existe una fila en `movimiento_stock` y se ejecuta en psql `UPDATE movimiento_stock SET cantidad = 99`
- **THEN** la sentencia falla con un error levantado por el disparador y la fila conserva su valor original

#### Scenario: DELETE rechazado

- **WHEN** existe una fila en `historial_precio_repuesto` y se ejecuta `DELETE FROM historial_precio_repuesto`
- **THEN** la sentencia falla con un error levantado por el disparador y la fila sigue en la tabla

#### Scenario: Las tres tablas protegidas

- **WHEN** se intenta un `UPDATE` y un `DELETE` sobre una fila de cada una de las tres tablas
- **THEN** los seis intentos son rechazados

#### Scenario: Inserción permitida

- **WHEN** se inserta una fila válida en `historial_estado_orden`
- **THEN** la inserción se acepta

### Requirement: Mensaje de rechazo propio

El error del disparador MUST indicar en español que la tabla es de sólo agregado y MUST nombrar la tabla afectada, sin exponer datos de la fila.

#### Scenario: Mensaje identifica la tabla

- **WHEN** se rechaza un `DELETE` sobre `historial_estado_orden`
- **THEN** el mensaje de error menciona `historial_estado_orden` y "sólo agregado" (o "solo agregado")

### Requirement: Tablas no protegidas siguen editables

El disparador MUST aplicarse sólo a las tres tablas de sólo agregado; el resto de las tablas (por ejemplo `repuesto`, `orden_trabajo`, `asignacion_rol`) MUST seguir admitiendo `UPDATE`.

#### Scenario: Repuesto editable

- **WHEN** se actualiza el `precio` de un repuesto existente con un valor válido
- **THEN** la sentencia se acepta

### Requirement: Instalación y retiro por migración

La función y los disparadores MUST instalarse en la migración escrita a mano `0002` y MUST eliminarse en su `downgrade`, de modo que tras `downgrade` a `0001` no quede ni la función ni ningún disparador de sólo agregado.

#### Scenario: Disparadores presentes en `head`

- **WHEN** se consultan los disparadores de usuario de la base en `head`
- **THEN** hay exactamente uno por cada una de las tres tablas de sólo agregado y la función existe

#### Scenario: Retiro en downgrade

- **WHEN** se ejecuta `alembic downgrade 0001`
- **THEN** no queda ningún disparador de sólo agregado ni su función, y las 13 tablas siguen presentes
