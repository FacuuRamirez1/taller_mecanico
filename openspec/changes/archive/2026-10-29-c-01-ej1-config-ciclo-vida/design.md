# Design

## Context

Ver `proposal.md` §Why. Estado observado en el repo al proponer:

- `migrations/env.py` ya hace `from app.core.config import Settings`, instancia `Settings()` a nivel de módulo y llama `config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)`. Hoy falla con `ModuleNotFoundError` (esperado desde C-00).
- `alembic.ini` sólo declara `script_location`; no hay `sqlalchemy.url`.
- `env.example` define las 12 variables setables; `JWT_SECRET_KEY=` queda **vacía** y `POSTGRES_PASSWORD=CAMBIAR_EN_TU_.env`. `SQL_ECHO=true`.
- `main.py` y `seed.py` son marcadores; `app/core/` y `app/modules/health/` sólo tienen `__init__.py`.
- Pines: `fastapi==0.111.1` (antes `fastapi[standard]`, ver Risks), `SQLModel==0.0.24`, `SQLAlchemy==2.0.55`, `asyncpg==0.30.0`, `pydantic-settings==2.0.3`, `pydantic==2.8.2`, `bcrypt==4.0.1`, `uvicorn[standard]==0.30.6`.
- Decisiones de equipo ya tomadas: **Q-01** → la clave de firma se llama `JWT_SECRET_KEY`. **Q-02** → cada integrante usa PostgreSQL 16 local, usuario `postgres`, base `taller_mecanico`; `env.example` mantiene 5432 y la máquina del proponente usa 5433 sólo vía `.env` local.
- Restricciones duras del proyecto aplicables: nada de `create_all`, bcrypt nunca en el bucle, secretos sin default, `get_session` sin `commit`, errores sin texto interno de la base, `.env` nunca se lee/versiona desde el repo.

## Goals / Non-Goals

**Goals:**
- Que `uvicorn main:app` y `alembic current` compartan **la misma** fuente de configuración y fallen igual ante secretos faltantes.
- Que "la app no arranca sin `JWT_SECRET_KEY`" sea verificable con un comando, incluso partiendo de un `env.example` copiado sin completar.
- Dejar listas las piezas que consumen C-02 (URL para Alembic), C-03 (`SessionDep`), C-04 (`security.py`, hash ficticio) y C-15 (`SQL_ECHO`).

**Non-Goals:**
- JWT, cookie, login, `get_usuario_actual`, `requiere_rol`: C-04/C-05.
- Los dos grupos de rutas (abierto/protegido) en `main.py`: C-05. En C-01 sólo se monta `health`.
- `BaseRepository`, `UnitOfWork`, manejadores globales de `IntegrityError`: C-03/C-06.
- Validación de longitud ≤ 72 bytes de la contraseña: se hace en los schemas de entrada de C-04.
- Tests automatizados con pytest: la aceptación del proyecto son `test/*.http` y verificaciones por CLI.

## Decisions

### D1. `Settings` con pydantic-settings, secretos como `SecretStr` y validación anti-placeholder

- `class Settings(BaseSettings)` con `model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")` (sin `case_sensitive`: en Windows `os.environ` es insensible a mayúsculas y el default `False` evita sorpresas entre máquinas).
  - `extra="ignore"`: en pydantic-settings 2.0.x una clave del `.env` no declarada en el modelo produce `extra_forbidden` y tumbaría el arranque (por ejemplo, si alguien deja `DATABASE_URL=` en su `.env`). Ignorarla es seguro porque la URL **nunca** se lee del entorno.
  - Prioridad nativa de pydantic-settings: argumentos de init > variables de entorno > `.env`. Eso es lo que permite la prueba "sin clave" sin tocar el `.env` (ver D7).
