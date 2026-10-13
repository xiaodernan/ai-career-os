# ROADMAP — AI Career OS (长期演进计划)

This file is the standing backlog toward the **final goal**: a complete,
production-grade *personal job-search operating system* — evidence-bound AI over
the full career loop, plus growth, outreach, and offer intelligence, with data
portability, analytics, and hardened delivery. It is the single source of truth
for "what to build next" across sessions; pick the top un-done task and execute.

> The loop the product runs today (Epic 0–9, shipped): resume → knowledge base →
> job discovery → JD intelligence → evidence-matched scoring → tailored materials →
> adaptive mock interviews → application tracking → observability. Every AI claim is
> traced to the user's own material. The forward epics extend *that* loop.

## Status
- **Epic 0–9: DONE.** Foundation, auth, resume intelligence, RAG, job discovery,
  materials, interview coach, copilot/agents, tracker/dashboard, quality & delivery.
  Verified end-to-end: 24/24 Playwright golden journey, both eval harnesses, RAG
  eval 15/15 on the seeded corpus.
- **Epics 10/11/12 (ai-service halves): DONE (2026-10-11 → 13).** Twelve internal,
  evidence-bound engines shipped in ai-service, all unit-tested offline:
  gap analysis (10.1), target-role readiness (10.7), learning plan (10.5),
  skill-progress tracking (10.6), market skill demand (10.9), STAR story bank (6.5),
  outreach drafting (11.2), salary benchmark (12.1), negotiation coach (12.2),
  offer comparison (12.3), counter-offer drafting (12.4), equity annualization (12.5)
  — plus an aggregate
  `POST /internal/features/growth-report` (10.8) that composes the growth page in one
  call, the **progression planner** (10.11, stepping-stone roles toward a dream
  role), the **learning-priority** ranker (10.12, learn the most-demanded gap
  first), and the **interview-prep** checklist (10.13, study the gaps, rehearse the
  strength stories). Seventeen internal engines now, all unit-tested offline, all
  pinned by `tests/test_forward_features_contract.py`.
  **None are wired to the backend yet** (10.2/10.3 and the 12.x bridges are pending).
- **The backend bridge is the next real step** and is blocked only on files another
  session has in flight (`HttpAiServiceClient.java`, `docs/API.md`,
  `frontend/src/lib/api/endpoints.ts`). Do it when they are clean.

## Epic 10 — Growth Intelligence
- [x] **10.1** Gap & growth analysis engine (evidence-bound coverage verdict).
- [ ] **10.2** Backend bridge: `HttpAiServiceClient` method + controller endpoint
  (`/api/v1/growth-report` first; granular endpoints after). Extend `docs/API.md` + gate.
- [ ] **10.3** Frontend page/panel: target-role input, readiness verdict, coverage
  bars (covered / partial / gap), learning plan, salary band, progress delta.
- [ ] **10.4** Persist a `growth_plan` per (user, target_role) so repeat runs diff
  (needs a migration + a knowledge-table write; backend-owned schema).
- [x] **10.5** Learning plan: gaps → phased study items (foundation → core → applied)
  with category-aware resource hints. (`features/learning.py`)
- [x] **10.6** Skill-progress tracking: diff two gap reports → closed / improved /
  regressed / opened + coverage delta. (`features/progress.py`)
- [x] **10.7** Target-role readiness synthesis: skills (10.1) + market (12.1) → one
  verdict, a must-gap capping a "ready". (`features/readiness.py`)
- [x] **10.8** Aggregate `growth-report` endpoint (readiness + gap + salary + learning
  plan + progress in one call) — the intended bridge target.
- [x] **10.9** Market skill demand: which skills a role family's postings ask for, and
  how often — the market-centric half of the gap view. (`features/demand.py`)
- [x] **10.11** Career progression planner: given an aspirational role, rank
  stepping-stone role families that are *reachable today* (current coverage) **and**
  build the dream role's missing skills. Composes gap-analysis + role-suggestions +
  demand; deterministic bridge score. (`features/progression.py`)
- [x] **10.12** Learning priority: enrich each gap with its market demand (10.9) over
  the role family and rank by importance × market pull, so the candidate learns the
  most-asked-for missing skill first. Composes gap-analysis + demand. (`features/prioritize.py`)
