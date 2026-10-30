# Spec Delta

## Purpose

Define el esquema relacional de seguridad y personal (usuarios, roles con vigencia, intentos de acceso y eventos de seguridad) para que la base garantice la unicidad del correo y a lo sumo una asignación abierta por rol.

## ADDED Requirements

### Requirement: Tabla `usuario`

La base SHALL tener la tabla `usuario` con las columnas `id` (PK entera autoincremental), `email`, `nombre`, `password_hash`, `activo`, `debe_cambiar_password` (todas no nulas) y `password_cambiada_en` (`timestamptz`, nula). `activo` MUST valer `true` por defecto y `debe_cambiar_password` `false`. La tabla MUST NOT tener una columna `rol`.

#### Scenario: Columnas literales y sin rol

- **WHEN** se inspecciona `usuario` en psql (`\d usuario`)
- **THEN** aparecen exactamente las columnas `id`, `email`, `nombre`, `password_hash`, `activo`, `debe_cambiar_password`, `password_cambiada_en`, y no hay columna `rol`

#### Scenario: Fecha de cambio con zona horaria

- **WHEN** se inspecciona el tipo de `usuario.password_cambiada_en`
- **THEN** es `timestamp with time zone` y admite nulos

### Requirement: Correo de usuario único

`usuario.email` MUST ser único mediante una restricción `UNIQUE` de la base, de modo que un segundo alta con el mismo correo falle con una violación de unicidad, sin depender de una consulta previa.

#### Scenario: Correo repetido rechazado por la base

- **WHEN** se insertan dos filas de `usuario` con el mismo `email`
- **THEN** la segunda inserción falla con violación de unicidad (`23505`)

### Requirement: Tabla `asignacion_rol` con rol restringido

La base SHALL tener la tabla `asignacion_rol` con `id`, `usuario_id` (FK a `usuario.id`, no nula), `rol` (texto, no nulo), `desde` (`timestamptz`, no nula, por defecto el instante actual), `vence_en`, `revocada_en` (`timestamptz`, nulas) y `otorgada_por` (FK a `usuario.id`, nula). `rol` MUST estar restringido por `CHECK` a `ADMIN`, `RECEPCION`, `MECANICO`, `CLIENTE`.

#### Scenario: Rol fuera de la lista

- **WHEN** se inserta una `asignacion_rol` con `rol = 'SUPERVISOR'`
- **THEN** la inserción falla por violación del `CHECK` (`23514`)

#### Scenario: Rol válido

- **WHEN** se inserta una `asignacion_rol` con `rol = 'MECANICO'` para un usuario existente
- **THEN** la inserción se acepta y `desde` queda con el instante actual

### Requirement: Una asignación abierta por rol

La base MUST tener un índice único **parcial** sobre `asignacion_rol (usuario_id, rol) WHERE revocada_en IS NULL`, de modo que un usuario tenga a lo sumo una asignación abierta por rol, pero conserve todas las revocadas.

#### Scenario: Segunda asignación abierta del mismo rol

- **WHEN** un usuario ya tiene una asignación `ADMIN` con `revocada_en` nula y se inserta otra `ADMIN` abierta
- **THEN** la inserción falla con violación de unicidad

#### Scenario: Reasignación tras revocar

- **WHEN** la asignación `ADMIN` anterior tiene `revocada_en` no nula y se inserta una nueva `ADMIN` abierta
- **THEN** la inserción se acepta y ambas filas quedan en la tabla

#### Scenario: Índice parcial visible

- **WHEN** se inspecciona `\d asignacion_rol` en psql
- **THEN** aparece un índice único sobre `(usuario_id, rol)` con `WHERE revocada_en IS NULL`

### Requirement: Tabla `intento_acceso` con índice de conteo

La base SHALL tener la tabla `intento_acceso` con `id`, `cuando` (`timestamptz`, por defecto el instante actual), `email`, `ip` y `exito` (todas no nulas), sin claves foráneas, y un índice compuesto `(email, ip, cuando)` que sostenga el conteo de fallos recientes.

#### Scenario: Índice compuesto presente

- **WHEN** se inspecciona `\d intento_acceso`
- **THEN** aparece un índice sobre `(email, ip, cuando)` en ese orden y la tabla no tiene claves foráneas

#### Scenario: Intento con correo inexistente

- **WHEN** se inserta un `intento_acceso` con un `email` que no corresponde a ningún usuario
- **THEN** la inserción se acepta (no hay relación con `usuario`)

### Requirement: Tabla `evento_seguridad`

La base SHALL tener la tabla `evento_seguridad` con `id`, `cuando` (`timestamptz`, por defecto el instante actual), `actor` (texto) y `accion` (texto), todas no nulas, sin claves foráneas ni restricciones adicionales, de modo que `actor` acepte el valor `SISTEMA`.

#### Scenario: Actor del sistema

- **WHEN** se inserta un `evento_seguridad` con `actor = 'SISTEMA'`
- **THEN** la inserción se acepta

### Requirement: Navegación de usuario

El modelo de `usuario` SHALL declarar navegación en los dos extremos hacia sus asignaciones de rol y hacia su ficha de cliente. `Usuario.cliente` MUST devolver un único objeto o `None`, nunca una lista. Ninguna relación MUST cargarse en forma perezosa: leer una relación no precargada MUST fallar en forma explícita.

#### Scenario: Cliente como objeto único

- **WHEN** se inspecciona la relación `Usuario.cliente` en el mapeo
- **THEN** es escalar (no una colección) y su inversa es `Cliente.usuario`

#### Scenario: Asignaciones navegables desde ambos extremos

- **WHEN** se inspecciona el mapeo de `Usuario` y `AsignacionRol`
- **THEN** `Usuario` expone sus asignaciones como colección y `AsignacionRol` expone su usuario, vinculados por `usuario_id` y no por `otorgada_por`

#### Scenario: Relación no precargada

- **WHEN** se accede a una relación de un objeto leído sin precarga
- **THEN** se produce un error explícito en lugar de una consulta implícita

### Requirement: Índice en cada clave foránea de seguridad

Cada clave foránea de `asignacion_rol` (`usuario_id`, `otorgada_por`) MUST tener un índice propio.

#### Scenario: Índices de FK presentes

- **WHEN** se consultan los índices de `asignacion_rol`
- **THEN** existe un índice cuya primera columna es `usuario_id` y otro sobre `otorgada_por`
