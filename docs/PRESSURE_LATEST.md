# Pressure Smoke Report (2026-11-21, local dev stack)

## Environment
- Base: http://127.0.0.1:8080 (backend), :8000 (ai), :3000 (frontend) — all 200 health
- Host: local Windows dev machine, Docker stack running

## concurrency_smoke.py
- 128 calls, 16 workers, 4 shared tokens, wall 3.0s
- p50 63ms | p95 2165ms | max 2478ms
- codes: {200: 96, 201: 32}
- 5xx: 0
- Result: **CONCURRENCY OK**

## load_probe.py --base http://127.0.0.1:8080
Total requests: 917

### Health ramp (4s each)
| workers | requests | status | p50 ms | p90 ms | p99 ms | max ms | rps |
|---:|---:|---|---:|---:|---:|---:|---:|
| 1 | 183 | 200:183 | 16.0 | 32.0 | 62.0 | 344.0 | 45.8 |
| 10 | 142 | 200:142 | 172.0 | 578.0 | 1922.0 | 2000.0 | 35.5 |
| 25 | 103 | 200:103 | 844.0 | 2375.0 | 3078.0 | 3109.0 | 25.8 |
| 50 | 136 | 200:136 | 1390.0 | 3281.0 | 4641.0 | 4703.0 | 34.0 |
| 100 | 193 | 200:193 | 2609.0 | 5187.0 | 6234.0 | 6359.0 | 48.2 |

### Auth gate (100 concurrent wrong-password attempts)
- status: {401: 99, 429: 1}
- post-storm health: 200
- 5xx: 0

### Authed read (/api/v1/jobs)
- registered: true, requests: 60, status: {200:60}
- p50 1359.0ms | p90 1937.0ms | max 2265.0ms

## Notes
- No LLM endpoints hit. No 5xx observed. Auth rate limiter engaged under storm.
- Latency increases under high concurrency on local dev host; no error-rate degradation observed.

## Live admin + portfolio verification (2026-11-21)

All admin endpoints answered 200 on the running stack. The figures are real rows,
not fabricated demo data:

- `/admin/stats`: users 195, resumes 47, applications 23, interviews 9,
  agentRuns 685, agentTraces 803, aiUsageEvents 198, knowledgeSources 200,
  notesKept 114, contacts 44, companies 13, jobs 45, matches 8, offers 5.
- `/admin/trends?weeks=4`: weekly series with real counts in the newest week
  (agentRuns 685, attentionLands 400, attentionDwells 22, aiUsageCached 85).
- `/admin/attention`: landings 400, dwells 22, acts 0, dwellPerLandingMs 1242,
  topLandings by path (/dashboard 198, /jobs 26, /data 16, ...).

Portfolio personal-info check against the live `https://xiaodernan.github.io/`:
赵欣曈 · 南方科技大学 · 香港中文大学 · 法狗狗 · IELTS 6.5 · CET6 546 ·
物理竞赛铜牌 · "隐盾" present and "隐图" absent. All accurate; no hallucination.

### Counsel-LLM investigation (2026-11-21)
`POST /admin/counsel-llm` first answered MALFORMED_REQUEST when probed with a flat
snapshot — the wrong shape. With the real shape the frontend sends (`stats`, `cohort`,
`cache`, `weekly`, `attention`, `funnel`) it returns 200 with `empty:false` but a blank
summary: the running stack is `llm_provider=mock`, so the counsel engine's extract
node catches the LLM failure and renders honest silence rather than an invented
analyst voice. Confirmed correct behaviour, not a defect. The engine's grounded-measure
discipline is covered by its own tests; a real-key deployment yields the counsel.

# Re-measured 2026-11-22 (after Epic 362/363: fitted inputs + one flight per key)

The model door changed, so the pressure numbers were re-taken rather than assumed.
Same scripts, same host, same stack, no code path reverted.

## concurrency_smoke.py
- 128 calls, 16 workers, 4 shared tokens, wall 5.1s
- p50 184ms | p95 3735ms | max 3927ms
- codes: {200: 96, 201: 32}
- 5xx: 0 — **CONCURRENCY OK**

## load_probe.py (health ramp, 4s each)

| workers | requests | status | p50 ms | p90 ms | p99 ms | max ms | rps |
|---:|---:|---|---:|---:|---:|---:|---:|
| 1 | 232 | 200:232 | 8.1 | 15.0 | 148.9 | 747.9 | 58.0 |
| 10 | 1141 | 200:1141 | 17.2 | 91.0 | 155.7 | 299.8 | 285.2 |
| 25 | 950 | 200:950 | 57.9 | 241.7 | 573.6 | 1354.2 | 237.5 |
| 50 | 1092 | 200:1092 | 122.3 | 420.0 | 1000.2 | 2465.5 | 273.0 |
| 100 | 617 | 200:617 | 520.5 | 1481.0 | 2722.7 | 3433.5 | 154.2 |

