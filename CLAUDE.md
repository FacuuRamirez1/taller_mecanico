# Taller Mecánico — Instrucciones para Agentes

> Este archivo (y su copia `CLAUDE.md`) es lo PRIMERO que todo agente lee al entrar al repo.
> Generado a partir de `knowledge-base/` y `CHANGES.md`. No editar a mano sin re-sincronizar ambos archivos.

TP de **Programación III** (TUP): API REST asincrónica, backend-only, para órdenes de trabajo, stock y acceso de un taller mecánico. Objetivo declarado: **aprobar el TP** (plazo 4 días, 4 personas, PostgreSQL 16 local sin Docker).

---

## Stack Tecnológico

Versiones **mínimas** exigidas por la consigna. No hay frontend.

| Capa | Tecnología | Versión mínima |
|------|------------|----------------|
| Lenguaje | Python | 3.12 |
| Framework web | FastAPI (`async def` en todos los handlers) | 0.111 |
| Modelos | SQLModel | 0.0.24 |
| ORM base | SQLAlchemy asincrónico (`selectinload`, `postgresql_where`) | 2.0 |
| Driver | asyncpg (o psycopg 3 async) | 0.30 |
| Base de datos | PostgreSQL | 16 |
| Migraciones | Alembic, plantilla asincrónica | 1.13 |
| Configuración | pydantic-settings | 2.0 |
| Hash de contraseñas | bcrypt | 4.0 |
| Token | PyJWT | 2.8 |
| Servidor ASGI | uvicorn (el de `fastapi[standard]`) | — |
| Pruebas | REST Client (VS Code): `test/*.http` + `test/solo_agregado.sql` | — |

Arquitectura obligatoria: **Router → Service → UoW → Repository → Model**, por módulo funcional (health, usuarios, clientes, repuestos, ordenes).

Detalle completo: [knowledge-base/02_descripcion_general.md](knowledge-base/02_descripcion_general.md)

---

## Base de Conocimiento

La fuente de verdad del dominio vive en `knowledge-base/`. **Leé el archivo relevante ANTES de implementar.**

| Archivo | Cuándo leerlo |
|---------|---------------|
| [01_vision_y_objetivos.md](knowledge-base/01_vision_y_objetivos.md) | Propósito, alcance, pesos de la grilla |
| [03_actores_y_roles.md](knowledge-base/03_actores_y_roles.md) | Auth, RBAC, tabla de los 33 endpoints |
| [04_modelo_de_datos.md](knowledge-base/04_modelo_de_datos.md) | Las 13 tablas, índices parciales, migraciones, seed |
| [05_reglas_de_negocio.md](knowledge-base/05_reglas_de_negocio.md) | RN-01 a RN-20 |
| [06_funcionalidades.md](knowledge-base/06_funcionalidades.md) | Historias por ejercicio y casos C-01…C-19 |
| [07_flujos_principales.md](knowledge-base/07_flujos_principales.md) | Flujos E2E |
| [08_arquitectura_propuesta.md](knowledge-base/08_arquitectura_propuesta.md) | Capas, estructura, env vars, las 16 prohibiciones |
| [09_decisiones_y_supuestos.md](knowledge-base/09_decisiones_y_supuestos.md) | Decisiones tomadas y supuestos sin probar |
| [10_preguntas_abiertas.md](knowledge-base/10_preguntas_abiertas.md) | ⚠️ Inconsistencias y preguntas a resolver ANTES de codear |

> ⚠️ Antes de arrancar: resolver **Q-01** (nombre de la variable de la clave de firma; propuesto `JWT_SECRET_KEY`) y **Q-02** (datos de conexión locales a PostgreSQL), ambas P0 que bloquean `C-00`/`C-01`. Las P1 se deciden antes del `design.md` del change que las usa. Inconsistencias a tener presentes: IN-01 (son **13** tablas, no 12) e IN-05 (bajar el precio de un repuesto no puede terminar en 500).

---

## Skills Disponibles

Fuente de verdad: `.atl/skill-registry.md`. Instaladas en `.agents/skills/`.

| Agente | Rol | Skills que carga |
|--------|-----|------------------|
| **Backend Core** | FastAPI, repositorios, UoW, servicios, routers | `fastapi`, `async-python-patterns` |
| **Base de datos** | Modelos, migraciones Alembic, índices parciales, trigger de solo agregado | `sqlalchemy-alembic-expert-best-practices-code-review`, `postgresql-table-design` |
| **Seguridad** | Login, JWT en cookie, RBAC, límite de intentos, revisión pre-entrega | `auth-implementation-patterns`, `jwt-security-review` |
| **Orquestación** | SDD / OPSX, KB, roadmap, registry | `kb-creator`, `roadmap-generator`, `agent-instruction`, `skill-registry` (globales en `~/.claude/skills`) |

