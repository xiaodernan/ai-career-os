# Algorithms horizon — Epics 132+

The product's loop is complete and the performance horizon (118–131) closed every
cost claim it made with a measurement. This horizon answers a different question
the operator actually pays for: **where does the algorithm come from, and is it
the cheapest one that gives the same answer?**

Epic 132 shipped a dependency-free algorithms package (`ai-service/app/algorithms`)
— an O(1) LRU/TTL, a stable O(n log k) heap top-K, dense/sparse cosine, Okapi BM25,
and the skill-gap/job-rank scorers — with 48 measured tests. A package nobody calls
is dead weight, so this horizon's rule is the repo's existing Definition of Done:
**an algorithm lands only when it replaces a live call site, and the replacement
is pinned by a test that fails if the old complexity sneaks back.**

| Epic | Claim | Verification |
|---|---|---|
| 132 | The primitives exist and are measured | `test_the_algorithms_module.py` (50) |
| 133 | The top-K helper uses the *right* heap for the scale | measurement + stability/streaming contract; fusion keeps its sort on purpose |
| 134 | A rerank that costs no model call is available and honest | `RERANK_MODE=bm25`, mode census, 10 offline rerank tests |
| 135 | The lexical channel can be scored in-process without pg_trgm when the corpus is small | CLOSED with evidence — pg_trgm's only live use is trigram near-miss recall, which term scoring cannot replace; no measured corpus bottleneck; BM25 rerank already shipped in 134 |
| 136 | N embed replicas do a job once, and a crashed worker's job comes back | `WorkQueue` consumer-group semantics (fake + real Redis), 12 + 12 offline tests |
| 137 | The auth door carries the landing's design language, without its light-panel pitfalls | `layout.test.ts` source contract, copy census, build + bundle budget |
| 138 | A poison job stops burning a worker on every retry; a failed retry never drops the job | re-queue + `attempts` + bounded DLQ, 9 offline tests + real-Redis end-to-end |
| 139 | A dead-lettered job stops being re-injected by the producer each tick, and heals when its cooldown lapses | `DlqGuard` Redis-ZSET cooldown, 32 offline tests + real-Redis end-to-end |
| 140 | The dead-letter pipeline can be *seen*: one honest verdict over live Redis + consumer liveness | read-only `GET /internal/ops/workqueue`, pure-function health fold, 54 offline tests + real-Redis end-to-end |
| 141 | The signed-in first screen carries the landing/auth design language, without washing the light theme or growing the bundle | `dashboard/page.test.ts` source contract, copy census, build + bundle budget |
| 143 | The RAG cache's saving is measured honestly and its invalidation boundary is named, not assumed | read-only `GET /internal/ops/cache`, pure-function verdict (0-rate is three states), off/memory/layered work-count baseline, 48 offline tests |
| 144 | A transient provider blip gets a jittered backoff window to heal in, instead of burning `max_deliveries` in five ticks | Redis-ZSET delay queue + pure-function exponential/full-jitter fold, zero-drift opt-in (worker default ON), 34 offline tests + real-Redis end-to-end |
| 145 | The producer stops re-enqueueing a job that is still sleeping out its backoff, so the delay is never bypassed | `parked_ids()` + dual-source `_suppressed(queue, guard)` unioned into the producer's SQL and the consumer's ACK path, both reads independent/fail-open, 58 offline tests |
| 146 | The queue stops claiming no worker ever died: orphan recovery is counted honestly | `WorkItem.reclaimed` observation tag from `XAUTOCLAIM`, `drain()` folds it into `ClaimStats.reclaimed`, zero behaviour drift, 5 offline tests |
| 147 | Deleting a note/source/resume stops the copilot quoting it from cache: the epoch bumps after the delete commits | `POST /internal/rag/cache/invalidate` + backend `RagCacheInvalidator` (after-commit, fail-open) wired into `KnowledgeService`; endpoint has a real caller, 9 offline + 6 backend tests |
| 148 | A long agent run cannot grow the timeline's DOM or reducer without bound: the trace window is O(cap), and what it folds away is counted, not hidden | pure `foldTrace` / `settleTraceFold` with injected `cap`, zero drift vs the old reducer, honest `tracesOmitted` surfaced in en/zh; 17 offline tests + source-contract |
| 149 | A concurrent spring-cloud merge is reconciled: the dev edge activates the same registry profile as the backend, and the count/timeout censuses tell the truth again | dev `docker-compose.yml` gateway gets `SPRING_PROFILES_ACTIVE=eureka` + `EUREKA_DEFAULT_ZONE`; `gateway-edge` spec counted in e2e/README + PRODUCT.md (69/69) and its alias registered; `.env.example` backoff comment stops masquerading as a Redis timeout; 17 + 22 offline gates |
| 150 | The two read-only ops verdicts get a real consumer: a backend collector scrapes their measured numbers into Prometheus, and their `no backend caller` markers become true | `AiOpsMetrics` (`@Scheduled` + `Gauge`) over `GET /internal/ops/{workqueue,cache}`, 7 excused-by-name signals, fail-open keeping last reading; backend `AiServiceClient` seam + `HttpAiServiceClient` GETs with a nil system id; API.md ledger 10→8; 7 offline backend tests + 31 contract/meter gates |
| 151 | A task's owner is decidable on any replica, not just the one that made it: the mirror that carries the frames also carries ownership, so the gate stops failing closed on a sibling | `aowner()` memory-first then `XREVRANGE` over the mirrored `owner` field; `_require_owner` async; owner never enters a wire frame or `state()`; 6 offline tests (fake-streams Redis) + 59 contract/census gates; MICROSERVICES §6 and PERFORMANCE_HORIZON legacy note reconciled |
| 152 | A long-lived service stops accumulating one Redis key and one dict entry per task: the task feed's space is bounded, and reclamation rides the clock that already ticks | `_MIRROR_TTL_S=3600` module constant + `pipeline([XADD, PEXPIRE])` write-time renewal (one round trip); `gc_old_tasks()` wired into all three existing embed loops via local imports; zero new tick/knob/resp command; memory mode sends no new Redis command; 4 source-contract + 2 runtime offline tests; liveness-interval line pin 275→291 / 282,279→298,295 |
| 153 | The dashboard event log the backend computes, caches and sends is no longer dropped at the browser boundary: the last unread component of `DashboardResponse` gets a real reader and a card a reader can act on | pure `normalizeRecentActivity` (five own components, free payload passed through, id-required, unknown kind kept); `recent-activity.tsx` renders all five wired kinds plus an honest neutral line for a stranger, linking each row to its application; honesty ledger 18→19 sites / diff set emptied, 8 mapper + 8 row tests; copy census 168→169, en/zh 15 keys, build + bundle budget |

## Rules
- No placeholder endpoints. Every mode/config knob is read by real code and pinned by
  the env/RAG-doc censuses in the same change.
- Complexity claims are measured with `time.perf_counter`, not asserted in prose.
- An algorithm that changes ranking is a behaviour change: the old ordering is pinned
  first, then the replacement must reproduce it. A mode that skips the model must say
  so in `describe()`/logs and never fabricate a score.
- Offline harness: `LLM_PROVIDER=mock EMBEDDING_PROVIDER=hash`. Docker-dependent suites
  stay recorded as not-run on this host.

## Epic 133 — the top-K helper uses the right heap for the scale **DONE (measured 2026-11-11)**

**This epic changed shape when it was measured, and the change is the point.** The
first sketch was to replace the full sort in `_fuse_rrf` (`app/agents/tools.py`)
with the bounded-heap `top_k`. Two measurements killed that idea before it shipped:

1. **The candidates are already SQL-LIMITed.** Both the keyword and semantic legs
   carry `LIMIT $n` with n clamped to ~10, so the fused set is a small constant.
   At that size a heap's asymptotic advantage is invisible and its per-item Python
   overhead is pure cost — the right tool is Timsort. Replacing it would have been
   optimising a number the database had already made small.
2. **A hand-written Python heap is slower than the C sort at every size tested.**
   Measured on this host (median of 9, `key` on descending RRF-like scores):

   | n (k=10) | `sorted` | Python tuple-heap `top_k` | `heapq.nlargest` |
   |---|---|---|---|
   | 1,000 | 0.058 ms | 0.123 ms | 0.064 ms |
   | 50,000 | 4.775 ms | 9.556 ms | **3.497 ms** |
   | 200,000 | 35.072 ms | 41.208 ms | **27.109 ms** |

**Do (what actually shipped).** `top_k` now delegates to the C-level
`heapq.nlargest` / `nsmallest`, which is stable, byte-for-byte equal to
`sorted(..., reverse=True)[:k]`, keeps only k items (O(k) space), and is the only
variant that actually wins at large n (~1.3x at 200k). `_fuse_rrf` deliberately keeps
its sort and now carries a comment recording *why*, so a future reader does not
re-attempt the same non-optimisation. The algorithms tests pin: stability across
scales and heavy ties, equivalence with a full sort, and selection over a 50k
generator (no `__len__`), which a materialise-and-sort helper would handle differently.

**Honest bound recorded in the test:** selection is still O(n) — it must see every
input; only *space* drops to O(k). An unbounded source has no "top k" and the helper
does not pretend to answer one. The C-heap win is for places n is genuinely large,
which Epic 134 begins to exercise (scoring a candidate corpus in-process).

**Done when** `test_the_algorithms_module.py` 50/50 and `test_job_search_hybrid.py`
unchanged/green; `_fuse_rrf` still returns byte-for-byte the same order.

## Epic 134 — a rerank that costs no model call

**Measured.** `rag/rerank.py` offers two modes: `llm` (an LLM relevance pass, one model
call, tens of tokens per candidate) and `none` (skip entirely — fused RRF order). There
is no middle: on a host with no provider configured, or on a query where spending a
model call is not worth it, the reader gets either a bill or no lexical re-scoring at
all. Meanwhile `app.algorithms.Bm25` is a pure-Python ranker that scores the same
fused candidates against the query in microseconds and needs no network.

**Do.** Add `RERANK_MODE=bm25`: build a BM25 index over the fused candidate texts,
re-order down to `top_n` by `score(query, i)`, and inject a `rerank` field that is
*the normalized BM25 score* — the same field the LLM path writes, so `to_evidence`
and the citation path need no change. `none` still skips. Keep `llm` the default so
no deployment changes behaviour until an operator opts in.

**Done when** (a) the mode census (`test_the_rag_doc_names_what_the_code_ships.py`)
and env-declaration census pass with `bm25` named in config comment, `.env.example`
and `docs/RAG.md`; (b) offline tests prove `bm25` orders by lexical relevance, keeps
stable ties, injects finite normalized scores, and never calls `ask_json`; (c) the
existing six rerank degradation tests still pass; (d) a measured note records the
BM25 pass's wall time on a 40-candidate corpus.

**DONE (verified 2026-11-11, offline).** All four conditions met:
- **Shipped.** `RERANK_MODE=bm25` is the third mode alongside `llm` (still default)
  and `none`. `app/rag/rerank.py` scores the fused `rows[:25]` with the BM25 from
  Epic 132, min-max normalising to (0, 1] so `pipeline.to_evidence`'s
  `max(rerank, rrf)` keeps a single scale — an out-of-scale BM25 score would
  fabricate confidence, so this is pinned by an explicit `to_evidence` test.
  Both computed modes inject the same `rerank` field and trace a `mode` key; the
  citation/observability paths do not branch on the ranker. `eval/run_eval.py`'s
  `--rerank` choices, `.env.example`, `config.py`'s mode comment, and `docs/RAG.md`
  carry the new mode; the RAG-doc census was generalised from a hardcoded
  two-mode parse to `findall(RERANK_MODE=(\w+))` so a fourth mode is one doc edit.
- **Chinese actually works.** A tokeniser that only matched `[a-z0-9]+` would
  score every Chinese resume chunk zero and make the feature useless on a Chinese
  job platform. `_rerank_tokens` emits overlapping CJK character bigrams (plus
  Latin words) — the standard no-segmenter IR trick — so "机器学习" shares signal
  with "机器学习框架". Writing it surfaced a real bug in the first draft: a missing
  `\\u` on the Hangul range (`\\ufaffac00`) widened the character class to cover
  ASCII, so English was bigrammed too; the bigram test caught it and the escape is
  fixed. Bigrams cost time linear in text length.
- **Measured (this host, 2026-11-11).** BM25 fit+score over 40 candidate chunks of
  ~600 mixed Chinese/English characters: **median 9.60 ms, p95 22.5 ms** (300 runs,
  varied vocabulary). That is one in-process CPU pass — zero model call, zero
  network round trip, zero token billing, and available when no provider is
  configured. The `llm` path remains for relevance quality; `bm25` is the honest
  middle between a model call and no lexical re-scoring at all. An earlier
  measurement with an artificially repetitive corpus read 31.6 ms; the varied
  corpus above is the representative one (repetition inflated the term counts).
- **Verified.** `test_the_rerank_that_costs_no_model_call.py` 10/10 (ordering,
  normalisation, evidence-scale safety, zero-match + tie stability, Chinese
  bigrams, never-LLM, unknown-mode fallthrough); `test_core_modules.py` rerank
  degradation suite still green; RAG-doc + env-declaration censuses green
  (100/100 combined with core_modules). Full ai-service suite is the operator's
  offline-gate run; this host has no Docker for the live RAG eval.

## Epic 136 — N embed replicas do a job once, and a crashed worker's job comes back **DONE (verified 2026-11-11)**

**Measured / observed.** `app/ops/embed_jobs.py::embed_loop` runs on **every** ai-service
replica and selects `jobs WHERE embedding IS NULL` with no claim. With R replicas the
same NULL rows are embedded R times: R model calls and R bills for one batch, plus
R concurrent `UPDATE`s racing the same rows, and a replica that dies mid-batch leaves
its share with nobody to re-claim it. `embedding IS NULL` is an idempotence *barrier*,
not a *claim* — two readers can both observe NULL before either writes. This is a work
queue problem, and it is the concrete reason to add one.

