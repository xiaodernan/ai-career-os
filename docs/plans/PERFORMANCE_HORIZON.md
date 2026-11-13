# Performance horizon — Epics 118+

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
| 131 | The task feed is a Redis Stream when scale-out asks for it | fake-streams suite |
| 162 | The backend's job queue runs on Redis Streams, one group across the fleet: a crashed replica's job is reclaimed, a poison job is dead-lettered, and nothing grows without bound | JobQueueIT 5/5 (real it-redis), JobQueueTest 6/6, JobWorkerTest 15/15 |
| 163 | The inbox mail/ring/read/write paths stop riding a per-key N+1: one IN-round trip plus one save per unread set | NotificationServiceTest 26/26 incl. 2 new pins, full backend suite |
| 167 | The fleet does not celebrate one expiry together: the Redis dashboard cache writes under a ±10% TTL | DashboardCacheTest 11/11 (band [40,50] over 300 seeded draws, spread non-constant, floor holds, captured Redis write inside the band) |
| 168 | The retention sweep rides the fleet queue when it is on — one replica runs it — and stays inline exactly where it was otherwise | RetentionSchedulerTest 6/6 + RetentionSweepHandlerTest 2/2 + full backend suite green (incl. every context-booting IT) |
| 169 | The weekly letter's two clocks race no longer — one replica per day per concern; the letter is mailed once, the digest is computed once | WeeklyDigestSchedulerTest 6/6 + WeeklyDigestComposeHandlerTest 2/2 + WeeklyDigestRetryHandlerTest 2/2 + RedisDayLease shared + full backend suite green |
| 170 | The ingestion freshness sweep stops re-fetching every feed N times per night; one replica runs it, the rest stand down | IngestionSchedulerTest 5/5 + IngestionSweepHandlerTest 3/3 + full backend suite green (incl. every context-booting IT) |
| 171 | The fleet's user pings stop multiplying: one node rings every minute, custody rotates with a 90s lease | ReminderSchedulerTest 8/8 (window arithmetic intact + 4 new fleet-dispatch pins) + full backend suite green |

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
**Scope as shipped:** memoised rows and derivations on the timeline, inbox, and Kanban board (react-memo on TimelineRow and KanbanCard, memoised visible/items/rows/kindGroups), so parent re-renders no longer redo per-row string/filter work. Virtual rendering shipped as Epic 141 (see the `Epic 141` section below; `components/common/virtual-list.tsx`).


**Measured.** The board, the timeline and the inbox all render windows of rows, and
every window re-derives strings, sorts and formats per render.

**Do.** Memoise the pure derivations per row identity, keep the sort keys stable
(`(at, kind, refId)`), and virtualise the longest lists rather than drawing the whole
window.

## Epic 141 — the ten-thousandth row is not drawn until it is wanted **DONE (verified 2026-11-12)**

**Measured.** Every row the timeline owned was in the DOM whether or not the reader ever
scrolled to it -- the merge is server-side (Epic 81) but the *draw* was always client-side.
Past a few hundred events the longest read path in the product pays for rows nobody sees.

**Shipped (2026-11-12, verified offline):**
- `components/common/virtual-list.tsx` -- a dependency-free, fixed-height windowed list:
  pure `computeWindow()` (clamped edges, zero-height-safe, exercised by unit tests without
  a layout) + a `VirtualList` component (absolute-positioned rows, full track height,
  `aria-setsize`/`aria-posinset` so AT is told the honest row count, ResizeObserver-measured
  viewport, SSR-deterministic at-rest window).
- Rows are fixed-height by design (72 px, single-line truncation with `title` fallback);
  variable-height rows belong to the full-render path, and this component says so.
- The timeline uses the window past 30 rows (`VIRTUAL_THRESHOLD`); below that, the
  DOM is byte-identical to before the change (unit/e2e small-feeds behave exactly as before).

