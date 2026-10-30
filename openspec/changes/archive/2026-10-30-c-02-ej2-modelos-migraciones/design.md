# Design

## Context

Ver `proposal.md` §Why. Estado observado en el repo al proponer (tras archivar C-00 y C-01):

- `migrations/env.py`: plantilla asincrónica (`async_engine_from_config` + `NullPool`), URL desde `Settings().DATABASE_URL` con `%`→`%%`, `target_metadata = SQLModel.metadata`, `compare_type=True` y un `TODO C-02` que pide importar los modelos (sin esos imports `autogenerate` genera una revisión vacía).
- `alembic.ini`: `file_template = %%(rev)s_%%(slug)s`, sin `sqlalchemy.url`. Con `--rev-id 0001 -m esquema_inicial` el archivo resultante es `0001_esquema_inicial.py`.
- `migrations/script.py.mako`: importa `op` y `sqlalchemy as sa`; **no** importa `sqlmodel`. Si un modelo usa `str` sin `sa_type`, SQLModel lo mapea a `AutoString` y `autogenerate` escribe `sqlmodel.sql.sqltypes.AutoString()` → `NameError` al aplicar la migración.
- `migrations/versions/` sólo tiene `.gitkeep`. `app/modules/{usuarios,clientes,repuestos,ordenes}/` sólo tienen `__init__.py`. `seed.py` es `# TODO C-03`.
- Pines verificados en el venv: SQLModel 0.0.24 (`Field` acepta `sa_type`, `sa_column_kwargs`, `max_digits`/`decimal_places`, `foreign_key`, `index`, `unique`, `nullable`; `Relationship` acepta `back_populates` y `sa_relationship_kwargs`), SQLAlchemy 2.0.55, Alembic 1.13.3 (tiene `alembic check`), asyncpg 0.30.
- Base local: PostgreSQL 16, rol `postgres`, base `taller_mecanico`, hoy **sin tablas** (spec `entorno-desarrollo-local`). Puerto vía `.env` (5433 en la máquina del proponente; `env.example` dice 5432). Nadie lee ni imprime el `.env`.
- La consigna manda sobre KB y skills: nombres literales, 13 tablas, 3 índices parciales con `postgresql_where`, estados por FK al catálogo, dos migraciones (una autogenerada, otra a mano), catálogo vacío, `upgrade → downgrade base → upgrade`.

## Goals / Non-Goals

**Goals:**
- Que los cuatro dueños (B, C, D por módulo; A migraciones) escriban sus `models.py` en paralelo sin pisarse, con un **contrato de nombres de relaciones** fijado acá.
- Que `autogenerate` produzca una `0001` correcta al primer intento revisable (sin `AutoString`, sin tipos `ENUM`, con nombres de restricciones estables).
- Que la puerta dura sea verificable por comandos, la mayor parte sin `psql` (vía `Settings`, sin exponer contraseñas) y la evidencia `\d` la corra el usuario.

**Non-Goals:**
- Schemas Pydantic, enums de API (`RolEnum`, `EstadoOrdenEnum`), repositorios, UoW, servicios, routers: C-03 en adelante. Los modelos de C-02 no definen validadores de entrada.
- `seed.py` y la carga del catálogo: C-03.
- `test/solo_agregado.sql` y el `.http` de `C-14`: C-07 (acá sólo se prueba el disparador con una transacción descartable).
- Traducción de `IntegrityError` a 409/422 (`IN-05`, `Q-10`): C-03/C-06; acá sólo se garantiza que cada restricción tenga un nombre reconocible.
- Defensa en profundidad por permisos del rol de base (sección 6.9): no se pide.

## Decisions

### D1. Convención de nombres en la metadata compartida (`app/core/metadata.py`)

Un módulo sin I/O fija `SQLModel.metadata.naming_convention`:

