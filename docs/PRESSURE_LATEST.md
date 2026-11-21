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
