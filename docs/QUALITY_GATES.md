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
  - `.github/workflows/ci.yml`: offline gates on PR/push (ai-service pytest + pip-audit, frontend vitest+tsc, backend unit tests, Spring Cloud contract gates, bundle budget); nightly Docker-backed *IT + eval + export checks.

## Gate categories (representative, measured additions recorded in backlog)

### API / agent / internal contracts (ai-service)
- OpenAPI route inventory fully documented; operations have summary/description; route path hygiene.
- Every `/internal/*` route requires `require_internal` (dependency-tree gate).
- `docs/AGENTS.md` ↔ live registry (tool count/names, 8 subagents and tool sets, bounds, memory limit, write set).
- Tool schemas strict objects with valid `required` refs; registry invariants (unique names, async handlers, handoff enum).

### Frontend performance and product surface (Epics 122–130, measured 2026-11-11)
- `frontend/scripts/bundle-budget.mjs` recomputes each page route's gzipped first-load JS
  from `app-build-manifest.json` and fails the `budget` CI job at 340 kB; `npm run budget`
  runs the production build first. Heaviest route at adoption ~302 kB (/applications).
- `loading-skeletons.test.ts` pins the loading skeletons to their loaded shapes
  (LoadingCardSkeleton holds the StatCard anatomy; the metric grid's breakpoints match the
  dashboard's loaded strip; the route fallback imports only exported skeletons).
- `warm-prefetch.test.ts` pins the sidebar's route-warm wiring (hover and keyboard focus).
- `product-preview.test.tsx` pins the shared front-door illustration (role=img, one honest
  label; both anonymous surfaces render it).
- `test_the_performance_horizon_marks_done_honestly.py` and
  `test_the_prewarm_script_covers_the_composite_indexes.py` keep the performance horizon
  and the prewarm script honest; both run in `scripts/verify_gates.{sh,ps1}` (261/261).

### The caller's own deadline (Epic 128, verified offline)
- Gateway `DeadlineHeaderFilter` stamps every /api/** request with `X-Request-Deadline-Ms`
  (well-formed caller value kept if future, garbage or expired replaced; `GATEWAY_DEADLINE_MS`).
- Backend `DeadlineFilter` carries the budget on the request thread; `HttpAiServiceClient`
  refuses before dispatch when it already passed (`AI_SERVICE_UNAVAILABLE`); the ai-service
  carries it in a context variable with its own backstop at `/internal/rag/answer`
  (`SERVICE_DEADLINE_EXCEEDED`). Tests: `DeadlineFilterTest`, `GatewayDeadlineTest`,
  `test_the_deadline_carries_across_the_mesh.py`; documented in MICROSERVICES.md §6.

### Security (Epic 77, verified)
- Backend: `SecurityConfig` default-deny, documented public routes, `/api/internal/**` guarded by `InternalApiFilter` (constant-time token compare, blank-config rejection, 401) registered before JWT; actuator exposure only `health,prometheus`; BCrypt `$2B`/12; `ProductionGuard` exists and guards published defaults incl. `INTERNAL_API_TOKEN`.
- ai-service: `require_internal` constant-time token compare, rejects empty configured token and whitespace `X-User-Id`; lifespan forbids mock LLM/voice and published/empty internal token in prod; no CORS middleware (internal-only).
- Frontend: baseline security headers in `next.config.ts` (XFO, XCTO, Referrer-Policy, Permissions-Policy, COOP, CORP, HSTS) on all routes; `poweredByHeader: false`; `tsconfig` `strict: true`.
- Secrets/hygiene: `.env.prod.example` covers compose vars and uses placeholders for sensitive keys; `.gitignore` protects `.env*`/build artifacts.

### Deploy / config / runtime reality
- `docs/DEPLOYMENT.md` host ports ↔ dev/prod compose; prod data services not published; dev data services loopback-bound; prod/dev pulled images pinned (no `:latest`/untagged); prod services define `restart:`; Dockerfiles + prod build contexts exist; `test_the_compose_files_parse.py` holds the compose files YAML-parseable, scalar `build.args`, args backed by each Dockerfile's `ARG`, and the Epic 78 `APP_BUILD_SHA` bake to its declared services.
- `docs/DEPLOYMENT.md` §"Running the stack without Docker (host) — the escape hatch": the exact procedure used to verify `e2e/tests/timeline.spec.ts` on this machine, with the honesty limits stated.
- `.env.example` covers dev compose vars; backend `application.yml` safety invariants (`ddl-auto:none`, `open-in-view:false`, graceful shutdown, Flyway enabled, docs paths); backend/ai-service/frontend dependency/tooling contracts.

### CI / schema / ops / docs integrity
- Flyway migration naming/version monotonicity; CI/nightly referenced paths + ops modules exist/importable.
- `SECURITY.md`/`RUNBOOK.md`/`architecture.md` structure; README/DEPLOYMENT markdown links resolve; expansion backlog structure.
- Observability wiring (request-id/error handlers) and health endpoints present; ai-service JSON logs carry `request_id` (unit-tested).
- Spring Cloud surfaces: backend/gateway/discovery/config-server share actuator, build info, metrics/distribution and Prometheus contracts (cross-service gates); edge ops surface gated by `GATEWAY_ACTUATOR_TOKEN` (docs/EDGE_OPERATIONS_LOCKDOWN.md).
- `scripts/verify_gates.{ps1,sh}` run a representative offline gate set in one command.

## Rules for adding gates
- Prove the gap with a failing case (destructive proof or mutation) when feasible; restore state.
- Use real verification (run the gate/tests); do not claim Docker-dependent `*IT`/Playwright green without a real stack.
- Stage only files created/modified for the batch; commit with `git commit -F <msgfile> -- <explicit paths>`; push `origin main`.

## Status note
- Measured progress is recorded additively in `docs/plans/expansion_backlog.md` (dated). 74.x shipped; the operative forward plan beyond Epic 77 is `docs/ROADMAP.md` (Epics 78–130). Spring Cloud microservices gates live in `ai-service/tests/` and are wired into `scripts/verify_gates.{ps1,sh}` (measured 2026-11-11: 261/261).