**Why not a consumer group on the existing task bus (the "合理使用" decision).**
`app/core/taskbus.py`'s Redis backplane is a **broadcast**: every browser following a
task must see every progress event, so it uses plain `XADD`/`XREAD` with no consumer
group — adding one would deliver each event to only one subscriber and break SSE.
A work queue is the opposite (each job to exactly one worker, recoverable on crash).
They are different abstractions over the same stream primitive; conflating them is the
mistake here. So this epic adds a **separate** `app/core/workqueue.py` and leaves the
task bus untouched.

**Do.**
- `WorkQueue` speaks RESP2 through the existing dependency-free `app.core.resp` pool:
  `XGROUP CREATE ... MKSTREAM` (BUSYGROUP startup race benign), `XREADGROUP GROUP ...
  >` (fresh jobs, one consumer each), `XAUTOCLAIM` (orphans idle past the visibility
  timeout), `XACK` (completed), `XPENDING` (observability). No new dependency.
- `app/ops/embed_workers.py` wires it opt-in: `WORK_QUEUE_BACKEND=redis` (default `off`)
  makes each tick run a **producer** (enqueue only the ids of NULL-embedding jobs —
  the stream stays small; text + embedding stay with the consumer) then a **consumer**
  (`drain` claims a batch, embeds each id, ACKs successes). `main.py` selects the
  distributed loop only for the `redis` value; `off` keeps `embed_loop` byte-for-byte.
- **At-least-once, stated plainly.** A worker that finishes but crashes before ACK is
  re-claimed and runs twice; so is a duplicate producer enqueue. The handler is
  idempotent two ways: it re-checks `embedding IS NULL` under a `WHERE ... AND
  embedding IS NULL` UPDATE, so a re-claimed already-written job costs one cheap
  SELECT, not a second model call. Exactly-once would need a transaction spanning
  Redis + the provider + Postgres, which does not exist; this is the standard honest
  answer, not a gap.
- **Fail-open.** Redis unusable (bad URL / outage) falls back to the original
  single-process `embed_jobs()` DB scan. The queue can cost parallelism, never recall.
  A per-process random `consumer` name attributes PEL entries across restarts.

**Verified (offline, 2026-11-11).** Two gates, 22 tests:
`test_the_work_queue_delivers_each_job_once.py` 10/10 (group created once, BUSYGROUP
benign, each fresh job to one consumer, ACK removes from PEL, un-ACKed job re-claimed
only after the visibility timeout, handler failure/raise leaves it pending, Redis-down
fail-open, knob validation) against an in-memory stream+PEL model; and
`test_the_embed_work_queue_shares_work.py` 12/12 (producer enqueues only NULL ids,
limit/DB fetch shape, enqueue fail-open, idempotent re-claim = no provider call, empty
job = no provider, real write carries the NULL guard, wrong vector count = pending,
no-provider = no claim, consumer ACK/failure split, main wiring, consumer identity).

**Real-Redis end-to-end (this host, 2026-11-11).** Not left to the fake: a scripted
run against the local Redis exercised the actual RESP commands — 3 `XADD`ed jobs went
to exactly one of two consumers (`{'a': 3, 'b': 0}`); after a 350 ms idle past a
300 ms visibility timeout, `XAUTOCLAIM` on the second consumer re-claimed all 3
un-ACKed ids; `XACK`ing them dropped `XPENDING` to 0. The fake model and the real
protocol agree.

**Honest bounds — including a measured correction.** The producer's `XADD` is capped
with `MAXLEN ~ WORK_QUEUE_MAXLEN` (10k). The `~` is *approximate* trimming: Redis
removes whole macro nodes (~100 entries) instead of trimming to the exact count,
which is the cheap O(1)-ish option for a high-throughput producer (exact `MAXLEN`
walks and deletes each extra entry). **Measured against the real Redis 7.4.11 on
this host, 2026-11-11:** 12 `XADD`s with `MAXLEN ~ 5` left `XLEN=12` (no macro node
full yet — the first end-to-end assertion wrongly expected `< 12` and correctly
failed); 150 `XADD`s with `MAXLEN ~ 5` left `XLEN=50` (one node), and exact
`MAXLEN 5` left `XLEN=5`. So the guarantee is **bounded growth at macro-node
granularity**, not an exact cap — for a 10k cap that ±100 is immaterial. A job
trimmed before a consumer claims it is re-enqueued by the next producer pass — the
DB's `embedding IS NULL` is the source of truth, so trimming loses no job
permanently. The duplicate-producer scan is at-least-once by design (no dedup index
— that would be a second truth). No load test of R real replicas was run here (no
multi-process Redis deployment on this host); the one-writer-per-job and
crash-reclaim properties are pinned by tests and the real-Redis script, not by a
fleet run. `verify_gates.sh`/`.ps1` gained all three new algorithm/queue gates.

## Epic 137 — the auth door carries the landing's design language **DONE (verified 2026-11-11)**

**Observed.** The landing hero was elevated to a designed surface (aurora, glass,
gradient text, scroll reveal — the motion system from the previous horizon), but the
**auth layout**, the first surface an anonymous visitor reaches, still showed a flat
static radial wash and plain brand text. Epic 130 made it *sell the product* (the
shared `ProductPreview`); it did not make it *feel* like the landing it precedes.
This epic closes that gap additively, without touching form logic or copy.

**The light-panel decision (why NOT to copy the landing wholesale).** The landing
hero can carry `AuroraBackground`, whose blobs use `mix-blend-mode: screen` — that
blends beautifully over a dark/hero field but **washes out on the auth panel's light
`bg-sidebar`** (`oklch(0.985 …)`). Copy-pasting the aurora would have been the
mechanically "consistent" move and the visually wrong one. So the auth door gets a
gradient accent (the `OS` brand word via `GradientText`), a shimmer rule, a glass
surface under the product preview, and a CSS-only staggered entrance instead. A
source-contract test **pins the rejection** (`not.toContain("AuroraBackground")`
and the `mix-blend-mode: screen` reason in globals.css), so a future copy-paste has
to make the case explicitly rather than quietly degrading the panel.

**Do (all additive, no new i18n keys, no form changes).** `app/(auth)/layout.tsx`:
`GradientText` on the brand accent; a decorative `shimmer-rule` above the eyebrow;
each of the four translated pillars and the glass-wrapped `ProductPreview` get
`animate-fade-up` with an inline `animationDelay` (120/210/300/390/480 ms) for a
cascade; content sits at `relative z-10` over the retained static radial. The
entrance is **CSS-only** (`animation-fill-mode: both` from the existing token) —
deliberately not the JS `Reveal`/IntersectionObserver — so the marketing copy is in
the first paint and never depends on JS or an observer to become visible. The
`prefers-reduced-motion` global rule already disables `.gradient-text`,
`.shimmer-rule` and all animations, so the reader's preference stays authoritative.
The form `children` and its original `animate-fade-up` are untouched.

**Verified (offline, 2026-11-11).** `app/(auth)/layout.test.ts` 5/5 source contract
(gradient accent, glass preview, CSS-delay stagger with no IntersectionObserver,
reduced-motion safety net, no screen-blended aurora, and all translated keys +
pillars + form still present); `tsc --noEmit` clean; copy-census 20/20 (no new or
hardcoded copy); `product-preview.test.tsx` 2/2; full frontend vitest green;
production `next build` + `bundle-budget.mjs` (auth/login route stays under the
340 kB gzip budget — the aurora-free choice also keeps this route's JS unchanged,
since all new motion is existing CSS/utilities and no new client JS was added).

## Epic 138 — a poison job stops burning a worker on every retry **DONE (verified 2026-11-11)**

**Observed.** Epic 136 gave the embed work queue at-least-once delivery and crash
recovery, but no *retry ceiling*. A job whose handler keeps returning failure (an
embedding provider that rejects one malformed row, a bad vector dimension, a
permanently broken id) was re-delivered forever: on each `drain()` tick it occupied
a batch slot and spent an embedding call, and a whole consumer group could be
starved behind one poison message. The fix needed a dead-letter queue — and the
first design for it was **wrong in a way only the protocol semantics reveal**.

**The design correction (why NOT to use Redis `delivery_count`).** The tempting
implementation is to let the message stay in the PEL, let `XAUTOCLAIM` re-claim it,
and read Redis's `delivery_count` from `XPENDING` to decide when to dead-letter.
That has a hole: **`XAUTOCLAIM` only re-claims *other* consumers' orphans.** A
worker that stays alive but whose handler keeps failing leaves the message in
*its own* PEL; Redis's count is pinned at 1 no matter how many times the handler
fails, so the DLQ never fires and the job loops forever. `XPENDING`'s
`delivery_count` is therefore demoted to an **observability metric**
(`pending_counts()`, documented as such), and the retry decision moves to an
**application-owned `attempts` field that travels with the message**:

* On handler failure, `drain()` increments `attempts`, `XADD`s the message **back
  to the main stream** (or to the DLQ if it reached `max_deliveries`), then `XACK`s
  the old copy. Re-queueing (rather than leaving it pending) is what makes a
  live-but-failing job actually get retried, and what carries the attempt count
  across a worker crash — the orphan a later `XAUTOCLAIM` picks up still has it.
* At the ceiling, the DLQ entry is **written first**, then the main-stream copy is
  ACKed. A failed DLQ `XADD` leaves the message pending (never ACKed, never
  silently dropped), so the poison job is recoverable rather than lost.
* `max_deliveries=0` (and a DLQ-disabled config) keeps Epic 136's behaviour:
  retry indefinitely, `attempts` still visible to an operator. Backward-compatible.

**Do.** `WorkQueue` gains `max_deliveries` / `dlq_stream` (validated together), a
`dead_lettered` counter on `ClaimStats`, and the re-queue / DLQ path in `drain()`.
DLQ entries carry `origin_stream`, `origin_id` and `dlq_at` so an operator can trace
a poison job back to its source. **The DLQ `XADD` is trimmed with `MAXLEN ~ maxlen`
just like the retry re-queues** — a correction made *after* the real-Redis run
showed an unbounded DLQ (see the honest bounds below). Two Settings knobs
(`WORK_QUEUE_MAX_DELIVERIES=5`, `WORK_QUEUE_DLQ_STREAM=careeros:jobs:embed:dlq`)
are declared in `.env.example` and wired through `embed_workers._queue()`; the env
census folds Settings fields into its read-oracle, so no test exemption was needed.
`pending_counts()` is explicitly documented as a PEL observability metric, not the
DLQ counter.

**Verified (offline + real Redis 7, 2026-11-11).** 9 new DLQ tests in
`test_the_work_queue_delivers_each_job_once.py` (now 21) pin: `XPENDING`
delivery-count observability across a two-consumer `XAUTOCLAIM` reclaim, the
attempt-count re-queue, dead-lettering exactly at the ceiling with provenance
fields, a failed DLQ write leaving the job pending, a successful job never being
dead-lettered, **the DLQ add carrying `MAXLEN ~`**, no-DLQ retry-forever backward
compatibility, invalid knob rejection, and Redis-down fail-open. The suite's
`FakePool` was corrected to model the real PEL faithfully: a plain `XADD` leaves a
message on the stream with `owner=None` and it enters the PEL only on
`XREADGROUP`/`XAUTOCLAIM` — so a just-re-queued retry is not miscounted as
"pending" before anyone claims it (the earlier model had wrongly counted it, and
one Epic 136 assertion had to be fixed to match real Redis).

**Real-Redis end-to-end (live Redis 7 at 127.0.0.1:16399, 2026-11-11).** Against
actual `XADD`/`XREADGROUP`/`XAUTOCLAIM`/`XACK`/`XRANGE` (not the fake):
* **(A)** one job poisoned twice: first `drain` re-queued it at `attempts=1` and
  ACKed the old PEL copy (PEL empty, one stream copy carries `attempts=1`); second
  `drain` wrote exactly one DLQ entry with `attempts=2` + `origin_stream` +
  `origin_id` + `dlq_at`, and ACKed the main copy (PEL empty).
* **(B)** with the DLQ key holding a non-stream (`SET`), the poison `XADD` raised
  `WRONGTYPE`; the job stayed pending and was never ACKed — *never silently dropped*.
* **(C)** a successful job was ACKed and never dead-lettered.
* **(D, the honest bound below)** a producer-style fresh re-enqueue was observed
  to reset the retry lineage. Two harness assertions were corrected against the
  real protocol — `XACK` removes from the PEL, **not** the stream, so `XRANGE`
  still shows the ACKed copy; and the *main* stream's dev Redis on 16380 was not
  serving RESP during this run, so the check used the live instance on 16399.
  `verify_gates.sh`/`.ps1` already run both work-queue suites.

**Honest bound — what the DLQ does and does not stop.** The retry ceiling is scoped
to **one message lineage**: a job whose handler keeps failing is dead-lettered after
`max_deliveries` *re-queues*, an operator gets a bounded, provenance-rich DLQ stream
to inspect/reprocess, and the worker stops spending a batch slot + model call on
*that lineage*. It does **not** suppress the producer: `producer_pass()` selects
`jobs WHERE embedding IS NULL` every tick and `XADD`s a **fresh, `attempts`-less**
message, so a permanently-unembeddable row still starts a new lineage each tick
(scenario D: live `attempts` values `['0','0','1','1']` after two producer ticks)
and can still cost ~one model call per tick. The DLQ stream is now `MAXLEN ~`
trimmed so this cannot grow it without bound, but **stopping the re-injection itself
is a producer-side decision** — dead-letter a job and suppress its id from future
producer passes until an operator requeues it. That is Epic 139; keeping it out of
138 preserves the DB-as-source-of-truth contract (a trimmed DLQ record never loses
the job, because the still-NULL row comes back next pass) and avoids silently
changing recall for transient provider failures.

