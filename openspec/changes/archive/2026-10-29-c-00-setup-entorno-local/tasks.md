# Tasks

> C-00 no tiene comportamiento de negocio: el ciclo TDD se aplica en su forma de verificación. Cada tarea trae el comando y la salida esperada; una verificación en rojo es el estado RED y sólo pasa a GREEN cuando el artefacto existe y el comando sale como se indica. **No hay pytest**: desde C-01 la aceptación son los `test/*.http`.
>
> Convención: `psql` pide la contraseña por prompt. Nunca se escribe el valor real de `POSTGRES_PASSWORD` ni de `JWT_SECRET_KEY` en un archivo versionado ni en la línea de comandos.

## 1. Higiene del repositorio y contrato de configuración

- [x] 1.1 Crear `.gitignore` con `.env`, `.venv/`, `__pycache__/`, `*.py[cod]`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/` y `*.egg-info/`, **antes** de crear el `.env`. Verificar: `git check-ignore -v .env` imprime la regla `.gitignore` que lo ignora y termina con código 0.
- [x] 1.2 Crear `env.example` con las 13 variables de `08_arquitectura_propuesta.md` §Variables de entorno: las 12 setables con valores de ejemplo (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_EXPIRE_SECONDS`, `BCRYPT_COST`, `DB_POOL_SIZE`, `SQL_ECHO`, `COOKIE_SECURE`) y `DATABASE_URL` **comentada** como calculada con `@computed_field`. Verificar: `grep -E "^[A-Z_]+=|^# *DATABASE_URL" env.example | wc -l` devuelve 13 y `grep -i "password\|secret" env.example` sólo muestra nombres de claves con placeholders (`CAMBIAR_EN_TU_.env` o vacío), sin valores reales.
- [x] 1.3 Escribir el contrato de arranque de 5 líneas como header de `env.example` (URL con `<password-local>`, activación del venv, `uvicorn main:app --reload`, `alembic upgrade head`, `python seed.py`) y pegar el mismo bloque en el mensaje fijado del canal. Verificar: `grep -c "^# [1-5])" env.example` devuelve 5 y las líneas 3–5 coinciden textualmente con el mensaje fijado.
- [x] 1.4 Crear el `.env` local copiando `env.example` y completar sólo `POSTGRES_PASSWORD` y `JWT_SECRET_KEY` (clave generada con `python -c "import secrets; print(secrets.token_urlsafe(64))"`). Verificar: `grep -E "^(POSTGRES_PASSWORD|JWT_SECRET_KEY)=.+" .env` devuelve las dos variables no vacías y `git status --porcelain` no muestra `.env`.

## 2. Dependencias y entorno virtual

- [x] 2.1 Crear `requirements.txt` pinneado con `==` según la tabla de `design.md` §D2: `fastapi[standard]==0.111.1`, `SQLModel==0.0.24`, `SQLAlchemy==2.0.55`, `asyncpg==0.30.0`, `alembic==1.13.3`, `pydantic-settings==2.0.3`, `bcrypt==4.0.1`, `PyJWT==2.8.0`, `uvicorn[standard]==0.30.6`, `pydantic==2.8.2`. Verificar: `grep -c "==" requirements.txt` devuelve 10 y ninguna versión queda por debajo del mínimo de la consigna.
- [x] 2.2 Crear el entorno virtual con Python 3.12 y validar la resolución de pines antes de instalar. Verificar: `python -m venv .venv && source .venv/Scripts/activate && python --version` reporta `3.12.x`, y `pip install --dry-run -r requirements.txt` termina sin conflicto de dependencias.
- [x] 2.3 Instalar el stack y correr el smoke de imports (primera comprobación de "Cierra con"). Verificar: `pip install -r requirements.txt` termina con código 0 y `python -c "import fastapi, sqlmodel, alembic, asyncpg"` termina con código 0 y sin error.

## 3. Base PostgreSQL 16 local (sin Docker)

- [x] 3.1 Confirmar PostgreSQL 16 instalado y servidor local arriba (segunda comprobación de "Cierra con", parte 1). Verificar: `psql -h localhost -p 5432 -U postgres -c "select version()"` responde con el prompt de contraseña y la salida contiene `PostgreSQL 16`.
- [x] 3.2 Crear la base `taller_mecanico` con dueño `postgres` (rol único) sin Docker. Verificar: `psql -h localhost -U postgres -d taller_mecanico -c "\conninfo"` conecta y muestra `database: taller_mecanico`; `psql -h localhost -U postgres -lqt` lista la base.
- [x] 3.3 Confirmar que C-00 no crea esquema. Verificar: `psql -h localhost -U postgres -d taller_mecanico -c "\dt"` responde `Did not find any relations` (cero tablas, cero modelos, cero `create_all`).

## 4. Configuración de Alembic (asincrónica, sin credenciales)

