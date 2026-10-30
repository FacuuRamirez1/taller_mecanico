# entorno-desarrollo-local Specification

## Purpose
Define el contrato del entorno de desarrollo local del TP para que las cuatro máquinas sean idénticas, reproducibles y libres de secretos, y para que el esquema de la base tenga una única vía de creación: las migraciones.

## Requirements

### Requirement: Versiones del stack fijadas y reproducibles

El repositorio SHALL declarar en `requirements.txt` las versiones exactas del stack obligatorio (Python 3.12, FastAPI 0.111, SQLModel 0.0.24, SQLAlchemy 2.0, asyncpg 0.30, Alembic 1.13, pydantic-settings 2.0, bcrypt 4.0, PyJWT 2.8 y uvicorn vía `fastapi[standard]`), de modo que las cuatro máquinas instalen el mismo conjunto y ninguna quede por debajo de la versión mínima de la consigna.

#### Scenario: Instalación limpia en una máquina nueva

- **WHEN** un integrante crea un entorno virtual con Python 3.12 y ejecuta `pip install -r requirements.txt`
- **THEN** la instalación termina sin error

#### Scenario: Verificación de imports del stack

- **WHEN** se ejecuta `python -c "import fastapi, sqlmodel, alembic, asyncpg"`
- **THEN** el comando termina con código 0 y sin salida de error

#### Scenario: Versiones mínimas respetadas

- **WHEN** se revisa `requirements.txt`
- **THEN** cada paquete obligatorio está pinneado a una versión igual o superior a la mínima de la consigna

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

### Requirement: Secretos fuera del repositorio

El repositorio MUST NOT contener credenciales reales. `env.example` SHALL listar las 13 variables de configuración con valores de ejemplo, y el `.env` local —con la contraseña real de PostgreSQL y el valor real de `JWT_SECRET_KEY`— SHALL estar ignorado por git.

#### Scenario: `.env` no aparece en git

- **WHEN** se ejecuta `git status --porcelain` en un checkout con `.env` creado
- **THEN** `.env` no aparece en la salida

#### Scenario: `env.example` no filtra secretos

- **WHEN** se ejecuta `grep -i "password\|secret" env.example`
- **THEN** sólo se ven nombres de claves y valores de ejemplo o vacíos, nunca la contraseña real ni una clave de firma utilizable

#### Scenario: Nombre de la clave de firma acordado

- **WHEN** se revisa `env.example`
- **THEN** la variable de la clave de firma se llama `JWT_SECRET_KEY` y no tiene un valor real

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

### Requirement: Estructura de carpetas de la consigna

El repositorio SHALL contener el árbol obligatorio: `app/core/`, `app/modules/{health,usuarios,clientes,repuestos,ordenes}/` con su `__init__.py`, `app/__init__.py`, `migrations/versions/`, `test/`, `main.py` como punto de entrada de la aplicación y `seed.py` como cargador del estado inicial. Los módulos de `clientes` y `repuestos` SHALL contener `schemas.py`, `service.py` y `router.py`; `usuarios` y `ordenes` SHALL contener sólo `schemas.py` hasta los changes que introducen sus rutas.

#### Scenario: Árbol completo y verificable

- **WHEN** se listan las carpetas del repositorio
- **THEN** existen `app/core/`, los cinco módulos con `__init__.py`, `migrations/versions/` y `test/`

#### Scenario: `main.py` y `seed.py` son marcadores

- **WHEN** se abren `main.py` y `seed.py` después de C-03
- **THEN** `main.py` define la aplicación con su lifespan, el router de salud y los routers de dominio (ya no es un marcador sin lógica de dominio), y `seed.py` contiene lógica ejecutable de carga inicial (ya no contiene `TODO C-03`)

### Requirement: Contrato de arranque compartido

El equipo SHALL publicar un contrato de arranque de seis líneas con la URL de conexión, el comando de arranque, el comando de migración y el comando de carga inicial, idéntico para las cuatro máquinas.

#### Scenario: Contrato completo

- **WHEN** un integrante lee el contrato de arranque
- **THEN** encuentra la URL de conexión, el comando de arranque de uvicorn, el comando de migración y el comando de carga inicial en no más de seis líneas

#### Scenario: Consistencia con la configuración

- **WHEN** se compara el contrato con `env.example`
- **THEN** host, puerto, usuario y nombre de la base coinciden con `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER` y `POSTGRES_DB`
