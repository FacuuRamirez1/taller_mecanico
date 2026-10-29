# Reglas de Negocio

Veinte reglas explícitas (`RN-01` a `RN-20`). El enunciado y el garante esperado son **literales de la consigna** (págs. 7-9); la columna HTTP es la respuesta que produce el incumplimiento según los códigos de la tabla de endpoints.

## Tabla maestra

| Regla | Enunciado (literal) | Garante esperado | HTTP |
|---|---|---|---|
| **RN-01** | El correo de un usuario y el documento de un cliente son únicos. La patente de un vehículo y el código de un repuesto son únicos entre los que no están dados de baja. | `UNIQUE` e índices únicos parciales en la base; mensaje propio | **409** |
| **RN-02** | El auto-registro crea el usuario, su rol CLIENTE y su ficha de cliente: o quedan las tres filas, o ninguna. Si el documento ya es de un cliente del taller, el registro da 409 y no se apropia de esa ficha. | Un solo Unit of Work | **409** |
| **RN-03** | Un usuario tiene a lo sumo una asignación abierta por rol. | Índice único parcial | **409** |
| **RN-04** | Los permisos se deciden con los roles vigentes en la base, en cada petición. Los roles que trae el token son informativos. | Dependencia que consulta `asignacion_rol` | **403** |
| **RN-05** | Un administrador no puede revocarse su propio rol ADMIN, y el sistema nunca queda sin administradores vigentes. | Comprobación en el servicio | **409** |
| **RN-06** | Mientras un usuario tenga el cambio de contraseña pendiente, sólo puede usar las rutas de `/auth` y las de salud. | Dos grupos de rutas | **403** |
| **RN-07** | Al cambiar la contraseña, las sesiones emitidas antes dejan de valer, aunque sean del mismo segundo que el cambio; la que devuelve el propio cambio, no. | Comparación de `iat` con `password_cambiada_en`, **sin truncar** | **401** |
| **RN-08** | Después de 5 intentos fallidos con el mismo correo desde la misma dirección en 60 segundos, el login responde 429 sin verificar la contraseña. Un login correcto reinicia la cuenta: los fallos anteriores siguen en la tabla, pero dejan de contar. | Conteo sobre `intento_acceso`; `Retry-After` | **429** |
| **RN-09** | El login responde lo mismo, y tarda lo mismo, exista o no el correo. | Mismo mensaje; verificación contra un hash ficticio | **401** |
| **RN-10** | Una orden nace PENDIENTE con al menos un ítem y sin repuestos repetidos. El precio de cada ítem se copia del repuesto, y el total lo calcula el servidor. | DTO; el precio y el total nunca viajan en el cuerpo | **422** (contrato) / **409** (si llega a la base) |
| **RN-11** | Las transiciones de una orden son PENDIENTE → EN_REPARACION (la inicia un mecánico, que queda asignado), EN_REPARACION → TERMINADA (la termina el mecánico asignado o un administrador) y PENDIENTE → CANCELADA. | Servicio; 409 si el estado no lo permite | **409** |
| **RN-12** | Cancelan una orden la recepción, el administrador o el dueño del vehículo. El permiso se evalúa antes que el estado. | Servicio; **403 antes que 409** | **403** / **409** |
| **RN-13** | Terminar una orden descuenta el stock de cada ítem, deja un movimiento por cada salida y una línea de historial. Si un repuesto no alcanza, no queda ninguna de esas escrituras. | Un solo Unit of Work | **409** |
| **RN-14** | El stock de un repuesto sólo cambia a través de movimientos: el alta con stock inicial, la reposición y la terminación de órdenes. No se edita por PATCH. | Punto único de escritura de stock | **422** (`extra="forbid"`) |
| **RN-15** | `historial_estado_orden`, `movimiento_stock` y `historial_precio_repuesto` son de sólo agregado: nadie puede modificar ni borrar sus filas. | Disparador en la base, instalado por migración | error de trigger (probado en psql, `C-14`) |
| **RN-16** | Un vehículo o un repuesto dado de baja deja de aparecer y no se puede usar en órdenes nuevas, pero sus datos se conservan. Un vehículo con órdenes abiertas —en un estado que el catálogo no marca como final— no se da de baja. | Borrado lógico; `es_final` | **409** |
| **RN-17** | Lo propio sólo pide estar autenticado: un cliente ve sus vehículos y las órdenes de sus vehículos, y ninguna otra. | `/mis-*` y comprobación de dueño | **403** |
| **RN-18** | Ningún error devuelve al cliente texto interno de la base, que le entregaría el mapa del esquema. Ninguna entrada inválida termina en un 500. | Traducción del `IntegrityError`; validación en el contrato | **409** / **422** |
| **RN-19** | Los estados posibles de una orden son las filas del catálogo `estado_orden`. El catálogo se consulta desde la API y no se edita desde ella. Si está vacío, crear una orden responde 409 con un mensaje propio. | Clave foránea; repositorio de sólo lectura | **409** |
| **RN-20** | Cada cambio del precio de un repuesto deja una línea en `historial_precio_repuesto`, en la misma transacción que el cambio. Un PATCH que no cambia el precio no deja línea. | Un solo Unit of Work; `CHECK precio_nuevo > precio_anterior` | **200**; **409**/**422** si el precio baja |

## Dominio: identidad y unicidad

### RN-01 — Unicidad
Hay **cuatro** unicidades, con dos mecanismos distintos:

| Dato | Mecanismo | Por qué |
|---|---|---|
| `usuario.email` | `UNIQUE` común | La fila no se borra nunca |
| `cliente.documento` | `UNIQUE` común | La fila no se borra nunca |
| `vehiculo.patente` | **índice único parcial** `WHERE borrado_en IS NULL` | Un auto vendido se da de baja y el comprador lo registra con la misma patente (`C-19`) |
| `repuesto.codigo` | **índice único parcial** `WHERE borrado_en IS NULL` | Un código dado de baja puede volver a usarse |

**Prohibido**: verificar la unicidad con un `SELECT` previo. Se intenta el `INSERT` y se traduce el `IntegrityError` a **409 con mensaje propio**. Un `UNIQUE` común sobre `patente` haría que la base respondiera "ya existe" de un vehículo que la aplicación no muestra en ningún listado.

### RN-02 — Auto-registro atómico
`POST /auth/registro` escribe **tres filas** en un solo UoW: `usuario` + `asignacion_rol` (`CLIENTE`, abierta) + `cliente`.

- Si cualquiera falla → **rollback completo**: o las tres, o ninguna.
- Si el `documento` ya es de un cliente del taller → **409** y **no se apropia de la ficha** (no vincula el usuario nuevo al cliente existente, no la modifica).
- Si el `email` ya existe → **409**.
- La respuesta es **201** y **no** incluye `password_hash`.
- **No** se puede mandar `rol` en el cuerpo: `extra="forbid"` → **422**.

### RN-03 — Una asignación abierta por rol
Índice único parcial `(usuario_id, rol) WHERE revocada_en IS NULL`. Asignar un rol que ya está abierto → **409**.

Reasignar un rol **vencido** es válido: primero se cierra la fila anterior (`revocada_en = now()`) y después se abre la nueva, en el mismo UoW.

## Dominio: autenticación

### RN-06 — Cambio obligatorio de contraseña
Con `debe_cambiar_password = true`, todo el **grupo protegido** responde **403**. Sólo pasan `/health/*` y `/auth/*`.

Se implementa con **dos grupos de rutas** en `main.py` (uno abierto y uno protegido, con el control montado **una sola vez**), porque FastAPI **suma** dependencias y no las resta. Verificar el flag dentro de cada ruta sería repetitivo y fácil de olvidar.

`POST /auth/cambiar-password` está en el grupo abierto justamente para que el usuario bloqueado pueda desbloquearse.

### RN-07 — Invalidación de sesiones por `iat`
Al cambiar la contraseña se escribe `password_cambiada_en = now()` y se emite un token nuevo **después** de anotar el cambio.

- `get_usuario_actual` rechaza con **401** todo token cuyo `iat` sea **anterior** a `password_cambiada_en`.
- La comparación es **sin truncar a segundos**: el estándar JWT admite fracciones y el token se emite con la hora completa. Si se truncara, una sesión iniciada en el mismo segundo pero antes del cambio sería indistinguible de la nueva y seguiría valiendo.
- El token que devuelve el propio cambio **sí vale**, porque se emite después del `UPDATE`.
- **`C-09`**: sin esperar entre el login y el cambio, la cookie nueva vale y la anterior da 401.

### RN-08 — Límite de intentos
- Universo: filas de `intento_acceso` con `exito = false`, **mismo email y misma IP**, dentro de los últimos **60 s**.
- Al llegar a **5 fallos**, el **sexto** intento responde **429** con `Retry-After`, **sin calcular ni verificar ningún hash**.
- El límite se evalúa **primero**, antes de buscar el usuario y antes de bcrypt: es lo que hace que el 429 llegue en pocos milisegundos (`C-05`).
- Un login correcto **reinicia la cuenta**: los fallos anteriores quedan en la tabla pero dejan de contar. La implementación concreta (marcar un corte, contar desde el último éxito) es una decisión abierta en cuanto a la ventana fija/deslizante → `10_preguntas_abiertas.md`.
- `Retry-After` en segundos.

### RN-09 — No revelar qué cuentas existen
- Correo inexistente y contraseña incorrecta devuelven **el mismo cuerpo** y el **mismo código (401)**.
- Si el correo no existe, se verifica igual contra un **hash ficticio** calculado una vez en el lifespan, para que el tiempo sea parecido.
- **`C-04`** compara cuerpo y tiempo.

### Límite de 72 bytes
Todo campo que termina en bcrypt —contraseña del login, la actual del cambio, la del alta de personal y la del registro— acepta **como máximo 72 bytes**: bcrypt no mira más allá y desde la versión 5 rechaza con excepción lo que sobra. Son **bytes, no caracteres** (una `ñ` ocupa dos). Sin el límite en el contrato, una contraseña larga daría **500** en lugar de **422**.

## Dominio: autorización

### RN-04 — Roles vigentes por petición
`requiere_rol` consulta `asignacion_rol` **en cada petición** y considera vigente = `revocada_en IS NULL AND (vence_en IS NULL OR vence_en > now())`.

- Revocar un rol corta el acceso **en la petición siguiente**, con la misma cookie (`C-07`).
- Los roles del token son **informativos**: `/auth/yo` los muestra al lado de los vigentes para que se vea la diferencia.
- Sin sesión válida → **401**; con sesión pero sin rol → **403**.

### RN-05 — Autoprotección del administrador
Dos comprobaciones en el servicio, ambas **409**:

1. Un admin **no puede revocarse su propio rol ADMIN** (`C-08`).
2. El sistema **nunca queda sin administradores vigentes**: si la revocación dejaría cero, se rechaza.

Se evalúan **antes** de escribir: no se confía en un conteo posterior. Queda abierto si el punto 2 también aplica al **desactivar** un usuario (`activo = false`) → `10_preguntas_abiertas.md` (P1).

### RN-17 — Lo propio sólo pide estar autenticado
- `/mis-vehiculos` y `/mis-ordenes` **no** llevan `requiere_rol`: alcanza con estar autenticado.
- El dueño de una orden es el dueño del **vehículo** de esa orden.
- Acceder a lo ajeno → **403** (no 404: existe, pero no es tuyo).
- **`C-06`**: el cliente ve su orden (200) y no la ajena (403).

## Dominio: órdenes

### RN-10 — Alta de orden
- Nace en `PENDIENTE` (no se acepta `estado` en el cuerpo).
- **Al menos un ítem**; sin ítems → **422** por contrato (`min_length=1`).
- **Sin repuestos repetidos**: el DTO lo valida (**422**) y `UNIQUE (orden_id, repuesto_id)` lo respalda (**409** si llegara a la base).
- `precio_unitario` se **copia** del repuesto vigente; `subtotal = cantidad * precio_unitario`.
- `total` lo **calcula el servidor** sumando los subtotales.
- **Nunca** viajan en el cuerpo: `precio`, `total`, `estado`, `creada_en` → `extra="forbid"` → **422**.
- Repuesto inexistente o dado de baja → **409** y **la orden no queda creada** (`C-10`). Es una sola transacción: si falla un ítem, no queda la cabecera.
- Se escribe además la primera línea de `historial_estado_orden`: `(null → PENDIENTE, usuario_id = quien crea)`.

### RN-11 — Transiciones
```
                 iniciar (MECANICO)
   PENDIENTE ────────────────────────► EN_REPARACION ──── terminar (mecánico asignado o ADMIN) ────► TERMINADA
       │                                                                                                 (final)
       └──────────── cancelar (RECEPCION, ADMIN o dueño) ─────────────► CANCELADA (final)
```
- `iniciar`: sólo `PENDIENTE`. Asigna `mecanico_id` al mecánico que la inicia.
- `terminar`: sólo `EN_REPARACION`, y sólo el **mecánico asignado** o un **ADMIN** (otro mecánico → **403**).
- `cancelar`: sólo `PENDIENTE`.
- Cualquier transición no listada → **409**.
- Cada transición escribe **una línea** en `historial_estado_orden`.

### RN-12 — Cancelación: 403 antes que 409
La ruta `POST /ordenes/{id}/cancelar` **no lleva `requiere_rol`** (el dueño no tiene rol de personal). El servicio evalúa en este orden:

1. ¿Existe la orden? → **404**.
2. ¿Es RECEPCION, ADMIN o el dueño del vehículo? → si no, **403**.
3. ¿Está en `PENDIENTE`? → si no, **409**.

`C-13` verifica los tres: dueño cancela la propia (200), orden ajena (403), orden terminada (409).

### RN-13 — Terminar: todo o nada
En **un solo UoW**:

1. Verifica el estado (`EN_REPARACION`) y el actor (asignado o ADMIN).
2. Para **cada ítem**: verifica `stock >= cantidad`; si alguno no alcanza → **409** y **nada** se escribe.
3. Descuenta `stock` por el **punto único de escritura** (RN-14) y agrega **un `movimiento_stock` por ítem** (no uno agregado), con `orden_id`, `usuario_id`, `cantidad` y motivo de consumo.
4. Agrega **una línea** `EN_REPARACION → TERMINADA` en `historial_estado_orden`.
5. Actualiza `estado = 'TERMINADA'`.

Si cualquier paso falla → rollback: el estado, el stock, los movimientos y el historial quedan **exactamente como estaban** (`C-11`). El `movimiento_stock` **no** guarda el stock resultante: el stock vive en `repuesto` y los movimientos son el registro.

**Después** del commit, el router agenda con `BackgroundTasks` el aviso al cliente (`asyncio.sleep(0.5)` + mensaje en el log). Si la transacción no se confirmó, **no se agenda**.

### RN-19 — El catálogo manda
- `orden_trabajo.estado` es FK a `estado_orden.codigo`: la base rechaza un estado que no exista.
- El `enum` de Python es el contrato de la API: un `estado` no declarado en `GET /ordenes?estado=...` → **422** (`C-17`).
- El catálogo se **consulta** (`GET /estados-orden`, por `posicion`) y **no se edita** por API.
- **Catálogo vacío → crear orden responde 409** con mensaje propio (no 500, no 422).

### RN-16 — Bajas lógicas
- `DELETE /vehiculos/{id}` y `DELETE /repuestos/{id}` escriben `borrado_en` y responden **204**.
- El recurso deja de aparecer en listados y de poder usarse en órdenes nuevas.
- Un vehículo con **órdenes abiertas** (algún estado con `es_final = false`) → **409**.
- **`C-19`**: dar de baja un vehículo sin órdenes (204) y registrarlo con la misma patente para otro cliente (201); una segunda patente vigente igual → 409.

## Dominio: inventario y precio

### RN-14 — Punto único de escritura de stock
El stock **sólo** cambia por:

| Origen | Movimiento | `orden_id` |
|---|---|---|
| `POST /repuestos` con `stock_inicial` | `"Stock inicial"` | `null` |
| `POST /repuestos/{id}/reponer` | `"Reposición"` | `null` |
| `POST /ordenes/{id}/terminar` | `"Consumo en orden"` (uno por ítem) | la orden |

`PATCH /repuestos/{id}` acepta **descripción y precio**, nunca `stock`: `extra="forbid"` → **422** (`C-16`).

### RN-20 — Historial de precios en la misma transacción
- Si el `PATCH` cambia el precio: actualiza `repuesto.precio` **y** agrega una línea en `historial_precio_repuesto` con `precio_anterior` y `precio_nuevo`, en el **mismo UoW**.
- Si el `PATCH` no cambia el precio (mismo valor, o sólo descripción): **no** deja línea (`C-18`).
- `CHECK precio_nuevo > precio_anterior` → el historial sólo admite **aumentos**. Bajar el precio viola el `CHECK`; el servicio debe traducirlo a un código de negocio (no 500) → decisión pendiente en `10_preguntas_abiertas.md`.

## Dominio: integridad

### RN-15 — Sólo agregado por disparador
La **segunda migración** (escrita a mano) instala una función y un trigger que rechazan `UPDATE` y `DELETE` sobre:

- `historial_estado_orden`
- `movimiento_stock`
- `historial_precio_repuesto`

Venga de donde venga: la API, `psql` o un script. `autogenerate` **no** ve funciones ni disparadores, por eso va a mano. `C-14` verifica en psql los **seis rechazos** (UPDATE y DELETE por cada una de las tres tablas).

### RN-18 — Errores sin filtrar el esquema
| Situación | Traducción |
|---|---|
| Violación de `UNIQUE` | **409** con mensaje propio ("Ya existe un vehículo con esa patente", etc.) |
| Violación de `FK` | **409** (o 404 si el recurso referenciado no existe) |
| Violación de `CHECK` | **409**/**422** según el caso; nunca 500 |
| Cuerpo con campos extra o tipos inválidos | **422** por contrato |
| Parámetro de ruta no entero (`C-01`) | **422**, sin ejecutar el handler |
| Cualquier error no previsto | 500 **sin** texto de PostgreSQL ni traza |