- [x] 4.1 Crear `alembic.ini` con `script_location = %(here)s/migrations`, `prepend_sys_path = .`, `path_separator = os` y las secciones de logging, **sin** la clave `sqlalchemy.url`. Verificar: `grep -n "sqlalchemy.url" alembic.ini` no devuelve nada y `grep -n "script_location\|prepend_sys_path" alembic.ini` devuelve ambas claves.
- [x] 4.2 Crear `migrations/env.py` con la plantilla asincrónica: `from app.core.config import Settings` en el nivel superior (con `TODO C-01`), `config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)`, `run_migrations_offline`, `run_async_migrations` con `async_engine_from_config` + `asyncio.run`, y `target_metadata = SQLModel.metadata` con `TODO C-02` para importar los modelos. Verificar: `grep -n "from app.core.config import Settings\|async_engine_from_config\|TODO C-01\|TODO C-02" migrations/env.py` devuelve las cuatro marcas, y `alembic current` falla con `ModuleNotFoundError: No module named 'app.core.config'` (fallo esperado y documentado hasta C-01).
- [x] 4.3 Crear `migrations/script.py.mako` y dejar `migrations/versions/` sin revisiones (`migrations/versions/.gitkeep` para que la carpeta exista en los 4 clones). Verificar: `test -f migrations/script.py.mako` y `grep -c "revision" migrations/script.py.mako` devuelve al menos 1; `find migrations/versions -name "*.py" | wc -l` devuelve 0 y `find migrations/versions -type f` sólo lista `.gitkeep`.

## 5. Árbol de carpetas y placeholders

- [x] 5.1 Crear `app/__init__.py`, `app/core/__init__.py`, `app/modules/__init__.py` y `app/modules/{health,usuarios,clientes,repuestos,ordenes}/__init__.py`, más `test/` (con `.gitkeep`). Verificar: `find app -name "__init__.py" | wc -l` devuelve 8 y `test -d test` sale con código 0.
- [x] 5.2 Crear `main.py` con sólo `# TODO C-01: aplicación FastAPI, lifespan y grupos de rutas` y `seed.py` con sólo `# TODO C-03: estado inicial conocido`. Verificar: `grep -n "TODO C-01" main.py` y `grep -n "TODO C-03" seed.py` devuelven la línea, y `grep -v "^#" main.py | grep -v "^$"` y el equivalente sobre `seed.py` no devuelven nada (cero código ejecutable).
- [x] 5.3 Confirmar que no se coló lógica ni esquema en el árbol. Verificar: `grep -rn "create_all\|def \|class " app/ main.py seed.py` no devuelve coincidencias, y `grep -rn "create_all" migrations/` tampoco (`migrations/env.py` y `script.py.mako` contienen `def` por plantilla, por eso se excluyen del patrón general).

## 6. Puerta de cierre de C-00 (integración, 4/4 máquinas)

- [x] 6.1 V0 — Higiene del repositorio: `git status --porcelain` no muestra `.env`; `git check-ignore -v .env` imprime la regla y sale con código 0; `SECRETO=$(grep '^POSTGRES_PASSWORD=' .env | cut -d= -f2-); git grep -nI "postgres:${SECRETO}@"` y `JWT=$(grep '^JWT_SECRET_KEY=' .env | cut -d= -f2-); git grep -nI "$JWT"` no devuelven coincidencias (ningún valor real versionado).
- [x] 6.2 V1 — Contrato estático: `grep -rn "create_all" . --exclude-dir=openspec --exclude-dir=.venv --exclude-dir=.git` sin coincidencias; `grep -n "sqlalchemy.url" alembic.ini` sin coincidencias; `grep -n "from app.core.config import Settings" migrations/env.py` con coincidencia; `find app -name "__init__.py" | wc -l` = 8; `grep -n "TODO C-01" main.py` y `grep -n "TODO C-03" seed.py` con coincidencia.
- [x] 6.3 V2 — Instalación e imports en las 4 máquinas (comprobación de "Cierra con" 1, consolidada): cada integrante reporta `pip install -r requirements.txt` con código 0 y `python -c "import fastapi, sqlmodel, alembic, asyncpg"` con código 0. Se cierra cuando A confirma 4/4 en el canal.
- [x] 6.4 V3 — Base en las 4 máquinas (comprobación de "Cierra con" 2, consolidada): cada integrante reporta `psql -h localhost -p 5432 -U postgres -c "select version()"` con `PostgreSQL 16` y `\dt` sobre `taller_mecanico` sin relaciones. Se cierra con 4/4.
- [x] 6.5 V4 — Reconfirmación de higiene con el `.env` real ya creado (comprobación de "Cierra con" 3): `git status` no muestra `.env`, `grep -i "password" env.example` no devuelve valores reales y `git diff --cached --name-only` no incluye `.env`. Se cierra con 4/4 y es la última verificación antes de archivar.
- [x] 6.6 Registrar la evidencia de cierre en el canal fijado: salida de V0–V4 por máquina, versión de PostgreSQL y `pip freeze` local. Verificar que el mensaje no contiene la contraseña ni la clave de firma.

## Workflow follow-up

- Archivar el change con `/opsx-archive c-00-setup-entorno-local` una vez que 6.1–6.6 estén en verde.
- Marcar `[C-00] setup-entorno-local` como `[x]` en `CHANGES.md` y anotar en el sync del día 1 que C-01 ya puede crear `app/core/config.py` con `Settings`.