| Tipo | Plantilla | Ejemplo |
|---|---|---|
| `pk` | `pk_%(table_name)s` | `pk_usuario` |
| `fk` | `fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s` | `fk_orden_trabajo_estado_estado_orden` |
| `uq` | `uq_%(table_name)s_%(column_0_N_name)s` | `uq_item_orden_orden_id_repuesto_id` |
| `ck` | `ck_%(table_name)s_%(constraint_name)s` | `ck_historial_precio_repuesto_precio_nuevo_mayor_anterior` |
| `ix` | `ix_%(column_0_label)s` | `ix_vehiculo_cliente_id` |

- **Por qué**: sin convención, PostgreSQL inventa nombres de `CHECK`/`UNIQUE` (`repuesto_precio_check`) y `autogenerate` no puede nombrarlos en el `downgrade`; además C-06 necesita distinguir *qué* `CHECK` falló (`IN-05`) sin parsear el texto de la base. Todos los nombres caben en 63 caracteres (el más largo, 57).
- Cada `models.py` hace `import app.core.metadata  # noqa: F401` **antes** de declarar tablas, así la convención rige sea cual sea el orden de importación. Asignar un diccionario a la metadata es configuración, no un recurso construido al importar (no choca con EA-08).
- **Alternativa descartada**: nombrar a mano cada restricción sin convención. Funciona para `CHECK`, pero deja PK/FK/UNIQUE con nombres implícitos y es fácil olvidar uno entre cuatro personas.

### D2. Mapeo de tipos

| Dominio | Declaración SQLModel | Tipo PostgreSQL |
|---|---|---|
| Ids | `id: int \| None = Field(default=None, primary_key=True)` | `INTEGER` autoincremental (`SERIAL`) |
| Texto | `str` con `sa_type=sa.Text` | `TEXT` |
| Dinero | `Decimal` con `max_digits=10, decimal_places=2` (o 12,2 en `total`) | `NUMERIC(10,2)` / `NUMERIC(12,2)` |
| Fechas | `datetime` con `sa_type=sa.DateTime(timezone=True)` | `timestamptz` |
| Booleanos | `bool` con `server_default` `true`/`false` | `BOOLEAN NOT NULL` |
| `rol`, `estado` | `str` (texto) | `TEXT` + `CHECK` (rol) / `TEXT` + FK (estado) |

- `sa.Text` en **todos** los `str`: evita `AutoString` en la migración (Context) y sigue la regla de la skill `postgresql-table-design` (TEXT para strings). Un `CHECK` de longitud no lo pide la consigna; los límites viven en los schemas de C-03.
- `rol` y `estado` **no** son `Enum` de Python en el modelo de tabla: SQLModel crearía un tipo `ENUM` de PostgreSQL, que la consigna no pide (el rol es `CHECK`, el estado es FK) y que `downgrade` deja huérfano. Los enums viven en los schemas (C-03).
- `ip` como `TEXT` (KB: "texto o INET, inferido"): evita conversión en el servicio de login; no hay consultas por rango de red.
- PK `INTEGER` y no `BIGINT IDENTITY` (sugerencia de la skill): volumen de TP, es lo que SQLModel/`autogenerate` producen sin `sa_column` manual, y los ids se exponen tal cual en la API. Desvío consciente de la skill.
- Columnas con default en la base (`cuando`, `desde`, `creada_en` → `now()`; `activo` → `true`; `debe_cambiar_password` → `false`) usan `sa_column_kwargs={"server_default": ...}` y `nullable=False`. Todas las tablas declaran `__mapper_args__ = {"eager_defaults": True}` para que el `INSERT ... RETURNING` traiga esos valores: con `expire_on_commit=False` y sesión asincrónica, leer un default no cargado dispararía un refresco implícito (error `MissingGreenlet`).

### D3. Restricciones e índices declarados en el modelo (no en la migración)

Todo se declara en `__table_args__` o en `Field` para que `autogenerate` lo vea:

