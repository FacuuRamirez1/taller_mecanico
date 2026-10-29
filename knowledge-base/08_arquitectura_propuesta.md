# Arquitectura Propuesta

## Patrones aplicados

| Patrón | Dónde se usa | Por qué |
|---|---|---|
| **Router → Service → UoW → Repository → Model** | Toda la aplicación, módulo por módulo | Es la arquitectura obligatoria de la consigna: cada capa sabe lo suyo y nada más. Un cambio de regla no toca el router; un cambio de consulta no toca el servicio |
| **Repository genérico** (`BaseRepository[T]`) | `app/core/repository.py` + `*/repository.py` | Centraliza `get_by_id`, `get_all`, `count`, `add`, `update`, `delete`; recibe **sesión y clase del modelo** porque los genéricos se borran en runtime |
| **Soft delete repository** (`SoftDeleteRepository[T]`) | `vehiculo`, `repuesto` | Filtra los dados de baja y agrega `get_by_id_including_deleted` / `soft_delete` **sólo** en la hija |
| **Unit of Work** | `app/core/unit_of_work.py` + `*/unit_of_work.py` | Agrupa las escrituras de una operación de negocio; confirma al salir, revierte con excepción y **no cierra** la sesión |
| **Service layer** | `*/service.py` | Vive acá el negocio: transiciones, permisos finos, 403 vs 409, cálculo de totales, RN-01..RN-20 |
| **DTO / schema separation** | `*/schemas.py` | Contratos de entrada y salida separados de las tablas; `extra="forbid"`; nunca `password_hash` en una respuesta |
| **Dependency injection** | `app/core/dependencies.py`, routers | `get_session`, `get_usuario_actual`, `requiere_rol`, y la dependencia que **construye** el UoW del módulo |
| **Resource lifecycle (lifespan)** | `main.py`, `app/core/database.py` | Motor y `sessionmaker` se crean en el lifespan y viven en `app.state`; nunca al importar |
| **Catalog table** | `estado_orden` | La lista de estados es un conjunto de filas con datos propios (`es_final`), no un `CHECK` con la lista adentro |
| **Append-only por trigger** | Segunda migración | El historial no se corrige ni desde `psql`; la garantía no depende de la aplicación |
| **Punto único de escritura de stock** | Repositorio/servicio de `repuestos` | Todo cambio de stock deja un `movimiento_stock`; imposible "editar el stock" por PATCH |
| **BackgroundTasks** | Terminar orden | Aviso simulado fuera del ciclo de la petición, en el mismo proceso, sólo si la transacción se confirmó |

**Lo que no se usa y por qué**: `create_all` (el esquema es de Alembic), carga perezosa (prohibida), `commit()` en repositorios (lo hace el UoW), locking/`SELECT FOR UPDATE` (concurrencia fuera de alcance), Celery/Redis (capítulo 8 fuera de alcance), frontend y deploy (no se piden).

## Estructura de directorios

Estructura **obligatoria** de la consigna (págs. 9-10). La raíz del repo es la del proyecto: `main.py`, `seed.py`, `app/`, `migrations/` y `test/` conviven.

