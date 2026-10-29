# Flujos Principales

Cada flujo se documenta extremo a extremo, con el reparto de responsabilidades entre capas y los casos de error. Las referencias `[RN-xx]` apuntan a `05_reglas_de_negocio.md`; los `[C-xx]` a `06_funcionalidades.md`.

**Convención de capas en todos los flujos**

```
HTTP → Router (contrato + UoW por dependencia) → Service (reglas, abre el UoW)
     → UoW (commit/rollback, no cierra la sesión) → Repository (flush, precarga)
     → Model → PostgreSQL
```
El router **construye** el UoW y **no lo abre**. El servicio lo **abre** con `async with` y **nunca lo construye**. La sesión la cierra `get_session`.

---

## Flujo 1 — Login

**Disparador**: `POST /auth/login`
**Actor**: cualquiera (ruta abierta)
**Reglas**: RN-08, RN-09

### Pasos

1. **Router**: valida el contrato (`email` con formato, `password` de hasta 72 bytes, `extra="forbid"`). Inválido → **422**.
2. **Servicio**: abre una **sesión y transacción propias** para `intento_acceso` (no la de la petición).
3. **Límite primero** [RN-08]: cuenta los fallos del **mismo email y la misma IP** en los últimos **60 s** sobre `intento_acceso` (`exito = false`). Es **una** consulta.
4. Si hay **5 o más** → **429** con `Retry-After`, **sin calcular ni verificar ningún hash**. La respuesta llega en pocos milisegundos `[C-05]`.
5. **Búsqueda del usuario** por email.
6. **Verificación** — siempre se ejecuta un bcrypt, exista o no el correo:
   - si el usuario existe y está activo → verifica contra `password_hash`;
   - si no existe → verifica contra el **hash ficticio** calculado una vez en el lifespan.
   - La llamada va a `to_thread` **bajo el semáforo** (nunca en el bucle de eventos).
7. **Anota el intento** (`exito = true/false`) en la transacción propia del paso 2 y **la confirma siempre**, incluso si el login falla [RN-08, Ej. 7].
8. **Fallo** → **401** con el **mismo cuerpo** que un correo inexistente `[C-04]`. **Nunca** se distingue "no existe" de "contraseña mala" [RN-09].
9. **Éxito** → emite el JWT con `sub`, `iat` (hora completa, **con fracciones**), `exp` (`iat` + 1800 s) y los **roles vigentes** consultados en la base.
10. Responde **200** con `{mensaje, debe_cambiar_password, expira_en_segundos}` y el token **sólo** en `Set-Cookie` (`HttpOnly`, `SameSite=Lax`, `Max-Age`, `Secure` configurable) `[C-03]`.

```
Cliente            Router            Servicio                 intento_acceso (txn propia)      PostgreSQL
  │ POST /auth/login │                   │                              │                          │
  ├─────────────────►│ valida contrato   │                              │                          │
  │                  ├──────────────────►│ abre txn propia ────────────►│ count fallos 60s ───────►│
  │                  │                   │                              │                          │
  │                  │                   │  ── 5+ fallos ──► 429 + Retry-After (sin bcrypt) ──┐     │
  │                  │                   │                              │                   │     │
  │                  │                   │ busca usuario ─────────────────────────────────────────►│
  │                  │                   │ bcrypt en to_thread + semáforo (real o ficticio)      │
  │                  │                   ├─────────────────────────────►│ INSERT intento (commit) ►│
  │                  │                   │ fallo ──► 401 mismo cuerpo                            │
  │                  │                   │ ok ──► JWT(sub, iat, exp, roles) + cookie             │
  │◄─────────────────┴───────────────────┴───────────────────────────────────────────────────────┘
```

### Casos de error

| Caso | Manejo |
|---|---|
| Cuerpo inválido, email mal formado, password > 72 bytes | **422** (contrato) |
| 5 fallos previos en 60 s | **429** + `Retry-After`, **sin bcrypt** |
| Correo inexistente | **401** igual que contraseña mala (hash ficticio) |
| Contraseña mala | **401** |
| Usuario `activo = false` | **401** (no se revela que existe) |
| Falla el `INSERT` de `intento_acceso` | Se registra en el log; el login **no** se cae por eso (la transacción propia se confirma aparte) |

