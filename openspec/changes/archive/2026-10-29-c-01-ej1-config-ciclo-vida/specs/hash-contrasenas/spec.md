# Spec Delta

## Purpose

Define cómo la aplicación calcula y verifica hashes de contraseñas con bcrypt sin bloquear el bucle de eventos ni saturar la CPU, como base que el login de C-04 extiende.

## ADDED Requirements

### Requirement: Hash bcrypt con costo configurable

La aplicación SHALL calcular hashes de contraseña con bcrypt usando el costo de `BCRYPT_COST` y una sal nueva por llamada. El hash resultante MUST NOT contener la contraseña en claro.

#### Scenario: Costo tomado de la configuración

- **WHEN** se calcula el hash de una contraseña con `BCRYPT_COST=12`
- **THEN** el hash empieza con `$2b$12$`

#### Scenario: Sal distinta por llamada

- **WHEN** se calcula dos veces el hash de la misma contraseña
- **THEN** los dos hashes son distintos y ambos verifican contra esa contraseña

### Requirement: Verificación de contraseña

La aplicación SHALL verificar una contraseña en claro contra un hash bcrypt devolviendo verdadero sólo si coinciden. Un hash malformado MUST tratarse como no coincidente, sin propagar un error.

#### Scenario: Contraseña correcta

- **WHEN** se verifica la contraseña original contra su hash
- **THEN** el resultado es verdadero

#### Scenario: Contraseña incorrecta

- **WHEN** se verifica otra contraseña contra ese hash
- **THEN** el resultado es falso

#### Scenario: Hash malformado

- **WHEN** se verifica una contraseña contra el texto `no-es-un-hash`
- **THEN** el resultado es falso y no se lanza excepción

### Requirement: bcrypt fuera del bucle de eventos y con concurrencia acotada

Todo cálculo o verificación bcrypt MUST ejecutarse en un hilo aparte, nunca en el bucle de eventos, y la cantidad de operaciones bcrypt simultáneas MUST estar limitada por un semáforo.

#### Scenario: El bucle sigue atendiendo

- **WHEN** hay un hash bcrypt en curso
- **THEN** `GET /health/live` responde sin esperar a que el hash termine

#### Scenario: Concurrencia limitada

- **WHEN** se lanzan más operaciones bcrypt simultáneas que el límite del semáforo
- **THEN** a lo sumo ese límite se ejecuta a la vez y el resto espera su turno