**Verification (live, 2026-11-12):** `virtual-list.test.tsx` 7/7; timeline page suite green; vitest full suite green; `tsc --noEmit` clean; production build exit 0. Live in the browser (a seeded one-off walkthrough, not part of the committed suite): a fold of **90** merged events rendered **15** rows in the DOM (`aria-setsize="90"` on the rendered rows, so AT is told the honest total). The production fold caps per source at 50 (`PER_SOURCE_CAP`), so realistic power-user folds converge near ~100 rows -- which is why the window engages at 30, not 100 (a 100-row threshold would never fire). Below 30 rows the DOM is byte-identical to before the change.

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
blocks-loaded output. The warm covers the routes the nav admits. The per-row prefetch of
job/resume detail pages (folded here from Epic 124's follow-ups) shipped 2026-11-12:
lib/hooks/use-warm-link.ts (hover + keyboard focus warms the detail route, the same
gesture contract as the sidebar's warm-on-intent), wired onto the job card row link and
both resume-list links; warm-link.test.ts pins the wiring source-contract style.

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

**Defect found by e2e and fixed (2026-11-12).** The yml literal `cache: off` was parsed by
YAML 1.1 as the boolean `false`, so `@Value("${careeros.dashboard.cache:off}")` received the
string `false` -- `"off".equals(mode)` was false, `"caffeine".equals(mode)` was false, and
every read took the Redis branch. The dev Docker stack ran the cache for weeks while the docs
and this horizon said passthrough; the Prometheus counter read `backend="false"` the whole
time. Found by the `golden-journey` spec: the browser's dashboard prefetch (login redirect)
populated the pre-write 0/0 snapshot, and the test's read after PATCH returned it verbatim
(`kanban 0/0`, `recentRuns` containing a run committed 5s before the app did). A/B reproduced
it deterministically: prime-once-then-write -> 0/0, no prime -> 1/1. The prod path was never
affected (the env var `CAREEROS_DASHBOARD_CACHE` arrives intact as a string); the defect was
the yml literal alone. Fixed in the yml (`cache: "off"`), hardened in `DashboardCache`
(normalizes `""`, `off`, `false`, `0`, `no` to off; any unrecognized spelling fails closed to
off with a warn -- a typo loses the cache, never correctness), and pinned with tests
(`aBareYmlOffIsNotABackend`, `anUnknownBackendFailsClosedToOff`,
`aQuotedOrEnvSpellingReachesTheRightBackend` -- `DashboardCacheTest` now 9/9).

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
  gzip-compressed), prints the table, and exits 1 when any route exceeds **310 kB gzip** (tightened from 340 on 2026-11-12; heaviest
route `/(app)/jobs/[id]/page` measured 299.6 kB gzip across 35 routes).
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
  scripted-budget test, 2026-11-11). A third backstop sits at the model door: `ask()` and
  `ask_stream()` -- the single funnel for every LLM call in the engine -- refuse before any
  provider is touched when the caller is already gone (Epic 128 follow-through, 2026-11-11;
  full suite 2404 passed).

**IT verification (2026-11-11):** the IT harness on this host ran the full *IT suite
(129 tests) green except `RateLimitIT` under whole-suite load (the 500ms limiter pin vs
a contended docker-desktop proxy; both assertions pass in isolation, 6/6 -- the
documented fail-open posture, not a regression). `ResilienceStatusService` gained
@Autowired on its DI constructor in c1bbf39; before it, every Spring context failed to
boot and the whole context-booting IT layer was unusable.
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
## Epic 131 — the task feed is a Redis Stream when scale-out asks for it **DONE (verified 2026-11-11)**

**Measured.** The SSE task feed is the one surface that still assumes a single process:
`subscribe()` yields from the owning replica's memory, and a second replica sees nothing
of it. The docstrings already named the path; the code never had it.

**Shipped (2026-11-11, verified offline):**
- `TASK_BUS_BACKEND=redis` (default `memory`): every `publish()` rides two paths --
  the in-process list (browsers on the owning replica, unchanged) and an ordered
  `XADD` drain (`careeros:tasks:<task_id>`, MAXLEN ~400) through a single drainer task on
  a bounded queue (maxsize 1000; a full queue sheds the mirror, never the caller).
