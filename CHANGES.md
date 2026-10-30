# CHANGES — Secuencia de Implementación

> Índice canónico de los changes del proyecto **Taller Mecánico** (TP Programación III, TUP).
> **9 changes**: `C-00` (setup del entorno) + `C-01`…`C-08` (Ej. 1 … Ej. 8 de la consigna, en ese orden exacto).
> 4 personas · 4 días · PostgreSQL 16 **local**, sin Docker · un solo rol de base · objetivo: **aprobar el TP**.
> Cada change es atómico y se cierra con sus casos `C-XX` en verde. **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**

---

## Cómo usar este documento

1. **Identificar el change**: solo se arranca el change cuyo bloque anterior está en `[x]`. El orden `C-00 → C-01 → … → C-08` **no se reordena por peso** (restricción del usuario).
2. **Leer la KB antes de codificar**: los 3-5 punteros de *Leer antes* del change. La KB es la fuente de verdad; si el código y la KB discrepan, gana la KB (salvo que se actualice la KB primero).
3. **Proponer**: `/opsx:propose C-NN-{nombre}`. El `proposal.md` no inventa alcance: copia el **Scope** de este archivo y los criterios de aceptación de `06_funcionalidades.md`.
4. **Implementar + archivar**: al cerrar, `/opsx:archive` y marcar el change como `[x]` acá.
5. **Definición de terminado (las 6 de siempre)** — un change no está cerrado si falla cualquiera:
   - [ ] `alembic upgrade head` sobre **base vacía** + `python seed.py` corren sin error (desde `C-02`; en `C-00`/`C-01` alcanza con que la app arranque y `/health/ready` dé 200).
   - [ ] Sus casos `C-XX` pasan y quedan en `test/*.http` con la respuesta esperada **comentada**.
   - [ ] `grep` de las prohibiciones que le aplican: sin `create_all`, sin `commit()` en repositorios, sin `Authorization`/token en el cuerpo, sin `password_hash` en respuestas, sin carga perezosa.
   - [ ] Ningún secreto nuevo en el repo (`.env` fuera de git; `env.example` sin valores reales).
   - [ ] `git rebase` sobre `main` + smoke test en `main` (arranca, migra, seed).
   - [ ] El **Estado** de este bloque queda en `[x]`.

> **Puerta dura (R-01, "que no levante")**: si en cualquier momento `alembic upgrade head` sobre base vacía deja de funcionar, **se congela todo** y ese es el único trabajo permitido hasta volver a verde. Un proyecto que no levanta no se corrige, y ese riesgo anula los 100 puntos.

---

## Árbol de dependencias

```
C-00  setup-entorno-local ......................... 0 %   5 h   ·  GATE 0
└── C-01  ej1-config-ciclo-vida ................... 8 %   6 h   ·  GATE 1 (arranca)
    └── C-02  ej2-modelos-migraciones ............. 14 %  12 h  ·  GATE 2 (migra) ◄ PUERTA DURA
        └── C-03  ej3-contratos-crud .............. 10 %   9 h  ·  GATE 3 ◄ PRIMER FORK
            ├── C-04  ej4-autenticacion ........... 16 %  11 h  ·  GATE 4
            │   ├── C-05  ej5-autorizacion ........ 14 %   9 h
            │   │   └── C-06  ej6-repositorios-uow  20 %  14 h
            │   │       └── C-08  ej8-n-plus-1 ..... 8 %   9 h  ·  GATE 5 → GATE 6 (entrega)
            │   └── C-07  ej7-integridad ........... 10 %   5 h
            │       (depende además de C-02: el trigger lo instala la 2.ª migración)
            └── C-06 núcleo (repository.py, unit_of_work.py, UoW por módulo,
                refactor de los services de C-03) arranca EN PARALELO con C-04
```

Lectura del árbol:

| Relación | Significado |
|---|---|
| **Dependencia dura** (`└──`) | No se puede **cerrar** el change sin el anterior mergeado en `main`. |
| **Solapamiento de ejecución** (`C-06 núcleo` al lado de `C-04`) | Se puede **empezar a escribir** con el contrato congelado, aunque el cierre espere. Es lo que hace posible el fork. |

### Paralelismo por fase

```
GATE 0: C-00 ✓
  → C-01  ej1-config-ciclo-vida          [4 personas, carril único]

GATE 1: C-01 ✓  (uvicorn arriba, /health/live 200, /health/ready 200 y 503 con la base caída)
  → C-02  ej2-modelos-migraciones        [4 personas, carril único — reparto por archivo de modelos]

GATE 2: C-02 ✓  (upgrade → downgrade → upgrade sobre base vacía)        ◄ PUERTA DURA
  → C-03  ej3-contratos-crud             [4 personas, carril único — reparto por módulo]

GATE 3: C-03 ✓                                                          ◄ PRIMER FORK
  → C-04  ej4-autenticacion              [Agente A + Agente B — 16 %, es el change más caro en riesgo]
  → C-06  ej6-repositorios-uow (núcleo)  [Agente C + Agente D — repository/UoW + refactor de C-03]
     · C-05 no puede arrancar: necesita el `get_usuario_actual` de C-04.
     · C-07 no puede arrancar: necesita el `intento_acceso` de C-04.

GATE 4: C-04 ✓                                                          ◄ 3 changes a la vez
  → C-05  ej5-autorizacion               [Agente B]
  → C-06  ej6-repositorios-uow (cierre)  [Agente C + Agente D]
  → C-07  ej7-integridad                 [Agente A]

GATE 5: C-05 ✓ y C-06 ✓
  → C-08  ej8-n-plus-1                   [Agente A + Agente D]
  → C-07  cierre (solo_agregado.sql + evidencia C-14)   [Agente B]
  → C-06  cierre de C-12 / C-18          [Agente C]

GATE 6: C-08 ✓  → entrega: corrida completa de los 19 casos desde cero + README + evidencias [todos]
```

**Respuesta corta a "¿desde cuándo pican en paralelo las 4 personas?"**
Desde **`C-04` (Ej. 4)**. Antes de eso, `C-00 → C-01 → C-02 → C-03` es una **cadena secuencial**: cada change es prerrequisito del siguiente y las 4 personas trabajan **dentro del mismo change**, repartiéndose archivos, no changes. En `C-04` se abre el primer fork real (2 ramas); en `C-05`/`C-06`/`C-07` (GATE 4) las 4 personas están en **3 changes distintos** a la vez, que es el máximo paralelismo del proyecto.

### Camino crítico (8 changes — mínimo irreducible)

```
C-00 → C-01 → C-02 → C-03 → C-04 → C-05 → C-06 → C-08
 5 h    6 h    12 h    9 h    11 h     9 h    14 h    9 h   =  75 h-persona
```

- `C-05` está en el camino crítico **solo por el cableado final de `requiere_rol`** de `C-06`; su trabajo propio (personal, roles, eventos, dos grupos de rutas) podría correr en paralelo. Si `C-05` se atrasa, `C-06` no cierra.
- `C-07` (5 h) es el **único change con holgura**: el trigger ya se instala en `C-02` (lo exigen US-008 y US-009) y su trabajo real es la verificación, `test/solo_agregado.sql` y la evidencia. No está en el camino crítico y es el colchón del día 4.
- `C-08` cierra el camino porque incluye las evidencias y la corrida completa, que es el último kilómetro de la entrega.

