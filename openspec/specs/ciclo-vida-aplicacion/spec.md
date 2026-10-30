# ciclo-vida-aplicacion Specification

## Purpose
Define el ciclo de vida del proceso de la API: qué recursos se crean al arrancar, cuáles se liberan al apagar, y cómo cada petición obtiene su propia sesión de base de datos sin confirmar transacciones por su cuenta.

## Requirements

### Requirement: Nada se construye al importar

Importar el módulo de la aplicación o cualquier módulo de `app/` MUST NOT leer la configuración, crear el motor de base de datos, crear la fábrica de sesiones, abrir conexiones ni calcular hashes. Esos recursos SHALL crearse sólo durante el arranque del servidor.

#### Scenario: Importar sin base ni secretos

- **WHEN** se ejecuta `python -c "import main"` con PostgreSQL detenido y sin `JWT_SECRET_KEY` en el entorno
- **THEN** el comando termina con código 0, sin intentar conectarse y sin error de configuración

#### Scenario: Sin creación de esquema

- **WHEN** se busca `create_all` en `main.py` y en `app/`
- **THEN** no hay coincidencias: el esquema sólo nace de Alembic

### Requirement: Recursos creados en el arranque

Durante el arranque la aplicación SHALL cargar la configuración, crear el motor asincrónico con el tamaño de pool configurado y la fábrica de sesiones dentro del bucle de eventos, y dejarlos disponibles en el estado de la aplicación. Si la configuración es inválida, el arranque MUST fallar y el servidor MUST NOT aceptar peticiones.

#### Scenario: Arranque exitoso

- **WHEN** se ejecuta `uvicorn main:app` con un `.env` válido y PostgreSQL en marcha
- **THEN** uvicorn informa `Application startup complete` y el servidor acepta peticiones

#### Scenario: Arranque con configuración inválida

- **WHEN** se ejecuta `uvicorn main:app` sin `JWT_SECRET_KEY`
- **THEN** uvicorn informa que el arranque falló y el proceso termina con código distinto de 0

#### Scenario: El arranque no exige la base

- **WHEN** se ejecuta `uvicorn main:app` con configuración válida y PostgreSQL detenido
- **THEN** el servidor arranca igual y la indisponibilidad de la base se refleja sólo en el chequeo de disponibilidad

### Requirement: Hash ficticio calculado una sola vez

Durante el arranque la aplicación SHALL calcular una única vez un hash bcrypt ficticio con el costo configurado y dejarlo disponible en el estado de la aplicación para que el login (C-04) compare contra él cuando el correo no existe. El hash MUST NOT recalcularse por petición.

#### Scenario: Hash disponible tras el arranque

- **WHEN** el arranque termina
- **THEN** el estado de la aplicación contiene un hash bcrypt válido cuyo costo coincide con `BCRYPT_COST`

#### Scenario: Calculado fuera del bucle de eventos

- **WHEN** se calcula el hash ficticio
- **THEN** el cálculo se ejecuta en un hilo aparte y no bloquea el bucle de eventos

### Requirement: Liberación de recursos al apagar

Al apagarse, la aplicación SHALL cerrar el motor de base de datos y liberar todas las conexiones del pool, incluso si el apagado ocurre tras un error durante el servicio.

#### Scenario: Apagado ordenado

- **WHEN** se detiene uvicorn con Ctrl+C
- **THEN** uvicorn informa `Application shutdown complete` y no quedan conexiones abiertas de la aplicación en PostgreSQL

### Requirement: Una sesión por petición sin confirmación automática

Cada petición que necesite base SHALL recibir una sesión propia creada desde la fábrica del estado de la aplicación, que no expira los objetos al confirmar. La sesión MUST cerrarse al terminar la petición, también ante un error, y MUST NOT confirmar la transacción: confirmar o revertir corresponde a la Unit of Work.

#### Scenario: Sesiones aisladas

- **WHEN** dos peticiones concurrentes requieren sesión
- **THEN** cada una recibe una sesión distinta

#### Scenario: Sin commit implícito

- **WHEN** un handler escribe con la sesión y termina sin que nadie confirme
- **THEN** los cambios no quedan persistidos en la base

#### Scenario: Cierre ante error

- **WHEN** el handler lanza una excepción mientras usa la sesión
- **THEN** la sesión se cierra y su conexión vuelve al pool
