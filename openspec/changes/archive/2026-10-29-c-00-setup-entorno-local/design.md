# Design

## Context

Ver `proposal.md` para la motivación. El estado actual del repositorio es sólo documentación: existen `knowledge-base/`, `CHANGES.md`, `AGENTS.md`, `CLAUDE.md`, `.atl/skill-registry.md` y la raíz de OpenSpec, pero **no hay** `app/`, `main.py`, `seed.py`, `requirements.txt`, `alembic.ini` ni `migrations/`. No hay historial de aplicación que preservar: C-00 es el primer change.

Restricciones que moldean el diseño:

- Stack obligatorio con versiones mínimas (ver `AGENTS.md` §Stack). PostgreSQL 16 **local, sin Docker** (`DD-08`).
- Arquitectura obligatoria Router → Service → UoW → Repository → Model por módulo; C-00 sólo prepara el árbol, no la implementa.
- Reglas duras: el esquema nace **sólo** de Alembic (`create_all` prohibido), ningún secreto con default en el código ni en `alembic.ini`, `.env` nunca versionado.
- Verificación: **sin pytest ni CI**. La aceptación de C-00 son las tres comprobaciones de "Cierra con"; desde C-01 los casos `test/*.http` son la puerta de aceptación.
- El CLI de OpenSpec exige nombres de change en minúsculas: el change se llama `c-00-setup-entorno-local` (el bloque de `CHANGES.md` se sigue citando como `C-00`).

## Goals / Non-Goals

**Goals:**

- Dejar las 4 máquinas con un entorno idéntico y reproducible: mismo Python, mismas dependencias pinneadas, misma base, mismas variables.
- Dejar `alembic.ini` + `migrations/env.py` listos para que C-01 complete `Settings` y C-02 genere la primera migración, sin reescribir la configuración.
- Garantizar que ningún secreto real pueda entrar al repositorio por accidente.
- Dejar el árbol de carpetas de la consigna creado y sin lógica de negocio.

**Non-Goals:**

- Implementar `Settings`, `database.py`, `security.py`, `main.py` o `seed.py` (C-01 / C-03).
- Crear tablas, modelos o revisiones de Alembic (C-02).
- Ejecutar `alembic upgrade head`: no hay revisiones ni `Settings` todavía.
- Docker, pytest, CI, `README.md` final (C-08) o cualquier endpoint.

## Decisions

### D1 — `alembic.ini` sin URL y `env.py` que falla fuerte hasta C-01

`alembic.ini` se crea con `script_location = %(here)s/migrations`, `prepend_sys_path = .` y `path_separator = os`, y **sin la clave `sqlalchemy.url`** (se elimina la línea, no se deja comentada con un valor de ejemplo, para que nadie la "complete" con credenciales). Las secciones de logging se conservan.

`migrations/env.py` sigue la plantilla asincrónica y, en el nivel superior, hace:

```python
from app.core.config import Settings   # se completa en C-01

settings = Settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
```

Como `app.core.config` no existe todavía, **cualquier comando de Alembic que cargue `env.py` falla con `ModuleNotFoundError` hasta que C-01 cree el módulo**. Es intencional y se documenta en tres lugares: el propio `env.py` (comentario `TODO C-01`), el header de `env.example` y `tasks.md`. El resto del archivo (`run_migrations_offline`, `run_async_migrations` con `async_engine_from_config` y `asyncio.run`, `target_metadata = SQLModel.metadata` con `TODO C-02` para importar los modelos) queda completo.

**Alternativas descartadas:**

- Leer `DATABASE_URL` directo de `os.environ` en `env.py`: duplica el contrato de `Settings` y permite que la URL de la app y la de Alembic diverjan.
- `try/except ImportError` con una URL de fallback: introduce un default de conexión, justo lo que la consigna prohíbe, y esconde que C-01 no se hizo.
- Dejar `env.py` con un placeholder y completarlo en C-01: contradice el Scope de C-00 ("se deja el import y se completa al día siguiente") y obliga a reescribir el archivo.

### D2 — `requirements.txt` derivado de las versiones mínimas, pinneado con `==`

La regla de derivación es: **una línea por dependencia directa, pinneada a la última revisión de la línea mínima exigida por la consigna**, sin rangos (`>=`) y sin `~=`. Se verificaron las versiones disponibles en PyPI al proponer.

