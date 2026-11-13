"""The platform preamble warms across capabilities on the live gateway (Epic 182).

The epic's claim, measured statistically: two DIFFERENT capabilities — a
jd-analyze-shaped call and a reply-classify-shaped call, different agent blocks,
different volatile content — share the ~1.3k-token platform preamble as their first
bytes, so a prefix-caching provider reports cached_tokens on warm rounds even
though nothing else about the request repeats.

Statistical, not per-round: this gateway load-balances requests across upstream
replicas, and a repeat only hits when it lands on the shard that holds the prefix.
`prompt_cache_key` (which the production path sends, stable per capability) exists
precisely to raise that affinity, and this probe measures how far it gets — the
assertion is that the majority of warm rounds hit, not that every round does; a
round that misses is the load balancer, not the calling method.

Opt-in (CAREEROS_REAL_LLM=1): costs a few thousand tokens on the real gateway.
"""

import os

import pytest

_OPT_IN = os.environ.get("CAREEROS_REAL_LLM") == "1"

pytestmark = pytest.mark.skipif(
    not _OPT_IN,
    reason="opt-in only: set CAREEROS_REAL_LLM=1 with a real LLM_PROVIDER/LLM_API_KEY",
)

ROUNDS = 6


def _real_harness():
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "ai-service"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from app.core.config import Settings
    from app.core.ai import stable_messages
    from app.providers.base import LLMMessage, LLMRequest
    from app.providers.registry import get_llm

    s = Settings()
    if s.llm_provider != "openai_compat":
        pytest.skip(f"LLM_PROVIDER is {s.llm_provider!r}, not 'openai_compat'")
    if not s.llm_api_key:
        pytest.skip("no LLM_API_KEY in the environment / gitignored .env")
    return get_llm(s), stable_messages, LLMMessage, LLMRequest


async def test_the_preamble_caches_across_capabilities():
    provider, stable_messages, LLMMessage, LLMRequest = _real_harness()

    analyze = LLMRequest(
        messages=stable_messages(
            "You analyze a job description. JSON only: {\"title\":\"\"}",
            LLMMessage("user", "<<<BEGIN UNTRUSTED JOB_DESCRIPTION>>>\n"
                       "Backend engineer, Java, Kafka, PostgreSQL. 5 years.\n"
                       "<<<END UNTRUSTED JOB_DESCRIPTION>>>"),
        ),
        temperature=0.0, max_tokens=40, cache_key="careeros:probe-analyze",
    )
    classify = LLMRequest(
        messages=stable_messages(
            "You classify a recruiter reply. JSON only: {\"intent\":\"\"}",
            LLMMessage("user", "<<<BEGIN UNTRUSTED RECRUITER REPLY>>>\n"
                       "Hi, are you available for a call next Tuesday?\n"
                       "<<<END UNTRUSTED RECRUITER REPLY>>>"),
        ),
        temperature=0.0, max_tokens=40, cache_key="careeros:probe-classify",
    )

    cold = await provider.complete(analyze)
    assert cold.usage.cached_tokens == 0, (
        "the first call is cold by definition; a cache report there means the "
        "gateway reused another tenant's request and this probe measures nothing")

    warm_same = [await provider.complete(analyze) for _ in range(ROUNDS // 2)]
    warm_other = [await provider.complete(classify) for _ in range(ROUNDS // 2)]
    hits_same = sum(1 for r in warm_same if r.usage.cached_tokens > 0)
    hits_other = sum(1 for r in warm_other if r.usage.cached_tokens > 0)
    total_hits = hits_same + hits_other

    print(f"\nprobe: same-capability warm hits {hits_same}/{len(warm_same)}, "
          f"cross-capability warm hits {hits_other}/{len(warm_other)}")
    for r in warm_same + warm_other:
        print(f"  cached={r.usage.cached_tokens} of {r.usage.input_tokens}")

    assert total_hits >= (ROUNDS - 1), (
        f"only {total_hits}/{ROUNDS} warm rounds hit: the shared prefix is not "
        "reaching the cache threshold, or the routing key is not being honored — "
        "both are engine bugs, not relay weather")
    assert hits_other >= 1, (
        "a different capability whose only shared bytes are the platform preamble "
        "must hit at least once across the rounds — the preamble is the whole claim")