- **CHECK** (nombre lógico → nombre final por D1): `asignacion_rol.rol_valido`, `vehiculo.anio_rango`, `repuesto.precio_positivo`, `repuesto.stock_no_negativo`, `orden_trabajo.total_no_negativo`, `item_orden.cantidad_positiva`, `item_orden.precio_unitario_positivo`, `movimiento_stock.cantidad_positiva`, `historial_precio_repuesto.precio_nuevo_positivo`, `historial_precio_repuesto.precio_nuevo_mayor_anterior`.
- **UNIQUE** (restricción, no índice): `usuario.email`, `cliente.documento`, `cliente.usuario_id`, `estado_orden.posicion`, `item_orden (orden_id, repuesto_id)`.
- **Índices únicos parciales** (`sa.Index(..., unique=True, postgresql_where=sa.text(...))` con nombre explícito): `ux_asignacion_rol_usuario_id_rol_abierta`, `ux_vehiculo_patente_vigente`, `ux_repuesto_codigo_vigente`. La patente y el código **no** llevan `unique=True` en el `Field`.
- **Índice compuesto**: `ix_intento_acceso_email_ip_cuando` sobre `(email, ip, cuando)`.
- **Índice en toda FK**: `Field(foreign_key=..., index=True)` en las 18 FK, salvo `cliente.usuario_id`, cuyo índice es el de su `UNIQUE`. `asignacion_rol.usuario_id` lleva índice propio aunque exista el parcial (el parcial no cubre las filas revocadas). `item_orden.orden_id` lleva índice propio aunque sea la primera columna del `UNIQUE` compuesto: la consigna dice "cada clave foránea lleva un índice" y preferimos que se vea literal en `\d` antes que ahorrar un índice redundante (la skill sugiere evitarlo; desvío consciente, a confirmar en 0.1).
- **FK sin `ON DELETE`** (= `NO ACTION`) en todas: en este sistema nada se borra físicamente (bajas lógicas, roles revocados, historiales de sólo agregado); un `CASCADE` chocaría con el disparador y escondería errores.

### D4. Contrato de relaciones (navegación en los dos extremos)

Regla uniforme: **cada FK tiene navegación en los dos extremos**, con `back_populates` y `lazy="raise_on_sql"`. Los nombres son contrato entre módulos (los usan C-03…C-08 en `selectinload`):

| FK | Lado "uno" (escalar) | Lado "muchos" (colección) | Notas |
|---|---|---|---|
| `asignacion_rol.usuario_id` | `AsignacionRol.usuario` | `Usuario.asignaciones` | `foreign_keys` explícito (hay dos FK a `usuario`) |
| `asignacion_rol.otorgada_por` | `AsignacionRol.otorgante` | `Usuario.asignaciones_otorgadas` | `foreign_keys` explícito |
| `cliente.usuario_id` | `Cliente.usuario` | `Usuario.cliente` (**escalar**, `uselist=False`) | 1:1 opcional |
| `vehiculo.cliente_id` | `Vehiculo.cliente` | `Cliente.vehiculos` | |
| `orden_trabajo.vehiculo_id` | `OrdenTrabajo.vehiculo` | `Vehiculo.ordenes` | |
| `orden_trabajo.mecanico_id` | `OrdenTrabajo.mecanico` | `Usuario.ordenes_asignadas` | |
| `orden_trabajo.estado` | `OrdenTrabajo.estado_catalogo` | `EstadoOrden.ordenes` | `estado` es la columna; la relación no puede llamarse igual |
| `item_orden.orden_id` | `ItemOrden.orden` | `OrdenTrabajo.items` | `cascade="all, delete-orphan"` (composición) |
| `item_orden.repuesto_id` | `ItemOrden.repuesto` | `Repuesto.items` | |
| `historial_estado_orden.orden_id` | `HistorialEstadoOrden.orden` | `OrdenTrabajo.historial` | |
| `historial_estado_orden.desde_estado` | `HistorialEstadoOrden.estado_desde` | `EstadoOrden.transiciones_desde` | `foreign_keys` explícito |
| `historial_estado_orden.hasta_estado` | `HistorialEstadoOrden.estado_hasta` | `EstadoOrden.transiciones_hasta` | `foreign_keys` explícito |
| `historial_estado_orden.usuario_id` | `HistorialEstadoOrden.usuario` | `Usuario.transiciones` | |
| `movimiento_stock.repuesto_id` | `MovimientoStock.repuesto` | `Repuesto.movimientos` | |
| `movimiento_stock.orden_id` | `MovimientoStock.orden` | `OrdenTrabajo.movimientos` | |
| `movimiento_stock.usuario_id` | `MovimientoStock.usuario` | `Usuario.movimientos_stock` | |
| `historial_precio_repuesto.repuesto_id` | `HistorialPrecioRepuesto.repuesto` | `Repuesto.historial_precios` | |
| `historial_precio_repuesto.usuario_id` | `HistorialPrecioRepuesto.usuario` | `Usuario.cambios_precio` | |

