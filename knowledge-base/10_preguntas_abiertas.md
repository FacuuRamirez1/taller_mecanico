# Preguntas Abiertas

Prioridades:

- **P0** — bloquea **arrancar** (sin resolverlo no se puede levantar el proyecto o escribir la primera línea).
- **P1** — bloquea **un change puntual** (hay que decidirlo antes del `design.md` de ese ejercicio).
- **P2** — cosmético o de bajo impacto (se puede avanzar y ajustar después).

## Inconsistencias detectadas

### IN-01 — "12 tablas" vs. las 13 del modelo
**El pedido de esta fase y el Discovery dicen**: "12 tablas".
**La consigna define**: **13** — `usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad`, `cliente`, `vehiculo`, `repuesto`, `estado_orden`, `orden_trabajo`, `item_orden`, `historial_estado_orden`, `movimiento_stock`, `historial_precio_repuesto`.
**Impacto**: si alguien implementa "12", se pierde una tabla (probablemente `evento_seguridad`, que no se relaciona con nada) y con ella el Ej. 5 (historial de seguridad) y la evidencia del actor `SISTEMA`.
**Resolución propuesta**: implementar las **13**; la diferencia es de conteo, no de alcance. Documentado así en `04_modelo_de_datos.md`.

### IN-02 — "14 prohibiciones" vs. las 16 enumeradas
**El pedido de esta fase dice**: "las 14 prohibiciones".
**El Discovery enumera**: 16 ítems si se desdoblan "secretos con valor por defecto en código" / "subir `.env`" y se cuentan por separado los cuatro campos vetados en el alta de orden.
**Impacto**: nulo en el código; sólo afecta cómo se enumera en la documentación y en el `design.md`.
**Resolución propuesta**: listar las **16** en `08_arquitectura_propuesta.md` (numeradas) y usar esa lista como checklist. No se omite ninguna por ajustar el número.

### IN-03 — `needs_infra` en el contrato de la KB
**El contrato de estado** marca `needs_infra = true` cuando los documentos mencionan base de datos, colas o despliegue.
**La consigna y el Discovery** dicen: PostgreSQL 16 **local**, sin Docker, sin deploy, sin colas.
**Impacto**: sólo afecta el metadato; no cambia ninguna decisión técnica.
**Resolución propuesta**: `false`, con la justificación de `SU-08` (hay base, pero no se aprovisiona infraestructura). Si en algún momento se agrega Docker o un entorno compartido, se revisa.

### IN-04 — El ejemplo de `POST /ordenes` no coincide con el seed
**El ejemplo** usa `"vehiculo_id": 2` y devuelve `"cliente": "Laura Cliente"`, `"patente": "AC456EF"`, `"id": 3`.
**El seed** asigna el **primer** vehículo de Laura a la orden 1 y el vehículo de **Jorge** a la orden 2. Con ese orden de carga, el vehículo 2 sería el segundo de Laura (si se cargan primero los dos de Laura) o el de Jorge (si se intercalan).
**Impacto**: si un `.http` copia el ejemplo tal cual, puede apuntar a un vehículo distinto del que espera.
**Resolución propuesta**: tratar el ejemplo como **ilustrativo**; en los `.http` referenciar ids reales del seed y no copiar `vehiculo_id: 2` a ciegas. Fijar el orden de carga en `seed.py` y documentarlo.

### IN-05 — `PATCH /repuestos` no declara 409, pero el `CHECK` puede producir un choque
**La tabla de endpoints** admite `200, 404, 422` para `PATCH /repuestos/{id}`.
**El modelo** tiene `CHECK precio_nuevo > precio_anterior`: bajar el precio viola la base.
**Impacto**: si el servicio no lo traduce, la violación del `CHECK` termina en **500** — lo que RN-18 prohíbe explícitamente.
**Resolución propuesta**: validar en el servicio y responder **422** (coherente con la tabla) o **409** (coherente con "choque con lo guardado"). Hay que elegir uno antes del Ej. 6. Ver `Q-10`.

## Preguntas abiertas priorizadas

