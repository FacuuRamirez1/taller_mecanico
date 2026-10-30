# Design

## Context

Ver `proposal.md` §Why. Estado observado en el repo al proponer (C-00/C-01/C-02 archivados):

- Esquema completo en 13 tablas, con nombres de constraint estables (`app/core/metadata.py`) e índices únicos parciales. `migrations/versions/0001_esquema_inicial.py` y `0002_solo_agregado.py` ya están aplicados; no hay migraciones nuevas en C-03.
- `app/core/config.py` expone `Settings` (sin defaults para los secretos); `app/core/database.py` expone `crear_engine`, `crear_sessionmaker`, `get_session` y `SessionDep`; `main.py` crea motor y sessionmaker en el lifespan y monta sólo `health_router`.
- Existen los cuatro `models.py` con relaciones `lazy="raise_on_sql"`; **no** existen `schemas.py`, `service.py`, `router.py` de dominio, ni `app/core/paginacion.py`.
- `seed.py` es un stub con `# TODO C-03`. `test/` sólo tiene `salud.http`.
- No hay `.env` en disco: el usuario debe crearlo antes de correr seed o pruebas.
- La consigna manda sobre KB y skills: `extra="forbid"`, `PATCH` con `exclude_unset=True`, stock sólo por movimientos, `IntegrityError` → 409 sin `SELECT` previo, `{id}` no entero → 422, ningún 500 con entrada inválida.

## Goals / Non-Goals

**Goals:**
- Congelar los contratos HTTP que consumen C-04…C-08 (campos, códigos, envoltorio de paginación y mensajes propios).
- Dejar `seed.py` idempotente y determinista para que los 19 casos sean reproducibles.
- Aislar la deuda de C-03 (servicios con `AsyncSession` directa) para que C-06 la reemplace sin tocar contratos.
- Cubrir `C-01`, `C-16` y `C-19` con archivos `.http` que declaren la respuesta esperada.

**Non-Goals:**
- Autenticación, JWT, cookies, RBAC y `requiere_rol`: C-04/C-05. Las rutas de C-03 quedan abiertas y se protegerán después.
- Endpoints de órdenes, usuarios, eventos y estados: C-04/C-05/C-06. Sólo se crean sus schemas.
- Repositorios, `UnitOfWork`, precarga declarada en repositorio y optimización N+1: C-06.
- Migraciones, triggers y `test/solo_agregado.sql`: cerrados en C-02 y C-07.
- Bloqueo optimista, `SELECT FOR UPDATE`, concurrencia y transacciones distribuidas.

## Decisions

### D1. Servicios con `AsyncSession` directa (deuda C-06)

Cada router recibe `SessionDep` y construye su servicio con la sesión (`RepuestoService(session)`, `ClienteService(session)`). El servicio ejecuta consultas y escrituras, y **confirma al final** de cada operación de escritura; ante excepción hace `rollback` y traduce el error. No hay repositorio ni UoW en C-03. Cada `service.py` lleva `# TODO C-06` y una nota de que la firma pública no cambia al migrar.

- **Por qué**: el scope de C-03 lo declara deuda explícita y C-06 es quien introduce Router → Service → UoW → Repository. Construir el UoW ahora duplicaría C-06 y rompería el orden del roadmap.
- **Alternativa descartada**: crear repositorios/UoW mínimos en C-03. Aumenta el riesgo de conflictos con C-06 y no lo pide el Ej. 3.
- **Regla conservada**: el router es el único que construye el servicio; ningún servicio construye recursos de infraestructura. El `commit` vive en el servicio sólo mientras no exista UoW.

### D2. Paginación (`app/core/paginacion.py`)

- `ParametrosPagina`: dependencia con `page: Annotated[int, Query(ge=1)] = 1` y `size: Annotated[int, Query(ge=1, le=100)] = 20`. Un valor fuera de rango lo rechaza FastAPI con **422** antes del handler.
- `Pagina[T]`: modelo genérico con `items: list[T]`, `total: int`, `page: int`, `size: int`, `pages: int`.
- `paginar(session, sentencia, page, size)`:
  1. Calcula `total` con `select(func.count()).select_from(sentencia.order_by(None).subquery())`, de modo que el conteo use **los mismos filtros** que la página.
  2. `pages = ceil(total / size)` (0 si `total == 0`).
  3. Si `total > 0` y `page > pages`, lanza `HTTPException(422, detail=f"La página {page} no existe: hay {pages}")`.
  4. Aplica `offset((page - 1) * size).limit(size)` y devuelve `Pagina`.
