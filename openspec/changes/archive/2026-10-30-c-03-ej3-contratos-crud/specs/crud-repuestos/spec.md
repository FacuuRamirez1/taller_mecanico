# Spec Delta

## Purpose

Define la administración del catálogo de repuestos: consulta paginada y segura, alta con stock inicial, modificación de descripción y precio, baja lógica, reposición e historiales, con el stock cambiando únicamente por movimientos.

## ADDED Requirements

### Requirement: Listado paginado con búsqueda por descripción

`GET /repuestos?q=&page=&size=` MUST devolver **200** con el envoltorio de paginación y MUST buscar por descripción usando parámetros ligados. El listado MUST excluir los repuestos dados de baja.

#### Scenario: Búsqueda por descripción

- **WHEN** se pide `GET /repuestos?q=aceite`
- **THEN** la respuesta es **200** con los repuestos vigentes cuya descripción contiene `aceite`

#### Scenario: Intento de inyección en la búsqueda

- **WHEN** se pide `GET /repuestos?q=' OR '1'='1`
- **THEN** la respuesta es **200** con `items = []` y `total = 0`; no se devuelven filas ajenas al filtro

#### Scenario: Repuesto dado de baja excluido

- **WHEN** un repuesto tiene `borrado_en` no nulo y se pide el listado
- **THEN** ese repuesto no aparece en `items` ni suma en `total`

#### Scenario: Paginación filtrada

- **WHEN** se pide `GET /repuestos?q=filtro&page=2&size=1` con 2 coincidencias
- **THEN** `total = 2`, `page = 2`, `pages = 2` e `items` contiene la segunda coincidencia

### Requirement: Detalle de repuesto

`GET /repuestos/{id}` MUST devolver **200** con el repuesto vigente y **404** si no existe o está dado de baja.

#### Scenario: Detalle existente

- **WHEN** se pide `GET /repuestos/{id}` de un repuesto vigente
- **THEN** la respuesta es **200** con código, descripción, precio y stock

#### Scenario: Detalle inexistente

- **WHEN** se pide `GET /repuestos/{id}` con un id inexistente
- **THEN** la respuesta es **404**

### Requirement: Alta con stock inicial y movimiento

`POST /repuestos` MUST aceptar `codigo`, `descripcion`, `precio` y `stock_inicial`, MUST responder **201** y MUST crear el repuesto. Si `stock_inicial` es mayor que cero, MUST crear además un `movimiento_stock` con motivo `"Stock inicial"`, `orden_id` nulo y el usuario que corresponda. Si `stock_inicial` es cero, MUST crear el repuesto sin movimiento.

#### Scenario: Alta con stock positivo

- **WHEN** se envía `POST /repuestos` con `stock_inicial = 10`
- **THEN** la respuesta es **201** y existe un movimiento `"Stock inicial"` de 10 unidades para ese repuesto

#### Scenario: Alta con stock cero

- **WHEN** se envía `POST /repuestos` con `stock_inicial = 0`
- **THEN** la respuesta es **201**, el repuesto queda con stock 0 y no se crea ningún movimiento

#### Scenario: Código repetido

- **WHEN** se envía `POST /repuestos` con un código ya usado por un repuesto vigente
- **THEN** la respuesta es **409** y no se crea el repuesto

#### Scenario: Precio no positivo

- **WHEN** se envía `POST /repuestos` con `precio = 0`
- **THEN** la respuesta es **422** y no se crea el repuesto

#### Scenario: `stock` en lugar de `stock_inicial`

- **WHEN** se envía `POST /repuestos` con un campo `stock`
- **THEN** la respuesta es **422**

### Requirement: Modificación de descripción y precio

`PATCH /repuestos/{id}` MUST aceptar únicamente `descripcion` y `precio`, MUST aplicar sólo los campos enviados y MUST responder **200** con el repuesto actualizado. Enviar `stock` MUST producir **422**. Si el precio cambia, MUST registrar una línea en el historial de precios en la misma transacción; si no cambia, MUST NOT registrar línea. Si el precio nuevo es menor al actual, MUST responder **422** sin modificarlo.

#### Scenario: PATCH parcial de descripción

- **WHEN** se envía `PATCH /repuestos/{id}` con sólo `descripcion`
- **THEN** la descripción cambia, el precio y el stock quedan iguales, y no se agrega historial de precio