### Plan multi-agente para 4 personas

> El formato canónico de este documento asume 3 agentes; acá el equipo real es de **4 personas**, así que la tabla tiene 4 columnas. Se mantiene una columna por *carril de propiedad*, no por persona intercambiable.

| Carril | Persona | Dueño de | Changes |
|---|---|---|---|
| **A — Plataforma** | A | `app/core/` (config, database, security en C-01, repository, unit_of_work, paginacion), `main.py`, `alembic.ini`, `migrations/`, `requirements.txt`, `env.example` | C-00, C-01, C-02 (migraciones), C-06 (core), C-07, C-08 |
| **B — Seguridad** | B | `app/core/security.py` y `dependencies.py` (desde C-04), `app/modules/usuarios/` | C-04, C-05, C-07 (cierre), C-08 |
| **C — Inventario** | C | `app/modules/repuestos/`, `app/modules/clientes/` | C-02 (modelos), C-03, C-06, C-08 |
| **D — Órdenes** | D | `app/modules/ordenes/`, `seed.py`, `README.md` | C-02 (modelos), C-03, C-06, C-08 |

| Paso | Agente A (plataforma) | Agente B (seguridad) | Agente C (inventario) | Agente D (órdenes) |
|---|---|---|---|---|
| **Día 1 · AM** | PG local + `requirements.txt` + `alembic.ini` + `env.py` (C-00) | `.env`, `env.example`, `.gitignore`, árbol de carpetas (C-00) | Verifica las 4 máquinas, `pip install` limpio (C-00) | `migrations/script.py.mako`, `versions/` vacío, prueba `alembic current` (C-00) |
| **Día 1 · PM** | `config.py` + `database.py` + `main.py` (lifespan) (C-01) | `security.py` mínimo (hash/verify + semáforo) + hash ficticio (C-01) | `health/router.py` (`live`/`ready`) (C-01) | Arranca modelos: `usuarios` + `clientes` (C-02) |
| **Día 2 · AM** | Migración 0001 `autogenerate` + revisión línea por línea (C-02) | Migración 0002 a mano: función + trigger + `downgrade` (C-02) | Modelos `repuestos` + `movimientos` + índices parciales (C-02) | Modelos `ordenes` + catálogo + navegación (C-02) |
| **Día 2 · PM** | `paginacion.py` + manejo de errores (`IntegrityError`→409, 422, 404) (C-03) | Schemas de `usuarios` + `extra="forbid"` global (C-03) | CRUD `repuestos` + `clientes` + `vehiculos` (C-03) | Schemas de `ordenes` + **`seed.py` completo** (C-03) |
| **Día 3 · AM** | **C-04**: JWT + cookie + orden del login | **C-04**: bcrypt en `to_thread`, límite, registro atómico | **C-06**: `repository.py` + `unit_of_work.py` | **C-06**: UoW de cada módulo + migra los services de C-03 |
| **Día 3 · PM** | **C-07**: verifica trigger, escribe `solo_agregado.sql` | **C-05**: `dependencies.py` + roles vigentes + dos grupos de rutas | **C-06**: repositorios por entidad + punto único de stock | **C-06**: órdenes (alta, iniciar, terminar, cancelar) + permisos finos |
| **Día 4 · AM** | **C-08**: precarga en repositorios + C-15 | **C-05** cierre (C-07, C-08, C-09) + **C-07** evidencia C-14 | **C-06** cierre (C-12, C-18, C-17) | **C-08**: `BackgroundTasks` + detalle sin N+1 |
| **Día 4 · PM** | **C-08**: `README.md` + evidencias + corrida completa | Corrida completa de los 19 casos | Corrida completa + `grep` de prohibiciones | Corrida completa + entrega |

#### Propiedad de archivos (regla anti-conflicto)

Los archivos core son el punto de conflicto real (`SU-04`, riesgo **alto**: 44 % de la nota depende de `unit_of_work.py`, `dependencies.py`, `config.py`, `database.py` y los modelos). Regla:

| Archivo / carpeta | Dueño único | Cómo lo toca otro |
|---|---|---|
| `app/core/config.py` | **A** | **Nadie.** En `C-01` se declara la superficie **completa** de `Settings` (las 13 variables de `08_arquitectura_propuesta.md` §Variables de entorno) y se congela. Si falta una variable, la agrega A en el mismo día. |
| `app/core/database.py` | **A** | Nadie. `get_session` es contrato: lo consumen todos, no lo editan. |
| `app/core/security.py` | **A** hasta C-01 → **B** desde C-04 | A entrega solo las primitivas (hash/verify + semáforo) porque el lifespan del Ej. 1 necesita el hash ficticio; a partir de C-04 el archivo es de B y A no lo vuelve a abrir. |
| `app/core/dependencies.py` | **B** (desde C-04) | Nadie más. El contrato (`get_usuario_actual`, `requiere_rol`) se anuncia en el sync del día 3. |
| `app/core/repository.py`, `unit_of_work.py` | **A** (C-06) | C y D **heredan/instancian**, no editan la base. |
| `app/core/paginacion.py` | **A** (C-03) | Nadie. |
| `main.py` | **A** | **Dos ediciones pactadas y nada más**: (1) B registra `/auth` en C-04; (2) B parte los dos grupos de rutas en C-05. Se avisa en el sync de las 9:00 y A está mirando. |
| `seed.py` | **D** (C-03, completo de una vez) | Nadie después. C-08 solo lo **corre** N veces para verificar idempotencia. |
| `alembic.ini`, `migrations/` | **A** | C-07 **no** crea migraciones nuevas (la consigna pide dos): si el trigger necesita un ajuste, lo pide a A y se corrige **antes** del merge de C-02. |
| `app/modules/usuarios/` | **B** | Nadie. |
| `app/modules/repuestos/`, `app/modules/clientes/` | **C** | Nadie. |
| `app/modules/ordenes/` | **D** | Nadie. C-05 **no** toca `ordenes/`: el permiso fino de la orden se implementa en C-06. |
| `test/` | Quien cierra el caso | Un archivo por caso (`c01…c19`) → sin conflictos por archivo. |
| `README.md` | **D** (C-08) | Nadie más escribe el README hasta el día 4. |

#### Estrategia de ramas (el supuesto sin probar, resuelto)

`SU-04` dice que **no hay** estrategia y que si 4 personas se pisan en los archivos core, se arrastra el 44 % de la nota. Propuesta concreta:

