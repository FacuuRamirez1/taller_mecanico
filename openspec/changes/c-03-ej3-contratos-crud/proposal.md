# Proposal — C-03 `ej3-contratos-crud`

## Why

El esquema ya existe (C-02), pero la API todavía no expone contratos: no hay schemas de entrada/salida, ni paginación uniforme, ni CRUD de repuestos y clientes, ni datos iniciales. El Ej. 3 (10 % de la nota) exige que todo lo que consumen C-04…C-08 tenga contratos HTTP estables, errores traducidos y un `seed.py` que deje el estado conocido del que dependen los 19 casos. Sin esta capa, autenticación, autorización, órdenes y N+1 no tienen sobre qué trabajar.

## What Changes

- **Schemas separados de los modelos** (`*/schemas.py`): toda entrada con `extra="forbid"`; ninguna salida con `password_hash`; `PATCH` con `exclude_unset=True`; alta de orden sin `precio`/`total`/`estado`/`creada_en`; alta de repuesto con `stock_inicial` (nunca `stock`); contraseña entre 8 caracteres y 72 bytes UTF-8.
- **Paginación uniforme** (`app/core/paginacion.py`): envoltorio `{items, total, page, size, pages}`; `page >= 1`; `size` 1..100 (default 20); página posterior a la última → **422** con mensaje propio; `total` con los mismos filtros que la página; con cero resultados, página vacía.
- **CRUD de repuestos** (`app/modules/repuestos/`): listado paginado con búsqueda por descripción con parámetros ligados, detalle, alta con `stock_inicial` → movimiento `"Stock inicial"`, `PATCH` de descripción/precio (rechaza `stock` con 422), baja lógica 204, reposición con movimiento `"Reposición"`, e historiales de movimientos y de precios.
- **Clientes y vehículos** (`app/modules/clientes/`): alta de cliente (201/409/422, sin `usuario_id`), detalle con sus vehículos vigentes (200/404), alta de vehículo (201/404/409/422), baja lógica de vehículo (204/404/409 si tiene órdenes abiertas) y `GET /mis-vehiculos` (200; su protección llega en C-05).
- **Errores transversales** (`app/core/errores.py` + handlers): `IntegrityError` → **409** con mensaje propio inspeccionando el nombre de la constraint (nunca un `SELECT` previo); 404 para el recurso de la ruta; 422 para contrato; ningún 500 con entrada inválida; `{id}` no entero → 422 sin ejecutar el handler.
- **`seed.py` completo de una sola vez**: `TRUNCATE ... RESTART IDENTITY CASCADE`, catálogo de 4 estados primero, 7 usuarios, 2 clientes (Laura con usuario y 2 vehículos; Jorge sin usuario y 1 vehículo), 4 repuestos con stock 10/4/2/20 como movimientos `"Stock inicial"`, órdenes 1 (`PENDIENTE`) y 2 (`EN_REPARACION`, 4 bujías con stock 2), historial de precio 8000 → 8500 y evento `SISTEMA`. Correrlo dos veces deja el mismo estado.
- **Casos en `test/*.http`**: `c01_parametro_invalido.http`, `c16_busqueda_paginacion.http`, `c19_baja_vehiculo.http`, cada uno con la respuesta esperada comentada.
- **Deuda declarada**: los services de C-03 usan `AsyncSession` directa y confirman al final; cada `service.py` lleva `# TODO C-06` para migrar a Router → Service → UoW → Repository sin cambiar contratos.

**Fuera de alcance**: login/JWT/cookies y RBAC (C-04/C-05); endpoints de órdenes, usuarios y eventos (C-04…C-06); repositorios, `UnitOfWork` y precarga declarada en repositorio (C-06); nuevas migraciones; `test/solo_agregado.sql` (C-07). Las rutas de C-03 quedan **sin `requiere_rol`**; C-05 las protege sin cambiar sus contratos.

## Capabilities

### New Capabilities

- `contratos-http`: schemas Pydantic de entrada/salida separados de los modelos para usuarios, clientes, repuestos y órdenes, con `extra="forbid"`, sin `password_hash` en salidas, `PATCH` parcial y reglas de contraseña.
- `paginacion`: envoltorio único de listados, validación de `page`/`size`, cálculo de `total` con los mismos filtros y respuesta 422 para páginas inexistentes.
- `errores-api`: traducción de `IntegrityError` a 409 con mensajes propios por constraint, 404/422 consistentes y garantía de que ninguna entrada inválida produce 500.
- `crud-repuestos`: endpoints de consulta, alta, modificación, baja lógica, reposición e historiales de repuestos, con el stock cambiando sólo por movimientos.
- `crud-clientes-vehiculos`: alta y consulta de clientes con sus vehículos, alta y baja lógica de vehículos y `GET /mis-vehiculos`.
- `seed-datos-iniciales`: carga idempotente del estado inicial conocido (catálogo, usuarios, clientes, vehículos, repuestos, movimientos, órdenes, historiales y evento de sistema).

### Modified Capabilities

- `entorno-desarrollo-local`: `seed.py` deja de ser un marcador `TODO C-03` y pasa a ser el cargador idempotente del estado inicial; la estructura deja de exigir módulos sin lógica.
- `ciclo-vida-aplicacion`: `main.py` monta los routers de dominio y garantiza que los cuatro módulos de modelos estén importados al arrancar, sin construir recursos al importar.

## Impact

- **Código nuevo**: `app/core/paginacion.py`, `app/core/errores.py`, `app/modules/usuarios/schemas.py`, `app/modules/clientes/{schemas,service,router}.py`, `app/modules/repuestos/{schemas,service,router}.py`, `app/modules/ordenes/schemas.py`, `seed.py` (reemplaza el stub), `test/c01_parametro_invalido.http`, `test/c16_busqueda_paginacion.http`, `test/c19_baja_vehiculo.http`.
- **Código modificado**: `main.py` (registro de routers e imports de modelos).
- **Base de datos**: no hay migraciones nuevas; el seed escribe sobre las 13 tablas existentes y usa `TRUNCATE ... RESTART IDENTITY CASCADE` porque el disparador de sólo agregado rechaza `DELETE`.
- **Dependencias**: ninguna nueva; se reutilizan `Settings`, `crear_engine`, `crear_sessionmaker`, `SessionDep` y `hash_password`.
- **Desbloquea**: C-04 (schemas de usuarios y login), C-05 (rutas a proteger), C-06 (órdenes, repositorios y UoW) y los casos `C-01`, `C-16`, `C-19`.
- **Governance ALTO**: los contratos los consumen C-04…C-08; un cambio acá rompe cuatro changes. `/opsx:apply` requiere aprobación explícita del usuario.
