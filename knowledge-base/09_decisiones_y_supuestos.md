# Decisiones y Supuestos

Este archivo separa dos cosas que suelen confundirse: lo que **ya está decidido** (por la consigna, por la cátedra o por el usuario) y lo que el equipo **asume sin haberlo probado**. Todo supuesto va marcado con **`Suposición:`** y tiene un riesgo asociado.

## Decisiones documentadas

### DD-01 — API REST backend-only, sin frontend
**Decisión**: el único artefacto es una API HTTP asincrónica. No hay frontend, ni HTML, ni BFF.
**Contexto**: la consigna evalúa capas, migraciones, autenticación, autorización, transacciones y lecturas; nada de eso requiere interfaz. El Discovery lo cierra explícitamente.
**Alternativas consideradas**: agregar una SPA mínima para "mostrar" el sistema.
**Justificación**: no suma nota y consume plazo (4 días). La verificación es con REST Client.
**Trade-offs aceptados**: la única evidencia de uso son archivos `.http` y capturas de consola/psql.

### DD-02 — Capas por módulo funcional, no por capa técnica
**Decisión**: `app/modules/<módulo>/{models,schemas,repository,unit_of_work,service,router}.py`, con `app/core/` para lo transversal. Módulos: `health`, `usuarios`, `clientes`, `repuestos`, `ordenes`.
**Contexto**: es la estructura obligatoria (págs. 9-10) y la corrección la verifica archivo por archivo.
**Alternativas consideradas**: `app/models/`, `app/routers/`, `app/services/` globales.
**Justificación**: cada módulo se puede asignar a una persona sin tocar los archivos de otra; el aislamiento es el que permite el paralelismo del equipo.
**Trade-offs aceptados**: duplicación de unidades de trabajo (una por módulo) y de imports.

### DD-03 — SQLModel para tablas + SQLAlchemy 2.0 async para consultas
**Decisión**: modelos con `SQLModel` (`table=True`), motor y sesión con SQLAlchemy 2.0 asincrónico, driver `asyncpg` 0.30.
**Contexto**: versión mínima fijada por la consigna; se acepta `psycopg` 3 asincrónico.
**Justificación**: `SQLModel` da el modelo y el schema base con poco código; SQLAlchemy aporta `selectinload`, `postgresql_where` y control del pool.
**Trade-offs aceptados**: `SQLModel` no cubre índices parciales con azúcar propia — se declaran con `__table_args__` y `Index(..., postgresql_where=...)`.

### DD-04 — El token viaja sólo en cookie `HttpOnly`
**Decisión**: `access_token` en cookie `HttpOnly`, `SameSite=Lax`, `Max-Age` = duración, `Secure` configurable. El cuerpo del login no trae el token y la dependencia no lee `Authorization`.
**Contexto**: exigencia de la consigna y del caso `C-03`. Un `Authorization: Bearer` debe dar **401**.
**Alternativas consideradas**: Bearer en el cuerpo o en el encabezado (las dos prohibidas).
**Justificación**: `HttpOnly` saca el token del alcance de JavaScript; `SameSite=Lax` frena CSRF básico.
**Trade-offs aceptados**: probar desde clientes que no manejan cookies requiere REST Client con cookie jar; `C-03` lo verifica explícitamente.

### DD-05 — Catálogo `estado_orden` en vez de un `CHECK` con la lista
**Decisión**: los estados son filas; `orden_trabajo.estado` es FK a `estado_orden.codigo`.
**Contexto**: la consigna lo pide (RN-19) y además `es_final` resuelve "orden abierta" para RN-16.
**Justificación**: el estado lleva datos propios (`posicion`, `es_final`) y la FK da integridad. La PK textual hace que `psql` y la API se lean igual.
**Trade-offs aceptados**: agregar un estado obliga a tocar catálogo (seed), enum y servicio. La migración crea la tabla vacía y **sin filas no se puede crear ninguna orden** (409).

### DD-06 — Unicidad parcial para patente y código
**Decisión**: índices únicos parciales `WHERE borrado_en IS NULL` para `vehiculo.patente` y `repuesto.codigo`; `UNIQUE` comunes para `usuario.email`, `cliente.documento` y `cliente.usuario_id`.
**Contexto**: `vehiculo` y `repuesto` tienen baja lógica. Un `UNIQUE` común impediría registrar un auto vendido con la misma patente (`C-19`).
**Justificación**: la base resuelve el caso sin lógica de aplicación.
**Trade-offs aceptados**: el índice no protege contra duplicados entre una fila vigente y una borrada, que es exactamente lo buscado.

