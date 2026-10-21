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
  strength stories). Seventeen internal engines then; **Epic 13 (portability) and
  Epic 15 (analytics) add more** — export/serialize/render/redact + import-plan, and
  pipeline funnel / response-rate / insight-digest — all unit-tested offline and pinned by
  `tests/test_forward_features_contract.py` where they are routed.
  **The growth loop is now bridged end-to-end (2026-10-14)** — the 10.2 aggregate
  (`/api/v1/growth-report`), the 10.3 `/growth` panel, and 10.4 plan persistence all ship.
  The granular growth engines (gap, salary, readiness, learning, progress as their own
  routes) and the 12.x bridges are still unwired.
  **Every engine is bridged (2026-10-20).** The forward surface that shipped
  ahead of its bridges is empty: the 10.x granular engines, 11.2/11.3, the 12.x
  salary & offer quartet, the 13.x portability trio, the 14.x ingestion quartet,
  the 15.x analytics trio and the 16.1 health report all have a backend route
  now, and each has a frontend surface where the answer is worth a screen of
  its own — `/growth` (the report and the per-engine panel), `/networking` and
  the dashboard's follow-up tile, `/offers`, `/data`, `/ingestion`, `/analysis`
  and `/monitoring`. The ai-service's 3.2 table in `docs/API.md` is empty, and
  the gate that measures the split re-measures it rather than remembering it.
  The E2E suite grew to match: every signed-in route is walked for its heading,
  and the golden journey now answers the growth report, the gap engine, the
  salary benchmark, the digest, the funnel, the rates and the export bundle
  through the real API.

  **The bridges are tested and the product is finished (2026-10-20, later).**
  Every new route carries a controller test (24 of them, from 402 to 426), every
  new client hook a wire-shape test, and the new surfaces a normalizer test —
  549 frontend tests and 426 backend ones, all green.
  The product got the rest of what a shipped app needs: a chart component with
  no library behind it (`components/common/bar-chart.tsx` — the scale is the
  caller's, the value is always printed), the i18n table extended to the new
  pages with a gate that holds the two languages to the same key set, and the
  landing page promoted to the public front door.

  **The round closed on the gates (2026-10-20, last pass).** Six of the contract
  gates read the code rather than trust it, and the bridges moved what they
  read: the record census, the toast floor, the skipped-test roster, the
  documentation ledger's line numbers, and the rate-limit knob's reader list.
  Each is now pinned to the measured population, with a comment saying what
  moved — the gates are the product's own account of itself, so leaving them
  stale would be a lie in the one place the reader can check.

- **The portability gap is closed (2026-10-22).** The export bundle's `knowledge`
  section read the `documents` table — the files the reader uploaded — while the
  notes they *typed* lived in `user_notes` and in no section of the bundle at all.
  So a reader who kept their salary research in a note and then exported their
  data did not get that note back: "your data" meant "the data in the tables the
  export reads". Since **1.2.0** the bundle carries the notes and the contacts
  too — the reader's own words and the people they know — and the browser can
  redact them like any other section. The schema version is read as *numbers*
  now, so a 1.1.0 backup is still a valid bundle and a 1.1.5 one is held to the
  1.1.0 sections rather than to the newest.
- **And the restore stopped writing over somebody else's rows.** A bundle's ids
  are the source's, and the restore kept them so the links inside the bundle
  still pointed where they did — but an id that belongs to *another account's*
  row was written into that row. So restoring a colleague's export changed the
  colleague's data (a note they had edited since the export went back to the
  exported text) and gave the caller nothing of their own, while the answer
  said "created". The id is now kept only when it is free and minted when it is
  not: the restore still lands the rows, and it no longer lands them on top of
  somebody else's.

