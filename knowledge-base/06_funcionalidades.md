# Funcionalidades

Organizadas por **épica** (una por ejercicio de la consigna, más una épica transversal de datos y entrega). Cada historia `US-NNN` declara sus criterios de aceptación y las reglas que implementa. El peso es el de la grilla de corrección y **suma 100 %**.

## Mapa de épicas → ejercicios

| Épica | Ejercicio | Peso | Historias |
|---|---|---|---|
| E0 — Fundaciones y ciclo de vida | Ej. 1 | **8 %** | US-001 … US-004 |
| E1 — Modelo, restricciones y migraciones | Ej. 2 | **14 %** | US-005 … US-009 |
| E2 — Contratos y CRUD | Ej. 3 | **10 %** | US-010 … US-014 |
| E3 — Autenticación | Ej. 4 | **16 %** | US-015 … US-019 |
| E4 — Autorización | Ej. 5 | **14 %** | US-020 … US-025 |
| E5 — Repositorios y Unit of Work | Ej. 6 | **20 %** | US-026 … US-032 |
| E6 — Integridad | Ej. 7 | **10 %** | US-033 … US-034 |
| E7 — Lecturas sin N+1 y asincronía | Ej. 8 | **8 %** | US-035 … US-036 |
| E8 — Datos iniciales y entrega | transversal (condición de corrección) | — | US-037 … US-039 |

---

## Épica 0 — Fundaciones y ciclo de vida (Ej. 1 · 8 %)

### US-001 — Configuración sin secretos por defecto
**Como** desarrollador **quiero** una clase `Settings` con pydantic-settings que lea el entorno **para** que el proyecto no arranque con credenciales inventadas.

**Criterios de aceptación**
- [ ] `app/core/config.py` define `Settings` con `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`.
- [ ] La URL se arma con un `@computed_field` y driver asincrónico (`postgresql+asyncpg` o `postgresql+psycopg`).
- [ ] La clave de firma y la contraseña de la base **no tienen valor por defecto**: si faltan, la aplicación **no arranca**.
- [ ] Declara además: algoritmo JWT, duración del token, costo bcrypt, tamaño del pool, `SQL_ECHO` y `secure` de la cookie.
- [ ] Se lee de `.env` (no versionado) o del entorno; `env.example` tiene todas las variables y **ningún** secreto.

**Reglas**: RN-18 · **Ejercicio**: 1

### US-002 — Motor y fábrica en el lifespan
**Como** desarrollador **quiero** crear el motor y el `sessionmaker` en el lifespan **para** que nazcan dentro del bucle de eventos.

**Criterios de aceptación**
- [ ] El motor se crea **en el lifespan** con el tamaño de pool de la configuración y se guarda en `app.state`.
- [ ] La fábrica de sesiones también se guarda en `app.state`.
- [ ] **Nada** se construye al importar un módulo.
- [ ] El lifespan calcula **una vez** el hash ficticio del login.
- [ ] Al apagar, cierra el motor con `dispose()`.

**Ejercicio**: 1

### US-003 — Sesión por petición
**Como** desarrollador **quiero** un `get_session` que entregue una sesión por petición **para** aislar transacciones.

**Criterios de aceptación**
- [ ] Toma la fábrica de `app.state`.
- [ ] Crea la sesión con `expire_on_commit=False`.
- [ ] La cierra al terminar la petición.
- [ ] No hace `commit`: eso es del UoW.

**Ejercicio**: 1, 6

### US-004 — Salud live y ready
**Como** operador **quiero** dos chequeos distintos **para** distinguir "el proceso vive" de "la base contesta".

**Criterios de aceptación**
- [ ] `GET /health/live` → **200** sin tocar la base.
- [ ] `GET /health/ready` → ejecuta `SELECT 1`; **200** si contesta, **503** si no.
- [ ] Reiniciar el proceso no se propone como solución a una base caída.

**Ejercicio**: 1

---

## Épica 1 — Modelo, restricciones y migraciones (Ej. 2 · 14 %)

### US-005 — Modelos con todas las restricciones
**Como** desarrollador **quiero** las 13 tablas con sus columnas, `CHECK`, `UNIQUE` y `FK` **para** que la base garantice lo que puede garantizar.