### DD-07 — Sólo agregado en la base y `intento_acceso` aparte
**Decisión**: trigger en migración manual para las tres tablas de historial; `intento_acceso` se escribe en sesión y transacción propias que se confirman siempre.
**Contexto**: RN-15 y el caso `C-14` (6 rechazos en `psql`). El fallo de login que se quiere contar es el mismo que revierte la petición.
**Alternativas consideradas**: sólo permisos de rol de PostgreSQL (descartado: un solo rol de base); contar intentos en la misma transacción (imposible: se pierde el fallo).
**Justificación**: la garantía no depende de la aplicación; el conteo sobrevive al rollback.
**Trade-offs aceptados**: `intento_acceso` acumula filas aunque la petición falle; el trigger obliga a que `downgrade` borre función y trigger en orden.

### DD-08 — PostgreSQL 16 local, sin Docker
**Decisión**: base instalada en la máquina de cada integrante; `POSTGRES_HOST=localhost`, puerto estándar.
**Contexto**: decisión del usuario. La consigna no menciona contenedores.
**Alternativas consideradas**: `docker-compose` (más reproducible entre 4 personas).
**Justificación**: menos piezas para el plazo; el enunciado no lo pide.
**Trade-offs aceptados**: diferencias de versión/menor entre máquinas; se mitiga exigiendo PostgreSQL 16 y documentando la creación de la base en el `README`.

### DD-09 — `seed.py` es parte de la puesta en marcha
**Decisión**: script que vacía y recarga el estado inicial; se corre antes de cada archivo de pruebas.
**Contexto**: el catálogo de estados no es dato de ejemplo: sin él no se puede crear una orden.
**Justificación**: los 19 casos necesitan un estado determinista; sin seed, `C-10` y `C-11` dependen de lo que quedó de la corrida anterior.
**Trade-offs aceptados**: cada archivo `.http` exige correr el script; olvidarlo produce fallos confusos (`Suposición: SU-05`).

### DD-10 — Un change por ejercicio, plazo de 4 días y equipo de 4
**Decisión**: el roadmap se parte en 8 changes (uno por ejercicio) más los transversales de datos y entrega.
**Contexto**: decisión del usuario, no de la consigna.
**Justificación**: cada change coincide con una unidad corregible y con un peso de la grilla; permite asignar y cerrar por separado.
**Trade-offs aceptados**: los tres primeros ejercicios son **prerrequisito** de casi todo; el paralelismo real empieza en el Ej. 4. Ver `SU-04`.

### DD-11 — Defaults aceptados de configuración
Valores cerrados para no re-discutirlos en cada change. **No** son exigencias de la consigna salvo donde se indica.

| Clave | Valor | Dónde se documenta |
|---|---|---|
| `JWT_ALGORITHM` | **HS256** | `Settings`, `design.md` del Ej. 4 |
| `JWT_EXPIRE_SECONDS` | **1800** | Es el `expira_en_segundos` del ejemplo de login |
| `BCRYPT_COST` | **12** | `Settings` (la consigna exige que el costo **no** esté fijo en el código) |
| Contraseña mínima | **8 caracteres** | La consigna sólo fija el máximo |
| Contraseña máxima | **72 bytes** | Exigido: bcrypt no mira más allá y falla con excepción |
| Vaciado del seed | **`TRUNCATE ... RESTART IDENTITY CASCADE`** (corregido en C-02, OQ-1; antes `DELETE`) | `DELETE` lo rechaza el trigger de sólo agregado; `TRUNCATE` no activa triggers de fila y el trigger queda sin bypass |

**Justificación**: son decisiones de bajo impacto, reversibles y sin efecto en la corrección; fijarlas evita preguntas repetidas y roces entre las 4 personas.
**Trade-offs aceptados**: si la cátedra pidiera otro algoritmo o duración, se cambia una variable de entorno.

### DD-12 — Contraseña actual incorrecta en el cambio → 401
**Decisión**: `POST /auth/cambiar-password` responde **401** si la contraseña actual no coincide.
**Contexto**: la tabla de endpoints de esa ruta sólo admite `200, 401, 422`; no hay `403` disponible.
**Justificación**: es la única opción compatible con la tabla. `401` además comunica "la credencial presentada no es válida".
**Trade-offs aceptados**: semánticamente `403` sería más preciso, pero contradiría los códigos declarados. Anotado como decisión derivada, no como preferencia.

### DD-13 — Autorización por roles vigentes en cada petición
**Decisión**: `requiere_rol` consulta `asignacion_rol` en cada request; los roles del JWT son informativos y sólo se muestran en `/auth/yo`.
**Contexto**: RN-04 y `C-07` (revocar con la sesión abierta debe cortar el acceso en la petición siguiente).
**Alternativas consideradas**: confiar en los roles del token hasta su vencimiento (más barato, pero incumple RN-04).
**Justificación**: el token no puede ser la fuente de verdad de un permiso revocable.
**Trade-offs aceptados**: una consulta extra por petición autorizada.