- **The errors a reader sees are still English (measured 2026-10-22, not closed).**
  A failed write answers with a toast, and the toast says what the server said — in
  English. The obvious fix is to translate by the **code**, because the code is the
  contract (`ApiErrorCode`'s own comment says "never rename an emitted code") and
  the code is what crosses the wire. Measured: the codes are **coarser than the
  messages**. `RESUME_NOT_FOUND` answers with six different sentences ("No parsed
  resume available for matching", "This resume has no original file behind it",
  "Resume not found", …), `BAD_REQUEST` with twelve, `TOKEN_INVALID` with five,
  `INTERNAL_ERROR` with five, `NOT_FOUND` with four, `DOCUMENT_NOT_FOUND` with
  three. One sentence per code would tell a reader whose resume exists but has no
  parsed version that "that resume is no longer there" — so the fix is not a
  translation, it is a *finer vocabulary*: roughly twenty-five more codes (one per
  distinct wording), about sixty sentences in each language, and the throw sites
  changed to name them. The ai-service's own rejections (the bundle's, the
  ingestion's) would need the same treatment, since a 400 that crosses the bridge
  arrives as one code whichever service said it. The rule the browser uses to read
  a key is now in one place (`lib/i18n/locale-context.tsx`'s `lookup`/`fill`), and
  the piece still missing is reading the reader's language *outside* a render — a
  toast is raised from an event handler, long after the render that knew it.
- **The export's readable half is Chinese-only (measured 2026-10-22, not closed).**
  13.1's *human-readable* export — the Markdown document and the print-ready
  HTML — is written in Chinese and has no other language: the section names, the
  title, the headings, the labels, and the note that says the file is
  anonymized. Measured: about 35 sentences across `export.py`'s `to_markdown`
  and `export_render.py`, so the work is the sentences plus a way to say which
  language a bundle should be rendered in. The bundle already carries the
  reader's id and the `anonymized` marker, so the locale could travel the same
  way; nothing carries it yet. An English reader's "printable document" is a
  Chinese document, which is the same class of defect as the rest of the
  i18n holes: a word the reader cannot change.
- **The restore's delete semantics for the sections the current state does not
  cover.** The plan tells a delete from a create by comparing the bundle with the
  caller's current state, and the backend's current state covers the profile, the
  applications, the growth runs, the notes and the contacts. The resumes, the
  knowledge base, the job descriptions, the interviews and the memories are not
  in it, so a restore cannot remove a row the bundle no longer carries in those
  sections — the plan never promises a delete it cannot keep. Closing it means
  either the current state grows to cover them (and the sections whose ids the
  restore remaps have to be thought about separately) or the restore is documented
  as an upsert rather than a replacement.
## Epic 10 — Growth Intelligence
- [x] **10.1** Gap & growth analysis engine (evidence-bound coverage verdict).
  (Backend bridge: `POST /api/v1/growth/gap-analysis`; the `/growth` page's
  engine panel runs it on its own.)
- [x] **10.2** Backend bridge: `HttpAiServiceClient.growthReport` + `GrowthController`
  (`/api/v1/growth-report`, the 10.8 aggregate; granular endpoints after). `docs/API.md`
  extended, the route rate-limited as AI-cost, controller pinned by `GrowthControllerTest`.
- [x] **10.3** Frontend page/panel: target-role input, readiness verdict, coverage
  bars (covered / partial / gap), learning plan, salary band, progress delta.
  (`/growth`, rendered from the 10.2 aggregate; the panel hands its own gap block
  back as `previous` until 10.4 persists the plan server-side).
- [x] **10.4** Persist a `growth_plan` per (user, target_role) so repeat runs diff.
  (`V9__growth_plans` + `GrowthService`: every run stored, the stored gap block fed
  back as the next run's `previous` unless the caller brought one; a failed store
  degrades the next diff, never the answer.)
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
- [x] **11.1** Contacts registry (name, role, company, relation, last touch).
  (`/api/v1/contacts` CRUD, `V10__contacts`, user-scoped; the outreach generator's
  `{name, role, company}` consumer shape came first and this registry feeds it.)
- [x] **11.2** Referral / networking message generator (evidence-bound; validator
  strips any skill the profile does not support). (`features/outreach.py`)
- [x] **11.3** Follow-up reminders + cadence; surface stale contacts on dashboard.
  The engine and its agent-facing half shipped first: `features/reminders.py` ranks a
  contact against its own relation's cadence (bucket before days, so a contact past due
  outranks a merely-old one) and the `get_follow_ups` tool hands that list to the agent.
  Both now read through one pair of definers -- `domain.list_contacts_for_follow_ups`
  (the capped, oldest-touch-first read) and `reminders.follow_ups_for` (rank, then draft)
  -- and that pair is routed as `POST /internal/features/follow-ups`, so the tile cannot
  disagree with the copilot. The dashboard tile now reads the same rows.
- [x] **11.4** Networking subagent wired into the orchestrator's whitelist.
  (`SUBAGENT_TOOLS["networking"]` = `search_contacts`, `get_follow_ups`, `draft_outreach`,
  `log_contact_touch`, `get_user_profile` -- the contact reads plus one touch write, and
  no job or application tool, which is the boundary AGENTS.md §2 documents and
  `tests/test_networking_tools.py` enforces.)

## Epic 12 — Salary & Offer Intelligence
- [x] **12.1** Salary benchmarking against the seeded corpus (percentiles by role /
  seniority band / location) — deterministic, no external data required.
  (`features/salary.py`. Backend bridge: `POST /api/v1/offers/salary-benchmark`;
  frontend: the `/offers` page.)
- [x] **12.2** Negotiation coaching: offer vs benchmark → leverage + talking points.
  (`features/negotiation.py`. Backend bridge: `POST /api/v1/offers/negotiate`.)
- [x] **12.3** Offer comparison (multiple offers, cash-only ranking). (`features/offers.py`.
  Backend bridge: `POST /api/v1/offers/compare`.)
- [x] **12.4** Counter-offer drafting (deterministic anchor + reasons, model phrases).
  (`features/counter_offer.py`. Backend bridge: `POST /api/v1/offers/counter-offer`.)
- [x] **12.5** Equity annualization (intrinsic value over the vest), folded into offer
  comparison so ranking is by total comp. (`features/equity.py`, `features/offers.py`)

## Epic 13 — Data Portability & Export
- [x] **13.1** Export bundle (resumes, knowledge, applications, interviews, growth
  plans) as JSON + a human-readable PDF. (ai-service half: `features/export.py`
  gather/serialize/validate/diff + content-hash idempotency; `features/export_render.py`
  print-ready HTML + lazy weasyprint PDF. Backend bridge: `POST /api/v1/data-portability/export`.)
- [x] **13.2** Import / re-import with idempotent upsert; local backup snapshot.
  (ai-service half: `features/import_plan.py` validates a bundle, then emits per-item
  create/update/delete ops with per-item content hashes so the backend can skip
  unchanged rows; `python -m app.ops.restore_plan backup.json [--existing current.json]`
  dry-runs that plan from a backup file with no database, so an operator can preview a
  restore or diff a backup before any write. Backend bridge: `POST /api/v1/data-portability/import-plan`
  and `POST /api/v1/data-portability/import-apply` — the second one executes the plan
  and reports what it wrote **and which sections it left alone, with the reason**. Every
  section applies: the profile, the applications, the stored growth runs, the job
  descriptions and the interviews are row writes (so the analyst does not run again and
  the interviewer does not question the user a second time), the resumes and the
  knowledge base are re-ingested (their ids belong to the ingestion pipeline, not to
  the row), and the long-term memories are upserted on the same (kind, key) the
  extraction path uses, which makes the restore idempotent.)
- [x] **13.3** Per-user data deletion (right-to-be-forgotten). (ai-service half:
  `features/export_redact.py` deep-copy section redaction + `anonymize`; recomputes the
  content hash and records `redacted_sections`. Backend bridge: `POST /api/v1/data-portability/redact`.)
  The redaction also has to leave a bundle the product can still use, which took three
  rules of its own: the counts are recomputed over what is left (they are the badges the
  reader sees and the last line of the printable document, and a stale count says their
  data is still in the file); a section the manifest records as withheld is *not* a
  missing section, so the redacted file still validates and still restores; and a
  withheld section gets no import ops at all, so "I did not share this" never reads as
  "delete yours".)

