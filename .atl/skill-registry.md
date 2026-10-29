# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

See `_shared/skill-resolver.md` for the full resolution protocol.

## User Skills

Project-level skills (`.agents/skills/`, deduplicated against identical copies in `.claude/skills/`). Foundation/workflow skills in `~/.claude/skills` (active-orchestrator, kb-creator, roadmap-generator, find-skill, agent-instruction, discovery-research, web-scraper, skill-creator) are intentionally excluded.

| Trigger | Skill | Path |
|---------|-------|------|
| FastAPI APIs, Pydantic models, dependencies, routers, streaming | fastapi | .agents/skills/fastapi/SKILL.md |
| SQLAlchemy models, Alembic migrations, schema changes, query optimization | sqlalchemy-alembic-expert-best-practices-code-review | .agents/skills/sqlalchemy-alembic-expert-best-practices-code-review/SKILL.md |
| Implementing auth, JWT, sessions, RBAC, securing APIs | auth-implementation-patterns | .agents/skills/auth-implementation-patterns/SKILL.md |
| Async APIs, concurrent I/O, asyncio, non-blocking operations | async-python-patterns | .agents/skills/async-python-patterns/SKILL.md |
| Designing/reviewing PostgreSQL schemas, types, constraints, indexes | postgresql-table-design | .agents/skills/postgresql-table-design/SKILL.md |
| Auditing JWT implementations (alg confusion, secrets, claims, lifecycle) | jwt-security-review | .agents/skills/jwt-security-review/SKILL.md |

## Compact Rules

Pre-digested rules per skill. Delegators copy matching blocks into sub-agent prompts as `## Project Standards (auto-resolved)`.

### fastapi
- Use `Annotated[..., Depends()/Query()/Path()]`; create reusable aliases (e.g. `SessionDep = Annotated[AsyncSession, Depends(get_session)]`).
- Never use `...` (Ellipsis) as default for required params/fields; do not use `RootModel`.
- Declare return types or `response_model` so output is validated/filtered (prevents leaking e.g. `password_hash`).
- Do not use `ORJSONResponse`/`UJSONResponse` (deprecated).
- Declare `prefix`, `tags`, shared `dependencies` on the `APIRouter`, not per route.
- One HTTP operation per function; use `async def` handlers only with non-blocking calls.
- Run with `fastapi dev` / `fastapi run`; entrypoint in `[tool.fastapi]` of pyproject.
- CAVEAT: skill prefers SQLModel/Asyncer; the TP consigna (async SQLAlchemy + async_sessionmaker in lifespan, to_thread for bcrypt) takes precedence.

### sqlalchemy-alembic-expert-best-practices-code-review
- Indexes in migrations: `postgresql_concurrently=True` inside `op.get_context().autocommit_block()` (on non-empty tables).
- Unique constraints: create unique index concurrently, then attach constraint using it.
- Foreign keys and CHECK constraints: add `NOT VALID` first, then `VALIDATE CONSTRAINT` separately.
- Column type changes: multi-step (add new, backfill, swap) to avoid table locks.
- Every query pattern (filters, joins, FK columns) should have a supporting index; avoid redundant indexes covered by a composite; max 3 columns for non-unique indexes.
- Note: for the initial empty-database migration in this TP, concurrent/NOT VALID splitting is optional; partial unique indexes use `postgresql_where`.

### auth-implementation-patterns
- Never store plain passwords; hash with bcrypt/argon2.
- Access tokens short-lived (15-30 min); store in httpOnly + SameSite (+ Secure on HTTPS) cookies, never localStorage.
- Always enforce authorization server-side; validate resource ownership for "own" resources.
- Rate-limit auth endpoints (brute force); log security events (login attempts, failed auth).
- Validate all input (email format, password strength); do not trust client data.
- Tokens must expire; rotate secrets; use RBAC with roles checked per request.

### async-python-patterns
- Never block the event loop: run blocking/CPU work (e.g. bcrypt) via `asyncio.to_thread` / `run_in_executor`.
- Always `await` coroutines (a bare call returns an unexecuted coroutine).
- Bound concurrency with `asyncio.Semaphore`; use `asyncio.gather` for independent concurrent I/O, with `return_exceptions` when appropriate.
- Use `asyncio.timeout`/`wait_for` for timeouts; always handle `CancelledError` (cleanup, re-raise).
- Use `async with` for resources (sessions, UoW) and `async for` for async iterators.
- Do not call async code from sync code directly; don't mix sync and async without `to_thread`/`asyncio.run`.

### postgresql-table-design
- PK: `BIGINT GENERATED ALWAYS AS IDENTITY` (UUID only if global/opaque IDs needed); normalize to 3NF.
- Types: `TIMESTAMPTZ` for time, `NUMERIC(p,s)` for money, `TEXT` for strings (+ CHECK for length), `BOOLEAN NOT NULL`.
- `NOT NULL` wherever semantically required; combine CHECK with NOT NULL (CHECK passes on NULL).
- PostgreSQL does NOT auto-index FK columns: add indexes manually; specify `ON DELETE/UPDATE` explicitly.
- UNIQUE allows multiple NULLs (use `NULLS NOT DISTINCT` on PG15+ if needed); partial indexes (`WHERE ...`) for hot/conditional-unique subsets.
- Evolving business values: lookup table or TEXT + CHECK instead of ENUM types.
- `snake_case` identifiers; sequences have gaps (normal).

### jwt-security-review
- Always pin `algorithms=[...]` on decode (never `jwt.decode` without verification, never allow `none`/`*`).
- HS256 secret >= 32 bytes of entropy, from config/env, never hardcoded.
- Enforce `exp` (and `iat`/`nbf`); require expected claims; reject unexpected privileged claims.
- Don't trust role/uid claims from the token when a server-side lookup exists (authorize from DB).
- `sub` must be a stable ID (user id, not email); revocation path for logout/password change.
- Access tokens short-lived; prefer httpOnly cookies over localStorage.

## Project Conventions

No project-level `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `GEMINI.md` or `copilot-instructions.md` found yet. Related project documents:

| File | Path | Notes |
|------|------|-------|
| Roadmap / change index | CHANGES.md | Operational index of OpenSpec changes |
| Knowledge base | knowledge-base/ | 10 canonical files (README.md + 01..10) |
| Discovery | discovery/discovery.md | Full discovery document |
| Skills lock | skills-lock.json | Installed skills manifest |

Read the convention files listed above for project-specific patterns and rules. All referenced paths have been extracted — no need to read index files to discover more.