### DD-14 — Se acepta la actualización perdida
**Decisión**: no hay locking ni control de concurrencia sobre el stock.
**Contexto**: la consigna lo saca de alcance explícitamente (capítulo 7).
**Justificación**: agregar `SELECT FOR UPDATE` cambiaría el alcance evaluado y sumaría riesgo sin nota.
**Trade-offs aceptados**: dos terminaciones simultáneas pueden sobrevender stock sin dejarlo negativo (el `CHECK stock >= 0` lo impide), que es exactamente el comportamiento declarado.

## Supuestos inferidos

### SU-01 — Los datos de seed que la consigna no fija
**Suposición:** las patentes, marcas, modelos, años, documentos, teléfonos, códigos y precios de los 4 repuestos se eligen **ficticios y consistentes con los 19 casos**; el único precio anclado es el del filtro de aceite (**8500**, por el historial 8000 → 8500).
**Origen**: la tabla "Datos iniciales" nombra los registros pero no sus atributos; `FIL-001`, `FRE-010`, `ACE-530`, `AC456EF` y los precios 32000/12000 aparecen en **respuestas de ejemplo**, no como datos obligatorios.
**Riesgo si es falso**: bajo. Los casos verifican comportamiento, no valores concretos; el riesgo es que un `.http` quede atado a un id concreto y se rompa si cambia el orden de carga.
**Cómo validar**: congelar los valores en `seed.py`, usar ids estables y referenciarlos desde los `.http`; confirmar con la cátedra si exige algún código en particular.

### SU-02 — Las líneas de historial de las órdenes del seed
**Suposición:** la orden 1 tiene 1 línea (`null → PENDIENTE`) y la orden 2 tiene 2 (`null → PENDIENTE`, `PENDIENTE → EN_REPARACION`); los movimientos de "Stock inicial" y el cambio de precio los firma `admin@example.com`.
**Origen**: el seed describe las órdenes y el historial de precios, pero no enumera las líneas de historial ni el `usuario_id` de cada escritura.
**Riesgo si es falso**: bajo, salvo que un caso cuente líneas de historial de las órdenes 1/2 (no lo hace: `C-12` verifica la línea **nueva**).
**Cómo validar**: revisar que `C-12` cuente sólo el delta, no el total.

### SU-03 — Qué roles son "el personal" en `GET /ordenes/{id}`
**Suposición:** ADMIN, RECEPCION y MECANICO.
**Origen**: la tabla de endpoints dice "El personal, o el dueño del vehículo" sin enumerar.
**Riesgo si es falso**: medio. Si "el personal" fuera sólo ADMIN + RECEPCION, un mecánico no podría ver la orden que debe reparar; si incluyera a cualquier autenticado, `C-06` (403 en la ajena) seguiría pasando pero se perdería el control.
**Cómo validar**: preguntar a la cátedra; mientras tanto, implementar como los tres roles de taller y dejar la constante en un solo lugar.

### SU-04 — El paralelismo del equipo no se pisa
**Suposición:** 4 personas sobre un mismo repositorio, en 4 días, no se pisan en los archivos core (`unit_of_work.py`, `dependencies.py`, `config.py`, `database.py` y los modelos).
**Origen**: decisión de equipo; no hay estrategia de ramas ni de propiedad de archivos definida.
**Riesgo si es falso**: **alto**. Un conflicto en `unit_of_work.py` o en los modelos arrastra auth, órdenes y stock, que son el 44 % de la nota (Ej. 5 + 6 + 7).
**Cómo validar**: asignar propiedad por módulo, congelar `app/core/` después del Ej. 1 y acordar que nadie toca modelos ajenos sin avisar.

### SU-05 — Los `.http` alcanzan como verificación
**Suposición:** los 19 casos se pueden demostrar con REST Client + `solo_agregado.sql`, sin pytest ni CI.
**Origen**: la consigna pide exactamente eso; el equipo no agrega tests automatizados.
**Riesgo si es falso**: medio. Depende de ejecución manual, de correr `seed.py` antes de cada archivo y de copiar bien las cookies entre pedidos.
**Cómo validar**: correr la suite completa dos veces seguidas desde cero (base vacía → migraciones → seed → los 19 archivos) antes de entregar.

### SU-06 — El plazo alcanza
**Suposición:** 4 días × 4 personas alcanzan para 8 ejercicios + 19 casos + 2 evidencias.
**Origen**: aritmética del Discovery: ~1,6 h por ejercicio a 8 h/día por persona, sin contar pruebas ni README.
**Riesgo si es falso**: **alto**. La condición de no corrección no distingue "no llegaste al Ej. 8" de "no arranca": un proyecto incompleto pero que levanta y migra se corrige; uno que no levanta, no.
**Cómo validar**: priorizar en este orden — (1) que arranque y migre, (2) Ej. 6 (20 %), (3) Ej. 4 (16 %), (4) Ej. 2 y 5 (14 % cada uno). Recortar prolijidad, no funcionamiento.

