# Discovery — Taller Mecánico (TP Programación III)

**Fecha**: 2026-10-27
**Fuentes investigadas**: ninguna URL de competidores (decisión del usuario). Fuente primaria: `TP_Cap1a6_Consigna.pdf` (22 páginas).
**Tipo de proyecto**: trabajo práctico académico (TUP — Tecnicatura Universitaria en Programación, Programación III, Unidad 1 a 6).

---

## 1. Problema que resuelve

Un taller mecánico coordina su operación a mano: la recepción anota ingresos y fallas en papel, el mecánico no deja trazabilidad del repuesto que consumió, el stock se pierde entre reposiciones, y no existe control de quién puede hacer qué dentro del taller.

El proyecto construye **una única API asincrónica en capas** que digitaliza ese flujo — alta de clientes y vehículos, órdenes de trabajo con repuestos, descuento de stock al terminar, catálogo administrado y personal con roles — apoyándose en PostgreSQL para las garantías que la base puede dar por sí sola (unicidad, claves foráneas, CHECK, sólo agregado).

**Contexto real**: el "cliente" es la cátedra. El problema está fijado por la consigna, no descubierto. El objetivo declarado por el usuario es **aprobar el TP**, no lanzar un producto.

## 2. Usuarios / roles

| Rol | Verbo principal |
|---|---|
| **ADMIN** | Administra — catálogo de repuestos, stock, personal, roles, eventos de seguridad |
| **RECEPCION** | Abre — clientes, vehículos, órdenes de trabajo |
| **MECANICO** | Repara — toma una orden, la termina, consume stock |
| **CLIENTE** | Consulta — se auto-registra, ve sus vehículos y órdenes, cancela las propias |
| **SISTEMA** | Audita — actor *texto* en `evento_seguridad`, no un usuario real |

Los roles viven en `asignacion_rol` (no hay columna `rol` en `usuario`), con vigencia y revocación sin borrado.

## 3. Casos de uso

1. **Como recepción**, quiero dar de alta un cliente, su vehículo y abrir la orden de trabajo con la falla y los repuestos, para que el mecánico tenga todo el contexto del ingreso.
2. **Como mecánico**, quiero tomar una orden pendiente y darla por terminada, para que al terminarla se descuente automáticamente el stock de cada repuesto usado.
3. **Como administrador**, quiero mantener el catálogo de repuestos, reponer stock y administrar al personal con sus roles y vigencias, para que el taller opere con datos correctos y permisos acotados.
4. **Como cliente**, quiero registrarme solo y consultar el estado de mis vehículos y mis órdenes, para no tener que llamar al taller.
5. **Como recepción / admin / dueño del vehículo**, quiero cancelar una orden pendiente, para liberar el trabajo cuando el cliente desiste.

## 4. Competidores / soluciones existentes

**No aplica.** Es un TP académico con alcance fijado por la cátedra: ninguna decisión de producto puede cambiar por analizar el mercado. Se documenta como ausencia consciente, no como hueco de investigación.

## 5. Funcionalidades necesarias

Los **8 ejercicios** de la consigna son todos mandatorios — existe una condición de *no corrección* (si el proyecto no levanta, no crea el esquema con `alembic upgrade head` sobre base vacía, o tiene credenciales en el repositorio, no se corrige hasta subsanarlo).

| Ej. | Contenido | Peso |
|---|---|---|
| 1 | Proyecto, configuración y ciclo de vida (Settings, motor en lifespan, `get_session`, salud live/ready) | 8 % |
| 2 | Modelos, relaciones y migraciones (restricciones, 3 índices únicos parciales, catálogo con FK, 2 migraciones — una a mano) | 14 % |
| 3 | Contratos y CRUD (`extra="forbid"`, códigos 201/204/404/409/422, PATCH parcial, paginación `{items,total,page,size,pages}`) | 10 % |
| 4 | Autenticación (bcrypt fuera del bucle con semáforo, orden del login, hash ficticio, cookie HttpOnly) | 16 % |
| 5 | Autorización (roles vigentes por petición, 401 vs 403, autoprotección, dos grupos de rutas, `iat` sin truncar) | 14 % |
| 6 | Repositorios y Unit of Work (`BaseRepository`/`SoftDeleteRepository`, `flush` no `commit`, quién construye/abre/confirma/cierra) | 20 % |
| 7 | Integridad (trigger de sólo agregado, `intento_acceso` en transacción propia) | 10 % |
| 8 | Lecturas sin N+1 y asincronía (carga anticipada en repositorio, `BackgroundTasks`) | 8 % |