- **Cero resultados (Q-20)**: `total = 0`, `pages = 0`, `items = []` y **sin** 422, aunque `page` sea alta. La consigna pide "una página vacía"; se elige `pages = 0` porque no hay páginas con contenido. Es un cambio de una línea si la cátedra espera `1`.
- **Por qué un helper y no repetir en cada servicio**: el envoltorio y el mensaje de página inexistente son contrato uniforme (US-013) y `C-16` los verifica.

### D3. Traducción de errores (`app/core/errores.py`)

- `traducir_integrity_error(exc) -> HTTPException` obtiene el nombre de la constraint de `exc.orig.__cause__.constraint_name` (asyncpg) con respaldo en `exc.orig.diag.constraint_name`. Si no puede obtenerlo, usa un mensaje genérico.
- Mapa de constraints → `(status, mensaje)`:

| Constraint | Status | Mensaje propio |
|---|---|---|
| `uq_cliente_documento` | 409 | "Ya existe un cliente con ese documento" |
| `uq_cliente_usuario_id` | 409 | "Ese usuario ya tiene una ficha de cliente" |
| `ux_vehiculo_patente_vigente` | 409 | "Ya existe un vehículo vigente con esa patente" |
| `ux_repuesto_codigo_vigente` | 409 | "Ya existe un repuesto vigente con ese código" |
| `ck_repuesto_precio_positivo` | 422 | "El precio debe ser mayor que cero" |
| `ck_repuesto_stock_no_negativo` | 422 | "El stock no puede ser negativo" |
| `ck_movimiento_stock_cantidad_positiva` | 422 | "La cantidad debe ser mayor que cero" |
| `ck_historial_precio_repuesto_precio_nuevo_mayor_anterior` | 422 | "El nuevo precio debe ser mayor que el anterior" |
| `ck_vehiculo_anio_rango` | 422 | "El año del vehículo debe estar entre 1950 y 2100" |
| `fk_orden_trabajo_estado_estado_orden` | 409 | "El estado indicado no existe en el catálogo" |
| (desconocida) | 409 | "No se pudo completar la operación por un conflicto de datos" |

- **Nunca** se incluye `str(exc.orig)` ni la traza en la respuesta. Se registra el detalle sólo en el log del servidor.
- **Sin `SELECT` previo** para unicidad: se intenta la escritura y se traduce el error. La única lectura previa admitida es la del recurso de la ruta (404) y la del precio actual para decidir el 422 de una baja de precio (regla de negocio, no unicidad).
- **Baja de precio (IN-05 / Q-10)**: el servicio compara `precio_nuevo` con el actual y responde **422** con mensaje propio antes de escribir. Si igual llegara el `CHECK`, el mapa lo traduce a 422. Se elige 422 y no 409 porque la tabla de endpoints de `PATCH /repuestos/{id}` sólo declara `200, 404, 422`.
- **`{id}` no entero**: el parámetro de ruta se declara `id: int`; FastAPI responde **422** antes de ejecutar el handler (`C-01`). No se agrega un exception handler que lo convierta a 404.

### D4. Schemas por módulo

Todos los schemas de entrada usan `model_config = ConfigDict(extra="forbid")`. Los de salida usan `from_attributes=True` y **no** declaran `password_hash`.

| Archivo | Schemas |
|---|---|
| `usuarios/schemas.py` | `RolEnum` (`ADMIN`, `RECEPCION`, `MECANICO`, `CLIENTE`), `UsuarioCreate`, `UsuarioRead`, `AsignacionRolCreate`, `AsignacionRolRead`, `CambioPassword` |
| `ordenes/schemas.py` | `ItemOrdenCreate`, `OrdenCreate`, `ItemOrdenRead`, `OrdenRead`, `EstadoOrdenRead`, `HistorialEstadoOrdenRead` |
| `clientes/schemas.py` | `ClienteCreate`, `ClienteRead`, `ClienteDetalleRead`, `VehiculoCreate`, `VehiculoRead` |
| `repuestos/schemas.py` | `RepuestoCreate`, `RepuestoUpdate`, `RepuestoRead`, `ReponerStock`, `MovimientoStockRead`, `HistorialPrecioRead` |

