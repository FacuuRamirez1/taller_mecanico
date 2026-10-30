# Spec Delta

## Purpose

Define el alta y la consulta de clientes y vehículos, la baja lógica de vehículos y la consulta de los vehículos del cliente autenticado, respetando la unicidad del documento y de la patente sólo entre vehículos vigentes.

## ADDED Requirements

### Requirement: Alta de cliente sin usuario

`POST /clientes` MUST aceptar `nombre`, `documento` y `telefono`, MUST NOT aceptar `usuario_id`, MUST responder **201** con el cliente creado, **409** si el documento ya existe y **422** si el contrato es inválido.

#### Scenario: Alta exitosa

- **WHEN** se envía `POST /clientes` con nombre, documento y teléfono válidos
- **THEN** la respuesta es **201** con el cliente creado y `usuario_id` nulo

#### Scenario: Documento repetido

- **WHEN** se envía `POST /clientes` con un documento ya registrado
- **THEN** la respuesta es **409** con un mensaje propio y no se crea otra ficha

#### Scenario: `usuario_id` enviado en el alta

- **WHEN** se envía `POST /clientes` con un campo `usuario_id`
- **THEN** la respuesta es **422** y no se crea el cliente

#### Scenario: Campos faltantes

- **WHEN** se envía `POST /clientes` sin `documento`
- **THEN** la respuesta es **422**

### Requirement: Detalle de cliente con sus vehículos

`GET /clientes/{id}` MUST responder **200** con el cliente y sus vehículos **vigentes**, y **404** si el cliente no existe. Los vehículos dados de baja MUST NOT aparecer en el detalle.

#### Scenario: Cliente con vehículos

- **WHEN** se pide `GET /clientes/{id}` de un cliente con dos vehículos vigentes
- **THEN** la respuesta es **200** e incluye los dos vehículos

#### Scenario: Vehículo dado de baja excluido

- **WHEN** uno de los vehículos del cliente tiene `borrado_en` no nulo
- **THEN** el detalle del cliente no lo incluye

#### Scenario: Cliente inexistente

- **WHEN** se pide `GET /clientes/{id}` con un id inexistente
- **THEN** la respuesta es **404**

### Requirement: Alta de vehículo de un cliente

`POST /clientes/{id}/vehiculos` MUST aceptar `patente`, `marca`, `modelo` y `anio`, MUST responder **201** con el vehículo creado, **404** si el cliente no existe, **409** si la patente ya pertenece a un vehículo vigente y **422** si el contrato es inválido.

#### Scenario: Alta exitosa

- **WHEN** se envía `POST /clientes/{id}/vehiculos` con datos válidos y una patente libre
- **THEN** la respuesta es **201** con el vehículo asociado al cliente

#### Scenario: Cliente inexistente

- **WHEN** se envía `POST /clientes/{id}/vehiculos` con un id de cliente inexistente
- **THEN** la respuesta es **404** y no se crea el vehículo

#### Scenario: Patente vigente repetida

- **WHEN** se envía `POST /clientes/{id}/vehiculos` con una patente ya usada por un vehículo vigente
- **THEN** la respuesta es **409** con un mensaje propio sobre la patente

#### Scenario: Año fuera de rango

- **WHEN** se envía `POST /clientes/{id}/vehiculos` con `anio = 1949` o `anio = 2101`
- **THEN** la respuesta es **422**

### Requirement: Baja lógica de vehículo

`DELETE /vehiculos/{id}` MUST escribir `borrado_en` y responder **204** sin borrar la fila. MUST responder **404** si el vehículo no existe o ya está dado de baja, y **409** si tiene alguna orden abierta (algún estado con `es_final = false`).

#### Scenario: Baja exitosa

- **WHEN** se pide `DELETE /vehiculos/{id}` de un vehículo sin órdenes abiertas
- **THEN** la respuesta es **204** y el vehículo deja de aparecer entre los vigentes

#### Scenario: Vehículo con orden abierta

- **WHEN** se pide `DELETE /vehiculos/{id}` de un vehículo con una orden en un estado no final
- **THEN** la respuesta es **409** y el vehículo sigue vigente

#### Scenario: Vehículo inexistente o ya dado de baja

- **WHEN** se pide `DELETE /vehiculos/{id}` con un id inexistente o de un vehículo ya dado de baja
- **THEN** la respuesta es **404**

#### Scenario: Misma patente tras la baja (C-19)

- **WHEN** se da de baja un vehículo con patente `AC456EF` y luego se registra otro vehículo vigente con esa misma patente para otro cliente
- **THEN** la segunda alta es **201** y ambas filas quedan en la base

#### Scenario: Segunda patente vigente igual

- **WHEN** ya existe un vehículo vigente con `AC456EF` y se intenta registrar otro vigente con la misma patente
- **THEN** la respuesta es **409**

### Requirement: Vehículos del cliente autenticado

`GET /mis-vehiculos` MUST responder **200** con los vehículos del cliente autenticado. En C-03 la protección y la resolución de la identidad llegan en C-05; hasta entonces la ruta responde **200** con una lista vacía y queda marcada para su protección.

#### Scenario: Respuesta disponible

- **WHEN** se pide `GET /mis-vehiculos`
- **THEN** la respuesta es **200** con una lista de vehículos

#### Scenario: Protección diferida

- **WHEN** se revisa la ruta en C-03
- **THEN** existe la marca de deuda para que C-05 exija sesión y filtre por el cliente autenticado
