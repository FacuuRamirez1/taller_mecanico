# Proposal

## Why

C-00 dejó el entorno listo pero la aplicación no existe: `main.py` es un marcador, `app/core/config.py` no existe y por eso `migrations/env.py` (que ya importa `Settings`) falla con `ModuleNotFoundError`. El Ej. 1 de la consigna (8 %) exige configuración leída del entorno **sin secretos por defecto**, motor y `sessionmaker` creados en el lifespan, sesión por petición y salud `live`/`ready`. Es el primer eslabón del camino crítico: sin C-01 no hay `alembic upgrade head` (C-02), ni `seed.py` (C-03), ni hash ficticio para el login (C-04).

## What Changes

- **Nuevo `app/core/config.py`**: clase `Settings` (pydantic-settings) con las 12 variables setables de `env.example` y `DATABASE_URL` calculada con `@computed_field` (driver `postgresql+asyncpg`). `JWT_SECRET_KEY` y `POSTGRES_PASSWORD` **sin default** y además rechazadas si llegan vacías o con el placeholder de `env.example`: si faltan, la app **no arranca**. `POSTGRES_PORT` se lee del entorno sin hardcodear (5432 en `env.example`, 5433 en la máquina del proponente vía `.env` local).
- **Nuevo `app/core/database.py`**: `crear_engine(settings)` y `crear_sessionmaker(engine)` (sólo los llama el lifespan) y `get_session` que toma la fábrica de `request.app.state`, abre la sesión con `expire_on_commit=False`, **no** hace `commit` y la cierra al terminar la petición; alias `SessionDep`.
- **`main.py` deja de ser marcador**: `FastAPI(lifespan=...)` cuyo startup lee `Settings`, crea motor + fábrica dentro del bucle y los guarda en `app.state`, calcula **una vez** el hash ficticio; el shutdown hace `engine.dispose()`. Importar `main` no construye ningún recurso.
- **Nuevo `app/core/security.py` mínimo**: `hash_password` / `verify_password` ejecutados con `asyncio.to_thread` bajo un `asyncio.Semaphore`, costo tomado de `Settings`. JWT y cookie quedan para C-04.
- **Nuevo `app/modules/health/router.py`**: `GET /health/live` → 200 sin tocar la base; `GET /health/ready` → `SELECT 1` con timeout; 200 si contesta, **503** con mensaje propio si no.
- **`migrations/env.py`**: se retira el `TODO C-01`; la URL de `Settings` se escapa para el `configparser` de Alembic (`%` → `%%`). `alembic current` pasa a conectar sin credenciales en `alembic.ini`.
- **Nuevo `test/salud.http`**: pedidos REST Client de `live`/`ready` con la respuesta esperada comentada (no es un caso `C-XX`; se nombra `salud` para no confundirlo con el caso `C-01` de la consigna).
- Queda como **ítem abierto** (no se cambia en silencio) el pin `fastapi[standard]==0.111.1`: el extra `standard` no existe en esa versión y `pip` lo advierte.

## Capabilities

### New Capabilities
- `configuracion-aplicacion`: contrato de `Settings` — variables leídas del entorno/`.env`, URL calculada, secretos obligatorios sin default y rechazo de valores vacíos o de ejemplo.
- `ciclo-vida-aplicacion`: lifespan (motor, fábrica de sesiones y hash ficticio creados en el startup y liberados en el shutdown), nada construido al importar, y sesión por petición sin `commit`.
- `salud-servicio`: chequeos `GET /health/live` y `GET /health/ready` con sus códigos 200/503.
- `hash-contrasenas`: hash y verificación bcrypt fuera del bucle de eventos (`to_thread` + semáforo) con costo configurable. C-04 la extiende.

### Modified Capabilities
- `entorno-desarrollo-local`: (1) Alembic deja de estar "pendiente de C-01" y MUST conectar usando `Settings`; (2) `main.py` deja de ser marcador (sólo `seed.py` sigue con `TODO C-03`); (3) el puerto de PostgreSQL deja de estar fijado en 5432 y se toma de `POSTGRES_PORT`.

## Impact

- **Código nuevo**: `app/core/config.py`, `app/core/database.py`, `app/core/security.py`, `app/modules/health/router.py`, `main.py`, `test/salud.http`.
- **Código modificado**: `migrations/env.py` (escape de `%` y retiro del TODO). `alembic.ini` y `env.example` no cambian.
- **Local, no versionado**: `.env` de cada integrante (ya existe desde C-00; no se lee ni se toca desde los artefactos).
- **API**: dos endpoints públicos, `/health/live` y `/health/ready`.
- **Dependencias**: ninguna nueva. Posible ajuste de `requirements.txt` (`fastapi[standard]` → `fastapi`) sujeto a decisión del equipo.
- **Governance CRÍTICO**: arranque y secretos. Una credencial real en el repo anula la corrección; cada task de cierre incluye la verificación de higiene.
- **Desbloquea**: C-02 (`alembic upgrade head`), C-03 (`seed.py` con la sesión), C-04 (hash ficticio y `security.py`) y C-15 (`SQL_ECHO`).