- **Imports entre módulos**: anotaciones como string (`"Cliente"`) con los imports reales bajo `if TYPE_CHECKING:`; sin `from __future__ import annotations` (SQLModel 0.0.24 no lo soporta bien en relaciones). SQLAlchemy resuelve los nombres al configurar los mapeos, por eso **los cuatro módulos de modelos deben estar importados** antes de la primera consulta (`env.py` los importa; en la app los importan los routers de C-03+, ver Risks).
- **`lazy="raise_on_sql"`** en todas las relaciones: la consigna prohíbe la carga perezosa; con esta opción, leer una relación no precargada falla con un error explícito en vez de un `MissingGreenlet` críptico, y un `selectinload` del repositorio la sobreescribe por consulta. `raise_on_sql` (y no `raise`) permite resolver un muchos-a-uno que ya está en el identity map sin SQL. **Alternativa descartada**: dejar el `lazy="select"` por defecto (en async falla igual, pero con un error que no señala la causa).
- **Composición**: `OrdenTrabajo.items` con `cascade="all, delete-orphan"`: agregar ítems a una orden nueva los persiste con ella (C-06 arma la orden y sus ítems en un solo bloque). No hay `ON DELETE CASCADE` en la base (D3).

### D5. Dónde vive cada modelo y quién lo escribe

| Archivo | Tablas | Dueño |
|---|---|---|
| `app/core/metadata.py` | (convención) | A |
| `app/modules/usuarios/models.py` | `Usuario`, `AsignacionRol`, `IntentoAcceso`, `EventoSeguridad` | B |
| `app/modules/clientes/models.py` | `Cliente`, `Vehiculo` | C |
| `app/modules/repuestos/models.py` | `Repuesto`, `MovimientoStock`, `HistorialPrecioRepuesto` | C |
| `app/modules/ordenes/models.py` | `EstadoOrden`, `OrdenTrabajo`, `ItemOrden`, `HistorialEstadoOrden` | D |
| `migrations/env.py`, `migrations/versions/*` | — | A |

Clases en singular y `PascalCase`, `__tablename__` explícito y literal (`"orden_trabajo"`, no el default de SQLModel `"ordentrabajo"`). Cada dueño declara las dos puntas de las relaciones **que toca su archivo** según D4; las puntas en otro módulo las escribe el dueño de ese módulo con los mismos nombres.

### D6. `env.py` final

Se reemplaza el `TODO C-02` por:

```python
import app.core.metadata  # noqa: F401  (convención de nombres)
from app.modules.usuarios import models as _usuarios  # noqa: F401
from app.modules.clientes import models as _clientes  # noqa: F401
from app.modules.repuestos import models as _repuestos  # noqa: F401
from app.modules.ordenes import models as _ordenes  # noqa: F401
```

El resto de `env.py` no cambia (`compare_type=True` ya está). No se agrega `compare_server_default` (genera falsos positivos con `now()`).

### D7. Migración `0001_esquema_inicial` (autogenerate + revisión)