### SU-07 — La ventana de 60 s de RN-08
**Suposición:** se implementa como **ventana deslizante** de 60 s sobre los fallos, y el 6.º intento es el que recibe 429.
**Origen**: `C-05` dice "seis intentos fallidos seguidos: el sexto, 429"; RN-08 dice "después de 5 intentos fallidos … en 60 segundos".
**Riesgo si es falso**: bajo/medio. Con ventana fija por bloques, el 6.º podría caer en el bloque siguiente y no dar 429.
**Cómo validar**: correr `C-05` seis veces seguidas dentro del mismo minuto y confirmar 429 en el sexto.

### SU-08 — `needs_infra = false`
**Suposición:** el proyecto **no** requiere infraestructura aprovisionada: hay PostgreSQL 16, pero **local**, instalado a mano, sin Docker, sin deploy, sin colas ni servicios externos.
**Origen**: decisión del usuario y Discovery (entorno local, sin Docker). El contrato de la KB marca `needs_infra` cuando hay base, colas o despliegue; acá la base existe pero no se aprovisiona.
**Riesgo si es falso**: bajo. Si mañana se pidiera Docker o un entorno compartido, cambia el onboarding, no el código.
**Cómo validar**: si aparece `docker-compose` o un deploy en el alcance, revisar este valor.

### SU-09 — El `PATCH` que baja el precio
**Suposición:** un intento de bajar el precio se rechaza con **409** (choque con `CHECK precio_nuevo > precio_anterior`), no con 422.
**Origen**: la consigna fija el `CHECK` pero no el código de respuesta; la tabla de `PATCH /repuestos/{id}` admite `200, 404, 422` (no 409).
**Riesgo si es falso**: bajo, pero **hay una tensión real**: si se respeta la tabla, debería ser 422; si se respeta la semántica, 409. Queda como pregunta abierta.
**Cómo validar**: decidir antes del change del Ej. 6 y dejarlo escrito en el `design.md`.

### SU-10 — El orden por defecto de los listados
**Suposición:** `/ordenes`, `/eventos`, `/mis-ordenes` y `/repuestos` ordenan por `id` descendente (más reciente primero), salvo `/estados-orden`, que ordena por `posicion`.
**Origen**: la consigna sólo fija el orden del catálogo.
**Riesgo si es falso**: bajo; ningún caso depende del orden salvo `C-17`, que sí está cubierto.
**Cómo validar**: definir el orden en el repositorio (no en el servicio) y reflejarlo en el `design.md`.

## Riesgos abiertos (del Discovery)

| # | Riesgo | Impacto | Mitigación |
|---|---|---|---|
| R-01 | **Que no levante o no se corrija** | Anula todo: la condición de no corrección no distingue alcance incompleto de proyecto roto | Prioridad 1: el proyecto **siempre** corre y migra; humo test al cerrar cada change |
| R-02 | **Repositorios + UoW (20 %)** | Quién construye, abre, confirma y cierra es fácil de violar; arrastra auth, órdenes y stock | Tabla de responsabilidades de `08`, revisión cruzada del `unit_of_work.py` |
| R-03 | **Autenticación (16 %)** | El orden del login, el hash ficticio y el `iat` sin truncar se pierden "a ojo" | `07` flujo 1 y 7 como checklist; `C-04`, `C-05`, `C-09` |
| R-04 | **Migraciones y restricciones (14 %)** | Los 3 índices parciales y la migración manual del trigger | Escribir la segunda migración con `C-14` al lado |
| R-05 | **Autorización (14 %)** | Roles vigentes por petición, 401 vs 403, 403 antes que 409 | `C-06`, `C-07`, `C-13` |
| R-06 | **Lecturas sin N+1 (8 %)** | El detalle debe tener consultas fijas, con precarga en el repositorio | `C-15` con `SQL_ECHO` desde el primer día |
| R-07 | Equipo pisándose archivos core | Ver `SU-04` | Propiedad por módulo; `app/core/` congelado tras el Ej. 1 |
| R-08 | `.http` como única verificación | Ver `SU-05` | Corrida completa desde cero antes de entregar |
| R-09 | Cadena secuencial Ej. 1 → 2 → 3 | El paralelismo real empieza en el Ej. 4 | Empezar 4 y 5 en cuanto el esquema esté congelado |
| R-10 | Plazo de 4 días | Ver `SU-06` | Orden de prioridad por peso de la grilla |
