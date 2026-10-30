# Tasks

> **Strict TDD en forma de verificación** (igual que C-00/C-01/C-02): no hay pytest; la aceptación son comandos de CLI, consultas a la base y archivos `.http` de REST Client. En cada task se corre **primero** la verificación y se registra el rojo (RED), luego se escribe el código mínimo hasta el verde (GREEN) y se repite con otra entrada (TRIANGULATE).
>
> **Convenciones**: todo se corre desde la raíz del repo con el venv activo (`source .venv/Scripts/activate`), nunca con el cwd dentro de `openspec/changes/*`. **Nunca** se abre, imprime ni edita el `.env`; ninguna contraseña va en la línea de comandos. `<PORT>` = el `POSTGRES_PORT` del `.env` (5433 en la máquina del proponente). Anteponer `SQL_ECHO=false` a los comandos de Python que tocan la base.
>
> **Ayudantes** (se pegan en la terminal; no se versionan):
> - **[S] seed**: `python seed.py` y luego un heredoc con `Settings()` + `crear_sessionmaker` que imprime `SELECT count(*)` por tabla; nunca imprime secretos.
> - **[Q] consulta**: heredoc que hace `e=crear_engine(Settings())`, `async with e.connect() as c: for f in (await c.execute(text(SQL))).all(): print(*f)` y `await e.dispose()`.
> - **[A] API**: `uvicorn main:app --reload` en una terminal y REST Client sobre `test/*.http` en otra. Cada archivo declara la respuesta esperada en un comentario.
> - **[P] psql (lo corre el usuario)**: `psql -h localhost -p <PORT> -U postgres -d taller_mecanico`; la contraseña se ingresa en el prompt o sale de `PGPASSWORD` ya exportada. El agente **no** ejecuta psql con contraseña.
>
> **Governance ALTO**: ante cualquier duda sobre contratos, campos o códigos, **parar y consultar al usuario**. Dueños sugeridos: A (grupos 1–3, 8), B (4.1), C (4.3, 4.4, 6, 7), D (4.2, 5).

## 0. Decisiones previas (con el usuario)

- [x] 0.1 Confirmar con el usuario los supuestos de `design.md`: **Q-20** (`pages = 0` con cero resultados), **IN-05/Q-10** (baja de precio → 422), **Q-21** (detalle de cliente sólo con vehículos vigentes), **Q-23** (`stock_inicial = 0` no crea movimiento), actor interno de movimientos (D8) y datos ficticios del seed (D9). Verificar: las respuestas quedan anotadas en `design.md` §Open Questions antes de empezar el grupo 2.

## 1. Precondiciones

- [x] 1.1 Verificar `.env` presente sin leerlo: `Test-Path .env` → `True`; `alembic current; echo "exit=$?"` → `0002 (head)` y `exit=0`. Si falta el `.env` o la base no responde, **parar**: crearlo o recrear la base lo decide y ejecuta el usuario.
- [x] 1.2 Línea de base (RED): `python -c "import app.core.paginacion"` falla con `ModuleNotFoundError`; `python -c "from app.modules.repuestos import schemas"` falla; `python -c "from app.modules.clientes import service"` falla; `grep -n "TODO C-03" seed.py` → presente.

## 2. Paginación (`app/core/paginacion.py`) — dueño A

- [x] 2.1 RED: `python -c "from app.core.paginacion import ParametrosPagina, Pagina, paginar, calcular_paginas"` falla.
- [x] 2.2 Crear `app/core/paginacion.py` con `ParametrosPagina` (`page: int = Query(1, ge=1)`, `size: int = Query(20, ge=1, le=100)`), `Pagina[T]` (`items`, `total`, `page`, `size`, `pages`), `calcular_paginas(total, size)` y `paginar(session, sentencia, page, size)` según design §D2. GREEN: `python -c "from app.core.paginacion import calcular_paginas as c; assert c(5,2)==3 and c(1,20)==1 and c(0,20)==0; print('ok')"`.
- [x] 2.3 TRIANGULATE: `paginar` con `total > 0` y `page > pages` lanza `HTTPException` 422 con `detail == "La página 3 no existe: hay 2"`; con `total = 0` y `page = 5` devuelve `items = []`, `pages = 0` y **no** lanza. Verificar con un heredoc que simule la sesión o con la integración de 6.4.

