# Spec Delta

## MODIFIED Requirements

### Requirement: Nada se construye al importar

Importar el módulo de la aplicación o cualquier módulo de `app/` MUST NOT leer la configuración, crear el motor de base de datos, crear la fábrica de sesiones, abrir conexiones ni calcular hashes. Esos recursos SHALL crearse sólo durante el arranque del servidor. Importar los routers y los modelos de dominio MUST NOT construir recursos: sólo registra rutas y declara mapeos.

#### Scenario: Importar sin base ni secretos

- **WHEN** se ejecuta `python -c "import main"` con PostgreSQL detenido y sin `JWT_SECRET_KEY` en el entorno
- **THEN** el comando termina con código 0, sin intentar conectarse y sin error de configuración

#### Scenario: Importar con routers de dominio

- **WHEN** se importa `main` con los routers de clientes y repuestos registrados
- **THEN** el import termina sin abrir conexiones ni leer el `.env`

#### Scenario: Sin creación de esquema

- **WHEN** se busca `create_all` en `main.py` y en `app/`
- **THEN** no hay coincidencias: el esquema sólo nace de Alembic

## ADDED Requirements

### Requirement: Routers de dominio registrados al arrancar

`main.py` SHALL registrar el router de salud y los routers de clientes y repuestos. Al arrancar, los cuatro módulos de modelos (`usuarios`, `clientes`, `repuestos`, `ordenes`) MUST estar importados para que los mapeos de SQLAlchemy queden configurados antes de la primera consulta.

#### Scenario: Rutas de dominio disponibles

- **WHEN** el servidor arranca
- **THEN** las rutas de repuestos, clientes, vehículos y `mis-vehiculos` están disponibles en la aplicación

#### Scenario: Mapeos configurados

- **WHEN** se ejecuta una consulta de repuestos o clientes
- **THEN** las relaciones entre módulos se resuelven sin error de nombre no encontrado

#### Scenario: Registro sin lógica de negocio en `main.py`

- **WHEN** se revisa `main.py`
- **THEN** sólo crea la aplicación, define el lifespan e incluye routers; la lógica vive en los módulos
