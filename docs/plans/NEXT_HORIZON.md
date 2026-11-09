# Next horizon — backlog beyond Epic 77

This file is the forward backlog while `docs/ROADMAP.md` and
`docs/plans/plan_long_term.md` are being edited by another session (Epic 74.1/74.2
is in flight). Each item below comes from something **measured in this repo**, not
from a wish list. Pick the top one, read the current files, implement, and move the
entry into ROADMAP when it lands.

Priority order is by "a reader or an operator can be misled today", not by size.

---

## Epic 78 — the deployed stack says which commit it is

> **Partly shipped by a concurrent session** (`cbbb90f feat(observability): bake
> build SHA into health (Epic 78)`), with `HealthService.java` still in flight
> when this note was updated. Read the current file before starting: the job now
> is to verify the SHA reaches `/health` **and** the journey report header, and to
> add the contract gate — not to rebuild what already landed.

**Measured (2026-11-07).** On 2026-11-07 the six `careeros-*` containers were healthy and
`GET /api/v1/health` answered `{db, redis, storage, ai: true}`, but
`docker inspect careeros-backend --format '{{.Created}}'` was hours older than
`HEAD`. A golden-journey run against that stack was therefore exercising code that
no longer matched the checkout. Nothing in the health answer or the journey report
could tell the operator which commit they had just validated.

**Do.** Bake the build SHA / commit id into each image (build arg → env →
`/health`'s `data`), and have `scripts/journey_api.py` print it once at the top of
every run so a latency report always names the code it measured. Add a contract
gate over the health response shape and a doc row in `API.md`.

**Done when** a journey report's header contains a SHA, `curl /health` returns the
same SHA, and a gate reddens if the field disappears. No secrets in the answer.

---

## Epic 79 — a real-provider eval anyone can reproduce — **CLOSED 2026-11-09**

**Measured (2026-11-07).** The RAG golden set (`app/eval/dataset.py`) is tuned for
the seeded dev corpus. On the live Postgres the best keyword-covered user had only
5 matching chunks, so a run would skip most of the 15 cases — and
`assert_something_was_measured` only refuses an *entirely* empty run, not a
mostly-skipped one. `ollama.exe` and the derived CPU model `qwen2.5-cpu` exist,
but no service is started by default.

**Already shipped before this session (do not rebuild).**
`app/ops/seed_eval_corpus.py` + `scripts/eval-corpus.json` +
`tests/test_seed_eval_corpus.py` ingest the golden corpus through the public path
and poll until `ready`; the nightly corpus step is that run. `EVALUATION.md`
already names the CPU-only ollama setup.

**Closed by this session.** `run_eval` gained `--require-all-cases`: any
`no_ground_truth` skip is now a non-zero exit that names the missing case ids and
the seed command, and the flag is recorded in the report's `config`.
`docs/EVALUATION.md` §5 carries the exact reproduction commands and the
"check `errors`, then `skipped`, then aggregate" rule. Four runner tests plus a
mutation probe (disabling the strict gate reddens exactly one case).

Remaining operator step, not a code task: seed a user on the running stack and
record a dated 15/15 mock-provider report as the first baseline.

---

## Epic 80 — the registry narrows by relationship — **CLOSED 2026-11-09**

**Measured.** Epic 70.3 gave the contacts board a word and 72 gave it a real
window. The `relation` column (referrer / mentor / peer) is written by the dialog
and rendered as a badge, but there is no way to ask "show me only referrers". The
notes board solved the same shape in 64.1/64.2 (tags + counts + a filter row).

**Do.** `GET /contacts` binds `?relation=` inside the same `BOARD_WHERE` and the
count query repeats it; add `GET /contacts/relations` for the counts; `/networking`
gains a chip row with `?relation=` in `PAGE_DEFAULTS`, resets `page` on a new
choice, and keeps the word and the window narrowing together.

**Done when** three disjoint filters (word, relation, page) compose in one real
Postgres IT test, and the endpoints / needle / window censuses move in the same
change.

**Shipped 2026-11-09.** `GET /contacts` binds `relation` with the same
"blank means no constraint" shape as the word (lower-cased by the caller,
matched case-insensitively); the count query repeats the same `BOARD_WHERE`
so the pager total is the chip-and-word total, not the window's. New
`GET /contacts/relations` returns the chip row's counts in query order (count
descending, relation name tiebreak). `/networking` gained its chip row: the
word, the chip and the window travel together in one `useContacts` call, the
chip resets `page` to 0, and the empty states name which narrowing left the
registry empty (`networking.noRelationContacts`). `PagePool` census moved: 209
records (`ContactDtos.RelationCount`), native-query pin moved
(`ContactRepository.java`, SECURITY.md SQL-injection row updated to name the
eight). Full suites green incl. `ContactRelationIT` 2/2 against the live stack.


