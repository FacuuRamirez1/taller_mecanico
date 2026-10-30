# Spec Delta

## Purpose

Define los contratos de entrada y salida de la API como schemas separados de las tablas, de modo que ninguna petición acepte campos no declarados y ninguna respuesta filtre columnas internas.

## ADDED Requirements

### Requirement: Entradas cerradas a campos declarados

Todo schema de entrada MUST rechazar campos no declarados (`extra="forbid"`) y tipos inválidos con **422**, sin llegar a escribir en la base.

#### Scenario: Campo extra en un alta

- **WHEN** se envía `POST /repuestos` con un campo no declarado además de los válidos
- **THEN** la respuesta es **422** y no se inserta ninguna fila

#### Scenario: Tipo inválido en un campo declarado

- **WHEN** se envía `POST /clientes/{id}/vehiculos` con `anio` como texto no numérico
- **THEN** la respuesta es **422** con un mensaje de contrato propio

### Requirement: Salidas sin `password_hash`

Ningún schema de salida MUST incluir `password_hash` ni ningún otro secreto, aunque el modelo de tabla lo tenga.

#### Scenario: Usuario devuelto sin hash

- **WHEN** se serializa un usuario para una respuesta
- **THEN** el cuerpo contiene `id`, `email`, `nombre`, `activo`, `debe_cambiar_password` y `password_cambiada_en`, y no contiene `password_hash`

#### Scenario: Alta de usuario sin hash

- **WHEN** se da de alta un usuario y se devuelve su representación
- **THEN** la respuesta es **201** y no incluye `password_hash` ni la contraseña enviada

### Requirement: `PATCH` aplica sólo los campos enviados

Toda modificación parcial MUST aplicar únicamente los campos presentes en el cuerpo (`exclude_unset=True`); los campos omitidos MUST conservar su valor.

#### Scenario: PATCH sólo de descripción

- **WHEN** se envía `PATCH /repuestos/{id}` con `descripcion` y sin `precio`
- **THEN** la descripción cambia y el precio queda exactamente igual

#### Scenario: PATCH con cuerpo vacío

- **WHEN** se envía `PATCH /repuestos/{id}` con `{}`
- **THEN** la respuesta es **200** y el repuesto queda sin cambios

### Requirement: Alta de orden sin campos calculados por el servidor

El schema de alta de orden MUST NOT aceptar `precio`, `total`, `estado` ni `creada_en`; esos valores los calcula o asigna el servidor. Enviarlos MUST producir **422**.

#### Scenario: Total enviado por el cliente

- **WHEN** se envía `POST /ordenes` con un campo `total`
- **THEN** la respuesta es **422** y no se crea la orden

#### Scenario: Estado enviado por el cliente

- **WHEN** se envía `POST /ordenes` con un campo `estado`
- **THEN** la respuesta es **422** y no se crea la orden

#### Scenario: Alta válida con ítems

- **WHEN** se envía `POST /ordenes` sólo con vehículo, falla e ítems (`repuesto_id`, `cantidad`)
- **THEN** el contrato acepta el cuerpo; el precio unitario, el total, el estado y la fecha los asigna el servidor en C-06

### Requirement: Alta de repuesto con `stock_inicial`

El schema de alta de repuesto MUST aceptar `stock_inicial` y MUST NOT aceptar `stock`. Enviar `stock` MUST producir **422**.

#### Scenario: `stock` rechazado

- **WHEN** se envía `POST /repuestos` con `stock` en lugar de `stock_inicial`
- **THEN** la respuesta es **422** y no se crea el repuesto

#### Scenario: `stock_inicial` aceptado

- **WHEN** se envía `POST /repuestos` con `stock_inicial = 10`
- **THEN** el contrato acepta el cuerpo y el repuesto nace con stock 10

### Requirement: Contraseña entre 8 caracteres y 72 bytes

Todo schema que reciba una contraseña MUST exigir al menos 8 caracteres y MUST rechazar con **422** cualquier valor que supere 72 bytes en UTF-8, sin producir 500.

#### Scenario: Contraseña de 7 caracteres

- **WHEN** se envía una contraseña de 7 caracteres
- **THEN** la respuesta es **422**

#### Scenario: Contraseña de 8 caracteres

- **WHEN** se envía una contraseña de 8 caracteres ASCII
- **THEN** el contrato la acepta

#### Scenario: Contraseña multibyte que supera 72 bytes

- **WHEN** se envía una contraseña de 30 caracteres multibyte cuyo largo en UTF-8 supera 72 bytes
- **THEN** la respuesta es **422** y no se calcula ningún hash

### Requirement: Contratos de órdenes y usuarios disponibles sin endpoints

Los schemas de entrada/salida de usuarios y órdenes MUST existir y ser reutilizables por C-04 y C-06, aunque C-03 no exponga todavía sus rutas.

#### Scenario: Schemas importables

- **WHEN** se importan los schemas de usuarios y de órdenes
- **THEN** exponen modelos de alta, de modificación y de lectura sin requerir conexión a la base