**Criterios de aceptación**
- [ ] Nombres de tablas y columnas **literales** de `04_modelo_de_datos.md`; se pueden agregar columnas, no quitar ni renombrar.
- [ ] Dinero en `NUMERIC`/`Decimal`; fechas en `timestamptz`.
- [ ] `CHECK`: `anio BETWEEN 1950 AND 2100`, `precio > 0`, `stock >= 0`, `total >= 0`, `cantidad > 0`, `precio_unitario > 0`, `precio_nuevo > 0`, `precio_nuevo > precio_anterior`, `rol IN (...)`.
- [ ] `UNIQUE`: `usuario.email`, `cliente.documento`, `cliente.usuario_id`, `estado_orden.posicion`, `(item_orden.orden_id, repuesto_id)`.
- [ ] `orden_trabajo.estado`, `historial_estado_orden.desde_estado` y `hasta_estado` son **FK a `estado_orden.codigo`**, no un `CHECK` con la lista.
- [ ] Toda FK tiene índice propio.

**Reglas**: RN-01, RN-10, RN-15, RN-19 · **Ejercicio**: 2

### US-006 — Tres índices únicos parciales
**Como** desarrollador **quiero** índices únicos parciales con `postgresql_where` **para** que la unicidad rija sólo entre los vigentes.

**Criterios de aceptación**
- [ ] `asignacion_rol (usuario_id, rol) WHERE revocada_en IS NULL`.
- [ ] `vehiculo (patente) WHERE borrado_en IS NULL`.
- [ ] `repuesto (codigo) WHERE borrado_en IS NULL`.
- [ ] Los tres declarados en SQLModel con `postgresql_where` y presentes en la migración.
- [ ] Dar de baja un vehículo permite reusar la patente (`C-19`).

**Reglas**: RN-01, RN-03, RN-16 · **Ejercicio**: 2

### US-007 — Catálogo y navegación bidireccional
**Como** desarrollador **quiero** el catálogo `estado_orden` y relaciones navegables **para** leer sin joins manuales ni listas inesperadas.

**Criterios de aceptación**
- [ ] `estado_orden` tiene PK textual `codigo`, `descripcion`, `posicion UNIQUE`, `es_final`.
- [ ] La migración crea la tabla **vacía**; las filas las carga `seed.py`.
- [ ] Navegación declarada en los dos extremos de cada relación que se lee.
- [ ] `Usuario.cliente` devuelve **un objeto** (o `None`), no una lista.
- [ ] `orden_trabajo` ↔ `item_orden` modela la composición.

**Reglas**: RN-19 · **Ejercicio**: 2

### US-008 — Migración `autogenerate` + migración manual
**Como** desarrollador **quiero** dos migraciones **para** versionar tablas y trigger por separado.

**Criterios de aceptación**
- [ ] Plantilla asincrónica de Alembic; **nada** de `create_all`.
- [ ] Migración 1: generada con `autogenerate`, con todas las tablas, índices y restricciones.
- [ ] Migración 2: **escrita a mano**, con la función y el trigger de sólo agregado sobre las tres tablas.
- [ ] Cada migración se leyó antes de aplicarla y lleva un comentario que lo diga.

**Reglas**: RN-15 · **Ejercicio**: 2, 7

### US-009 — Reversibilidad del esquema
**Como** corrector **quiero** poder ir y volver **para** comprobar que el esquema está completo.

**Criterios de aceptación**
- [ ] `alembic upgrade head` sobre base **vacía** funciona.
- [ ] `alembic downgrade base` funciona (incluye borrar el trigger y la función).
- [ ] Otro `upgrade head` funciona.
- [ ] Sin credenciales en `alembic.ini` ni en el repo.

**Ejercicio**: 2

---

## Épica 2 — Contratos y CRUD (Ej. 3 · 10 %)

### US-010 — Contratos separados de los modelos
**Como** desarrollador **quiero** schemas de entrada y salida independientes **para** no filtrar columnas ni aceptar campos ajenos.

**Criterios de aceptación**
- [ ] Ningún schema de entrada acepta campos no declarados (`extra="forbid"`).
- [ ] **Ninguna** respuesta incluye `password_hash`.
- [ ] Los `PATCH` aplican sólo lo enviado (`exclude_unset=True`).
- [ ] El alta de orden **no** acepta `precio`, `total`, `estado` ni `creada_en`.
- [ ] El alta de repuesto acepta `stock_inicial` (no `stock`).
- [ ] Contraseñas: máx. **72 bytes**; mín. 8 caracteres (default aceptado).