---

## Epic 81 — one timeline over the whole loop — **CLOSED 2026-11-09**

**Measured.** The product stores resume versions, JD analyses, matches, tailored
materials, interview sessions, applications, notes, contacts, offers and digests,
each with its own screen. There is no single place where a reader can see "what
happened to this job search, in order". Every AI claim in the product is already
evidence-bound, so a timeline is a read over existing rows, not a new model.

**Do.** An internal engine `POST /internal/features/career-timeline` in ai-service
that merges per-user events into `{at, kind, title, refId, summary}` (deterministic
sort, no LLM), bridged by a backend `GET /api/v1/timeline` scoped to the caller,
with a `/timeline` page. Pin the new internal route in
`tests/test_forward_features_contract.py` and the public row in `API.md`.

**Done when** a journey-created account sees its own events in order, an empty
account sees an honest empty, and no other account's row can appear.

**Shipped 2026-11-09.** The engine (`app/features/career_timeline.py`) merges the
caller's event rows into one deterministic `{at, kind, title, refId, summary}` list,
sorted by `(at, kind, refId)`, no LLM; `POST /internal/features/career-timeline`
is behind `require_internal` with its FORWARD pin. The backend bridge
(`com.careeros.report`: `TimelineService` + `TimelineController`) reads the caller's
own applications, notes, contacts, resume versions, matches and interview sessions
(50 rows per source, capped), maps them to the engine's five fields and forwards
them to the engine; the answer is the engine's own shape under `GET /api/v1/timeline`
(`TimelineIT` 3/3 against the live stack (+ e2e `timeline.spec.ts` 1 passed in a real
browser on this stack): empty account answers an honest empty,
one account's rows never reach another, all six kinds mapped and pinned by units).
The frontend gains `/timeline` (`lib/hooks/timeline.ts`, `mapTimelineEntry`,
`KIND_VISUALS`) and its nav row; i18n has both languages. Measured green: backend
non-IT 1214 run / 0 failures incl. `TimelineServiceTest` 3/3; ai-service 2286
passed / 2 skipped; frontend 1164/1164 (118 files) + `tsc --noEmit` + `npm run
build`; doc census gates 54/54.

---

## Epic 82 — quality regressions are visible over time — **CLOSED 2026-11-09**

> **Shipped.** `app/ops/verify_eval_baseline.py` grades errors -> population ->
> skipped -> provider fallback -> shared metrics, with exit codes 0/1/2;
> `evals/baseline.json` is checked in from the real 15/15 report of 2026-10-14;
> `tests/test_verify_eval_baseline.py` (20 cases + a mutation probe) pins both.
> Verified against three real historical reports: the 13/15 lexical-fallback
> outage is refused *before* any aggregate is read, the 12-skip run is refused,
> and the low-score strategy run is named as a regression.
> `docs/EVALUATION.md` §6 carries the CI command and the baseline-editing rule.
> What remains is an operator choice, not code: wire the command into the nightly
> workflow once the team decides which run is authoritative.

**Original brief (kept for the reasoning).**

**Measured.** The eval harnesses write reports to `ai-service/evals/reports/`
(gitignored) and can `--diff` two runs, but nothing compares a run to the last
known-good baseline in CI, and the memory notes that an all-error real-provider run
once *looked* like a clean regression. `errors` must be read before aggregates.

**Do.** A `scripts/verify_eval_baseline.py` that loads a checked-in baseline JSON,
refuses a run with `errors > 0` or `n_cases == 0`, and compares recall/F1 with an
explicit tolerance, plus a dated record of the baseline in `docs/EVALUATION.md`.

**Done when** a deliberately broken retrieval run exits non-zero with a message
naming the metric that moved, and a healthy run passes without editing the
baseline.

---

## Epic 83 — the timeline narrates: the pipeline log folds in — **CLOSED 2026-11-09**

**Measured.** Epic 81 gave every account one ordered read of what it owns, but the spine of the
search — the transitions between stages — lived in `application_events` without ever reaching it.
The reader saw "Backend Engineer · Acme Robotics — status: saved" and nothing of the weeks of
work between saved and applied.

**Do.** `TimelineService` reads the transition log (capped at the same 50 newest), maps it to
the engine's five fields — status moves arrive as `application` rows titled `→ <to>` with a
`from → to` summary, notes written beside a move arrive as `note` rows truncated to 120 chars,
reminders/outcomes as their own kinds-labeled rows — and leaves the fold's contract untouched.
Kinds that own a served screen now deep-link into it (`/applications?application=<refId>`,
`/resumes/<refId>`, `/interviews/<refId>`); facts with no screen stay text.

**Done when** a real status PATCH round-trips into the timeline (`→ oa` appears for the right
account only), and units pin the five-field mapping plus the transition row.

**Shipped 2026-11-09.** `TimelineService` (`com.careeros.report`) now folds the transition log
into the engine's input; `TimelineController` unchanged (same `GET /api/v1/timeline` answer
shape); frontend `KIND_VISUALS` gained per-kind `href` on `application` / `resume_version` /
`interview` rows only. Measured green: backend non-IT 1215 run ×0 failures; `TimelineIT` 3/3
against the live stack (row count grows by exactly one transition row per status PATCH, and the
`→ oa` title is present); `TimelineServiceTest` 4/4 (entity + transition both fold, summary
`saved → applied`, at carried verbatim); frontend 1164/1164 (118 files), `tsc` clean,
`npm run build` compiles, `npm audit --omit=dev` 0.