- `UsuarioCreate`: `email`, `nombre`, `password`, `rol` opcional. `UsuarioRead`: `id`, `email`, `nombre`, `activo`, `debe_cambiar_password`, `password_cambiada_en`. **Nunca** `password_hash`.
- Validador de contraseña compartido: mínimo 8 caracteres y máximo 72 **bytes** UTF-8 (`len(v.encode("utf-8")) <= 72`). Se aplica en `UsuarioCreate`, `CambioPassword` y en cualquier schema de C-04 que reciba contraseña.
- `OrdenCreate`: `vehiculo_id`, `falla`, `items: list[ItemOrdenCreate]`. `ItemOrdenCreate`: `repuesto_id`, `cantidad`. **No** existen campos `precio`, `total`, `estado` ni `creada_en`; enviarlos da 422 por `extra="forbid"`.
- `RepuestoCreate`: `codigo`, `descripcion`, `precio` (`Decimal`, `gt=0`), `stock_inicial` (`int`, `ge=0`). No existe `stock`. `RepuestoUpdate`: `descripcion: str | None = None`, `precio: Decimal | None = Field(default=None, gt=0)`; el servicio aplica `model_dump(exclude_unset=True)`.
- `ReponerStock`: `cantidad: int` con `gt=0`.
- `ClienteCreate`: `nombre`, `documento`, `telefono`. **No** acepta `usuario_id` (Q-11 resuelto en el scope).
- `VehiculoCreate`: `patente`, `marca`, `modelo`, `anio` con `ge=1950, le=2100`. `VehiculoRead` agrega `id` y `cliente_id`.
- `ClienteDetalleRead` extiende `ClienteRead` con `vehiculos: list[VehiculoRead]`.
- Se normalizan `codigo` y `patente` con `strip()` y mayúsculas para que la unicidad parcial sea predecible; no se inventan formatos adicionales.

### D5. Contratos HTTP de C-03

| Método | Ruta | Cuerpo / query | Éxito | Errores |
|---|---|---|---|---|
| GET | `/repuestos` | `q`, `page`, `size` | 200 `Pagina[RepuestoRead]` | 422 |
| GET | `/repuestos/{id}` | — | 200 `RepuestoRead` | 404, 422 |
| POST | `/repuestos` | `RepuestoCreate` | 201 `RepuestoRead` | 409, 422 |
| PATCH | `/repuestos/{id}` | `RepuestoUpdate` | 200 `RepuestoRead` | 404, 422 |
| DELETE | `/repuestos/{id}` | — | 204 | 404, 422 |
| POST | `/repuestos/{id}/reponer` | `ReponerStock` | 200 `RepuestoRead` | 404, 422 |
| GET | `/repuestos/{id}/movimientos` | — | 200 `list[MovimientoStockRead]` | 404, 422 |
| GET | `/repuestos/{id}/precios` | — | 200 `list[HistorialPrecioRead]` | 404, 422 |
| POST | `/clientes` | `ClienteCreate` | 201 `ClienteRead` | 409, 422 |
| GET | `/clientes/{id}` | — | 200 `ClienteDetalleRead` | 404, 422 |
| POST | `/clientes/{id}/vehiculos` | `VehiculoCreate` | 201 `VehiculoRead` | 404, 409, 422 |
| DELETE | `/vehiculos/{id}` | — | 204 | 404, 409, 422 |
| GET | `/mis-vehiculos` | — | 200 `list[VehiculoRead]` | 422 |

- `RepuestoRead`: `id`, `codigo`, `descripcion`, `precio`, `stock`. No expone `borrado_en`.
- `MovimientoStockRead`: `id`, `repuesto_id`, `orden_id`, `usuario_id`, `cantidad`, `motivo`, `cuando`.
- `HistorialPrecioRead`: `id`, `repuesto_id`, `usuario_id`, `precio_anterior`, `precio_nuevo`, `cuando`.
- Los historiales se devuelven como lista simple ordenada por `cuando` descendente; **no** usan el envoltorio paginado porque la tabla de endpoints sólo declara 200/404 para esas rutas.
- `GET /mis-vehiculos` en C-03 responde **200** con `[]` y `# TODO C-05`: la identidad y el filtro por cliente llegan con la autenticación. El contrato de respuesta ya es `list[VehiculoRead]`.
- Orden por defecto (Q-17): repuestos por `id` descendente; vehículos por `id` ascendente; movimientos y precios por `cuando` descendente.

### D6. Servicio de repuestos