Además: `seed.py` con los datos iniciales, los **19 casos de prueba** C-01 a C-19 en `.http` (+ `solo_agregado.sql`), `README.md`, `requirements.txt`, `env.example` y `alembic.ini`.

## 6. Funcionalidades opcionales

Excluidas **conscientemente**, en su mayoría porque la propia consigna las saca de alcance:

- **Concurrencia y locking** (capítulo 7) — fuera de alcance; se acepta la actualización perdida.
- **Colas de tareas con Redis** (capítulo 8) — fuera de alcance; el aviso se hace con `BackgroundTasks` in-process.
- **Segundo mecanismo de sólo agregado** por permisos de rol de PostgreSQL — la consigna lo describe pero no lo pide (el TP usa un solo rol de base).
- **Tests automatizados con pytest** — los "casos de prueba" son archivos `.http` (REST Client) y un `.sql`.
- **docker-compose** — no se menciona; se usa PostgreSQL 16 local.
- **Frontend** — no se pide.
- **Despliegue / CI** — no se pide.

## 7. Reglas de negocio

Veinte reglas explícitas (RN-01 a RN-20). Las de mayor impacto:

| Regla | Enunciado |
|---|---|
| **RN-01** | Email de usuario y documento de cliente únicos; patente y código de repuesto únicos **entre los vigentes** (índice único parcial); 409 con mensaje propio |
| **RN-02** | El auto-registro crea usuario + rol CLIENTE + ficha de cliente: o las tres filas o ninguna. Si el documento ya existe, 409 y **no se apropia de la ficha** |
| **RN-03** | A lo sumo una asignación abierta por rol (índice único parcial) |
| **RN-04** | Los permisos se deciden con los **roles vigentes en la base, en cada petición**; los del token son informativos |
| **RN-05** | Un admin no puede revocarse su propio ADMIN y el sistema **nunca queda sin administradores vigentes** (409) |
| **RN-06** | Con cambio de contraseña pendiente, sólo `/auth` y salud (403) |
| **RN-07** | Cambiar la contraseña invalida las sesiones anteriores **del mismo segundo inclusive**, salvo la que devuelve el propio cambio (`iat` comparado sin truncar) |
| **RN-08** | 5 fallos del mismo email desde la misma IP en 60 s → **429 sin verificar la contraseña**, con `Retry-After`; un login correcto reinicia la cuenta |
| **RN-09** | El login responde **lo mismo y tarda lo mismo** exista o no el correo (hash ficticio) |
| **RN-10** | La orden nace PENDIENTE, con ≥1 ítem, sin repuestos repetidos; el precio se copia del repuesto y el total lo calcula el servidor |
| **RN-11** | PENDIENTE → EN_REPARACION → TERMINADA; PENDIENTE → CANCELADA (409 si el estado no lo permite) |
| **RN-12** | Cancelan recepción, admin o dueño. **El permiso se evalúa antes que el estado** — 403 antes que 409 |
| **RN-13** | Terminar descuenta stock, deja un movimiento por salida y una línea de historial: **si un repuesto no alcanza, no queda ninguna** (409) |
| **RN-14** | El stock **sólo cambia por movimientos** (stock inicial, reposición, terminación); nunca por PATCH |
| **RN-15** | `historial_estado_orden`, `movimiento_stock` y `historial_precio_repuesto` son de **sólo agregado**, garantizado por disparador instalado en migración |
| **RN-16** | Borrado lógico en vehículo y repuesto; un vehículo con órdenes abiertas no se da de baja (409) |
| **RN-17** | Lo propio sólo pide estar autenticado (403 si es ajeno) |
| **RN-18** | **Ningún error devuelve texto interno de la base; ninguna entrada inválida termina en 500** |
| **RN-19** | Los estados son filas del catálogo; se consulta por API y no se edita desde ella. Catálogo vacío → crear orden da 409 |
| **RN-20** | Cada cambio de precio deja línea en `historial_precio_repuesto` **en la misma transacción**; un PATCH que no cambia el precio no deja línea |