- **Trunk-based con ramas cortas**: una rama por change (`c-00-setup`, `c-01-ej1`, …, `c-08-ej8`). `C-02` y `C-06` duran más de un día → se parten en `c-02a-modelos` / `c-02b-migraciones` y `c-06a-uow-base` / `c-06b-ordenes`.
- **Integración diaria a las 18:00**: A es el integrador. Cada uno hace `git pull --rebase` + corre el smoke antes de pedir merge. **Sin merge commits**, sin ramas de más de 36 h.
- **`main` siempre verde**, con esta definición operativa: `alembic upgrade head` sobre base vacía + `uvicorn main:app` + `/health/ready` 200 + `python seed.py` OK. Nada entra a `main` si rompe eso.
- **Contrato congelado**: al pasar GATE 2 quedan congelados los nombres de `04_modelo_de_datos.md` y la tabla de endpoints de `03_actores_y_roles.md`. Cambiar un contrato no es una decisión de una persona: se anuncia en el sync de las 9:00 y se anota en el Scope del change.
- **Dos syncs de 10 minutos**: 9:00 (qué se mergea hoy + contratos) y 17:30 (estado de los gates y del recorte, si toca).

#### Bloqueantes P0 (asignados, no sueltos)

| ID | Qué se decide | Change donde se resuelve | Cuándo | Dueño | Si no se resuelve |
|---|---|---|---|---|---|
| **Q-02** | Datos de conexión locales: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT` (un solo rol, sin Docker) | **C-00** | Día 1, 9:00, antes de instalar PG | A (acuerda con el equipo) | Nadie levanta el proyecto el día 1 |
| **Q-01** | Nombre de la variable de la clave de firma — **propuesto `JWT_SECRET_KEY`** | **C-01** (`Settings`), consumida ya en `env.example` de C-00 | Día 1, 9:00 (10 min) | A | La app no arranca o `env.example` miente |
| **IN-05 / Q-10** | `PATCH /repuestos/{id}` con precio **menor**: ¿**422** o **409**? (el `CHECK precio_nuevo > precio_anterior` lo rechaza igual) | **C-06** (lo implementa C en `repuestos/service.py`) | Día 3, 9:00, antes de arrancar C-06 | C, confirma el equipo | El caso termina en **500**, que RN-18 prohíbe explícitamente |

> Recomendación del roadmap para `Q-10`: **422**, porque la tabla de la ruta declara `200, 404, 422` y `409` no está entre los códigos admitidos. Queda como decisión del equipo, no como hecho consumado.

Otros P1 que van a morder si nadie los mira: `Q-14` (nombres de los campos de cambio de contraseña) → **C-04**; `Q-06` (ventana de 60 s deslizante) → **C-04**; `Q-11` (`POST /clientes` no acepta `usuario_id`) y `Q-20` (`pages` con 0 resultados) → **C-03**; `Q-04` ("el personal" = ADMIN + RECEPCION + MECANICO), `Q-05`, `Q-12`, `Q-13` → **C-05**; `Q-09` (métodos del repo de catálogo) y `Q-16` (repuesto dado de baja → 409) → **C-06**; `Q-15` (¿el 429 se registra?) → **C-07**.

---

## FASE 0 — Arranque (nada de código de negocio)

### [C-00] `setup-entorno-local`

- **Estado**: `[x]` completado (archivado 2026-10-29)
- **Ejercicio**: ninguno (transversal, **condición de corrección**) · **Peso**: 0 % · **Esfuerzo**: 5 h-persona
- **Dueño**: A (con B, C y D en paralelo sobre su propia máquina)
- **Scope**:
  - **PostgreSQL 16 local, sin Docker**: crear el rol único y la base `taller_mecanico`; verificar `psql -c "select version()"` y `\dt`. Un solo rol de base (no se implementa el segundo mecanismo de sólo agregado por permisos).
  - `.venv` + `requirements.txt` **pinneado**: Python 3.12, FastAPI 0.111, SQLModel 0.0.24, SQLAlchemy 2.0 async, asyncpg 0.30, Alembic 1.13, pydantic-settings 2.0, bcrypt 4.0, PyJWT 2.8, uvicorn.
  - `env.example` con las **13 variables** de `08_arquitectura_propuesta.md` §Variables de entorno y **ningún** secreto; `.env` local creado a partir de él y **no** versionado; `.gitignore` con `.env`, `__pycache__/`, `.venv/`.
  - `alembic.ini` **sin credenciales** + `migrations/env.py` con plantilla **asincrónica** (importa `Settings` de `app.core.config`, que existe recién en C-01 → se deja el import y se completa al día siguiente) + `script.py.mako` + `versions/` vacío.
  - **Estructura de carpetas vacía** de la consigna: `app/core/`, `app/modules/{health,usuarios,clientes,repuestos,ordenes}/` (cada una con su `__init__.py`), `migrations/versions/`, `test/`, y `main.py`/`seed.py` como archivos vacíos con un `TODO C-01` / `TODO C-03`.
  - **Contrato de arranque**: un documento de 5 líneas en el mensaje fijado del canal con la URL de conexión, el comando de arranque y el comando de migración, para que las 4 máquinas sean idénticas.
- **Dependencias**: ninguna
- **Governance**: **ALTO** — si esto falla no hay proyecto; no hay nota que rescatar.
- **Cubre**: — (no hay caso `C-XX`; habilita a todos)
- **Produce**: `requirements.txt`, `env.example`, `.gitignore`, `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`, árbol de `app/` y `test/`, `.env` local.
- **Cierra con**:
  - [ ] 4/4 máquinas: `pip install -r requirements.txt` sin error y `python -c "import fastapi, sqlmodel, alembic, asyncpg"`.
  - [ ] `psql` conecta con el rol único y la base creada.
  - [ ] `git status` no muestra `.env`; `grep -r "password" env.example` no devuelve valores reales.
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios
  - `knowledge-base/08_arquitectura_propuesta.md` §Variables de entorno
  - `knowledge-base/08_arquitectura_propuesta.md` §Migraciones
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-08 (PostgreSQL local, sin Docker)
  - `knowledge-base/10_preguntas_abiertas.md` §Q-02

---

## FASE 1 — Cadena fundacional (secuencial, sin paralelismo entre changes)

> Acá las 4 personas trabajan **dentro del mismo change**, repartiéndose archivos. Ningún change de esta fase se puede adelantar: `C-01` necesita la base y el venv, `C-02` necesita la app, `C-03` necesita el esquema.

### [C-01] `ej1-config-ciclo-vida`

- **Estado**: `[x]` completado (archivado 2026-10-29)
- **Ejercicio**: **Ej. 1** · **Peso**: 8 % · **Esfuerzo**: 6 h-persona
- **Dueño**: A (B aporta `security.py` mínimo; C el router de health)
- **Scope**:
  - `app/core/config.py`: `Settings` (pydantic-settings) con `POSTGRES_USER/PASSWORD/DB/HOST/PORT` + `JWT_SECRET_KEY`, `JWT_ALGORITHM=HS256`, `JWT_EXPIRE_SECONDS=1800`, `BCRYPT_COST=12`, `DB_POOL_SIZE=5`, `SQL_ECHO`, `COOKIE_SECURE`; `DATABASE_URL` con `@computed_field` y driver `postgresql+asyncpg`; **sin default** en la clave de firma ni en la contraseña de la base → si faltan, la app **no arranca**.
  - `app/core/database.py`: `crear_engine(settings)` / `crear_sessionmaker(engine)` (los llama el lifespan) + `get_session` que toma la fábrica de `app.state`, crea con `expire_on_commit=False`, **no** hace `commit` y cierra al terminar la petición.
  - `main.py`: `lifespan` que crea motor y `sessionmaker` **dentro** del bucle, los guarda en `app.state`, calcula **una vez** el hash ficticio y en el shutdown hace `engine.dispose()`. **Nada** se construye al importar.
  - `app/core/security.py` **mínimo**: `hash_password` / `verify_password` en `to_thread` bajo `asyncio.Semaphore`, costo desde `Settings` (lo necesita el lifespan para el hash ficticio; C-04 lo completa con JWT).
  - `app/modules/health/router.py`: `GET /health/live` → 200 sin tocar la base; `GET /health/ready` → `SELECT 1`, 200 si contesta y **503** si no.
- **Dependencias**: `C-00`
- **Governance**: **CRÍTICO** — arranque + secretos sin default (una credencial real en el repo anula la corrección).
- **Cubre**: — (no hay caso `C-XX`; habilita `C-03` y `C-15`)
- **Produce**: `app/core/config.py`, `app/core/database.py`, `app/core/security.py` (mínimo), `app/modules/health/router.py`, `main.py`, `.env` local.
- **Cierra con**:
  - [ ] `uvicorn main:app` levanta; `/health/live` 200 y `/health/ready` 200.
  - [ ] Con PostgreSQL detenido, `/health/ready` da **503** y `/health/live` sigue 200.
  - [ ] Sin `JWT_SECRET_KEY` en el entorno, la app **no** arranca (probarlo).
  - [ ] `alembic current` conecta usando `Settings` (sin credenciales en `alembic.ini`).
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md` §Variables de entorno
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad
  - `knowledge-base/06_funcionalidades.md` §Épica 0 — Fundaciones y ciclo de vida
  - `knowledge-base/07_flujos_principales.md` §Flujo 11 — Arranque y salud
  - `knowledge-base/10_preguntas_abiertas.md` §Q-01

