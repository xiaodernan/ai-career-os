# Why your cache rate report looked bad — and what the code did wrong

You said the cache rate on live calls was low and streaming must be doing something
better. Two real bugs were hiding behind the numbers, one in the route that ran most.

## The bug we fixed (Epic 173, `de532cf`)

**The streaming path never reported `usage`.**
OpenAI's streaming contract — and this gateway follows it — only includes `usage` in the
final frame when the caller asks for it with
`stream_options: {"include_usage": true}`. Without it, the stream completes, the
`llm_call` trace event carries `text_preview` only, and `ai_usage_events` writes
`cached_tokens = 0` and `cost_usd = 0.00` for every streaming call the copilot and the
SSE face made. So the table said "every streaming call was free and uncached", while the
gateway had always been reporting it — it just wasn't being read.

Fixed: the payload is `stream_options: {"include_usage": true}`; `PRICING` gained
`gpt-6-sol` so cost stops silently printing `$0.00` for the exact model the stack runs.

Attestation: `test_a_real_model_reports_the_cache.py` — three `complete()` and two
`stream()` calls on one loop against the real gateway; asserts the second identical
round reports `cached_tokens > 0`. `1 passed in 14.7s` at this tree (2026-11-13).

## Why most one-shot calls still show a low cache rate — honest answer

OpenAI's gateway cache matches **identical byte prefixes** across calls. The prefix has
to repeat, above a minimum length, for the cache to fire. For the vast majority of this
stack's workload it cannot:

| Kind | 26 days | cache hit | why it is low |
|---|---:|---:|---|
| `jd_analyze` | 12 | 21.8% | each JD is unique — the entire user payload differs every call, so the prefix before the unique content is short |
| `match_narrative` | 4 | 5.3% | a single JD + single resume per call; no shared prefix beyond a few sentences |
| `query_understanding` | 14 | 13.6% | the user's question differs every call |
| `resume_parse` | 26 | 48.2% | the résumé is re-used across iterations of the same document, so the prefix warms up quickly |
| `memory_extract` | 19 | 31.4% | each conversation tail differs |
| `answer_eval` | 5 | 0.0% | one-shot by design |
| `interview_advance` | 5 | 0.3% | each answer is unique; only the shared instructions match |

**Streaming looked better but the cause was not that streaming is faster** — it was
that the copilot's streaming call reuses one ~6k-token shared prefix (system + memory
context + the full tools catalogue) across turns of one conversation. Steps 4–6 in the
aggregate show 98–99% cache hits. The cache fires because the *conversation prefix is
identical each turn*, not because the provider treats streaming specially.

## Verified against the live gateway (this tree)

```text
identical prompt, three sync rounds:
    cached=0 (ms 2906) → cached=6006 (ms 2093) → cached=6386 (ms 1687)

identical prompt, three stream rounds (with the fix):
    cached=0 (ms 2953) → no-usage → cached=6381 (ms 2327)
```

Feature calls re-asked with the same JD:

```text
jd_analyze (identical JD, four rounds)
    cached=0  prompt=4453 cached=0   ms=3969
    cached=0  prompt=4453 cached=0   ms=3530
    cached=97% prompt=4453 cached=4352 ms=3266
    cached=97% prompt=4453 cached=4352 ms=5733
```

This gateway needs roughly ≥ ~1024 prefix tokens before the cache fires. Small system
prompts — every one-shot in this stack has one — never cross it alone; the user payload
is the long part and it differs.

## What you can see yourself

```text
docker exec careeros-postgres psql -U career_os -d career_os -c \
  "SELECT kind, count(*) calls, sum(cached_tokens) cached, sum(input_tokens) in_,
         round(100.0*sum(cached_tokens)/nullif(sum(input_tokens),0),1) pct
   FROM ai_usage_events WHERE provider='openai_compat'
   GROUP BY kind ORDER BY calls DESC"
```

Every number in the tables above came from that query on the running install, or from a
live probe of `wkapi.pro` at this tree.

## What this leaves open (honest boundary)

- Feature calls that differ per call cannot be improved by caller code. The lever is
  their pipeline: re-using a parsed JD across features amortizes a ~1k-input-token
  call that every feature the user opens the same JD for currently pays for again.
- The prefix cache matches a long *identical byte* prefix. The suffix layout is
  already correct (short stable instructions first, the unique user payload at the
  end); no further prefix shuffling would produce a hit that the gateway declines
  to give for short-prefix feature prompts. The next honest lever is fewer calls,
  not warmer ones — and that lever is what Epic 174 built.