## Epic 14 — Job Ingestion Connectors
- [x] **14.1** Pluggable connector interface (RSS / board API / paste) feeding `jobs`.
  (ai-service half: `features/ingestion.py::Connector` protocol + `normalize_posting`
  mapping a raw payload onto the canonical jobs fields. The HTTP fetch + `jobs` write
  stay in the backend.)
- [x] **14.2** First real connector (e.g. RSS/Atom board) with the same hybrid index path
  as the seed import. (ai-service half: `features/ingestion.py::parse_feed` parses RSS
  2.0 / Atom XML, and `parse_json_board` parses a board-API JSON payload (top-level array
  or jobs/data/results/items/postings) -- both stdlib-only, offline, size-capped, and
  raising on bad input. `parse_any` picks between them from the text, so a reader is
  not asked to say which shape they pasted. Routed as
  `POST /internal/features/parse-feed`. Backend bridge:
  `POST /api/v1/jobs/ingest/parse`.)
- [x] **14.3** De-duplication + freshness sweep against existing `jobs`.
  (`features/ingestion.py::dedupe_postings` collapses exact-fingerprint duplicates to
  the newest / most complete survivor; `freshness_sweep` partitions into fresh / stale /
  expired / undated; `plan_ingest` composes parse/normalize/dedupe/freshness into one
  create / update / close plan. Routed as `POST /internal/features/dedupe-jobs`,
  `/freshness-sweep`, `/plan-ingest`; `python -m app.ops.ingest_plan feed.xml|feed.json`
  dry-runs that plan from a file with no database (`--existing`, `--now` for a
  reproducible diff). Backend bridge: `POST /api/v1/jobs/ingest/dedupe|freshness-sweep|plan`.)

