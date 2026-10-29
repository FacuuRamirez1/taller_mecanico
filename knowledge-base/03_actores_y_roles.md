# Actores y Roles

## Actores del sistema

| Actor | Descripción | Cómo interactúa |
|---|---|---|
| **ADMIN** | Dueño o encargado del taller. Rol `ADMIN` en `asignacion_rol`. | API con cookie: administra repuestos, stock, personal, roles y consulta eventos de seguridad. Termina cualquier orden en reparación. |
| **RECEPCION** | Personal de mostrador. Rol `RECEPCION`. | API con cookie: alta de clientes, vehículos y órdenes; listados; cancelación; bajas de vehículos y consulta de repuestos. |
| **MECANICO** | Mecánico del taller. Rol `MECANICO`. | API con cookie: toma (inicia) órdenes pendientes, las termina y consulta repuestos y órdenes. |
| **CLIENTE** | Dueño del vehículo que se auto-registra. Rol `CLIENTE`. | API con cookie: `/auth/registro`, `/mis-vehiculos`, `/mis-ordenes`, detalle y cancelación de sus propias órdenes, cambio de contraseña. |
| **SISTEMA** | **Actor texto**, no un usuario. No existe en `usuario` ni se autentica. | Sólo aparece como valor de `evento_seguridad.actor` (ej. `"Carga de los datos iniciales"` en el seed). |
| **Cualquiera** (anónimo) | Sin cookie. | Sólo `/health/*` y `/auth/registro`, `/auth/login`. |

### Los roles no están en `usuario`

`usuario` **no tiene columna `rol`**. Los roles de una persona son las filas **vigentes** de `asignacion_rol`: no revocadas (`revocada_en IS NULL`) y sin vencer (`vence_en IS NULL OR vence_en > now()`).

- Revocar un rol escribe `revocada_en`; la fila **no se borra nunca** (historial de quién tuvo qué rol y hasta cuándo).
- Reasignar un rol vencido cierra la fila anterior y abre una nueva.
- Un usuario puede tener **a lo sumo una asignación abierta por rol** (índice único parcial).

### `SISTEMA` no es un usuario

`SISTEMA` es un **texto** en `evento_seguridad.actor`. Consecuencias prácticas:

- No tiene fila en `usuario`, no tiene contraseña, no puede loguearse, no aparece en `/usuarios/{id}/roles`.
- `historial_estado_orden.usuario_id` es `NOT NULL` y apunta a `usuario`: por eso la primera línea del historial de una orden la escribe **el usuario que la creó** (en el ejemplo de la consigna, `usuario_id: 3`), no `SISTEMA`.
- El seed escribe **una** línea de `evento_seguridad` con `actor = "SISTEMA"` y `accion = "Carga de los datos iniciales"`.

## RBAC — Matriz de permisos por recurso

| Rol | Usuarios y roles | Eventos | Clientes | Vehículos | Repuestos y stock | Órdenes | Rutas `/mis-*` |
|---|---|---|---|---|---|---|---|
| **ADMIN** | C, R, U (roles: asignar/revocar) | R (listado paginado) | C, R | C, D (baja lógica) | C, R, U (descripción/precio), D, reponer, movimientos, precios | C, R, terminar, cancelar, detalle | R |
| **RECEPCION** | — | — | C, R | C, D | R | C, R, cancelar, detalle | R |
| **MECANICO** | — | — | — | — | R | R, iniciar, terminar (sólo la asignada), detalle | R |
| **CLIENTE** | — | — | — | — | — | detalle y cancelar **sólo las propias** | R |
| **Anónimo** | — | — | — | — | — | — | — |

`R` = lectura, `C` = alta, `U` = modificación, `D` = baja.

## RBAC — Tabla literal de endpoints

Reproducción de la tabla "Endpoints de referencia" de la consigna (págs. 15-17). Es la fuente de verdad para `requiere_rol` y para los códigos esperados.

