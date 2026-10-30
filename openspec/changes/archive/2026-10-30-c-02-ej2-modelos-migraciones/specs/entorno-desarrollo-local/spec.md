# Spec Delta

## MODIFIED Requirements

### Requirement: Base PostgreSQL 16 local con rol único

El entorno SHALL usar PostgreSQL 16 instalado localmente, sin Docker, con un único rol de base (`postgres`) y la base `taller_mecanico` accesible en `localhost` en el puerto que declara `POSTGRES_PORT` (5432 en `env.example`; un integrante MAY usar otro puerto declarándolo sólo en su `.env`). Las únicas tablas de la base MUST ser las que crean las migraciones de Alembic; una base nueva MUST arrancar sin tablas hasta correr `alembic upgrade head`.

#### Scenario: El servidor responde y es la versión correcta

- **WHEN** se ejecuta `psql -h localhost -p <POSTGRES_PORT> -U postgres -d taller_mecanico -c "select version()"`
- **THEN** la consulta responde y la salida indica PostgreSQL 16

#### Scenario: La base existe y está vacía

- **WHEN** se crea la base `taller_mecanico` y, antes de migrar, se ejecuta `psql -h localhost -p <POSTGRES_PORT> -U postgres -d taller_mecanico -c "\dt"`
- **THEN** el comando responde y no lista ninguna tabla

#### Scenario: Sólo el esquema de las migraciones

- **WHEN** la base está en `head` y se ejecuta `\dt`
- **THEN** se listan las 13 tablas del dominio y `alembic_version`, ninguna otra

#### Scenario: Sin dependencia de Docker

- **WHEN** se levanta el entorno en una máquina limpia
- **THEN** no se requiere `docker-compose`, contenedor ni servicio orquestado

#### Scenario: Puerto local distinto sin tocar el repo

- **WHEN** un integrante tiene PostgreSQL en el puerto 5433 y declara `POSTGRES_PORT=5433` sólo en su `.env`
- **THEN** la aplicación y Alembic se conectan sin modificar `env.example` ni ningún otro archivo versionado

### Requirement: Configuración de Alembic sin credenciales y asincrónica

`alembic.ini` MUST NOT declarar URL de conexión ni credenciales. `migrations/env.py` SHALL usar la plantilla asincrónica y obtener la URL desde la configuración de la aplicación (`Settings` en `app.core.config`), la misma que usa la API. Los comandos de Alembic MUST conectarse a la base con esa URL. `create_all` MUST NOT usarse en ningún archivo.

#### Scenario: `alembic.ini` sin URL

- **WHEN** se busca `sqlalchemy.url` en `alembic.ini`
- **THEN** no hay una URL ni credenciales declaradas

#### Scenario: `env.py` asincrónico y basado en `Settings`

- **WHEN** se revisa `migrations/env.py`
- **THEN** importa `Settings` desde `app.core.config` y configura el motor con `async_engine_from_config` (o equivalente asincrónico)

#### Scenario: Alembic conecta con la configuración de la aplicación

- **WHEN** se ejecuta `alembic current` con un `.env` válido y PostgreSQL en marcha
- **THEN** el comando termina con código 0 sin pedir credenciales y sin `ModuleNotFoundError`

#### Scenario: Contraseña con `%`

- **WHEN** `POSTGRES_PASSWORD` contiene el carácter `%`
- **THEN** `alembic current` no falla por interpolación de la configuración y conecta igual

#### Scenario: Alembic sin secretos no arranca

- **WHEN** se ejecuta `alembic current` sin `POSTGRES_PASSWORD` ni `JWT_SECRET_KEY`
- **THEN** el comando falla con el error de validación de la configuración, sin usar una URL por defecto

#### Scenario: `versions/` nace vacío

- **WHEN** se inspecciona `migrations/versions/` en un checkout posterior a C-02
- **THEN** no hay más revisiones que `0001_esquema_inicial.py` y `0002_solo_agregado.py`, y ninguna otra vía crea tablas

#### Scenario: Sin `create_all`

- **WHEN** se busca `create_all` en `app/`, `main.py` y `seed.py`
- **THEN** no hay coincidencias