- Se genera con `alembic revision --autogenerate --rev-id 0001 -m esquema_inicial` sobre la base **vacía**.
- Revisión obligatoria antes de aplicar (checklist en tasks 6.x): 13 `create_table`; ningún `sqlmodel.` en el archivo (si apareciera, se corrige el modelo con `sa_type=sa.Text`, no la plantilla); los 10 `CheckConstraint` con nombre; las 5 `UniqueConstraint`; los 3 `create_index(..., unique=True, postgresql_where=...)`; un `create_index` por FK; `server_default=sa.text('now()')` en las fechas; ninguna `op.execute`/`bulk_insert` (catálogo vacío); `downgrade` con `drop_index`/`drop_table` en orden inverso; ningún `sa.Enum`.
- Se edita sólo para agregar el docstring/comentario `# Migración leída y revisada antes de aplicarla (C-02).` y, si hiciera falta, reordenar. Cualquier corrección de contenido se hace **en el modelo** y se regenera, para que la migración siga siendo producto de `autogenerate`.

### D8. Migración `0002_solo_agregado` (a mano)

- Se crea con `alembic revision --rev-id 0002 -m solo_agregado` (sin autogenerate; `down_revision = "0001"`) y se completa con `op.execute(...)` de SQL **constante** (sin datos de usuario; no aplica la regla de concatenación).
- `upgrade`:
  - `CREATE FUNCTION rechazar_cambio_solo_agregado() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'La tabla % es de sólo agregado: % no permitido', TG_TABLE_NAME, TG_OP; END; $$;`
  - Por cada tabla (`historial_estado_orden`, `movimiento_stock`, `historial_precio_repuesto`), escrito explícito tres veces: `CREATE TRIGGER trg_<tabla>_solo_agregado BEFORE UPDATE OR DELETE ON <tabla> FOR EACH ROW EXECUTE FUNCTION rechazar_cambio_solo_agregado();`
- `downgrade`: `DROP TRIGGER IF EXISTS trg_<tabla>_solo_agregado ON <tabla>;` ×3 y `DROP FUNCTION IF EXISTS rechazar_cambio_solo_agregado();`.
- **`FOR EACH ROW`** y no `FOR EACH STATEMENT`: el rechazo nombra la tabla igual, y un `UPDATE`/`DELETE` que no afecta filas no falla (relevante para el vaciado del seed sobre tablas vacías, ver Open Questions).
- **SQLSTATE**: el `RAISE EXCEPTION` por defecto (`P0001`, `raise_exception`), no un código de la clase 23: así un rechazo del disparador no se confunde con una violación de integridad que la app traduce a 409. El mensaje no incluye datos de la fila.
- `TRUNCATE` **no** se bloquea: la consigna pide `UPDATE` y `DELETE`.

### D8b. Comentario "leída antes de aplicar"

Ambas migraciones llevan en el docstring y como comentario la frase `Leída antes de aplicarla` con el nombre de quien la revisó (consigna Ej. 2: "cada migración se lee antes de aplicarla y lleva un comentario que lo diga").

### D9. Estrategia de verificación (sin pytest, sin contraseñas)

- **Verificaciones automáticas** (las puede correr el agente): `python` con heredoc que construye el motor con `Settings()` y `crear_engine` (la contraseña nunca aparece en el comando ni en la salida) y consulta `information_schema`, `pg_indexes`, `pg_constraint` y `pg_trigger`. Las pruebas de restricciones y del disparador corren **dentro de una transacción que termina en `ROLLBACK`** (o con `SAVEPOINT` por intento), así la base queda vacía y la puerta dura sigue partiendo de cero.
- **Evidencia `\d` en psql** (la corre el **usuario**): `psql -h localhost -p <PORT> -U postgres -d taller_mecanico` pide la contraseña por prompt (o la toma de `PGPASSWORD` ya exportada en su sesión); **nunca** se pasa en la línea de comandos.
- Ciclo RED→GREEN→TRIANGULATE como en C-00/C-01: cada verificación se corre antes de escribir el código (rojo), después (verde) y con una entrada distinta (triangulación).

## Risks / Trade-offs