- `listar(q, page, size)`: `select(Repuesto).where(Repuesto.borrado_en.is_(None))`; si `q` viene, `Repuesto.descripcion.ilike(f"%{q}%")`. SQLAlchemy liga `q` como parámetro; no hay concatenación de SQL. Se ordena por `id` descendente y se pasa a `paginar`.
- `obtener(id)`: filtra `borrado_en IS NULL`; si no hay fila, 404.
- `crear(datos)`: resuelve el usuario actor (D8), crea `Repuesto(stock=datos.stock_inicial)`, `flush` para obtener el id; si `stock_inicial > 0`, crea `MovimientoStock(motivo="Stock inicial", orden_id=None, usuario_id=actor)`; `commit`; devuelve el repuesto. `stock_inicial = 0` no crea movimiento (Q-23).
- `actualizar(id, datos)`: carga el repuesto vigente; si viene `precio` y es **menor** al actual, lanza 422; si es **mayor**, actualiza el precio y agrega `HistorialPrecioRepuesto` en la misma transacción; si es igual, no agrega historial. Aplica sólo `exclude_unset`. `stock` nunca está en el schema, así que llega como 422 por `extra="forbid"`.
- `dar_baja(id)`: si no existe vigente, 404; escribe `borrado_en = now()`; `commit`; 204.
- `reponer(id, cantidad)`: repuesto vigente o 404; `stock += cantidad`; `MovimientoStock(motivo="Reposición", orden_id=None, usuario_id=actor)`; `commit`; devuelve el repuesto.
- `movimientos(id)` / `precios(id)`: repuesto vigente o 404; consulta ordenada por `cuando` descendente.
- Todas las escrituras hacen `try/except IntegrityError → rollback + traducir_integrity_error`.

### D7. Servicio de clientes y vehículos

- `crear_cliente(datos)`: inserta `Cliente` sin `usuario_id`; `commit`; traduce `uq_cliente_documento` a 409.
- `obtener_cliente(id)`: `select(Cliente).options(selectinload(Cliente.vehiculos)).where(Cliente.id == id)`; si no existe, 404; filtra en memoria los vehículos con `borrado_en` no nulo antes de serializar (Q-21: sólo vigentes).
- `crear_vehiculo(cliente_id, datos)`: verifica existencia del cliente (404); inserta `Vehiculo`; `commit`; traduce `ux_vehiculo_patente_vigente` a 409 y `ck_vehiculo_anio_rango` a 422.
- `dar_baja_vehiculo(id)`: busca el vehículo vigente (404); consulta si tiene órdenes abiertas con `select(OrdenTrabajo.id).join(EstadoOrden, OrdenTrabajo.estado == EstadoOrden.codigo).where(OrdenTrabajo.vehiculo_id == id, EstadoOrden.es_final.is_(False))`; si hay alguna, 409 con mensaje propio; si no, `borrado_en = now()` y `commit`; 204.
- `mis_vehiculos()`: en C-03 devuelve `[]`; `# TODO C-05` para inyectar el usuario autenticado y filtrar por su cliente.
- La consulta de órdenes abiertas es una lectura de negocio, no una verificación de unicidad; no reemplaza el índice parcial.

### D8. Actor de los movimientos y del historial de precios

`movimiento_stock.usuario_id` y `historial_precio_repuesto.usuario_id` son `NOT NULL`, pero C-03 todavía no tiene autenticación. El servicio resuelve un usuario actor interno: primero `admin@example.com`, y si no existe, el primer `ADMIN` vigente; si no hay ninguno, responde **409** con "No hay un usuario administrador para registrar la operación". Se marca `# TODO C-05: usar el usuario autenticado`. Esto mantiene los contratos sin aceptar `usuario_id` en el cuerpo.

### D9. `seed.py`

- Estructura: `async def main()` con `Settings()`, `crear_engine`, `crear_sessionmaker`; una sola sesión y una transacción; `TRUNCATE` de las 13 tablas con `RESTART IDENTITY CASCADE` (una sola sentencia con la lista literal); carga en orden de dependencias; `commit`; `engine.dispose()`.
- Orden de carga: `estado_orden` → `usuario` + `asignacion_rol` → `cliente` → `vehiculo` → `repuesto` + `movimiento_stock` ("Stock inicial") → `orden_trabajo` + `item_orden` + `historial_estado_orden` → `historial_precio_repuesto` → `evento_seguridad`.
- Contraseñas ficticias con `hash_password` de C-01 (fuera del bucle, `to_thread` + semáforo). No se documentan en la KB ni en el repo.
- Datos deterministas (supuestos, consistentes con `C-19` y el seed de KB 04):