## Epic 15 — Analytics & Insights
- [x] **15.1** Pipeline funnel: applied → OA → interview → offer, with conversion %.
  (`features/analytics.py::pipeline_funnel`, `POST /internal/features/pipeline-funnel`.
  Reached-stage semantics are cumulative; `rejected` counts as reached `applied` only,
  the honest bound of a schema that stores just the current status.)
- [x] **15.2** Response-rate and time-in-stage analytics from `applications`.
  (`features/analytics.py::response_rate`, `POST /internal/features/response-rate`.
  A rejection is a response; per-stage avg/median durations skip apps missing timestamps
  rather than inventing them.)
- [x] **15.3** Personal insight digest (weekly): strongest gaps closing, top matches,
  stalled applications. (`features/analytics.py::insight_digest`,
  `POST /internal/features/insight-digest`. Surfaces stalled apps past a window and the
  live stage mix; `growthDeltas` / `topMatches` are echoed through so the digest composes
  the growth engines instead of inventing data. Backend bridge: `GET /api/v1/analysis/insight-digest`.)

## Epic 16 — Production Hardening
- [x] **16.1** Monitoring/alerting on agent error rate, LLM cost, eval regressions.
  (ai-service half: `features/monitoring.py` -- `summarize_runs` (error rate, latency
  percentiles, cost/token totals), `cost_by`, and a generic `detect_regressions` that
  compares a metric set to a baseline with direction + severity; `health_report`
  composes them into a healthy/warn/regressed verdict and also folds an eval harness's
  current/baseline pair. Routed as `POST /internal/features/health-report`; backend
  bridge: `GET /api/v1/monitoring/health-report`.)
- [x] **16.2** Rate-limit dashboard + the residual SECURITY.md risks closed.
  (Backend: `GET /api/v1/rate-limit/status` + `RedisSlidingWindowRateLimiter.remaining`.
  Frontend: `/rate-limit` page showing the configured limits and the caller's
  remaining quota per bucket.)
- [x] **16.3** CI that runs all three suites + both eval harnesses on a schedule.
  (`.github/workflows/ci.yml`: an offline gate for all three suites plus nightly
  Docker-backed `*IT` and both eval harnesses.)

## Epic 17 — Internationalization & Accessibility
- [x] **17.1** CN/EN content parity (the product is CN-context but English content).
  (Frontend: `lib/i18n/translations.ts` + `LocaleProvider` context; the root layout
  wraps the app, the sidebar reads every label through a key, and the new
  surfaces — offers, analysis, monitoring, rate limit, data, ingestion and the
  growth engine panel — answer in the caller's language. A gate
  (`translations.test.ts`) holds the two halves of the table to the same key set
  and keeps Chinese out of the English table.)
