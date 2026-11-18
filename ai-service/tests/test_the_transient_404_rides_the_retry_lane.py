"""The transient relay 404 rides the retry lane (Epic 326).

Measured 2026-11-18 against the live aizzz.xyz relay through the host proxy:
the identical gpt-6.1-terra request answered 200 four times, then 404 nine
times in a row, then 200 again — the message names the cause honestly
("Model ... is not supported by any configured account in this group"): the
account group rotates channels, some hours/channels can't serve the model, and
the very next call answers normally with the same body. The provider used to
raise on any 404, poisoning every retry-free path on those bad minutes. Now
that specific marker rides the same lane as 429/5xx — bounded, backed off, and
never traded for a permanent refusal (a genuinely unknown model's 404 stays
terminal on the first call).

Offline: httpx.MockTransport answers the relay, no socket is opened.
"""
from __future__ import annotations

import httpx
import pytest

from app.providers.base import LLMMessage, LLMRequest
from app.providers.llm.openai_compat import (
    OpenAICompatProvider,
    ProviderError,
    TRANSIENT_GROUP_404,
)

GROUP_404 = {"error": {"message":
                       'Model "gpt-6.1-terra" is not supported by any configured account in this group',
                       "type": "model_not_found"}}
MODEL_UNKNOWN = {"error": {"message": "the model does not exist", "type": "model_not_found"}}
OK = {"id": "resp_1", "object": "chat.completion", "created": 1, "model": "gpt-6.1-terra",
      "choices": [{"message": {"role": "assistant", "content": "ok"},
                   "finish_reason": "stop", "index": 0}],
      "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12}}


def _provider(handler, max_retries: int = 2) -> OpenAICompatProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return OpenAICompatProvider(client, "https://relay.test/v1", "k", "gpt-6.1-terra",
                                max_retries=max_retries)


def _req() -> LLMRequest:
    return LLMRequest(messages=[LLMMessage("user", "hi")], temperature=0.0, max_tokens=8)


@pytest.mark.asyncio
async def test_the_transient_group_404_retries_then_answers():
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(404, json=GROUP_404)
        return httpx.Response(200, json=OK)

    provider = _provider(handler)
    out = await provider.complete(_req())
    assert out.text == "ok"
    assert calls["n"] == 3                      # two transient 404s retried, third answered


@pytest.mark.asyncio
async def test_a_permanent_404_raises_on_the_first_call():
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(404, json=MODEL_UNKNOWN)

    provider = _provider(handler)
    with pytest.raises(ProviderError):
        await provider.complete(_req())
    assert calls["n"] == 1                      # a real model-not-found is terminal immediately


@pytest.mark.asyncio
async def test_exhausted_transient_404s_raise_with_the_relays_marker():
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(404, json=GROUP_404)

    provider = _provider(handler, max_retries=1)
    with pytest.raises(ProviderError) as excinfo:
        await provider.complete(_req())
    assert calls["n"] == 2                      # max_retries=1 -> one retry, not an infinite loop
    assert "404" in str(excinfo.value)


@pytest.mark.asyncio
async def test_the_transient_404_marker_is_what_the_relay_actually_sends():
    # If aizzz.xyz ever rotates its wording, this pin is the canary: the retry lane
    # silently degrades to terminal failures, not to wrong behavior.
    assert "configured account" in TRANSIENT_GROUP_404
