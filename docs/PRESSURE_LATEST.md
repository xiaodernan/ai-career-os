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
