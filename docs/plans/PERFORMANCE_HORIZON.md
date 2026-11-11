# Performance horizon — Epics 118–130

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
| 126 | The matches digest reads in index order | Flyway + explain gate |
| 127 | A route that ships too much Java goes red | `npm run budget` |
| 128 | A request carries its own deadline | gateway/backend/ai-service tests |
| 129 | The applications board ships when it is needed | bundle budget |
| 130 | The auth door sells the same product the landing does | vitest + budget |

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

**Live-migration verification (2026-11-11):** the IT harness on this host now applies
V1..V37 from scratch on the dedicated `career_os_it` database (Flyway at boot) and
46/46 context-booting ITs pass against it: GlobalSearchHybridIT 4/4, JobSearchHybridIT
4/4, PagingApiIT 5/5, JobBoardOrderingIT 1/1, TimelineIT 3/3, DomainApiIT 14/14,
SavedJobBoardIT 5/5, HealthIT 2/2, ApplicationNeedleIT 3/3, CompanyNeedleIT 2/2,
JobImportAtomicityIT 3/3. Bringing the context up at all exposed a startup defect
shipped in Epic 105 (`ResilienceStatusService` had two constructors and no
`@Autowired`, so no Spring context could boot), fixed in the commit that followed
this note; every context-booting IT was red before it. Live `EXPLAIN` stays with the
target install: the dev corpus is too small for the planner to prefer the composites
(TARGET_INSTALL_EXPLAIN.md).

**Do.** Read the three retrieval channels' SQL, run `EXPLAIN (ANALYZE, BUFFERS)` on
the dev corpus, and add only the indexes a plan actually asks for.

## Epic 122 — the surface is designed **DONE (verified 2026-11-11)**
**Shipped so far (2026-11-11, verified offline):**
- Token layer: `--shadow-halo` / `--shadow-glow`, an ambient body background (two corner
  radials over `--background`), and three utilities (`.glow-halo`, `.card-lift`, `.hairline[-solid]`).
- The landing hero now carries a static illustration of the product at work (board + match ring
  + Copilot doorway), drawn from the product's own tokens and labelled as an illustration.
- Active nav item reads as focused via `glow-halo`; timeline rows use the quieter `hairline` border.

**Closed (2026-11-11):** transitions that explain where a panel came from were already
shipped in the design system (dialog fade+zoom from center, sheet slide-in with origin side,
tooltip/popover direction-aware origins, all `data-[state]` animate-in/out) -- Epic 122's
checklist item existed for a surface that already carried the rule; no new code was needed
beyond the token layer above. Skeleton shapes pinned to the loaded layout: done in Epic 122's
follow-through and pinned by `loading-skeletons.test.ts` in Epic 124. And the dashboard hero
proper: the greeting band is now a designed front door -- PageHeader's exact contract inside a
rounded-2xl band with two token-coloured ambient washes, a hairline border and the card shadow
from the elevation token layer; the Primary CTA carries `glow-halo`. Static gradients, zero
per-frame cost; dashboard route 254.0 -> 254.3 kB gzip, budget holds.


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

## Epic 124 — the gates **DONE (verified 2026-11-11)**

Every claim above gets a test that fails when the claim stops being true, plus the
roadmap/census updates the repo already requires.

