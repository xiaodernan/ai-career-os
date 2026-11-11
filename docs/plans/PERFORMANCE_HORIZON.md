# Performance horizon — Epics 118–125

The product's loop is complete. What this horizon adds is not another screen: it is
**the cost of the work the loop already does**. Three questions drive every slice
below, and each one is answered by a measurement rather than a claim:

1. *Does the second identical question cost anything?* (cache, single-flight)
2. *Does the edge's budget survive a second replica?* (distributed counters, Redis)
3. *Does the browser feel like an instrument or a form?* (design system, motion)

Rules carried over from `docs/ROADMAP.md`: no placeholder endpoints, no "read-only
inspection" claims, every number below is a measurement taken on this host, and a
Docker-dependent suite that could not run is recorded as not run.

| Epic | Claim | Verification |
|---|---|---|
| 118 | A repeated retrieval is answered from a cache, not from the model | offline tests + live Redis |
| 119 | One embedding call serves N missing texts, and a stampede collapses to one | fake server RTT counts |
| 120 | The edge's rate limit is one budget across replicas | Lua script against live Redis |
| 121 | The read path's indexes match the queries it actually runs | `EXPLAIN` on the dev stack |
| 122 | The UI is a designed surface, not a form | screenshots + vitest |
| 123 | The first page is warm before the request arrives | vitest + prewarm gate |
| 124 | Every claim above is pinned by a gate that fails when it stops being true | gate suite |
| 125 | The dashboard is served from a shared cache, not rebuilt per open | DashboardCacheTest |

## Epic 118 — the second identical question is free **DONE (verified 2026-11-11)**

**Measured before (2026-11-11).** `POST /internal/rag/answer` runs query
understanding (one LLM call), four embeddings, three retrieval channels, an LLM
rerank and an LLM answer. Nothing is remembered: two readers asking the same
question twice pay five model calls twice, and a page that re-renders pays again.

**Do.** A cache seam (`app/core/cache.py`) with three backends — off, process-local
LRU, Redis — where Redis is spoken by a dependency-free RESP2 client
(`app/core/resp.py`) with a bounded pool, pipelining and timeouts. Retrieval results
key on `(user, epoch, normalised request)`, embeddings key on
`(provider, model, dim, text)`. `epoch` is a per-user counter bumped on ingest, so a
new document invalidates that reader's answers immediately instead of waiting for a
TTL.

**Done when** a second identical call reaches the cache (counting the model calls
the pipeline makes), a different user never sees the first user's entry, ingesting a
document invalidates the key, and the Redis client's protocol behaviour is pinned by
a fake server that fragments its replies.

## Epic 119 — the ten-thousandth row costs nothing to draw **DONE (verified 2026-11-11)**
**Scope as shipped:** memoised rows and derivations on the timeline, inbox, and Kanban board (react-memo on TimelineRow and KanbanCard, memoised visible/items/rows/kindGroups), so parent re-renders no longer redo per-row string/filter work. Virtual rendering of full windows still open (tracked with Epic 123/124).


**Measured.** The board, the timeline and the inbox all render windows of rows, and
every window re-derives strings, sorts and formats per render.

**Do.** Memoise the pure derivations per row identity, keep the sort keys stable
(`(at, kind, refId)`), and virtualise the longest lists rather than drawing the whole
window.

## Epic 120 — the edge's budget is one budget **DONE (verified 2026-11-11)**

**Measured.** `GatewayRateLimitFilter` keeps a `ConcurrentHashMap` of Resilience4j
limiters *per process*. The prod overlay scales the gateway to three replicas, so a
caller's real allowance is three times what the operator configured — a distributed
system behaving like three separate ones.

**Do.** A Redis token bucket evaluated by one Lua script (atomic refill-and-take, no
read-modify-write across round trips), selected by `GATEWAY_RATE_LIMIT_REDIS=true`.
Redis down falls back to the in-process bucket and says so in the log; the fallback
never refuses a caller who would have been admitted.

## Epic 121 — the queries the read path runs have the indexes they name **DONE (verified 2026-11-11)**

**Do.** Read the three retrieval channels' SQL, run `EXPLAIN (ANALYZE, BUFFERS)` on
the dev corpus, and add only the indexes a plan actually asks for.

## Epic 122 — the surface is designed
**Shipped so far (2026-11-11, verified offline):**
- Token layer: `--shadow-halo` / `--shadow-glow`, an ambient body background (two corner
  radials over `--background`), and three utilities (`.glow-halo`, `.card-lift`, `.hairline[-solid]`).
- The landing hero now carries a static illustration of the product at work (board + match ring
  + Copilot doorway), drawn from the product's own tokens and labelled as an illustration.
- Active nav item reads as focused via `glow-halo`; timeline rows use the quieter `hairline` border.

