# Proposal

## Why

El TP se corrige sobre un proyecto que **tiene que levantar**: si el entorno local difiere entre las 4 máquinas, o si el esquema no nace de Alembic, no hay nota que rescatar (R-01). Hoy no existe ni el entorno ni el esqueleto del repositorio, y dos decisiones P0 (`Q-01` y `Q-02`) bloqueaban la primera línea de código porque `Settings`, `env.example`, el `README` y `migrations/env.py` comparten esos nombres.

Este change es el **GATE 0**: deja las 4 máquinas idénticas, el árbol de carpetas de la consigna y la configuración de Alembic lista para que `C-01` escriba `app/core/config.py` y `C-02` genere la primera migración. No agrega comportamiento de negocio.

**Decisiones ya tomadas (no se re-abren):**

- **Q-01 resuelta**: la variable de entorno de la clave de firma se llama **`JWT_SECRET_KEY`**. No tiene valor por defecto en ningún lugar del código: si falta, la aplicación no arranca. Se declara en `Settings` (C-01), en `env.example`, en el `README` y la consume `migrations/env.py` a través de `Settings`.
- **Q-02 resuelta**: PostgreSQL 16 **local, sin Docker**, un solo rol de base: usuario `postgres`, contraseña `postgres`, base `taller_mecanico`, host `localhost`, puerto `5432`. La contraseña real vive **sólo** en el `.env` local (ignorado por git); `env.example` lleva los nombres de las claves con valores de ejemplo y **ningún secreto real**.

## What Changes

- **PostgreSQL 16 local, sin Docker**: crear el rol único y la base `taller_mecanico`; verificar con `psql -c "select version()"` y `\dt` que la base está vacía de tablas.
- **`.venv` + `requirements.txt` pinneado** con las versiones mínimas de la consigna: Python 3.12, FastAPI 0.111, SQLModel 0.0.24, SQLAlchemy 2.0 async, asyncpg 0.30, Alembic 1.13, pydantic-settings 2.0, bcrypt 4.0, PyJWT 2.8 y uvicorn (vía `fastapi[standard]`).
- **`env.example` con las 13 variables** de `knowledge-base/08_arquitectura_propuesta.md` §Variables de entorno y **ningún** secreto; `.env` local creado a partir de él y **no** versionado.
- **`.gitignore`** con `.env`, `__pycache__/` y `.venv/` como mínimo.
- **`alembic.ini` sin credenciales** (sin `sqlalchemy.url`) + **`migrations/env.py` con plantilla asincrónica** que importa `Settings` desde `app.core.config`, módulo que recién existe en C-01. El import se deja escrito y el `env.py` queda **funcionalmente incompleto hasta C-01**; se documenta explícitamente como deuda de ese change. Se agrega `migrations/script.py.mako` y `migrations/versions/` vacío.
- **Estructura de carpetas vacía** de la consigna: `app/core/`, `app/modules/{health,usuarios,clientes,repuestos,ordenes}/` (cada una con su `__init__.py`), `migrations/versions/`, `test/`, y `main.py` / `seed.py` como archivos vacíos con `TODO C-01` / `TODO C-03`.
- **Contrato de arranque**: un documento de 5 líneas con la URL de conexión, el comando de arranque y el comando de migración, para que las 4 máquinas sean idénticas.
- **BREAKING**: ninguno. El repositorio todavía no tiene aplicación.

**Fuera de alcance**: código de negocio, `app/core/config.py`, `app/core/database.py`, `main.py` implementado, `seed.py` implementado, tablas, modelos, migraciones con contenido, `create_all`, Docker, pytest y CI.

## Capabilities

### New Capabilities

- `entorno-desarrollo-local`: contrato del entorno reproducible del TP — versiones mínimas pinneadas, base PostgreSQL 16 local con un rol único, secretos fuera del repositorio, Alembic sin credenciales y asincrónico como única vía de creación del esquema, estructura de carpetas de la consigna y contrato de arranque compartido por las 4 máquinas.

### Modified Capabilities

Ninguna. `openspec/specs/` está vacío: este es el primer change del proyecto y no modifica requisitos existentes.

## Impact

- **Archivos nuevos en la raíz**: `requirements.txt`, `env.example`, `.gitignore`, `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`, `main.py` y `seed.py` (vacíos con `TODO`), `.env` local **no versionado**.
- **Árbol nuevo**: `app/__init__.py`, `app/core/__init__.py`, `app/modules/*/__init__.py`, `migrations/versions/`, `test/`.
- **Sin** modelos, tablas, endpoints ni lógica de negocio. `C-00` crea el esquema con **nada**: no hay `create_all` ni migraciones con contenido.
- **Habilita**: `C-01` (necesita el venv, la base y el `.env`), y de ahí en cadena toda la FASE 1 del roadmap.
- **Riesgo principal**: cualquier credencial real en el repositorio anula la corrección del TP. Se mitiga con `env.example` sin secretos, `.env` ignorado y una verificación ejecutable en `tasks.md` (`git status` no muestra `.env`, `env.example` no tiene valores reales).
- **Governance**: ALTO.