- [x] **17.1b** The browser's copy census (the long tail of 17.1, measured).
  (Frontend: `lib/i18n/copy-scan.ts` walks the 130 `.tsx` files under
  `app/` and `components/` and finds the copy that is still a literal — a
  copy-bearing attribute (`title`, `label`, `placeholder`, `aria-label`,
  `eyebrow`, `heading`, …), the text between two tags at any length, the
  same copy-bearing names inside an object literal (`{ label: "Technical" }`)
  or inside a JSX expression (`{cond ? "Interview-ready" : "Needs work"}`),
  and a plain quoted literal (`toast.success("Export ready.")`). A string in
  any of those is a word the reader cannot change, and it is the shape the
  fix took every time. The four shapes the scan did not read before were
  the blind spots: half the product's copy is written as an object literal,
  most of the rest is prose longer than the scan's old length bound, the
  words a card shows when one thing is true and another when it is not are
  inside an expression, and a toast message is neither of those — it is a
  string that is simply a *value*. A bar labelled "Technical" on a Chinese
  page was exactly as invisible to the gate as an attribute was.
  `KNOWN` is the honest list of what is left, file by file and string by
  string, and the number is pinned: 93, every one of them in a file
  another session is working in at the same time.
  `scripts/regen-known.mjs` regenerates the list from the browser's own
  sources — through the same scan the gate uses, so the two cannot drift
  and leave the list measuring a different population than the gate.)
  The pipeline's seven stage names live in one table (`stages.*`) read
  through `lib/pipeline.ts`'s three readers, the score dimensions live in
  one table (`dimensions.*`) read through `lib/dimensions.ts`, the
  document kinds and the ingestion stages in tables of their own
  (`lib/source-kinds.ts`, `lib/ingest-steps.ts`), the section overlines in
  one (`eyebrows.*`), and `t()` fills a `{hole}` so a sentence can be
  written in one language's word order and not another's.)
- [x] **17.1c** The page's title, in the reader's language.
  (The title is rendered into the document's head, and the head is the
  browser's first paint and the crawler's whole view — so it has to be
  right in the HTML the *server* sends. The locale therefore travels in a
  cookie as well as in `localStorage`, and the server reads it
  (`lib/i18n/metadata.ts`): twenty-four routes name themselves through
  `sectionMetadata` or `absoluteMetadata`, and the root's title template
  still gives the suffix, so a section reads "Jobs · AI Career OS" in
  English and "职位 · AI Career OS" in Chinese. A `useEffect` that writes
  `document.title` does *not* work: React's own metadata reconciliation
  resets it a moment later, because the `<title>` element is part of the
  tree it just hydrated. The end-to-end suite holds the result — the
  titles are read in both languages, and the 404 names itself in the
  reader's language too.)
- [x] **17.2** Full a11y pass (keyboard, motion-reduce, screen-reader labels) — the
  recent frontend commits already moved this forward; finish the long tail.
  (Global CSS: skip link, `:focus-visible` ring, `.sr-only`, 44px touch targets,
  `prefers-contrast` and `forced-colors` media queries.)

## Epic 18 — Delivery
- [x] **18.1** Production docker build + deployment runbook (existing DEPLOYMENT.md).
  (`docker-compose.prod.yml` + `docs/DEPLOYMENT.md`; the runbook now opens with an
  ai-service **preflight gate** (`app/ops/preflight.py`, `python -m app.ops.preflight`)
  that blocks offline providers in prod, the published default `INTERNAL_API_TOKEN`, the
  dev DB password, a missing API key, and an inverted pool — pure and offline-tested,
  with a census pinning its default constants to `config.py`.)
- [x] **18.2** Public demo script + a short marketing/landing page.
  (demo script: `docs/DEMO.md` — the eight-minute golden journey, UI-first, with the API
  equivalents per step and the three offline dry-run CLIs. Frontend: `app/(marketing)/page.tsx`
  — hero, features, trust, CTA sections.)

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