**Reglas**: RN-10, RN-14, RN-18 · **Ejercicio**: 3

### US-011 — CRUD de repuestos
**Como** ADMIN **quiero** administrar el catálogo **para** mantener precios y stock correctos.

**Criterios de aceptación**
- [ ] `POST /repuestos` (con `stock_inicial`) → **201**, y genera un movimiento `"Stock inicial"`.
- [ ] `GET /repuestos?q=&page=&size=` → **200** paginado; búsqueda por descripción con **parámetros ligados**.
- [ ] `GET /repuestos/{id}` → **200** / **404**.
- [ ] `PATCH /repuestos/{id}` (descripción y precio) → **200** / **404** / **422**; el stock no es aceptado.
- [ ] `DELETE /repuestos/{id}` → **204** (baja lógica) / **404**.
- [ ] `POST /repuestos/{id}/reponer` → **200**, movimiento `"Reposición"`.
- [ ] `GET /repuestos/{id}/movimientos` y `/precios` → **200** / **404**.

**Reglas**: RN-01, RN-14, RN-16, RN-20 · **Ejercicio**: 3

### US-012 — Clientes y vehículos
**Como** RECEPCION **quiero** dar de alta clientes y vehículos **para** abrir después la orden.

**Criterios de aceptación**
- [ ] `POST /clientes` → **201** / **409** (documento repetido) / **422**.
- [ ] `GET /clientes/{id}` devuelve el cliente **con sus vehículos** → **200** / **404**.
- [ ] `POST /clientes/{id}/vehiculos` → **201** / **404** / **409** (patente vigente repetida) / **422**.
- [ ] `DELETE /vehiculos/{id}` → **204** / **404** / **409** (tiene órdenes abiertas).
- [ ] `GET /mis-vehiculos` → **200** con los vehículos del cliente autenticado.

**Reglas**: RN-01, RN-16, RN-17 · **Ejercicio**: 3

### US-013 — Paginación uniforme
**Como** consumidor **quiero** el mismo envoltorio en todos los listados **para** paginar sin casos especiales.

**Criterios de aceptación**
- [ ] Todo listado devuelve `{items, total, page, size, pages}`.
- [ ] `page >= 1`; `size` de **1 a 100**, default 20.
- [ ] Página más allá de la última → **422** con mensaje propio ("La página 3 no existe: hay 2").
- [ ] `total` cuenta con los **mismos filtros** que la página.
- [ ] Con cero resultados hay **una** página vacía (`total 0`, `pages` 0 o 1 — ver `10_preguntas_abiertas.md`).
- [ ] `size=500` → **422** (`C-16`).

**Ejercicio**: 3

### US-014 — Códigos y errores traducidos
**Como** consumidor **quiero** códigos predecibles y mensajes propios **para** no recibir el esquema de la base.

**Criterios de aceptación**
- [ ] `201` crear, `204` baja, `404` ruta inexistente, `409` choque, `422` contrato, `401` sin sesión, `403` sin permiso.
- [ ] `IntegrityError` traducido a **409** con mensaje propio.
- [ ] Ninguna entrada inválida produce **500** (incluido un `{id}` no entero → 422, `C-01`).
- [ ] Ningún mensaje contiene texto de PostgreSQL ni traza.

**Reglas**: RN-18 · **Ejercicio**: 3

---

## Épica 3 — Autenticación (Ej. 4 · 16 %)

### US-015 — bcrypt fuera del bucle y con semáforo
**Como** desarrollador **quiero** hashear en `to_thread` bajo un semáforo **para** no frenar el servidor.

**Criterios de aceptación**
- [ ] Toda llamada a bcrypt corre en `to_thread`.
- [ ] Un semáforo limita cuántas corren a la vez.
- [ ] El costo sale de `Settings` (default aceptado: **12**), no está fijo en el código.
- [ ] El hash se calcula **antes** de abrir la transacción (adentro la conexión quedaría tomada ~300 ms sin usar la base).
- [ ] El lifespan calcula una vez el hash ficticio.

**Reglas**: RN-09 · **Ejercicio**: 4

