# configuracion-aplicacion Specification

## Purpose
Define cómo la aplicación obtiene su configuración: sólo del entorno o de un `.env` local no versionado, con los secretos obligatorios y sin ningún valor por defecto que permita arrancar con credenciales inventadas.

## Requirements

### Requirement: Configuración leída del entorno

La aplicación SHALL leer su configuración de las variables de entorno y, en su ausencia, del archivo `.env` local. Las variables reconocidas MUST ser las 12 setables de `env.example`: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_EXPIRE_SECONDS`, `BCRYPT_COST`, `DB_POOL_SIZE`, `SQL_ECHO` y `COOKIE_SECURE`. Una variable del entorno MUST prevalecer sobre la del `.env`.

#### Scenario: Valores tomados del `.env`

- **WHEN** el `.env` local define las 12 variables con valores válidos y el entorno no las redefine
- **THEN** la configuración cargada refleja exactamente esos valores

#### Scenario: El entorno prevalece sobre el `.env`

- **WHEN** el `.env` define `POSTGRES_PORT=5432` y el proceso se lanza con `POSTGRES_PORT=5433` en el entorno
- **THEN** la configuración cargada usa el puerto 5433

#### Scenario: Puerto no fijado en el código

- **WHEN** un integrante usa PostgreSQL en un puerto distinto de 5432 y lo declara sólo en su `.env`
- **THEN** la aplicación y Alembic se conectan a ese puerto sin modificar ningún archivo versionado

### Requirement: Secretos obligatorios sin valor por defecto

`JWT_SECRET_KEY` y `POSTGRES_PASSWORD` MUST NOT tener valor por defecto en el código ni en `alembic.ini`. Si cualquiera de los dos falta, está vacío o conserva el placeholder de `env.example`, la carga de la configuración MUST fallar y la aplicación MUST NOT arrancar. El mensaje de error MUST nombrar la variable y MUST NOT mostrar su valor.

#### Scenario: Falta la clave de firma

- **WHEN** se intenta arrancar la aplicación sin `JWT_SECRET_KEY` en el entorno ni en el `.env`
- **THEN** el arranque falla con un error de validación que nombra `JWT_SECRET_KEY` y el servidor no queda escuchando

#### Scenario: Clave de firma vacía

- **WHEN** se arranca con `JWT_SECRET_KEY=` (vacía), como queda al copiar `env.example` sin completar
- **THEN** el arranque falla igual que si la variable no existiera

#### Scenario: Contraseña de la base con el placeholder

- **WHEN** se arranca con `POSTGRES_PASSWORD=CAMBIAR_EN_TU_.env`
- **THEN** el arranque falla con un error que nombra `POSTGRES_PASSWORD`

#### Scenario: El error no filtra el secreto

- **WHEN** la validación de la configuración falla por cualquier variable
- **THEN** la salida no contiene el valor de `POSTGRES_PASSWORD` ni el de `JWT_SECRET_KEY`

### Requirement: Clave de firma con longitud mínima

`JWT_SECRET_KEY` MUST tener al menos 32 caracteres; una clave más corta MUST rechazarse al cargar la configuración. La clave MUST provenir del entorno: la aplicación MUST NOT generarla al arrancar.

#### Scenario: Clave demasiado corta

- **WHEN** se arranca con `JWT_SECRET_KEY=abc`
- **THEN** el arranque falla con un error que nombra `JWT_SECRET_KEY`

#### Scenario: Clave generada con el método documentado

- **WHEN** la clave se generó con `python -c "import secrets; print(secrets.token_urlsafe(64))"` y está en el `.env`
- **THEN** la configuración carga sin error y el valor es el mismo en cada reinicio

### Requirement: URL de conexión calculada

La URL de conexión a PostgreSQL SHALL calcularse a partir de `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` y `POSTGRES_DB` con el driver asincrónico `postgresql+asyncpg`. MUST NOT leerse de una variable `DATABASE_URL` del entorno y MUST NOT aparecer completa en la representación textual de la configuración.

#### Scenario: URL armada con los cinco componentes

- **WHEN** la configuración tiene usuario `postgres`, host `localhost`, puerto `5433` y base `taller_mecanico`
- **THEN** la URL calculada empieza con `postgresql+asyncpg://postgres:` y termina con `@localhost:5433/taller_mecanico`

#### Scenario: Contraseña con caracteres especiales

- **WHEN** `POSTGRES_PASSWORD` contiene `@`, `/` o `%`
- **THEN** la URL calculada sigue siendo válida y la conexión usa la contraseña literal

#### Scenario: Representación sin secretos

- **WHEN** se imprime o se registra el objeto de configuración
- **THEN** la salida no contiene la contraseña ni la clave de firma

### Requirement: Valores no secretos con defaults acordados

Las variables no secretas SHALL aceptar los valores acordados como default: `JWT_ALGORITHM=HS256`, `JWT_EXPIRE_SECONDS=1800`, `BCRYPT_COST=12`, `DB_POOL_SIZE=5`, `SQL_ECHO=false`, `COOKIE_SECURE=false`. Los valores numéricos y booleanos MUST validarse por tipo; un valor inválido MUST impedir el arranque.

#### Scenario: Defaults aplicados

- **WHEN** el `.env` sólo define las cinco `POSTGRES_*` y `JWT_SECRET_KEY`
- **THEN** la configuración carga con `HS256`, `1800`, `12`, `5`, `false` y `false`

#### Scenario: Tipo inválido

- **WHEN** se arranca con `BCRYPT_COST=doce`
- **THEN** el arranque falla con un error que nombra `BCRYPT_COST`