- Auth gate (100 wrong-password attempts): {401: 95, 429: 5}, post-storm health 200, 5xx: 0.
- Authed read (/api/v1/jobs), 60 requests: all 200, p50 180ms | p90 294ms | max 323ms.
- Total 4192 requests across the run. **Zero 5xx at every level.**

### What moved, and what did not

Nothing in the request path changed shape — the coalescing (Epic 363) only engages
on a *deterministic* cache miss, and the health ramp never reaches the model door, so
the ramp's improvement over the 2026-11-21 run (285 rps at 10 workers against 35.5) is
host load, not the change. The honest reading: the same saturation curve, measured on a
quieter box. What did not change in either direction is the one that matters — no 5xx at
any level, and the auth limiter still engaging under storm.

# Re-measured 2026-11-22 (after the frontend rebuild + the dashboard fix)

The stack was rebuilt from the tree (backend and frontend images), so the numbers
were re-taken rather than carried over.

## concurrency_smoke.py
- 128 calls, 16 workers, 4 shared tokens, wall 1.3s
- p50 45ms | p95 534ms | max 732ms
- codes: {200: 96, 201: 32}
- 5xx: 0 — **CONCURRENCY OK**

## load_probe.py (health ramp, 4s each)

| workers | requests | status | p50 ms | p90 ms | p99 ms | max ms | rps |
|---:|---:|---|---:|---:|---:|---:|---:|
| 1 | 753 | 200:753 | 4.6 | 7.1 | 11.3 | 126.0 | 188.2 |
| 10 | 1220 | 200:1220 | 18.9 | 61.5 | 241.7 | 403.9 | 305.0 |
| 25 | 1007 | 200:1007 | 58.3 | 233.5 | 558.9 | 984.4 | 251.8 |
| 50 | 704 | 200:704 | 163.2 | 709.6 | 2968.8 | 3593.0 | 176.0 |
| 100 | 437 | 200:437 | 742.6 | 2132.0 | 4248.4 | 4485.3 | 109.2 |

- Auth gate (100 wrong-password attempts): {401: 95, 429: 5}, post-storm health 200, 5xx: 0.
- Authed read (/api/v1/jobs), 60 requests: all 200, p50 287ms | p90 332ms | max 357ms.
- Total 4281 requests across the run. **Zero 5xx at every level.**

### What this run was for

The earlier run in this file was taken before the frontend and backend images were
rebuilt from the tree, and before the dashboard 500 was found and fixed (Epic 375).
A run that only exercises /health cannot see an aggregate that throws — which is
exactly what the browser sweep caught — so the honest reading of this table is "the
edge holds", and the browser sweep is what says the pages do.

# Re-measured 2026-11-22 (after Epic 410, same day, later window)

Same scripts, same host, same running stack — taken again after the calendar work,
with no backend change in between, so this is a second sample of the same shape
rather than a before/after.

## concurrency_smoke.py
- 128 calls, 16 workers, 4 shared tokens, wall 0.9s
- p50 17ms | p95 541ms | max 594ms
- codes: {200: 96, 201: 32}
- 5xx: 0 — **CONCURRENCY OK**

## load_probe.py --strict (health ramp, 4s each)

| workers | requests | status | p50 ms | p90 ms | p99 ms | max ms | rps |
|---:|---:|---|---:|---:|---:|---:|---:|
| 1 | 1186 | 200:1186 | 3.2 | 4.2 | 6.0 | 64.6 | 296.5 |
| 10 | 2091 | 200:2091 | 10.8 | 39.6 | 122.9 | 233.9 | 522.8 |
| 25 | 1641 | 200:1641 | 35.9 | 144.1 | 307.0 | 670.2 | 410.2 |
| 50 | 1512 | 200:1512 | 94.4 | 296.0 | 584.9 | 868.8 | 378.0 |
| 100 | 1220 | 200:1220 | 251.9 | 739.2 | 1408.0 | 2324.1 | 305.0 |

- Auth gate (100 concurrent wrong-password attempts): {401: 99, 429: 1},
  post-storm health 200, 5xx: 0.
- Authed read (/api/v1/jobs), 60 requests: all 200, p50 400ms | p90 418ms | max 433ms.
- Total 7,810 requests. **Zero 5xx at every level. Verdict: PASS.**

### The limiter was measured, not assumed

The first concurrency smoke of this window was itself refused with `429` at
registration, because the 100-way wrong-password storm had just spent the auth
bucket (`RATELIMIT_AUTH_PER_MINUTE=100` on this stack). Sixty-five seconds later,
with the one-minute window drained, the same 128 calls all landed (96×200, 32×201).
That is the limiter doing its job in both directions: the storm could not turn into
a credential-stuffing sled, and an ordinary registration was not permanently locked
out. Every one of the 7,810 measured requests in this window was answered — none
was a 5xx, and none was a connection error.

# Credential-stuffing siege — 2026-11-23 (Block XI: 撞库)