- **[Base no vacía al empezar]** → Task 1.1 verifica `0` tablas en `public` y `alembic current` sin revisión. Si hay restos, **parar**: recrear la base (`dropdb`/`createdb`) es destructivo y lo decide y ejecuta el usuario.
- **[`autogenerate` vacío o parcial porque falta un import]** → D6 + task 6.2 cuenta 13 `create_table` antes de aplicar.
- **[`AutoString`/`sqlmodel` en la migración → `NameError`]** → D2 (`sa.Text` en todo `str`) + grep en la revisión de `0001`.
- **[Tipos `ENUM` huérfanos tras `downgrade`]** → D2 (sin `Enum` en modelos de tabla) + verificación `pg_type` tras `downgrade base`.
- **[Ambigüedad de FK múltiples (`usuario` ×2 en `asignacion_rol`, `estado_orden` ×2 en historial)]** → `foreign_keys` explícito (D4) + task que corre `configure_mappers()`.
- **[Choques entre dueños por nombres de relaciones]** → contrato D4; integración (task 5.x) la hace A con `configure_mappers()` antes de generar `0001`.
- **[Mapeos no configurables en la app si un router importa sólo su módulo]** → hoy no aplica (no hay routers de dominio); C-03 debe importar los cuatro `models` al arrancar (nota en Workflow follow-up de tasks).
- **[`lazy="raise_on_sql"` sorprende a quien no precarga]** → es el comportamiento buscado (consigna: carga perezosa prohibida); el error aparece en desarrollo, no en la corrección.
- **[Defaults del servidor no cargados tras el `INSERT`]** → `eager_defaults=True` (D2).
- **[Índice redundante en `item_orden.orden_id`]** → costo despreciable; se prioriza la lectura literal de la consigna (a confirmar en 0.1).
- **[Seed vs. disparador]** → ver Open Questions; no bloquea C-02 pero sí C-03.
- **[Contraseña expuesta al verificar con psql]** → D9: el agente no usa psql con contraseña; el usuario usa prompt/`PGPASSWORD` de su sesión.

## Migration Plan

1. Base vacía confirmada (1.1). 2. Modelos por módulo (2–4) e integración (5). 3. `0001` autogenerada, leída, aplicada (6). 4. `0002` a mano, leída, aplicada (7). 5. Puerta dura: `upgrade head` → `downgrade base` → `upgrade head` + evidencia `\d` (8). **Rollback**: `alembic downgrade base` deja la base como estaba (sin datos que perder: el seed todavía no existe). Si `0001` sale mal antes de commitear, se borra el archivo, `downgrade base` y se regenera.

## Open Questions

- **OQ-1 — Vaciado del seed vs. disparador — RESUELTA: el usuario aprobó `TRUNCATE ... RESTART IDENTITY CASCADE` en `seed.py` (C-03); el disparador queda SIN bypass; `DD-11` corregido en KB 04/06/09 y CHANGES.md (C-03).** `DD-11`/`06 US`/`CHANGES C-03` dicen "`DELETE` en orden inverso de FK (no `TRUNCATE`, que no dispara el trigger de fila)". Con el disparador de D8, un `DELETE` sobre `movimiento_stock`/`historial_*` **con filas** es rechazado: el seed funcionaría la primera vez (tablas vacías, el disparador de fila no se activa) y **fallaría desde la segunda corrida**, que es justamente lo que pide "correr `python seed.py` antes de cada `.http`". Propuesta: el seed vacía con `TRUNCATE ... RESTART IDENTITY CASCADE` (que no activa disparadores de fila y es lo que la consigna no prohíbe) y se corrige `DD-11` en la KB. Alternativas: (b) el disparador admite un bypass por variable de sesión (`SET LOCAL`), que debilita "venga de donde venga"; (c) el seed hace `ALTER TABLE ... DISABLE TRIGGER` (requiere ser dueño de la tabla). La opción elegida **no cambia** C-02 salvo en (b).
- **OQ-2 — Confirmaciones de bajo impacto — RESUELTA: el usuario aprobó las cuatro tal como están en D2/D3/D4/D8**: `lazy="raise_on_sql"` (D4), PK `INTEGER` (D2), índice explícito en `item_orden.orden_id` (D3), SQLSTATE `P0001` del disparador (D8). Todas reversibles con una nueva migración o un cambio de modelo antes de C-03.