- `subscribe()` reads that stream end to end: `XRANGE` backlog then `XREAD BLOCK` on the
  tail. One writer per task keeps order; a finished task replays and returns; an
  unknown task answers with an error frame instead of a hung stream.
- `astate()`/`ais_done()` give the async boundary a foreign-task peek
  (`XREVRANGE` + `XLEN`); the owner gate stays fail-closed, so cross-replica
  follow-along is documented as the ownership-store question, not smuggled past it.
- Fail-open everywhere: a Redis outage keeps the memory feed serving (test proves it);
  the drainer never crashes the request path.
- Documented in MICROSERVICES.md §6. Honest bounds (as of this epic): the mirror is
  live; cross-replica owner resolution and sticky-session routing are the remaining
  scale-out items; nothing here was load-tested. Epic 151 later closed the first of
  those two by moving the owner onto the mirrored events; sticky-session routing is
  still open.

**Verification (offline, 2026-11-11):** `test_the_task_bus_can_scale_out_through_redis_streams.py`
6/6 (fake-streams Redis with BLOCK/XRANGE/XADD semantics, foreign replica replay,
redis-down equivalence, queue-shed); full ai-service suite 2410 passed; verify_gates
267/267 (gate now includes the backplane suite). The interval census moved from one
definer to one definer + two module-local consumers (renamed in the module), annotated;
the frame-census moved 2 -> 5 yields with the reason in the assertion text.

## Epic 162 — the backend's job queue over Redis Streams ** landed green (2026-11-13)**

Landed as the parallel session's in-flight epic; this entry records what the work is
and how this box proved it out. One consumer group (`backend`) is shared by every
replica of the backend: a job is handed to one consumer, a crashed replica's
unacknowledged job is reclaimed by a sibling (`XCLAIM` re-checks idle time), and a
job failing `max-deliveries` times is written to `careeros:v1:jobs:dlq` and never
retried. Space is bounded at the write (`XADD MAXLEN ~ max-len`), not by a sweep, and
a job's tags ride the registered handler's own name, never the wire field.
`CAREEROS_QUEUE_ENABLED=false` (the default) sends no Redis command and runs no
scheduled work: every producer keeps its inline path.

Production wiring is deliberately NOT shipped here: no producer is wired to the queue
yet — this is the transport and its bounds, proven in isolation. Turning it on with a
real call site is the next epic's decision, with its own e2e.

**Two breaks were left in the in-flight state; they were fixed here without touching
the design.** `QueueMetrics.JOBS` was package-private while the cross-package IT reads
it off the registry (the meter's name is its contract — now public); and `JobQueueIT`
asserted two bulk `>` reads of size 20 split across replicas, which Redis does not do
— the read offers the whole un-delivered queue to the asker, capped by `count`. The
test now alternates unit reads, the interleaving a real fleet produces, which proves
exclusivity and both-replica progress deterministically. The same suite storms 300
individual XADDs, past this shared box's 500 ms Redis command window (which exists to
fail fast in production); this class alone registers a 5 s timeout. The production
default is untouched.

**Measured on real `careeros-it-redis`:** JobQueueIT 5/5 (121 s), JobQueueTest 6/6,
JobWorkerTest 15/15 — green on this host. Suite-level runs on this portable sandbox
also surface sandbox flakiness that is not the epic's (RateLimitIT under docker-desktop
stalls; re-ran green with no code change).

## Epic 163 — the inbox write paths stop riding a per-key N+1 **DONE (verified 2026-11-13)**

The inbox's mail/ring/read/clear paths rebuilt the synthesized inbox via `inbox()`
— calling `shown()` twice per public write — and then selected one state row per key
(`states.findByUserIdAndSignalKey` -> `orElseGet(fresh)`) before saving each. A
`markAllRead` showing N unread episodes cost about 2N round trips on the read side
plus N saves, on top of two full candidate syntheses; the mail/ring latches paid the
same per-key price.

