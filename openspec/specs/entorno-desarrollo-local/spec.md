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

El entorno SHALL usar PostgreSQL 16 instalado localmente, sin Docker, con un único rol de base y la base `taller_mecanico` accesible en `localhost:5432`. En C-00 la base MUST quedar sin tablas: no se crea esquema alguno.

#### Scenario: El servidor responde y es la versión correcta

- **WHEN** se ejecuta `psql -h localhost -p 5432 -U postgres -d taller_mecanico -c "select version()"`
- **THEN** la consulta responde y la salida indica PostgreSQL 16

#### Scenario: La base existe y está vacía

- **WHEN** se ejecuta `psql -h localhost -p 5432 -U postgres -d taller_mecanico -c "\dt"`
- **THEN** el comando responde y no lista ninguna tabla

#### Scenario: Sin dependencia de Docker

- **WHEN** se levanta el entorno en una máquina limpia
- **THEN** no se requiere `docker-compose`, contenedor ni servicio orquestado

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

`alembic.ini` MUST NOT declarar URL de conexión ni credenciales. `migrations/env.py` SHALL usar la plantilla asincrónica y obtener la URL desde `Settings` (`app.core.config`), módulo que se implementa en C-01; hasta entonces el arranque de Alembic queda pendiente de ese change. `create_all` MUST NOT usarse en ningún archivo.

#### Scenario: `alembic.ini` sin URL

- **WHEN** se busca `sqlalchemy.url` en `alembic.ini`
- **THEN** no hay una URL ni credenciales declaradas

#### Scenario: `env.py` asincrónico y basado en `Settings`

- **WHEN** se revisa `migrations/env.py`
- **THEN** importa `Settings` desde `app.core.config` y configura el motor con `async_engine_from_config` (o equivalente asincrónico)

#### Scenario: `versions/` nace vacío

- **WHEN** se inspecciona `migrations/versions/`
- **THEN** no hay archivos de revisión y el esquema sigue sin tablas

#### Scenario: Sin `create_all`

- **WHEN** se busca `create_all` en `app/`, `main.py` y `seed.py`
- **THEN** no hay coincidencias

### Requirement: Estructura de carpetas de la consigna

El repositorio SHALL contener el árbol obligatorio: `app/core/`, `app/modules/{health,usuarios,clientes,repuestos,ordenes}/` con su `__init__.py`, `app/__init__.py`, `migrations/versions/`, `test/`, y `main.py` / `seed.py` como marcadores vacíos. Ningún módulo SHALL contener lógica de negocio en C-00.

#### Scenario: Árbol completo y verificable

- **WHEN** se listan las carpetas del repositorio
- **THEN** existen `app/core/`, los cinco módulos con `__init__.py`, `migrations/versions/` y `test/`

#### Scenario: `main.py` y `seed.py` son marcadores

- **WHEN** se abren `main.py` y `seed.py`
- **THEN** `main.py` contiene `TODO C-01`, `seed.py` contiene `TODO C-03`, y ninguno define código ejecutable de negocio

### Requirement: Contrato de arranque compartido

El equipo SHALL publicar un contrato de arranque de cinco líneas con la URL de conexión, el comando de arranque y el comando de migración, idéntico para las cuatro máquinas.

#### Scenario: Contrato completo

- **WHEN** un integrante lee el contrato de arranque
- **THEN** encuentra la URL de conexión, el comando de arranque de uvicorn y el comando de migración en no más de cinco líneas

#### Scenario: Consistencia con la configuración

- **WHEN** se compara el contrato con `env.example`
- **THEN** host, puerto, usuario y nombre de la base coinciden con `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER` y `POSTGRES_DB`