- `POSTGRES_PASSWORD: SecretStr` y `JWT_SECRET_KEY: SecretStr` **sin default** (campo requerido). `SecretStr` hace que `repr()`, `str()` y los mensajes de `ValidationError` muestren `**********`.
- Un `field_validator` sobre ambos secretos rechaza: cadena vacía o sólo espacios, y el placeholder literal `CAMBIAR_EN_TU_.env`. Para `JWT_SECRET_KEY` exige además longitud ≥ 32. **Motivo**: `env.example` deja `JWT_SECRET_KEY=` vacía; sin este validador, "requerido" se satisface con `""` y la app arrancaría con una clave vacía, que es exactamente lo que la consigna prohíbe. Los mensajes del validador nombran la variable y **no** incluyen el valor recibido.
- Resto de campos con default en el código (permitido por KB 08 §Variables para no secretos): `POSTGRES_USER: str`, `POSTGRES_DB: str`, `POSTGRES_HOST: str` (requeridos, sin default: el contrato es `env.example`), `POSTGRES_PORT: int` (requerido, **sin** default para que nadie dependa de un 5432 implícito), `JWT_ALGORITHM: str = "HS256"`, `JWT_EXPIRE_SECONDS: int = 1800`, `BCRYPT_COST: int = 12` (rango 4..31), `DB_POOL_SIZE: int = 5` (≥ 1), `SQL_ECHO: bool = False`, `COOKIE_SECURE: bool = False`.
- **Alternativa descartada**: `str` plano para los secretos + `repr=False`. `SecretStr` cubre además los mensajes de validación y el `model_dump()`, que puede terminar en logs.

### D2. `DATABASE_URL` con `@computed_field` y `sqlalchemy.engine.URL`

- `@computed_field(repr=False)` + `@property def DATABASE_URL(self) -> str` que devuelve `URL.create("postgresql+asyncpg", username=..., password=self.POSTGRES_PASSWORD.get_secret_value(), host=..., port=..., database=...).render_as_string(hide_password=False)`.
- `URL.create` escapa `@`, `/`, `:` y `%` en la contraseña; concatenar con f-string rompe con contraseñas reales.
- `repr=False` evita que la URL (con la contraseña) aparezca en `repr(settings)`.
- **Alternativa descartada**: devolver el objeto `URL`. `migrations/env.py` necesita un `str` para `set_main_option`, y el engine acepta ambos; un único tipo simplifica.

### D3. Interacción `Settings` ↔ Alembic: escapar `%` en `env.py`

- `config.set_main_option` pasa por `configparser` con interpolación: un `%` en la URL (que `URL.create` produce al escapar, p. ej. `%40` para `@`) lanza `InterpolationSyntaxError`. Se cambia la línea a `config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))` y se retiran los comentarios `TODO C-01` del docstring/import.
- `env.py` sigue instanciando `Settings()` a nivel de módulo: es aceptable porque `env.py` sólo lo carga Alembic (no es un import de la aplicación) y así Alembic falla con el **mismo** `ValidationError` que uvicorn si faltan secretos. Consecuencia conocida: `alembic` exige `JWT_SECRET_KEY` aunque no la use; es deseado (un único contrato de configuración).
- `.env` se resuelve relativo al directorio de trabajo: Alembic y uvicorn se corren **desde la raíz del repo** (ya es el contrato de arranque de `env.example`).

### D4. `database.py`: fábricas puras + `get_session` desde `app.state`

- `crear_engine(settings) -> AsyncEngine`: `create_async_engine(settings.DATABASE_URL, pool_size=settings.DB_POOL_SIZE, echo=settings.SQL_ECHO, pool_pre_ping=True)`. `pool_pre_ping` hace que, cuando PostgreSQL vuelve tras una caída, el pool descarte conexiones muertas y `/health/ready` vuelva a 200 sin reiniciar (spec `salud-servicio`).
- `crear_sessionmaker(engine) -> async_sessionmaker[AsyncSession]` con `expire_on_commit=False` y `class_=AsyncSession` de `sqlmodel.ext.asyncio.session` (da `session.exec(...)` para los repositorios de C-03/C-06, y es compatible con `execute`).
- `async def get_session(request: Request) -> AsyncIterator[AsyncSession]`: `async with request.app.state.sessionmaker() as session: yield session`. El `async with` cierra la sesión también ante excepción; **no** hay `commit` ni `rollback` explícitos (la sesión cerrada sin commit descarta la transacción).
- `SessionDep = Annotated[AsyncSession, Depends(get_session)]` en `database.py` (C-05 creará `dependencies.py` para usuario/roles y podrá reexportarlo).
- Ningún objeto a nivel de módulo: sólo funciones y el alias de tipo.

