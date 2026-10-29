# Visión y Objetivos

> **Proyecto**: Taller mecánico — órdenes de trabajo, stock y acceso con FastAPI y PostgreSQL.
> **Origen**: `docs/consigna.md` (extracción literal de `docs/TP_Cap1a6_Consigna.pdf`, 22 páginas), Discovery aprobado (`discovery/discovery.md`) y `state.discovery`.
> **Naturaleza**: trabajo práctico académico de Programación III (TUP), unidades 1 a 6. El "cliente" es la cátedra.

## Propósito del sistema

**Una única API REST asincrónica, backend-only, que digitaliza la operación diaria de un taller mecánico: alta de clientes y vehículos, órdenes de trabajo con repuestos, descuento de stock al terminar, catálogo administrado y personal con roles y vigencia.**

El taller coordina hoy su operación a mano: la recepción anota ingresos y fallas en papel, el mecánico no deja trazabilidad del repuesto que consumió, el stock se pierde entre reposiciones y no existe control de quién puede hacer qué. El sistema reemplaza ese registro por una base PostgreSQL 16 y una API en capas `Router → Service → UoW → Repository → Model`, delegando en la base las garantías que la base puede dar por sí sola: unicidad, integridad referencial, `CHECK` y sólo agregado.

El valor del proyecto no está en la interfaz (no hay frontend) sino en demostrar seis capacidades: capas que saben lo suyo, un esquema versionado con Alembic —incluida una migración escrita a mano—, autenticación sin bloquear el servidor ni revelar qué cuentas existen, autorización decidida en la base en cada petición, transacciones que agrupan todas las escrituras de una operación de negocio y lecturas sin N+1.

## Objetivos por actor

| Actor | Objetivo principal | Objetivos secundarios |
|---|---|---|
| **ADMIN** | Administrar el taller: catálogo de repuestos, stock, personal, roles y eventos de seguridad | Reponer stock, cambiar precios con historial, asignar y revocar roles con vigencia, consultar el historial de seguridad, terminar cualquier orden en reparación |
| **RECEPCION** | Abrir el ingreso: cliente, vehículo y orden de trabajo con falla e ítems | Consultar clientes con sus vehículos, listar y filtrar órdenes, cancelar órdenes, dar de baja vehículos sin órdenes abiertas, consultar repuestos |
| **MECANICO** | Tomar una orden pendiente, repararla y terminarla | Consultar repuestos y órdenes, ver el detalle de una orden; al terminar, el stock se descuenta solo |
| **CLIENTE** | Auto-registrarse y consultar el estado de sus vehículos y órdenes sin llamar al taller | Ver el detalle de sus propias órdenes, cancelar las propias mientras estén pendientes, cambiar su contraseña |
| **SISTEMA** | Registrar en el historial de seguridad los eventos que no ejecuta una persona (ej. la carga inicial) | — (es un **actor texto** en `evento_seguridad.actor`, no un usuario ni una fila de `usuario`) |

## Objetivos técnicos (los seis del enunciado)

1. **Capas**: construir una API asincrónica en capas `Router → Service → UoW → Repository → Model` donde cada capa sabe lo suyo y nada más.
2. **Esquema**: traducir un modelo con asociación, composición, uno a uno y una tabla de catálogo a un esquema relacional versionado con Alembic, incluida una migración escrita a mano.
3. **Autenticación**: contraseñas con bcrypt y token en cookie `HttpOnly`, sin frenar el servidor y sin revelar qué cuentas existen.
4. **Autorización**: consultar los roles en la base en cada petición, con vigencia, y distinguir siempre entre `401` y `403`.
5. **Transacciones**: agrupar en una sola transacción las escrituras de una operación de negocio, de modo que un fallo en el medio no deje datos a medias.
6. **Garantías en la base**: delegar unicidad, claves foráneas, comprobaciones y sólo agregado en PostgreSQL.

## Alcance v1.0