## 3. Errores (`app/core/errores.py`) — dueño A

- [x] 3.1 RED: `python -c "from app.core.errores import traducir_integrity_error"` falla.
- [x] 3.2 Crear `app/core/errores.py` con el mapa de constraints de design §D3 y `traducir_integrity_error(exc)` que lee `constraint_name` de asyncpg con respaldo en `diag`. GREEN: heredoc que construye un error falso por cada constraint del mapa y verifica `status_code` y `detail`; una constraint desconocida → 409 con el mensaje genérico.
- [x] 3.3 Verificación estática: `grep -n "duplicate key\|violates\|asyncpg" app/core/errores.py` sin coincidencias en los mensajes; `grep -c "uq_cliente_documento\|ux_vehiculo_patente_vigente\|ux_repuesto_codigo_vigente" app/core/errores.py` → al menos 3.

## 4. Schemas separados de los modelos — dueños B/C/D

- [x] 4.1 `app/modules/usuarios/schemas.py` (dueño B): `RolEnum`, `UsuarioCreate`, `UsuarioRead`, `AsignacionRolCreate`, `AsignacionRolRead`, `CambioPassword`, con el validador de contraseña de 8 caracteres a 72 bytes UTF-8 y `extra="forbid"` en las entradas. Verificar: `UsuarioRead` no declara `password_hash`; `UsuarioCreate(password="x"*7)` → `ValidationError`; `"x"*8` → válido; `"á"*40` (80 bytes) → `ValidationError`; un campo extra → `ValidationError`.
- [x] 4.2 `app/modules/ordenes/schemas.py` (dueño D): `ItemOrdenCreate` (`repuesto_id`, `cantidad`), `OrdenCreate` (`vehiculo_id`, `falla`, `items`), `ItemOrdenRead`, `OrdenRead`, `EstadoOrdenRead`, `HistorialEstadoOrdenRead`. Verificar: `OrdenCreate` acepta el cuerpo válido; `OrdenCreate` con `precio`, `total`, `estado` o `creada_en` → `ValidationError`; ningún schema de entrada declara esos campos.
- [x] 4.3 `app/modules/clientes/schemas.py` (dueño C): `ClienteCreate`, `ClienteRead`, `ClienteDetalleRead`, `VehiculoCreate`, `VehiculoRead`. Verificar: `ClienteCreate` no acepta `usuario_id` (`ValidationError`); `VehiculoCreate(anio=1949)` y `anio=2101` → `ValidationError`; `anio=1950` → válido; `ClienteDetalleRead` anida `vehiculos`.
- [x] 4.4 `app/modules/repuestos/schemas.py` (dueño C): `RepuestoCreate`, `RepuestoUpdate`, `RepuestoRead`, `ReponerStock`, `MovimientoStockRead`, `HistorialPrecioRead`. Verificar: `RepuestoCreate` acepta `stock_inicial` y rechaza `stock`; `precio=0` → `ValidationError`; `ReponerStock(cantidad=0)` → `ValidationError`; `RepuestoUpdate()` es válido (todos opcionales); `RepuestoRead` no declara `borrado_en`.
- [x] 4.5 Contrato estático: `grep -rn "password_hash" app/modules/*/schemas.py` sin coincidencias; `grep -c 'extra="forbid"' app/modules/*/schemas.py` coincide con la cantidad de schemas de entrada de cada archivo; `python -c "import app.modules.usuarios.schemas, app.modules.ordenes.schemas, app.modules.clientes.schemas, app.modules.repuestos.schemas"` → código 0 sin base.

## 5. `seed.py` completo — dueño D

