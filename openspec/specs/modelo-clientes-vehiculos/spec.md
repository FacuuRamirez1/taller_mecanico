# modelo-clientes-vehiculos Specification

## Purpose
Define el esquema relacional de clientes y vehículos: la ficha de cliente con usuario opcional (1:1), la unicidad del documento y la patente única sólo entre vehículos vigentes, con baja lógica.

## Requirements

### Requirement: Tabla `cliente`

La base SHALL tener la tabla `cliente` con `id` (PK entera autoincremental), `usuario_id` (FK a `usuario.id`, nula), `nombre`, `documento` y `telefono` (texto, no nulos).

#### Scenario: Cliente sin usuario

- **WHEN** se inserta un `cliente` con `usuario_id` nulo
- **THEN** la inserción se acepta

#### Scenario: Columnas literales

- **WHEN** se inspecciona `\d cliente`
- **THEN** aparecen exactamente `id`, `usuario_id`, `nombre`, `documento`, `telefono`

### Requirement: Documento de cliente único

`cliente.documento` MUST ser único mediante una restricción `UNIQUE` de la base.

#### Scenario: Documento repetido

- **WHEN** se insertan dos clientes con el mismo `documento`
- **THEN** la segunda inserción falla con violación de unicidad (`23505`)

### Requirement: A lo sumo un cliente por usuario

`cliente.usuario_id` MUST ser único mediante `UNIQUE`, de modo que un usuario quede vinculado a lo sumo a una ficha, y varias fichas sin usuario (nulo) puedan coexistir. La columna MUST tener índice.

#### Scenario: Dos fichas para el mismo usuario

- **WHEN** se insertan dos clientes con el mismo `usuario_id` no nulo
- **THEN** la segunda inserción falla con violación de unicidad

#### Scenario: Varias fichas sin usuario

- **WHEN** se insertan dos clientes con `usuario_id` nulo y documentos distintos
- **THEN** ambas inserciones se aceptan

### Requirement: Tabla `vehiculo` con año plausible

La base SHALL tener la tabla `vehiculo` con `id`, `cliente_id` (FK a `cliente.id`, no nula, indexada), `patente`, `marca`, `modelo` (texto, no nulos), `anio` (entero, no nulo) y `borrado_en` (`timestamptz`, nula). `anio` MUST estar restringido por `CHECK anio BETWEEN 1950 AND 2100`.

#### Scenario: Año fuera de rango

- **WHEN** se inserta un vehículo con `anio = 1949` o `anio = 2101`
- **THEN** la inserción falla por violación del `CHECK` (`23514`)

#### Scenario: Año en el borde

- **WHEN** se inserta un vehículo con `anio = 1950`
- **THEN** la inserción se acepta

#### Scenario: Vehículo sin cliente

- **WHEN** se inserta un vehículo con un `cliente_id` inexistente
- **THEN** la inserción falla por violación de clave foránea (`23503`)

### Requirement: Patente única entre vehículos vigentes

La base MUST tener un índice único **parcial** sobre `vehiculo (patente) WHERE borrado_en IS NULL`. La patente MUST NOT tener un `UNIQUE` común.

#### Scenario: Dos vigentes con la misma patente

- **WHEN** existe un vehículo vigente con patente `AC456EF` y se inserta otro vigente con la misma patente
- **THEN** la inserción falla con violación de unicidad

#### Scenario: Reuso de patente tras la baja

- **WHEN** el vehículo con patente `AC456EF` tiene `borrado_en` no nulo y se inserta otro vigente con esa patente
- **THEN** la inserción se acepta y ambas filas quedan en la tabla

#### Scenario: Índice parcial visible

- **WHEN** se inspecciona `\d vehiculo` en psql
- **THEN** aparece un índice único sobre `(patente)` con `WHERE borrado_en IS NULL`

### Requirement: Navegación cliente–usuario y cliente–vehículos

El modelo SHALL declarar navegación en los dos extremos: `Cliente.usuario` (objeto o `None`) ↔ `Usuario.cliente`, y `Cliente.vehiculos` (colección) ↔ `Vehiculo.cliente` (objeto). Ninguna de estas relaciones MUST cargarse en forma perezosa.

#### Scenario: Vehículos de un cliente

- **WHEN** se inspecciona el mapeo de `Cliente`
- **THEN** `vehiculos` es una colección cuya inversa es `Vehiculo.cliente`, y `usuario` es escalar con inversa `Usuario.cliente`
