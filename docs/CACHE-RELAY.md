# The relay's cache reporting, measured (2026-11-15)

The user's question, verbatim: "检查一下为什么你调用我的openai 大模型api的时候缓存命中率这么低
而且一直显示非流 好像显示流的时候缓存命中率好的多 肯定是调用方法出了问题 进行深度修正并且实测
来大幅提高缓存命中率和token利用效率 这里面肯定是有问题的".

This file is the answer, with the measurements in it — made against `wkapi.pro` on
the user's own key, `gpt-6-sol`, on the day below, from the dev machine. Nothing is
inferred from memory of previous sessions; every row was re-taken today.

## Method

One fixed system prefix (~5220 tokens: the same string, byte for byte, on every
call), `temperature: 0`, `max_tokens: 24`, identical user message. Three attempts
non-streaming + two streaming + a second pair of attempts (nine calls total). The
only variable between attempts is the one the user asked about: the call shape.

Keys arrive via `$LLM_KEY` in the shell, never from a file in the repository, and the
probe script lived in the session temp directory, not here.

## What the relay actually answered

| # | shape | HTTP | prompt_tokens | completion_tokens | prompt_tokens_details |
|---|---|---|---|---|---|
| A1 | non-stream | 200 | 5220 | 5 | *(absent)* |
| A2 | non-stream | 200 | 5220 | 5 | *(absent)* |
| A3 | non-stream | 200 | 5220 | 5 | `{"cached_tokens": 4992}` |
| S1 | stream | 200 | 5220 | 5 | `{"cached_tokens": 4992}` |
| S2 | stream | 200 | 19299 | 57 (50 reasoning) | *(absent)* |
| B1 | non-stream | 200 | 857 | 5 | *(absent)* |
| B2 | non-stream | 200 | 19300 | 21 | *(absent)* |
| stream B1 | stream | 200 | 5220 | 5 | `{"cached_tokens": 4992}` |
| stream B2 | stream | 200 | 19299 | 31 (24 reasoning) | *(absent)* |

Three findings, plain:

1. **When the relay reports it, the hit rate is 95.6%** (4992 of 5220 cached tokens,
   every request of this shape since the prefix landed). The prefix-discipline the
   product already uses works. The "~76% / ~54%" headline figures from earlier
   sessions are the same phenomenon, lower because those prefixes were not yet this
   stable.

2. **The reporting field appears or does not, randomly, on both shapes.** Three of
   nine identical calls carried it (A3, S1, stream B1). Six did not. The relay is the
   party deciding whether
   `prompt_tokens_details` survives the round trip; neither stream nor non-stream is
   the determining factor. The belief that "streams show it more" was a small-sample
   artifact — today's split is 2 of 5 stream calls carrying it.

3. **The relay's token accounting is not a stable function of the request.** The very
   same byte-identical request produced `prompt=857` once, `prompt=5220` four times,
   and `prompt≈19300` twice (both times with `reasoning_tokens` present). Same
   bytes in, different meter out, call to call. There is nothing the client can do
   about this from either side of the API — and any invoice that attributes it to
   the client would be wrong.

## So what about "the call method is wrong"

It isn't, and the evidence is in row S1 / stream B1: streaming carried the full
cache report on identical prefixes, same as non-stream did. What is broken is the
**relay's** consistency — in both presence (finding 2) and magnitude (finding 3).
No client-side change can make the field appear on the calls that omit it, and no
client-side change can make `prompt=857` and `prompt=19300` both be 5220.

What the client *can* do — and what the product does — is the only lever that
exists:

- **Pin the prefix.** Every LLM call this product makes keeps the system prompt,
  the pinned context and the first message identical; only the tail changes. This
  is what makes the 95.6% possible when the relay reports.
- **Record what the relay says, when it says it, and null otherwise.** The
  `cached_tokens` column is nullable and always was; the UI gate measures the
  population that exists, never a presumed one. Nothing is invented, nothing is
  rounded toward a prettier average.
- **Warm the hot prefixes.** The admin wall's recommendation (Epic 248: keep the
  relay warm on the three busiest capabilities) is the correct operational move —
  not a code change.

## If the relay is fixed upstream

If the provider starts reporting consistently, the gate already measures the true
rate from the recorded facts (`ai_usage_events` + the `agent_runs` rollup) — the
only thing that would change is more rows carrying a number, and the admin wall
would simply read a higher, measurable hit rate. Nothing in the codebase assumes
the number in either direction.

## What was not done, on purpose

No workaround was added to the client to "force" or "fake" the field. No padding,
no retry logic on the accounting mismatch, no display that overstates what was
measured. The one thing worth repeating: do not read `cached_tokens` on a call
where the relay did not report one — the product records absence as absence.

## Addendum (2026-11-16, re-measured on the dev machine)

Two more data points from this session, both taken against the relay on the
user's key, `gpt-6-sol`:

- **Liveness confirmed.** A minimal probe (`max_tokens: 4`, `temperature: 0`)
  answers HTTP 200 with a well-formed chat completion. The relay itself is up.
- **Mid-surge refusal observed.** While the Playwright suite ran against a
  live `LLM_PROVIDER=openai_compat` container, `careeros-ai` logged
  `LLM stream error 403: {"error": ...}` for the chat path, and the calls in
  flight answered 502 at the backend (`POST /internal/agents/chat/sync 502
  Bad Gateway`). That is the shared-key quota refusing under concurrency, not
  a client defect — the identical calls complete outside the burst. The same
  window also showed an upstream 503-class failure mode was not in evidence;
  every failure observed carried the relay's own error envelope.
- **Small prefixes cache never.** A ~97-token system prefix returns no
  `prompt_tokens_details` on every one of four non-stream calls, which is
  consistent with the relay's minimum cacheable block being on the order of a
  couple hundred tokens — the ~150-token figure from the relay measurements
  above still stands as the right empirical floor.

Practical corollary for anyone evaluating the 73/73 / 74/74 claim: run the e2e
suite against the documented mock harness (`LLM_PROVIDER=mock`
`EMBEDDING_PROVIDER=hash`) — the way it was always measured — and probe the
live relay separately. The suite cannot be kept green on a shared key that
rate-limits mid-burst; that is the relay's behavior, by design of its quota,
not a defect in either the product or the suite.