```
taller_mecanico/
├── main.py                          # Aplicación, lifespan y los DOS grupos de rutas
├── seed.py                          # Deja la base en el estado inicial conocido
├── requirements.txt
├── env.example                      # Todas las variables, NINGÚN secreto
├── alembic.ini                      # Sin credenciales
├── README.md                        # Puesta en marcha desde cero + evidencias
├── .env                             # NO se versiona
├── .gitignore                       # incluye .env, __pycache__, .venv
│
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                # Settings (pydantic-settings) + @computed_field de la URL
│   │   ├── database.py              # crear motor y fábrica (los llama el lifespan) + get_session
│   │   ├── security.py              # bcrypt en to_thread + semáforo; emitir y verificar JWT
│   │   ├── dependencies.py          # usuario actual, roles vigentes, cambio obligatorio, requiere_rol
│   │   ├── repository.py            # BaseRepository[T] y SoftDeleteRepository[T]
│   │   ├── paginacion.py            # envoltorio {items,total,page,size,pages} y cálculo de páginas
│   │   └── unit_of_work.py          # UnitOfWork base: confirma/revierte al salir del bloque
│   │
│   └── modules/
│       ├── health/
│       │   └── router.py            # único archivo del módulo
│       ├── usuarios/
│       │   ├── models.py            # usuario, asignacion_rol, intento_acceso, evento_seguridad
│       │   ├── schemas.py
│       │   ├── repository.py
│       │   ├── unit_of_work.py
│       │   ├── service.py
│       │   └── router.py
│       ├── clientes/
│       │   ├── models.py            # cliente, vehiculo
│       │   ├── schemas.py
│       │   ├── repository.py
│       │   ├── unit_of_work.py
│       │   ├── service.py
│       │   └── router.py
│       ├── repuestos/
│       │   ├── models.py            # repuesto, movimiento_stock, historial_precio_repuesto
│       │   ├── schemas.py
│       │   ├── repository.py
│       │   ├── unit_of_work.py
│       │   ├── service.py
│       │   └── router.py
│       └── ordenes/
│           ├── models.py            # orden_trabajo, item_orden, estado_orden, historial_estado_orden
│           ├── schemas.py
│           ├── repository.py
│           ├── unit_of_work.py
│           ├── service.py
│           └── router.py
│
├── migrations/
│   ├── env.py                       # plantilla ASINCRÓNICA; toma la URL de Settings
│   ├── script.py.mako
│   └── versions/
│       ├── xxxx_esquema_inicial.py  # autogenerate: todas las tablas, índices y CHECK
│       └── yyyy_solo_agregado.py    # A MANO: función + trigger; downgrade lo elimina
│
└── test/
    ├── c01_parametro_invalido.http
    ├── ...                          # C-01 .. C-19, cada uno con la respuesta esperada comentada
    ├── c14_solo_agregado.http
    └── solo_agregado.sql            # 6 rechazos del trigger
```

**Reglas de la estructura**

| Regla | Detalle |
|---|---|
| Módulos mínimos | `health`, `usuarios`, `clientes`, `repuestos`, `ordenes` |
| Seis capas por módulo | `models`, `schemas`, `repository`, `unit_of_work`, `service`, `router` |
| Excepción | `health` **sólo** tiene `router.py` |
| Dónde vive cada entidad | `AsignacionRol`, `IntentoAcceso`, `EventoSeguridad` → `usuarios`; `Vehiculo` → `clientes`; `MovimientoStock`, `HistorialPrecioRepuesto` → `repuestos`; `EstadoOrden`, `ItemOrden`, `HistorialEstadoOrden` → `ordenes` |
| `main.py` | Monta el grupo abierto y el protegido; el control de cambio obligatorio se monta **una sola vez** |
| `migrations/` | Configuración de Alembic + versiones; **`env.py` asincrónico** |
| `test/` | `.http` de REST Client + `solo_agregado.sql` |

**Reparto de responsabilidades (el punto que más pesa)**

| Componente | Crea la sesión | Crea el UoW | Abre el UoW | Confirma | Cierra la sesión |
|---|---|---|---|---|---|
| `get_session` | **sí** | no | no | no | **sí**, al terminar la petición |
| Router | no | **sí** (vía dependencia) | no | no | no |
| Servicio | no | **no** | **sí** (`async with`) | no (lo hace el UoW) | no |
| UoW | no | no | no | **sí** / revierte | **no** (no la creó) |
| Repositorio | no | no | no | **nunca** (`flush`) | no |

## Seguridad

