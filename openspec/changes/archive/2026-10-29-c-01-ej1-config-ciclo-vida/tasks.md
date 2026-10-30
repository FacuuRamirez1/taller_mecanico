# Tasks

> **Strict TDD en forma de verificación** (igual que C-00): no hay pytest; la aceptación son `test/*.http` y comandos de CLI. En cada task se corre **primero** la verificación y se registra que da rojo (RED), luego se escribe el código mínimo hasta que da verde (GREEN) y se corre una segunda verificación con otra entrada (TRIANGULATE). Las salidas esperadas están en cada task.
>
> Convenciones: todo se corre desde la raíz del repo con el venv activo (`source .venv/Scripts/activate`). **Nunca** se abre, imprime ni edita el `.env`; las pruebas de "secreto faltante" sobreescriben la variable desde el entorno del comando (el entorno prevalece sobre el `.env`). Los valores usados en los comandos (`abc`, `x%y`) son de prueba, nunca reales. `<PORT>` = el `POSTGRES_PORT` de tu `.env` (5432 por defecto, 5433 en la máquina del proponente).
>
> Governance **CRÍTICO** (arranque + secretos): ante cualquier duda sobre secretos o sobre cambiar `requirements.txt`, parar y consultar al usuario.

## 0. Decisión previa

- [x] 0.1 Decidir con el usuario el ítem abierto `fastapi[standard]==0.111.1` (design.md §Risks): (a) mantenerlo y documentar la advertencia de pip, o (b) cambiarlo a `fastapi==0.111.1`. **No cambiar sin respuesta explícita.** Si se elige (b): editar `requirements.txt`, reemplazar en `openspec/changes/c-01-ej1-config-ciclo-vida/specs/entorno-desarrollo-local/spec.md` la mención "uvicorn vía `fastapi[standard]`" si corresponde, y verificar `pip install -r requirements.txt 2>&1 | grep -i "does not provide the extra"` sin coincidencias y `python -c "import fastapi; print(fastapi.__version__)"` → `0.111.1`. Si se elige (a): verificar que la decisión quedó anotada en design.md.

## 1. Configuración (`app/core/config.py`)

- [x] 1.1 RED: `python -c "from app.core.config import Settings"` falla con `ModuleNotFoundError`. Smoke de compatibilidad de pines: `python -c "from pydantic import SecretStr, computed_field; from pydantic_settings import BaseSettings, SettingsConfigDict"` termina con código 0.
- [x] 1.2 Crear `Settings` según design.md §D1: `SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")`; `POSTGRES_USER/DB/HOST: str` y `POSTGRES_PORT: int` requeridos; `POSTGRES_PASSWORD` y `JWT_SECRET_KEY` como `SecretStr` **sin default**; defaults `HS256`, `1800`, `12` (4..31), `5` (≥1), `SQL_ECHO=False`, `COOKIE_SECURE=False`. Ningún objeto `Settings()` a nivel de módulo. GREEN: `python -c "from app.core.config import Settings; s=Settings(); print(s.POSTGRES_PORT, s.JWT_ALGORITHM, s.BCRYPT_COST)"` imprime tu `<PORT> HS256 12` y no imprime secretos.
- [x] 1.3 Agregar el `field_validator` de secretos (vacío/espacios, placeholder `CAMBIAR_EN_TU_.env`, `JWT_SECRET_KEY` ≥ 32 caracteres; mensajes que nombran la variable sin incluir el valor). Verificar las tres entradas (TRIANGULATE): `JWT_SECRET_KEY= python -c "from app.core.config import Settings; Settings()"`, `JWT_SECRET_KEY=abc python -c "..."` y `POSTGRES_PASSWORD=CAMBIAR_EN_TU_.env python -c "..."` terminan con `ValidationError` que nombra la variable; ninguna salida contiene el valor del `.env`. `BCRYPT_COST=doce python -c "..."` falla nombrando `BCRYPT_COST`.
- [x] 1.4 Agregar `DATABASE_URL` con `@computed_field(repr=False)` usando `sqlalchemy.engine.URL.create("postgresql+asyncpg", ...).render_as_string(hide_password=False)` (design.md §D2). Verificar: `python -c "from app.core.config import Settings; u=Settings().DATABASE_URL; print(u.startswith('postgresql+asyncpg://postgres:'), u.endswith('/taller_mecanico'))"` → `True True`; `POSTGRES_PASSWORD='p@s/s%x' python -c "from app.core.config import Settings; from sqlalchemy.engine import make_url; print(make_url(Settings().DATABASE_URL).password)"` → `p@s/s%x`; `python -c "from app.core.config import Settings; s=Settings(); r=repr(s); print('DATABASE_URL' in r, s.POSTGRES_PASSWORD.get_secret_value() in r)"` → `False False`.
- [x] 1.5 Verificar que el puerto viene del entorno: `POSTGRES_PORT=6543 python -c "from app.core.config import Settings; print(Settings().DATABASE_URL.endswith(':6543/taller_mecanico'))"` → `True`; `grep -n "5432\|5433" app/core/config.py` sin coincidencias.

