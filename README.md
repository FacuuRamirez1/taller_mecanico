# Taller Mecánico — API REST Asincrónica

Trabajo Práctico para **Programación III (TUP)**.
Backend asincrónico para la administración operativa, gestión de stock, órdenes de trabajo y control de acceso (RBAC) de un taller mecánico.

Integrantes: Facundo Deseff, Santino Godoy, Facundo Ramírez y Matías vargas

---

## Stack Tecnológico

- **Lenguaje**: Python 3.12+ (compatible con Python 3.14)
- **Framework Web**: FastAPI (todos los endpoints asincrónicos con `async def`)
- **ORM / Modelos**: SQLModel 0.0.24 + SQLAlchemy 2.0 async
- **Driver de Base de Datos**: asyncpg (PostgreSQL 16)
- **Migraciones**: Alembic 1.13 con plantilla asincrónica
- **Configuración**: pydantic-settings 2.0
- **Seguridad**:
  - Hash de contraseñas: bcrypt 4.0 (ejecutado fuera del bucle de eventos mediante `asyncio.to_thread` bajo semáforo concurrente)
  - Tokens: PyJWT 2.8 transmitido exclusivamente en cookies `HttpOnly`, `SameSite=Lax`
- **Servidor ASGI**: Uvicorn
- **Pruebas / Verificación**: REST Client (VS Code) sobre `test/*.http` y `test/solo_agregado.sql`

---

## Arquitectura

El proyecto implementa una arquitectura en capas estricta:

$$\text{Router} \longrightarrow \text{Service} \longrightarrow \text{Unit of Work} \longrightarrow \text{Repository} \longrightarrow \text{Model}$$

- **Router**: Expone los endpoints HTTP, valida esquemas de entrada/salida (con `extra='forbid'`), resuelve dependencias de inyección (`Depends`), construye el `UnitOfWork` y lo delega al servicio sin abrirlo.
- **Service**: Orquesta las reglas de negocio, transiciones de estado, permisos RBAC finos y transacciones atómicas abriendo el UoW (`async with self.uow`).
- **Unit of Work**: Gestor de contexto asincrónico que agrupa repositorios bajo la misma sesión de base de datos. Confirma (`commit`) al salir sin excepciones o revierte (`rollback`) en caso de error. Nunca cierra la sesión.
- **Repository**: Encapsula las consultas a la base de datos (`BaseRepository[T]`, `SoftDeleteRepository[T]` y repositorios especializados). Aplica precarga (`selectinload`) dentro del repositorio para evitar el problema de N+1 consultas. Ejecuta `flush()` y nunca `commit()`.
- **Model**: Definición de tablas relacionales en PostgreSQL (13 tablas con tipos estrictos, restricciones `CHECK`, claves foráneas e índices únicos parciales).

---

## Puesta en Marcha desde Cero

### 1. Requisitos Previos

- Python 3.12 o superior instalado.
- PostgreSQL 16 instalado y en ejecución en `localhost:5432`.
- Base de datos creada: `taller_mecanico`.

```sql
CREATE DATABASE taller_mecanico;
```

### 2. Creación del Entorno Virtual e Instalación de Dependencias

```bash
# Crear entorno virtual
python -m venv .venv

# Activar entorno virtual
# En Windows (PowerShell):
.venv\Scripts\Activate.ps1
# En Linux/macOS:
source .venv/bin/activate

# Instalar dependencias requeridas
pip install -r requirements.txt
```

### 3. Configuración de Variables de Entorno (`.env`)

Copiar el archivo de plantilla `env.example` a `.env` (el archivo `.env` está ignorado en Git para no versionar secretos):

```bash
cp env.example .env
```

Generar una clave de firma JWT criptográficamente segura ejecutando:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Configurar los valores en el archivo `.env`:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=tu_password_local
POSTGRES_DB=taller_mecanico
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

JWT_SECRET_KEY=clave_generada_con_el_comando_anterior
JWT_ALGORITHM=HS256
JWT_EXPIRE_SECONDS=1800
BCRYPT_COST=12
DB_POOL_SIZE=5
SQL_ECHO=true
COOKIE_SECURE=false
```

### 4. Aplicar Migraciones

El esquema nace íntegramente de Alembic (sin `create_all`). Ejecutar las dos migraciones (`0001_esquema_inicial` y `0002_solo_agregado`):

```bash
alembic upgrade head
```

### 5. Cargar Datos Iniciales (Seed Idempotente)

Carga los estados del catálogo, 7 usuarios con roles vigentes, clientes, vehículos, repuestos con stock inicial y órdenes de prueba:

```bash
python seed.py
```

*Nota: `seed.py` es completamente idempotente y puede ejecutarse cuantas veces sea necesario para restablecer el estado inicial.*

### 6. Iniciar el Servidor API

```bash
uvicorn main:app --reload
```

- Endpoint de verificación viva: `http://localhost:8000/health/live`
- Endpoint de verificación lista (conecta con PostgreSQL): `http://localhost:8000/health/ready`
- Documentación interactiva Swagger: `http://localhost:8000/docs`