**Orden innegociable**: límite → hash ficticio/verificación en `to_thread` → token. Invertirlo rompe RN-08 (se gastaría bcrypt en un pedido que ya debía ser 429) y RN-09 (los tiempos se distinguirían).

---

## Flujo 2 — Auto-registro de cliente

**Disparador**: `POST /auth/registro`
**Actor**: cualquiera (ruta abierta)
**Reglas**: RN-01, RN-02
**Caso**: `C-02`

### Pasos

1. **Router**: valida `email`, `password` (8..72 **bytes**), `nombre`, `documento`, `telefono`. Cualquier campo extra (por ejemplo `rol`) → **422**.
2. **Servicio**: calcula el hash bcrypt **antes de abrir la transacción**, en `to_thread` bajo semáforo. Adentro de la transacción la conexión quedaría tomada ~300 ms sin usar la base.
3. Abre **un solo UoW** y escribe, en este orden:
   1. `usuario` (`activo = true`, `debe_cambiar_password = false`);
   2. `asignacion_rol` (`CLIENTE`, `desde = now()`, `revocada_en = NULL`);
   3. `cliente` (`usuario_id` = el id recién creado, `nombre`, `documento`, `telefono`);
   4. `evento_seguridad` (alta de usuario).
4. `flush()` para obtener el id del usuario; **ningún** `commit` intermedio.
5. Al salir del bloque: **commit**. Si cualquier escritura falló: **rollback** y **no queda ninguna de las tres filas**.
6. Responde **201** con los datos públicos (sin `password_hash`).

### Errores

| Caso | Manejo |
|---|---|
| `email` ya existe | `IntegrityError` de `usuario.email` → **rollback** → **409** con mensaje propio |
| `documento` ya es de un cliente del taller | `IntegrityError` de `cliente.documento` → **rollback** → **409** |
| Documento existente | **No se apropia de la ficha**: no se hace `UPDATE cliente SET usuario_id`, no se vincula, no se modifica. El registro se rechaza entero [RN-02] |
| Contraseña > 72 bytes | **422** (no 500) |
| Falla el rol CLIENTE | rollback de las tres |

**Cómo distinguir el campo sin violar la regla de unicidad**: se inspecciona el **nombre de la constraint** en el `IntegrityError`. Está prohibido hacer un `SELECT` previo para "ver si existe".

---

## Flujo 3 — Alta de orden de trabajo

**Disparador**: `POST /ordenes`
**Actor**: RECEPCION o ADMIN
**Reglas**: RN-10, RN-19
**Casos**: `C-10`, `C-17`

### Pasos

1. **Router**: valida `{vehiculo_id, falla, items[]}`. `items` con **al menos uno**, cada uno `{repuesto_id, cantidad > 0}`, **sin repuestos repetidos**. `precio`, `total`, `estado` y `creada_en` **no** se aceptan (`extra="forbid"`) → **422**.
2. **Servicio** abre el UoW:
   1. busca el vehículo **vigente** (sin `borrado_en`) → si no existe o está dado de baja, **409**;
   2. lee el estado `PENDIENTE` del **catálogo** con el repositorio de sólo lectura → si el catálogo está vacío, **409** [RN-19];
   3. por cada ítem, busca el repuesto **vigente** → si no existe o está dado de baja, **409** y **no se crea la orden**;
   4. **copia** `precio_unitario = repuesto.precio` y calcula `subtotal = cantidad × precio_unitario`;
   5. `total = Σ subtotales` (lo calcula el **servidor**, nunca el cliente);
   6. `INSERT orden_trabajo` (`estado = 'PENDIENTE'`, `mecanico_id = NULL`, `creada_en = now()`, `total`);
   7. `flush` para obtener el `id`;
   8. `INSERT item_orden` por cada ítem;
   9. `INSERT historial_estado_orden` (`desde_estado = NULL`, `hasta_estado = 'PENDIENTE'`, `usuario_id` = quien crea).
3. **Commit** al salir.
4. **201** con la forma del ejemplo de la consigna: `id`, `estado`, `patente`, `total`, `creada_en`, `mecanico_id: null`, `falla`, `cliente`, `items[]` (con `codigo`, `descripcion`, `cantidad`, `precio_unitario`, `subtotal`) e `historial[]`.

### Errores