| Entidad | Valores |
|---|---|
| Estados | `PENDIENTE` (1, no final), `EN_REPARACION` (2, no final), `TERMINADA` (3, final), `CANCELADA` (4, final) |
| Usuarios | `admin@example.com`, `admin2@example.com` (ADMIN); `recepcion@example.com`; `mecanico@example.com`, `mecanico2@example.com`; `cliente@example.com`; `nuevo@example.com` (MECANICO con `debe_cambiar_password = true`) |
| Clientes | Laura Gómez (`30111222`, `11-5555-0101`) con `cliente@example.com`; Jorge Pérez (`27888999`, `11-5555-0202`) sin usuario |
| Vehículos | Laura: `AC456EF` Toyota Corolla 2020 y `AB123CD` Ford Focus 2018; Jorge: `AA111AA` Fiat Cronos 2021 |
| Repuestos | `FIL-001` Filtro de aceite 8500 stock 10; `FRE-010` Pastillas de freno 45000 stock 4; `BUJ-001` Bujía 3200 stock 2; `ACE-530` Aceite por litro 9000 stock 20 |
| Movimientos | 4 × `"Stock inicial"` con la cantidad del stock, `orden_id` nulo, actor `admin@example.com` |
| Órdenes | Orden 1: `AC456EF`, `PENDIENTE`, 1 filtro ×1 (total 8500); Orden 2: `AA111AA`, `EN_REPARACION`, mecánico, 4 bujías ×3200 (total 12800) |
| Historial de estados | Orden 1: `null → PENDIENTE`; Orden 2: `null → PENDIENTE` y `PENDIENTE → EN_REPARACION` (usuario `recepcion@example.com`; la transición la firma `mecanico@example.com`) |
| Historial de precios | `FIL-001`: 8000 → 8500, actor `admin@example.com` |
| Evento | `actor = 'SISTEMA'`, `accion = 'Carga de los datos iniciales'` |

- **Por qué `TRUNCATE`**: el disparador de sólo agregado rechaza `DELETE` con filas (OQ-1 resuelto en C-02); `TRUNCATE` no activa disparadores de fila.
- **Por qué los precios y patentes son supuestos**: KB 04 los declara no fijados por la consigna; se eligen valores ficticios consistentes con `C-19` (misma patente tras la baja) y con el historial 8000 → 8500 del filtro.

### D10. `main.py`

- Se mantiene el lifespan sin cambios.
- Se agregan los imports explícitos de los cuatro módulos de modelos (`import app.modules.usuarios.models  # noqa: F401`, etc.) antes de incluir routers, para que SQLAlchemy configure todos los mapeos al arrancar.
- Se incluyen `repuestos_router` y los routers de clientes/vehículos/`mis-vehiculos`. `main.py` no contiene lógica de negocio.

### D11. Archivos `.http`

- `test/c01_parametro_invalido.http`: `GET /repuestos/abc`, `GET /clientes/abc`, `DELETE /vehiculos/abc` → **422** con la respuesta esperada comentada; nota de que el handler no se ejecuta.
- `test/c16_busqueda_paginacion.http`: búsqueda `q=' OR '1'='1` → 200 `total 0`; búsqueda filtrada con `page`/`size`; `PATCH` parcial de descripción; `PATCH` con `stock` → 422; `size=500` → 422; página fuera de rango → 422 con el mensaje exacto.
- `test/c19_baja_vehiculo.http`: baja de un vehículo sin órdenes → 204; alta de la misma patente para otro cliente → 201; segunda patente vigente igual → 409; baja de un vehículo con orden abierta → 409.
- Cada archivo empieza con la nota `# Ejecutar python seed.py antes de este archivo` y declara la respuesta esperada en un comentario.
- Variables `@baseUrl = http://localhost:8000`; los ids se toman de las respuestas del seed o de altas previas en el mismo archivo.

### D12. Verificación

- **Sin pytest**: la aceptación son comandos de CLI y `.http` de REST Client.
- RED→GREEN→TRIANGULATE por task: primero se corre la verificación y se registra el rojo, luego se implementa, luego se prueba con otra entrada.
- Verificación de seed sin exponer contraseñas: heredoc de Python que usa `Settings()` y `crear_sessionmaker` para contar filas; nunca imprime el `.env`.
- Cierre: `alembic upgrade head` sobre base vacía → `python seed.py` → conteos de KB 04 → `python seed.py` otra vez → mismos conteos → los tres `.http` en verde.
- La evidencia de `psql` la corre el usuario con prompt de contraseña; el agente no pasa la contraseña por línea de comandos.