## 2. Hash de contraseñas (`app/core/security.py` mínimo)

- [x] 2.1 RED: `python -c "from app.core.security import hash_password"` falla con `ImportError`/`ModuleNotFoundError`.
- [x] 2.2 Implementar `hash_password(password, cost)` y `verify_password(password, password_hash)` async con `asyncio.to_thread` bajo semáforo creado perezosamente (`MAX_BCRYPT_CONCURRENTES = 4`), y `verify_password` devolviendo `False` ante `ValueError` (design.md §D6). GREEN + TRIANGULATE: `python -c "import asyncio; from app.core.security import hash_password as h, verify_password as v; x=asyncio.run(h('clave-uno', 12)); y=asyncio.run(h('clave-uno', 12)); print(x[:7], x!=y, asyncio.run(v('clave-uno', x)), asyncio.run(v('otra', x)), asyncio.run(v('clave-uno', 'no-es-un-hash')))"` → `$2b$12$ True True False False`. Con costo 4 el prefijo es `$2b$04$`.
- [x] 2.3 Verificar que nada se construye al importar y que bcrypt nunca corre en el bucle: `grep -n "bcrypt\.\(hashpw\|checkpw\|gensalt\)" app/core/security.py` sólo aparece dentro de funciones síncronas pasadas a `asyncio.to_thread`; `grep -n "^_\?[a-z_]* *= *asyncio.Semaphore" app/core/security.py` sin coincidencias (el semáforo no se crea a nivel de módulo).

## 3. Motor y sesión (`app/core/database.py`)

- [x] 3.1 RED: `python -c "from app.core.database import crear_engine, crear_sessionmaker, get_session, SessionDep"` falla.
- [x] 3.2 Implementar `crear_engine(settings)` (`create_async_engine` con `pool_size=DB_POOL_SIZE`, `echo=SQL_ECHO`, `pool_pre_ping=True`), `crear_sessionmaker(engine)` (`async_sessionmaker`, `class_=AsyncSession` de SQLModel, `expire_on_commit=False`), `get_session(request)` con `async with ... yield` sin `commit`, y `SessionDep` (design.md §D4). GREEN: el import de 3.1 termina con código 0. TRIANGULATE: `python -c "import asyncio; from sqlalchemy import text; from app.core.config import Settings; from app.core.database import crear_engine, crear_sessionmaker
async def m():
    e=crear_engine(Settings()); f=crear_sessionmaker(e)
    async with f() as s: print((await s.execute(text('SELECT 1'))).scalar(), f.kw['expire_on_commit'])
    await e.dispose()
asyncio.run(m())"` → `1 False` con PostgreSQL arriba.
- [x] 3.3 Verificar contrato estático: `grep -n "commit" app/core/database.py` sin coincidencias; `grep -n "create_async_engine\|async_sessionmaker(" app/core/database.py` sólo dentro de `def crear_engine`/`def crear_sessionmaker` (nada a nivel de módulo); `grep -rn "create_all" app/` sin coincidencias.