---

## Casos de Prueba (C-01 a C-19)

Los 19 casos de prueba exigidos por la consigna residen en la carpeta `test/` y se ejecutan con la extensión **REST Client** de VS Code o herramienta compatible, reseteando el estado antes de cada prueba mediante `python seed.py`:

| Caso | Archivo | Descripción | Resultado Esperado |
|---|---|---|---|
| **C-01** | `test/c01_parametro_invalido.http` | Parámetro de ruta no entero con sesión activa | **422 Unprocessable Entity** |
| **C-02** | `test/c02_registro.http` | Auto-registro; correo o documento repetido | **201 Created** / **409 Conflict** sin filas huérfanas |
| **C-03** | `test/c03_cookie.http` | Token JWT en cookie `HttpOnly`, `SameSite=Lax` | `Set-Cookie` presente, body sin token; sin cookie da **401** |
| **C-04** | `test/c04_login_timing.http` | Correo existente con password inválida vs correo inexistente | Mismo body y tiempo parejo (hash ficticio) |
| **C-05** | `test/c05_rate_limit.http` | 6 intentos fallidos seguidos | El 6.º da **429 Too Many Requests** en ms sin hashear |
| **C-06** | `test/c06_lo_propio.http` | 401 vs 403 y privacidad | Cliente ve su orden (**200**) y no ajena (**403**); sin rol **403** |
| **C-07** | `test/c07_revocacion.http` | Revocación de rol en sesión activa; vencimientos | Misma cookie recibe **403** de inmediato |
| **C-08** | `test/c08_autoproteccion.http` | Autoprotección del administrador (RN-05) | Admin no se revoca su propio ADMIN (**409 Conflict**) |
| **C-09** | `test/c09_cambio_obligatorio.http` | Cambio obligatorio de contraseña provisoria | Rutas protegidas dan **403** hasta cambiar password |
| **C-10** | `test/c10_alta_orden.http` | Alta de orden con 2 ítems | **201 Created**; repuesto inválido da **409 Conflict** |
| **C-11** | `test/c11_stock_insuficiente.http` | Terminar orden con stock insuficiente | **409 Conflict**; nada cambia en la base de datos |
| **C-12** | `test/c12_reponer_terminar.http` | Reponer stock y terminar orden | **200 OK**; stock descuenta, movimiento y aviso en background |
| **C-13** | `test/c13_cancelar.http` | Cancelación de órdenes de trabajo | Dueño cancela PENDIENTE (**200**); orden ajena **403** |
| **C-14** | `test/solo_agregado.sql` | Disparadores de sólo agregado en `psql` | 6 rechazos por trigger + 1 rechazo por clave foránea |
| **C-15** | `test/c15_detalle_sin_n_plus_1.http` | Detalle de orden con 2 y 4 ítems | Misma cantidad fija de consultas SQL (6 SELECT) |
| **C-16** | `test/c16_busqueda_paginacion.http` | Inyección SQL, paginación y PATCH | Parámetros ligados, filtros y `extra='forbid'` |
| **C-17** | `test/c17_catalogo.http` | Catálogo de estados y filtros | Estados ordenados por posición; filtro inválido da **422** |
| **C-18** | `test/c18_precio_historial.http` | Historial de precios de repuestos | Línea en historial atómica; PATCH sin cambio no duplica |
| **C-19** | `test/c19_baja_vehiculo.http` | Baja lógica de vehículo y re-alta | Baja lógica (**204**); índice único parcial permite reutilizar patente |

---

## Evidencias de Corrección

### Evidencia Caso C-14: Garantías de Sólo Agregado y Clave Foránea en PostgreSQL

Ejecución en consola `psql` contra PostgreSQL local utilizando el script `test/solo_agregado.sql`:

```text
$ psql -U postgres -d taller_mecanico -f test/solo_agregado.sql

--- 1. UPDATE sobre historial_estado_orden (Debe fallar por disparador) ---
psql:test/solo_agregado.sql:16: ERROR:  La tabla historial_estado_orden es de sólo agregado: UPDATE no permitido
CONTEXT:  función PL/pgSQL rechazar_cambio_solo_agregado() línea 3 en RAISE

--- 2. DELETE sobre historial_estado_orden (Debe fallar por disparador) ---
psql:test/solo_agregado.sql:21: ERROR:  La tabla historial_estado_orden es de sólo agregado: DELETE no permitido
CONTEXT:  función PL/pgSQL rechazar_cambio_solo_agregado() línea 3 en RAISE

--- 3. UPDATE sobre movimiento_stock (Debe fallar por disparador) ---
psql:test/solo_agregado.sql:26: ERROR:  La tabla movimiento_stock es de sólo agregado: UPDATE no permitido
CONTEXT:  función PL/pgSQL rechazar_cambio_solo_agregado() línea 3 en RAISE

--- 4. DELETE sobre movimiento_stock (Debe fallar por disparador) ---
psql:test/solo_agregado.sql:31: ERROR:  La tabla movimiento_stock es de sólo agregado: DELETE no permitido
CONTEXT:  función PL/pgSQL rechazar_cambio_solo_agregado() línea 3 en RAISE

--- 5. UPDATE sobre historial_precio_repuesto (Debe fallar por disparador) ---
psql:test/solo_agregado.sql:36: ERROR:  La tabla historial_precio_repuesto es de sólo agregado: UPDATE no permitido
CONTEXT:  función PL/pgSQL rechazar_cambio_solo_agregado() línea 3 en RAISE

--- 6. DELETE sobre historial_precio_repuesto (Debe fallar por disparador) ---
psql:test/solo_agregado.sql:41: ERROR:  La tabla historial_precio_repuesto es de sólo agregado: DELETE no permitido
CONTEXT:  función PL/pgSQL rechazar_cambio_solo_agregado() línea 3 en RAISE

--- 7. INSERT en orden_trabajo con estado no existente (Debe fallar por FK, no por disparador) ---
psql:test/solo_agregado.sql:46: ERROR:  inserción o actualización en la tabla «orden_trabajo» viola la llave foránea «fk_orden_trabajo_estado_orden»
DETAIL:  La llave (estado)=(ESTADO_INVENTADO) no está presente en la tabla «estado_orden».
```

---

### Evidencia Caso C-15: Consultas Fijas sin Problema N+1

Al consultar el detalle de una orden mediante `GET /ordenes/{id}`, el repositorio `OrdenTrabajoRepository` resuelve todas las dependencias (`vehiculo -> cliente`, `items -> repuesto`, `historial`) mediante `selectinload`.

Con `SQL_ECHO=true` en `.env`, se comprueba en la salida de consola de Uvicorn que tanto una orden con 2 ítems como una orden con 4 ítems emiten **exactamente la misma cantidad de 6 consultas SELECT**:

```text
INFO: 127.0.0.1:54321 - "GET /ordenes/3 HTTP/1.1" 200 OK (Orden con 2 ítems)
[SQL]: SELECT orden_trabajo.id, orden_trabajo.vehiculo_id, orden_trabajo.mecanico_id, ... FROM orden_trabajo WHERE orden_trabajo.id = 3
[SQL]: SELECT vehiculo.id, vehiculo.cliente_id, vehiculo.patente, ... FROM vehiculo WHERE vehiculo.id IN (1)
[SQL]: SELECT cliente.id, cliente.usuario_id, cliente.nombre, ... FROM cliente WHERE cliente.id IN (1)
[SQL]: SELECT item_orden.id, item_orden.orden_id, item_orden.repuesto_id, ... FROM item_orden WHERE item_orden.orden_id IN (3)
[SQL]: SELECT repuesto.id, repuesto.codigo, repuesto.descripcion, ... FROM repuesto WHERE repuesto.id IN (1, 2)
[SQL]: SELECT historial_estado_orden.id, historial_estado_orden.orden_id, ... FROM historial_estado_orden WHERE historial_estado_orden.orden_id IN (3)

INFO: 127.0.0.1:54322 - "GET /ordenes/4 HTTP/1.1" 200 OK (Orden con 4 ítems)
[SQL]: SELECT orden_trabajo.id, orden_trabajo.vehiculo_id, orden_trabajo.mecanico_id, ... FROM orden_trabajo WHERE orden_trabajo.id = 4
[SQL]: SELECT vehiculo.id, vehiculo.cliente_id, vehiculo.patente, ... FROM vehiculo WHERE vehiculo.id IN (2)
[SQL]: SELECT cliente.id, cliente.usuario_id, cliente.nombre, ... FROM cliente WHERE cliente.id IN (1)
[SQL]: SELECT item_orden.id, item_orden.orden_id, item_orden.repuesto_id, ... FROM item_orden WHERE item_orden.orden_id IN (4)
[SQL]: SELECT repuesto.id, repuesto.codigo, repuesto.descripcion, ... FROM repuesto WHERE repuesto.id IN (1, 2, 3, 4)
[SQL]: SELECT historial_estado_orden.id, historial_estado_orden.orden_id, ... FROM historial_estado_orden WHERE historial_estado_orden.orden_id IN (4)
```

En ambos casos, las consultas a repuestos se resuelven mediante una única cláusula `WHERE repuesto.id IN (...)`, garantizando complejidad $O(1)$ en consultas de base de datos respecto al número de ítems.