| Caso | Manejo |
|---|---|
| Sin ítems, cantidad ≤ 0, repuesto repetido, campo extra | **422** |
| Vehículo inexistente o dado de baja | **409** (la ruta no tiene `{id}`, así que no aplica 404) |
| Repuesto inexistente o dado de baja | **409**, y **la orden no queda creada** |
| Catálogo de estados vacío | **409** con mensaje propio |
| `estado` enviado en el body | **422** |

**Por qué 409 y no 404**: el `404` de la tabla de endpoints aplica al **recurso de la ruta** (la orden). Un `vehiculo_id` del cuerpo que no existe es un **choque con lo guardado**, no una ruta inexistente.

---

## Flujo 4 — Iniciar una orden

**Disparador**: `POST /ordenes/{id}/iniciar`
**Actor**: MECANICO
**Reglas**: RN-11

1. `requiere_rol("MECANICO")` → sin rol, **403**; sin sesión, **401**.
2. Busca la orden → **404** si no existe.
3. Verifica `estado == 'PENDIENTE'` → si no, **409** (otro mecánico ya la tomó o ya está terminada).
4. Asigna `mecanico_id` = usuario actual (queda **asignado**).
5. `UPDATE estado = 'EN_REPARACION'` + **una** línea de historial (`PENDIENTE → EN_REPARACION`, `usuario_id` = el mecánico).
6. Commit → **200** con la orden actualizada.

**Error típico**: dos mecánicos inician a la vez. Sin locking (fuera de alcance) ambos pueden pasar la verificación; la segunda escritura pisa a la primera. Se acepta la actualización perdida — es el mismo trade-off que la consigna declara para el stock.

---

## Flujo 5 — Terminar una orden (el flujo crítico)

**Disparador**: `POST /ordenes/{id}/terminar`
**Actor**: el **mecánico asignado** o un ADMIN
**Reglas**: RN-11, RN-13, RN-14, RN-15
**Casos**: `C-11`, `C-12`, `C-15`

### Pasos

1. **Router**: construye el UoW (sin abrirlo) y llama al servicio.
2. **Servicio** abre el UoW:
   1. busca la orden con su vehículo, cliente, ítems e historial (precarga del repositorio) → **404** si no existe;
   2. **permiso**: `mecanico_id == usuario actual` **o** rol `ADMIN` → si no, **403** (otro mecánico no puede terminarla);
   3. **estado**: debe ser `EN_REPARACION` → si no, **409**;
   4. por **cada** ítem: ¿`repuesto.stock >= cantidad`? Si **alguno** no alcanza → **409** y **no se escribe nada** [RN-13];
   5. por cada ítem: descuenta `stock` por el **punto único de escritura de stock** [RN-14] y agrega **un `movimiento_stock`** con `orden_id`, `usuario_id`, `cantidad` y motivo de consumo;
   6. agrega **una** línea de historial (`EN_REPARACION → TERMINADA`);
   7. `UPDATE orden_trabajo SET estado = 'TERMINADA'`.
3. **Commit** al salir del bloque. Si algo falla → **rollback**: estado, stock, movimientos e historial quedan **exactamente como estaban**.
4. **Sólo si el commit salió bien**, el router agenda con `BackgroundTasks` el aviso al cliente: `await asyncio.sleep(0.5)` + mensaje en el log. Corre **después** de enviar la respuesta.
5. **200** con la orden terminada.

```
Router            Servicio                          UoW                          PostgreSQL
  │ construye UoW     │                               │                              │
  ├──────────────────►│ async with uow: ─────────────►│ BEGIN ──────────────────────►│
  │                   │  orden + precarga ────────────┼─────────────────────────────►│
  │                   │  403 si no es asignado/ADMIN  │                              │
  │                   │  409 si estado ≠ EN_REPARACION│                              │
  │                   │  ¿stock >= cantidad? (por ítem)                              │
  │                   │      no ──► 409 + ROLLBACK ───┼──── ROLLBACK ───────────────►│
  │                   │  stock−=, 1 movimiento/ítem,  │                              │
  │                   │  1 historial, estado=TERMINADA│                              │
  │                   │ ◄── salida normal ────────────┤ COMMIT ─────────────────────►│
  │◄──────────────────┤ 200                           │                              │
  │ BackgroundTasks.add_task(avisar) → corre DESPUÉS de la respuesta                │
```

### Errores