### [C-02] `ej2-modelos-migraciones`

- **Estado**: `[ ]` pendiente
- **Ejercicio**: **Ej. 2** · **Peso**: 14 % · **Esfuerzo**: 12 h-persona
- **Dueño**: A (migraciones) + B/C/D (modelos por módulo)
- **Scope**:
  - `Modelos: usuario, asignacion_rol, intento_acceso, evento_seguridad, cliente, vehiculo, repuesto, estado_orden, orden_trabajo, item_orden, historial_estado_orden, movimiento_stock, historial_precio_repuesto` — **13 tablas**, no 12 (`IN-01`: el conteo de 12 pierde `evento_seguridad` y con ella el Ej. 5 y el actor `SISTEMA`).
  - Nombres de tabla y columna **literales** de `04_modelo_de_datos.md`; tipos: dinero en `NUMERIC(10,2)`/`NUMERIC(12,2)` con `Decimal`, fechas en `timestamptz`.
  - **CHECK**: `anio BETWEEN 1950 AND 2100`, `precio > 0`, `stock >= 0`, `total >= 0`, `cantidad > 0`, `precio_unitario > 0`, `precio_nuevo > 0`, `precio_nuevo > precio_anterior`, `rol IN ('ADMIN','RECEPCION','MECANICO','CLIENTE')`.
  - **UNIQUE**: `usuario.email`, `cliente.documento`, `cliente.usuario_id`, `estado_orden.posicion`, `(item_orden.orden_id, repuesto_id)`.
  - **3 índices únicos parciales** con `postgresql_where`: `asignacion_rol (usuario_id, rol) WHERE revocada_en IS NULL`, `vehiculo (patente) WHERE borrado_en IS NULL`, `repuesto (codigo) WHERE borrado_en IS NULL`.
  - `orden_trabajo.estado`, `historial_estado_orden.desde_estado` y `hasta_estado` son **FK a `estado_orden.codigo`** (no un CHECK con la lista).
  - **Navegación en los dos extremos**; `Usuario.cliente` devuelve **un objeto** o `None`, nunca una lista; `orden_trabajo ↔ item_orden` modela la composición.
  - **Índice propio en toda FK** + índice compuesto `intento_acceso (email, ip, cuando)`.
  - `migrations/versions/0001_esquema_inicial.py`: **`autogenerate`**, con todas las tablas, CHECK, UNIQUE y los 3 índices parciales; crea `estado_orden` **vacía**; comentario de que se leyó antes de aplicar.
  - `migrations/versions/0002_solo_agregado.py`: **a mano**, función + trigger que rechazan `UPDATE`/`DELETE` en las 3 tablas de sólo agregado; **`downgrade` elimina función y trigger**; comentario de que se leyó antes de aplicar. (El trigger se instala acá, no en C-07: lo exigen US-008/US-009 para que `downgrade base` funcione.)
  - Sin `create_all` en ningún archivo.
- **Dependencias**: `C-01`
- **Governance**: **CRÍTICO** — modelos core que todo lo demás referencia + `alembic upgrade head` sobre base vacía (puerta dura).
- **Cubre**: `C-14` (instalación del trigger, demostración en C-07) · `C-17` (mitad esquema: catálogo con FK y `posicion` única) · `C-19` (mitad esquema: el índice parcial de patente)
- **Produce**: `app/modules/{usuarios,clientes,repuestos,ordenes}/models.py`, `migrations/env.py` (final), `migrations/versions/0001_esquema_inicial.py`, `migrations/versions/0002_solo_agregado.py`.
- **Cierra con — PUERTA DURA**:
  - [ ] `alembic upgrade head` sobre base **vacía** funciona.
  - [ ] `alembic downgrade base` funciona (borra el trigger y la función).
  - [ ] Otro `alembic upgrade head` funciona.
  - [ ] `\d` en psql muestra las **13 tablas** y los **3 índices parciales** (`WHERE borrado_en IS NULL` / `WHERE revocada_en IS NULL`).
  - [ ] `python seed.py` **todavía no existe** → el catálogo queda vacío; crear una orden sin catálogo debe dar 409 (se verifica en C-06).
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Entidades (las 13) y §Índices y restricciones — resumen
  - `knowledge-base/06_funcionalidades.md` §Épica 1 — Modelo, restricciones y migraciones
  - `knowledge-base/08_arquitectura_propuesta.md` §Migraciones
  - `knowledge-base/05_reglas_de_negocio.md` §RN-01, §RN-03, §RN-15, §RN-19
  - `knowledge-base/10_preguntas_abiertas.md` §IN-01

### [C-03] `ej3-contratos-crud`