### US-016 — Login con el orden correcto
**Como** usuario **quiero** iniciar sesión **para** obtener una cookie válida.

**Criterios de aceptación**
- [ ] Orden: **(1)** límite de intentos (RN-08) → **(2)** hash ficticio si el correo no existe o verificación real → **(3)** emisión del token.
- [ ] Si se superó el límite, **429 + `Retry-After`** en pocos milisegundos, **sin calcular ningún hash**.
- [ ] Correo inexistente y contraseña mala: **mismo cuerpo**, **mismo 401**, tiempo parecido.
- [ ] Cada intento (éxito o fallo) se anota en `intento_acceso` en **sesión y transacción propias**.
- [ ] Un login correcto reinicia el conteo.
- [ ] Respuesta: `{mensaje, debe_cambiar_password, expira_en_segundos}` — **sin token**.

**Reglas**: RN-08, RN-09 · **Ejercicio**: 4, 7

### US-017 — Token en cookie `HttpOnly`
**Como** usuario **quiero** que el token no esté accesible desde JavaScript **para** reducir el riesgo de robo.

**Criterios de aceptación**
- [ ] JWT con `sub`, `iat`, `exp` y roles vigentes al emitir.
- [ ] Viaja **sólo** en cookie `access_token`: `HttpOnly`, `SameSite=Lax`, `Max-Age` = duración, `Secure` configurable.
- [ ] El cuerpo del login **no** trae el token.
- [ ] La dependencia lee `request.cookies`; **nunca** `Authorization` ni el cuerpo.
- [ ] `Authorization: Bearer` → **401** (`C-03`).

**Ejercicio**: 4

### US-018 — Auto-registro
**Como** cliente **quiero** registrarme solo **para** consultar mis vehículos y órdenes.

**Criterios de aceptación**
- [ ] Crea `usuario` + `asignacion_rol` CLIENTE + `cliente` en **un solo UoW**.
- [ ] Si falla cualquiera, **no queda ninguna** fila (`C-02`).
- [ ] Documento ya existente → **409** y **no se apropia de la ficha**.
- [ ] Email repetido → **409**.
- [ ] **201**; el cuerpo no incluye `password_hash`.
- [ ] No se acepta `rol` en el cuerpo → **422**.

**Reglas**: RN-02 · **Ejercicio**: 4, 6

### US-019 — Logout, `/auth/yo` y cambio de contraseña
**Como** usuario **quiero** cerrar sesión, ver mi identidad y cambiar mi contraseña.

**Criterios de aceptación**
- [ ] `POST /auth/logout` borra la cookie → **200** (idempotente).
- [ ] `GET /auth/yo` → usuario, **roles vigentes** y **roles del token**, para ver la diferencia (`C-07`).
- [ ] `POST /auth/cambiar-password` → **200**, emite **cookie nueva**, escribe `password_cambiada_en` y **desmarca** `debe_cambiar_password`.
- [ ] La cookie anterior da **401** en la petición siguiente, **sin esperar** (`C-09`).
- [ ] Contraseña de más de 72 bytes → **422**, no 500.

**Reglas**: RN-06, RN-07 · **Ejercicio**: 4, 5

---

## Épica 4 — Autorización (Ej. 5 · 14 %)

### US-020 — `get_usuario_actual` responde 401
**Como** sistema **quiero** rechazar sesiones inválidas **para** no confundir identidad con permiso.

**Criterios de aceptación**
- [ ] Sin cookie → **401**.
- [ ] Token inválido, mal firmado o vencido → **401**.
- [ ] Usuario inexistente o `activo = false` → **401**.
- [ ] `iat` anterior a `password_cambiada_en` → **401**.
- [ ] Comparación de `iat` **sin truncar** a segundos.

**Reglas**: RN-07 · **Ejercicio**: 5

### US-021 — `requiere_rol` responde 403
**Como** ADMIN **quiero** acotar cada ruta a roles concretos **para** que nadie haga más de lo suyo.

**Criterios de aceptación**
- [ ] Consulta `asignacion_rol` **en cada petición**; vigente = no revocada y no vencida.
- [ ] Revocar un rol corta el acceso **en la petición siguiente**, con la misma cookie (`C-07`).
- [ ] Sin rol → **403** (con sesión válida).
- [ ] Los roles del token **no** habilitan nada.