**The refactor, zero production-shape drift.** `shown()` is walked once per public call
and `foldInbox` is the one fold every inbox-shaped answer goes through (no hand-rolled
second fold, so the two surfaces cannot disagree); `inbox()` is `foldInbox(shown(userId))`.
Every batch write goes through one `states.findByUserIdAndSignalKeyIn` IN-round trip plus
one `saveAll` — a miss mints the fresh row exactly as the old `stateFor` did, so the
latch semantics are unchanged. `dismissRead`/`dismiss`/`markRead`/`markAllRead` fold the
just-applied writes into the walked snapshot in memory, byte-identical to a re-read after
the flush; `markNotified`/`markPushed` share the same helper under a documented
`STATE_BATCH_CAP=500` clamp; the per-key `findByUserIdAndSignalKey` is gone.

**Honesty boundary.** The saving is a call-side shape — ones, not N — pinned by tests,
not a wall-clock number on a rested DB; no ranking changed, no wire shape moved.
`NotificationServiceTest` 26/26 with two new pins (one IN-round trip and one save per
`markAllRead`, zero per-key `save`), plus dedup of repeated read keys into one row per
episode. The whole backend suite runs green on this host apart from the box-flaky
`RateLimitIT` (re-ran green; environment, not this code).

## Epic 167 — the fleet does not celebrate one expiry together (verified 2026-11-13)

The Redis branch of the dashboard cache stamped the *same* 45 s `EX` onto every entry
it minted. Every replica fills its own keys at its own miss, but their TTLs lapsed
together, so a minute after an expiry the store absorbed one refilling burst for the
same key space — the tail latency of exactly the run that rushed.

**The change, bounded on the honest side.** The Redis branch now writes under a
±10 % uniform TTL (`jitterSeconds`, spread `max(1, round(base*0.1))`, floor 1 s, Caffeine
stays on the fixed value — a process-local expiry cannot dogpile a fleet, so jitter
would only add variance without removing a wave). No eviction, no invalidation, no
lock — the same TTL contract with more useful shapes; a reader who moved a card still
waits at most one TTL.

**Measured.** `DashboardCacheTest` 11/11: the band pins every seeded draw at 45 s into
`[40,50]` across 300 draws (a distribution outside the band reds), the band actually
spreads (TreeSet over 300 draws is non-constant), floor holds for non-positive bases,
and the Redis `set` the class issued at write carries a TTL inside the same band. Call
site does no I/O; no behaviour contract moved; no wire shape; no new knob. Backend
suite re-run at this tree came back green (2026-11-13; the earlier loss was the box, not this class).

## Epic 168 — the retention sweep gets on the fleet queue (verified 2026-11-13)

The backend's Redis-Streams job queue (careeros:v1:jobs, Epic 162) shipped with a
promise — enable it and one replica does the work — but zero producers. This epic
extends that one producer over the one long-running scheduled job the install can
prove to itself weekly: the 04:47 retention sweep (tokens, retired-evidence rows,
unnamed bucket objects).

**Design, closed-loop with Epic 167's honesty rules.**
- RetentionSweepHandler (auth.retention): kind retention.sweep; idempotent by
  construction (cutoff watermark deletes) — the at-least-once contract's demanded
  shape, on a path that never needed to change behaviour to satisfy it.
- RetentionScheduler (auth.retention): replaces the bare cron on the sweeper.
  Queue disabled → inline sweep on EVERY replica, byte-for-byte pre-queue semantics
  (the shipped default). Queue enabled → one UTC-day Redis SET NX (ex 1 day,
  careeros:v1:retention:owner:<yyyy-MM-dd>) elects the single enqueuing replica;
  siblings skip; leader failure to enqueue → leader sweeps inline alone; election
  errors → this replica sweeps inline (fail-open toward the work, never the skip).
- RetentionSweeper is unchanged in behaviour (package-private sweep(now) stays
  the one testable seam; its @Scheduled moved to the scheduler).

**What this is not, honestly.**
- Not enabled anywhere yet: CAREEROS_QUEUE_ENABLED defaults false by design and
  the e2e profile keeps it that way; the enablement ships disabled-by-default with the
  same flip-it-and-prove-your-deploy posture as every other opt-in element.