| Grupo | Método | Ruta | Quién | Códigos |
|---|---|---|---|---|
| Abierto | GET | `/health/live` | Cualquiera | 200 |
| Abierto | GET | `/health/ready` | Cualquiera | 200, 503 |
| Abierto | POST | `/auth/registro` | Cualquiera | 201, 409, 422 |
| Abierto | POST | `/auth/login` | Cualquiera | 200, 401, 422, 429 |
| Abierto | POST | `/auth/logout` | Cualquiera | 200 |
| Abierto | GET | `/auth/yo` | Autenticado | 200, 401 |
| Abierto | POST | `/auth/cambiar-password` | Autenticado | 200, 401, 422 |
| Protegido | POST | `/usuarios` (alta de personal, con contraseña provisoria) | ADMIN | 201, 409, 422 |
| Protegido | GET | `/usuarios/{id}/roles` | ADMIN | 200, 404 |
| Protegido | POST | `/usuarios/{id}/roles` | ADMIN | 201, 404, 409, 422 |
| Protegido | DELETE | `/usuarios/{id}/roles/{rol}` | ADMIN | 200, 404, 409 |
| Protegido | GET | `/eventos` (`page`, `size`) | ADMIN | 200, 422 |
| Protegido | POST | `/clientes` | RECEPCION, ADMIN | 201, 409, 422 |
| Protegido | GET | `/clientes/{id}` (con sus vehículos) | RECEPCION, ADMIN | 200, 404 |
| Protegido | POST | `/clientes/{id}/vehiculos` | RECEPCION, ADMIN | 201, 404, 409, 422 |
| Protegido | DELETE | `/vehiculos/{id}` | RECEPCION, ADMIN | 204, 404, 409 |
| Protegido | GET | `/mis-vehiculos` | Autenticado | 200 |
| Protegido | GET | `/repuestos` (`q`, `page`, `size`) | ADMIN, RECEPCION, MECANICO | 200, 422 |
| Protegido | GET | `/repuestos/{id}` | ADMIN, RECEPCION, MECANICO | 200, 404 |
| Protegido | POST | `/repuestos` (con `stock_inicial`) | ADMIN | 201, 409, 422 |
| Protegido | PATCH | `/repuestos/{id}` (descripción y precio) | ADMIN | 200, 404, 422 |
| Protegido | DELETE | `/repuestos/{id}` | ADMIN | 204, 404 |
| Protegido | POST | `/repuestos/{id}/reponer` | ADMIN | 200, 404, 422 |
| Protegido | GET | `/repuestos/{id}/movimientos` | ADMIN | 200, 404 |
| Protegido | GET | `/repuestos/{id}/precios` (historial de precios) | ADMIN | 200, 404 |
| Protegido | POST | `/ordenes` | RECEPCION, ADMIN | 201, 409, 422 |
| Protegido | GET | `/ordenes` (`estado`, `page`, `size`) | ADMIN, RECEPCION, MECANICO | 200, 422 |
| Protegido | GET | `/ordenes/{id}` | El personal, o el dueño del vehículo | 200, 403, 404 |
| Protegido | POST | `/ordenes/{id}/iniciar` | MECANICO | 200, 404, 409 |
| Protegido | POST | `/ordenes/{id}/terminar` | El mecánico asignado, o ADMIN | 200, 403, 404, 409 |
| Protegido | POST | `/ordenes/{id}/cancelar` | RECEPCION, ADMIN o el dueño | 200, 403, 404, 409 |
| Protegido | GET | `/estados-orden` (el catálogo, por posición) | Autenticado | 200 |
| Protegido | GET | `/mis-ordenes` (`page`, `size`) | Autenticado | 200, 422 |

> **Regla transversal**: toda ruta del grupo protegido responde además **401** sin sesión y **403** con el cambio de contraseña pendiente.

## Rutas abiertas (sin autenticación)

| Ruta | Por qué es abierta |
|---|---|
| `GET /health/live` | Liveness: no toca la base; debe contestar aunque la base esté caída |
| `GET /health/ready` | Readiness: ejecuta `SELECT 1`; 503 si la base no contesta |
| `POST /auth/registro` | Auto-registro de clientes (RN-02) |
| `POST /auth/login` | Emite la cookie |
| `POST /auth/logout` | Borra la cookie; idempotente, responde 200 igual |
| `GET /auth/yo` | Abierta en el **grupo**, pero exige cookie válida (401 si no) |
| `POST /auth/cambiar-password` | Abierta en el **grupo** porque es la única salida cuando el cambio es obligatorio (RN-06) |

"Abierto" describe el **grupo de rutas**, no la ausencia de autenticación: `/auth/yo` y `/auth/cambiar-password` verifican la cookie igual, pero **no** llevan el control de contraseña pendiente — si lo llevaran, un usuario obligado a cambiarla no podría cambiarla nunca.

## `401` vs `403` — distinción obligatoria

| Situación | Código | Quién lo emite |
|---|---|---|
| No hay cookie `access_token` | **401** | `get_usuario_actual` |
| Token inválido, mal firmado, vencido o con `exp` pasado | **401** | `get_usuario_actual` |
| El usuario del `sub` no existe o está `activo = false` | **401** | `get_usuario_actual` |
| El token es anterior al último cambio de contraseña (RN-07) | **401** | `get_usuario_actual` |
| Hay sesión válida, pero el rol vigente no alcanza | **403** | `requiere_rol` |
| Hay sesión válida y el recurso es ajeno (RN-17) | **403** | servicio (comprobación de dueño) |
| Hay sesión válida con cambio de contraseña pendiente, en ruta protegida (RN-06) | **403** | control del grupo protegido |
| El rol se revocó con la sesión abierta | **403** en la petición siguiente | `requiere_rol` (consulta la base, no el token) |

**401 = "no sé quién sos".** **403 = "sé quién sos y no podés".** Nunca se usa 403 para un token ausente ni 401 para un permiso faltante.

Consecuencia de diseño: `C-06` exige que el cliente vea su orden (200) y no la ajena (**403**), y `C-07` exige que revocar un rol corte el acceso **con la misma cookie** en la petición siguiente — lo que demuestra que `requiere_rol` consulta `asignacion_rol` en cada petición y no confía en los roles del token.

## Autorización de `GET /ordenes/{id}` y `POST /ordenes/{id}/cancelar`

Estas dos rutas **no** usan `requiere_rol`: el dueño del vehículo no tiene un rol de personal, y si la ruta exigiera RECEPCION o ADMIN recibiría "no tenés permiso" cuando sí lo tiene. La decisión es del **servicio**:

1. Primero **quién es y qué relación tiene con la orden** → `403` si no es personal ni dueño.
2. Recién después **si el estado lo permite** → `409` si no.

De ahí la regla RN-12: **403 antes que 409**. `C-13` la verifica con una orden ajena (403) y una orden terminada (409).

Queda abierto qué roles cuentan exactamente como "el personal" en `GET /ordenes/{id}` → ver `10_preguntas_abiertas.md` (P1).
