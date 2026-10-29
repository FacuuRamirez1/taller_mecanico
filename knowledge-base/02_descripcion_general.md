# Descripción General

## Stack tecnológico

Versiones **mínimas** exigidas por la consigna. No hay frontend: el único artefacto es una API REST.

| Capa | Tecnología | Versión mínima | Uso |
|---|---|---|---|
| Lenguaje | **Python** | **3.12** | Runtime |
| Framework web | **FastAPI** | **0.111** | Framework HTTP; todos los handlers con `async def` |
| ORM / modelos | **SQLModel** | **0.0.24** | Modelos de tabla (`table=True`) y relaciones |
| ORM base | **SQLAlchemy** | **2.0 asincrónico** | Motor, sesión, `selectinload`, `postgresql_where` |
| Driver | **asyncpg** | **0.30** | Controlador asincrónico (se acepta `psycopg` 3 asincrónico) |
| Base de datos | **PostgreSQL** | **16** | Persistencia, garantías, disparadores, índices parciales |
| Migraciones | **Alembic** | **1.13**, plantilla asincrónica | `migrations/`, `alembic.ini` |
| Configuración | **pydantic-settings** | **2.0** | `Settings` desde entorno / `.env` |
| Hash de contraseñas | **bcrypt** | **4.0** | Costo declarado en configuración |
| Token | **PyJWT** | **2.8** | JWT firmado (`sub`, `iat`, `exp`, roles) |
| Servidor ASGI | **uvicorn** | el que instala `fastapi[standard]` | Arranque local |
| Cliente de pruebas | **REST Client** (extensión VS Code) | — | Archivos `test/*.http` (+ `test/solo_agregado.sql` en psql) |

**Versiones mínimas exactas, en una línea**: `Python 3.12` · `FastAPI 0.111` · `SQLModel 0.0.24` · `SQLAlchemy 2.0` async · `asyncpg 0.30` (o `psycopg` 3 async) · `PostgreSQL 16` · `Alembic 1.13` async · `pydantic-settings 2.0` · `bcrypt 4.0` · `PyJWT 2.8` · `uvicorn` (el que instala `fastapi[standard]`).

Dependencias transitivas relevantes: `greenlet` (lo necesita SQLAlchemy async), `python-dotenv` (lo usa pydantic-settings para leer `.env`). No se agrega ninguna dependencia de infraestructura: **no hay Docker, ni Redis, ni broker, ni CI**.

## Arquitectura general

Arquitectura en capas estricta, organizada **por módulo funcional** (no por capa técnica global). Cada módulo repite las mismas seis capas. La cadena de llamada es `Router → Service → UoW → Repository → Model`: el router valida el contrato y **construye** el UoW, el servicio aplica las reglas y lo **abre**, el UoW compone los repositorios y **confirma o revierte**, el repositorio hace `flush` y declara la precarga, y el modelo llega a PostgreSQL.

```
                    ┌──────────────────────────────────────────┐
   HTTP (cookie)    │  main.py                                 │
  ─────────────────►│   · lifespan: motor + sessionmaker       │
                    │   · app.state.engine / app.state.session │
                    │   · grupo ABIERTO (/auth, /health)       │
                    │   · grupo PROTEGIDO (control de cambio)  │
                    └───────────────┬──────────────────────────┘
                                    │
                    ┌───────────────▼──────────────────────────┐
                    │  Router  (app/modules/*/router.py)        │
                    │   · valida contrato (schemas)             │
                    │   · construye el UoW por dependencia      │
                    │   · llama al servicio; traduce errores    │
                    └───────────────┬──────────────────────────┘
                                    │ UoW (sin abrir)
                    ┌───────────────▼──────────────────────────┐
                    │  Service (app/modules/*/service.py)       │
                    │   · reglas de negocio (RN-01..RN-20)      │
                    │   · abre el UoW con `async with`          │
                    │   · decide 403 / 409 / 404                │
                    └───────────────┬──────────────────────────┘
                                    │ una sesión
                    ┌───────────────▼──────────────────────────┐
                    │  UnitOfWork (core + por módulo)           │
                    │   · compone repositorios con la MISMA     │
                    │     sesión                                │
                    │   · commit al salir OK / rollback si hay  │
                    │     excepción                             │
                    │   · NO cierra la sesión (no la creó)      │
                    └───────────────┬──────────────────────────┘
                                    │
                    ┌───────────────▼──────────────────────────┐
                    │  Repository (core + por módulo)           │
                    │   · BaseRepository[T] / SoftDeleteRepo[T] │
                    │   · add/update = flush(), nunca commit()  │
                    │   · precarga declarada acá (selectinload) │
                    └───────────────┬──────────────────────────┘
                                    │
                    ┌───────────────▼──────────────────────────┐
                    │  Model (SQLModel) → PostgreSQL 16        │
                    │   UNIQUE · FK · CHECK · índices parciales │
                    │   · trigger de sólo agregado              │
                    └──────────────────────────────────────────┘
```