**Reglas**: RN-04 · **Ejercicio**: 5

### US-022 — Alta de personal y gestión de roles
**Como** ADMIN **quiero** dar de alta personal y asignar/revocar roles con vigencia.

**Criterios de aceptación**
- [ ] `POST /usuarios` (con contraseña provisoria) → **201** / **409** / **422**.
- [ ] `GET /usuarios/{id}/roles` → **200** / **404**.
- [ ] `POST /usuarios/{id}/roles` → **201** / **404** / **409** (ya abierto) / **422**.
- [ ] `vence_en` con zona horaria y en el futuro; sin zona o en el pasado → **422**.
- [ ] `DELETE /usuarios/{id}/roles/{rol}` → **200**; escribe `revocada_en`, **no borra la fila**.
- [ ] Reasignar un rol vencido cierra la fila anterior y abre una nueva.

**Reglas**: RN-03, RN-05 · **Ejercicio**: 5

### US-023 — Autoprotección del administrador
**Como** sistema **quiero** que nunca falten administradores **para** no dejar el taller sin gobierno.

**Criterios de aceptación**
- [ ] Un admin **no** puede revocarse su propio ADMIN → **409** (`C-08`).
- [ ] Si la revocación dejaría **cero** admins vigentes → **409**.
- [ ] La comprobación es en el servicio y ocurre **antes** de escribir.

**Reglas**: RN-05 · **Ejercicio**: 5

### US-024 — Dos grupos de rutas
**Como** sistema **quiero** bloquear todo con contraseña pendiente **para** forzar el cambio.

**Criterios de aceptación**
- [ ] Grupo abierto (`/health`, `/auth`) y grupo protegido (el resto).
- [ ] El control se monta **una sola vez** en el grupo protegido.
- [ ] Con `debe_cambiar_password = true`: **403** en toda ruta protegida (`C-09`).
- [ ] `/auth/cambiar-password` sigue accesible.

**Reglas**: RN-06 · **Ejercicio**: 5

### US-025 — Lo propio y el historial de seguridad
**Como** CLIENTE **quiero** ver sólo lo mío; **como** ADMIN **quiero** auditar.

**Criterios de aceptación**
- [ ] `/mis-vehiculos`, `/mis-ordenes` sólo piden autenticación.
- [ ] `GET /ordenes/{id}`: el personal o el dueño; ajeno → **403**.
- [ ] `GET /eventos` (paginado, ADMIN) → **200** / **422**.
- [ ] Se registran altas, cambios de rol y de contraseña; el seed deja `actor = 'SISTEMA'`.
- [ ] `SISTEMA` es texto, no un usuario.

**Reglas**: RN-17 · **Ejercicio**: 5

---

## Épica 5 — Repositorios y Unit of Work (Ej. 6 · 20 %)

### US-026 — `BaseRepository[T]`
**Como** desarrollador **quiero** un repositorio genérico **para** no repetir consultas.

**Criterios de aceptación**
- [ ] Recibe en el constructor **la sesión y la clase del modelo** (los genéricos se borran en runtime).
- [ ] Expone al menos `get_by_id`, `get_all`, `count`, `add`, `update`, `delete`.
- [ ] `add`/`update` hacen **`flush()`**, nunca `commit()`.
- [ ] Cada entidad tiene su repositorio con métodos nombrados por lo que traen.

**Ejercicio**: 6

### US-027 — `SoftDeleteRepository[T]`
**Como** desarrollador **quiero** una variante con baja lógica **para** conservar históricos.

**Criterios de aceptación**
- [ ] Hereda de `BaseRepository`.
- [ ] Filtra los dados de baja en las lecturas normales.
- [ ] Agrega `get_by_id_including_deleted` y `soft_delete`, que **no existen** en la base.
- [ ] Se usa en `vehiculo` y `repuesto`, no en el resto.

**Reglas**: RN-16 · **Ejercicio**: 6

### US-028 — `UnitOfWork` base
**Como** desarrollador **quiero** un gestor de contexto asincrónico **para** que un fallo no deje datos a medias.

**Criterios de aceptación**
- [ ] `async with` confirma al salir sin excepción.
- [ ] Revierte si se sale con excepción.
- [ ] **No cierra la sesión** (no la creó).
- [ ] No construye la sesión: la recibe.