- [x] 5.1 RED: `python seed.py` termina con código 0 pero **[Q]** `SELECT count(*) FROM estado_orden` → `0` (el stub no carga nada). Crear `seed.py` con `TRUNCATE ... RESTART IDENTITY CASCADE`, la carga en el orden de design §D9 y `hash_password` para las contraseñas ficticias. GREEN: `python seed.py; echo "exit=$?"` → `exit=0`; `grep -n "TODO C-03\|create_all" seed.py` sin coincidencias.
- [x] 5.2 Verificar el estado inicial con **[S]**: `estado_orden = 4`; `usuario = 7`; `cliente = 2`; `vehiculo = 3`; `repuesto = 4` con stocks `10, 4, 2, 20`; `movimiento_stock = 4` con motivo `"Stock inicial"` y `orden_id` nulo; `orden_trabajo = 2`; el ítem de la orden 2 tiene `cantidad = 4` y el stock de bujías sigue en `2`; `historial_estado_orden = 3`; `historial_precio_repuesto = 1` con `8000 → 8500`; `evento_seguridad = 1` con `actor = 'SISTEMA'`.
- [x] 5.3 Idempotencia: correr `python seed.py` una segunda vez y repetir **[S]**; los conteos y valores MUST ser idénticos. Verificar `grep -n "DELETE FROM" seed.py` sin coincidencias sobre las tres tablas de sólo agregado.
- [x] 5.4 Verificar roles y bandera: **[Q]** `SELECT u.email, a.rol, u.debe_cambiar_password FROM usuario u JOIN asignacion_rol a ON a.usuario_id=u.id WHERE a.revocada_en IS NULL ORDER BY 1` → 7 filas con los roles de design §D9; `nuevo@example.com` con `debe_cambiar_password = true`. No imprimir los hashes.

## 6. Repuestos (service + router) — dueño C

- [x] 6.1 RED: `python -c "from app.modules.repuestos import service, router"` falla.
- [x] 6.2 `app/modules/repuestos/service.py`: `RepuestoService(session)` con `listar`, `obtener`, `crear`, `actualizar`, `dar_baja`, `reponer`, `movimientos`, `precios` según design §D6; resolución del actor de D8; `commit`/`rollback`; `# TODO C-06` y `# TODO C-05` en el actor. Verificar: `grep -n "# TODO C-06" app/modules/repuestos/service.py` → presente; `grep -n "create_all\|session.delete\|DELETE FROM" app/modules/repuestos/service.py` sin coincidencias.
- [x] 6.3 `app/modules/repuestos/router.py`: `APIRouter(prefix="/repuestos", tags=["repuestos"])` con las 8 rutas de design §D5, `SessionDep` y construcción del servicio en el router. Registrar el router en `main.py`. GREEN: `python -c "import main"` → 0; `uvicorn main:app --reload` arranca y `GET /repuestos` responde 200.
- [x] 6.4 Crear `test/c16_busqueda_paginacion.http` con la respuesta esperada comentada y correrlo con **[A]** tras **[S]**: `q=' OR '1'='1` → 200 `total 0`; búsqueda filtrada → 200 con `total` coherente; `page` fuera de rango → 422 `La página N no existe: hay M`; `size=500` → 422; `PATCH` sólo de descripción → 200 y precio intacto; `PATCH` con `stock` → 422; aumento de precio → 200 + línea en `/precios`; baja de precio → 422; reposición → 200 + movimiento `"Reposición"`; `DELETE` → 204.
- [x] 6.5 TRIANGULATE: `GET /repuestos/{id}` del repuesto dado de baja → 404; alta con el mismo `codigo` tras la baja → 201; alta con `stock_inicial = 0` → 201 sin movimiento; `POST /repuestos/{id}/reponer` con `cantidad = 0` → 422; `GET /repuestos/abc` → 422.

## 7. Clientes y vehículos (service + router) — dueño C