**Decisiones de alto nivel (y por qué):**

- **El router construye el UoW y el servicio lo abre.** El router recibe el UoW ya construido por una dependencia; el servicio lo abre con `async with` y nunca lo instancia. Es el punto que más pesa en la corrección (Ej. 6, 20 %).
- **Una sesión por petición**, creada por `get_session` desde la fábrica guardada en `app.state`, con `expire_on_commit=False`, y cerrada al terminar la petición. El UoW no la cierra.
- **El motor y la fábrica se crean en el lifespan**, no al importar: un recurso creado al importar nace antes de que exista el bucle de eventos.
- **La base garantiza lo que puede garantizar**: unicidad (incluidos parciales), FK del estado al catálogo, `CHECK` de cantidades/precios/año y sólo agregado por disparador. El servicio **no** verifica unicidad con una consulta previa: intenta escribir y traduce el `IntegrityError`.
- **La autorización se resuelve en la base, por petición**, no con lo que dice el token (RN-04).
- **Todo async, sin bloqueos**: bcrypt va a `to_thread` bajo semáforo; ninguna lectura usa carga perezosa.

## Módulos funcionales

Cinco módulos mínimos. `health` es la excepción: sólo tiene `router.py`.

| Módulo | Entidades que contiene | Responsabilidad |
|---|---|---|
| `health` | — | `GET /health/live` (no toca la base) y `GET /health/ready` (`SELECT 1`, 503 si no contesta) |
| `usuarios` | `usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad` | Autenticación, alta de personal, roles con vigencia, historial de seguridad, límite de intentos |
| `clientes` | `cliente`, `vehiculo` | Fichas de cliente, vehículos, borrado lógico, rutas `/mis-*` |
| `repuestos` | `repuesto`, `movimiento_stock`, `historial_precio_repuesto` | Catálogo, stock por movimientos, reposición, historial de precios |
| `ordenes` | `orden_trabajo`, `item_orden`, `estado_orden`, `historial_estado_orden` | Alta con ítems, transiciones de estado, detalle sin N+1, catálogo de estados |

`EstadoOrden`, `ItemOrden` e `HistorialEstadoOrden` viven en `ordenes`; `Vehiculo` en `clientes`; `MovimientoStock` y `HistorialPrecioRepuesto` en `repuestos`; `AsignacionRol`, `IntentoAcceso` y `EventoSeguridad` en `usuarios`.

## Integraciones externas

**Ninguna.** No hay servicios de terceros, ni pagos, ni correo real, ni storage.

| Servicio | Propósito | Tipo |
|---|---|---|
| — | — | — |

El único efecto fuera de la petición es el **aviso al cliente al terminar una orden**, simulado con `BackgroundTasks` + `await asyncio.sleep(0.5)` y un mensaje en el log. Corre en el mismo proceso, después de enviar la respuesta y sólo si la transacción se confirmó. No hay cola, ni reintento, ni canal real (eso es capítulo 8, fuera de alcance).

## API REST

33 endpoints en **dos grupos de rutas** montados en `main.py`:

- **Grupo abierto**: `/health/*` y `/auth/*`. No lleva el control del cambio obligatorio de contraseña.
- **Grupo protegido**: todo el resto. Lleva montado **una sola vez** el control de cambio de contraseña pendiente (RN-06) y responde `401` sin sesión y `403` con cambio pendiente.

Los endpoints, con su rol y sus códigos, están en `03_actores_y_roles.md` (tabla literal de la consigna). Resumen por recurso:

| Recurso | Endpoints |
|---|---|
| Salud | `GET /health/live`, `GET /health/ready` |
| Autenticación | `POST /auth/registro`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/yo`, `POST /auth/cambiar-password` |
| Usuarios y roles | `POST /usuarios`, `GET /usuarios/{id}/roles`, `POST /usuarios/{id}/roles`, `DELETE /usuarios/{id}/roles/{rol}` |
| Seguridad | `GET /eventos` (paginado) |
| Clientes | `POST /clientes`, `GET /clientes/{id}` (con vehículos), `POST /clientes/{id}/vehiculos`, `DELETE /vehiculos/{id}`, `GET /mis-vehiculos` |
| Repuestos | `GET /repuestos` (`q`, `page`, `size`), `GET /repuestos/{id}`, `POST /repuestos`, `PATCH /repuestos/{id}`, `DELETE /repuestos/{id}`, `POST /repuestos/{id}/reponer`, `GET /repuestos/{id}/movimientos`, `GET /repuestos/{id}/precios` |
| Órdenes | `POST /ordenes`, `GET /ordenes` (`estado`, `page`, `size`), `GET /ordenes/{id}`, `POST /ordenes/{id}/iniciar`, `POST /ordenes/{id}/terminar`, `POST /ordenes/{id}/cancelar`, `GET /estados-orden`, `GET /mis-ordenes` |

**Convenciones transversales de la API**

| Tema | Convención |
|---|---|
| Token | Sólo en cookie `access_token`: `HttpOnly`, `SameSite=Lax`, `Max-Age` = duración del token, `Secure` configurable. Nunca en el cuerpo ni en `Authorization` |
| Contratos | Separados de los modelos de tabla; entrada con `extra="forbid"`; ninguna respuesta incluye `password_hash` |
| PATCH | Sólo aplica los campos enviados (`exclude_unset=True`) |
| Códigos | `201` crear, `204` dar de baja, `404` recurso de la ruta inexistente, `409` choque con lo guardado, `422` cuerpo o parámetros fuera de contrato, `401` sin sesión/token inválido, `403` sin permiso o con contraseña pendiente |
| Listados | `{items, total, page, size, pages}`; `page >= 1`; `size` 1..100 (default 20); página más allá de la última → `422`; con cero resultados hay una página vacía |
| Dinero | `NUMERIC` en la base, `Decimal` en Python. Nunca `float` |
| Fechas | `timestamptz` en la base, con zona; las respuestas de ejemplo usan ISO-8601 con `Z` |
| Errores | Mensaje propio en español; nunca texto interno de PostgreSQL ni traza. Ninguna entrada inválida termina en `500` |
| Diagnóstico | `SQL_ECHO=true` (o equivalente) para ver las consultas en consola — es lo que prueba `C-15` |

## Requisitos no funcionales

| Requisito | Detalle |
|---|---|
| Asincronía | Todos los handlers `async def`; bcrypt siempre fuera del bucle (`to_thread` + semáforo) |
| Credenciales | Ninguna contraseña ni clave de firma en el código —tampoco como valor por defecto—, en `alembic.ini` ni en el repositorio |
| Esquema | Sólo Alembic; la aplicación no usa `create_all` |
| Transacciones | Ningún repositorio confirma; ningún servicio construye su UoW; el UoW no cierra la sesión |
| Carga perezosa | Prohibida: toda relación que se lee se precarga en el repositorio |
| SQL | Nunca armado por concatenación con datos del usuario (parámetros ligados) |
| Unicidad | Garantizada por la base; no se verifica con una consulta previa |
| Concurrencia | Fuera de alcance: se acepta la actualización perdida |