- **Estado**: `[ ]` pendiente
- **Ejercicio**: **Ej. 3** · **Peso**: 10 % · **Esfuerzo**: 9 h-persona
- **Dueño**: C (repuestos, clientes, vehículos) + D (`seed.py`, schemas de órdenes) + B (schemas de usuarios) + A (paginación y errores)
- **Scope**:
  - `*/schemas.py` separados de los modelos: **`extra="forbid"`** en toda entrada, **nunca** `password_hash` en una salida, `PATCH` con `exclude_unset=True`, el alta de orden **no** acepta `precio`/`total`/`estado`/`creada_en`, el alta de repuesto acepta `stock_inicial` (no `stock`), contraseña máx. **72 bytes** y mín. 8.
  - `app/core/paginacion.py`: envoltorio `{items, total, page, size, pages}`; `page >= 1`; `size` 1..100 (default 20); página más allá de la última → **422** con mensaje propio ("La página N no existe: hay M"); `total` con los mismos filtros que la página; con cero resultados, una página vacía.
  - `app/modules/repuestos/`: `GET /repuestos?q=&page=&size=` (búsqueda por descripción con **parámetros ligados**), `GET /repuestos/{id}`, `POST /repuestos` (con `stock_inicial` → movimiento `"Stock inicial"`), `PATCH /repuestos/{id}` (descripción y precio; `stock` → 422), `DELETE /repuestos/{id}` (204 baja lógica), `POST /repuestos/{id}/reponer`, `GET /repuestos/{id}/movimientos`, `GET /repuestos/{id}/precios`.
  - `app/modules/clientes/`: `POST /clientes` (201/409/422), `GET /clientes/{id}` con sus vehículos (200/404), `POST /clientes/{id}/vehiculos` (201/404/409/422), `DELETE /vehiculos/{id}` (204/404/409), `GET /mis-vehiculos` (200, se protege en C-05).
  - Errores transversales: `IntegrityError` → **409** con mensaje propio (se inspecciona el nombre de la constraint, **nunca** un `SELECT` previo), 404 para el recurso de la ruta, 422 para contrato, ningún 500 con entrada inválida, `{id}` no entero → 422.
  - **Deuda declarada**: los services de C-03 usan `AsyncSession` directa; C-06 los migra a `Router → Service → UoW → Repository` **sin cambiar los contratos**. Queda anotado en cada `service.py` con `# TODO C-06`.
  - `seed.py` **completo de una sola vez** (dueño D): `DELETE` en orden inverso de FK (no `TRUNCATE`, que no dispara el trigger de fila), catálogo (4 estados) **primero**, 7 usuarios, 2 clientes (Laura con usuario y 2 vehículos; Jorge sin usuario y 1 vehículo), 4 repuestos con stock 10/4/2/20 como movimientos `"Stock inicial"`, órdenes 1 (`PENDIENTE`) y 2 (`EN_REPARACION`, 4 bujías con stock 2), historial de precio 8000 → 8500, evento `SISTEMA`.
- **Dependencias**: `C-02`
- **Governance**: **ALTO** — los contratos los consumen C-04…C-08; un cambio acá rompe cuatro changes.
- **Cubre**: `C-01` (id no entero → 422 sin ejecutar el handler) · `C-16` (búsqueda con `' OR '1'='1`, paginación filtrada, PATCH parcial, PATCH del stock) · `C-19` (baja lógica + misma patente)
- **Produce**: `app/modules/usuarios/schemas.py`, `clientes/{schemas,service,router}.py`, `repuestos/{schemas,service,router}.py`, `ordenes/schemas.py`, `app/core/paginacion.py`, `seed.py`, `test/c01_parametro_invalido.http`, `test/c16_busqueda_paginacion.http`, `test/c19_baja_vehiculo.http`.
- **Cierra con**:
  - [ ] `alembic upgrade head` sobre base vacía + `python seed.py` deja el estado exacto de `04_modelo_de_datos.md` §Seed data inicial (contar filas).
  - [ ] `C-01`, `C-16`, `C-19` en verde con la respuesta esperada comentada en cada archivo.
  - [ ] `python seed.py` corre dos veces seguidas y deja el mismo estado.
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §Épica 2 — Contratos y CRUD
  - `knowledge-base/08_arquitectura_propuesta.md` §Prohibiciones (las 16)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-18 y §RN-01
  - `knowledge-base/07_flujos_principales.md` §Flujo 8 — Reposición de stock y cambio de precio, y §Flujo 9 — Baja lógica
  - `knowledge-base/04_modelo_de_datos.md` §Seed data inicial

---

## FASE 2 — Primer fork: seguridad y dominio en paralelo

> Desde acá **sí** hay paralelismo real entre changes. `C-04` y el núcleo de `C-06` arrancan juntos en GATE 3; `C-05` y `C-07` se suman en GATE 4.

### [C-04] `ej4-autenticacion`

- **Estado**: `[ ]` pendiente
- **Ejercicio**: **Ej. 4** · **Peso**: 16 % · **Esfuerzo**: 11 h-persona
- **Dueño**: B (A ayuda con JWT y el registro del router en `main.py`)
- **Scope**:
  - `security.py` completo: bcrypt con costo desde `Settings`, **todas** las llamadas en `to_thread` y bajo `asyncio.Semaphore`; **hash calculado antes de abrir la transacción**; límite de **72 bytes** en todo campo que termina en bcrypt (login y contraseña actual incluidos) → **422**, no 500.
  - Login con el **orden innegociable**: (1) límite de intentos sobre `intento_acceso` (una consulta) → si hay 5+ fallos en 60 s, **429 + `Retry-After`** en pocos milisegundos **sin calcular ningún hash**; (2) verificación contra el hash del usuario **o contra el hash ficticio** precalculado en el lifespan; (3) emisión del token. Mismo cuerpo y tiempo parecido exista o no el correo. Un login correcto reinicia el conteo.
  - `intento_acceso` se anota (éxito o fallo) en **sesión y transacción propias**, que se confirman **siempre** — si no, `C-05` no puede pasar. El comentario de costo y la verificación quedan en C-07.
  - JWT HS256 con `sub`, `iat` (hora completa, **con fracciones**), `exp`, roles vigentes al emitir; viaja **sólo** en cookie `access_token` `HttpOnly`, `SameSite=Lax`, `Max-Age` = duración, `Secure` configurable; el cuerpo del login **no** trae el token; la dependencia lee `request.cookies` y `Authorization: Bearer` → **401**.
  - `POST /auth/registro` (usuario + `asignacion_rol` CLIENTE + `cliente` en **un solo UoW**; falla cualquiera → no queda ninguna fila; documento existente → 409 **sin apropiarse de la ficha**; `rol` en el cuerpo → 422), `POST /auth/logout` (borra cookie, idempotente), `GET /auth/yo` (usuario + roles vigentes + roles del token), `POST /auth/cambiar-password` (cookie nueva emitida **después** de escribir `password_cambiada_en`, `iat` sin truncar; contraseña actual incorrecta → 401).