## Risks / Trade-offs

- **[C-05 debe reemplazar el actor interno de D8]** → el contrato no cambia; sólo se sustituye la resolución por el usuario autenticado. Se marca `# TODO C-05` y se documenta en tasks.
- **[C-06 refactoriza servicios sin cambiar contratos]** → las firmas públicas y los schemas quedan congelados en `specs/`; C-06 sólo mueve la sesión a un UoW y las consultas a repositorios.
- **[Commit en el servicio]** → cada operación tiene un único `commit`; ante error se hace `rollback`. El riesgo de escritura parcial se acota a una operación y desaparece en C-06.
- **[Baja de precio 422 vs 409]** → se elige 422 por la tabla de endpoints (IN-05); si la cátedra espera 409, se cambia el mapa en `app/core/errores.py` sin tocar los schemas.
- **[`pages = 0` con cero resultados]** → decisión Q-20; si se espera `1`, es un cambio de una línea en `paginar`.
- **[`GET /mis-vehiculos` vacío en C-03]** → contrato estable; C-05 agrega la dependencia de sesión y el filtro, sin cambiar el schema de respuesta.
- **[Seed depende de un `.env` existente]** → sin `.env` el seed falla con el error de configuración de C-01; el usuario debe crearlo antes (C-00). No se commitea ningún `.env`.
- **[`TRUNCATE` es destructivo]** → es el comportamiento pedido para el seed; se ejecuta sólo sobre la base local de desarrollo.
- **[Datos ficticios no fijados por la consigna]** → se eligen valores deterministas y consistentes con `C-19`; quedan documentados en D9 y en `seed.py`.
- **[Rutas abiertas hasta C-05]** → riesgo asumido y declarado; C-05 las protege sin cambiar contratos.

## Migration Plan

1. Crear `app/core/paginacion.py` y `app/core/errores.py` (sin dependencias de dominio).
2. Crear los cuatro `schemas.py` y verificar que importan sin base.
3. Implementar `repuestos` (service + router) y verificar con `.http` y consultas.
4. Implementar `clientes` (service + router) y verificar con `.http` y consultas.
5. Registrar routers e imports de modelos en `main.py`.
6. Escribir `seed.py` y verificar dos corridas consecutivas contra los conteos de KB 04.
7. Escribir los tres `.http`, correr `alembic upgrade head` sobre base vacía + seed y cerrar los casos.
8. **Rollback**: revertir los archivos nuevos y el cambio de `main.py`; no hay migraciones que deshacer. La base puede quedar con datos del seed; volver a correr `alembic downgrade base && alembic upgrade head` la deja vacía.

## Open Questions

- **OQ-1 — Actor de movimientos hasta C-05**: resuelto en D8 con el usuario `admin@example.com` (o el primer ADMIN vigente). No cambia el contrato; C-05 lo reemplaza por el usuario autenticado.
- **OQ-2 — Texto exacto de los mensajes (Q-18)**: los mensajes de D3 son la propuesta; se pueden ajustar sin cambiar códigos ni schemas.
- **OQ-3 — `pages` con cero resultados (Q-20)**: se elige `0`; si la cátedra espera `1`, se cambia sólo el cálculo en `paginar`.

### Resolución de supuestos (task 0.1 — aceptados por el orquestador)

Los supuestos de este documento quedan **aceptados tal cual** antes de comenzar la implementación (governance ALTO, decisión registrada por el orquestador):

- **Q-20**: con cero resultados se devuelve **200** con `items = []`, `total = 0`, `pages = 0` y **sin** 422, aunque `page` sea alta (D2, OQ-3).
- **IN-05 / Q-10**: un `PATCH /repuestos/{id}` que **baja** el precio responde **422** con mensaje propio, sin modificar el precio ni agregar historial (D3, D6).
- **Q-21**: el detalle de cliente (`GET /clientes/{id}`) muestra **sólo los vehículos vigentes** (`borrado_en IS NULL`) (D7).
- **Q-23**: `stock_inicial = 0` en el alta de repuesto **no** crea movimiento de stock (D6).
- **D8 (actor interno)**: hasta C-05, los movimientos e historial de precios usan `admin@example.com` (o el primer `ADMIN` vigente); si no hay ninguno, **409** con mensaje propio.
- **D9 (datos del seed)**: se usan los valores ficticios y deterministas de la tabla de D9; el seed es idempotente por `TRUNCATE ... RESTART IDENTITY CASCADE`.