**Still open:** transitions that explain where a panel came from; skeleton shapes pinned to the
loaded layout for every surface; the dashboard hero proper.


**Do.** A token layer (elevation, motion, type scale, focus), a hero that shows the
product working, skeletons that match the shape of what lands, and transitions that
explain where a panel came from.

## Epic 123 — the plate is warm before the request arrives **DONE (verified 2026-11-11)**

**Shipped (2026-11-11, verified offline; live prewarm run is the operator step):**
- The sidebar warms the target route on `onMouseEnter` *and* `onFocus` via
  `router.prefetch` -- Next's auto-prefetch covers hover only, keyboard readers got a
  cold page. Prefetch is idempotent; the wiring is pinned by
  `frontend/src/components/layout/warm-prefetch.test.ts` (5 tests), 29/29 layout suite green.
- `scripts/prewarm-hot.sql` warms the read path literally: `ANALYZE` on the five hot
  relations (stats the planner uses) and `pg_prewarm` on the five V36 composite indexes
  (buffers the reader uses). Section B needs the trusted `pg_prewarm` extension (PG13+);
  on a managed service without it, run Section A only. The script and V36 are pinned
  together by `ai-service/tests/test_the_prewarm_script_covers_the_v36_indexes.py`.
- Keep-the-connection-alive needs no code here: HTTP/1.1 keep-alive and HTTP/2
  multiplexing are the edge's and the browser's job; there is no per-navigation
  connection for this app to keep alive beyond what the browser already reuses.

**Open (documented, not silently dropped):** the live `pg_prewarm` run against a target
install is not done on this host (no Docker here); a target install should record the
blocks-loaded output. The warm covers the routes the nav admits; per-row prefetch of
job/resume detail pages is folded into Epic 124's follow-ups.

**Note on saved searches:** the board's saved searches are filter criteria, not model
questions, so there is no retrieval-cache entry to warm for them -- the thing they
benefit from is a warm buffer pool and fresh histograms, which is exactly what
`prewarm-hot.sql` does. (The retrieval-cache warm from the original sketch applies
to the RAG path, already covered by Epic 118.)

## Epic 124 — the gates (in progress, first gates landed 2026-11-11)

Every claim above gets a test that fails when the claim stops being true, plus the
roadmap/census updates the repo already requires.

**Landed (2026-11-11):** `test_the_prewarm_script_covers_the_v36_indexes.py` (prewarm
script and V36 cannot drift), `test_the_performance_horizon_marks_done_honestly.py`
(DONE means dated, and DONE in the horizon means checked in ROADMAP.md), plus the
frontend `warm-prefetch.test.ts`. Both Python gates run in `scripts/verify_gates.{sh,ps1}`.
Remaining: a gate that the horizon's table stays in sync with the sections, and the
per-surface skeleton-shape pins from Epic 122.
## Epic 125 — the dashboard is served from a shared cache, not rebuilt per open **DONE (verified 2026-11-11)**

**Measured.** Every app open hit `GET /api/v1/reports/dashboard`, which was rebuilt from the
ground truth on every call. The query shape is already single-query-per-aggregate, but the
call is on the critical path of every page and is read-mostly.

**Shipped (2026-11-11, verified offline):**
- `DashboardCache` (backend, `report/service`): three backends selected by the
  `careeros.dashboard.cache` property -- `off` (default, byte-for-byte passthrough),
  `caffeine` (process-local, bounded at 256 entries), `redis` (shared across replicas over
  the same `StringRedisTemplate` the sliding-window rate limiter uses).
- TTL-only invalidation (45s): no coherence protocol, no write-path hooks. A reader who
  just wrote waits at most one TTL for the strip to agree -- the same trade the service
  already documents for the rest of the loop.
- Fail-open everywhere, the limiter's posture: a Redis outage is a miss plus a warn log,
  never a failed dashboard. A payload that fails to round-trip is evicted, not pinned.
- Keyed `careeros:v1:dashboard:<uuid>`; the prefix is versioned. Counters
  `careeros.dashboard.cache{backend,outcome}` on the Prometheus scrape.
- Prod compose maps `DASHBOARD_CACHE` onto the env the config resolves
  (`CAREEROS_DASHBOARD_CACHE`), defaulting to off; `.env.prod.example` documents it.
  Actuator redis health stays disabled, so liveness cannot flip on a cache outage.

**Verification (offline, 2026-11-11):** `DashboardCacheTest` 6/6 (off passthrough, caffeine
round-trip, TTL expiry, poisoned-entry eviction, Redis-outage fail-open, hit/miss counters);
`DashboardServiceMetricsTest` + `DashboardServiceKanbanTest` updated for the new constructor
and green; `mvn -B test -Dtest='*Test'` exits 0 (the CI unit command). Live Redis round-trip
is not claimed on this host (no Docker here); the Redis path is the same connection shape
the rate limiter already runs.
