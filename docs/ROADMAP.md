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
- **Epic 10.1: DONE (2026-10-11).** Career Gap & Growth Analysis feature shipped in
  ai-service (`app/features/gap_analysis.py` + `POST /internal/features/gap-analysis`)
  with 17 passing unit tests. Backend wiring + UI are the remaining 10.x tasks.

## Epic 10 — Growth Intelligence
- [x] **10.1** Gap & growth analysis engine (evidence-bound coverage verdict).
- [ ] **10.2** Backend bridge: `HttpAiServiceClient` method + controller endpoint
  `/api/v1/gap-analysis` (X-Internal-Token). Extend `docs/API.md` + its gate.
- [ ] **10.3** Frontend page/panel: target-role input, coverage bars (covered /
  partial / gap), development plan list, link to learning resources.
- [ ] **10.4** Persist a `growth_plan` per (user, target_role) so repeat runs diff.
- [ ] **10.5** Learning plan generation: turn gaps into ordered study items with
  resource hints, reusing the interview report's `recommended_study` shape.
- [ ] **10.6** Skill-progress tracking: when a gap later appears in the resume /
  knowledge base, mark it closed and surface the delta on the dashboard.

## Epic 11 — Outreach & Networking
- [ ] **11.1** Contacts registry (name, role, company, relation, last touch).
- [ ] **11.2** Referral / networking message generator (evidence-bound, per contact).
- [ ] **11.3** Follow-up reminders + cadence; surface stale contacts on dashboard.
- [ ] **11.4** Networking subagent wired into the orchestrator's whitelist.

## Epic 12 — Salary & Offer Intelligence
- [ ] **12.1** Salary benchmarking against the seeded corpus (percentiles by role/
  seniority/geo) — deterministic, no external data required.
- [ ] **12.2** Negotiation coaching: given an offer, surface leverage points from the
  candidate's match strength + market data.
- [ ] **12.3** Offer comparison view (multiple offers side by side).

## Epic 13 — Data Portability & Export
- [ ] **13.1** One-click export bundle (resumes, knowledge, applications, interviews,
  growth plans) as JSON + a human-readable PDF.
- [ ] **13.2** Import / re-import with idempotent upsert; local backup snapshot.
- [ ] **13.3** Per-user data deletion (right-to-be-forgotten) wired through backend.

## Epic 14 — Job Ingestion Connectors
- ] **14.1** Pluggable connector interface (RSS / board API / paste) feeding `jobs`.
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
  never commit another session's in-flight work. See `MEMORY.md`.
- Verify by running, not by reading. Offline harness: `LLM_PROVIDER=mock
  EMBEDDING_PROVIDER=hash`. Docker-dependent suites (backend `*IT`, RAG eval, E2E)
  are run by the user — don't fake them green.
- Every new AI claim must trace to evidence; never fabricate. Offline providers are
  refused when `APP_ENV=prod`.
- Keep `docs/PRODUCT.md`, `API.md`, `AGENTS.md` and their gates true to the code; a
  new endpoint/field updates the census in the same change.
