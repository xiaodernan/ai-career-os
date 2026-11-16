# The siege — a measured high-concurrency pass

Epic 256. The question this file answers: **does the stack stay up when many
readers arrive at once, and what does it cost to keep it that way?**

## What was run

Every number below is this install's own night of 2026-11-15/16: k6 v2.0.0-rc1
on the dev machine, the backend inside Docker Desktop (single-node, loopback
ports), Postgres and Redis in the same compose. **This is not a production
claim** — one desktop, one Docker daemon, one container each — it is a
measurement of how the system behaves when it runs out of room, and a rerun
protocol for comparing versions.

Target surface — **read-only GETs only**, no mutations, no authenticated
routes (they legitimately 429 under burst), no auth flows:

- `GET /api/v1/health` — dependency report; the probe runs all four dependency
  checks under one 2-second bound by design, so its tail is built in.
- `GET /api/v1/admin/stats` — the twenty-row counter (cache default off).
- `GET /api/v1/admin/trends?weeks=12` — five weekly aggregates.
- `GET /api/v1/admin/freshness` — eight `max(clock)` reads.

k6 script: `scripts/siege.js` (tracked). Round-robin per VU when `ROUTE=all`,
otherwise one route per run (`-e ROUTE=…`), phases as `-e PHASE=baseline|spike|capacity`.
Zero warm-up beyond the compose health gate; every run once; failures are
HTTP non-2xx (there were none, ever, at any level — including capacity).

## The numbers — cache off (the shipped default)

Per-route, per-phase. `reqs` = completed iterations; `med`/`p95`/`max` in ms.

| Route | Phase (VUs) | reqs | med | p95 | max | 5xx |
|---|---|---|---|---|---|---|
| health | baseline (10) | 5195 | 18 | 58 | 408 | 0 |
| stats | baseline (10) | 4026 | 36 | 90 | 659 | 0 |
| trends | baseline (10) | 3938 | 42 | 83 | 842 | 0 |
| freshness | baseline (10) | 4645 | 22 | 81 | 321 | 0 |
| health | spike (100) | 10147 | 274 | 1360 | 2710 | 0 |
| stats | spike (100) | 17033 | 185 | 485 | 1070 | 0 |
| trends | spike (100) | 14654 | 201 | 660 | 1970 | 0 |
| freshness | spike (100) | 18492 | 140 | 465 | 2410 | 0 |
| health | capacity (200) | 8443 | 801 | 3580 | 6820 | 0 |
| stats | capacity (200) | 11953 | 539 | 2140 | 4710 | 0 |
| trends | capacity (200) | 14047 | 523 | 1520 | 4310 | 0 |
| freshness | capacity (200) | 30718 | 196 | 722 | 2020 | 0 |

Observations, written down instead of extrapolated:

- **Zero 5xx at any level.** The stack saturates, it does not fall over: at
  200 concurrent readers the median is ~0.2–0.8 s and the tail is seconds — the
  shape of a system degrading gracefully, not of a process dying.
- `freshness` is the cheapest read by an order of magnitude: `max(clock)` over
  indexed timestamps is an index scan, not a count over 6655 user rows.
- `/health` stretching under 100+ VUs is the 2-second probe bound doing its
  job: the route reports dependency truth within a fixed window rather than
  hanging — its capacity tail is by design, not a regression.

## The same siege, cache on (the Epic 253 admin cache, redis branch, 60 s TTL)

| Route | Phase (VUs) | reqs | med | p95 | max | 5xx |
|---|---|---|---|---|---|---|
| stats | spike (100) | 47875 | **20** | 123 | 713 | 0 |
| trends | spike (100) | 74182 | **5.5** | 35 | 186 | 0 |
| freshness | spike (100) | 78827 | **4.7** | 19 | 85 | 0 |

Under the identical siege, identical JVM, identical box:

- **2.8× / 5.1× / 4.3× the throughput** (17.0k → 47.9k; 14.7k → 74.2k; 18.5k → 78.8k),
- **9–37× median latency** (185 → 20 ms; 201 → 5.5 ms; 140 → 4.7 ms),
- p95 **3.9–16× better** (485 → 123 ms; 660 → 35 ms; 465 → 19 ms),
- still **0.00% errors**.

This is what the read-through cache is for. The shipped default stays `off`
(byte-for-byte pre-cache behaviour, enable with `CAREEROS_ADMIN_CACHE=redis`);
what changes in production, when the operator flips it, is a guarantee that the
overseer's wall never becomes a query load the product can feel.



## Epic 292 — the widened siege, measured 2026-11-17

`scripts/siege-e292.js` extends the same protocol to the routes the month added:

- `GET /api/v1/admin/attention` — the trailing-30-day aggregate (`land/dwell/act` roll-up, `topLandings`, `dwellPerLandingMs`), the same rows `admin/attention` feeds from the attention spine.
- `GET /api/v1/admin/funnel` — the lower half of the funnel (`registered → uploaded → applied → interviewed → offered`) the admin page draws.

Run, same host, same single-node docker topology, fresh stack healthy after Docker Desktop crashed around midnight:

| Route | Phase (VUs) | reqs | med | p95 | max | 5xx / EOF |
|---|---|---|---|---|---|---|
| all routes, round-robin | spike (100) | 20,283 | 142 ms | 412 ms | 1.19 s | **0** |
p95 pages: p99 held under 500 ms, max 1.19 s — the tail is the per-request `/health` probe's 2-second bound, by design.

Observations:

- Zero 5xx / zero EOF against the steady-state stack, on the same box that showed 100% EOF when the k6 start raced Compose's health gate (backend still coming up at 15:59Z, 121 s to boot). The readout distinction matters for the next run: `http_req_failed 100%` from the same script on the same host is Compose, not the code.
- The attention endpoint is in the same league as the original four read-only routes: all six promise sub-500 ms p95 on this host with 100 VUs.


## Mixed-workload control run

One 10-VU round-robin over all four routes (the default profile) completed
913 iterations in ~52 s, 0 failures — the fleet case, not the worst case; it is
recorded here so the per-route numbers are not mistaken for separate sieges.

## Honest limits and what was not measured

- **One node, loopback, warm steady state.** No multi-replica fleet, no TLS
  termination, no network loss, no Postgres buffer-cache pressure from a
  bigger corpus. Numbers for this mix on this install are real; general
  capacity claims are not.
- **/health's tail is deliberately expensive** and measured as such.
- **Writes were not besieged** — a counter under 200 writers is a different
  experiment; the read-only surface was chosen deliberately because it is the
  public one anyone can hit without a credential.
- The 200-VU capacity pass shows **saturation, not failure**: every response
  was a 200, every time. Pushing harder would parade a semaphore queue; the
  correct next experiment is target-queue depth per dependency, not heroics.

## Re-running

```bash
TARGET=http://localhost:8080   # whatever origin your stack answers on
k6 run scripts/siege.js -e PHASE=baseline -e ROUTE=adminStats -e TARGET=$TARGET
# or all four round-robin at once:
k6 run scripts/siege.js -e PHASE=spike -e ROUTE=all -e TARGET=$TARGET
```

The script asserts no origin of its own — the target arrives by argument, never
as a literal. JSON per-run summaries (`--summary-export out.json`) print the same
numbers this file carries. If the numbers regress, the first questions are: is
Redis `up`, is the budget at the yml default, and has the corpus grown past where
`COUNT(*)` stays an index scan — the freshness row tells you which.