| Línea | Mínimo de la consigna | Pin propuesto | Por qué |
|---|---|---|---|
| `fastapi[standard]` | 0.111 | `0.111.1` | última revisión de la línea mínima; el extra `standard` trae uvicorn |
| `SQLModel` | 0.0.24 | `0.0.24` | es la única versión de esa línea |
| `SQLAlchemy` | 2.0 async | `2.0.55` | última 2.0.x; SQLModel 0.0.24 exige `<2.1` |
| `asyncpg` | 0.30 | `0.30.0` | línea mínima exacta |
| `alembic` | 1.13 | `1.13.3` | última 1.13.x |
| `pydantic-settings` | 2.0 | `2.0.3` | última 2.0.x |
| `bcrypt` | 4.0 | `4.0.1` | última 4.0.x; wheels `abi3` compatibles con 3.12 |
| `PyJWT` | 2.8 | `2.8.0` | línea mínima exacta |
| `uvicorn[standard]` | (vía fastapi) | `0.30.6` | se explicita para que el servidor también quede pinneado |
| `pydantic` | (transitiva) | `2.8.2` | pin de compatibilidad con `pydantic-settings 2.0.3`; evita que un salto mayor lo rompa |

En `tasks.md` la primera tarea de instalación verifica la resolución con `pip install --dry-run -r requirements.txt`. Si un pin no existe para la plataforma, se sube al siguiente parche **dentro de la misma línea**, nunca por debajo del mínimo. No se agrega `requirements.lock.txt` (no está en el Scope); si hace falta reproducibilidad bit a bit, `pip freeze` es evidencia local, no un archivo versionado.

**Alternativa descartada:** `>=` con mínimos sueltos. Deja que cada máquina instale un árbol distinto y rompe la condición de "4 máquinas idénticas".

### D3 — `env.example` como contrato único de las 13 variables

`env.example` lista las 13 variables de `08_arquitectura_propuesta.md` §Variables de entorno, con valores de ejemplo y **sin ningún secreto**. `DATABASE_URL` se incluye **comentada** con la leyenda "calculada con `@computed_field`; no se escribe en `.env`": es la 13.ª variable del contrato, pero si se pudiera setear competiría con la URL derivada de `POSTGRES_*`.

Los dos secretos (`POSTGRES_PASSWORD`, `JWT_SECRET_KEY`) llevan placeholders explícitos (`CAMBIAR_EN_TU_.env` / vacío), nunca el valor acordado en Q-02. `JWT_SECRET_KEY` no tiene default en el código: `Settings` (C-01) la declara obligatoria y la app no arranca si falta.

### D4 — El contrato de arranque vive en el header de `env.example`

`CHANGES.md` pide "un documento de 5 líneas en el mensaje fijado del canal". No se agrega un archivo extra (el Scope enumera exactamente los artefactos de C-00 y `README.md` es propiedad del carril D en C-08). Las 5 líneas se escriben como comentario al inicio de `env.example` —el archivo que las 4 personas copian— y se pegan tal cual en el mensaje fijado del canal:

```
# 1) URL: postgresql+asyncpg://postgres:<password-local>@localhost:5432/taller_mecanico
# 2) Venv: python -m venv .venv && source .venv/Scripts/activate
# 3) Arranque: uvicorn main:app --reload        (desde C-01)
# 4) Migrar: alembic upgrade head               (desde C-01)
# 5) Seed: python seed.py                       (desde C-03)
```

La URL versionada usa `<password-local>`; el valor real sólo existe en el canal y en el `.env` de cada máquina.

### D5 — Creación de la base: rol único, sin Docker

Se usa el rol `postgres` de la instalación local (un solo rol de base, `DD-07`: no hay segundo mecanismo de sólo-agregado por permisos) y se crea la base `taller_mecanico` con dueño `postgres`. Comandos de referencia para el apply: `CREATE DATABASE taller_mecanico OWNER postgres;` ejecutado desde `psql -U postgres`, con la contraseña pedida por prompt (nunca en la línea de comandos, para no dejarla en el historial). `\dt` debe devolver "Did not find any relations": C-00 no crea tablas.

### D6 — `.gitignore` mínimo y explícito, creado primero

Se escribe `.gitignore` **antes** que `.env` para que el archivo de secretos nunca llegue a estar "untracked visible". Contenido: `.env`, `.venv/`, `__pycache__/`, `*.py[cod]`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `*.egg-info/`. No se ignora `env.example` (nombre distinto de `.env`, no hace falta negación) ni `migrations/`.

### D7 — Árbol de carpetas con `__init__.py` y placeholders `TODO`

`app/__init__.py`, `app/core/__init__.py`, `app/modules/__init__.py` y un `__init__.py` por módulo (`health`, `usuarios`, `clientes`, `repuestos`, `ordenes`). `app/modules/__init__.py` no figura explícitamente en el diagrama de la KB pero es necesario para que `app.modules.health` sea importable como paquete; agregarlo no altera la estructura obligatoria.

`main.py` contiene sólo `# TODO C-01: aplicación FastAPI, lifespan y grupos de rutas`. `seed.py` contiene sólo `# TODO C-03: estado inicial conocido`. Ninguno define código ejecutable, imports ni constantes.

`migrations/versions/.gitkeep` mantiene la carpeta en los 4 clones (git no versiona directorios vacíos). Se considera "vacío" en el sentido de **sin revisiones**, que es lo que exige la consigna.

