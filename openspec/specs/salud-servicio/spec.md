# salud-servicio Specification

## Purpose
Permite distinguir "el proceso está vivo" de "el proceso está listo para atender porque la base contesta", con dos chequeos públicos y códigos HTTP inequívocos.

## Requirements

### Requirement: Chequeo de vida sin tocar la base

`GET /health/live` SHALL responder 200 con un cuerpo JSON propio mientras el proceso esté en marcha, sin abrir sesión ni conexión a la base. MUST NOT requerir autenticación.

#### Scenario: Proceso vivo con base disponible

- **WHEN** se pide `GET /health/live` con PostgreSQL en marcha
- **THEN** la respuesta es 200 con `{"status": "ok"}`

#### Scenario: Proceso vivo con base detenida

- **WHEN** se pide `GET /health/live` con PostgreSQL detenido
- **THEN** la respuesta sigue siendo 200 y no se intenta ninguna conexión

### Requirement: Chequeo de disponibilidad contra la base

`GET /health/ready` SHALL ejecutar `SELECT 1` contra la base con un tiempo máximo acotado. Si la consulta contesta, MUST responder 200; si falla o excede el tiempo, MUST responder 503 con un mensaje propio, sin texto interno de PostgreSQL ni traza. MUST NOT requerir autenticación.

#### Scenario: Base disponible

- **WHEN** se pide `GET /health/ready` con PostgreSQL en marcha
- **THEN** la respuesta es 200 con `{"status": "ok"}`

#### Scenario: Base detenida

- **WHEN** se pide `GET /health/ready` con PostgreSQL detenido
- **THEN** la respuesta es 503 con un `detail` propio que indica que la base no responde, y el cuerpo no contiene texto de asyncpg ni de PostgreSQL

#### Scenario: La base vuelve sin reiniciar el proceso

- **WHEN** PostgreSQL se detiene, `GET /health/ready` responde 503, y luego PostgreSQL se vuelve a iniciar
- **THEN** un nuevo `GET /health/ready` responde 200 sin haber reiniciado uvicorn

#### Scenario: Nunca 500

- **WHEN** la base falla de cualquier forma durante el chequeo
- **THEN** la respuesta es 503 y nunca 500