### D5. `main.py`: lifespan como único lugar de construcción

```text
lifespan(app):
  settings = Settings()                       # ValidationError → arranque falla
  engine = crear_engine(settings)
  app.state.settings, .engine, .sessionmaker = settings, engine, crear_sessionmaker(engine)
  app.state.hash_ficticio = await hash_password(secrets.token_urlsafe(32), settings.BCRYPT_COST)
  try: yield
  finally: await engine.dispose()
app = FastAPI(title=..., lifespan=lifespan); app.include_router(health_router)
```

- `FastAPI(...)` a nivel de módulo es necesario para `uvicorn main:app` y **no** es un recurso (no lee config ni abre conexiones).
- El lifespan **no** hace `SELECT 1`: la API debe poder arrancar con la base caída y reportarlo vía `/ready` (separación live/ready, Flujo 11).
- `Settings` se guarda en `app.state.settings` para que C-04 lea `JWT_*`/`COOKIE_SECURE` sin instanciarla de nuevo.
- **Alternativa descartada**: `@lru_cache get_settings()` como dependencia global. Introduce un segundo punto de construcción y se cachea fuera del lifespan; `app.state` mantiene un solo dueño.

### D6. `security.py` mínimo: `to_thread` bajo semáforo creado perezosamente

- `async def hash_password(password: str, cost: int) -> str` y `async def verify_password(password: str, password_hash: str) -> bool`; ambas hacen `async with _semaforo(): return await asyncio.to_thread(...)`.
- Límite: constante `MAX_BCRYPT_CONCURRENTES = 4` (bcrypt es CPU; más hilos no aceleran y saturan el pool por defecto de `to_thread`).
- El semáforo se crea perezosamente en la primera llamada (`_semaforo()` con un global inicializado a `None`), es decir, dentro del bucle: respeta al pie de la letra "nada se construye al importar". (En 3.12 `asyncio.Semaphore()` ya no se ata al loop al construirse, así que crearlo a nivel de módulo también funcionaría; se elige la versión perezosa para no dejar dudas en la corrección.)
- `verify_password` captura `ValueError` de `bcrypt.checkpw` (hash malformado) y devuelve `False`.
- El costo se recibe por parámetro (no se lee `Settings` dentro de `security.py`): la función es pura respecto de la configuración y el lifespan/servicios le pasan `settings.BCRYPT_COST`.
- bcrypt 4.0.1 trunca en silencio por encima de 72 bytes; el límite lo validará el schema de C-04 (fuera de alcance aquí).

### D7. Health: sólo `router.py`, con timeout y 503 propio

- `router = APIRouter(prefix="/health", tags=["health"])`. Excepción documentada de la arquitectura: `health` no tiene service/UoW/repository (KB 08).
- `/live`: `async def` que devuelve `{"status": "ok"}` y no declara `SessionDep`.
- `/ready`: declara `SessionDep`; `await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=3)`. Captura `SQLAlchemyError`, `OSError` (incluye `ConnectionRefusedError`) y `TimeoutError` y lanza `HTTPException(503, detail="La base de datos no responde")`. Nunca re-lanza el mensaje del driver.
- La sesión se obtiene sin conectar: la conexión real se pide recién en `execute`, por eso el fallo cae dentro del `try`.
- Verificación manual en `test/salud.http` (REST Client) con respuesta esperada comentada; se usa `@host = http://localhost:8000`.

### D8. Verificación en lugar de pytest (Strict TDD en forma de verificación)

