# Expansion Backlog — AI Career OS (集大成路线)

> Living backlog of **new** epics beyond the current shipped/active line (Epics 0–74).  
> Purpose: make the system comprehensive, resilient, and production-grade across product,
> engineering, operations, and governance dimensions. Pick work in priority order when
> unblocked; each epic must ship with a gate, destructive proof, and real verification
> (no read-only “inspection” claims). Update this file only by adding measured outcomes.

## Status & rules
- This file is additive planning content; it does not override `docs/plans/plan_long_term.md`
  or `docs/ROADMAP.md`. When an epic starts, record its ID, owner/session notes, and
  measured verification in the relevant canonical docs.
- Verification rule: typecheck/tests/e2e where applicable; Docker-dependent `*IT`/Playwright
  require a real stack and must be recorded honestly if unavailable.
- Worktree/branch consolidation: committed history on detached worktrees audited as ancestors
  of `main` (2026-11-08) — no merge required; do not force-merge stale dirty worktrees over
  in-flight work.

## P0 — Reliability, safety, and operability (foundation for scale)

### Epic 75 — End-to-end observability contract
- **Goal**: Every critical user journey emits correlated traces/metrics/logs with stable IDs;
  SLOs defined for chat, ingest, match, export.
- **Deliverables**: trace propagation gate (frontend→backend→ai-service), structured log schema
  gate, runbook entries with measured alert thresholds, dashboard spec tied to real metrics.
- **Acceptance**: contract tests for correlation IDs; synthetic probe script (offline-safe where
  possible); RUNBOOK numbers from real measurements.

### Epic 76 — Backup, restore, and disaster recovery drills
- **Goal**: Prove data can be restored and the app recovers.
- **Deliverables**: scripted backup/restore for Postgres + object storage manifests; restore
  verification gate (schema + row counts + key invariants on a fixture dataset); DR runbook.
- **Acceptance**: drill executed and recorded (timestamped); RPO/RTO targets stated and measured
  where feasible.

### Epic 77 — Security hardening pass (continuous)
- **Goal**: Reduce authz/authn and supply-chain risk.
- **Deliverables**: periodic dependency audit in CI (pip-audit/npm audit as applicable),
  secret-scanning gate, authz matrix tests for every sensitive endpoint class, rate-limit
  coverage review, CSP/headers checklist for frontend.
- **Acceptance**: no known high/critical advisories untracked; gates fail on regression.

## P1 — Product completeness (user-facing depth)

### Epic 78 — Notification & reminder system v2
- **Goal**: Reliable, user-controlled reminders (interviews, follow-ups, stale applications)
  with delivery semantics and preferences.
- **Deliverables**: notification preferences model, delivery log, idempotent scheduler,
  in-app + (optional) email channels behind explicit config; gates for idempotency and
  preference enforcement.
- **Acceptance**: end-to-end reminder flow verified; no duplicate sends under retry.

### Epic 79 — Calendar & scheduling integration
- **Goal**: Connect interviews/applications to calendar workflows (ICS export first; OAuth
  integrations behind feature flags).
- **Deliverables**: ICS feed/export hardening, timezone correctness gates, provider adapters
  behind interfaces, privacy review for scopes.
- **Acceptance**: ICS validates; timezone round-trip tests green.

### Epic 80 — Accessibility (WCAG 2.2 AA target) and inclusive UX
- **Goal**: Core flows usable with keyboard/screen readers; contrast and focus visible.
- **Deliverables**: axe/pa11y-style checks in CI where feasible, keyboard E2E paths for
  top journeys, ARIA/landmark audit gates for key pages, reduced-motion support.
- **Acceptance**: no critical automated a11y violations on core routes; manual checklist recorded.

### Epic 81 — Internationalization completeness
- **Goal**: All user-visible strings localized; locale switching consistent (server/client),
  pluralization/formatting correct.
- **Deliverables**: i18n key coverage gate (no hardcoded UI strings in app routes/components
  beyond allowlist), date/number/currency formatting by locale, copy review workflow.
- **Acceptance**: coverage gate green; visual smoke in supported locales.

### Epic 82 — Data portability & compliance workflows
- **Goal**: User can export/delete data with verifiable scope; audit trail for sensitive actions.
- **Deliverables**: export manifest completeness gate, deletion/retention policy doc + tests,
  admin/support playbook (if applicable), legal-hold considerations documented.
- **Acceptance**: export/import round-trip tests; deletion verified on fixture data.

## P2 — Intelligence & quality (AI excellence)

### Epic 83 — Eval harness expansion & regression budgets
- **Goal**: RAG/agent/interview evals cover critical intents; regressions caught before merge.
- **Deliverables**: golden sets per intent, deterministic offline baselines, flaky-test quarantine
  policy, cost/latency budgets recorded.
- **Acceptance**: eval gates run in CI/nightly per policy; baseline numbers checked in.

