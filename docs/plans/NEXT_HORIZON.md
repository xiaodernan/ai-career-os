# Next horizon — backlog beyond Epic 77

This file is the forward backlog while `docs/ROADMAP.md` and
`docs/plans/plan_long_term.md` are being edited by another session (Epic 74.1/74.2
is in flight). Each item below comes from something **measured in this repo**, not
from a wish list. Pick the top one, read the current files, implement, and move the
entry into ROADMAP when it lands.

Priority order is by "a reader or an operator can be misled today", not by size.

---

## Epic 78 — the deployed stack says which commit it is

**Measured.** On 2026-11-07 the six `careeros-*` containers were healthy and
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

## Epic 80 — the registry narrows by relationship

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

---

## Epic 81 — one timeline over the whole loop

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

---

## Epic 82 — quality regressions are visible over time

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

## Rules for whoever picks these up

- This repo is developed **concurrently**: re-read a file immediately before
  editing, `git add` only your own files, and read the whole diff before staging.
- `GET /contacts` and the Saved tab are being changed by another session right
  now (Epic 74); do not start Epic 80 until that lands.
- Implementation + tests + real API/UI wiring + census/contract gates in the same
  change. Docker-dependent suites are run against the live stack, never faked.
- Salary stays in the currency's base unit per year; resume body field is
  `plaintext`; offline providers are refused under `APP_ENV=prod`.
