"""Epic 174 — a deterministic model call served from Redis costs zero provider calls.

The gateway's prefix cache cannot help a prompt whose fixed prefix is below the
gateway's minimum cacheable size (measured live: a ~150-token system prefix came
back with `cached_tokens: 0` on every call). Those calls — `jd_analyze`,
`resume_parse`, `reply_classify`, `gap_analysis`, `rerank`, `memory_extract` — are
temperature-0 requests for identical work when the input is identical, so the
exact-match cache serves them without a model at all.

What this file measures, in the house style, is the *number of provider calls*, not
a stopwatch reading:

* the second identical call makes no provider call;
* a different input, a different json_mode, a non-zero temperature or a call that
  asks for tools is a different call, and the model is asked;
* a tool-calling reply is never stored -- a replayed "the model wanted to act"
  would never act;
* caching off (the default) changes nothing;
* telemetry reports the replay honestly: the full prompt as cached tokens at zero
  marginal cost, and the trace names where the answer came from.
"""

from __future__ import annotations

import pytest

from app.core import ai, cache as cache_mod, llm_cache
from app.providers.base import LLMMessage, LLMRequest, LLMResponse, ToolCall, ToolSpec, Usage
from app.providers.pricing import estimate_cost


class CountingProvider:
    name = "counting"

    def __init__(self, text="ok", tool_calls=None):
        self.model = "gpt-test-1"
        self.calls = 0
        self.text = text
        self.tool_calls = tool_calls or []

    async def complete(self, req: LLMRequest) -> LLMResponse:
        self.calls += 1
        return LLMResponse(
            text=self.text,
            tool_calls=list(self.tool_calls),
            usage=Usage(input_tokens=4242, output_tokens=17, cached_tokens=0),
            model=self.model,
            latency_ms=120,
            finish_reason="stop")


@pytest.fixture
def cached(monkeypatch):
    provider = CountingProvider()
    monkeypatch.setattr(ai, "get_llm", lambda s: provider)
    cache_mod.install_cache(cache_mod.MemoryCache(max_entries=64, ttl=300))
    yield provider
    cache_mod.install_cache(cache_mod.NullCache())


@pytest.fixture
def uncacheable(monkeypatch):
    provider = CountingProvider()
    monkeypatch.setattr(ai, "get_llm", lambda s: provider)
    cache_mod.install_cache(cache_mod.NullCache())
    yield provider
    cache_mod.install_cache(cache_mod.NullCache())


def req(prompt: str, *, temperature=0.0, json_mode=False, tools=None) -> LLMRequest:
    return LLMRequest(messages=[LLMMessage("system", "sys"),
                                LLMMessage("user", prompt)],
                      temperature=temperature, max_tokens=64,
                      json_mode=json_mode, tools=tools)


def tool_spec() -> ToolSpec:
    return ToolSpec(name="search_jobs", description="x",
                    parameters={"type": "object", "properties": {}})


async def ask(prompt: str, **kw) -> LLMResponse:
    return await ai.ask(req(prompt, **kw))


async def test_the_second_identical_deterministic_call_makes_no_provider_call(cached):
    first = await ask("analyze this jd")
    assert cached.calls == 1
    second = await ask("analyze this jd")
    assert cached.calls == 1, "the replay still asked the model"
    assert second.text == first.text


async def test_the_replay_reports_the_whole_prompt_cached_at_zero_marginal_cost(cached):
    cached.model = "gpt-4o-mini"
    await ask("hello")
    replay = await ask("hello")
    assert replay.usage.cached_tokens == replay.usage.input_tokens == 4242
    assert replay.usage.output_tokens == 17
    assert replay.latency_ms == 1
    # a replay is a cache hit over the whole prompt, which the provider prices at
    # cached tokens; the priced cost of this call must be below an uncached one
    cost = estimate_cost(replay.model, replay.usage.input_tokens,
                         replay.usage.output_tokens, replay.usage.cached_tokens)
    assert cost < estimate_cost(replay.model, replay.usage.input_tokens,
                                replay.usage.output_tokens, 0)


async def test_a_different_message_is_a_different_call(cached):
    await ask("jd one")
    await ask("jd two")
    assert cached.calls == 2


async def test_the_key_covers_json_mode(cached):
    await ask("same words", json_mode=True)
    await ask("same words", json_mode=False)
    assert cached.calls == 2


async def test_a_temperature_that_is_not_zero_is_never_replayed(cached):
    await ask("same words", temperature=0.3)
    await ask("same words", temperature=0.3)
    assert cached.calls == 2


async def test_a_call_that_asks_for_tools_is_never_replayed(cached):
    await ask("same words", tools=[tool_spec()])
    await ask("same words", tools=[tool_spec()])
    assert cached.calls == 2


async def test_a_tool_calling_answer_is_never_stored(cached):
    cached.tool_calls = [ToolCall(id="1", name="search_jobs", arguments={})]
    await ask("same words")
    await ask("same words")
    assert cached.calls == 2, "a replay of 'the model wanted to act' never acts"


async def test_an_empty_reply_is_never_stored(cached):
    cached.text = ""
    await ask("same words")
    await ask("same words")
    assert cached.calls == 2


async def test_with_caching_off_every_call_asks_the_model(uncacheable):
    await ask("same words")
    await ask("same words")
    assert uncacheable.calls == 2


async def test_content_with_quotes_newlines_and_emoji_round_trips(cached):
    messy = "quote \" and \\ backslash\nnewline 中 \U0001f600"
    await ask(messy)
    replay = await ask(messy)
    assert cached.calls == 1
    assert replay.text == "ok"


async def test_oversized_reply_is_not_stored(cached, monkeypatch):
    cached.text = "x" * 512
    monkeypatch.setattr(llm_cache, "_MAX_VALUE_BYTES", 64)
    await ask("big")
    await ask("big")
    assert cached.calls == 2


async def test_the_trace_names_where_the_answer_came_from(cached, monkeypatch):
    traced: list[dict] = []

    async def spy(run_id, kind, agent, payload):
        traced.append(payload)

    async def no_record(*a, **kw):
        return None

    monkeypatch.setattr(ai.observability, "trace", spy)
    monkeypatch.setattr(ai.observability, "record_usage", no_record)
    await ai.ask(req("same words"), run_id="run-1")
    assert len(traced) == 1
    assert traced[0].get("served_from") is None
    await ai.ask(req("same words"), run_id="run-1")
    assert len(traced) == 2
    assert traced[-1].get("served_from") == "exact_cache"
    assert traced[-1]["latency_ms"] == 1


async def test_ask_json_replay_does_not_reparse_the_world(cached):
    cached.text = '{"a": 1}'
    first_req = req("return the json", json_mode=True)
    first = await ai.ask_json(first_req)
    assert cached.calls == 1
    second = await ai.ask_json(first_req)
    assert cached.calls == 1
    assert second == first