| Caso | Manejo |
|---|---|
| No existe la orden | **404** |
| Otro mecánico (no asignado) y no es ADMIN | **403** |
| Estado `PENDIENTE`, `TERMINADA` o `CANCELADA` | **409** |
| Un repuesto no alcanza (`C-11`: 4 bujías, stock 2) | **409**, sin ningún cambio |
| Falla el trigger de sólo agregado | rollback; no debería ocurrir desde la API |

**Detalle que se pierde fácil**: el aviso **no** se agenda antes del commit. Si se agendara antes y el commit fallara, el cliente recibiría un aviso de una orden que sigue en reparación.

**Detalle de `C-15`**: el detalle se resuelve con un **número fijo** de consultas que **no crece** con los ítems, porque la precarga está declarada en el repositorio (ítems, repuesto de cada ítem, vehículo, cliente, historial).

---

## Flujo 6 — Cancelar una orden

**Disparador**: `POST /ordenes/{id}/cancelar`
**Actor**: RECEPCION, ADMIN o **el dueño del vehículo**
**Reglas**: RN-12, RN-17
**Caso**: `C-13`

### Pasos

1. La ruta **no lleva `requiere_rol`**: el dueño no tiene rol de personal. Sí exige sesión (401 sin cookie).
2. Busca la orden con su vehículo → **404** si no existe.
3. **Permiso primero**: ¿es RECEPCION, ADMIN o el usuario dueño del vehículo? → si no, **403**.
4. **Estado después**: ¿está `PENDIENTE`? → si no, **409**.
5. `UPDATE estado = 'CANCELADA'` + **una** línea de historial (`PENDIENTE → CANCELADA`).
6. Commit → **200**.

### Errores

| Caso | Manejo |
|---|---|
| Orden ajena (ni personal ni dueño) | **403** |
| Orden terminada (`C-13`) | **409** |
| Orden en `EN_REPARACION` | **409** (no hay transición a CANCELADA) |
| Sin sesión | **401** |

**Por qué el orden importa**: si se evaluara el estado antes que el permiso, un cliente que intenta cancelar una orden **ajena y terminada** recibiría `409` — y ese `409` le confirmaría que la orden existe y está terminada. **403 antes que 409** evita filtrar información y es exactamente lo que pide RN-12.

**No toca el stock**: en `PENDIENTE` no se consumió nada, así que no hay movimiento que revertir.

---

## Flujo 7 — Cambio de contraseña (con `iat` sin truncar)

**Disparador**: `POST /auth/cambiar-password`
**Actor**: autenticado (ruta del grupo **abierto**, porque es la salida del bloqueo de RN-06)
**Reglas**: RN-06, RN-07
**Caso**: `C-09`

### Pasos

1. `get_usuario_actual` valida la cookie → **401** si falta, venció, el usuario está inactivo o el token es anterior al último cambio.
2. **Router**: valida `password_actual` y `password_nueva` (**máx. 72 bytes** cada una; la nueva, mín. 8) → **422** si no.
3. **Servicio**: verifica `password_actual` en `to_thread` bajo semáforo. Incorrecta → **401** (la tabla de la ruta sólo admite 200/401/422; no hay 403).
4. Calcula el hash de la nueva **antes de abrir la transacción**.
5. UoW:
   1. `UPDATE usuario SET password_hash = ..., password_cambiada_en = now(), debe_cambiar_password = false`;
   2. `evento_seguridad` (cambio de contraseña).
6. **Commit**.
7. **Después del commit**, emite el token nuevo con `iat = now()` — **estrictamente posterior** a `password_cambiada_en`, con fracciones de segundo.
8. **200** + `Set-Cookie` con el token nuevo.

### Por qué el `iat` no se trunca

`get_usuario_actual` rechaza con **401** todo token con `iat < password_cambiada_en`.

- Si `iat` se emitiera truncado a segundos, un token emitido en el **mismo segundo** pero **antes** del cambio tendría el mismo `iat` que `password_cambiada_en` y **seguiría valiendo**.
- Emitiendo con la hora completa y comparando sin truncar, el token viejo queda estrictamente antes y muere; el nuevo, estrictamente después, vive.
- **Orden crítico**: el token nuevo se emite **después** de escribir `password_cambiada_en`. Si se emitiera antes, el propio cambio se autoinvalidaría.

### Errores

| Caso | Manejo |
|---|---|
| Sin cookie / token vencido | **401** |
| `password_actual` incorrecta | **401** |
| Nueva > 72 bytes o < 8 caracteres | **422** |
| Token viejo usado después del cambio | **401** (sin esperar al `exp`) |