### Epic 84 — Prompt/version governance
- **Goal**: Prompts and tool schemas versioned, diffable, and testable.
- **Deliverables**: prompt registry with IDs/versions, snapshot tests for schema stability,
  rollout/rollback notes.
- **Acceptance**: changing a prompt requires version bump + test update.

### Epic 85 — Cost, quota, and model routing controls
- **Goal**: Predictable spend; graceful degradation.
- **Deliverables**: per-user/per-feature budgets (configurable), model fallback policy,
  telemetry for token/cost, guardrails for expensive operations.
- **Acceptance**: budget enforcement tests; fallback behavior verified offline.

## P3 — Extensibility & ecosystem

### Epic 86 — Plugin/extension points for tools and importers
- **Goal**: Add new job sources, parsers, or agent tools without core rewrites.
- **Deliverables**: stable interfaces, capability registry, sandboxing/allowlist rules,
  example plugin + contract tests.
- **Acceptance**: third importer/tool added via interface only.

### Epic 87 — Public/internal API stability & changelog
- **Goal**: Consumers can rely on versioned contracts.
- **Deliverables**: API changelog, deprecation policy, contract tests tied to OpenAPI/DTOs,
  breaking-change checklist.
- **Acceptance**: CI gate for unversioned breaking changes on stable surfaces.

## P4 — Performance & scale

### Epic 88 — Performance budgets and load characterization
- **Goal**: Known latency/throughput under representative load.
- **Deliverables**: k6/Locust profiles (or equivalent), p95 budgets per endpoint class,
  caching/index review tied to measured slow queries.
- **Acceptance**: budget gate or recorded benchmark report; regressions flagged.

## Next concrete picks (when 74.x unblocks verification flow)
1. Keep shipping independent gates/hardening on `main` (no 74.1 conflicts).
2. After 74.1 lands: full verification → measured status update → 74.2 → then select Epic 75/77
   slices that can be delivered with real gates in the current environment.

## Measured progress (additive, verified)
> Recorded 2026-11-08 (this session chain, `origin/main` advancing). Each item shipped with
> a gate and destructive proof where applicable; 74.1 in-flight files were not touched.

- **OpenAPI/agent/internal contract gates** (ai-service, pytest): route inventory fully
  documented in OpenAPI; every OpenAPI operation has summary/description; route path hygiene;
  every `/internal/*` route requires `require_internal` (62 routes, floor 50) — security gate.
  AGENTS.md↔registry (26 tools, 8 subagents, bounds, memory 40, write set) and tool schema
  invariants (strict object, required refs, async handlers, unique names, handoff enum).
- **Doc↔reality/deploy gates**: `DEPLOYMENT.md` host ports vs dev/prod compose; `.env.prod.example`
  covers compose.prod required vars and uses placeholders for sensitive keys; `.env.example`
  covers dev compose vars; `SECURITY.md`/`RUNBOOK.md` required sections/anchors; expansion backlog
  structure gate.
- **Security/config hardening gates (Epic 77)**: frontend `next.config.ts` baseline security headers
  (XFO/XCTO/Referrer/Permissions/COOP/CORP/HSTS, all routes, `poweredByHeader:false`) regression
  gate; prod compose data services (postgres/redis/minio) must not publish host ports; dev compose
  data services must bind loopback; `.env.prod.example` sensitive values must be placeholders
  (no real/dev-default secrets). Backend source-level invariants: `SecurityConfig` keeps
  `/api/internal/**` permitted but `InternalApiFilter` enforces `X-Internal-Token` before JWT,
  key public routes preserved; actuator exposure exactly `health,prometheus` and redis health
  indicator disabled.
- **Schema/CI/ops hygiene**: Flyway migration naming/version monotonicity gate; CI/nightly
  referenced paths+ops modules exist and ops modules (`embed_jobs,seed_eval_corpus,check_export,
  nightly_report`) import cleanly; CI frontend adds non-blocking `npm audit --audit-level=high`
  visibility (blocking deferred until controlled remediation). Existing pip-audit gate remains.
- **Doc/service integrity**: `README.md`/`docs/DEPLOYMENT.md` relative markdown doc links resolve;
  `docs/architecture.md` key sections gate; every `ai-service/app/api` `APIRouter` declares `tags=`;
  ai-service `main.py` forbids mock LLM/voice in prod and has no CORS middleware (internal-only);
  ai-service `pytest.ini` + frontend `tsconfig strict` CI-critical settings.
- **Security fixes (Epic 77, verified)**: `ai-service` `require_internal` uses
  `secrets.compare_digest` for `X-Internal-Token` (timing-safe) + regression gate; backend
  BCrypt `$2B`/strength 12 gate; `.gitignore` protects `.env*`/build artifacts.
- **Worktree consolidation (2026-11-08, audited)**: committed detached worktree HEADs are
  ancestors of `main` (no merge required). Stale dirty `u256/wt` (372 behind, 667 files,
  large churn) not force-merged over 74.1 in-flight work.