- **Dependencias**: `C-03`
- **Governance**: **CRÍTICO** — auth es 16 % y el orden del login se pierde si se implementa "a ojo" (`R-03`).
- **Cubre**: `C-02` (registro atómico) · `C-03` (cookie) · `C-04` (mismo cuerpo y tiempo) · `C-05` (el sexto intento, 429 sin hash) · `C-09` (mitad: cambio de contraseña e invalidación inmediata)
- **Produce**: `app/core/security.py` (completo), `app/core/dependencies.py` (v1: `get_usuario_actual`), `app/modules/usuarios/{schemas,service,router}.py` (rutas `/auth`), `main.py` (registro del router `/auth` — edición pactada de A), `test/c02_registro.http`, `test/c03_cookie.http`, `test/c04_login_timing.http`, `test/c05_rate_limit.http`, `test/c09_cambio_obligatorio.http`.
- **Cierra con**:
  - [ ] `C-02`, `C-03`, `C-04`, `C-05` en verde.
  - [ ] `C-05`: el sexto intento responde 429 **en pocos ms** (medirlo) y los cinco fallos quedaron en `intento_acceso`.
  - [ ] `grep -r "Authorization" app/` solo aparece para **rechazarlo**; `grep -r "password_hash" app/modules/*/schemas.py` no devuelve nada.
  - [ ] `grep -rn "bcrypt\." app/` fuera de `to_thread` no devuelve nada.
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 1 — Login y §Flujo 7 — Cambio de contraseña
  - `knowledge-base/05_reglas_de_negocio.md` §RN-06, §RN-07, §RN-08, §RN-09 y §Límite de 72 bytes
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad
  - `knowledge-base/06_funcionalidades.md` §Épica 3 — Autenticación
  - `knowledge-base/10_preguntas_abiertas.md` §Q-06 y §Q-14

### [C-05] `ej5-autorizacion`

- **Estado**: `[ ]` pendiente
- **Ejercicio**: **Ej. 5** · **Peso**: 14 % · **Esfuerzo**: 9 h-persona
- **Dueño**: B
- **Scope**:
  - `get_usuario_actual` **final**: 401 sin cookie, token inválido/mal firmado/vencido, usuario inexistente o `activo = false`, y `iat` anterior a `password_cambiada_en` comparado **sin truncar**.
  - `requiere_rol(...)`: **403** con sesión válida; consulta `asignacion_rol` **en cada petición** (vigente = no revocada y no vencida); los roles del token **no habilitan nada**.
  - `POST /usuarios` (contraseña provisoria + `debe_cambiar_password = true`), `GET /usuarios/{id}/roles`, `POST /usuarios/{id}/roles` (`vence_en` con zona y en el futuro; sin zona o en el pasado → 422), `DELETE /usuarios/{id}/roles/{rol}` (escribe `revocada_en`, **no borra**; 200), reasignar un rol vencido cierra la fila anterior y abre una nueva.
  - **Autoprotección RN-05**: un admin no se revoca su propio ADMIN y la revocación que deja cero admins vigentes → **409**, comprobado en el servicio **antes** de escribir.
  - `main.py`: **dos grupos de rutas** — abierto (`/health`, `/auth`) y protegido (el resto) — con el control de `debe_cambiar_password` montado **una sola vez** en el protegido; `/auth/cambiar-password` sigue accesible. (Edición pactada de `main.py` con A.)
  - `GET /eventos` (ADMIN, paginado, 200/422) y escritura de `evento_seguridad` en altas, cambios de rol y de contraseña; el seed deja `actor = 'SISTEMA'` (texto, no usuario).
  - Lo propio: `/mis-vehiculos` y `/mis-ordenes` sólo piden autenticación; `GET /ordenes/{id}` con permiso fino **se implementa en C-06** (el módulo `ordenes/` es de D).
- **Dependencias**: `C-04`
- **Governance**: **ALTO** — 401 vs 403 y "403 antes que 409" es lo que más se rompe al copiar patrones (`R-05`).
- **Cubre**: `C-07` (revocación con sesión abierta, vencimientos inválidos, `/auth/yo`) · `C-08` (autoprotección) · `C-09` (resto: bloqueo 403 salvo `/auth`) · `C-17` (mitad autorización: sin sesión → 401) · `C-06` (**cierre conjunto en GATE 5**: necesita `GET /ordenes/{id}` de C-06)
- **Produce**: `app/core/dependencies.py` (final), `app/modules/usuarios/{schemas,service,router}.py` (personal, roles, eventos), `app/modules/clientes/router.py` (`/mis-vehiculos`), `main.py` (dos grupos), `test/c07_revocacion.http`, `test/c08_autoproteccion.http`, `test/c09_cambio_obligatorio.http` (cierre).
- **Cierra con**:
  - [ ] `C-07`, `C-08`, `C-09` y `C-17`(401) en verde.
  - [ ] La misma cookie que funcionaba deja de poder en la petición siguiente a la revocación (sin re-login).
  - [ ] `GET /eventos` con `?size=500` → 422 (usa la paginación de A).
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §RBAC — Matriz de permisos por recurso y §401 vs 403 — distinción obligatoria
  - `knowledge-base/05_reglas_de_negocio.md` §RN-04, §RN-05, §RN-06, §RN-12, §RN-17
  - `knowledge-base/07_flujos_principales.md` §Flujo 6 — Cancelar una orden y §Flujo 10 — Revocación de un rol
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad
  - `knowledge-base/10_preguntas_abiertas.md` §Q-04, §Q-05, §Q-12

### [C-06] `ej6-repositorios-uow`

- **Estado**: `[ ]` pendiente
- **Ejercicio**: **Ej. 6** · **Peso**: **20 %** · **Esfuerzo**: 14 h-persona
- **Dueño**: C y D en paralelo (A entrega `repository.py` y `unit_of_work.py` en GATE 3)
- **Scope**:
  - `app/core/repository.py`: `BaseRepository[T]` que recibe **sesión y clase del modelo** (los genéricos se borran en runtime) con `get_by_id`, `get_all`, `count`, `add`, `update`, `delete`; `add`/`update` hacen **`flush()`**, **nunca** `commit()`.
  - `SoftDeleteRepository[T]` **sólo** en `vehiculo` y `repuesto`: filtra los dados de baja y agrega `get_by_id_including_deleted` y `soft_delete`, que **no existen** en la base.
  - `app/core/unit_of_work.py`: gestor de contexto asincrónico — confirma al salir sin excepción, revierte con excepción, **no cierra** la sesión (no la creó) y **no la construye** (la recibe).
  - `*/unit_of_work.py` por módulo: compone los repositorios que sus operaciones necesitan, **todos con la misma sesión**. El **router** lo construye con una dependencia y lo pasa al servicio **sin abrirlo**; el **servicio** lo abre con `async with` y **nunca** lo construye.
  - **Refactor de C-03**: los services de `repuestos`, `clientes` y `usuarios` pasan de `AsyncSession` directa a UoW + repositorio **sin cambiar contratos ni códigos**.
  - Repositorio de sólo lectura del catálogo (`EstadoOrden`): **no hereda** de `BaseRepository`, expone solo `listar_por_posicion` y `get_by_codigo`.
  - **Punto único de escritura de stock**, usado por reposición y terminación (RN-14).
  - `ordenes/`: `POST /ordenes` (precio copiado, total calculado por el servidor, 1.ª línea de historial; repuesto inexistente → 409 **sin crear la orden**), `POST /ordenes/{id}/iniciar` (sólo `PENDIENTE`, asigna `mecanico_id`), `POST /ordenes/{id}/terminar` (mecánico asignado o ADMIN → 403; stock insuficiente → 409 **sin ninguna escritura**), `POST /ordenes/{id}/cancelar` (**403 antes que 409**), `GET /ordenes?estado=&page=&size=` (estado fuera del enum → 422), `GET /ordenes/{id}` (personal o dueño; ajeno → 403), `GET /estados-orden`, `GET /mis-ordenes`.
  - `PATCH /repuestos` con cambio de precio dentro del **mismo UoW** que el `historial_precio_repuesto` (RN-20); PATCH que no cambia el precio **no deja línea**; precio menor → **422** (o 409) validado en el servicio, nunca 500 (`IN-05`/`Q-10`).