**Ejercicio**: 6

### US-029 — UoW por módulo y cableado correcto
**Como** desarrollador **quiero** que cada módulo componga sus repositorios **para** operar con una sola sesión.

**Criterios de aceptación**
- [ ] Cada módulo tiene su UoW con los repositorios que sus operaciones necesitan, **todos con la misma sesión**.
- [ ] El **router** construye el UoW con una dependencia y se lo pasa al servicio **sin abrirlo**.
- [ ] El **servicio** lo abre con `async with` y **nunca** lo construye.
- [ ] La sesión la cierra `get_session`, no el UoW.

**Ejercicio**: 6

### US-030 — Repositorio de catálogo y punto único de stock
**Como** desarrollador **quiero** repositorios acotados **para** no ofrecer escrituras que no corresponden.

**Criterios de aceptación**
- [ ] `EstadoOrden` tiene repositorio **propio de sólo lectura** que **no hereda** de `BaseRepository`.
- [ ] Expone sólo lo necesario para listar por `posicion` y buscar por código.
- [ ] El stock se escribe en **un solo punto**, usado por reposición y terminación (RN-14).

**Reglas**: RN-14, RN-19 · **Ejercicio**: 6

### US-031 — Operaciones de varias escrituras
**Como** negocio **quiero** que registro, terminación y cambio de precio sean atómicos.

**Criterios de aceptación**
- [ ] RN-02: 3 filas o ninguna.
- [ ] RN-13: N movimientos + 1 línea de historial + stock + estado, o nada.
- [ ] RN-20: precio + historial de precio en la misma transacción.
- [ ] Cada una se escribe en **un solo bloque** `async with uow`, sin commits intermedios.

**Reglas**: RN-02, RN-13, RN-20 · **Ejercicio**: 6

### US-032 — Órdenes: alta y transiciones
**Como** RECEPCION/MECANICO/ADMIN **quiero** crear, iniciar, terminar y cancelar órdenes.

**Criterios de aceptación**
- [ ] `POST /ordenes` → **201** con precios copiados, total calculado y 1.ª línea de historial; repuesto inexistente → **409** y **sin** orden (`C-10`).
- [ ] `POST /ordenes/{id}/iniciar` → **200**, sólo `PENDIENTE`, asigna `mecanico_id`; otro estado → **409**.
- [ ] `POST /ordenes/{id}/terminar` → **200**; stock insuficiente → **409** sin escrituras (`C-11`); otro mecánico → **403**.
- [ ] `POST /ordenes/{id}/cancelar` → **200**; ajeno → **403** antes que **409** (`C-13`).
- [ ] `GET /ordenes?estado=&page=&size=` → **200**; estado fuera del enum → **422**.
- [ ] `GET /estados-orden` → **200** por `posicion`; `GET /mis-ordenes` → **200**.

**Reglas**: RN-10, RN-11, RN-12, RN-13, RN-19 · **Ejercicio**: 6

---

## Épica 6 — Integridad (Ej. 7 · 10 %)

### US-033 — Sólo agregado por disparador
**Como** auditor **quiero** que los historiales no se puedan corregir **para** confiar en ellos.

**Criterios de aceptación**
- [ ] Trigger instalado por la **segunda migración**, sobre las tres tablas.
- [ ] Rechaza **UPDATE** y **DELETE** venga de donde venga.
- [ ] `downgrade` elimina función y trigger.
- [ ] `test/solo_agregado.sql` demuestra los **6 rechazos** (`C-14`).

**Reglas**: RN-15 · **Ejercicio**: 7

### US-034 — `intento_acceso` en transacción propia
**Como** sistema **quiero** contar el fallo aunque la petición se revierta.

**Criterios de aceptación**
- [ ] Cada intento (éxito o fallo) se anota en **sesión y transacción propias**, que se confirman **siempre**.
- [ ] Es la **única** escritura que no comparte la transacción de su petición.
- [ ] Un comentario en el código lo declara, junto con su costo (deja filas aunque la petición falle).
- [ ] Los 5 fallos de `C-05` quedan registrados pese a los 401.

**Reglas**: RN-08 · **Ejercicio**: 7

---

## Épica 7 — Lecturas sin N+1 y asincronía (Ej. 8 · 8 %)