- No deployed environment in this tree runs with the fleet queue enabled. That
  switch belongs to your call as the operator; nothing in this file changes it.

## Epic 174 — the deterministic calls stop paying twice (measured 2026-11-13)

The remaining cache miss was workload-shaped, not a bug: every one-shot feature
call carries a unique user payload, and its fixed system prefix is far below the
gateway's minimum cacheable block. Those calls *are* identical work when the input
is identical — so this tree now replays them instead of re-billing them.

**What was built** — `app/core/llm_cache.py` in ai-service, wired into `core/ai.py`'s
`ask()`:

- only `temperature == 0.0` and only calls that ask for no tools;
- the key hashes the model, the full message list, `max_tokens` and `json_mode` —
  a hit is a verbatim replay, never a paraphrase;
- stored answers live in the cache backend the operator already chose
  (`CACHE_BACKEND`; dev now runs `redis` — layered memory+Redis —, prod ships `off`,
  unchanged); a cache that is down is a miss, never a raised error — `NullCache`
  counts a miss and the model is asked, exactly as before;
- a reply larger than 256 KB or carrying tool calls is never stored — a replayed
  "the model wanted to act" would never act;
- telemetry is honest: a replay is recorded with the full prompt as cached tokens,
  `$0.00` cost, ~1 ms latency, and the `llm_call` trace event carries
  `served_from: "exact_cache"` so a dashboard counting cached tokens sees the number
  for what it is.

**Measured** — `tests/test_the_second_identical_deterministic_call_is_free.py`
13/13 (counts provider calls, never times them): the second identical call makes
zero provider calls; a different message, a different `json_mode`, a non-zero
temperature or a requested tool ask the model every time; a tool-calling answer and
an oversized answer are never stored; Unicode round-trips byte-exact; the replay
reports `cached_tokens == input_tokens`. Live on the dev stack (rebuilt
`careeros-ai`, `CACHE_BACKEND=redis`), 2026-11-13:

```text
jd_analyze, identical JD, two posts
    run 1: 16733ms  in=4930 cached=0    cost=0.003190
    run 2:   141ms  in=4930 cached=4930 cost=0.000000   (replay; ~119x faster)
jd_analyze, a *different* JD, next call
                      in=18926 cached=0  cost=0.008380   (fresh, as it must be)

the same user's health report, straight off the live route
    totalRuns: 2 · totalTokens: 10824 · totalCachedTokens: 4883
    cacheHitRatio: 0.5 · totalCostUsd: 0.0028 · verdict: healthy
```

The second identical post answers in 141 ms because there is no model in the loop;
a *first* miss always pays full price, a *hit* is priced at $0 by construction, and
the replay is recorded in `ai_usage_events` exactly once, as observed above.

## Epic 175 — the dashboard shows the number (and the cards work at all)

The monitoring page was rendered off the top level of a payload that never had
anything at the top level. The backend returns `{summary, regressions, alerts,
verdict}` (the engine's own shape), while `useHealthReport` cast that straight
onto the flat `HealthReport` view model — so every card read its fallback
(0 tokens, $0.00, "—" latency) and only the verdict badge rendered. Proven against
the live route on this tree before the fix (raw JSON quoted below), then fixed end
to end:

- the engine's `summarize_runs` now also reports `totalCachedTokens` and
  `cacheHitRatio` (cached ÷ input tokens); `cacheHitRatio` joins the regression
  checker as a lower-is-worse metric, so "the cache stopped firing" becomes an
  alert instead of a silent decay;
- the backend now sends `cached_tokens` per run into the engine, and the report is
  built from a named literal (`_health_report_document`) the contract census walks;
- the frontend gained `normalizeHealthReport`, which unwraps exactly the shape the
  endpoint returns — pinned by `normalize.test.ts` (169 tests) and the
  response-field census (54 mappers, 16 named reads);
- the page shows two new tiles (cache hit rate, prompt tokens saved) and a
  prompt-cache explainer card, which states plainly which calls the prefix cache
  can and cannot fire on.

The raw wire observed on this tree before the fix:

```json
{"success": true, "data": {"summary": {"totalRuns": 0, "errorRate": 0.0,
  "latencyMs": {"p50": null, "p95": null, "max": null},
  "totalCostUsd": 0.0, "totalTokens": 0}, "regressions": [],
 "alerts": [], "verdict": "healthy"}}
```