## 4. Ciclo de vida (`main.py`)

- [x] 4.1 RED: `uvicorn main:app --port 8000` falla con `Attribute "app" not found in module "main"`.
- [x] 4.2 Implementar el `lifespan` de design.md §D5 (Settings → engine → sessionmaker → `app.state.settings/engine/sessionmaker` → `app.state.hash_ficticio` vía `hash_password(secrets.token_urlsafe(32), settings.BCRYPT_COST)` → `yield` → `finally: await engine.dispose()`), `app = FastAPI(lifespan=lifespan)`; quitar el `TODO C-01`. GREEN: `uvicorn main:app --port 8000` muestra `Application startup complete`; Ctrl+C muestra `Application shutdown complete`.
- [x] 4.3 Verificar "nada al importar" (TRIANGULATE): `JWT_SECRET_KEY= python -c "import main"` termina con código 0 (sin `ValidationError`) incluso con PostgreSQL detenido; `grep -n "Settings()\|crear_engine(\|hash_password(" main.py` sólo aparece dentro de `lifespan`.
- [x] 4.4 **Cierra con 3 — sin `JWT_SECRET_KEY` la app NO arranca**: `JWT_SECRET_KEY= uvicorn main:app --port 8000; echo "exit=$?"` muestra `ValidationError` nombrando `JWT_SECRET_KEY`, `Application startup failed. Exiting.` y `exit=` distinto de 0; repetir con `JWT_SECRET_KEY=abc` (mismo resultado) y con `POSTGRES_PASSWORD=` (falla nombrando `POSTGRES_PASSWORD`). En ninguna salida aparece un valor del `.env`.
- [x] 4.5 Verificar el hash ficticio sin modificar código: `python -c "import asyncio; from main import app, lifespan
async def m():
    async with lifespan(app): print(app.state.hash_ficticio[:7])
asyncio.run(m())"` → `$2b$12$` (o el costo de tu `.env`), y `grep -c "hash_password(" main.py` → 1.

## 5. Salud (`app/modules/health/router.py` + `test/salud.http`)

- [x] 5.1 RED: con el server arriba, `curl -s -o /dev/null -w "%{http_code}" localhost:8000/health/live` → `404`.
- [x] 5.2 Implementar el router de design.md §D7 (`APIRouter(prefix="/health", tags=["health"])`; `/live` sin `SessionDep`; `/ready` con `SessionDep`, `wait_for(..., 3)` y 503 `"La base de datos no responde"` ante `SQLAlchemyError`/`OSError`/`TimeoutError`) y montarlo en `main.py`. GREEN: `curl -s -w " %{http_code}" localhost:8000/health/live` → `{"status":"ok"} 200` y `/health/ready` → `{"status":"ok"} 200`.
- [x] 5.3 Crear `test/salud.http` (REST Client, `@host = http://localhost:8000`) con `GET {{host}}/health/live` y `GET {{host}}/health/ready`, cada uno con la respuesta esperada comentada (200 `{"status":"ok"}`; y para `ready` con la base detenida: 503 `{"detail":"La base de datos no responde"}`). Verificar: correr ambos pedidos desde VS Code y comparar con los comentarios; `grep -c "^GET" test/salud.http` → 2.
- [x] 5.4 **Cierra con 2 — base detenida**: detener PostgreSQL (`Get-Service *postgres*` para el nombre; `net stop <servicio>` en consola de administrador, o `pg_ctl stop -D <data>`). Verificar: `/health/ready` → `503` con `{"detail":"La base de datos no responde"}` (sin texto de asyncpg/PostgreSQL) y `/health/live` → `200`. TRIANGULATE: volver a iniciar PostgreSQL y, **sin reiniciar uvicorn**, `/health/ready` → `200`.
- [x] 5.5 Verificar arranque con base caída: con PostgreSQL detenido, `uvicorn main:app --port 8000` muestra `Application startup complete` (el lifespan no consulta la base) y `/health/ready` → 503.