- **Dependencias**: `C-04` (usuario actual) y `C-05` (`requiere_rol`, para el cableado final de permisos). Núcleo (`repository.py`, `unit_of_work.py`, UoW por módulo, refactor) **arranca en GATE 3** en paralelo con C-04.
- **Governance**: **CRÍTICO** — es el 20 % y el riesgo `R-02`: quién crea, abre, confirma y cierra la sesión se viola sin querer y arrastra auth, órdenes y stock.
- **Cubre**: `C-10` (alta + repuesto inexistente) · `C-11` (4 bujías, stock 2 → 409 sin escrituras) · `C-12` (mitad: reposición + término + movimientos + historial) · `C-13` (403 antes que 409) · `C-17` (422 del filtro de estado) · `C-18` (historial de precio + 403 de recepción)
- **Produce**: `app/core/repository.py`, `app/core/unit_of_work.py`, `app/modules/{usuarios,clientes,repuestos,ordenes}/{repository,unit_of_work}.py`, `app/modules/{repuestos,clientes,usuarios}/{service,router}.py` (refactor), `app/modules/ordenes/{service,router}.py`, `test/c10_alta_orden.http`, `test/c11_stock_insuficiente.http`, `test/c12_reponer_terminar.http`, `test/c13_cancelar.http`, `test/c17_catalogo.http`, `test/c18_precio_historial.http`.
- **Cierra con**:
  - [ ] `C-10` a `C-13` en verde + `C-17`(422) + `C-18`.
  - [ ] `grep -rn "\.commit()" app/modules/*/repository.py app/core/repository.py` → **vacío**.
  - [ ] `grep -rn "UnitOfWork(" app/modules/*/service.py` → **vacío** (el servicio no lo construye).
  - [ ] `C-11`: después del 409, `stock`, `movimiento_stock` e `historial_estado_orden` tienen exactamente las mismas filas que antes (contarlas).
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados (tabla "Reparto de responsabilidades")
  - `knowledge-base/06_funcionalidades.md` §Épica 5 — Repositorios y Unit of Work
  - `knowledge-base/07_flujos_principales.md` §Flujo 3 — Alta de orden, §Flujo 5 — Terminar una orden, §Flujo 6 — Cancelar
  - `knowledge-base/05_reglas_de_negocio.md` §RN-10 a §RN-14 y §RN-20
  - `knowledge-base/10_preguntas_abiertas.md` §Q-09, §Q-10 y §Q-16

---

## FASE 3 — Integridad y cierre

### [C-07] `ej7-integridad`

- **Estado**: `[ ]` pendiente
- **Ejercicio**: **Ej. 7** · **Peso**: 10 % · **Esfuerzo**: 5 h-persona
- **Dueño**: A (trigger/evidencia) + B (`intento_acceso`)
- **Scope**:
  - **Verificar** el trigger instalado en `0002_solo_agregado.py` sobre `historial_estado_orden`, `movimiento_stock` y `historial_precio_repuesto`: rechaza `UPDATE` y `DELETE` **venga de donde venga**, incluido `psql` con el rol de la aplicación.
  - `test/solo_agregado.sql`: los **6 rechazos** (update + delete × 3 tablas) listos para correr en `psql`, más el intento de insertar una orden con un estado fuera del catálogo que debe fallar por **clave foránea**.
  - Evidencia `C-14`: captura de `psql` con los 6 rechazos + el de la FK.
  - `intento_acceso` en **sesión y transacción propias**, confirmadas **siempre**: revisar lo que dejó C-04, dejar el **comentario de costo** en el código ("deja filas aunque la petición falle") y, si C-04 lo dejó dentro de la transacción de la petición, **moverlo** (checklist obligatorio: es el único punto que la consigna marca como "la única escritura que no comparte su transacción").
  - Historial de precio en la **misma transacción** que el cambio de precio: verificado, no reimplementado.
  - **No se crean migraciones nuevas**: la consigna pide dos. Si el trigger necesita un ajuste, se corrige `0002` con A antes del merge de C-02.
- **Dependencias**: `C-02` (trigger) y `C-04` (`intento_acceso`)
- **Governance**: **ALTO** — la garantía de sólo agregado no puede depender de la aplicación; es lo que el corrector prueba desde `psql`.
- **Cubre**: `C-14` (completo) · `C-05` (resto: los cinco fallos quedan registrados pese a los 401)
- **Produce**: `test/solo_agregado.sql`, `test/c14_solo_agregado.http`, `app/modules/usuarios/service.py` (ajuste del registro de intentos + comentario), evidencia `C-14` en el README (texto/captura).
- **Cierra con**:
  - [ ] Los **6** `UPDATE`/`DELETE` rechazados por el trigger, ejecutados a mano en `psql`.
  - [ ] `INSERT` de una orden con estado inexistente → error de **FK**, no del trigger.
  - [ ] `alembic downgrade base` borra función y trigger; `upgrade head` los vuelve a crear.
  - [ ] Los 5 fallos de `C-05` están en `intento_acceso` **y siguen ahí** después de los 401.
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §RN-15 (sólo agregado por disparador)
  - `knowledge-base/07_flujos_principales.md` §Flujo 1 — Login (paso 7: `intento_acceso`) y §Flujo 5 — Terminar una orden
  - `knowledge-base/08_arquitectura_propuesta.md` §Migraciones
  - `knowledge-base/06_funcionalidades.md` §Épica 6 — Integridad
  - `knowledge-base/10_preguntas_abiertas.md` §Q-15

### [C-08] `ej8-n-plus-1-asincronia`