### D8 — Orden de ejecución y verificación (TDD en forma de verificación)

C-00 no tiene comportamiento de negocio que testear, así que el ciclo TDD se aplica a las comprobaciones de cierre: cada tarea de verificación es un check **ejecutable** con salida esperada, que está en RED antes de la tarea correspondiente y en GREEN después. Orden (de más barato a más caro, y de "peligro de secreto" a "infraestructura"):

1. **V0 — Higiene del repositorio** (bloquea todo): `git status --porcelain` no lista `.env`; `git check-ignore -v .env` lo confirma; `grep -i "password\|secret" env.example` no devuelve valores reales.
2. **V1 — Contrato estático**: `alembic.ini` sin `sqlalchemy.url`; `migrations/env.py` importa `Settings` y usa motor asincrónico; no hay `create_all`; el árbol y los `TODO` existen.
3. **V2 — Instalación e imports (4/4 máquinas)**: `pip install -r requirements.txt` y `python -c "import fastapi, sqlmodel, alembic, asyncpg"`.
4. **V3 — Base**: `psql ... -c "select version()"` responde 16; `\dt` sin relaciones.
5. **V4 — Reconfirmación de V0** después de crear el `.env` real (es el momento en que el riesgo de filtrar la contraseña es máximo).

V0 se corre primero y último a propósito. Nada de `pytest`: desde C-01 la aceptación pasa a ser los archivos `test/*.http` con la respuesta esperada comentada.

## Risks / Trade-offs

- **[Credencial real en el repositorio → anula la corrección del TP]** → `.gitignore` primero, `.env` sólo local, `env.example` con placeholders, y V0/V4 como checks ejecutables. Si alguna vez se commitea, se rota la contraseña y se limpia el historial **antes** de la entrega.
- **[`env.py` no corre hasta C-01 → parece "roto" el día 1]** → falla con `ModuleNotFoundError` inmediato y explicable; está anotado en `env.py`, en `env.example` y en `tasks.md`, y C-01 arranca creando `app/core/config.py`. Se prefiere un fallo ruidoso a un fallback con credenciales.
- **[Un pin no resuelve en alguna máquina (rueda nativa, Python 3.12)]** → verificación con `pip install --dry-run` antes de instalar; si falla, subir el parche dentro de la misma línea, nunca bajar del mínimo. `bcrypt 4.0.1` publica wheels `abi3` y `asyncpg 0.30.0` soporta 3.12.
- **[Pydantic transitivo incompatible con `pydantic-settings 2.0.3`]** → pin explícito `pydantic==2.8.2`; el dry-run de V2 lo confirma.
- **[Las 4 máquinas difieren en PostgreSQL (versión/menor/locale)]** → `select version()` debe decir 16 en las 4; el contrato de arranque fija host, puerto, usuario y base.
- **[`migrations/versions/` vacío no sobrevive al clonado]** → `.gitkeep`, documentado como "sin revisiones", no como contenido.
- **[El header de `env.example` se desactualiza respecto del contrato del canal]** → el header es la copia canónica versionada; el mensaje fijado se pega desde él, no al revés.
- **Trade-off aceptado**: C-00 no se puede validar con un comando único ("arranca y responde 200") porque todavía no hay app; la señal es la suma de V0–V4. Es el precio de no escribir código de negocio en la fase 0.

## Migration Plan

1. A crea el rol/base local y los archivos en el orden: `.gitignore` → `env.example` → `requirements.txt` → `alembic.ini` → `migrations/` → árbol `app/` y `test/` → `main.py`/`seed.py` → `.env` local.
2. B, C y D clonan, crean su `.venv`, copian `env.example` a `.env` y completan los dos secretos.
3. Cada integrante corre V0–V3 en su máquina y reporta en el canal; A consolida 4/4.
4. Rollback (no hay datos): borrar `.venv` y `.env`, `DROP DATABASE taller_mecanico;` y repetir. No hay migraciones ni tablas que deshacer.
5. Al cerrar: `/opsx-archive` y marcar `[C-00]` como `[x]` en `CHANGES.md` (eso lo hace el cierre del change, no este propose).

## Open Questions

- **Q-19** (método para generar la clave de firma) sigue siendo P2 y se documenta en el `README` de C-08. Mientras tanto, el valor local de `JWT_SECRET_KEY` se genera con `python -c "import secrets; print(secrets.token_urlsafe(64))"` y no se versiona. No cambia specs, enfoque ni tareas.
- **Nota de consistencia (no bloqueante)**: la tabla de bloqueantes de `CHANGES.md` asigna `Q-01` a C-01; el usuario ya fijó el nombre `JWT_SECRET_KEY`, así que C-00 lo refleja en `env.example` y C-01 sólo implementa `Settings`. No se modifica `CHANGES.md` en este change.
