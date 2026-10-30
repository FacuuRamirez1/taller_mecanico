# Spec Delta

## Purpose

Define cómo la API traduce los conflictos de la base y los errores de contrato a códigos y mensajes propios, sin exponer el esquema ni producir 500 ante entradas inválidas.

## ADDED Requirements

### Requirement: Violación de unicidad traducida a 409

Toda violación de unicidad MUST traducirse a **409** con un mensaje propio que describa el conflicto de negocio. La decisión MUST basarse en el nombre de la constraint violada, MUST NOT depender de una consulta previa de unicidad y MUST NOT incluir el texto de PostgreSQL.

#### Scenario: Documento repetido

- **WHEN** se intenta dar de alta un cliente con un documento ya existente
- **THEN** la respuesta es **409** con un mensaje propio sobre el documento

#### Scenario: Patente vigente repetida

- **WHEN** se intenta dar de alta un vehículo con una patente ya usada por otro vehículo vigente
- **THEN** la respuesta es **409** con un mensaje propio sobre la patente

#### Scenario: Código de repuesto vigente repetido

- **WHEN** se intenta dar de alta un repuesto con un código ya usado por otro repuesto vigente
- **THEN** la respuesta es **409** con un mensaje propio sobre el código

#### Scenario: Sin SELECT previo

- **WHEN** se revisa el flujo de un alta que termina en 409
- **THEN** la aplicación intentó la escritura y tradujo el error de la base, sin una consulta de existencia anterior

### Requirement: Recurso de la ruta inexistente

Cuando el recurso identificado en la ruta no existe, no está vigente o ya fue dado de baja, la respuesta MUST ser **404** con un mensaje propio.

#### Scenario: Repuesto inexistente

- **WHEN** se pide `GET /repuestos/{id}` con un id que no existe
- **THEN** la respuesta es **404**

#### Scenario: Vehículo ya dado de baja

- **WHEN** se pide `DELETE /vehiculos/{id}` sobre un vehículo con `borrado_en` no nulo
- **THEN** la respuesta es **404**

### Requirement: Error de contrato

Un cuerpo, parámetro de consulta o tipo inválido MUST producir **422** con un mensaje propio, sin ejecutar la escritura.

#### Scenario: Campo extra

- **WHEN** se envía un cuerpo con un campo no declarado
- **THEN** la respuesta es **422**

#### Scenario: Identificador de ruta no entero

- **WHEN** se pide `GET /repuestos/abc`
- **THEN** la respuesta es **422** y el handler no se ejecuta

### Requirement: Violación de `CHECK` de negocio sin 500

Una violación de `CHECK` que represente una regla de negocio MUST traducirse a **422** o **409** según el caso, nunca a 500. La traducción MUST reconocer la constraint por su nombre.

#### Scenario: Baja de precio de repuesto

- **WHEN** se intenta `PATCH /repuestos/{id}` con un precio menor al actual
- **THEN** la respuesta es **422** con un mensaje propio sobre que el precio no puede bajar, y el precio queda intacto

#### Scenario: Restricción desconocida

- **WHEN** la base rechaza una escritura por una constraint no mapeada
- **THEN** la respuesta es **409** con un mensaje genérico propio y sin texto interno de la base

### Requirement: Ninguna entrada inválida produce 500

Ninguna entrada inválida de un cliente MUST producir una respuesta 500 ni exponer una traza o el texto interno de PostgreSQL.

#### Scenario: Barrido de entradas inválidas

- **WHEN** se prueban cuerpos con campos extra, tipos incorrectos, identificadores no enteros y páginas fuera de rango
- **THEN** todas las respuestas son 4xx con mensajes propios