Cargá la skill correspondiente al contexto ANTES de escribir código. **La consigna manda sobre las skills**: `fastapi` empuja SQLModel síncrono/Asyncer y `sqlalchemy-alembic` sugiere índices `CONCURRENTLY`/`NOT VALID`; en este TP se usa SQLAlchemy async con `async_sessionmaker` en el lifespan y, en la migración inicial sobre base vacía, esas técnicas son opcionales.

> Los compact rules de cada skill los resuelve el orquestador desde `.atl/skill-registry.md` (generado por `skill-registry`; no versionado — no está en el repo). Esta tabla solo mapea skill→rol.

---

## Roadmap de Changes

El plan completo está en [CHANGES.md](CHANGES.md). Resumen:

- **Total**: 9 changes: `C-00` (setup del entorno) + `C-01`…`C-08` (Ej. 1 a Ej. 8 de la consigna, en ese orden exacto, sin reordenar por peso).
- **Camino crítico** (8): `C-00 → C-01 → C-02 → C-03 → C-04 → C-05 → C-06 → C-08` (≈75 h-persona).
- **Único con holgura**: `C-07` (integridad, 5 h), colchón del día 4.
- **Primer fork** en `C-03 ✓`: `C-04` y el núcleo de `C-06` corren en paralelo.
- **Puerta dura**: si `alembic upgrade head` sobre base vacía deja de funcionar, se congela todo hasta volver a verde (un proyecto que no levanta no se corrige).
- **Primer change**: `C-00` (`setup-entorno-local`).

**Antes de cualquier `/opsx:propose`**: leé [CHANGES.md](CHANGES.md), identificá las dependencias del change y sus punteros de "Leer antes".

---

## Reglas Duras (específicas del proyecto)

> Reglas globales ya definidas en `~/.claude/CLAUDE.md` (orquestador, governance, TDD, engram): el proyecto las hereda. Acá viven solo las reglas **específicas de este proyecto** + las universales que el global no cubra.

Son contrato; romperlas es un defecto. Formato `NUNCA X → hacer Y`.

### Arquitectura y base de datos
- NUNCA `create_all` → todo el esquema nace de Alembic (`alembic upgrade head` sobre base vacía).
- NUNCA carga perezosa → precarga (`selectinload`) declarada en el repositorio, no en el servicio.
- NUNCA `commit()` en repositorios → solo `flush`; confirma/revierte el UoW.
- NUNCA que un servicio construya su UoW → lo construye el router y el servicio lo abre.
- NUNCA verificar unicidad con una consulta previa → índice único (parcial donde aplique) y traducir el `IntegrityError` a 409.
- NUNCA SQL por concatenación → parámetros ligados.
- NUNCA devolver texto interno de la base en un error → mensajes propios; ninguna entrada inválida termina en 500.

### Seguridad y contratos
- NUNCA bcrypt en el bucle de eventos → `asyncio.to_thread` bajo semáforo, con el hash calculado antes de abrir la transacción.
- NUNCA token en el cuerpo ni en `Authorization` → cookie `HttpOnly` `SameSite=Lax`.
- NUNCA `password_hash` en una respuesta → schemas de salida separados de los modelos.
- NUNCA schema de entrada sin `extra='forbid'` → rechazar campos no declarados.
- NUNCA secretos con valor por defecto en el código ni subir `.env` → `env.example` sin valores reales.
- NUNCA editar el stock por `PATCH` ni el catálogo de estados por la API → el stock cambia solo por movimientos.
- NUNCA aceptar precio, total, estado ni fecha en el alta de una orden → los calcula/asigna el servidor.

### Estilo Python y asincronía
- `snake_case` y type hints en todo; todos los handlers `async def` sin llamadas bloqueantes.
- Schemas Pydantic separados de los modelos de tabla; `Annotated` + `Depends` con alias reutilizables (`SessionDep`); `prefix`/`tags`/`dependencies` declarados en el `APIRouter`.
- NUNCA dar un change por cerrado → sin sus casos `C-XX` en `test/*.http` (respuesta esperada comentada) y sin que `alembic upgrade head` + `python seed.py` corran sobre base vacía.

### Universales que el global no cubre
- NUNCA buildear ni commitear/pushear sin pedido explícito del usuario.
- Commits con conventional commits (`feat:`, `fix:`, `chore:`, …).

---

## Flujo de Trabajo

```
1. Leer la KB relevante (knowledge-base/)        → entender el dominio
2. Identificar el change en CHANGES.md           → respetar dependencias
3. /opsx:propose C-NN-nombre                     → proposal + design + specs + tasks
4. Implementar las tasks (cargando skills)       → respetando las reglas duras
5. /opsx:archive C-NN-nombre + marcar [x]        → cerrar el change
```

Aplicar TODAS las reglas duras en cada paso. Ante conflicto entre la KB y este archivo, las reglas duras prevalecen.