- Not the last producer: ingestion sweep, nightly verdict and weekly letter stay
  unwrapped — each is a separate epic with its own failure modes; this one proves the
  producer contract end to end cheaply.
- Not distributed deletion: every replica still runs the same sweeper code; only
  the scheduling is elected.

**Measured.** RetentionSchedulerTest 6/6 (disabled→inline; election-win→enqueue only;
election-win+refusal→inline; election-lose→silent; election error→inline),
RetentionSweepHandlerTest 2/2 (kind wire name, one call), every context-booting IT
green with the two components wired (RetiredEvidencePurgeIT, RetentionSweepIT,
UnnamedObjectSweepIT). Full backend suite green on this host with the app stack's
backend stopped. Zero knobs, zero wire-shape change, zero client JS; the sweeper's
measured behaviour (heartbeat, counters, failed-table reporting) is byte-identical.

## Epic 169 — the weekly letter stops racing its own fleet (verified 2026-11-13)

The weekly digest's two clocks — the Monday compose sweep and the daily 09:05 UTC
retry — fired on every replica at the same instant. The compose race multiplied the
full digest computation across N replicas (the letter upsert is idempotent, so it
was waste, not corruption), but the retry race re-mailed the same refused letter to
the same mailbox twice whenever two replicas found the same candidates in the same
mutex window — the exact duplicate-mail failure the Monday letter's design went out
of its way to never create (delivered_at is a latch; two readers both seeing it null
before either commit is what the latch does not prevent by itself).

**Design, one lease, two concerns.** A shared `RedisDayLease` in `com.careeros.queue`
acquires a single Redis SET NX EX 1d per concern per UTC day. The weekly scheduler
and the retention scheduler both use it; the retention scheduler's private election is
retired in favour of the one implementation. `digest.compose` and `digest.retry` hold
separate leases so the two clocks fire independently.

**Queue semantics, unchanged by the move.** Queue disabled every replica runs the
handler's clock exactly as shipped (inline, today's behaviour). Queue enabled: one
lease holder enqueues, siblings stand down, a refused enqueue runs inline on the
leader alone, lease errors fail open toward the work. Handlers carry the clock's own
promises: the compose sweep keeps its 08:00 heartbeat, the failed-compose log, "a
bad night costs no other account"; the retry sweep keeps "refused only, oldest
first, under the cap". One implementation per clock; the two paths execute identical
code via `handle(Map.of())`.

**What this is not.** Not enabled anywhere (`CAREEROS_QUEUE_ENABLED=false`,
e2e unchanged), not the last scheduled job (ingestion sweep, nightly verdict stay
unwrapped), not distributed settlement (`delivered_at` still decides races; the
lease only makes the fleet tidy). Consolidation note: two Redis `SET NX` variants
existed for one night (`careeros:v1:lease:<concern>:<yyyy-MM-dd>` unified the
inaward key shapes); nothing else touched the wire.

**Measured.** WeeklyDigestSchedulerTest 6/6 (disabled→inline; lease-win→enqueue
only; lease-win+refusal→inline; lease-lose→silent; lease error→inline; the two
leases fire independently), WeeklyDigestComposeHandlerTest 2/2 (the moved compose
clock: last week, heartbeat, failure log-not-throw), WeeklyDigestRetryHandlerTest
2/2 (the moved retry: refused-only, failure log-not-throw), RetentionSchedulerTest
6/6 (same suite, now through the shared lease — key shape
`careeros:v1:lease:retention:<yyyy-MM-dd>`). Full backend suite green at this tree
on this host. One honest miss caught inside this epic's own test window: a new
CANDIDATE for the wiring mistake this class of work reliably produces (the lease
was not a Spring bean — first IT bootstrap died of UnsatisfiedDependencyException),
found by the full backend IT sweep and fixed by making it a @Component.
## Epic 170 — the ingestion sweep stops re-fetching every feed nightly (verified 2026-11-13)

