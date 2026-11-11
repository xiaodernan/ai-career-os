# Performance horizon — Epics 118–124

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
| 123 | The database optimiser is told what the hot queries need | Flyway + explain gate |
| 124 | Every claim above is pinned by a gate that fails when it stops being true | gate suite |

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

**Do.** A token layer (elevation, motion, type scale, focus), a hero that shows the
product working, skeletons that match the shape of what lands, and transitions that
explain where a panel came from.

## Epic 123 — the plate is warm before the request arrives

**Do.** Prefetch the routes a nav row admits, warm the retrieval cache for a
reader's saved searches, and keep the browser's connection to the edge alive across
navigations.

## Epic 124 — the gates

Every claim above gets a test that fails when the claim stops being true, plus the
roadmap/census updates the repo already requires.
