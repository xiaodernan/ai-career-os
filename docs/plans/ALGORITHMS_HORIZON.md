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
| 139 | (next) A dead-lettered job stops being re-injected by the producer each tick, until an operator requeues it | producer-side dead-letter suppression keyed by job id |

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