| ID | Prioridad | Pregunta | Bloquea | Decisor |
|---|---|---|---|---|
| **Q-01** | **P0** | ¿Cómo se llama la variable de entorno de la clave de firma? La consigna exige que exista y que **no** tenga default, pero no fija el nombre (`JWT_SECRET_KEY`, `SECRET_KEY`, `CLAVE_FIRMA`…). Hay que fijarlo porque `Settings`, `env.example`, el `README` y `alembic` lo comparten. | **Ej. 1** (sin la variable la app no arranca) | Equipo técnico |
| **Q-02** | **P0** | ¿Cada integrante usa su propia base local con qué usuario, nombre y puerto? `POSTGRES_*` no tiene valores por defecto, así que sin estos datos nadie levanta el proyecto el día 1. | **Ej. 1** (operativo) | Equipo |
| **Q-03** | P1 | **Contrato exacto de los endpoints que la consigna no ejemplifica**: `POST /usuarios`, `GET /usuarios/{id}/roles`, `DELETE /usuarios/{id}/roles/{rol}` (200 sin body definido), `GET /eventos`, `GET /mis-vehiculos`, `GET /mis-ordenes`, `GET /estados-orden`, `GET /repuestos/{id}/movimientos`, `GET /repuestos/{id}/precios`, `DELETE /vehiculos/{id}`. ¿Qué campos viajan y qué devuelve cada uno? | Ej. 3 y 5 (`design.md`) | Cátedra / equipo |
| **Q-04** | P1 | `GET /ordenes/{id}`: ¿qué roles cuentan exactamente como **"el personal"**? (`Suposición` actual: ADMIN + RECEPCION + MECANICO). | Ej. 5 / 6 | Cátedra |
| **Q-05** | P1 | RN-05: "el sistema nunca queda sin administradores vigentes", ¿se controla **sólo** al revocar un rol o **también** al desactivar un usuario (`activo = false`)? | Ej. 5 | Cátedra |
| **Q-06** | P1 | RN-08: la ventana de **60 s**, ¿es **deslizante** o **fija**? `C-05` exige que el **sexto** intento reciba 429. (`Suposición` actual: deslizante). | Ej. 4 | Cátedra |
| **Q-07** | P1 | **Datos de seed incompletos**: patentes, marcas, modelos, años, documentos, teléfonos, códigos y precios de los 4 repuestos. ¿La cátedra exige algunos valores concretos o alcanza con ficticios consistentes? | Seed / Ej. 2 | Cátedra |
| **Q-08** | P1 | Descripciones exactas de los 4 estados del catálogo. La consigna dice "cada uno con su descripción" sin darlas. | Seed | Cátedra |
| **Q-09** | P1 | Repositorio de sólo lectura del catálogo (`EstadoOrden`): ¿qué métodos expone, dado que **no** hereda de `BaseRepository`? (`listar_por_posicion`, `get_by_codigo` es lo mínimo). | Ej. 6 | Equipo |
| **Q-10** | P1 | `PATCH /repuestos/{id}` con un precio **menor**: ¿**422** (respeta la tabla de códigos) o **409** (respeta la semántica de "choque con lo guardado")? El `CHECK` de la base lo rechaza igual. | Ej. 6 (`IN-05`) | Equipo |
| **Q-11** | P1 | `POST /clientes`: ¿el body puede traer `usuario_id`, o el cliente **siempre** se crea sin usuario y sólo el auto-registro lo vincula? | Ej. 3 | Equipo |
| **Q-12** | P1 | `GET /mis-ordenes` / `/mis-vehiculos`: un usuario autenticado **sin ficha de cliente** (ej. un admin), ¿recibe **lista vacía** o **error**? | Ej. 5 | Equipo |
| **Q-13** | P1 | `POST /usuarios` con "contraseña provisoria": ¿debe crear al usuario con `debe_cambiar_password = true`? (Es lo que sugiere el nombre). | Ej. 5 | Equipo |
| **Q-14** | P1 | `POST /auth/cambiar-password`: la consigna no fija el nombre de los campos (`password_actual` / `password_nueva` vs `actual` / `nueva`). Hay que fijarlo para los `.http`. | Ej. 4 | Equipo |
| **Q-15** | P1 | Un intento que recibe **429**: ¿se registra también en `intento_acceso`? `C-05` sólo exige que estén los **cinco** fallos. | Ej. 7 (`C-05`) | Equipo |
| **Q-16** | P1 | RN-16: usar un repuesto o vehículo **dado de baja** en una orden nueva, ¿**409** o **404**? La consigna dice que "no se puede usar" pero no fija el código (la tabla de `POST /ordenes` sólo admite 409/422). | Ej. 6 | Equipo |
| **Q-17** | P2 | **Orden por defecto** de los listados (`/ordenes`, `/eventos`, `/mis-ordenes`, `/repuestos`). `Suposición`: `id` descendente; el catálogo, por `posicion`. | Ej. 3 | Equipo |
| **Q-18** | P2 | **Texto exacto de los mensajes de error**: se piden "mensajes propios" sin vocabulario fijado, salvo el ejemplo de paginación ("La página 3 no existe: hay 2"). | Ej. 3 | Equipo |
| **Q-19** | P2 | **Generación de la clave de firma**: el `README` debe explicar cómo, pero la consigna no fija el método. Propuesta: `python -c "import secrets; print(secrets.token_urlsafe(64))"`. | Entrega | Equipo |
| **Q-20** | P2 | Paginación **sin resultados**: ¿`pages = 0` o `pages = 1` con `items` vacío? La consigna dice "con cero resultados hay una página, vacía" y `total 0`. | Ej. 3 | Equipo |
| **Q-21** | P2 | `GET /clientes/{id}` "con sus vehículos": ¿incluye los **dados de baja** o sólo los vigentes? | Ej. 3 | Equipo |
| **Q-22** | P2 | `evento_seguridad.actor`: ¿se guarda el **email**, el **id** o un texto libre? La columna es texto y admite `SISTEMA`. | Ej. 5 | Equipo |
| **Q-23** | P2 | `POST /repuestos` con `stock_inicial = 0`: ¿se permite y deja un movimiento en 0? El `CHECK stock >= 0` lo permite, pero `movimiento_stock.cantidad > 0` lo impediría como movimiento. | Ej. 3 | Equipo |