- [x] **10.13** Interview prep plan: the pre-interview checklist -- weak areas to study
  (gaps, by importance), strength stories to rehearse (covered skills mapped to the
  candidate's own STAR stories), and likely topics (responsibilities + gap-address
  lines). Complements the adaptive coach (interview.py). Composes gap-analysis + stories.

## Epic 11 — Outreach & Networking
- [ ] **11.1** Contacts registry (name, role, company, relation, last touch).
- [x] **11.2** Referral / networking message generator (evidence-bound; validator
  strips any skill the profile does not support). (`features/outreach.py`)
- [ ] **11.3** Follow-up reminders + cadence; surface stale contacts on dashboard.
- [ ] **11.4** Networking subagent wired into the orchestrator's whitelist.

## Epic 12 — Salary & Offer Intelligence
- [x] **12.1** Salary benchmarking against the seeded corpus (percentiles by role /
  seniority band / location) — deterministic, no external data required.
  (`features/salary.py`)
- [x] **12.2** Negotiation coaching: offer vs benchmark → leverage + talking points.
  (`features/negotiation.py`)
- [x] **12.3** Offer comparison (multiple offers, cash-only ranking). (`features/offers.py`)
- [x] **12.4** Counter-offer drafting (deterministic anchor + reasons, model phrases).
  (`features/counter_offer.py`)
- [x] **12.5** Equity annualization (intrinsic value over the vest), folded into offer
  comparison so ranking is by total comp. (`features/equity.py`, `features/offers.py`)

## Epic 13 — Data Portability & Export
- [ ] **13.1** One-click export bundle (resumes, knowledge, applications, interviews,
  growth plans) as JSON + a human-readable PDF.
- [ ] **13.2** Import / re-import with idempotent upsert; local backup snapshot.
- [ ] **13.3** Per-user data deletion (right-to-be-forgotten) wired through backend.

## Epic 14 — Job Ingestion Connectors
- [ ] **14.1** Pluggable connector interface (RSS / board API / paste) feeding `jobs`.
- [ ] **14.2** First real connector (e.g. RSS/Atom board) with the same hybrid
  index path as the seed import.
- [ ] **14.3** De-duplication + freshness sweep against existing `jobs`.

## Epic 15 — Analytics & Insights
- [ ] **15.1** Pipeline funnel: applied → OA → interview → offer, with conversion %.
- [ ] **15.2** Response-rate and time-in-stage analytics from `applications`.
- [ ] **15.3** Personal insight digest (weekly): strongest gaps closing, top matches,
  stalled applications.

## Epic 16 — Production Hardening
- [ ] **16.1** Monitoring/alerting on agent error rate, LLM cost, eval regressions.
- [ ] **16.2** Rate-limit dashboard + the residual SECURITY.md risks closed.
- [ ] **16.3** CI that runs all three suites + both eval harnesses on a schedule.

## Epic 17 — Internationalization & Accessibility
- [ ] **17.1** CN/EN content parity (the product is CN-context but English content).
- [ ] **17.2** Full a11y pass (keyboard, motion-reduce, screen-reader labels) — the
  recent frontend commits already moved this forward; finish the long tail.

## Epic 18 — Delivery
- [ ] **18.1** Production docker build + deployment runbook (existing DEPLOYMENT.md).
- [ ] **18.2** Public demo script + a short marketing/landing page.

## Definition of Done (per task)
Implementation + tests + wired into the real API/UI (no placeholder endpoints) +
lint/build green + a census/contract gate updated where the population moved.

## Execution discipline
- This repo is developed **concurrently**: read the file you are about to edit
  *immediately* before editing; `git add` only the files you created/changed so you
  never commit another session's in-flight work.
- Verify by running, not by reading. Offline harness: `LLM_PROVIDER=mock
  EMBEDDING_PROVIDER=hash`. Docker-dependent suites (backend `*IT`, RAG eval, E2E)
  are run by the user — don't fake them green.
- Every new AI claim must trace to evidence; never fabricate. Offline providers are
  refused when `APP_ENV=prod`.
- Keep `docs/PRODUCT.md`, `API.md`, `AGENTS.md` and their gates true to the code; a
  new endpoint/field updates the census in the same change.
- **ai-service features shipped ahead of their bridge are internal-only** and pinned
  by `tests/test_forward_features_contract.py` — add every new forward route there.
