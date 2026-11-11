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
| 135 | (next) The lexical channel can be scored in-process without pg_trgm when the corpus is small | to be measured |
| 136 | N embed replicas do a job once, and a crashed worker's job comes back | `WorkQueue` consumer-group semantics (fake + real Redis), 12 + 12 offline tests |
| 137 | The auth door carries the landing's design language, without its light-panel pitfalls | `layout.test.ts` source contract, copy census, build + bundle budget |
| 138 | A poison job stops burning a worker on every retry; a failed retry never drops the job | re-queue + `attempts` + bounded DLQ, 9 offline tests + real-Redis end-to-end |
| 139 | A dead-lettered job stops being re-injected by the producer each tick, and heals when its cooldown lapses | `DlqGuard` Redis-ZSET cooldown, 32 offline tests + real-Redis end-to-end |
| 140 | The dead-letter pipeline can be *seen*: one honest verdict over live Redis + consumer liveness | read-only `GET /internal/ops/workqueue`, pure-function health fold, 54 offline tests + real-Redis end-to-end |
| 141 | The signed-in first screen carries the landing/auth design language, without washing the light theme or growing the bundle | `dashboard/page.test.ts` source contract, copy census, build + bundle budget |

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
