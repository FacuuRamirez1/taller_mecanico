# Spec Delta

## MODIFIED Requirements

### Requirement: Base PostgreSQL 16 local con rol único

El entorno SHALL usar PostgreSQL 16 instalado localmente, sin Docker, con un único rol de base (`postgres`) y la base `taller_mecanico` accesible en `localhost` en el puerto que declara `POSTGRES_PORT` (5432 en `env.example`; un integrante MAY usar otro puerto declarándolo sólo en su `.env`). Antes de C-02 la base MUST quedar sin tablas: no se crea esquema alguno.

#### Scenario: El servidor responde y es la versión correcta

- **WHEN** se ejecuta `psql -h localhost -p <POSTGRES_PORT> -U postgres -d taller_mecanico -c "select version()"`
- **THEN** la consulta responde y la salida indica PostgreSQL 16

#### Scenario: La base existe y está vacía

- **WHEN** se ejecuta `psql -h localhost -p <POSTGRES_PORT> -U postgres -d taller_mecanico -c "\dt"`
- **THEN** el comando responde y no lista ninguna tabla

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

- **WHEN** se inspecciona `migrations/versions/`
- **THEN** no hay archivos de revisión y el esquema sigue sin tablas

#### Scenario: Sin `create_all`

- **WHEN** se busca `create_all` en `app/`, `main.py` y `seed.py`
- **THEN** no hay coincidencias

### Requirement: Estructura de carpetas de la consigna

El repositorio SHALL contener el árbol obligatorio: `app/core/`, `app/modules/{health,usuarios,clientes,repuestos,ordenes}/` con su `__init__.py`, `app/__init__.py`, `migrations/versions/`, `test/`, `main.py` como punto de entrada de la aplicación y `seed.py` como marcador vacío hasta C-03. Ningún módulo SHALL contener lógica de negocio antes de los changes que la introducen.

#### Scenario: Árbol completo y verificable

- **WHEN** se listan las carpetas del repositorio
- **THEN** existen `app/core/`, los cinco módulos con `__init__.py`, `migrations/versions/` y `test/`

#### Scenario: `main.py` y `seed.py` son marcadores

- **WHEN** se abren `main.py` y `seed.py`
- **THEN** `main.py` define la aplicación con su lifespan y el router de salud, sin lógica de negocio, y `seed.py` contiene `TODO C-03` sin código ejecutable
