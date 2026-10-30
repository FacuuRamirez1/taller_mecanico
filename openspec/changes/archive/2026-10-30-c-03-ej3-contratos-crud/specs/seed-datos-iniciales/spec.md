# Spec Delta

## Purpose

Define la carga idempotente del estado inicial conocido de la base, del que dependen todos los casos de prueba, con el catálogo de estados como primera pieza y los historiales cargados como movimientos válidos.

## ADDED Requirements

### Requirement: Vaciado idempotente previo a la carga

`seed.py` MUST vaciar las tablas con `TRUNCATE ... RESTART IDENTITY CASCADE` antes de insertar, MUST NOT usar `DELETE` sobre las tablas de sólo agregado y MUST dejar el mismo estado al correrse dos veces seguidas.

#### Scenario: Dos corridas consecutivas

- **WHEN** se ejecuta `python seed.py` dos veces seguidas
- **THEN** la segunda corrida termina sin error y el conteo de filas de todas las tablas es idéntico al de la primera

#### Scenario: Sin DELETE sobre sólo agregado

- **WHEN** se revisa el vaciado del seed
- **THEN** usa `TRUNCATE` y no intenta `DELETE` sobre `movimiento_stock`, `historial_precio_repuesto` ni `historial_estado_orden`

### Requirement: Catálogo de estados primero

El seed MUST cargar primero los cuatro estados `PENDIENTE` (posición 1), `EN_REPARACION` (2), `TERMINADA` (3, final) y `CANCELADA` (4, final), cada uno con su descripción, antes de crear cualquier orden.

#### Scenario: Catálogo completo

- **WHEN** termina el seed
- **THEN** `estado_orden` tiene exactamente 4 filas con las posiciones y marcas de final indicadas

#### Scenario: Orden con estado válido

- **WHEN** el seed crea una orden
- **THEN** su estado existe en el catálogo ya cargado y la clave foránea se satisface

### Requirement: Usuarios y roles iniciales

El seed MUST cargar 7 usuarios: dos `ADMIN`, un `RECEPCION`, dos `MECANICO`, un `CLIENTE` y un `MECANICO` con cambio de contraseña obligatorio. Cada usuario MUST tener su asignación de rol abierta correspondiente.

#### Scenario: Conteo de usuarios

- **WHEN** termina el seed
- **THEN** `usuario` tiene 7 filas y cada una tiene al menos una asignación de rol vigente

#### Scenario: Usuario con cambio obligatorio

- **WHEN** se consulta el usuario con cambio obligatorio
- **THEN** `debe_cambiar_password` es verdadero

### Requirement: Clientes y vehículos iniciales

El seed MUST cargar dos clientes: Laura, vinculada al usuario cliente y con 2 vehículos, y Jorge, sin usuario y con 1 vehículo.

#### Scenario: Conteo de clientes y vehículos

- **WHEN** termina el seed
- **THEN** `cliente` tiene 2 filas, `vehiculo` tiene 3 filas vigentes, Laura tiene 2 vehículos y Jorge 1

#### Scenario: Laura vinculada a su usuario

- **WHEN** se consulta el cliente de Laura
- **THEN** su `usuario_id` corresponde al usuario `cliente@example.com`

### Requirement: Repuestos y stock inicial como movimientos

El seed MUST cargar 4 repuestos con stock 10, 4, 2 y 20, y cada stock MUST quedar respaldado por un movimiento `"Stock inicial"` con `orden_id` nulo.

#### Scenario: Conteo de repuestos

- **WHEN** termina el seed
- **THEN** `repuesto` tiene 4 filas vigentes con stocks 10, 4, 2 y 20

#### Scenario: Un movimiento por repuesto

- **WHEN** se consultan los movimientos de stock inicial
- **THEN** hay exactamente 4 movimientos `"Stock inicial"`, uno por repuesto, con la cantidad del stock cargado

### Requirement: Órdenes e historial de estados iniciales

El seed MUST cargar la orden 1 en estado `PENDIENTE` para el primer vehículo de Laura y la orden 2 en estado `EN_REPARACION` para el vehículo de Jorge, asignada al mecánico, con 4 bujías aunque el stock sea 2. Cada orden MUST tener su historial de estados coherente.

#### Scenario: Órdenes iniciales

- **WHEN** termina el seed
- **THEN** hay 2 órdenes: la 1 en `PENDIENTE` y la 2 en `EN_REPARACION` asignada al mecánico

#### Scenario: Orden 2 con cuatro bujías

- **WHEN** se consultan los ítems de la orden 2
- **THEN** hay un ítem de 4 bujías y el stock del repuesto sigue siendo 2

#### Scenario: Historial coherente

- **WHEN** se consulta el historial de estados de las órdenes
- **THEN** la orden 1 tiene la transición inicial a `PENDIENTE` y la orden 2 tiene la inicial y la transición de `PENDIENTE` a `EN_REPARACION`

### Requirement: Historial de precio y evento de sistema

El seed MUST cargar una línea de historial del filtro de aceite de 8000 a 8500 y una línea de `evento_seguridad` con `actor = 'SISTEMA'` y la acción de carga inicial.

#### Scenario: Historial de precio

- **WHEN** termina el seed
- **THEN** existe una línea con precio anterior 8000 y precio nuevo 8500 para el filtro de aceite, y su precio actual es 8500

#### Scenario: Evento de sistema

- **WHEN** termina el seed
- **THEN** existe un evento con `actor = 'SISTEMA'` y la acción `"Carga de los datos iniciales"`

### Requirement: Sin secretos documentados ni esquema alternativo

Las contraseñas del seed MUST ser ficticias y MUST vivir sólo en `seed.py`. El seed MUST NOT usar `create_all` ni crear tablas: asume `alembic upgrade head` ya ejecutado.

#### Scenario: Sin `create_all`

- **WHEN** se busca `create_all` en `seed.py`
- **THEN** no hay coincidencias

#### Scenario: Base sin migrar

- **WHEN** se ejecuta `python seed.py` sobre una base sin tablas
- **THEN** el comando falla con un error comprensible y no crea el esquema por su cuenta
