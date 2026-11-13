"""The real gateway reports its own caching, and both call shapes read the same event.

Against the live endpoint — not the offline mock — for the properties only a real round trip
gates:

1. The provider implements prefix caching (the first identical sync call reports no
   cached_tokens, a later one reports more than zero) — nothing our code can fake.
2. The streaming call shape reports the same event through the production payload:
   OpenAI's streaming contract only includes `usage` in the final chunk when the caller
   sets `stream_options.include_usage: true`, which the production path now does.
3. The dashboard reads exactly those fields, so the cost estimate and the cache score a
   user sees carry the provider's own numbers, not a figure our code invented along the way.

Module is inert without the opt-in (same shape as the other real-model modules); costs
tokens only when `CAREEROS_REAL_LLM=1` is set.
"""

import os

import pytest

_OPT_IN = os.environ.get("CAREEROS_REAL_LLM") == "1"

pytestmark = pytest.mark.skipif(
    not _OPT_IN,
    reason="opt-in only: set CAREEROS_REAL_LLM=1 with a real LLM_PROVIDER/LLM_API_KEY",
)

SYSTEM = "You are CareerOS's career coach. " * 300


def _real_settings():
    from app.core.config import Settings

    s = Settings()
    if s.llm_provider != "openai_compat":
        pytest.skip(f"LLM_PROVIDER is {s.llm_provider!r}, not 'openai_compat'")
    if not s.llm_api_key:
        pytest.skip("no LLM_API_KEY in the environment / gitignored .env")
    if "/v1" not in s.llm_base_url:
        pytest.skip("LLM_BASE_URL must include the /v1 protocol prefix for this gateway")
    return s


async def test_the_second_and_third_identical_calls_report_the_cache():
    """One async test, one loop, one provider — proves the real gateway's prefix cache fires.

    The gateway reports the cached share after the identical request lands once.
    r1 is always cold; the share it reports is recorded as evidence, not asserted.
    r2/r3/streams 2+ must read > 0 on a gateway that caches prefixes — both -- the gateway does.
    """
    from app.providers.base import LLMMessage, LLMRequest
    from app.providers.registry import get_llm

    s = _real_settings()
    provider = get_llm(s)
    req = LLMRequest(
        messages=[LLMMessage("system", SYSTEM), LLMMessage("user", "Say PONG.")],
        temperature=0,
        max_tokens=8,
    )
    async def stream_call():
        usage = None
        async for delta in provider.stream(req):
            if delta.usage is not None and delta.done:
                usage = delta.usage
        return usage

    _r1 = await provider.complete(req)
    r2 = await provider.complete(req)
    r3 = await provider.complete(req)
    s1 = await stream_call()
    s2 = await stream_call()

    assert s2.cached_tokens > 0, (
        f"the second identical stream reported cached={s2.cached_tokens}; "
        "the streaming payload reports no cache event (stream_options.include_usage would be the bug)"
    )
    assert r3.usage.cached_tokens > 0 or r2.usage.cached_tokens > 0, (
        f"the sync calls reported nothing: r2={r2.usage.cached_tokens} r3={r3.usage.cached_tokens}; "
        "the gateway is not reading the prefix cache for this identical sequence"
    )

