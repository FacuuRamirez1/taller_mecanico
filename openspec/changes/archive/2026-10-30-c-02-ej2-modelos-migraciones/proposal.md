# Proposal — C-02 `ej2-modelos-migraciones`

## Why

Todo lo que viene después (contratos, login, autorización, órdenes, integridad) lee y escribe sobre un esquema que todavía no existe: `migrations/versions/` está vacío y `SQLModel.metadata` no conoce ninguna tabla. El Ej. 2 (14 % de la nota) pide además que la base **garantice** lo que puede garantizar —unicidades, `CHECK`, el catálogo de estados por FK y el sólo agregado por disparador— y que el esquema nazca **sólo** de Alembic, con `upgrade head` / `downgrade base` / `upgrade head` funcionando sobre una base vacía. Si esa secuencia falla, el TP no se corrige (puerta dura del roadmap), por eso va ahora y antes que cualquier otro change.

## What Changes

- **Modelos de tabla de las 13 tablas** (no 12: `IN-01`) repartidos por módulo como manda la consigna:
  - `app/modules/usuarios/models.py`: `usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad`.
  - `app/modules/clientes/models.py`: `cliente`, `vehiculo`.
  - `app/modules/repuestos/models.py`: `repuesto`, `movimiento_stock`, `historial_precio_repuesto`.
  - `app/modules/ordenes/models.py`: `estado_orden`, `orden_trabajo`, `item_orden`, `historial_estado_orden`.
- Nombres de tabla y columna **literales** de la consigna; dinero en `NUMERIC(10,2)`/`NUMERIC(12,2)` mapeado a `Decimal`; todas las fechas `timestamptz`.
- Todas las restricciones del modelo de dominio: 9 `CHECK`, 5 `UNIQUE`, los **3 índices únicos parciales** con `postgresql_where`, FKs de `orden_trabajo.estado`, `historial_estado_orden.desde_estado`/`hasta_estado` a `estado_orden.codigo` (catálogo, no `CHECK`), índice propio en **toda** FK e índice compuesto `intento_acceso (email, ip, cuando)`.
- Navegación declarada en los dos extremos de cada relación; `Usuario.cliente` devuelve un objeto o `None`; `orden_trabajo ↔ item_orden` como composición. La carga perezosa queda deshabilitada a nivel de modelo para que una relación no precargada falle de forma explícita.
- Convención de nombres de restricciones en la metadata compartida, para que cada `CHECK`/`UNIQUE`/FK/índice tenga un nombre estable (lo usarán C-03/C-06 para traducir `IntegrityError` a 409/422 sin mostrar texto de la base).
- `migrations/env.py` final: importa los modelos de los cuatro módulos (retira el `TODO C-02`).
- `migrations/versions/0001_esquema_inicial.py`: generada con `alembic revision --autogenerate`, revisada a mano, con todas las tablas, restricciones e índices; crea `estado_orden` **vacía**; comentario de que se leyó antes de aplicar.
- `migrations/versions/0002_solo_agregado.py`: **escrita a mano**, función + disparador que rechazan `UPDATE`/`DELETE` en `historial_estado_orden`, `movimiento_stock` e `historial_precio_repuesto`; `downgrade` los elimina; comentario de que se leyó antes de aplicar.
- Sin `create_all` en ningún archivo. `seed.py` **sigue sin existir** como lógica (C-03): el catálogo queda vacío y crear una orden sin catálogo se verificará como 409 en C-06.

**Fuera de alcance**: schemas de entrada/salida, repositorios, UoW, servicios, routers y `seed.py` (C-03 en adelante); la demostración de los seis rechazos en `test/solo_agregado.sql` (C-07, `C-14`); la traducción de errores de la base a 409/422 (C-03/C-06, `IN-05`).

## Capabilities

### New Capabilities
- `modelo-usuarios-acceso`: tablas `usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad` con sus restricciones, el índice parcial de rol abierto y la navegación usuario ↔ roles/cliente.
- `modelo-clientes-vehiculos`: tablas `cliente` y `vehiculo`, el 1:1 opcional usuario–cliente y el índice parcial de patente vigente.
- `modelo-repuestos-stock`: tablas `repuesto`, `movimiento_stock`, `historial_precio_repuesto`, el índice parcial de código vigente y los `CHECK` de precio, stock y aumento de precio.
- `modelo-ordenes`: catálogo `estado_orden`, `orden_trabajo`, `item_orden`, `historial_estado_orden`, las FKs al catálogo y la composición orden–ítems.
- `migraciones-esquema`: cómo nace y se revierte el esquema (dos migraciones, convención de nombres, metadata completa en `env.py`, catálogo vacío, reversibilidad sobre base vacía, prohibición de `create_all`).
- `historiales-solo-agregado`: el disparador de base que rechaza `UPDATE`/`DELETE` sobre las tres tablas de sólo agregado (RN-15), venga de donde venga.

### Modified Capabilities
- `entorno-desarrollo-local`: el requisito "antes de C-02 la base queda sin tablas" y el escenario "`versions/` nace vacío" dejan de valer; pasan a exigir que el único esquema presente sea el creado por las migraciones.

## Impact

- **Código nuevo**: `app/core/metadata.py` (convención de nombres, sin lógica), 4 × `app/modules/<módulo>/models.py`, `migrations/versions/0001_esquema_inicial.py`, `migrations/versions/0002_solo_agregado.py`.
- **Código modificado**: `migrations/env.py` (imports de modelos). Posible ajuste mínimo de `migrations/script.py.mako` si la revisión autogenerada referencia tipos de `sqlmodel` (ver design).
- **Base de datos**: la base local `taller_mecanico` (PostgreSQL 16) pasa de vacía a 13 tablas + `alembic_version` + 1 función + 3 disparadores. La verificación exige partir de una base **vacía**.
- **Dependencias**: ninguna nueva (SQLModel 0.0.24, SQLAlchemy 2.0.55, Alembic 1.13.3, asyncpg 0.30 ya fijados).
- **Desbloquea**: C-03 (contratos y `seed.py`), C-04, C-05, C-06 y C-07 (demostración de `C-14`). Cubre la mitad de esquema de `C-14`, `C-17` y `C-19`.
- **Governance CRÍTICO**: modelos core que referencia todo lo demás + puerta dura de migraciones. `/opsx:apply` requiere aprobación explícita del usuario.