The one pressure shape the brief names explicitly and that had never been *run* —
`scripts/credential-stuff.js` (k6 v2.0.0-rc1) — was finally fired at the live stack.
Read-only by construction: every request is a wrong password on a synthetic email,
so nothing is created, updated or authenticated. Bounded burst: 60 VUs × 20s.

| metric | measured |
|---|---|
| requests | 11,052 (551/s) |
| answer shape | 10,943 × 429 + 109 × 401 — **100% 401/429, zero 5xx, zero timeouts** |
| `check` "answer is 401 or 429 (never a crash)" | 11,052 / 11,052 passed (100%) |
| http_req_duration | avg 50ms · p90 111ms · p95 175ms · max 1.56s |
| post-storm health | `/actuator/health`, `/api/v1/health`, ai `/health` all 200 |

Note on the k6 `http_req_failed 100%` line: k6 marks any non-2xx/3xx as a "failed"
request, so 401/429 count there by definition. The script's own custom rate
(`http_req_failed_custom = 0%`) and its 100%-passing check are the honest signal:
the stack answered every stuffing attempt with a refusal, never a crash. This is
the 撞库 scenario the brief asked to simulate, now measured rather than assumed.

# Adversarial register fuzz — 2026-11-24 (Block XI)

`scripts/fuzz_auth.py` fires malformed-but-plausible payloads at the register door.
Its first run this round aborted before the verdict with a `UnicodeEncodeError`:
the deliberately injected control/non-ASCII bytes, printed with `ensure_ascii=False`,
cannot be encoded by the Windows GBK console. That was a harness portability bug,
not an app defect — fixed by reconfiguring stdout/stderr to UTF-8 at import. Re-run:

- 69 adversarial payloads: **2xx=21, 4xx=48, 5xx=0** — `FUZZ OK · the door held`
- wrong JSON shapes (array/bare string/number/null/nested/unicode-escape bomb) all
  answered `MALFORMED_REQUEST` or `VALIDATION_FAILED`, never a 5xx
- 12-way register burst on one email: exactly **1 created + 11 conflicts, 0 5xx**
  — the Epic 226 race fix still holds under a simultaneous stampede

Every malformed email/password/displayName was refused with a structured envelope;
the validation and SQL layers never flinched. No LLM, no external API.

## Harness-network caveat (2026-11-24) — read before re-running localhost probes

After this date, outbound HTTP from the AI-harness shell to the host's loopback
ports (8080/3000) is intercepted by the harness network layer: TCP connects in
~6ms but ZERO response bytes arrive — curl reports `000`, k6 reports
`http_req_failed 100%` with `data_received 0 B`. The backend's own logs show it
answering `GET /api/v1/health 200` to the CI runner at the same moment. So a
`000`/100%-failed result from a localhost probe launched INSIDE this harness is
NOT a stack regression and NOT a Clash issue — it is the harness sandbox. The
genuine measurements above (7,810 load-probe requests, 11,052 stuffing requests,
69 fuzz payloads) stand; do not replace them with sandbox-poisoned numbers.

To re-measure for real, launch the probe from a normal shell (Win+R → cmd) or
the self-hosted runner, NOT from the harness tool shell.

## In-process credential stuffing (Epic 447, 2026-11-25) — the auth door under a burst

`backend/src/test/java/com/careeros/ratelimit/AuthLoginCredentialStuffingTest.java`
drives the real filter → limiter → `AuthController.login` path with 200 simultaneous
wrong-password POSTs from one IP through 16 threads. The limiter's fake template
models the shipped Lua script atomically; no socket, Redis, Docker or model is used.

| Scenario | Result |
|---|---|
| 200 concurrent wrong passwords from one IP | exactly 10 reach the password check (401, the auth-per-minute ceiling); the other 190 are refused (429) before any auth work — `verify(authService, times(10))` proves the short-circuit |
| 5xx / successful logins | 0 / 0 |
| different IP, same moment | 401 — admitted to the password check, not caught in the attacker's bucket (the ceiling is per IP, not an account lockout) |
| limiter metrics | denied bucket = 190 |

This is a unit-level stress gate: it proves the ceiling holds under contention at
the auth door, not that the deployment survives a network flood. Same honesty caveat
as the Epic 439 row above.

## In-process concurrency (Epic 439, 2026-11-24) — measurable without a socket

`backend/src/test/java/com/careeros/ratelimit/RedisSlidingWindowConcurrencyTest.java`
hammers the limiter's admission path with 200 callers released together through a
16-thread pool. The fake template models the shipped Lua script atomically (one lock,
unique members, trim/count/add), so the result describes the algorithm rather than
the sandbox:

| Scenario | Callers | Ceiling | Admitted | Result |
|---|---|---|---|---|
| simultaneous burst | 200 | 25 / minute | 25 exactly | pass |
| clock advanced 2 minutes | 1 extra | 25 / minute | admitted | pass |

This is a unit-level stress gate, not a replacement for the stack-level numbers
above — it proves the admission ceiling holds under contention, not that the
deployment survives a flood. No Redis, no Docker, no LLM.