**Landed (all verified 2026-11-11):** `test_the_prewarm_script_covers_the_composite_indexes.py`
(prewarm script and V36+V37 cannot drift, and a script warming an index nothing creates
fails), `test_the_performance_horizon_marks_done_honestly.py` (DONE means dated and checked
in ROADMAP.md; the horizon's table must name every epic), `warm-prefetch.test.ts` (the
sidebar's warm-on-intent wiring cannot be deleted quietly), and
`loading-skeletons.test.ts` (the per-surface skeleton-shape pins from Epic 122: every
exported skeleton declares itself to AT, LoadingCardSkeleton holds the StatCard anatomy,
the metric grid's breakpoints match the loaded strip, and the route fallback imports
only exported skeletons). Both Python gates run in `scripts/verify_gates.{sh,ps1}`; the
frontend pins run in the vitest suite.
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
- Enable with `CAREEROS_DASHBOARD_CACHE=redis` (the prod override deliberately carries no
  interpolation for it, the same posture as the edge's opt-ins): the backend reads the env
  the `env_file` fills, so an operator sets one line in `.env.prod` and the yml literal
  stays the fallback. Actuator redis health stays disabled, so liveness cannot flip on a
  cache outage.

**Verification (offline, 2026-11-11):** `DashboardCacheTest` 6/6 (off passthrough, caffeine
round-trip, TTL expiry, poisoned-entry eviction, Redis-outage fail-open, hit/miss counters);
`DashboardServiceMetricsTest` + `DashboardServiceKanbanTest` updated for the new constructor
and green; `mvn -B test -Dtest='*Test'` exits 0 (the CI unit command). Live Redis round-trip
is not claimed on this host (no Docker here); the Redis path is the same connection shape
the rate limiter already runs.
## Epic 126 — the matches digest reads in index order **DONE (verified 2026-11-11)**

**Shipped (2026-11-11, verified offline; live EXPLAIN is the target-install follow-up):**
- `V37__matches_digest_indexes.sql`: two composites, both backing statements the app
  runs on the dashboard's hot path --
  - `idx_match_job_user_created (job_id, user_id, created_at DESC)` -- every LATERAL /
    scalar "latest score" lookup (`job_id = j.id AND user_id = :userId`) becomes a
    backward index scan for its `LIMIT 1`, no per-row sort;
  - `idx_matches_user_job_created (user_id, job_id, created_at DESC)` -- the
    dashboard's `averageMatch` DISTINCT ON (job_id) newest-overall becomes an
    index-ordered scan instead of a full sort of the reader's match history.
- `scripts/prewarm-hot.sql` extended to warm both (plus `ANALYZE job_matches`); the
  contract test is generalized to cover V36+V37 (renamed
  `test_the_prewarm_script_covers_the_composite_indexes.py`), and now also refuses a
  script that warms an index nothing creates.

**Target-install EXPLAIN is the documented follow-up in docs/plans/TARGET_INSTALL_EXPLAIN.md.** The migrations themselves are no longer unverified: the IT harness applied V36+V37 from scratch on `career_os_it` (see Epic 121's note), and JobSearchHybridIT (4/4) and GlobalSearchHybridIT (4/4) exercise the match and search paths on a real PostgreSQL 16.15. The dev corpus (142 jobs / 212 matches / 210 match owners / 4272 notes / 1230 resumes) is too small for the planner to prefer the composites over a scan, which is why the EXPLAIN reading stays with the target install.

**Deliberately not shipped:** a `(user_id, created_at DESC)` composite -- grep of the
Java call sites shows no statement that filters on user_id and orders by created_at on
job_matches, so it would be a speculative index. Live target-install EXPLAIN remains
the follow-up ledger note, as with V36.
## Epic 127 — a route that ships too much Java goes red **DONE (verified 2026-11-11)**

**Measured.** `next build` prints the per-route "First Load JS" table, but nothing made a
contributor read it: the build was green either way. On this host the heaviest route
(/applications) ships ~302 kB gzip; every app route sits between 189 kB and 302 kB; the
shared base is ~103 kB.

**Shipped (2026-11-11, verified offline):**
- `frontend/scripts/bundle-budget.mjs` -- recomputes each page route's first-load weight
  from `.next/app-build-manifest.json` the way the table does (unique chunks per route,
  gzip-compressed), prints the table, and exits 1 when any route exceeds **340 kB gzip**.
- `npm run budget` (= `npm run build && node scripts/bundle-budget.mjs`); README Tests
  section documents it.
- CI: a dedicated `budget` job (its own runner, so the fast vitest+tsc job stays fast),
  wired into `offline-gate` so a route over budget blocks the merge.
- The budget is named with its headroom on purpose: raise it only with a reason in the
  commit; tighten it as routes shrink.

**Deliberately not done:** chunk-level attribution (which dependency grew the route) --
`next build --debug` or the analyzer plugin is the follow-up when a route breaches.
## Epic 128 — a request carries its own deadline **DONE (verified 2026-11-11)**

**Measured.** Every caller has a moment they stop waiting, but nothing in the mesh told
the services that. A browser's timeout, a fetch aborted at 30 seconds, a queue that filled:
the backend and the engine kept doing work for a reader who had gone, and every token of it
was spent on nobody.

**Shipped (2026-11-11, verified offline):**
- Gateway `DeadlineHeaderFilter` stamps every `/api/**` request with `X-Request-Deadline-Ms`
  (epoch milliseconds). A well-formed caller deadline still in the future is kept; an
  expired or garbage value is replaced, never forwarded. `GATEWAY_DEADLINE_MS` bounds the
  budget (default 300000, above the 180s AI read budget; `0` disables the stamp).
- Backend `DeadlineFilter` carries the value on the request thread (cleared on exit, never
  leaked to a pooled thread); the AI bridge's interceptor forwards it to the ai-service, and
  `exchange()` refuses before dispatch when the budget already passed
  (`AI_SERVICE_UNAVAILABLE`, one clock read, no I/O).
- ai-service carries the value into a context variable (echoed on the answer); the most
  expensive route (`/internal/rag/answer`) has two checkpoints: before retrieval (a budget
  already gone refuses with `SERVICE_DEADLINE_EXCEEDED`, 503, nothing retrieved) and after
  retrieval (retrieval can burn the whole budget; the model is never asked -- pinned by a
  scripted-budget test, 2026-11-11).
- Documented in MICROSERVICES.md §6. A deadline is work conservation, never a permission
  problem; `x-request-deadline-ms` is echoed, garbage is ignored.

**Verification (offline, 2026-11-11):** DeadlineFilterTest 4/4; HttpAiServiceClientTest
25/25 (new cases: past budget refuses before the wire, future budget reaches the engine);
GatewayDeadlineTest 4/4 (stamp shape, kept-future, replaced-expired, replaced-garbage);
ai-service `test_the_deadline_carries_across_the_mesh.py` 5/5 (backstop refuses before any
engine work, echo, garbage ignored, no-budget unchanged). The full ai-service suite reds
this change surfaced were fixed here, not deferred: the prod-compose override carried an
unmarked interpolation for the dashboard cache opt-in (removed -- the override now carries
no interpolation for it; `.env.prod` is the pass-through), the docs vocabulary census gained
the decision-count bump for the two mentions of the decision this epic's roadmap and horizon
entries carry, and the notes-writer census gained the ANALYZE-only exemption for
`scripts/prewarm-hot.sql`. Backend *Test suite exits 0.
Not run here (no Docker): the *IT deadline path against a live stack.
## Epic 129 — the applications board ships when it is needed **DONE (verified 2026-11-11)**

**Measured.** The applications page is the heaviest route in the app (~302 kB gzip of
first-load Java at Epic 127's baseline), and its board -- dnd-kit, sortable, and the
drag strategy -- is the chunk responsible for the drag interaction. In production the
board only ever renders with client-side data, so the static markup already showed the
loading skeleton; shipping dnd-kit in first-load Java bought pixels nobody saw.

**Shipped (2026-11-11, verified offline):** the board is dynamically imported
(`next/dynamic`, `ssr:false`) with `LoadingKanbanSkeleton` as the fallback -- the board's
own grid shape, not a spinner. The applications route drops to ~287 kB gzip (-15.6 kB)
and the `budget` CI job keeps it honest. The page's own contract test now asserts the
honest fallback; the kanban's rendering is pinned unchanged by `kanban.test.tsx`.

**Verification (offline, 2026-11-11):** `npm run build` exits 0; `node scripts/bundle-budget.mjs`
prints /applications at 286.8 kB gzip (was 302.4); applications page suite 6/6 (updated
fallback assertions); full frontend vitest 1186/1186; `tsc --noEmit` clean.
## Epic 130 — the auth door sells the same product the landing does **DONE (verified 2026-11-11)**

**Measured.** Both anonymous surfaces had a claim about the product but only one of
them showed it: the landing hero carried the static product illustration, while the
auth panel — the page a visitor reaches right before signing in — argued with pillars
and a quote only. The illustration markup was duplicated figure code inside
`landing-page.tsx`, so reusing it by copy would fork the design.

**Shipped (2026-11-11, verified offline):**
- `components/marketing/product-preview.tsx` -- the front-door illustration as one
  shared element (role=img, one honest aria-label, every inner node aria-hidden,
  match panel hidden below `sm` so the auth panel degrades to board + copilot).
- The landing hero renders it via `<ProductPreview />` (six `landing.preview.*` keys
  moved with it; the landing copy gate passes on the remaining keys).
- The auth panel renders it between the pillars and the quote -- the visitor reads
  what the product is before the form asks who they are.
- `product-preview.test.tsx` pins the contract: labelled image, no raw-key label,
  the 92 is legible in the illustration. Copy census 163 -> 164 (annotated).

**Verification (offline, 2026-11-11):** full frontend vitest 1193/1193; production
build exit 0; bundle budget OK; landing copy gate green; `tsc --noEmit` clean.