---

## Epic 84 — /timeline?kind= narrows the fold — **CLOSED 2026-11-09**

The timeline was the one page where the narrowing had no URL. With Epic 80's chips as the pattern
and Epic 70's URL-state rule as the convention, the fold became `/timeline?kind=application`.

**Do.** `useUrlState<{ kind?: string }>(PAGE_DEFAULTS)` carries one key; chips and counts are
computed from the engine's own answer (an absent kind is not offered); a bogus `?kind=` narrows to
its own honest empty (`timeline.noKindRows`, both languages) rather than the workspace's default empty.
`All kinds` clears it. No param on the API row — narrowing is a view over one capped read.

**Done when** the page tests pin the chip counts, `aria-pressed`, the URL write on chip/deselect, the
absent-kind and unknown-kind honest empties, and the row links from 83 still render.

**Shipped 2026-11-09.** `./timeline/page.tsx` renders `KIND_VISUALS` per non-empty kind with the
count as a tabulated adornment; `useUrlState` restores a pasted link; `timeline.kindFilter` /
`filterAll` / `noKindRows` i18n in both languages. Measured: 7 page tests green, frontend 1169/1169
(118 files), `tsc --noEmit` clean, `npm run build` 33/33, `npm audit --omit=dev` 0.

---

## Rules for whoever picks these up

- This repo is developed **concurrently**: re-read a file immediately before
  editing, `git add` only your own files, and read the whole diff before staging.
- `GET /contacts` and the Saved tab are being changed by another session right
  now (Epic 74); do not start Epic 80 until that lands.
- Implementation + tests + real API/UI wiring + census/contract gates in the same
  change. Docker-dependent suites are run against the live stack, never faked.
- Salary stays in the currency's base unit per year; resume body field is
  `plaintext`; offline providers are refused under `APP_ENV=prod`.