## 8. Integraciones

**Ninguna externa.** El único efecto "fuera de la petición" es el aviso al cliente al terminar una orden, simulado con `BackgroundTasks` + `await asyncio.sleep(0.5)` y un mensaje en el registro — mismo proceso, sin cola, sin canal real.

## 9. Restricciones

**Stack obligatorio (versiones mínimas):** Python 3.12 · FastAPI 0.111 · SQLModel 0.0.24 · SQLAlchemy 2.0 asincrónico · asyncpg 0.30 (o psycopg 3 asincrónico) · PostgreSQL 16 · Alembic 1.13 (plantilla asincrónica) · pydantic-settings 2.0 · bcrypt 4.0 · PyJWT 2.8.

**Arquitectura:** `Router → Service → UoW → Repository → Model`, organización por módulo funcional (`health`, `usuarios`, `clientes`, `repuestos`, `ordenes`) con las mismas seis capas en todos.

**Nombres:** tablas y columnas son obligatorios (los usan los casos de prueba y la corrección). El modelo tiene **13 tablas**. Se pueden **agregar** columnas; no quitar ni renombrar.

**Prohibiciones explícitas:** `create_all` · carga perezosa · `commit()` en repositorios · que un servicio construya su UoW · token en el cuerpo o en `Authorization` · bcrypt dentro del bucle de eventos · SQL por concatenación · texto interno de la base en errores · verificar unicidad con consulta previa · editar stock por PATCH · editar el catálogo por API · `password_hash` en respuestas · aceptar campos no declarados · precio/total/estado/fecha en el alta de orden · secretos con valor por defecto en código · subir `.env`.

**Restricciones del usuario (no de la consigna):**

| Restricción | Valor |
|---|---|
| **Plazo** | **4 días** |
| **Equipo** | **4 personas** |
| Entorno | PostgreSQL 16 instalado local (sin Docker) |
| Rol de base | Uno solo |
| Objetivo | Aprobar el TP (no producto real) |
| Granularidad del roadmap | **Un change por ejercicio** de la consigna |

## 10. Riesgos

**Los cinco que preocupan al usuario, en orden de impacto:**

1. 🔴 **Que no levante / no se corrija.** Es el riesgo que anula todo lo demás: la condición de no corrección no distingue entre "no llegaste al ejercicio 8" y "no arranca". La prioridad #1 del roadmap es que el proyecto **siempre** corra y migre.
2. 🔴 **Repositorios + Unit of Work (20 %).** Quién construye el UoW, quién lo abre, quién confirma y quién cierra la sesión es fácil de violar sin darse cuenta, y una violación arrastra auth, órdenes y stock.
3. 🟠 **Autenticación (16 %).** El orden del login (límite de intentos **antes** de hashear), el hash ficticio para igualar tiempos, y el `iat` sin truncar son detalles que se pierden si se implementan "a ojo".
4. 🟠 **Migraciones y restricciones en la base (14 %).** Los tres índices únicos parciales (`postgresql_where`) y la segunda migración **escrita a mano** con el trigger: `autogenerate` no ve funciones ni disparadores.
5. 🟡 **Lecturas sin N+1 y asincronía (8 %).** El detalle de una orden tiene que resolverse con un número **fijo** de consultas, con la precarga declarada en el repositorio, no en el servicio.