- [x] 7.1 RED: `python -c "from app.modules.clientes import service, router"` falla.
- [x] 7.2 `app/modules/clientes/service.py`: `ClienteService(session)` con `crear_cliente`, `obtener_cliente`, `crear_vehiculo`, `dar_baja_vehiculo`, `mis_vehiculos` según design §D7; `selectinload` para los vehículos; chequeo de órdenes abiertas por `es_final`; `commit`/`rollback`; `# TODO C-06` y `# TODO C-05` en `mis_vehiculos`. Verificar: `grep -n "# TODO C-06\|# TODO C-05" app/modules/clientes/service.py` → presentes; `grep -n "create_all\|session.delete" app/modules/clientes/service.py` sin coincidencias.
- [x] 7.3 `app/modules/clientes/router.py`: routers `/clientes`, `/vehiculos` y `/mis-vehiculos` con las rutas de design §D5 y `SessionDep`. Registrar en `main.py`. GREEN: `python -c "import main"` → 0; `GET /clientes/1` responde 200 con sus vehículos; `GET /mis-vehiculos` responde 200 con `[]`.
- [x] 7.4 Crear `test/c19_baja_vehiculo.http` con la respuesta esperada comentada y correrlo con **[A]** tras **[S]**: baja de un vehículo sin órdenes → 204; alta de la misma patente para otro cliente → 201; segunda patente vigente igual → 409; baja de un vehículo con orden abierta → 409; `GET /clientes/{id}` ya no muestra el vehículo dado de baja.
- [x] 7.5 TRIANGULATE: `POST /clientes` con documento repetido → 409; con `usuario_id` → 422; `GET /clientes/{id}` inexistente → 404; `POST /clientes/{id}/vehiculos` con cliente inexistente → 404; con `anio = 1949` → 422; `DELETE /vehiculos/abc` → 422.

## 8. Integración y cierre — dueño A

- [x] 8.1 Crear `test/c01_parametro_invalido.http` con la respuesta esperada comentada y correrlo: `GET /repuestos/abc`, `GET /clientes/abc` y `DELETE /vehiculos/abc` → **422**; ninguna respuesta es 500 ni ejecuta el handler.
- [x] 8.2 Ciclo completo sobre base vacía: `alembic downgrade base && alembic upgrade head; echo "exit=$?"` → `exit=0`; `python seed.py` → `exit=0`; **[S]** coincide con 5.2; `python seed.py` otra vez → **[S]** idéntico. Confirmar `alembic current` → `0002 (head)` y `estado_orden` con 4 filas.
- [x] 8.3 Correr los tres `.http` (`c01`, `c16`, `c19`) después de un `python seed.py` fresco y verificar que cada respuesta coincide con el comentario esperado; registrar la salida como evidencia.
- [x] 8.4 Contrato estático transversal: `grep -rn "create_all" app/ main.py seed.py` sin coincidencias; `grep -rn "password_hash" app/modules/*/schemas.py` sin coincidencias; `grep -rn "execute(f\"\|execute(\"SELECT.*+\|text(f\"" app/modules/` sin coincidencias (búsqueda con parámetros ligados); `grep -c "# TODO C-06" app/modules/repuestos/service.py app/modules/clientes/service.py` → 1 en cada uno; `grep -rn "session.delete\|DELETE FROM" app/modules/` sin coincidencias (bajas lógicas).
- [x] 8.5 Verificar que `main.py` importa los cuatro módulos de modelos y monta los routers: `grep -n "app.modules.*models" main.py` → 4 coincidencias; `grep -n "include_router" main.py` → salud + repuestos + clientes/vehículos; `python -c "import main; print(sorted(r.path for r in main.app.routes))"` incluye `/repuestos`, `/clientes`, `/vehiculos`, `/mis-vehiculos`.
- [x] 8.6 Cierre documental: `openspec validate c-03-ej3-contratos-crud --strict` → válido; `openspec status --change "c-03-ej3-contratos-crud"` → todos los artefactos `done`.

## Workflow follow-up

- Archivar con `/opsx:archive c-03-ej3-contratos-crud` cuando 8.1–8.6 estén en verde (sincroniza las 6 specs nuevas y los deltas de `entorno-desarrollo-local` y `ciclo-vida-aplicacion`).
- Marcar `[C-03] ej3-contratos-crud` como `[x]` en `CHANGES.md` y avisar que los contratos quedaron congelados: C-04 (auth), C-05 (RBAC), C-06 (órdenes/repositorios/UoW) y C-08 pueden arrancar.
- Dejar anotado para C-05: reemplazar el actor interno de D8 por el usuario autenticado y proteger `/mis-vehiculos`; para C-06: mover `commit` a UoW y las consultas a repositorios sin cambiar firmas ni schemas.
- Commit sólo con pedido explícito del usuario, con conventional commits (`feat: C-03 contratos y CRUD`).