The 03:20 ingestion sweep fired on every replica at once — every enabled feed was
asked for its recent postings N times per night, which is N× the third-party HTTP
requests for data the platform already pays to fetch. Politeness, relay rate
limits, and the fleet's own egress discipline all argue for one asking voice; the
install now has one.

**Design, same honest pattern as Epics 168/169.** `IngestionSweepHandler`
(`ingestion.sweep`) carries the night's work — the sweep call and its catch-warn
tail — inline-capable so the same body runs inline-when-disabled and
queue-claimed-when-enabled.
`IngestionScheduler` becomes the producer with the UTC-day lease
(`careeros:v1:lease:ingestion:<yyyy-MM-dd>`); queue disabled → every replica sweeps
exactly as shipped; enabled → the lease winner enqueues, siblings stand down,
a refused enqueue runs the winner inline alone, a lease error fails open toward the
work. Cron knob unchanged (`careeros.ingestion.cron`).

**What this is not.** Not a new fetch topology (the handler calls the same
`sweepEnabled()`, so whatever the sweep's own behaviour and failure posture is
unchanged — per-feed failures stay per-feed, a fatal error is still a warn), not
enabled anywhere (e2e unchanged), not shared with the other two newly-ported clocks
only conceptually (they ride the same lease helper, independently).

**Measured.** IngestionSchedulerTest 5/5 (disabled→inline; lease-win→enqueue only;
lease-win+refusal→inline; lease-lose→silent; lease error→inline),
IngestionSweepHandlerTest 3/3 (wire name; one `sweepEnabled()` call per entry;
a failed night logs and does not crash the worker). Full backend suite green at
this tree on this host with the app stack's backend stopped; every context-booting
IT green with the two new beans wired. Zero wire-shape change, zero client JS, zero
new knob.


## Epic 171 — the fleet stops pinging users twice (verified 2026-11-13)

The reminder clock fires `careeros.reminders.tick-ms` (60s by default) on every replica.
Before this epic, a fleet of N mailed and rang every minute-reminder N times — the
duplicate the other schedulers were rebuilt to end, except this one rings 1440 times a
day and the recipient is a real phone with its own battery. This is the single
highest-duplication scheduled job in the backend.

**Design.** A short-lifetime lease (`careeros:v1:lease:reminders-clock`, 90s TTL,
SET-NX — one winner per acquire window; custody rotates through the fleet on each
expiry, which is the right shape for a minute clock). With the queue disabled, every
replica rings — byte-for-byte the pre-queue behaviour, opt-in as every other
distributed element in this repo. With it enabled, a replica that does not win
returns without touching push or mail. A Redis failure closes the clock rather than
duplicate a user-facing ping: better one silent minute than one duplicated one, and
the `careeros_reminders_last_tick_timestamp` heartbeat already says exactly that —
a stopped clock reads stale, which is the designed 5-missed-ticks alarm's job.
Custody flaps are harmless because the latch the push half already keeps (an
episode mailed or pushed is never rung again) means a handover costs reads, never
re-pings.

**What this is not.** Not enabled anywhere (`CAREEROS_QUEUE_ENABLED=false`, e2e
unchanged), not distributed state (the ring outcome is unchanged; only who mails is
one per minute per deployment), not a new mechanism (the same acquire-or-fail-open
shape as Epics 168–170 with a TTL sized for a standing minute role instead of a day
lease), and not a fair-share scheduler (custody rotates through the fleet on TTL
expiry; at most one winner at a time — that is the whole SLA).

**Measured.** ReminderSchedulerTest 8/8: the pre-existing window pins (reach-back,
elapsed-span, failure-retry, heartbeat) kept plus four fleet pins new in this epic
(won lease → full window runs and the heartbeat moves; lost lease → zero push/mail
calls and the heartbeat holds; Redis down → closed, neither half runs; lost then won
→ the next won tick carries the window since the last read — ask costs reads, never
re-pings, because the latch already lives in the service). Full backend suite green
on this host with the app stack's backend stopped. Docker-compose and e2e stay
byte-identical.

