# Spec Delta

## Purpose

Define un envoltorio único para todos los listados de la API, con validación de página y tamaño, conteo coherente con los filtros y un error propio cuando se pide una página inexistente.

## ADDED Requirements

### Requirement: Envoltorio uniforme de listados

Todo listado paginado MUST devolver exactamente los campos `items`, `total`, `page`, `size` y `pages`. `items` MUST ser una lista, `total` el número de filas que cumplen los filtros, `page` la página pedida, `size` el tamaño efectivo y `pages` la cantidad de páginas.

#### Scenario: Listado con resultados

- **WHEN** se pide `GET /repuestos?page=1&size=2` con 5 repuestos vigentes
- **THEN** la respuesta es **200** con `items` de 2 elementos, `total = 5`, `page = 1`, `size = 2` y `pages = 3`

#### Scenario: Campos exactos del envoltorio

- **WHEN** se inspecciona el cuerpo de cualquier listado paginado
- **THEN** contiene los cinco campos del envoltorio y ningún otro campo de control

### Requirement: Validación de `page` y `size`

`page` MUST ser mayor o igual a 1. `size` MUST estar entre 1 y 100, con valor por defecto 20. Un valor fuera de rango MUST producir **422**.

#### Scenario: Página cero

- **WHEN** se pide `GET /repuestos?page=0`
- **THEN** la respuesta es **422**

#### Scenario: Tamaño cero o mayor a cien

- **WHEN** se pide `GET /repuestos?size=0` o `GET /repuestos?size=101`
- **THEN** la respuesta es **422**

#### Scenario: Tamaño por defecto

- **WHEN** se pide `GET /repuestos` sin `size`
- **THEN** la respuesta usa `size = 20`

#### Scenario: Tamaño excesivo del caso C-16

- **WHEN** se pide `GET /repuestos?size=500`
- **THEN** la respuesta es **422**

### Requirement: Página posterior a la última

Si `total` es mayor que cero y `page` supera la última página, la respuesta MUST ser **422** con un mensaje propio que indique la página pedida y la cantidad de páginas existentes, sin texto de la base.

#### Scenario: Página inexistente

- **WHEN** hay 3 repuestos, `size = 2` (2 páginas) y se pide `page = 3`
- **THEN** la respuesta es **422** con el mensaje `La página 3 no existe: hay 2`

### Requirement: `total` con los mismos filtros que la página

El conteo MUST aplicar exactamente los mismos filtros que la consulta de la página, de modo que `total` y `items` sean coherentes.

#### Scenario: Total filtrado

- **WHEN** se pide `GET /repuestos?q=filtro` y sólo 2 repuestos vigentes coinciden
- **THEN** `total = 2` y `items` contiene esos 2 repuestos

#### Scenario: Total sin coincidencias

- **WHEN** se pide `GET /repuestos?q=inexistente`
- **THEN** `total = 0` e `items` está vacío

### Requirement: Cero resultados devuelve una página vacía

Cuando no hay resultados, la respuesta MUST ser **200** con `items` vacío, `total = 0` y `pages = 0`, y MUST NOT responder 422 por página inexistente.

#### Scenario: Listado vacío en la primera página

- **WHEN** no hay repuestos vigentes y se pide `page = 1`
- **THEN** la respuesta es **200** con `items = []`, `total = 0`, `pages = 0`

#### Scenario: Listado vacío en una página alta

- **WHEN** no hay resultados y se pide `page = 5`
- **THEN** la respuesta es **200** con `items = []`, `total = 0`, `pages = 0`
