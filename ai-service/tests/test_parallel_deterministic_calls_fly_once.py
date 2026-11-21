"""Epic 363: two readers asking the same question in the same moment call once.

The exact-match cache (Epic 174) answers a repeated *deterministic* call from
Redis, but only after the first caller has already paid for it. Two parallel
sessions -- two readers pasting the same posting, two resumes parsing at once,
the same gap analysis requested twice by one impatient click -- both missed,
both called the relay, and both wrote the same answer. That is the "并行会话同时打
API 导致缓存互相干扰、命中混乱" the product was asked to stop doing, and it is
measurable: N callers, one model call, one piece of work.

The gate is behavioural, not structural: it drives the real entry point
(`llm_cache.get_or_produce`) with a provider that counts its calls and sleeps
long enough for the others to arrive, then asserts the count. The leader's
answer is the one stored, so the cache holds one answer rather than whichever
writer landed last.

Scope, stated rather than implied: this is per-process. The engine runs several
uvicorn workers, and two readers on two workers still both call once -- a
cross-process lock would need a Redis lease, which is a different trade. What
this removes is the duplicated call inside one worker, which is where parallel
sessions land.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from app.core import cache as cache_mod
from app.core import llm_cache
from app.providers.base import LLMMessage, LLMRequest, LLMResponse, Usage


def _req(text: str = "same question") -> LLMRequest:
    return LLMRequest(messages=[LLMMessage("user", text)], temperature=0.0)


class CountingProvider:
    """A relay that remembers how many times it was actually called."""

    def __init__(self, delay: float = 0.05) -> None:
        self.calls = 0
        self.delay = delay

    async def complete(self, req: LLMRequest) -> LLMResponse:
        self.calls += 1
        await asyncio.sleep(self.delay)
        return LLMResponse(text=f"answer to {len(req.messages)} messages",
                           model="probe-model",
                           usage=Usage(input_tokens=10, output_tokens=5))


class _ExplodingProvider:
    async def complete(self, req: LLMRequest) -> LLMResponse:
        raise RuntimeError("relay down")


def _with_memory_cache() -> cache_mod.Cache:
    """Turn caching on for a scenario, the way a configured install runs."""
    previous = cache_mod._cache
    cache_mod._cache = cache_mod.MemoryCache()
    return previous


def test_ten_parallel_readers_make_one_model_call() -> None:
    async def scenario() -> int:
        llm_cache._inflight.clear()
        provider = CountingProvider()
        req = _req()
        # Every caller misses the cache first (nothing stored yet), then all of
        # them race on the same key.
        results = await asyncio.gather(*[
            llm_cache.get_or_produce(req, "probe-model", lambda: provider.complete(req))
            for _ in range(10)
        ])
        assert all(r is not None for r, _ in results)
        assert all(cached is False for _, cached in results)
        # Every reader gets the same bytes, and only one call was made.
        texts = {r.text for r, _ in results}
        assert len(texts) == 1, f"the waiters were answered differently: {texts}"
        return provider.calls

    calls = asyncio.run(scenario())
    assert calls == 1, f"{calls} model calls were made for one question"


def test_a_second_wave_is_served_from_the_cache_the_first_wave_wrote() -> None:
    async def scenario() -> tuple[int, bool]:
        llm_cache._inflight.clear()
        previous = _with_memory_cache()
        try:
            provider = CountingProvider(delay=0)
            req = _req("another question")
            first, from_cache_first = await llm_cache.get_or_produce(
                req, "probe-model", lambda: provider.complete(req))
            # The leader wrote its answer back before returning, so the next
            # reader finds it without touching the relay.
            second, from_cache_second = await llm_cache.get_or_produce(
                req, "probe-model", lambda: provider.complete(req))
            assert from_cache_first is False and from_cache_second is True
            assert second.text == first.text
            return provider.calls, from_cache_second
        finally:
            cache_mod._cache = previous

    calls, cached = asyncio.run(scenario())
    assert calls == 1, "the second wave called the relay again"
    assert cached is True


def test_a_failing_leader_is_not_cached_as_an_answer() -> None:
    async def scenario() -> int:
        llm_cache._inflight.clear()
        req = _req("the question that fails")

        # A leader that fails must not leave a future behind that a later reader
        # would await as if it were an answer.
        raised = 0
        for _ in range(2):
            try:
                await llm_cache.get_or_produce(req, "probe-model", lambda: _ExplodingProvider().complete(req))
            except RuntimeError:
                raised += 1
        assert raised == 2, "the failure was swallowed for one of the callers"
        assert llm_cache._inflight == {}, (
            "a failed flight left an entry behind; the next reader would await it"
        )
        return raised

    assert asyncio.run(scenario()) == 2


def test_an_ineligible_request_is_neither_coalesced_nor_stored() -> None:
    """A tool call or a warm temperature is a decision, not a repeatable answer."""
    async def scenario() -> tuple[int, bool]:
        llm_cache._inflight.clear()
        previous = _with_memory_cache()
        try:
            provider = CountingProvider(delay=0)
            warm = LLMRequest(messages=[LLMMessage("user", "creative")], temperature=0.7)
            first, cached1 = await llm_cache.get_or_produce(
                warm, "probe-model", lambda: provider.complete(warm))
            second, cached2 = await llm_cache.get_or_produce(
                warm, "probe-model", lambda: provider.complete(warm))
            assert cached1 is False and cached2 is False
            assert first.text and second.text
            return provider.calls, cached2
        finally:
            cache_mod._cache = previous

    calls, cached = asyncio.run(scenario())
    assert calls == 2, "an unrepeatable call was served from the cache"
    assert cached is False