### US-035 — Precarga declarada en el repositorio
**Como** desarrollador **quiero** que la precarga viva en el repositorio **para** que el servicio no arme consultas.

**Criterios de aceptación**
- [ ] Toda respuesta con datos de una relación los obtiene con **carga anticipada** (`selectinload`/`joinedload`).
- [ ] La precarga se declara **adentro del método** que la necesita, en el repositorio.
- [ ] Ninguna lectura depende de carga perezosa.
- [ ] El detalle de una orden trae vehículo, cliente, ítems, repuesto de cada ítem e historial con un **número fijo** de consultas (`C-15`: 2 y 4 ítems → mismas consultas).

**Ejercicio**: 8

### US-036 — Todo async, aviso en segundo plano
**Como** cliente **quiero** que terminar una orden me avise **sin** demorar la respuesta.

**Criterios de aceptación**
- [ ] Todos los handlers son `async def`; ninguna llamada bloqueante.
- [ ] Al terminar una orden se agenda `BackgroundTasks`: `await asyncio.sleep(0.5)` + mensaje en el log.
- [ ] Corre **después** de enviar la respuesta.
- [ ] Sólo se agenda si la transacción **se confirmó** (`C-12`).

**Ejercicio**: 8

---

## Épica 8 — Datos iniciales y entrega (transversal)

> Sin peso propio, pero es **condición de corrección**: si el proyecto no levanta, no migra o tiene credenciales, no se corrige.

### US-037 — `seed.py` reproducible
**Como** equipo **quiero** un estado inicial conocido **para** que los 19 casos sean deterministas.

**Criterios de aceptación**
- [ ] Vacía con `DELETE` en **orden inverso de FK** (no `TRUNCATE`: no dispara el trigger de fila).
- [ ] Carga primero el catálogo (4 estados), después el resto.
- [ ] 7 usuarios, 2 clientes (Laura con usuario y 2 vehículos; Jorge sin usuario y 1 vehículo), 4 repuestos con stock inicial como movimiento.
- [ ] Órdenes 1 (`PENDIENTE`) y 2 (`EN_REPARACION`, 4 bujías con stock 2).
- [ ] Historial de precio del filtro 8000 → 8500 y evento `SISTEMA`.
- [ ] Se puede correr N veces y siempre deja el mismo estado.

**Ejercicio**: transversal

### US-038 — Los 19 casos de prueba
**Como** corrector **quiero** evidencia ejecutable **para** verificar cada regla.

**Criterios de aceptación**
- [ ] `test/*.http` con `C-01` a `C-19`, cada uno con la **respuesta esperada comentada**.
- [ ] `test/solo_agregado.sql` para `C-14`.
- [ ] Cada archivo se ejecuta después de `python seed.py`.
- [ ] Las sesiones simultáneas usan `# @name`, `# @no-cookie-jar` y `Cookie: {{login.response.headers.Set-Cookie}}`.

**Ejercicio**: transversal

### US-039 — Entregables y evidencias
**Como** alumno **quiero** entregar todo lo pedido **para** que el TP se corrija.

**Criterios de aceptación**
- [ ] `README.md` con los pasos desde cero: venv, dependencias, `.env` (y **cómo generar la clave de firma**), `alembic upgrade head`, `python seed.py`, arranque.
- [ ] `requirements.txt`, `env.example`, `alembic.ini`, `migrations/`, `test/`.
- [ ] `.env` **no** versionado; ninguna credencial real en el repo.
- [ ] Evidencia `C-15`: consola con las consultas del detalle con 2 y con 4 ítems.
- [ ] Evidencia `C-14`: captura de psql con los 6 rechazos + el de la clave foránea.

**Ejercicio**: transversal

---

## Casos de prueba `C-01` … `C-19` (criterio de aceptación global)

Tabla literal de la consigna (págs. 20-21). Cada caso es el criterio de aceptación de integración: si no pasa, la épica correspondiente no está terminada.