### Las 11 preguntas del `state` y dónde quedaron

| # (state) | Pregunta | Acá |
|---|---|---|
| 1 | Contrato exacto de los endpoints no ejemplificados | **Q-03** (P1) |
| 2 | `GET /ordenes/{id}`: qué roles son "el personal" | **Q-04** (P1) + `SU-03` |
| 3 | RN-05: alcance de "nunca sin administradores" | **Q-05** (P1) |
| 4 | RN-08: ventana deslizante o fija | **Q-06** (P1) + `SU-07` |
| 5 | Datos de seed incompletos | **Q-07** (P1) + `SU-01` |
| 6 | Métodos del repositorio de sólo lectura del catálogo | **Q-09** (P1) |
| 7 | `POST /clientes`: ¿acepta `usuario_id`? | **Q-11** (P1) |
| 8 | `GET /mis-ordenes` sin ficha de cliente | **Q-12** (P1) |
| 9 | Orden por defecto de los listados | **Q-17** (P2) + `SU-10` |
| 10 | Generación de la clave de firma | **Q-19** (P2) |
| 11 | Texto exacto de los mensajes de error | **Q-18** (P2) |

## Riesgos del `state` (10)

| # | Riesgo | Severidad | Mitigación (detalle en `09`) |
|---|---|---|---|
| R-01 | Que el proyecto **no levante o no se corrija**; la condición de no corrección no distingue alcance incompleto de proyecto roto | 🔴 | El proyecto **siempre** corre y migra; humo test al cerrar cada change |
| R-02 | **Repositorios + UoW (20 %)**: quién construye, abre, confirma y cierra | 🔴 | Tabla de responsabilidades de `08`; revisión cruzada |
| R-03 | **Autenticación (16 %)**: orden del login, hash ficticio, `iat` sin truncar | 🟠 | Checklist de `07` flujos 1 y 7 |
| R-04 | **Migraciones (14 %)**: 3 índices parciales y la 2.ª migración a mano con el trigger | 🟠 | Escribir la migración con `C-14` al lado |
| R-05 | **Autorización (14 %)**: roles vigentes por petición, 401 vs 403, 403 antes que 409 | 🟠 | `C-06`, `C-07`, `C-13` |
| R-06 | **Lecturas sin N+1 (8 %)**: consultas fijas con precarga en el repositorio | 🟡 | `C-15` con `SQL_ECHO` desde el día 1 |
| R-07 | **`Suposición`**: 4 personas en 4 días sobre un repo no se pisan en los archivos core | 🔴 | Propiedad por módulo; `app/core/` congelado tras el Ej. 1 |
| R-08 | **`Suposición`**: los `.http` alcanzan sin pytest ni CI; dependen de `seed.py` | 🟠 | Corrida completa desde cero antes de entregar |
| R-09 | **`Suposición`**: el paralelismo convive con la cadena Ej. 1 → 2 → 3 | 🟠 | Empezar 4 y 5 apenas se congela el esquema |
| R-10 | **Plazo**: 4 días para 8 ejercicios + 19 casos + 2 evidencias (~1,6 h por ejercicio) | 🔴 | Priorizar por peso: arranque → 6 → 4 → 2/5 |

## Lo que la consigna no permitió resolver

Resumen de los huecos que **no** se pueden cerrar leyendo el PDF, para que no se confundan con omisiones de la KB:

1. **Ningún valor concreto de los datos de seed** salvo los emails, los stocks (10/4/2/20), los estados y el historial 8000 → 8500 (`Q-07`, `SU-01`).
2. **Los contratos de respuesta** de 10 endpoints que la consigna sólo nombra (`Q-03`).
3. **Los textos** de las descripciones de estado y de los mensajes de error (`Q-08`, `Q-18`).
4. **El nombre** de la variable de la clave de firma, de los campos de cambio de contraseña y de las clases de UoW (`Q-01`, `Q-14`).
5. **El código exacto** para bajar el precio de un repuesto, usar un recurso dado de baja en una orden nueva, o el 429 en `intento_acceso` (`Q-10`, `Q-16`, `Q-15`).
6. **La inclusión de las 13 tablas frente a las "12"** del pedido interno (`IN-01`): se resolvió documentando las 13, pero la discrepancia queda registrada.