## 6. Alembic con `Settings` (`migrations/env.py`)

- [x] 6.1 RED: con contraseña de prueba que contiene `%`, `POSTGRES_PASSWORD='x%y' alembic current 2>&1 | grep -i "interpolation"` muestra `InterpolationSyntaxError` (o `invalid interpolation syntax`).
- [x] 6.2 Cambiar en `migrations/env.py` a `config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))` y retirar los `TODO C-01` del docstring y del import (design.md §D3); no tocar `alembic.ini`. GREEN: el comando de 6.1 ya no muestra error de interpolación (falla sólo por autenticación, esperado con una contraseña falsa).
- [x] 6.3 **Cierra con 4 — `alembic current` conecta usando `Settings`**: `alembic current; echo "exit=$?"` → `exit=0` sin `ModuleNotFoundError` ni prompt de credenciales (sin revisiones todavía, no imprime ninguna). TRIANGULATE: `JWT_SECRET_KEY= alembic current` falla con el `ValidationError` de `JWT_SECRET_KEY` (mismo contrato que uvicorn). `grep -n "sqlalchemy.url" alembic.ini` sin coincidencias; `grep -n "TODO C-01" migrations/env.py main.py` sin coincidencias.

## 7. Puerta de cierre de C-01 (integración)

- [x] 7.1 **Cierra con 1**: con `.env` válido y PostgreSQL arriba, `uvicorn main:app` levanta; `/health/live` 200 y `/health/ready` 200 (pedidos de `test/salud.http`). Repetir en las 4 máquinas (cada una con su `POSTGRES_PORT`; la del proponente en 5433) y confirmar 4/4 en el canal.
- [x] 7.2 Higiene de secretos (CRÍTICO): `git status --porcelain` no muestra `.env`; `git check-ignore -v .env` sale con código 0; `SECRETO=$(grep '^POSTGRES_PASSWORD=' .env | cut -d= -f2-); git grep -nI -F "$SECRETO" -- . ':!env.example'` y `JWT=$(grep '^JWT_SECRET_KEY=' .env | cut -d= -f2-); git grep -nI -F "$JWT"` sin coincidencias (sin imprimir las variables); `git diff --stat` no incluye `env.example` ni `alembic.ini`.
- [x] 7.3 Contrato estático final: `grep -rn "create_all" app/ main.py seed.py migrations/` sin coincidencias; `grep -rn "commit()" app/core/database.py app/modules/health/` sin coincidencias; `grep -rn "SecretStr" app/core/config.py` muestra los dos secretos; `grep -n "TODO C-03" seed.py` sigue presente; `grep -rnE "(PASSWORD|SECRET_KEY)[^=]*=\s*['\"][^'\"]+['\"]" app/ main.py migrations/` sin coincidencias (ningún secreto con default).
- [x] 7.4 Log de arranque sin secretos: `uvicorn main:app --port 8000 2>&1 | head -40` (con `SQL_ECHO=true`) no contiene la contraseña ni la clave; verificar con `grep -F` contra los valores del `.env` sin imprimirlos, igual que 7.2.

## Workflow follow-up

- Archivar con `/opsx:archive c-01-ej1-config-ciclo-vida` cuando 0.1 y 7.1–7.4 estén en verde (sincroniza las specs nuevas y el delta de `entorno-desarrollo-local`).
- Marcar `[C-01] ej1-config-ciclo-vida` como `[x]` en `CHANGES.md` y avisar que C-02 ya puede correr `alembic revision --autogenerate`.
- Commit sólo con pedido explícito del usuario, con conventional commits (`feat: C-01 configuración y ciclo de vida`).