#### Scenario: Aumento de precio

- **WHEN** se envía `PATCH /repuestos/{id}` con un precio mayor al actual
- **THEN** la respuesta es **200**, el precio cambia y se agrega una línea con el precio anterior y el nuevo

#### Scenario: Mismo precio

- **WHEN** se envía `PATCH /repuestos/{id}` con el mismo precio actual
- **THEN** la respuesta es **200** y no se agrega ninguna línea al historial de precios

#### Scenario: Baja de precio

- **WHEN** se envía `PATCH /repuestos/{id}` con un precio menor al actual
- **THEN** la respuesta es **422**, el precio queda intacto y no se agrega historial

#### Scenario: Intento de editar el stock

- **WHEN** se envía `PATCH /repuestos/{id}` con un campo `stock`
- **THEN** la respuesta es **422** y el stock no cambia

#### Scenario: PATCH de repuesto inexistente

- **WHEN** se envía `PATCH /repuestos/{id}` con un id inexistente
- **THEN** la respuesta es **404**

### Requirement: Baja lógica de repuesto

`DELETE /repuestos/{id}` MUST escribir `borrado_en` y responder **204** sin borrar la fila. MUST responder **404** si el repuesto no existe o ya está dado de baja.

#### Scenario: Baja exitosa

- **WHEN** se pide `DELETE /repuestos/{id}` de un repuesto vigente
- **THEN** la respuesta es **204** y el repuesto deja de aparecer en el listado y en el detalle

#### Scenario: Baja repetida

- **WHEN** se pide `DELETE /repuestos/{id}` sobre un repuesto ya dado de baja
- **THEN** la respuesta es **404**

#### Scenario: Reuso del código tras la baja

- **WHEN** se da de baja `FIL-001` y se intenta crear un nuevo repuesto vigente con `FIL-001`
- **THEN** el alta es **201**

### Requirement: Reposición de stock

`POST /repuestos/{id}/reponer` MUST aceptar una `cantidad` mayor que cero, MUST incrementar el stock y MUST crear un `movimiento_stock` con motivo `"Reposición"` y `orden_id` nulo, en la misma transacción. MUST responder **200** con el repuesto actualizado, **404** si el repuesto no existe o está dado de baja y **422** si la cantidad no es válida.

#### Scenario: Reposición exitosa

- **WHEN** se envía `POST /repuestos/{id}/reponer` con `cantidad = 5`
- **THEN** la respuesta es **200**, el stock aumenta en 5 y existe un movimiento `"Reposición"` de 5 unidades

#### Scenario: Cantidad no positiva

- **WHEN** se envía `POST /repuestos/{id}/reponer` con `cantidad = 0`
- **THEN** la respuesta es **422** y el stock no cambia

#### Scenario: Repuesto inexistente

- **WHEN** se envía `POST /repuestos/{id}/reponer` con un id inexistente
- **THEN** la respuesta es **404**

### Requirement: Historiales de movimientos y precios

`GET /repuestos/{id}/movimientos` y `GET /repuestos/{id}/precios` MUST responder **200** con los registros del repuesto ordenados del más reciente al más antiguo, y **404** si el repuesto no existe o está dado de baja.

#### Scenario: Movimientos del repuesto

- **WHEN** se pide `GET /repuestos/{id}/movimientos` de un repuesto con movimientos
- **THEN** la respuesta es **200** e incluye cantidad, motivo, fecha y orden asociada cuando corresponda

#### Scenario: Historial de precios

- **WHEN** se pide `GET /repuestos/{id}/precios` de un repuesto con un aumento registrado
- **THEN** la respuesta es **200** e incluye el precio anterior, el nuevo y la fecha

#### Scenario: Historial de repuesto inexistente

- **WHEN** se pide cualquiera de los dos historiales con un id inexistente
- **THEN** la respuesta es **404**

### Requirement: El stock sólo cambia por movimientos

Ninguna ruta de repuestos MUST permitir fijar el stock directamente; todo cambio de stock MUST quedar registrado como un movimiento.

#### Scenario: No existe edición directa de stock

- **WHEN** se revisan las rutas de repuestos
- **THEN** sólo el alta con `stock_inicial` y la reposición modifican el stock, y ambas dejan movimiento