- **Estado**: `[ ]` pendiente
- **Ejercicio**: **Ej. 8** · **Peso**: 8 % · **Esfuerzo**: 9 h-persona
- **Dueño**: A y D (D es dueño de `README.md` y de `ordenes/`)
- **Scope**:
  - **Precarga declarada en el repositorio** (no en el servicio): `selectinload`/`joinedload` adentro del método que la necesita. Ninguna lectura depende de carga perezosa.
  - `GET /ordenes/{id}` con **número fijo de consultas**: vehículo, cliente, ítems, repuesto de cada ítem e historial; `C-15` exige la **misma cantidad** con 2 y con 4 ítems.
  - Todos los handlers `async def`; auditoría con `grep` de llamadas bloqueantes (sin `requests`, sin `time.sleep`, sin bcrypt fuera de `to_thread`).
  - `POST /ordenes/{id}/terminar` agenda `BackgroundTasks`: `await asyncio.sleep(0.5)` + mensaje en el registro, **después** de la respuesta y **sólo si la transacción se confirmó**.
  - `seed.py`: verificación de idempotencia (correrlo 3 veces). **No se reescribe lo que hizo C-03**; si falta la orden con 4 ítems para `C-15`, se genera por API en el propio caso, no se toca el seed.
  - `README.md`: pasos **desde cero** (venv, dependencias, `.env` y **cómo generar la clave de firma** con `python -c "import secrets; print(secrets.token_urlsafe(64))"`, `alembic upgrade head`, `python seed.py`, arranque), evidencias `C-14` y `C-15` y la aclaración de que `.env` no se versiona.
  - **Corrida completa de los 19 casos** desde cero, en una máquina limpia, con `python seed.py` antes de cada archivo.
- **Dependencias**: `C-06` (precarga y órdenes) y `C-04` (aviso al terminar)
- **Governance**: **MEDIO** — el riesgo `R-06` (N+1 con consultas que crecen con los ítems) es de 8 % pero **visible** en la consola; si no se mide desde el día 1, se descubre el día 4.
- **Cubre**: `C-15` (consultas fijas) · `C-12` (resto: el aviso sale en el registro **después** de la respuesta)
- **Produce**: `*/repository.py` (precarga en los métodos de detalle), `app/modules/ordenes/{service,router}.py` (BackgroundTasks), `README.md`, `test/c15_detalle_sin_n_plus_1.http`, evidencias `C-14`/`C-15`.
- **Cierra con**:
  - [ ] `C-15`: con `SQL_ECHO=true`, el detalle de una orden de 2 ítems y de una de 4 emite **la misma cantidad** de consultas (contarlas en la salida).
  - [ ] `C-12`: el mensaje del aviso aparece **después** de la respuesta (se ve en la consola) y **no** aparece si la terminación falló.
  - [ ] `README.md` permite levantar el proyecto desde cero en una máquina que nunca lo vio.
  - [ ] **Los 19 casos pasan** en una corrida limpia; `.env` no está en el repo; `alembic upgrade head` sobre base vacía vuelve a funcionar.
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §Épica 7 — Lecturas sin N+1 y asincronía
  - `knowledge-base/07_flujos_principales.md` §Flujo 5 — Terminar una orden (paso 4: el aviso)
  - `knowledge-base/08_arquitectura_propuesta.md` §Estrategia de pruebas
  - `knowledge-base/09_decisiones_y_supuestos.md` §SU-05 (los `.http` alcanzan) y §DD-09 (`seed.py` es parte de la puesta en marcha)
  - `knowledge-base/06_funcionalidades.md` §Épica 8 — Datos iniciales y entrega

---

## Resumen

| Change | Ejercicio | Peso | Horas | Gobernanza | Depende de | Dueño | Casos `C-XX` |
|---|---|---|---|---|---|---|---|
| `C-00` | setup del entorno | 0 % | 5 h | ALTO | — | A | — |
| `C-01` | Ej. 1 — config y ciclo de vida | 8 % | 6 h | CRÍTICO | C-00 | A | — |
| `C-02` | Ej. 2 — modelos y migraciones | 14 % | 12 h | CRÍTICO | C-01 | A + B/C/D | C-14 (instala), C-17, C-19 (esquema) |
| `C-03` | Ej. 3 — contratos y CRUD | 10 % | 9 h | ALTO | C-02 | C + D + B + A | C-01, C-16, C-19 |
| `C-04` | Ej. 4 — autenticación | 16 % | 11 h | CRÍTICO | C-03 | A + B | C-02, C-03, C-04, C-05, C-09 |
| `C-05` | Ej. 5 — autorización | 14 % | 9 h | ALTO | C-04 | B | C-06, C-07, C-08, C-09, C-17 |
| `C-06` | Ej. 6 — repositorios y UoW | **20 %** | 14 h | CRÍTICO | C-04, C-05 | C + D | C-10, C-11, C-12, C-13, C-17, C-18 |
| `C-07` | Ej. 7 — integridad | 10 % | 5 h | ALTO | C-02, C-04 | A + B | C-14, C-05 (registro) |
| `C-08` | Ej. 8 — N+1 y asincronía | 8 % | 9 h | MEDIO | C-06, C-04 | A + D | C-15, C-12 (aviso) |
| **Total** | **8 ejercicios** | **100 %** | **80 h** | — | — | 4 personas | **19/19** |

### Presupuesto de horas contra el plazo

- **Capacidad**: 4 personas × 4 días × **6 h efectivas/día** = **96 h-persona**. (La consigna de esta fase menciona "48 hs-persona"; el cálculo con 6 h/día da 96. Con 3 h/día daría 48, y ahí el roadmap **no cerraría**: hacen falta 80 h. Se calibra en **96**, con 6 h efectivas.)
- **Estimado**: **80 h-persona** = **83 %** de la capacidad → **16 h de colchón (17 %)**.
- **El colchón no está repartido**: la cadena `C-00 → C-03` consume 32 h con **4 personas serializadas** (utilización ~67 %: config y migraciones no se paralelizan 4×); el fork `C-04 → C-08` consume 48 h sobre 48 h disponibles = **100 % de utilización**. Es decir: **el total cierra, pero los días 3 y 4 no tienen margen**. Cualquier desvío en `C-04` o `C-06` se paga con el recorte de abajo, no con el colchón.
- **Si el total no cierra** (por ejemplo, si el equipo dispone de 3 h efectivas/día = 48 h): no se recorta por ejercicios —eso rompe la restricción de un change por ejercicio— se recorta **en este orden**:
  1. **Pulido de entregables**: evidencias `C-14`/`C-15` en texto crudo de consola (siguen existiendo, dejan de estar "lindas") y README sin capturas.
  2. **Consolidación de `.http`**: los 19 casos se agrupan en 8 archivos (uno por ejercicio) con `# @name` por caso. **Ningún caso se cae**; solo se juntan archivos.
  3. **Extras no evaluados de `C-08`**: se conserva la precarga + `C-15` + `BackgroundTasks` y se elimina la auditoría de handlers uno por uno (se reemplaza por el `grep`).
  4. **Último recurso**: `C-07` entrega `C-14` con la salida manual de `psql` sin archivo `.sql` comentado.
  - **Nunca se recorta**: `C-00`/`C-01` (arranque), `C-02` (13 tablas, 3 índices, trigger), el orden del login de `C-04` y el UoW de `C-06`. Son las cuatro cosas que la cátedra mira primero y las que anulan la corrección si faltan.

### Primer change recomendado

`C-00` (`setup-entorno-local`). No escribe negocio, pero es el que decide si el día 1 se pierde en instalar PostgreSQL o en codificar. Arrancarlo con `Q-02` y `Q-01` resueltas en los primeros 10 minutos.

Para arrancar: `/opsx:propose C-00-setup-entorno-local`
