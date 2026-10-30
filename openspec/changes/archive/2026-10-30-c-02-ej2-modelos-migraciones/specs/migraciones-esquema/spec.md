# Spec Delta

## Purpose

Define cómo nace, evoluciona y se revierte el esquema de la base: exclusivamente con migraciones de Alembic (una autogenerada y una escrita a mano), reversibles sobre una base vacía y sin cargar datos.

## ADDED Requirements

### Requirement: Esquema creado sólo por migraciones

El esquema MUST crearse exclusivamente con `alembic upgrade head`. Ningún archivo del repositorio MUST usar `create_all`, y la aplicación MUST NOT crear tablas al arrancar.

#### Scenario: Sin `create_all`

- **WHEN** se busca `create_all` en `app/`, `main.py`, `seed.py` y `migrations/`
- **THEN** no hay coincidencias

#### Scenario: Arrancar no crea tablas

- **WHEN** la base está vacía y se levanta la aplicación sin correr migraciones
- **THEN** la base sigue sin tablas

### Requirement: Dos migraciones encadenadas

El repositorio SHALL tener exactamente dos revisiones lineales: `0001` (esquema inicial, generada con `alembic revision --autogenerate` y revisada) y `0002` (sólo agregado, escrita a mano, con `0001` como revisión anterior). Cada archivo MUST llevar un comentario que declare que se leyó antes de aplicarse.

#### Scenario: Historia lineal

- **WHEN** se ejecuta `alembic history`
- **THEN** muestra `<base> -> 0001` y `0001 -> 0002 (head)` y nada más

#### Scenario: Comentario de lectura

- **WHEN** se abren `migrations/versions/0001_esquema_inicial.py` y `migrations/versions/0002_solo_agregado.py`
- **THEN** cada uno contiene un comentario que declara que la migración se leyó antes de aplicarla

### Requirement: Metadata completa para autogenerate

La configuración de Alembic SHALL registrar los modelos de los cuatro módulos (`usuarios`, `clientes`, `repuestos`, `ordenes`) en la metadata que compara `autogenerate`, de modo que, aplicado `head`, la comparación no detecte diferencias entre modelos y base.

#### Scenario: Sin diferencias tras aplicar

- **WHEN** la base está en `head` y se ejecuta `alembic check`
- **THEN** informa que no hay operaciones pendientes

### Requirement: Nombres de restricciones estables

Toda restricción e índice creado por las migraciones (`PK`, `FK`, `UNIQUE`, `CHECK`, índices) MUST tener un nombre determinista derivado de la tabla y las columnas o del nombre lógico de la restricción, igual en todas las máquinas, para que la aplicación pueda reconocer qué restricción falló sin mostrar el texto de la base.

#### Scenario: CHECK con nombre reconocible

- **WHEN** se viola el `CHECK precio_nuevo > precio_anterior`
- **THEN** el error de la base nombra una restricción con prefijo `ck_historial_precio_repuesto_`

#### Scenario: Mismos nombres en otra máquina

- **WHEN** dos integrantes aplican `head` en bases vacías distintas y listan las restricciones
- **THEN** obtienen los mismos nombres

### Requirement: Reversibilidad sobre base vacía

Sobre una base sin tablas, la secuencia `alembic upgrade head`, `alembic downgrade base`, `alembic upgrade head` MUST completarse sin error. `downgrade base` MUST dejar la base sin las 13 tablas, sin la función ni los disparadores de sólo agregado y sin tipos ni secuencias huérfanas.

#### Scenario: Ida desde vacío

- **WHEN** la base no tiene tablas y se ejecuta `alembic upgrade head`
- **THEN** termina con código 0 y la base tiene las 13 tablas del dominio más `alembic_version`

#### Scenario: Vuelta a base

- **WHEN** se ejecuta `alembic downgrade base`
- **THEN** termina con código 0 y en la base sólo queda, a lo sumo, `alembic_version` vacía; no queda la función de sólo agregado

#### Scenario: Segunda ida

- **WHEN** después de `downgrade base` se ejecuta otra vez `alembic upgrade head`
- **THEN** termina con código 0 y el esquema es idéntico al de la primera ida

### Requirement: Esquema completo tras `upgrade head`

Aplicado `head`, la base MUST tener exactamente las 13 tablas del dominio (`usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad`, `cliente`, `vehiculo`, `repuesto`, `estado_orden`, `orden_trabajo`, `item_orden`, `historial_estado_orden`, `movimiento_stock`, `historial_precio_repuesto`), los 3 índices únicos parciales y un índice en cada clave foránea.

#### Scenario: Trece tablas

- **WHEN** se ejecuta `\dt` en psql sobre la base en `head`
- **THEN** se listan las 13 tablas del dominio y `alembic_version`, ninguna otra

#### Scenario: Tres índices parciales

- **WHEN** se consultan los índices cuya definición contiene `WHERE`
- **THEN** hay exactamente tres: `asignacion_rol (usuario_id, rol) WHERE revocada_en IS NULL`, `vehiculo (patente) WHERE borrado_en IS NULL`, `repuesto (codigo) WHERE borrado_en IS NULL`, los tres únicos

#### Scenario: Ninguna FK sin índice

- **WHEN** se cruzan las claves foráneas con los índices cuya primera columna es la columna de la FK
- **THEN** no queda ninguna FK sin índice

### Requirement: Migraciones sin datos

Las migraciones MUST NOT insertar filas. En particular `estado_orden` MUST quedar vacía tras `upgrade head`; sus filas las carga `seed.py`.

#### Scenario: Catálogo vacío

- **WHEN** se ejecuta `SELECT count(*) FROM estado_orden` sobre la base recién migrada
- **THEN** el resultado es 0