Igual que C-00: cada task trae primero la verificación que hoy da **rojo** (RED), luego el código mínimo que la pone en **verde** (GREEN) y una segunda verificación con otra entrada (TRIANGULATE). Las verificaciones son comandos `python -c`, `uvicorn`, `alembic`, `grep` y los pedidos de `test/salud.http`. Para la prueba "sin clave" se usa `JWT_SECRET_KEY= uvicorn main:app` (el entorno vacío prevalece sobre el `.env` y el validador lo rechaza); nunca se edita ni se imprime el `.env`.

## Risks / Trade-offs

- **[`fastapi[standard]==0.111.1` — RESUELTO: opción (b) elegida por el usuario; `requirements.txt` ahora pina `fastapi==0.111.1`]** El extra `standard` aparece recién en FastAPI 0.112; con 0.111.1 `pip` advierte `fastapi 0.111.1 does not provide the extra 'standard'`. No rompe la instalación (en 0.111 `fastapi` ya trae `fastapi-cli`, `uvicorn[standard]` está pineado aparte). → **No se cambia en este change sin decisión del equipo.** Opciones: (a) dejarlo y documentar la advertencia; (b) cambiar a `fastapi==0.111.1` (mismo resultado instalado, sin advertencia, y ajustar el escenario de la spec `entorno-desarrollo-local` que menciona "uvicorn vía `fastapi[standard]`"). Recomendación: (b), decidido antes de la task 1.x de apply; queda como task de decisión explícita (tasks §0).
- **[Validación de secretos más estricta que "requerido"]** Rechazar vacío/placeholder/corta puede hacer que un `.env` existente que antes "andaba" ya no arranque. → Es el comportamiento deseado; el mensaje nombra la variable y `env.example` documenta cómo generar la clave.
- **[Alembic exige `JWT_SECRET_KEY`]** Al compartir `Settings`, `alembic` falla sin clave de firma aunque no la use. → Aceptado: un solo contrato; queda escrito en el escenario de la spec.
- **[`%` en la contraseña]** Sin el escape de D3, Alembic falla con `InterpolationSyntaxError` sólo en las máquinas con `%`/`@` en la contraseña (difícil de diagnosticar). → Escape en `env.py` + task de verificación con una contraseña de prueba vía entorno.
- **[pydantic-settings 2.0.3 con pydantic 2.8.2]** Versión vieja de pydantic-settings sobre pydantic más nuevo; `computed_field` y `SecretStr` son de pydantic, no de pydantic-settings, así que no hay dependencia de features nuevas. → Smoke de import en la task 1.1 antes de escribir el resto.
- **[Timeout de `/ready`]** Con PostgreSQL detenido en Windows el `connect` suele fallar al instante (conexión rechazada); si el host no responde, el timeout de 3 s acota la espera. → `wait_for` + `TimeoutError` → 503.
- **[`SQL_ECHO=true` en `env.example`]** Con echo activo, el log de SQLAlchemy muestra SQL pero no la URL con contraseña. → Verificado en la task de higiene (`grep` del log de arranque).
- **[Detener PostgreSQL para probar 503]** En Windows requiere consola de administrador (`net stop postgresql-x64-16`) o `pg_ctl stop -D <data>`. → Documentado en la task; el nombre exacto del servicio se toma de `Get-Service *postgres*`.

## Migration Plan

1. Implementar en el orden de `tasks.md` (config → security → database → lifespan → health → alembic → cierre).
2. Cada integrante hace `git pull` y corre `uvicorn main:app` desde la raíz; si su `.env` tiene `JWT_SECRET_KEY` vacía o corta, regenerarla con el comando documentado.
3. **Rollback**: revertir el commit; el repo vuelve al estado de C-00 (Alembic falla con `ModuleNotFoundError`, esperado). No hay esquema ni datos que migrar.

## Open Questions

- (Resuelta) `fastapi[standard]` vs `fastapi`: se eligió `fastapi==0.111.1` (ver Risks). No cambia specs de C-01 ni el desglose de tasks; sí un escenario de `entorno-desarrollo-local` si se elige (b), que se ajusta en la misma task de decisión.