**Supuestos sin probar** (detectados por assumption-mapping, no reportados por el usuario):

- ⚠️ Que **4 personas sobre un mismo repositorio en 4 días** no se pisen en los archivos core (`unit_of_work.py`, `dependencies.py`, `config.py`, `database.py`, y los modelos). No hay evidencia: no se definió estrategia de ramas ni de propiedad de archivos.
- ⚠️ Que **los `.http` de REST Client alcancen** para verificar los 19 casos sin pytest ni CI. Depende de ejecución manual y de reiniciar `seed.py` antes de cada archivo.
- ⚠️ Que el **paralelismo de 4 personas** conviva con una cadena de dependencias secuencial (Ej.1 → Ej.2 → Ej.3): los tres primeros ejercicios son prerrequisito de casi todo lo demás, así que el paralelismo real empieza recién en el Ej.4.
- ⚠️ Que el plazo de 4 días alcance para 8 ejercicios + 19 casos + 2 evidencias (capturas de C-14 en psql y C-15 en consola). La aritmética da ~1.6 hs por ejercicio a 8 hs/día.

## 11. Preguntas abiertas

**Cerradas por default aceptado** (a documentar en el `design.md` del change correspondiente, no a re-discutir):

- JWT con **HS256**, `exp` a **1800 s** (el ejemplo de la consigna).
- **bcrypt costo 12**, declarado en `Settings`.
- Contraseña: **mínimo 8 caracteres, máximo 72 bytes** (la consigna sólo fija el máximo).
- `seed.py` vacía con **`DELETE` en orden inverso de claves foráneas** (no `TRUNCATE`, que no dispara el trigger de fila).

**Sin resolver — bloquean el `design.md` del change que las toque:**

1. **Contrato exacto** de los endpoints que la consigna no ejemplifica: `POST /usuarios`, `GET /usuarios/{id}/roles`, `DELETE /usuarios/{id}/roles/{rol}` (200 sin body definido), `GET /eventos`, `GET /mis-vehiculos`, `GET /mis-ordenes`, `GET /estados-orden`, `GET /repuestos/{id}/movimientos`, `GET /repuestos/{id}/precios`, `DELETE /vehiculos/{id}`.
2. **`GET /ordenes/{id}`** — "el personal": ¿qué roles cuentan exactamente como personal? (¿ADMIN + RECEPCION + MECANICO?)
3. **RN-05** — "el sistema nunca queda sin administradores vigentes": ¿se controla sólo en la revocación de rol, o también al desactivar un usuario?
4. **RN-08** — la ventana de 60 s: ¿deslizante o fija? (C-05 dice que el **sexto** intento recibe 429).
5. **Datos de seed incompletos** — la consigna no da patentes, marcas, modelos, años, documentos, teléfonos, ni códigos y precios exactos de los 4 repuestos (los ejemplos `FIL-001` / `FRE-010` / `ACE-530` aparecen en respuestas de ejemplo, no como dato de seed obligatorio).
6. **Repositorio de sólo lectura del catálogo** (`EstadoOrden`) — qué métodos expone, dado que no hereda de `BaseRepository`.
7. **`POST /clientes`** — ¿el body puede traer `usuario_id`, o el cliente siempre se crea sin usuario?
8. **`GET /mis-ordenes`** — un usuario autenticado sin ficha de cliente: ¿lista vacía o error?
9. **Orden por defecto** de los listados (`/ordenes`, `/eventos`, `/mis-ordenes`, `/repuestos`) — la consigna no lo define.
10. **Duración de `exp`** y algoritmo JWT: cerrado por default (HS256/1800 s), pero la consigna no lo exige.
11. **Generación de la clave de firma** — el README tiene que explicar "cómo generarla" pero la consigna no indica el método esperado.
12. **Texto exacto de los mensajes de error** — se piden "mensajes propios" sin vocabulario fijado (salvo el ejemplo de paginación).
