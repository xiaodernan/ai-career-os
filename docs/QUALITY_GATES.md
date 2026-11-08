# Quality Gates — AI Career OS

> Factual index of automated gates that protect contracts, security boundaries, deploy/config
> reality, and engineering hygiene. Gates are enforced by tests/scripts in-repo and (where
> applicable) CI. This is an additive reference; canonical product/epic status lives in
> `docs/plans/plan_long_term.md` and `docs/ROADMAP.md`.

## How to run (local, typical)

- **ai-service (pytest, offline-capable for most contract gates)**
  - `cd ai-service && .venv\Scripts\python.exe -m pytest tests -q` (Windows) / `pytest -q`
  - Many gates are source/doc/contract checks (no DB/network). Full suite includes DB-dependent tests; see CI config.
- **frontend**
  - `cd frontend && npx vitest run` and `npx tsc --noEmit`
- **backend**
  - `cd backend && mvn -B "-Dtest=!*IT" test` (unit/contract tests; `*IT` requires Docker/stack)
- **CI**
  - `.github/workflows/ci.yml`: offline gates on PR/push (ai-service pytest + pip-audit, frontend vitest+tsc, backend unit tests); nightly Docker-backed *IT + eval + export checks.

## Gate categories (representative, measured additions recorded in backlog)

### API / agent / internal contracts (ai-service)
- OpenAPI route inventory fully documented; operations have summary/description; route path hygiene.
- Every `/internal/*` route requires `require_internal` (dependency-tree gate).
- `docs/AGENTS.md` ↔ live registry (tool count/names, 8 subagents and tool sets, bounds, memory limit, write set).
- Tool schemas strict objects with valid `required` refs; registry invariants (unique names, async handlers, handoff enum).

### Security (Epic 77, verified)
- Backend: `SecurityConfig` default-deny, documented public routes, `/api/internal/**` guarded by `InternalApiFilter` (constant-time token compare, blank-config rejection, 401) registered before JWT; actuator exposure only `health,prometheus`; BCrypt `$2B`/12; `ProductionGuard` exists and guards published defaults incl. `INTERNAL_API_TOKEN`.
- ai-service: `require_internal` constant-time token compare, rejects empty configured token and whitespace `X-User-Id`; lifespan forbids mock LLM/voice and published/empty internal token in prod; no CORS middleware (internal-only).
- Frontend: baseline security headers in `next.config.ts` (XFO, XCTO, Referrer-Policy, Permissions-Policy, COOP, CORP, HSTS) on all routes; `poweredByHeader: false`; `tsconfig` `strict: true`.
- Secrets/hygiene: `.env.prod.example` covers compose vars and uses placeholders for sensitive keys; `.gitignore` protects `.env*`/build artifacts.

### Deploy / config / runtime reality
- `docs/DEPLOYMENT.md` host ports ↔ dev/prod compose; prod data services not published; dev data services loopback-bound; prod/dev pulled images pinned (no `:latest`/untagged); prod services define `restart:`; Dockerfiles + prod build contexts exist.
- `.env.example` covers dev compose vars; backend `application.yml` safety invariants (`ddl-auto:none`, `open-in-view:false`, graceful shutdown, Flyway enabled, docs paths); backend/ai-service/frontend dependency/tooling contracts.

### CI / schema / ops / docs integrity
- Flyway migration naming/version monotonicity; CI/nightly referenced paths + ops modules exist/importable.
- `SECURITY.md`/`RUNBOOK.md`/`architecture.md` structure; README/DEPLOYMENT markdown links resolve; expansion backlog structure.
- Observability wiring (request-id/error handlers) and health endpoints present.

## Rules for adding gates
- Prove the gap with a failing case (destructive proof or mutation) when feasible; restore state.
- Use real verification (run the gate/tests); do not claim Docker-dependent `*IT`/Playwright green without a real stack.
- Stage only files created/modified for the batch; commit with `git commit -F <msgfile> -- <explicit paths>`; push `origin main`.

## Status note
- Measured progress is recorded additively in `docs/plans/expansion_backlog.md` (dated). 74.x roadmap execution and settled full-suite counts follow `docs/plans/plan_long_term.md` once in-flight work lands.