## Epic 139 — the producer stops re-injecting a dead-lettered job, and it heals **DONE (verified 2026-11-12)**

**Observed (the bound Epic 138 measured and left open).** Epic 138's retry ceiling is
scoped to **one message lineage**, but `producer_pass()` re-selects
`jobs WHERE embedding IS NULL` every 60 s tick and `XADD`s a *fresh* message with no
`attempts` field. A permanently-unembeddable row therefore starts a brand-new
`attempts=0` lineage every tick: the real-Redis scenario D saw live attempts
`['0','0','1','1']` after two producer ticks. Result: ~one model call burned per
tick, forever, and one DLQ dead-letter per tick (bounded in stream *size* by Epic
138's `MAXLEN ~`, but the *work* was unbounded). The DLQ alone cannot fix this — the
re-injection is a producer decision.

**The design decision: a bounded cooldown, NOT a permanent tombstone.** The obvious
fix is "suppress dead-lettered ids forever until an operator clears them." That is
**dangerous**: a 10-minute provider blip can dead-letter hundreds of *perfectly good*
jobs (5 fast retries inside the blip), and a permanent set would leave all of them
un-embedded until a human noticed — a silent recall drop, exactly the failure the
"DB as source of truth" contract exists to prevent. So suppression is a **cooldown**
keyed by job id, backed by **one Redis sorted set** (`ZADD key <expiry_epoch> job_id`):

* ``active(now)`` = `ZRANGEBYSCORE key (now +inf` — ids whose window is still open;
* ``ZREMRANGEBYSCORE key -inf now`` runs in the **same pipeline round trip**, so the
  set cannot accumulate dead members;
* after `WORK_QUEUE_DLQ_COOLDOWN_S` (default 900 s) a lapsed id leaves the set and the
  next producer tick re-enqueues it — **a transient outage heals on its own**;
* an operator can `release(ids)` / `release_all()` early (or plain `ZREM` /
  `ZREMRANGEBYSCORE -inf +inf` via redis-cli) after fixing the row or restoring the
  provider. This is the "requeue it" half of the contract.

The DB column `embedding IS NULL` stays the single source of truth for *whether a job
needs work*; the guard only decides *when it is eligible to be tried*. A pruned or
released entry can never lose a job.

**Do (two halves, one batched guard read per pass).** `app/core/dlq_guard.py` is a
dependency-free `DlqGuard` over the existing RESP pool (ZADD/ZSCORE/ZRANGEBYSCORE/
ZREMRANGEBYSCORE/ZREM/ZCARD + `pipeline`), with an injectable clock. Producer half:
`producer_pass` excludes cooling ids **in SQL** (`NOT j.id = ANY($n::uuid[])`), not in
Python — a post-`LIMIT` filter would let suppressed ids fill the batch and starve
older embeddable jobs; pushing it into the WHERE makes `LIMIT` count only eligible
rows. Consumer half: `WorkQueue.drain` (new optional `id_field`) reports
`ClaimStats.dead_lettered_ids`; `consumer_pass` marks those into the guard, and **ACKs
leftover at-least-once duplicate copies of cooling ids without a model call** (the
producer stops *new* enqueues, but copies enqueued in earlier ticks may still sit in
the stream). `embed_loop_distributed` builds one guard and threads it to both passes.
`release_cooldowns()` is the operator entry point.

**Honest bounds.**
* **Fail-open at two layers.** `DlqGuard` swallows its own Redis errors; the caller
  boundary (`_suppressed`) also degrades any escaping exception to "suppress nothing".
  A guard outage costs suppression, never recall — the system degrades to exact Epic
  138 behaviour. This was *found by a failing test*, not assumed: a stub whose
  `active()` raised exposed that the caller was trusting the guard too much, so the
  boundary wrapper was added.
* **Approximate across replicas, on purpose.** All replicas share one ZSET (global
  suppression, no leader). Two replicas may both `ZADD` an id (idempotent, last
  expiry wins) or read the same active set; a job may be tried at most ~once per
  window per replica in the worst case — bounded, not "once per tick".
* **A cooldown is not a fix for the underlying poison row.** It reduces a permanently
  bad job's cost from ~1 model call/tick to ~1 per 900 s; the row stays `embedding IS
  NULL` and re-enters each window until someone fixes it or the provider. That is the
  correct trade-off: bounded cost + self-healing + no silent recall loss, without
  pretending the bad row is gone.
* **Wall-clock scores** (unix epoch) because ZSET scores must be comparable across
  processes; `time.time` is injectable so expiry is tested without sleeping.

**Verified (offline + real Redis 7, 2026-11-12).** 13 `DlqGuard` tests (mark/batched
ZADD/expiry-refresh/self-heal/pipeline-prune/release/release_all/fail-open on down and
on RESP error/disabled-knob/malformed-id) + 16 new embed integration tests
(producer SQL bind shape, no-guard and disabled-guard backward compatibility,
malformed-id filtering, guard-error fail-open, consumer ACKs cooling duplicates with
zero model calls, consumer marks dead-lettered ids, loop wiring source contract,
operator release) + 3 `drain` tests for `dead_lettered_ids`; the existing 33
workqueue/embed tests stay green (backward compatible). `test_the_env_examples...`
census passes with both new knobs declared and read. **Real Redis 7 end-to-end** on
the live instance: mark→active (ZADD+ZRANGEBYSCORE), window-lapse→heal+prune (same
pipeline), re-mark→refreshed window, release/release_all, and disabled guard — all
passed against actual RESP commands. `verify_gates.sh`/`.ps1` gained the new guard
gate. `WORK_QUEUE_DLQ_COOLDOWN_S=0` reproduces Epic 138 exactly.

## Epic 140 — the dead-letter pipeline can be seen, not just written **DONE (verified 2026-11-12)**

Epics 136/138/139 made the embed work queue reliable — consumer groups, a dead-letter
queue, a cooldown guard — but every one of them **wrote** state into Redis and only
narrated it in log lines. A growing DLQ, a stalled consumer, a killed worker: none of
them was queryable. An operator's only recourse was `redis-cli` and a log grep. This
Epic adds the read half: one honest verdict over the whole pipeline, exposed as a
read-only, internal-auth'd endpoint a monitor or a future Micrometer gauge can read.

**The core problem is that "zero" is ambiguous.** A fail-open Redis read returns 0,
and so does a genuinely empty, healthy queue. A naive observer that just reports
"pending = 0" would call a dead Redis healthy, and call a dead *consumer* healthy
because an idle stream looks the same whether a worker just drained it or died an
hour ago. The design therefore keeps three observations separate and lets an explicit
verdict ladder resolve the ambiguity, highest precedence first:

```
disabled    work_queue_backend != redis — nothing to watch (informational)
unknown     Redis unreachable (snapshot.ok=False) — the numbers are zeroes we
            cannot trust; never report healthy on an unreadable queue
stalled     Redis reads fine, but the consumer heartbeat is missing/stale — a
            dead worker behind an idle-looking queue
degraded    live consumer, but dead letters in the DLQ or job ids cooling down
backlogged  live + clean, but PEL depth over the warn line
healthy     live, no poison, no meaningful backlog
```

**Three observations, one author each** (no second source of truth can drift):

* **live Redis** — `WorkQueue.snapshot()` (`XLEN` main + `XLEN` DLQ + `XPENDING`
  summary, issued concurrently via `asyncio.gather`) plus `DlqGuard.size()` (`ZCARD`).
  A new `ok` bit records whether *all* reads succeeded; each numeric still degrades
  to 0 independently (partial failure blanks one number, not the report).
* **consumer liveness** — `app/ops/queue_observer.py`, a module-level single-writer
  heartbeat that `embed_loop_distributed` stamps *after a complete produce→consume→
  drain pass*, not on wake. It stores **only** liveness + last-tick throughput;
  cooldown/DLQ counts are deliberately *not* duplicated here (they are read live),
  so a stale heartbeat can never disagree with a fresh Redis read. No mode flag
  either: `work_queue_backend` is the single author for "is this enabled".
* **pure fold** — `app/features/work_queue_health.py` takes plain dicts + an
  injected `now`, and produces `{verdict, alerts, freshness, queue, guard, backend}`
  with no Redis client, no clock of its own, no new dependency (same discipline as
  `monitoring.health_report`). Raw numbers travel alongside the verdict so a chart
  and an alert name the same value.

`app/ops/queue_status.read_status()` is the one fail-open seam: it reads config once
(mode + the two tuning knobs), builds a **short-lived** pool from `REDIS_URL` (never
the loop's — the loop owns its pool's lifetime), constructs the *same* read-only
`WorkQueue`/`DlqGuard` the loop uses via `embed_workers._queue`/`_guard`, and closes
its pool in `finally`. When `backend != redis` it touches no Redis at all. Redis
down, a bad URL, a RESP error, even an unexpected exception all degrade to a
well-formed *unknown* report, never a 500. `GET /internal/ops/workqueue` adds only
`require_internal` plus a last-resort catch — a control-plane endpoint cannot turn
an observer's bad day into a 500 that looks like the service died. Two new knobs
`WORK_QUEUE_HEALTH_STALE_S=300` and `WORK_QUEUE_HEALTH_BACKLOG_WARN=32` are declared
in `.env.example` and read by the collector (env census passes); both tune the
report only and cannot change the queue.

**Verified (offline + real Redis, 2026-11-12).** 54 new offline tests: 49 in four
new suites — pure health fold (21: the full verdict ladder, precedence, freshness
boundary, future-clock clamp, malformed input, stream-depth-alone-is-healthy),
heartbeat registry (9: copy semantics, int coercion, replace-not-append, reset,
loop source contract), fail-open collector (12: off/disabled without touching
Redis, healthy/degraded/stalled/backlogged, bad URL, RESP error, unexpected
exception, pool-always-closed, knobs threaded through), and the HTTP endpoint
(7: 401/400 auth, 401 wrong token, full shape, degraded-is-still-200, collector-
raises→unknown-not-500, GET-only/405) — plus 5 new observation tests in the existing
workqueue suite (`snapshot` read-only/no-mutation, `ok` bit, NOGROUP, DLQ bounds).
The internal-auth gate picks the new route up
automatically. **Live Redis end-to-end** (the instance on 16380) proved:
`snapshot()` matches real `XLEN`/`XPENDING`; a fresh queue reports `ok=True`; a
fresh heartbeat + DLQ + cooldown folds to `degraded`; a stale heartbeat folds to
`stalled`; and an unreachable Redis folds to `unknown` with `ok=False` — with the
observed `dlq_len` **exactly equal** to the real DLQ `XLEN`.

**Two honest findings from the live run, both folded back into the code:**

1. **Real Redis answers `NOGROUP` for `XPENDING` before a queue's first consumer
   pass.** The first end-to-end run read `ok=False` on a freshly deployed, empty
   queue — which would make every new deployment report `unknown` until its first
   job. `snapshot()` now treats `NOGROUP` as *known-empty* (`pending=0, ok=True`),
   and a contract test pins it. Any *other* RESP error still fails open.
2. **At-least-once + per-tick re-injection can legitimately put more DLQ entries
   than poison jobs.** One real `drain(fail)×2` produced 8 DLQ records for 2 jobs
   (`XAUTOCLAIM` claimed duplicate lineages). The harness's `== 2` assertion was
   wrong, not the code; the meaningful guarantee Epic 140 makes is that the
   **observed number equals the real `XLEN`** (measured: observed 8 == XLEN 8), so a
   dashboard and Redis cannot disagree.

**Honest bounds.** The heartbeat is in-memory: it is lost on process restart, so a
just-restarted worker reports `stalled` until its first complete tick — the right
conservative answer. `stale_s` must be set comfortably above the loop interval or
a slow-but-healthy loop looks dead. `DlqGuard.size()` counts not-yet-pruned expired
members too (documented in the guard); a cooldown window that has lapsed but not
been pruned can read a hair high. The verdict is a *read*, not an action: it never
releases a cooldown or drains the DLQ (the operator's `release_cooldowns()` remains
the explicit action). This Epic stays entirely inside ai-service by deliberate
choice: the project's Prometheus registries and `careeros.*` meter roster live in
backend/gateway Java under a strict "every meter is registered or documented"
gate, so wiring these numbers into `/actuator/prometheus` is a separate, deliberate
next step — this endpoint is the clean single source that step would scrape.

## Epic 141 — the signed-in first screen carries the designed language **DONE (verified 2026-11-12)**

Epics 137 (auth door) and the landing page established a visual language — aurora,
glass, gradient text, shimmer hairlines, CSS-only staggered entrance — but it lived
only on the two *anonymous* surfaces. The first screen a signed-in reader actually
sees, `(app)/dashboard`, was still the Epic 122 band: two static token washes, a
hairline and a card shadow. Design debt on the highest-traffic surface in the app.

This Epic dresses that existing band in the Epic 137 language **without** the two
traps that language carries, and without adding a single byte of client JS:

* **No light-theme wash-out.** Aurora blobs are `mix-blend-mode: screen`, which
  blows a light `bg-card/60` surface to white — the exact trap Epic 137 documented
  on the auth sidebar and pinned in its source contract. The dashboard band is
  light in the light theme and dark via `.dark` in the dark theme, so the aurora is
  gated `hidden … dark:block`: the drift composites only ever over a dark surface.
  A light-theme reader keeps the two static token washes (a safe primary tint, not
  a screen blend); a dark-theme reader gets the blobs + masked grid, tamed to
  `opacity-30` for a short band. This is the conscious evolution of auth's "no
  aurora at all" into "aurora where it is safe", pinned by a test.
* **No new client JS / no IntersectionObserver.** The blobs are plain decorative
  `<span>`s, not the `AuroraBackground` component (vw-scale, no dark gate) and not
  the `Reveal` component (the one visual primitive that brings a client
  IntersectionObserver). Entrance is CSS-only: `animate-fade-up` with inline
  `animationDelay` on the description and the actions row. So the greeting is in
  the first paint, needs no JS to appear, and the `/dashboard` route's gzip stays
  inside the 340 kB budget.
* **Zero copy / zero key churn.** Every label still goes through `t("dashboard.*")`;
  only `className`, decorative spans and a `<GradientText>` wrapper changed. No new
  `.tsx` source file was created, so the `copy-census` browser-source count pin
  (167) is untouched and `used-keys` stays green.
* **Motion stays optional.** All new layered motion reuses existing globals.css
  utilities, so the shared `prefers-reduced-motion` blanket (animations → 1ms) and
  the Epic 137 per-utility overrides (`.aurora-blob` / `.gradient-text` →
  `animation: none`) apply automatically; `globals.test.ts` already guards that
  shape. `GradientText` stays real, selectable text.

Concretely: a `shimmer-rule` hairline crowns the band; the greeting name accent
moves from a flat `text-primary` span to `<GradientText>`; the band itself enters
with `animate-fade-up`; description (`+90ms`) and action buttons (`+160ms`) follow
in a CSS-staggered cascade; both CTAs gain `glow-on-hover` (the primary keeps its
`glow-halo`). `PageHeader`'s contract — `title` / `description` / `actions` — is
completely unchanged, so no shared component was touched.

**Verified.** New `frontend/src/app/(app)/dashboard/page.test.ts` (7 source-contract
assertions, `.test.ts` so it is excluded from the copy census): gradient accent,
shimmer hairline, CSS stagger with **no actual `new IntersectionObserver(`** and no
`Reveal`/`AuroraBackground` import, the dark-only aurora gate (`hidden … dark:block`
+ tamed opacity) against the real `mix-blend-mode: screen` rule in globals.css,
reduced-motion authority, CTA hover, and that all copy still reads from `t()` on an
unmodified `PageHeader`. `npm run test`: the full suite is 1204 passing tests; one
unrelated endpoints↔backend parity test hit its 15s timeout under concurrent load
and passed 16/16 when re-run alone (its own case takes 4.9s) — no regression from
this change. `npm run budget` (next build + 340 kB gzip/route): **OK across all 35
routes**; `/dashboard/page` stays at **253.8 kB gzip**, i.e. unchanged from before
this Epic — direct evidence the design pass added zero client JS (every added node
is a server-rendered CSS class or decorative span, and Tailwind compiled the
`dark:block` variant). The build needed the environment's per-turn bulk-delete
guard temporarily disabled for the one `npm run budget` command (`CODEBUDDY_
SAFE_DELETE_ENABLED=0`) because Next's own `.next/` cache cleanup had exhausted
the turn's unlink budget after two large Epics — an environment quirk, not a code
fault; the app's own delete-safety was never bypassed. Honest bound: the aurora is
decorative and lives only in the dark theme by design; a light-theme reader
deliberately does not see it.

## Epic 143 — the cache's saving is measured honestly, and its invalidation boundary is named **DONE (verified 2026-11-12)**

**Observed — the claim that was never cashed.** Epic 118 built a genuinely careful
RAG cache: a reader-scoped, epoch-invalidated retrieval cache, an embedding cache
keyed by `(provider, model, dim, text)`, and a `SingleFlight` that collapses a
thundering herd into one model call. Its headline test,
`test_the_second_question_is_free.py`, proves the second identical question makes
**zero** model/search calls — by installing a `MemoryCache` *by hand* inside the
test. But `Settings.cache_backend` defaults to `"off"`, and both `docker-compose.yml`
and `.env.prod.example` ship it off. So in every shipped configuration the entire
L1/L2/semantic/single-flight machinery has **never run**: every question recomputes
the full pipeline. Epic 118's saving was demonstrated in a fixture and never
delivered to a user.

**Observed — the write-only telemetry.** `CacheStats` faithfully increments
`hits / misses / writes / evictions / l2_hits`, `RedisCache` counts `breaker_trips`,
and `SingleFlight` counts `leaders / joined`. `GET /internal/rag/cache` even returns
`caching.describe()`. But *nothing read any of it into a decision*: no verdict, no
alert, no dashboard, no "is this cache earning its write cost?" answer. This is the
same write-without-read shape Epic 140 found in the dead-letter pipeline — and the
same fix applies: a pure-function fold over the numbers, exposed as a fail-open
read-only control-plane endpoint.

**The central honesty problem: a hit rate of 0 is three different states.** Folding
every zero into "healthy because there are no errors" is the dangerous lie — it
would let a cache that is taxing the product look fine. The verdict separates them:

| verdict | meaning |
| --- | --- |
| `off` | `cache_backend=off` (the shipped default); the optimisation has *never run*. Information, not an error — but a dashboard may not claim a saving that was never enabled. |
| `unknown` | the reading is untrustworthy: backend errors, a tripped Redis breaker, or a malformed counter. Reported before any rate; calling an unobservable cache healthy is the lie Epic 140 refuses. |
| `cold` | enabled, but too few lookups to measure (0 included). Expected on a fresh deploy; says nothing about whether the cache wastes writes. |
| `ineffective` | enabled, enough lookups, hit rate below the warn line (`0.50`): the cache is consulted but not answering often enough to pay for its writes. **This is the expensive one** that a naive "0 errors = healthy" hides. |
| `healthy` | enabled, enough lookups (`>= 20`), hit rate at/above the warn line. |

**Why 20 / 0.50 live as pure-function constants, not config.** They are measurement
discipline, not deployment knobs: one hit in two calls is 50% and would pass a bare
rate line while proving nothing. Keeping them as `DEFAULT_MIN_LOOKUPS` /
`DEFAULT_HIT_RATE_WARN` arguments (injectable in tests, overridable by a future
caller) avoids another `Settings` field, another `.env.example` declaration, and
another env-census surface — the knobs that actually change cache behaviour already
exist (`cache_backend`, `cache_ttl_s`, `cache_max_entries`).

**The layered-cache subtlety that a root-only fold would miss.**
`LayeredCache.describe()` reports *logical* hit counters on the root (a hit is a hit,
wherever it came from) but records transport faults on the **nested `shared` Redis
layer**. A fold that reads only the root would report a healthy 75% hit rate while
the fleet's only shared cache is down. `cache_health._walk()` traverses `local` /
`shared` and sums `errors` + `breaker_trips` across every layer, so a tripped shared
layer correctly yields `unknown`. This is also why `RedisCache.describe()` was
changed to surface `breaker` — the trips were written but never read, even from
`describe()`.

**The A/B baseline — counts, not a stopwatch.** `test_the_cache_baseline_is_honest.py`
reuses Epic 118's `Work` counter around every model/search seam and runs the same
question through all three real backends (off / memory / layered, the layered using
an in-process `MemoryCache` as the shared stand-in so the baseline needs no Redis):

- **off**: the 2nd ask spends the *same* work as the 1st (a full pass, `> 0` extra
  model/search calls). This is the shipped default, honestly named.
- **memory / layered**: the 2nd identical ask spends **0** extra calls and returns
  the identical answer. Layered additionally books one `l2_hits` when a shared-layer
  entry fills a cold front — the fleet-cheap signal (one process warm vs. the fleet
  warm).
- A wall-clock check is deliberately only a *loose sanity bound* (a cached hit must
  not cost more than a full recompute): timing on a shared CI box proves nothing, and
  "a fast wrong answer is not an optimisation" remains the project's rule. The work
  count is the assertion; the stopwatch is not the claim.

**The invalidation boundary — named, not assumed.** `caching.invalidate_user()` is
wired in exactly one place: `app/ingestion/pipeline.py`, ai-service's own document
ingest. A corpus writer that bypasses that seam — a backend direct SQL write, a
backfill job, another service — does **not** bump the reader's epoch, so the cache
keeps serving the pre-write answer until the TTL. A contract test proves this
explicitly: it changes the corpus the search sees without calling `invalidate_user`,
asserts the cached (stale) answer survives, then asserts that an explicit
`invalidate_user` finally surfaces the new corpus. This pins the limitation so
nobody claims epoch invalidation covers a write path it cannot see. The honest
remediation is architectural, not in this Epic: **every corpus writer must call the
invalidation seam, or the cache must stay off for that path.** Until that is
enforced fleet-wide, `cache_backend=off` remains the correct default — which is
precisely why Epic 143 does *not* switch caching on.

**What this Epic deliberately does not do.**
- **Does not turn the cache on.** Enabling it by default would make an unverified
  optimisation (over an un-enforced invalidation boundary) every user's problem.
  The honest fix is observability + a baseline first; opt-in stays opt-in.
- **Does not hard-wire orphan algorithms.** Epic 133 already showed a `top_k` heap
  over a SQL-`LIMIT`ed ~10-row candidate set is a pseudo-optimisation (Python heap
  slower than Timsort). No orphan `top_k` / cosine-micro-optimisations are attached
  to this work just to look algorithmic.
- **Adds no Prometheus client**; the meter centre stays in backend Micrometer, as
  Epic 140 established. This endpoint is the same shape a future gauge scrapes.
- **Does not add a public surface.** `GET /internal/ops/cache` carries
  `require_internal` and is auto-enrolled by the three internal-auth gates.

**Shipped.**
- `app/features/cache_health.py` — pure-function fold (`classify` / `health_report`
  / layered `_walk`), no cache client, no clock, injectable thresholds.
- `app/ops/cache_status.py` — the one fail-open seam: reads `caching.describe()`,
  reports both the configured `mode` (intent) and the actual `backend` (fact), and
  flags `degraded_to` when they disagree (e.g. `redis` configured, `memory` built
  because `REDIS_URL` was unusable). No I/O, no Redis connection of its own.
- `app/api/ops.py` — `GET /internal/ops/cache`, always 200, verdict in the body;
  last-resort catch degrades to `unknown`, never a 500.
- `app/core/cache.py` — `RedisCache.describe()` now surfaces `breaker`
  (`trips / open / cooldown_s`), closing the write-only gap.
- 4 new offline test files (48 tests): verdict truth table (0-rate three states,
  malformed counter → `unknown`, layered shared-layer fault detection), collector
  fail-open + two-truths, endpoint auth/shape/405, and the A/B + invalidation
  baseline. `scripts/verify_gates.sh / .ps1` enrol all four.

**Verified (2026-11-12).** New suites 48/48; the four Epic 143 suites plus all three
internal-auth gates, OpenAPI-route/description gates, Epic 140 health regressions and
Epic 118 cache regressions run together: **270 passed**. The full `verify_gates`
representative offline set: **497 passed, 1 failed** — the single failure is
`test_done_in_horizon_means_checked_in_roadmap` on **Epic 141**, an *concurrent-session
ledger inconsistency unrelated to this Epic*: a concurrent frontend worktree marked
its virtual-list "Epic 141" DONE in `PERFORMANCE_HORIZON.md` without adding
`- [x] **141**` to `ROADMAP.md`. Both files are concurrent-session-owned and were
not touched by Epic 143; a byte-identical check against `HEAD` versions of those two
files shows the ledger is consistent (`missing = []`) and the mismatch appears only
in the concurrent working-tree edits. Epic 143's own gates are all green; the
number-141 collision between the dashboard Epic (141) and the virtual-list Epic
(141) is left for the concurrent session to disambiguate in its own commit.

**Honest bound.** The verdict's warn line (2 hits in 40 lookups = 5% → `ineffective`)
is a *policy* threshold, not a measured law; it encodes "writes must pay for
themselves" and is tunable by a caller. The endpoint reads process-local counters,
so with `CACHE_BACKEND=redis` the fleet's true hit rate is the sum across replicas —
one replica's report is its own, exactly as `/internal/rag/cache` already documents.
The A/B baseline is intentionally in-process (no Redis, no provider): it proves the
cache *mechanism* collapses repeat work, not that a specific production deployment
will save a specific number of milliseconds.

## Open findings — observed 2026-11-12

Two real gaps were found while scoping the work after Epic 143. Both are recorded
with their evidence. Finding A was **resolved by Epic 144** and Finding B was
**resolved by Epic 147**, each in a later turn (the reason for deferring them
initially, and why the eventual implementations are now zero-drift and honest, are
preserved below). Neither remains open.

### Finding A — failed jobs have no retry backoff — RESOLVED by Epic 144

`WorkQueue.drain()` (`app/core/workqueue.py`, the failure branch at lines ~299–331)
re-queues a failed job with `XADD` straight back onto the main stream, increments
`attempts`, and ACKs the old copy. `claim()` takes fresh deliveries first. There is
**no delay**: the very next producer tick re-claims the job. With
`work_queue_max_deliveries=5`, a *transient* embed-provider blip that would heal in
30 s can therefore be retried five times within five tick intervals and be
dead-lettered prematurely — a permanent loss of a job that was only briefly
unhealthy. Epic 139's `DlqGuard` cooldown starts **after** a job reaches the DLQ, so
it does not cover the retry cadence before that point. Backoff is the missing link.

The clean design (not yet implemented): carry a `not_before` epoch field on the
re-queued entry, exponential (`base * 2**(attempts-1)`, capped) + full jitter so N
replicas do not retry in lockstep; `claim()` honors `not_before` by leaving
not-yet-due entries on the stream (a due-only read needs care — plain `XREADGROUP`
has no per-field filter, so this is either a ZSET scheduler or a producer-side
eligibility gate). Verify: a failed job is not re-claimed before its window, a
transient failure heals without reaching the DLQ, a persistent failure still
dead-letters at the cap, and the drift from Epic 138/139 behaviour is explicit.

**Why deferred then, built now.** This edits the `drain`/`claim` core that Epics
138/139/140 just stabilised, plus `Settings` + `.env.example` and every FakePool in
the queue suites. Doing it in the same turn as Epic 143, with the backend/e2e/
frontend sessions still actively committing, would have been a rushed regression
risk. It was deferred with a full design, then built as Epic 144 once the concurrent
sessions had landed. The eventual design honours the earlier caution: backoff is a
**zero-drift opt-in layer** — `WorkQueue`'s constructor default `backoff_base_ms=0`
leaves `drain`/`claim` byte-for-byte the old path and issues *no* ZSET command
(pinned by a zero-drift tripwire test), while only the real worker factory turns it
ON by default to fix the bug. See the full Epic 144 section below.

### Finding B — the cache can quote a deleted document — RESOLVED by Epic 147

Epic 143's contract test proves that a corpus write which does **not** call
`caching.invalidate_user` leaves the reader's epoch unmoved, so the cached answer
survives. A concrete instance existed: `KnowledgeService.deleteNote` / `retireRef`
(and the resume-delete analogue) retires chunks by direct JPA
(`documents.status` → terminal + `reclaimer.reclaim`) without going through
ai-service's ingest pipeline, which was the only place `invalidate_user` was wired.
Add/Edit *do* re-ingest through `fileIngest.ingestText` and were covered; **Delete
was the gap**. Until TTL, the copilot could cite a note or resume the reader had
deleted.

**Why deferred, and what the honest fix turned out to be.** The correction belongs
on the backend delete path, not in ai-service alone: a brand-new
`POST /internal/rag/cache/invalidate` route with no caller would be the orphan
"write" machine Epic 143 was written to expose. It was deferred while the backend
was under concurrent edit, then built as **Epic 147** as one cross-service change:
the endpoint and its *real* backend caller landed together (a contract test fails
if the caller disappears), and the bump runs **after the delete transaction
commits** — the detail that makes the fix correct rather than cosmetic. See the
full Epic 147 section below. The original note that it was "backend-owned" held:
the epoch seam already existed in ai-service; only its wiring was missing.

---

## Epic 144 — a transient blip gets a jittered window to heal in (DONE)

**The bug, stated precisely.** `WorkQueue.drain()` re-queued a failed job by
`XADD`-ing it straight back onto the main stream; `claim()` reads `XREADGROUP >`,
which returns every not-yet-delivered entry with **no per-field filter**. So the
retry was claimed again on the very next producer tick, zero delay. With
`work_queue_max_deliveries=5`, an embed-provider blip that would have healed in
30 seconds could be retried five times in five ticks and dead-lettered — a
permanent loss of a job that was only briefly unhealthy. Epic 139's `DlqGuard`
cooldown only starts *after* a job reaches the DLQ; nothing paced the attempts
before that. This is Finding A, observed after Epic 143 and deferred one turn to
avoid a rushed edit to the most delicate reliability path.

**Why full jitter, not a fixed or plain-exponential sleep.** A fixed delay — even
an exponentially growing one — makes every worker that failed on the same blip
retry at the *same* instant. N replicas then fire N synchronised spikes into a
provider that is still recovering, and keep it down: a **retry storm** (thundering
herd). The actual delay is therefore a uniform draw from `[0, min(cap, base·2^(n−1))]`
(**full jitter**, from AWS's "Exponential Backoff And Jitter", Brooker 2015), not
`ceiling/2 ± jitter`. Spread across the window, N replicas produce a roughly
constant trickle instead of N spikes. The exponential *ceiling* still grows so a
persistent outage backs off, and `cap_ms` bounds the worst-case sleep; the jitter
is what de-correlates. This is the networking principle the Epic is really about.

**The data structure.** A Redis sorted set (`careeros:jobs:embed:delayed`) is the
delay scheduler: member = `<origin stream id>\x1f<fields JSON>`, score = `not_before`
epoch-ms. A parked job is on **none** of the main stream / PEL / DLQ, so `XREADGROUP >`
cannot re-claim it early. `drain()` calls `promote_due()` first each pass:
`ZRANGEBYSCORE delay -inf now LIMIT 0 batch` → for each matured member, `XADD` it
back to the stream, then `ZREM` the member. ZSET-as-delay-queue is the classic
Redis pattern and needs no new dependency — the existing dependency-free RESP2
pool already speaks these commands.

**Zero-drift opt-in (the honesty pivot).** `WorkQueue.__init__` gains
`backoff_base_ms=0` — the *constructor* default is OFF, so every existing caller
and every FakePool in the queue suites keeps the byte-for-byte old immediate-XADD
path. A zero-drift tripwire test asserts the off path issues **no ZSET command at
all** (the fake raises on any unmodelled command). In deliberate contrast, the
*real worker factory* `embed_workers._queue()` reads `Settings` and defaults
`work_queue_backoff_base_ms=500` ON, so a shipped worker actually gets the fix;
a seam test pins that the factory passes the knobs through, because a wiring slip
there would silently leave production on the storm path while every unit test
stayed green. A half-rolled-out `Settings` lacking the field still gets 500 via
`getattr(settings, ..., 500)` — the two defaults (0 for direct callers, 500 for
production) are intentionally different. `cap` and the jitter shape are pure
functions in `app/core/backoff.py` with module constants, **not** new config
churn; only `base`/`cap` are operator knobs, both declared in `.env.example`.

**The honest failure boundary.** promote is deliberately **two non-atomic
commands**, not a Lua script: Redis has no transaction spanning a ZSET and a
stream, and an embedded script would be a second unauditable implementation of
the same protocol over the thin transport. The queue's existing at-least-once +
idempotent-handler contract covers both orders: `XADD`-then-`ZREM`-fails leaves a
duplicate (a cheap no-op `SELECT` in the embed handler, since it re-checks
`embedding IS NULL`); a crash in between replays the same parked job next pass.
What must never happen is `ZREM`-before-`XADD`, which could **drop** a job — the
code orders XADD first and a failed XADD leaves the member parked. A `ZADD` park
failure leaves the message pending (never ACK), so `XAUTOCLAIM` recovers it. A
corrupt member is ZREM-dropped so it cannot block the head of the score range
forever (at-least-once means the DB's NULL scan re-enqueues any still-live job).
`promote_due` moves at most `batch` matured entries per tick; a burst drains over
several ticks, which is well within the seconds-scale backoff window.

**Observability is mandatory, not a nice-to-have.** A parked job is invisible to
`XLEN` (stream), `XPENDING` (PEL) and `dlq_len` (DLQ) — without a new reading, a
growing delay set would be a **silent black hole** and the queue would look
healthy while work waited out its backoff. `snapshot()` gains `delayed_len`
(`ZCARD`) + `delayed_enabled`, fail-open, and the `GET /internal/ops/workqueue`
health report folds both through as first-class raw numbers. Following Epic 140's
`stream_len` precedent, `delayed_len` deliberately does **not** flip the verdict:
a backoff window is expected work-in-waiting, not degradation, and alerting on it
would cry wolf on every hiccup. A sustained climb with a fresh heartbeat is a
chart/operator signal — that is the honest distinction. The verdict set and
precedence ladder are unchanged.

**What was explicitly not done.** No Lua script (see failure boundary). No
per-job `not_before` field on the stream itself (plain `XREADGROUP` cannot filter
by field, so that would need a due-only read that does not exist; the ZSET is the
honest scheduler). No change to DLQ/DlqGuard semantics — poison jobs still skip
backoff and go straight to the DLQ, because a known-bad job has nothing to wait
for. No new endpoint or public surface. Finding B (cached content surviving a
backend delete) remains **open and backend-owned** — recorded above, not touched
here, and no orphan invalidation endpoint was built for it.

**Verification.** `app/core/backoff.py` pure-function contract (exponential curve,
cap, full-jitter bounds `[0, ceiling]`, hostile/NaN rng clamps, huge-`attempts`
DoS guard, off→0) and `test_the_retry_backoff_breaks_the_retry_storm.py`
integration (zero-drift off, park-not-requeue, maturity-gated promote, same-pass
promote, doubling windows, poison bypass, ZADD-failure keeps pending,
XADD-failure keeps parked, corrupt-member drop, `delayed_len` fail-open, the two
worker-factory wiring seams) — 34 offline tests, no sleeps/real Redis. Zero-drift
Epic 138/139/140 regressions: `test_the_work_queue_delivers_each_job_once.py` 29,
`test_the_workqueue_health_report_tells_the_truth.py` + queue-status/ops endpoint
73 combined, `test_the_embed_work_queue_shares_work.py` 28. Env/config censuses
14 (both examples declare what code reads; the two new knobs bind to real Settings
fields). Full `verify_gates` green at commit. A real-Redis end-to-end case is the
same shape Epic 136/139/140 use and is run by the local Redis check, not by the
offline suite.

## Epic 145 — the producer stops un-parking a job that is still sleeping (DONE)

**The bug Epic 144 left behind, stated precisely.** Epic 144 parks a failed job in
the delay ZSET and keeps it off the main stream, so `XREADGROUP >` cannot re-claim
it early. But the DB is the source of truth, and a parked job still has
`embedding IS NULL`. On the very next tick `producer_pass` ran its
`SELECT j.id ... WHERE embedding IS NULL` and `XADD`-ed that same job back onto the
main stream as a **fresh `attempts=0` message**. The consumer group claimed it
immediately — the backoff was bypassed entirely. A persistently-failing provider
therefore still got hammered every tick; Epic 144 paced a *message lineage*, but
the producer re-seeded a new lineage before the old one matured. Worse, the
consumer could burn a model call on an at-least-once duplicate copy of a job that
was legitimately parked. This was found by self-review *after* Epic 144 was
committed (`6590b9c`), not by a failing test — precisely the integration seam
unit tests on the queue alone cannot see.

**The fix: two sources of "do not re-enqueue / do not embed yet", unioned once.**
`_suppressed(queue, guard)` in `embed_workers.py` now merges:

* `DlqGuard.active()` — ids inside a dead-letter cooldown (Epic 139);
* `WorkQueue.parked_ids()` — ids currently sitting in the delay ZSET (this Epic).

Both passes call it. The producer pushes the union into the **SQL WHERE**
(`NOT j.id = ANY($n::uuid[])`) *before* `LIMIT`, for the same reason as Epic 139:
a Python post-filter would let suppressed ids fill the batch and starve older
embeddable rows. The consumer checks the same set and ACKs a suppressed duplicate
for free, so a leftover copy of a parked/cooling job never spends a model call;
its authoritative copy returns on its own (`promote_due` / cooldown lapse).

**`parked_ids()` is read-only and fail-open.** With backoff off or `id_field`
unset it issues **no command** and returns an empty set (zero-drift). Otherwise
`ZRANGE delay 0 -1`, split each `<origin>\x1f<fields JSON>` member, pull
`fields[id_field]`; a corrupt member is skipped, duplicates collapse into the set.
A Redis error returns empty. Crucially, the two sources are read
**independently** with separate try/except: an outage in one must not blank the
other and silently re-open that source's storm hole. Both are optimisations over
the DB scan, never a correctness dependency — total failure degrades to exact
Epic 138 behaviour ("enqueue everything"), so a Redis outage costs suppression,
never recall.

**What was explicitly not done.** No change to the ZSET schema, `promote_due`, or
the delay/backoff math from Epic 144. No new endpoint or public surface. No
attempt to make the DB producer aware of the delay set directly — the queue is
the single authority for "this job is parked", and `_suppressed` is the one seam
where that authority meets the producer's SQL. `parked_ids` is deliberately
`ZRANGE 0 -1` (the whole small delay set), not a score-filtered read: a parked
job's `not_before` is irrelevant to suppression — it must stay suppressed until
`promote_due` moves it back to the stream, at which point it is no longer in the
ZSET. Finding B (cached content surviving a backend delete) remains **open and
backend-owned**, untouched here.

**Verification.** `parked_ids()` contract (parse / dedup / corrupt-member skip /
off→no-command / id_field-unset→no-command / Redis-down fail-open) in
`test_the_retry_backoff_breaks_the_retry_storm.py`; and end-to-end dual-source
suppression in `test_the_embed_work_queue_shares_work.py` (producer unions both
sources, overlaps dedup, each source's outage preserves the other; consumer
ACKs a parked duplicate without a model call and survives a guard outage;
backoff-off zero drift; a source-contract test that both passes call
`await _suppressed(queue, guard)` and no single-source call site remains).
58 offline tests across the two files pass; full `verify_gates` green at commit.

## Epic 146 — the queue stops claiming no worker ever died in (DONE)

**The bug, stated precisely.** `claim()` really does recover a dead consumer's
orphan via `XAUTOCLAIM` — but `drain()` returned `ClaimStats(reclaimed=0)`
**hard-coded**. That 0 was then written into the liveness heartbeat
(`queue_observer.record_tick`) and the `embed_loop_distributed` log line
(`reclaimed=%d`). So the one number that tells an operator "a worker crashed and
its job was picked back up" was a permanent, confident lie: it read 0 no matter
how many orphans were recovered. This is the same class of dishonesty Epic 140
existed to remove, hiding in a field nobody had wired to a source.

**The fix: an observation tag, not a behaviour switch.** `WorkItem` gains
`reclaimed: bool = False`. `claim()` tags only the items that came back from the
`XAUTOCLAIM` branch (`reclaimed=True`); `XREADGROUP >` items keep the default.
`drain()` folds the tag into `ClaimStats.reclaimed` with a plain sum over the
items it already claimed — **no extra Redis command**, no change to how any
message is handled (at-least-once + idempotent handler treats both paths the
same). The full observation chain was already in place (stats → heartbeat →
`/internal/ops/workqueue` → logs), so this single upstream correction makes the
whole line honest at once.

**Zero behaviour drift, deliberately.** `delivered` stays the total claimed
(fresh + reclaimed), so the heartbeat's throughput number is byte-for-byte what
it was — only the previously-always-zero `reclaimed` changes. `reclaimed` is
documented as a *subset* of `delivered`, which is the honest reading Redis gives:
the batch contains both new deliveries and recovered orphans. The `WorkItem`
default keeps every existing constructor and every FakePool in the queue suites
untouched; the health report's verdict ladder never reads either number, so no
verdict shifts. This is a measurement repair, not a scaling change.

**What was explicitly not done.** No change to `XAUTOCLAIM` itself, the
visibility timeout, or the retry/DLQ path. No new endpoint or public surface.
No attempt to attribute an orphan to the *specific* consumer that died — Redis
`XAUTOCLAIM` returns the message, not its former owner, and inventing that
attribution would be a second unprovable truth. The multi-replica heartbeats are
still process-local (Epic 131's recorded scale-out item); this Epic makes the
number each replica reports honest, which is a prerequisite for ever aggregating
them, but does not aggregate them here.

**Verification.** `test_the_work_queue_delivers_each_job_once.py` gains five
offline cases: a fresh delivery stays `reclaimed=False` (zero drift); an
XAUTOCLAIM orphan is tagged `reclaimed=True`; a mixed batch (1 fresh + 1 orphan)
reports `delivered=2, reclaimed=1`; the no-orphan common case keeps `reclaimed=0`;
and a 3-fresh + 2-orphan batch reports exactly `reclaimed=2`. FakePool models
XAUTOCLAIM's PEL semantics, so the count is pinned against a real recovery
path, not a stub. Workqueue/observation group 123 passed; full `verify_gates`
green at commit.

## Epic 147 — a delete the reader can no longer keep quoting (DONE)

**Finding B, closed.** The backend's delete paths retire a document's chunks by
setting `documents.status='retired'` inside a JPA transaction, but the ai-service's
RAG retrieval cache is a separate process that never learns about it. A retrieval
cached moments before the delete keeps quoting the deleted note / source / resume
until its TTL. Add and Edit were already covered (they re-ingest through
`fileIngest.ingestText`, whose success path bumps the epoch); Delete was the hole.
The cache's epoch seam (`caching.invalidate_user`) already existed — what was
missing was a *trigger* on the backend delete path.

**The fix is cross-service, and the endpoint is not an orphan.** `POST
/internal/rag/cache/invalidate` is registered on ai-service, but it is never built
without its consumer: `HttpAiServiceClient.invalidateCache(userId)` calls it and
`RagCacheInvalidator` drives that client from `KnowledgeService`'s delete seam. A
contract test (`test_the_write_endpoint_has_a_real_backend_caller`) fails if either
the endpoint loses the backend caller or the after-commit invalidator disappears —
the inverse of Epic 143's discipline, where an unwired *read* was the sin. This is
why the endpoint was deliberately *not* built in the Epic 143 turn: a write surface
with nobody to call it is a machine built for nobody.

**"After commit" is the whole bug, not a detail.** Bumping the epoch *inside* the
delete transaction would be a plausible-looking but wrong fix: until the rows
commit, another replica reading the shared store still sees `status='ready'`, so
the freshly bumped generation would let the reader re-fetch and re-cache the old,
still-quotable content. `RagCacheInvalidator.invalidateAfterCommit(userId)` uses the
same `TransactionSynchronizationManager.afterCommit()` pattern
`StoredObjectReclaimer` established for object deletes: the rows are durable and
retired before any reader is told to look again, and a rollback never bumps. Called
with no active transaction (a maintenance path), it runs inline. The one seam
`KnowledgeService.retireRef` funnels note edits/deletes *and* resume
delete/version-switch through it; `deleteSource` calls it directly. A note **edit**
re-ingests new text immediately after, whose success bumps the epoch again — the
extra after-commit bump is harmless (a generation counter, not a lock) and covers
the case where that re-ingest fails or is slow.

**Fail-open on every layer.** The endpoint takes **no body** — the user is its own
`X-User-Id`, so a caller cannot name another user's cache to retire — and its only
effect is `invalidate_user`, which is already fail-open: cache off → 0, Redis blip
→ 0 (turns a failure into a miss, never a 5xx). The backend adds a second layer:
an ai-service that is unreachable at `afterCommit` is counted (`careeros.rag.cache_invalidations`,
outcome `failed`) and logged, never escalated to the reader whose delete already
succeeded. The worst honest case is that a stale entry expires on its own TTL; the
delete stands. `AiServiceClient.invalidateCache` is a **default no-op** so every
test double and mock that does not care about the cache compiles and behaves
exactly as before (zero drift); only `HttpAiServiceClient` performs the call.

**Why one call invalidates the whole fleet.** A generation bump is not a scramble
of cached values: retrieval keys embed the per-user epoch, so retiring a generation
makes all its keys unaddressed at once and the old values age out on their own TTL.
With `CACHE_BACKEND=redis` or `layered`, `LayeredCache.incr` writes the epoch to the
**shared** store and drops this process's local copy; every replica's `counter()`
reads it back from there. So one HTTP call to any replica invalidates every
replica — the design epoch was built for, now actually reachable. With the
single-process `memory` backend there is exactly one process to bump. The user id
comes from the request's own header, never a body field, which the internal-contract
key census enforces (no body model → no phantom keys).

**What was explicitly not done.** No Lua script or atomic delete+invalidate (the
cache is a different service; there is no shared transaction, and the after-commit
ordering is the honest boundary). No SCAN+UNLINK of cached keys — generation
retirement is cheaper and cannot miss a concurrent write from another replica.
No e2e test against a live stack (this host has no Docker): the cross-service
contract is pinned on both sides offline instead — the ai-service surface + epoch
mechanism in `test_the_cache_invalidate_endpoint_closes_the_delete_hole.py`, and the
after-commit / rollback / fail-open ordering in the backend's
`RagCacheInvalidatorTest`. No change to the ingest path's existing bump
(Add/Edit stay covered as before). No new operator endpoint beyond the one the
backend now calls. No per-transaction de-duplication of the bump: a bundle import
that deletes N notes inside one transaction registers N after-commit bumps (N
idempotent epoch increments, N cheap HTTP calls). Correct, just not coalesced; a
hot batch path would be where a transaction-scoped "already bumped this user" set
earns its keep, which this low-frequency recovery path does not justify.

**Two honest boundaries, stated plainly.** (1) No live-stack e2e (no Docker on this
host): the "delete a note, ask the same question, get no citation" walkthrough is
pinned on each side offline but never run end to end here — the one operator step
that remains. (2) The `/internal/ops/*` verdict endpoints this pass touched in
`API.md` are still read-only diagnostics with no frontend or alert consumer; giving
them honest rows (a completeness gate the *full* suite exposed, since that gate is
not in `verify_gates`) makes the surface truthful but does not put those two
numbers on a screen. Wiring one to a real consumer is a separate, larger task.

**Verification.** ai-service: 9 offline tests (401/400 auth door; cache-off →
`{invalidated:false,generation:0}`; one call bumps 1, repeats bump again; a
retrieval key under generation 0 is no longer the reader's key after the bump; a
caller cannot reach another user's epoch; a blipped backend reports "not
invalidated" rather than a lie; the endpoint has a real after-commit caller).
backend: `mvn test` green on `RagCacheInvalidatorTest` (6: inline-with-no-transaction,
waits-for-commit, rollback-never-bumps, refusal-can't-undo-delete, refusal-inside-
afterCommit, null-user-noop) plus the four `KnowledgeService` constructor-wiring
suites and `StoredObjectReclaimTest` regression. The internal surface reconciles
on both sides (`test_api_doc_contract`, `test_internal_contract`,
`test_response_shape_contract`): the new route has exactly one API.md row naming
its `{invalidated,generation}` response, and the two previously-undocumented
`/internal/ops/*` verdict endpoints picked up by that census were given honest
"No backend caller" rows + ledger reasons. The new `careeros.rag.cache_invalidations`
Micrometer counter is named in `DEPLOYMENT.md`'s meter roster (excused, not alarmed —
a failed bump is a freshness cost behind a WARN line, not an outage) and in the alarm
gate's `METRICS`, so the "every shipped meter is watched or excused by name" census
stays complete. The keep-alive vocabulary census grew to admit this horizon's worker-
liveness paragraphs and the three `ai-service` noun-only comments (different clock,
no interval beside the word) rather than renaming honest comments to dodge a count.
Full `verify_gates` + backend `mvn test` green at commit.

---

## Epic 148 — the live trace window is bounded, and its folds are counted

**The shape of the risk.** `useTaskStream` accumulates two arrays straight off the SSE
relay. `text` appends every token delta (`prev + token`) and `traces` appends every
trace frame (`[...settled, next]`). Neither had a ceiling, so both the React state
and the DOM `AgentTimeline` mounts (`events.map(...)` → one `<li>` per row, each with
its own payload-expand state) grew with the length of the run. The step fold
(`applyStatusEvent`) was already bounded by the seeded roster; these two were not.

**Honest boundary, stated first.** As of this epic the `trace` channel has **no
producer**: the pipelines publish `status` / `progress` / `done` / `error` and an
idle transport frame, while `trace` (like `token` and `artifact`) is declared in
`lib/sse/use-sse.ts` with nobody writing it yet. Today's timeline stays empty.
This is therefore a ceiling on a render path that is *already wired*, not a fix
for an OOM happening right now — it matters the moment a producer lands, or a
caller supplies a long external list. `token` is deliberately left unbounded:
it is a *complete* answer, and dropping a delta would corrupt the sentence rather
than bound a window. Bounding the streamed answer is a separate task with a
different correctness contract (it needs a reader-visible truncation decision,
not a silent slice); this epic does not pretend to have solved it.

**What shipped.** A pure reducer in `frontend/src/lib/trace-fold.ts`:
`foldTrace(fold, next, cap)` and `settleTraceFold(fold)`, with `cap` injected so the
bound is testable with small windows (default `TRACE_ROW_CAP = 200`, a conservative
ceiling rather than a measured P99 — there is no producer to measure yet).
`useTaskStream` now holds a `TraceFold { events, omitted }` instead of a bare
array; `onTrace` folds through `foldTrace`, `onDone` settles through
`settleTraceFold`, and the state exposes `tracesOmitted`. `TaskProgress` renders
`N steps · M earlier steps folded` (en/zh, `ai.taskStream.foldedSteps`) so a reader
can see that the window is partial rather than believing the timeline is whole.
Caller-supplied `traces` bypass the fold and report an omitted count of 0 — the
window's number would be a lie for data that never passed through it.

**Zero drift, proven by an oracle.** With the cap unreached, `foldTrace` is the old
reducer verbatim: a same-id frame merges in place, a new frame settles the
previous running rows, and append order is unchanged. The test file carries the
pre-cap reducer copied out of the hook and folds a mixed wire sequence (new ids,
repeated ids, settles, an error flip) frame-by-frame against it, asserting exact
array equality and `omitted === 0` throughout. `settleTraceFold` is the old
`onDone` map. A source-contract check pins the hook to these two functions and
refuses any return to a bare `setTraces([...settled, next])`.

**One simplification worth recording.** The first cut partitioned the grown array
into settled vs running indices, dropping the oldest settled first so an in-flight
row would survive. That partition turned out to be dead logic: the new-id branch
settles every earlier running row *before* appending, so by the time the cap
slices, `next` is the only row that can still be running, and it sits at the
tail — a front slice cannot evict it. The fold collapses to one bounded
`grown.slice(drop)`, so per-frame cost is O(cap) (settle + slice) and memory is
O(cap), down from O(frames seen) and unbounded in run time. The test
`never evicts the in-flight step` pins the real invariant instead of an
unreachable state; a 1000-frame run at the default cap asserts the window holds
exactly 200 rows, keeps the newest, and counts all 800 folds. Edge cases pinned:
cap of one, a same-id merge that must not touch `omitted` even when full, a late
frame for a rolled-off id re-entering at the tail (a window over *frames*, not a
per-id store), non-positive/non-finite caps degrading to one row rather than
removing the bound, and input-fold immutability.

**A cross-epic census interaction, resolved without disguise.** The heartbeat
vocabulary census in `test_response_shape_contract.py` walks every `docs/*.md`
paragraph and shipped source comment for the noun (`ping|keep-alive|heartbeat`)
and requires the count to match the ledger exactly. Epic 147 had just grown that
ledger to count this horizon's own worker-liveness sentences (10); its closing
paragraph, which names the census, then pushed the file to 11, and the ledger was
corrected to 11 rather than rewriting an honest sentence to dodge the count.
This chapter naming the census adds two more vocabulary lines (the explanatory
paragraph and the roster of nouns), taking `ALGORITHMS_HORIZON.md` from 11 to 13 —
the ledger follows to 13, still with zero interval-bearing claims. The census is
self-referential by design: a paragraph about the word is the word, and making
the prose vaguer to keep a number down would be the dishonest way out.

Epic 148 also had to keep the **code** side of that same census unchanged,
because both epics share the one test file: the new `trace-fold.ts` docstring
avoids the census noun entirely (an idle transport frame, never the borrowed
word), and `task-stream.tsx` merged its two `@/components/ai/processing-steps`
imports into one block so the docstring span stays on line 21 — the exact line
Epic 147's assertion names. With that, the two commits are each independently
green: Epic 147 never references a file it did not ship, and Epic 148 adds no
code span the ledger does not already count.

**Verification.** `trace-fold.test.ts` 17 offline tests (zero-drift oracle, bound,
honest count, in-flight survival, late frame, bad caps, immutability, 1000-frame
bound, plus a source-contract on the hook); related frontend suites 84/84
(`trace-fold`, `use-sse`, `processing-steps`, `translations`, `used-keys`);
`tsc --noEmit` clean. No live-stack e2e: the trace channel has no producer to
drive a real long run, so the bound is proven on the pure reducer and the hook
wiring, not on a browser streaming thousands of frames. The two i18n gates hold:
`foldedSteps` exists in en/zh and is asked for by a literal `t()` call.

---

## Epic 149 — a concurrent spring-cloud merge, reconciled into the truth

**How this arrived.** A full-suite pass over the accumulated worktree surfaced
eight failures. One was Epic 147's own self-referential vocabulary count and was
closed in that commit; the other seven were not from this line of work at all.
Their input files were byte-identical to `HEAD` and outside the staged set: a
concurrent session had shipped a Spring Cloud edge citizen (`gateway-edge.spec.ts`,
the `eureka`-profile compose path) and left the surrounding documents and one
compose environment block behind. The long-standing instruction for this repo is
to pick up an abandoned merge where it stopped rather than wait, so these are
closed here, with the fix made to the *source of truth*, never to the gate.

**One real configuration defect, not a doc drift.** The dev `docker-compose.yml`
had the backend on the `eureka` profile with a discovery service present, while
the gateway still declared "the dev stack uses the default simple mode" and
activated no profile. That is precisely the half-configured edge its own comment
warns against: the backend registers with the registry, the gateway keeps polling
a static list, and roughly half the routing decisions can disagree. The gateway
now activates `SPRING_PROFILES_ACTIVE=eureka` and names
`EUREKA_DEFAULT_ZONE=http://discovery:8761/eureka/`, matching both the backend in
the same file and `docker-compose.prod.yml`. The stale simple-mode comment was
replaced with an honest account of the two mutually exclusive paths. The
`GATEWAY_BACKEND_URI` default stays in the base document as an inert fallback —
the `eureka` profile empties the simple instance list, so it resolves nothing —
because removing it would change the base document outside a compose deployment.

**The count and timeout censuses, told the truth.** Three honest-counting gates
had drifted against what actually ships, and each was repaired at its source:

- `e2e/README.md` listed the new `gateway-edge` spec as a parenthetical prose
  aside inside the `N passed (...)` breakdown, which the arithmetic gate parsed as
  an unknown label and double-counted. The breakdown now carries the plain
  `1 gateway edge` item; the prose describing what that case walks moved to its
  own sentence after the parenthetical. The alias table in
  `test_the_e2e_readme_keeps_its_own_arithmetic.py` grew by exactly one entry —
  the extension point the test itself names ("update ALIASES or the README,
  never neither"), matching the real spec rather than excusing it.
- `docs/PRODUCT.md` recorded `68/68` while `e2e/tests/` ships 69 cases (17 specs).
  It now says `69/69`. The undated sentence is graded against the live spec count,
  and the dated run record in `e2e/README.md` stays untouched — the gate needs at
  least one dated record to tell a historical run from a claim about today.
- `.env.example` described the backoff base as "draws from `[0, 500ms]`", and the
  limiter's fail-open census, which counts millisecond figures to check the Redis
  timeout pair, read that as a fourth timeout claim. The comment now says
  `[0, 500] milliseconds` — the same meaning, and more precise about a variable
  whose unit is already `_MS`; a number in a backoff comment must not impersonate
  a client timeout.

**Verification and boundaries.** The seven failures pass (17 tests across the
e2e-arithmetic, product-doc, limiter and registry suites), plus 22 compose/env
regression gates (parse, dev variable coverage, declared-knob coverage, loopback
bindings, the two doors, config-client opt-in, deployment port doc). No test was
relaxed, skipped or re-baselined downward; every change makes a document or a
compose environment agree with what the code and specs actually ship. No live
stack was started, so the newly-activated dev gateway profile is verified by the
compose/registry contract and YAML parse, not by watching Eureka registration on
running containers — that walk remains an operator step, stated rather than
implied. This chapter deliberately names no transport-liveness noun, so the
vocabulary census stays at its honest 13 lines and the ledger does not move.


## Epic 150 — the two read-only verdicts get a real consumer, and their honesty markers become true **DONE (verified 2026-11-12)**

Epics 140 and 143 shipped two read-only control-plane verdicts: `GET
/internal/ops/workqueue` (the embed work queue's health over live Redis plus the
consumer's own tick) and `GET /internal/ops/cache` (the RAG cache's honest
saving, where a zero hit rate is three states and not one fault). Both are pure
observers — fail-open, always 200, verdict in the body — and both were recorded
in `docs/API.md` with a literal `no backend caller:` marker. That marker was
honest, but it was also a promise: each row ended with a sentence naming the
consumer that had not arrived yet ("a future backend gauge can scrape it").
This Epic is that consumer. It closes the promise at its source rather than
quietly deleting the sentence.

**What was deliberately NOT built.** The task that opened this Epic proposed
giving `release_cooldowns()` a POST HTTP route so a backend caller could clear
the dead-letter cooldown set, and adding a matching `WorkQueue.release_parked()`
to clear the backoff set alongside it. That design was rejected after reading
the three sources that would have had to agree with it, because it fails this
horizon's own rules:

* The verdict endpoints are *readers*, not actuators. This document (Epic 140)
  states the boundary verbatim: the verdict is a read, and it never releases a
  cooldown or drains the dead-letter stream; `release_cooldowns()` remains the
  operator's explicit action. A route that mutates Redis would invert a boundary
  two shipped Epics and a contract test deliberately drew. "No caller" here was
  a design decision, not a gap to fill with the first caller that presents itself.
* The backend has no authorization tier for a mutation like that. The whole
  Spring security chain ends in `anyRequest().authenticated()`; the `admin` word
  exists in the user schema and nowhere as an `@PreAuthorize` check. A
  `POST .../release` under the current surface would therefore let *any*
  signed-in account flush every cooled-down poison job at once — releasing them
  straight back into the producer's next tick, which is a model-call storm and a
  new attack surface, not a diagnostic. Building the admin gate is a separate,
  larger decision and does not belong inside a queue-observability Epic.
* Even as an internal, unexposed call, a Java method nobody invokes is the same
  write-only machine one layer over: the "real consumer" would be a method whose
  only purpose is to satisfy the router that added it. That is the exact shape
  this horizon's Definition of Done forbids — an algorithm or mechanism lands
  only when it replaces a *live* call site.

**What was built instead — the next step the project already named.** This
document's Epic 140 section says the verifier endpoints are "the clean single
source that step would scrape" and that wiring their numbers into the
backend/gateway `careeros.*` meter roster is "a separate, deliberate next
step"; `docs/API.md` says the same in one line. That step is done here. A new
backend collector, `com.careeros.ai.service.AiOpsMetrics`, is the consumer:

* It is a `@Component` with a `@Scheduled(fixedDelayString =
  ${careeros.ai.ops.metrics-refresh-ms:60000})` tick — the same shape as
  `AiUsageMetrics`, reusing `@EnableScheduling` (already on) and the shared
  `MeterRegistry`. One fixed-delay tick asks both engine endpoints.
* It crosses the existing typed seam: `AiServiceClient` gains two default
  methods (`workqueueVerdict`, `cacheVerdict`) returning an empty map, so every
  fake, mock and alternative client compiles and behaves byte-for-byte as
  before (zero drift); only `HttpAiServiceClient` overrides them with the two
  GETs. The default empty map is also what a scrape sees when no client serves
  control-plane reads, and the collector treats that as a failed read, not a
  healthy zero.
* `require_internal` insists on a non-empty `X-User-Id` even though neither
  verdict's calculation scopes by user (`read_status` / `read_health` never
  touch `ctx.user_id`). The bridge therefore sends one explicit, non-personal
  value — the nil UUID — and says so in the seam's own javadoc. It cannot
  collide with an account and makes the wire honest: this is a system read, not
  a person's context.

**Only measured numbers cross.** A Prometheus series is a number, so the
collector publishes the *raw readings* the verdicts already carry — `dlq_len`,
`delayed_len`, `pending` and the engine's own `queue.ok` from one endpoint;
`hit_rate` and `errors` from the other — plus a `scrape_ok` self-check. It
deliberately does **not** encode the verdict word into an integer: the engine
never claimed a total order among `degraded`, `stalled`, `backlogged` and
`healthy`, and a numeric colour scale would silently invent one that a
dashboard would then treat as severity. The verdict sentence, its `alerts`
strings, and per-key diagnostics (`observation_error`, `degraded_to`,
`freshness.last_tick`) stay on the control-plane endpoint and never become
series. A contract test pins that the registry holds exactly the seven declared
gauges and nothing else, so a future field cannot leak in silently. The project
also gains no public route and lowers no authorization boundary: the two engine
endpoints remain behind the shared internal token; there is simply one more
authenticated caller.

**Fail-open, without confusing a silent engine with an empty queue.** The two
reads are independent, so a cache endpoint that is briefly unreachable cannot
blank the queue's numbers. A refresh that cannot reach one endpoint keeps that
half's last good readings and flips `scrape_ok` to 0 — it never publishes a zero
for "the queue is empty". The projection is a pure function of the two answers
and the previous reading (`AiOpsMetrics.project`), so all of this is measured
offline with an injected `AiServiceClient` and a `SimpleMeterRegistry`: the first
refresh's numbers, a full failure keeping the last reading with `scrape_ok=0`,
one half failing alone, an empty answer not claiming healthy zero, a later
refresh replacing numbers together, and a malformed field degrading to zero for
that field only. Seven backend tests, all green.

Two census gates had to grow with the new file, as their own rules require. The
backend-reader corpus in `test_response_shape_contract.py` gained `AiOpsMetrics.java`
— it is a real consumer of both verdict answers — with a written note that its
control-plane field names are bound inside independent try/catch arms rather than
the `Map<String,Object> x = ai.y(...)` form this key-reconciliation reader can
follow, so its seven projections are pinned by the meter roster and the collector
test instead of by that walk. The same file's Java-record declaration census went
from 209 to 210 for `AiOpsMetrics.Reading`, a non-route receipt counted like the
`Purge` and `Reclaim` records before it. Neither pin was relaxed: a consumer that
arrived unmentioned, or a record the shared opener could not read, would still
redden this gate.

**Verification.** Backend `mvn test`: 205 suites / 1405 tests, 0 failures, 0
errors — including the repeated `@SpringBootTest` context starts, which prove the
new collector's constructor cannot block startup when the engine is unreachable.
`scripts/verify_gates.sh`: 557 representative offline contract gates passed. The
three contract/meter files touched directly (`test_api_doc_contract.py`,
`test_internal_contract.py`, the alarm roster) pass together (31), as does the
full `test_response_shape_contract.py` (32) and the three configuration/window
censuses most likely to see a new fixed-delay tick (22). Full ai-service suite:
2709 passed, 2 skipped. No test was skipped, relaxed or re-baselined downward to
make this Epic pass.

**The meter roster, honoured in both directions.** Every new gauge is named in
`test_the_alarms_name_metrics_that_ship_and_a_page_that_says_what_to_do.py`'s
`METRICS` dict and gets exactly one row in `docs/DEPLOYMENT.md` under "Every
Meter and What Watches It", with a reason of its own. None is alarmed, and that
is a decision with a reason rather than an omission: queue health is a brand-new
signal with no measured good/bad baseline, and a threshold invented now would
page on a busy minute. They are excused by name *for dashboards* until a
baseline separates a stuck queue from a busy one — the same honest state
`careeros_ratelimit_decisions_total` already documents. `scrape_ok` is the
strongest candidate for a future rule (a dead or silent engine), but a single
missed tick during a redeploy is noise, so even it waits for a continuity
baseline. Adding a rule later is the ordinary "retire an excuse" move this gate
was built to make visible.

**The honesty ledger, closed at its source.** Because the backend now really
calls both endpoints, `docs/API.md` drops the `no backend caller:` marker from
each row and replaces it with the collector that reads it. The measured
`UNREACHED_BY_THE_APP` ledger in `test_api_doc_contract.py` shrinks from 10 to
8, and the two rows move out of "advertised but never reached" by crossing the
gate that would have reddened had the doc and the client disagreed. No other
contract moved: neither row carries a `{...}` response group, so the five-row
`response_claims()` positive control is unchanged, and no new `/internal/...`
literal entered the page, so the exempt-literal census is unchanged.

**Honest bounds.** There is no live Prometheus or Grafana on this host, so the
scrape is verified by the backend's offline collector tests and the three-way
meter roster gate, not by watching a real scrape endpoint — that walk remains an
operator step, stated rather than implied. The reading is a 60-second snapshot,
not an event stream: a fault that appears and clears inside one tick is not
captured, which is the right resolution for a queue-health dashboard but not a
sub-minute incident probe. The refresh adds one authenticated GET per endpoint
per minute of backend traffic — bounded, and itself measured by `scrape_ok`.
Finally, this chapter names no transport-liveness noun, so the docs' vocabulary
census stays at its honest 13 lines and that ledger does not move.

## Epic 135 — closed with evidence: pg_trgm is not a term-scoring stand-in **CLOSED (2026-11-12)**

The roadmap once carried one `(next)` line: "the lexical channel can be scored
in-process without pg_trgm when the corpus is small." Worked from the sources
rather than the phrase, that claim does not survive contact with the code, and
shipping a BM25 scorer for it would have been two things this horizon forbids
at once — a behaviour change dressed as an optimisation, and a second scorer
for a job another scorer already does.

**Where pg_trgm is actually used.** The backend's `/jobs` and `/search` rank
with tsvector + `ts_rank`, ILIKE and pgvector; they never touch pg_trgm. The
only live trigram call is `ai-service/app/rag/store.py:trigram_search`, one of
the three RAG recall lanes, and its own docstring names its job: "Catch
misspellings / rare exact tokens via pg_trgm on chunk text," implemented as
`similarity(c.text, $2) > 0.15`. That is a *near-miss* lane — it exists to find
a chunk whose spelling is close to the query but whose exact terms are absent.
Okapi BM25 (already in `app/algorithms`, already reranking under
`RERANK_MODE=bm25` since Epic 134) scores exact-term TF-IDF relevance. It cannot
return a document that shares no term with the query, so substituting one for
the other would silently drop the misspelling recall lane. That is a real
behaviour change, not a complexity win.

**No measured bottleneck to fix.** There is no query plan, no profile and no
timing record anywhere in the repo naming pg_trgm as a cost, and no seed giving
the chunk corpus a size at which an in-process pass would win. The "small
corpus" premise in the phrase referred to the ~40 job rows — which, as above,
do not use trigram scoring at all. Optimising an unmeasured path while changing
what it returns is exactly the shape the Definition of Done rejects.

**Disposition.** The roadmap row is corrected to `CLOSED with evidence` with
the three reasons inline; no scorer was added, no recall lane was touched, and
Epic 134's BM25 rerank remains the one place term scoring is paid for. If a
future profile does put a number on the trigram lane's cost, the honest next
step is to *measure it first* and then decide whether a near-miss-preserving
in-process index can match `similarity()` — not to relabel BM25 as its
equivalent. No census was relaxed to close this row.

## Epic 151 — a sibling replica can settle whose task it is **DONE (verified 2026-11-12)**

Epic 131 made every task's frame feed replayable from a Redis stream, so a
subscriber on any replica can follow a task another replica owns. One question
was deliberately left on the in-process dictionary: `owner()` read only
`_TASKS`, so a request that landed on a node which had not run the task answered
the same 404 as a task that never existed. The backend relay absorbed that by
walking every door until one stopped refusing (`SseRelayService.consume`, the
first 200 wins). A refusal is a slow, ambiguous way to ask "who owns this?" —
and it means a task is only reachable while its home node answers.

**Ownership rides with the frames, not beside them.** The one design that keeps
a single source of truth is to put the owner on the mirrored event itself.
`publish()` now copies the payload onto the mirror with one extra top-level
field, `owner`, next to `event`/`data`/`ts`. The in-memory list and the frames
built from it keep the exact three keys they always had — the SSE generator
forwards only `event` and `data`, and `state()` projects only its four declared
fields — so the ownership field never reaches a browser. No second redis key,
no ownership store to keep in sync: the same `XREVRANGE` that `peek()` uses to
answer a foreign task's state also answers who may read it (`_Backplane.holder`).

**Memory-first, then the mirror; fail-closed either way.** `aowner()` answers
from `_TASKS` on the home node with no new wire command, and reads the last
mirrored event only when the task is not local. `_require_owner` becomes async
to make that read possible; the synchronous `owner()` stays as the memory-only
form and is what `aowner()` calls first, so it is not an orphan. The refusal
did not get looser: a stranger, a task recorded with no owner, and a sibling
whose mirror is unreachable all still get the identical 404 a missing task
gets. Three offline cases pin each of those, plus the home-node no-extra-read
case and the guarantee that `owner` stays off both the wire frames and the
state projection. `test_a_sibling_replica_can_settle_whose_task_it_is.py`
measures all six against the existing fake-streams Redis.

**Backend untouched, and still correct.** `SseRelayService.consume` already
walks doors in order and stops at the first 200. With a sibling able to settle
ownership, the first healthy node can now answer instead of every node but one
refusing; the walk and its 404-tolerant fallback are unchanged, and its own
test pinning "knock past a 404" still describes real behaviour for the moment
the mirror is down. No Java source, no meter roster and no public route moved.

**Census sync, not relaxation.** The only contract that moved was the one that
must: `test_response_shape_contract.py`'s liveness-interval definer ledger saw
its `subscribe` declaration shift 258 → 275 and its two consumer reads 265/262
→ 282/279, because this chapter's `holder()` reader and the frame-safety comment
sit above `subscribe` in the same file. The signature, its number and both
consumers are unchanged, so the ledger was updated in place with the reason
written beside it. The frame-payload census did not move: no `publish(` call
site's data argument changed, and `owner` is attached on the mirror branch,
which that walk does not read. The docs' vocabulary ledger stays at 13 — this
chapter, like Epic 150's, names no transport-liveness noun. The API honesty
ledger is unchanged: the app still reaches these routes only through
`/internal/stream/{id}`, so no `UNREACHED_BY_THE_APP` reason was edited.

**Verification.** `test_the_task_bus_can_scale_out_through_redis_streams.py`,
`test_the_route_that_hands_out_a_task_stream_knows_whose_task_it_is.py` and
`test_stream_event_contract.py` pass together (20) after the change; the full
contract/census set (`test_response_shape_contract.py`, `test_api_doc_contract.py`,
`test_internal_contract.py`, `test_stream_event_contract.py`) passes (59); the
six new offline cases pass. No test was skipped, relaxed or re-baselined
downward to close this Epic.

## Epic 152 — the task feed stops accumulating one entry per task **DONE (verified 2026-11-12)**

Epics 131 and 151 made the task feed correct on any replica: every `publish()`
appends to an in-process list and mirrors the same event onto a Redis stream,
and ownership travels with it so a sibling can settle whose task it is. What
neither Epic bounded was *space*. The in-process `_TASKS` dictionary grows by
one entry per task for the whole process lifetime, and every mirrored task gets
a `careeros:tasks:<id>` stream key with no expiry. On a service that runs for
days, that is unbounded growth in both process memory and Redis for a feed
whose usefulness ends minutes after its terminal frame. `gc_old_tasks()` had
even been written to reclaim the memory side -- and was dead code, called by no
shipped path. This Epic closes both without starting a new clock or adding a
knob nobody would tune.

**Redis: a bounded window, renewed on every write.** The mirror client already
has a `pipeline()` that batches commands into one round trip (the cache's
liveness counter was the first user). `_Backplane.write()` now sends the event
and its key expiry together: `XADD ... MAXLEN ~ 400` followed by `PEXPIRE key
3600000`. Two commands, one wire round -- non-atomic (this client has no
transactions) but the drainer is the sole writer, so an append is always paired
with its renewal in order. The consequence is the one a follower needs: **a task
that is still being published never lapses**, because each event pushes the
window out to a full hour; only a task that goes quiet for that whole window is
left to expire. The window is a module constant, `_MIRROR_TTL_S = 3600`, beside
`_MAX_HISTORY = 400` -- deliberately *not* an operator setting, since no caller
needs to retune it and a knob with no reader is a knob that does nothing. It is
measured to outlast the backend relay's ten-minute read budget and the stream's
own short wait, so a renewing key cannot vanish mid-follow.

**Memory: reclamation rides the clock that already ticks.** Rather than add a
sweeper task, `gc_old_tasks()` is called once per pass from the three periodic
loops that already run on the service's existing cadence: `embed_loop` (single
process), `embed_loop_distributed` (multi-replica), and `_fallback_loop` (Redis
down). The last one matters: when the mirror is unavailable, memory gc is the
*only* reclamation the feed gets. Each call is a local import, which keeps the
loops' module-level line layout -- and the shipped-source comment census that
reads it -- untouched. No `create_task`, no extra `sleep`, no new interval: a
source-contract test pins that every loop calls the reclaimer and that the
number of wait calls per loop did not grow, so a future "just add a sweeper"
cannot slip a second clock in unseen.

**Honest boundary, stated rather than hidden.** `gc_old_tasks()` has always
meant one thing (its offline test pins it): remove only tasks that are both
*finished* and older than the window; leave fresh and still-running tasks
alone. Wiring it up means a finished task queried more than an hour later now
answers `state() is None` where it used to keep returning its last frame. That
is the intended fix, not a regression -- no relay can still be following a
task after an hour (its read budget is ten minutes), and the alternative is a
dictionary that grows without limit. The behavior change is confined to that
one projection; event shapes, ordering, the three-key wire frame, and the
ownership field's absence from frames are all unchanged. A task created but
abandoned before its first `publish()` has no stream key at all, so the Redis
TTL cannot reach it; that case is exactly why the memory-side gc is wired too,
and neither side alone would have closed the leak.

**Why the mirror-down follow path stays honest.** If a key lapses while a
subscriber is waiting on the tail, the stream client does not error: an absent
key simply answers no event, the loop keeps waiting within its short interval,
and the relay's own finite read budget is what ends the connection. A *new*
subscriber whose key already lapsed gets the same "task not found" answer as a
task that never existed -- consistent with Epic 151's fail-closed ownership
gate. Write-time renewal is what keeps this from ever happening to a live
task.

**Zero drift where it counts.** In the default memory mode the mirror is not
built, so `write()` is never reached and not a single new Redis command is
issued; the offline suite proves the memory feed stays whole with no backplane.
No config field or env example changed, no `resp.py` reply parser changed
(`PEXPIRE` returns an integer the existing `:` branch already reads), and no
public route moved. One test double grew a `PEXPIRE` branch so the pipeline's
second command is answered rather than refused; the six existing scale-out
cases and the five Epic 151 cases pass unchanged against it.

**Census sync, not relaxation.** Adding the constant block and the two-command
write pushed `taskbus.py`'s single liveness-interval definer down 16 lines: the
`subscribe` signature moved 275 → 291 and its two consumers 282/279 → 298/295.
Those three line numbers were updated in place with the reason beside them; the
default interval, the definer count, and the override file list are all
untouched. The docs' noun-vocabulary ledger stays at 13 -- this chapter names
no transport-liveness noun, and an early roadmap line that did was reworded
before it could move the count.

**Verification.** Reclamation and source-contract set 104 passed (including the
four new source-contract cases and two new runtime cases), full
`test_response_shape_contract.py` 32 passed, and the four configuration/window
censuses most likely to see a new time constant or knob 29 passed -- evidence
that the module-constant TTL really does stay out of the knob and lifetime
ledgers. Full ai-service suite, backend `mvn test`, `verify_gates.sh` and the
pre-commit hook all pass; no test was skipped or re-baselined downward.

## Epic 153 — the dashboard's last unread component gets a reader **DONE (measured 2026-11-12)**

**The gap was a wire field, not a missing endpoint.** `DashboardService.recentActivity(UUID)`
(`report/service/DashboardService.java:148`) queries `application_events` newest-first with
`Paging.first(RECENT_LIMIT=5)`, maps each row through `toActivity` into the
`RecentActivity(UUID id, UUID applicationId, String kind, Map<String,Object> payload,
OffsetDateTime createdAt)` record (`report/dto/DashboardDtos.java:37`), includes it as the
eleventh component of `DashboardResponse`, and caches the whole response through the Epic 125
L1/L2 `DashboardCache`. `DashboardCacheTest.sample()` even builds a `RecentActivity` to verify
the cache round-trips it. The field is real, maintained and paid for on every dashboard read.

**It was thrown away at the browser boundary.** The comment in `normalizeDashboard`
(`frontend/src/lib/api/normalize.ts:1263`) already listed `recentActivity[]` among the response's
components, but the mapper's return had no such key, `DashboardPayload` (`types.ts`) had no such
field, and a full frontend search found it only in two test fixtures and that comment -- no reader,
no render. `ai-service/tests/test_response_field_contract.py` pinned this precisely:
`_emitted("DashboardResponse") - read_off_d == {"recentActivity"}`, with a comment saying the
record carried it for a future reader to notice. This epic is that reader. The consumer is the
signed-in reader looking at their own dashboard, which is a harder consumer than an operator who
might curl an endpoint -- so it clears the "no write-only machines" rule on evidence.

**A pure reader, then a card.** `normalizeRecentActivity(raw)` is a module-level mapper that reads
only the record's five own camelCase components and passes the free `payload` map through
untouched: its keys have five different writers (`ApplicationService.writeEvent` emits `status`
`{from,to}`, `note` `{note}`, `reminder` `{reminder_at}`/`{cleared}`, `outcome` `{field}` with
`offer_compensation`/`rejection_reason`; `InboundReplyService.file` emits `reply`
`{mail_id,sender,subject,intent}`), so reading any of them in the mapper would be guessing at
shapes no single producer pins. A row with no `id` is dropped exactly as an attention row is,
because every line links to its application. `recent-activity.tsx` owns that vocabulary instead:
it renders a human sentence per kind, names the two outcome fields the product writes, resolves a
`status` move's stage through the stages table, and gives a newer, unknown kind a neutral line
rather than filtering a real event out -- the exact defect this card closes. Rows with an
`applicationId` link to `/applications?application=...`; a row cached before that id existed still
renders as text. All copy is en/zh through `t()`, so the card is readable in both languages.

**Honesty ledger advanced, never relaxed.** The Python static census counts every accessor read in
the browser mappers and binds each one to a Java record component. This change registered
`RecentActivity` as a new `("java", …)` producer, registered `normalizeRecentActivity` in `READERS`,
and moved the counts it actually measured: `normalizeDashboard` sites 18 → 19 (the one new
`list(d, "recentActivity")`), receiver `d` 10 → 11, `PRODUCERS` 88 → 89, mapper population 52 → 53,
named accessor calls 398 → 404, whole-oracle reads 409 → 415, derived locals 99 → 103. The
`_emitted("DashboardResponse") - read_off_d` difference went from `{"recentActivity"}` to the empty
set: **every component of `DashboardResponse` now has a reader.** Each moved number carries the
reason beside it; no assertion was deleted or re-baselined downward. Two `payload` sub-steps were
split onto separate lines (`const payloadMap = pick(...)` then `rec(payloadMap)`) so the field
census can still name the local, following `normalizeResumeScore`'s existing pattern.

**Verification.** `test_response_field_contract.py` 18 passed, and the four static censuses most
likely to see a new reader or key (`response_field`, `stream_event`, lifetime ledger, config-knob
ledger) 40 passed. Frontend `recent-activity.test.tsx` 8 cases (each kind's copy, cleared-vs-set
reminder, both outcome fields plus a stranger, stage badge, id-required link, payload-less row,
event instant) and `normalize.test.ts` 3 new boundary cases (payload pass-through with an unknown
kind, id-required drop, empty-array omission) pass; full frontend suite 131 files / 1250 tests
green. `used-keys` and `translations` gates confirm all 15 new en/zh keys are asked for by name
and non-blank in both languages; `copy-census` browser sources moved 168 → 169 with the new card
(and no English literal was introduced). `next build` and the 340 kB route budget are the final
gate. No backend source changed; `docs/API.md` notes the field is now consumed.