- **8 ejercicios obligatorios** (100 % de la nota): proyecto y ciclo de vida (8 %), modelos y migraciones (14 %), contratos y CRUD (10 %), autenticación (16 %), autorización (14 %), repositorios y Unit of Work (20 %), integridad (10 %), lecturas sin N+1 y asincronía (8 %).
- **13 tablas** del modelo de dominio con nombres y columnas obligatorios, 3 índices únicos parciales (`postgresql_where`), 1 catálogo (`estado_orden`) apuntado por FK y 3 tablas de sólo agregado protegidas por disparador.
- **2 migraciones** Alembic: la primera por `autogenerate` con todas las tablas; la segunda escrita a mano con el trigger. `upgrade head` → `downgrade base` → `upgrade head` sobre base vacía.
- **33 endpoints** de referencia en dos grupos de rutas (abierto y protegido), con token sólo en cookie.
- **`seed.py`** idempotente que deja la base en un estado inicial conocido (catálogo, 7 usuarios, 2 clientes, 3 vehículos, 4 repuestos, 2 órdenes, historial de precio y evento `SISTEMA`).
- **19 casos de prueba** `C-01` a `C-19` en `test/*.http` con la respuesta esperada comentada, más `test/solo_agregado.sql` para `C-14`.
- **Entregables**: `README.md` con los pasos desde cero, `requirements.txt`, `env.example`, `alembic.ini`, `migrations/`, `test/` y las dos evidencias (`C-14` en psql, `C-15` en consola).

## Fuera de alcance

- **Concurrencia y locking** (capítulo 7). Dos órdenes terminadas al mismo tiempo pueden leer el mismo stock y pisarse: es una actualización perdida, se acepta.
- **Colas de tareas con Redis** (capítulo 8). El aviso al cliente usa `BackgroundTasks` en el mismo proceso; si el proceso se reinicia, el aviso se pierde y no hay reintento.
- **Segundo mecanismo de sólo agregado** por permisos de rol de PostgreSQL: se describe en la cátedra pero no se pide (un solo rol de base).
- **Frontend, despliegue, CI y `docker-compose`**: no se piden. PostgreSQL 16 se instala local.
- **Tests automatizados con pytest**: los "casos de prueba" son archivos `.http` (extensión REST Client) y un `.sql`.
- **Edición del catálogo de estados por API**: se consulta, no se edita.
- **Apropiación de una ficha de cliente existente en el auto-registro**: si el documento ya existe, `409`.

## Métricas de éxito

El éxito se mide contra la grilla de corrección de la cátedra, no contra métricas de producto.

| Criterio | Peso | Qué se mira |
|---|---|---|
| Proyecto, configuración y ciclo de vida | 8 % | Estructura, `Settings` sin secretos por defecto, motor y fábrica en el lifespan, `get_session`, salud |
| Modelos, relaciones y migraciones | 14 % | Restricciones, índices únicos parciales, catálogo con FK, navegación, dos migraciones (una a mano), upgrade y downgrade |
| Contratos y CRUD | 10 % | Contratos separados, `extra="forbid"`, códigos, ninguna entrada inválida en 500, PATCH parcial, envoltorio de paginación |
| Autenticación | 16 % | bcrypt fuera del bucle y con semáforo, orden del login, límite, hash ficticio, cookie `HttpOnly` |
| Autorización | 14 % | 401 y 403, roles vigentes en la base, autoprotección, dos grupos de rutas, `iat`, lo propio |
| Repositorios y Unit of Work | 20 % | Dos jerarquías, clase del modelo, `flush` y no `commit`, precarga en el repositorio, quién crea/abre/confirma/cierra, operaciones de varias escrituras |
| Integridad | 10 % | Disparador de sólo agregado en las tres tablas; historial de precios en la misma transacción; intento de acceso en su propia sesión |
| Lecturas sin N+1 y asincronía | 8 % | Consultas fijas en el detalle; ninguna llamada bloqueante; aviso en segundo plano |

**Condición de no corrección** (anula todo lo anterior): un proyecto que no levanta, que no crea su esquema con `alembic upgrade head` sobre una base vacía, o que contiene credenciales reales en el repositorio **no se corrige hasta que se subsane**. Esto convierte "el proyecto arranca y migra" en la prioridad número uno del plan de trabajo.

**Verificación funcional**: los 19 casos `C-01` a `C-19` pasan ejecutándose a mano con REST Client, después de correr `python seed.py` antes de cada archivo.

## Restricciones de contexto

| Restricción | Valor | Origen |
|---|---|---|
| Plazo | **4 días** | Decisión del usuario (no de la consigna) |
| Equipo | **4 personas** | Decisión del usuario (no de la consigna) |
| Entorno de base | PostgreSQL 16 **local**, sin Docker | Decisión del usuario |
| Rol de base | Uno solo | Consigna (Ej. 7) |
| Objetivo | **Aprobar el TP**, no construir un producto | Decisión del usuario |
| Granularidad del roadmap | **Un change por ejercicio** | Decisión del usuario |

El plazo de 4 días para 8 ejercicios, 19 casos y 2 evidencias es el riesgo de calendario dominante: ver `09_decisiones_y_supuestos.md` y `10_preguntas_abiertas.md`.