**`C-16`**: `q=' OR '1'='1` devuelve lista vacía con `total 0` — la búsqueda usa **parámetros ligados**, nunca concatenación.

## Mapa de trazabilidad

| Regla | Ejercicio | Endpoint(s) | Caso |
|---|---|---|---|
| RN-01 | Ej. 2 | `POST /auth/registro`, `POST /clientes`, `POST /clientes/{id}/vehiculos`, `POST /repuestos` | C-02, C-19 |
| RN-02 | Ej. 4, 6 | `POST /auth/registro` | C-02 |
| RN-03 | Ej. 2, 5 | `POST /usuarios/{id}/roles` | — |
| RN-04 | Ej. 5 | todas las protegidas | C-06, C-07 |
| RN-05 | Ej. 5 | `DELETE /usuarios/{id}/roles/{rol}` | C-08 |
| RN-06 | Ej. 5 | grupo protegido | C-09 |
| RN-07 | Ej. 5 | `POST /auth/cambiar-password`, `get_usuario_actual` | C-09 |
| RN-08 | Ej. 4, 7 | `POST /auth/login` | C-05 |
| RN-09 | Ej. 4 | `POST /auth/login` | C-04 |
| RN-10 | Ej. 3, 6 | `POST /ordenes` | C-10 |
| RN-11 | Ej. 6 | `iniciar` / `terminar` / `cancelar` | C-11, C-12, C-13 |
| RN-12 | Ej. 5, 6 | `POST /ordenes/{id}/cancelar` | C-13 |
| RN-13 | Ej. 6 | `POST /ordenes/{id}/terminar` | C-11, C-12 |
| RN-14 | Ej. 6 | `POST /repuestos`, `reponer`, `terminar`, `PATCH` | C-12, C-16 |
| RN-15 | Ej. 2, 7 | (base) | C-14 |
| RN-16 | Ej. 3, 6 | `DELETE /vehiculos/{id}`, `DELETE /repuestos/{id}` | C-19 |
| RN-17 | Ej. 5 | `/mis-*`, `GET /ordenes/{id}` | C-06 |
| RN-18 | Ej. 3 | todas | C-01, C-16 |
| RN-19 | Ej. 2, 6 | `GET /estados-orden`, `POST /ordenes` | C-17 |
| RN-20 | Ej. 6, 7 | `PATCH /repuestos/{id}` | C-18 |