- **Autenticación**: contraseñas con **bcrypt** (costo en configuración, llamadas en `to_thread` bajo semáforo); JWT **HS256** firmado con `sub`, `iat`, `exp` y roles, transportado **sólo** en cookie `access_token` `HttpOnly`, `SameSite=Lax`, `Max-Age` = duración del token, `Secure` configurable.
- **Sesión**: se lee de `request.cookies`. **Nunca** del cuerpo ni del encabezado `Authorization` (un `Bearer` da 401).
- **Autorización**: `get_usuario_actual` (401) + `requiere_rol` (403) que consulta **roles vigentes en la base en cada petición**. Los roles del token son informativos. Los permisos finos (dueño de la orden, mecánico asignado) se deciden en el servicio.
- **Cambio obligatorio**: dos grupos de rutas; el control se monta una vez en el protegido (FastAPI suma dependencias, no las resta).
- **Invalidación de sesiones**: `iat` con fracciones comparado **sin truncar** contra `password_cambiada_en`.
- **Anti-enumeración**: mismo cuerpo y tiempo parecido exista o no el correo (hash ficticio precalculado en el lifespan), y límite de intentos **antes** de hashear.
- **Validación de entrada**: schemas con `extra="forbid"`, límites de tamaño (`size` 1..100, password ≤ 72 **bytes**), parámetros de ruta tipados (`C-01` → 422 sin ejecutar el handler) y **SQL con parámetros ligados** (nunca concatenación).
- **Errores**: mensaje propio, sin texto de PostgreSQL ni traza; `IntegrityError` traducido; ninguna entrada inválida en 500.
- **Secretos**: sólo del entorno. `Settings` **no** define default para la clave de firma ni para la contraseña de la base: si faltan, la aplicación **no arranca**. `env.example` documenta las variables y no contiene valores reales; `.env` no se versiona; `alembic.ini` no lleva credenciales.
- **Integridad**: el trigger de sólo agregado protege los historiales incluso de un `UPDATE` manual en `psql`.

## Variables de entorno

Los **nombres** de `POSTGRES_*` están fijados por la consigna. Los demás nombres no están fijados: se proponen acá y deben coincidir con `Settings`, `env.example` y el `README`.

| Variable | Descripción | Ejemplo | Sensible |
|---|---|---|---|
| `POSTGRES_USER` | Usuario de PostgreSQL | `taller` | N |
| `POSTGRES_PASSWORD` | Contraseña de PostgreSQL | `***` | **S** |
| `POSTGRES_DB` | Nombre de la base | `taller_mecanico` | N |
| `POSTGRES_HOST` | Host | `localhost` | N |
| `POSTGRES_PORT` | Puerto | `5432` | N |
| `DATABASE_URL` | **Calculada** con `@computed_field` (no se escribe en `.env`) | `postgresql+asyncpg://…` | S (contiene la password) |
| `JWT_SECRET_KEY` *(nombre propuesto)* | Clave de firma del JWT | `***` | **S** |
| `JWT_ALGORITHM` *(propuesto)* | Algoritmo | `HS256` | N |
| `JWT_EXPIRE_SECONDS` *(propuesto)* | Duración del token y del `Max-Age` | `1800` | N |
| `BCRYPT_COST` *(propuesto)* | Costo de bcrypt | `12` | N |
| `DB_POOL_SIZE` *(propuesto)* | Tamaño del pool del motor | `5` | N |
| `SQL_ECHO` *(propuesto)* | Ver consultas en consola | `true` en desarrollo | N |
| `COOKIE_SECURE` *(propuesto)* | Flag `Secure` de la cookie | `false` en local | N |

**Sobre los valores por defecto**: la prohibición de la consigna aplica a los **secretos** — la clave de firma y la contraseña de la base **no** pueden tener default en el código ni en `alembic.ini`. El resto de la configuración puede declarar un default en `Settings` o, preferentemente, en `env.example`; los valores acordados son `HS256`, `1800` s, bcrypt `12`, `size` de página 20 y pool chico (5).

**Clave de firma**: el `README` tiene que explicar cómo generarla. La consigna **no** fija el método; propuesta: `python -c "import secrets; print(secrets.token_urlsafe(64))"`. Una clave generada al arrancar **no sirve**: cambia en cada reinicio y dos procesos rechazarían los tokens del otro.

