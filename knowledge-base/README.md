# Taller Mecánico — Base de Conocimiento

Base de conocimiento del TP de **Programación III** (TUP): una API REST asincrónica, backend-only, para órdenes de trabajo, stock y acceso de un taller mecánico, con FastAPI y PostgreSQL 16.

Generada en **Mode A (ingest)** a partir de la consigna (`docs/TP_Cap1a6_Consigna.pdf`, extraída a `docs/consigna.md`), del Discovery aprobado (`discovery/discovery.md`) y del estado del orquestador (`.active-orchestrator-state.json`).

## Índice de archivos

| Archivo | Contenido |
|---|---|
| [01_vision_y_objetivos.md](01_vision_y_objetivos.md) | Propósito, objetivos por actor, alcance y fuera de alcance, métricas de éxito (pesos de la grilla), restricciones de contexto (4 días, 4 personas) |
| [02_descripcion_general.md](02_descripcion_general.md) | Stack con versiones mínimas, arquitectura en capas, módulos, integraciones (ninguna), resumen de la API y convenciones transversales |
| [03_actores_y_roles.md](03_actores_y_roles.md) | Actores, `SISTEMA` como texto, matriz RBAC, **tabla literal de los 33 endpoints**, rutas abiertas, `401` vs `403` |
| [04_modelo_de_datos.md](04_modelo_de_datos.md) | Las 13 tablas con columnas, `CHECK`, `UNIQUE`, índices únicos parciales y FKs; ERD Mermaid; **seed data completo** |
| [05_reglas_de_negocio.md](05_reglas_de_negocio.md) | **RN-01 a RN-20** literales, con garante esperado, código HTTP, detalle por dominio y mapa de trazabilidad |
| [06_funcionalidades.md](06_funcionalidades.md) | 39 historias por épica (= ejercicio) con peso, criterios de aceptación y los **19 casos C-01…C-19** |
| [07_flujos_principales.md](07_flujos_principales.md) | 11 flujos extremo a extremo: login, registro, alta/inicio/término/cancelación de orden, cambio de contraseña, stock y precio, bajas, salud |
| [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md) | Patrones, **estructura de directorios obligatoria**, reparto de responsabilidades, seguridad, variables de entorno, migraciones, 16 prohibiciones |
| [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md) | 14 decisiones cerradas con justificación, defaults aceptados y 10 supuestos marcados como **`Suposición:`** |
| [10_preguntas_abiertas.md](10_preguntas_abiertas.md) | 5 inconsistencias, 23 preguntas priorizadas P0/P1/P2 y los 10 riesgos del proyecto |

## Quick start para desarrolladores

1. **Entender el dominio** → [01](01_vision_y_objetivos.md), [03](03_actores_y_roles.md).
2. **Entender los datos** → [04](04_modelo_de_datos.md) (nombres de tablas y columnas **obligatorios**; el seed es parte de la puesta en marcha).
3. **Entender las reglas** → [05](05_reglas_de_negocio.md) (RN-01…RN-20; las que más pesan: RN-02, RN-04, RN-07, RN-13, RN-15).
4. **Entender la arquitectura** → [02](02_descripcion_general.md), [08](08_arquitectura_propuesta.md) (quién crea, abre, confirma y cierra).
5. **Implementar** → [07](07_flujos_principales.md) para el orden de los pasos, [06](06_funcionalidades.md) para el alcance y los criterios de aceptación.
6. **Antes de codificar** → [10](10_preguntas_abiertas.md): hay **2 preguntas P0** que bloquean el arranque.

## Orden de lectura para el equipo (4 personas, 4 días)

| Momento | Leer | Objetivo |
|---|---|---|
| Día 1, mañana | 01, 02, 04, 08 | Acordar estructura, nombres y esquema. **Nadie escribe código antes de cerrar `04`.** |
| Día 1, tarde | 05, 07 (flujos 1-3) | Reglas y flujos base |
| Día 2 | 03, 06 (épicas 2-4), 07 (flujos 4-7) | CRUD, auth, autorización |
| Día 3 | 06 (épica 5), 07 (flujos 5, 8, 9), 08 | UoW, stock, integridad |
| Día 4 | 06 (épica 7-8), 10 | N+1, casos, evidencias, huecos |

## Resumen ejecutivo

Una API asincrónica en capas `Router → Service → UoW → Repository → Model` que digitaliza el taller: recepción abre clientes, vehículos y órdenes; el mecánico las inicia y al terminarlas descuenta stock con movimientos e historial; el admin administra catálogo, stock, personal y roles; el cliente se auto-registra y ve sólo lo suyo. **13 tablas**, **3 índices únicos parciales**, **1 catálogo con FK**, **3 tablas de sólo agregado** protegidas por trigger y **19 casos de prueba** manuales. El riesgo dominante no es funcional sino de calendario y de arranque: si el proyecto no levanta y no migra sobre base vacía, no se corrige.