---

## Flujo 8 — Reposición de stock y cambio de precio

**Disparadores**: `POST /repuestos/{id}/reponer` y `PATCH /repuestos/{id}`
**Actor**: ADMIN
**Reglas**: RN-14, RN-20
**Caso**: `C-12` (reposición), `C-18` (precio)

### Reposición

1. `requiere_rol("ADMIN")` → **403** si no.
2. Busca el repuesto **vigente** → **404** si no existe.
3. Valida `cantidad > 0` → **422** si no.
4. En un UoW: **punto único de escritura de stock** (`stock += cantidad`) + `movimiento_stock` (`motivo = "Reposición"`, `orden_id = NULL`, `usuario_id` = admin).
5. Commit → **200** con el repuesto actualizado.

### Cambio de precio

1. `PATCH` con `extra="forbid"`: acepta **descripción** y **precio**. `stock` → **422** `[C-16]`.
2. `exclude_unset=True`: sólo se aplica lo enviado.
3. Si el precio **cambia**:
   - `UPDATE repuesto.precio`;
   - `INSERT historial_precio_repuesto` (`precio_anterior`, `precio_nuevo`, `usuario_id`), **en el mismo UoW** [RN-20].
4. Si el precio **no** cambia (mismo valor o sólo descripción): **no** deja línea `[C-18]`.
5. Commit → **200**.

**Restricción de la base**: `CHECK precio_nuevo > precio_anterior`. El historial sólo admite **aumentos**; un PATCH que baje el precio viola el `CHECK` y el servicio debe traducirlo (no 500). El código exacto para ese caso no está definido en la consigna → `10_preguntas_abiertas.md`.

---

## Flujo 9 — Baja lógica de un vehículo

**Disparador**: `DELETE /vehiculos/{id}`
**Actor**: RECEPCION o ADMIN
**Reglas**: RN-16
**Caso**: `C-19`

1. Busca el vehículo **vigente** → **404** si no existe o ya está dado de baja.
2. Cuenta/consulta sus órdenes abiertas: alguna con estado `es_final = false` → **409**.
3. Escribe `borrado_en = now()` (no borra la fila).
4. Commit → **204**.

Después, el mismo par `(cliente, patente)` se puede volver a registrar: el índice único parcial sólo mira las filas con `borrado_en IS NULL`. Una **segunda** patente vigente igual → **409** (el índice parcial la rechaza). Las órdenes viejas del vehículo dado de baja siguen existiendo y siguen siendo consultables.

---

## Flujo 10 — Revocación de un rol con la sesión abierta

**Disparador**: `DELETE /usuarios/{id}/roles/{rol}`
**Actor**: ADMIN
**Reglas**: RN-03, RN-04, RN-05
**Caso**: `C-07`

1. `requiere_rol("ADMIN")`.
2. **Autoprotección** [RN-05]: si `id` es el propio admin y `rol == 'ADMIN'` → **409** `[C-08]`. Si la revocación dejaría **cero** admins vigentes → **409**.
3. Busca la asignación **abierta** `(usuario_id, rol)` → **404** si no hay.
4. Escribe `revocada_en = now()`; **la fila queda**.
5. Commit → **200** (sin body definido).
6. La **cookie del usuario afectado sigue siendo válida como token**, pero la petición siguiente a una ruta con `requiere_rol` consulta la base, no encuentra el rol vigente y responde **403** [RN-04]. `/auth/yo` muestra el rol en "los del token" y ausente en "los vigentes".

---

## Flujo 11 — Arranque y salud

**Disparadores**: `GET /health/live`, `GET /health/ready`

1. `uvicorn` importa `main.py`; **no se construye ningún recurso** al importar.
2. **Lifespan (startup)**: lee `Settings` (si falta la clave de firma o la contraseña de la base → **no arranca**); crea el motor con el pool configurado y el `sessionmaker`; los guarda en `app.state`; calcula **una vez** el hash ficticio.
3. `GET /health/live` → **200** sin tocar la base.
4. `GET /health/ready` → `SELECT 1`; si la base no contesta → **503** (el proceso está vivo pero no listo; reiniciarlo no arregla una base caída).
5. **Lifespan (shutdown)**: `engine.dispose()`.