| Caso | Qué se demuestra | Resultado esperado | Historias |
|---|---|---|---|
| **C-01** | Un parámetro de ruta que no es entero, con la sesión iniciada | **422**, sin ejecutar el handler | US-014 |
| **C-02** | Registro; correo y documento repetidos | **201**; **409** con mensaje propio, y el registro rechazado **no deja ninguna fila suelta** | US-018, US-031 |
| **C-03** | La cookie del login | `Set-Cookie` con `HttpOnly`, `SameSite=Lax` y `Max-Age`; el cuerpo **sin token**; sin cookie o con `Authorization: Bearer`, **401** | US-017 |
| **C-04** | Correo existente con contraseña mala, y correo inexistente | **401** con el **mismo cuerpo** y un tiempo parecido | US-016 |
| **C-05** | Seis intentos fallidos seguidos | El **sexto**, **429** con `Retry-After` y en pocos milisegundos; los cinco fallos están en `intento_acceso` | US-016, US-034 |
| **C-06** | 401 contra 403, y lo propio | Sin rol, **403**; el cliente ve su orden (**200**) y no la ajena (**403**) | US-021, US-025 |
| **C-07** | Revocar un rol con la sesión abierta; vencimientos inválidos | La misma cookie, **403** en la petición siguiente; `/auth/yo` muestra la diferencia; la fila revocada sigue. Vencimiento en el pasado o sin zona, **422** | US-019, US-021, US-022 |
| **C-08** | Autoprotección | El administrador no se revoca su ADMIN: **409** | US-023 |
| **C-09** | Cambio obligatorio | Bloqueado (**403**) salvo `/auth`; después del cambio, la cookie nueva vale y la anterior da **401**, sin esperar entre el login y el cambio | US-019, US-024 |
| **C-10** | Alta de una orden con dos ítems | **201** con precios copiados, total e historial; con un repuesto inexistente, **409** y la orden **no** queda creada | US-032 |
| **C-11** | Terminar la orden 2, que pide más bujías que las que hay | **409**; estado, stock, movimientos e historial **exactamente como estaban** | US-032 |
| **C-12** | Reponer y terminar la orden 2 | **200**; baja el stock, aparecen los movimientos y la línea de historial; el aviso sale en el registro **después** de la respuesta | US-032, US-036 |
| **C-13** | Cancelar | El dueño cancela su orden pendiente (**200**); una orden ajena **403**; una terminada **409** | US-032 |
| **C-14** | `UPDATE` y `DELETE` sobre las tres tablas de sólo agregado en psql; una orden con un estado que no está en el catálogo | Los **seis**, rechazados por el disparador; el último, por la **clave foránea** | US-033 |
| **C-15** | Detalle de una orden con 2 y con 4 ítems | La **misma cantidad de consultas** en la consola | US-035 |
| **C-16** | Búsqueda con `' OR '1'='1`; paginación con filtro; PATCH parcial; PATCH del stock | Lista vacía con `total 0`; con `q=freno&size=1`, `total 1` y `pages 1`, y `page=2` da **422**; `size=500`, **422**; sólo cambia lo enviado; **422** | US-010, US-011, US-013, US-014 |
| **C-17** | Catálogo de estados; filtrar órdenes por un estado que el contrato no declara | Los cuatro por posición, con `TERMINADA` y `CANCELADA` finales; sin sesión, **401**; **422** | US-007, US-021, US-032 |
| **C-18** | Cambiar el precio de un repuesto y después sólo su descripción | Una línea nueva en `/repuestos/{id}/precios` con el precio anterior y el nuevo; el segundo PATCH **no agrega ninguna**; la recepción recibe **403** | US-011, US-020, US-031 |
| **C-19** | Dar de baja un vehículo sin órdenes y registrarlo con la misma patente para otro cliente | **204** y **201**: el índice único parcial sólo cuenta los vigentes; una segunda patente vigente igual, **409** | US-006, US-012 |

**Cobertura**: los 19 casos tocan las 8 épicas. Los casos `C-14`, `C-15`, `C-03`, `C-05`, `C-07` y `C-09` son los que la cátedra usa como evidencia de los detalles finos (trigger, consultas fijas, cookie, orden del login, roles por petición, `iat`): no se pueden improvisar el último día.

## Historias que no se pueden paralelizar

`US-001` → `US-005` → `US-010` son **prerrequisito** de casi todo lo demás: configuración, esquema y contratos. El paralelismo real del equipo de 4 personas empieza en la épica 3 (autenticación) y se abre del todo en las épicas 5-7. Ver `09_decisiones_y_supuestos.md` (`SU-04`) y `10_preguntas_abiertas.md`.