## Migraciones

| Migración | Cómo se produce | Contenido |
|---|---|---|
| 1 | `alembic revision --autogenerate` | Todas las tablas, FKs, `CHECK`, `UNIQUE` y los **3 índices únicos parciales** con `postgresql_where`. Crea `estado_orden` **vacía** |
| 2 | **A mano** | Función + trigger que rechazan `UPDATE`/`DELETE` sobre las tres tablas de sólo agregado. `downgrade` los elimina |

- `autogenerate` **no ve funciones ni disparadores**: por eso la segunda va a mano.
- Cada migración se **lee** antes de aplicarla y lleva un comentario que lo diga.
- Secuencia de aceptación: `upgrade head` sobre base vacía → `downgrade base` → `upgrade head`.
- El catálogo **no** se carga en la migración: es dato, lo carga `seed.py`.

## Prohibiciones

Enumeración exhaustiva. Son las que la cátedra busca activamente al leer el código.

| # | Prohibido | Dónde se verifica |
|---|---|---|
| 1 | `create_all` / `metadata.create_all` | `main.py`, `database.py` |
| 2 | Carga perezosa (leer una relación no precargada) | Repositorios; `C-15` |
| 3 | `commit()` dentro de un repositorio | `repository.py` (`flush` solamente) |
| 4 | Que un **servicio** construya su UoW | `service.py` |
| 5 | Token en el cuerpo de la respuesta o leído de `Authorization` | `security.py`, `dependencies.py`; `C-03` |
| 6 | bcrypt dentro del bucle de eventos (sin `to_thread`) | `security.py` |
| 7 | SQL armado por concatenación con datos del usuario | Búsqueda de repuestos; `C-16` |
| 8 | Devolver texto interno de la base o una traza | Manejo de excepciones; `RN-18` |
| 9 | Verificar unicidad con una consulta previa (`SELECT` + `INSERT`) | Altas; `RN-01` |
| 10 | Editar el stock por `PATCH` | `schemas.py` de repuestos; `C-16` |
| 11 | Editar el catálogo `estado_orden` por API | No existe endpoint de escritura |
| 12 | `password_hash` en cualquier respuesta | `schemas.py` |
| 13 | Aceptar campos no declarados (`extra="forbid"`) | Todos los schemas de entrada |
| 14 | Aceptar `precio`, `total`, `estado` o `creada_en` en el alta de orden | Schema de `POST /ordenes` |
| 15 | Secretos con valor por defecto en el código | `config.py` |
| 16 | Versionar `.env` | `.gitignore`, repo |

> El pedido interno de esta fase habla de "14 prohibiciones": al desdoblarlas (secretos en código / `.env` versionado; los cuatro campos del alta de orden) el listado exhaustivo da **16**. Se listan las 16 para no perder ninguna → `IN-02` en `10_preguntas_abiertas.md`.

## Estrategia de pruebas

| Artefacto | Qué prueba |
|---|---|
| `test/c01…c19*.http` | Los 19 casos, con la respuesta esperada en un comentario. Se corre `python seed.py` **antes de cada archivo** |
| `test/solo_agregado.sql` | Los 6 `UPDATE`/`DELETE` rechazados por el trigger (`C-14`), ejecutados en `psql` |
| `SQL_ECHO=true` | Evidencia de `C-15`: mismas consultas con 2 y con 4 ítems |
| Evidencia `C-14` | Captura de `psql` con los 6 rechazos + el de la FK |
| Evidencia `C-15` | Fragmento de consola con las consultas del detalle |

Sesiones simultáneas en REST Client: cada login con `# @name`, los pedidos de esa sesión con `# @no-cookie-jar` y `Cookie: {{loginAdmin.response.headers.Set-Cookie}}`. Es lo que permite tener admin y recepción a la vez en `C-07`.

**No hay pytest ni CI**: los casos son manuales y dependen de correr el seed. Riesgo asumido y documentado (`09_decisiones_y_supuestos.md`, `SU-05`).
