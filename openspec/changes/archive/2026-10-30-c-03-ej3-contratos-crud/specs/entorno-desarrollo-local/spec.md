# Spec Delta

## MODIFIED Requirements

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
