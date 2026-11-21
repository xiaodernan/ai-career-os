import json
import time
from collections.abc import AsyncIterator

import httpx

from app.providers.base import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
    StreamDelta,
    ToolCall,
    Usage,
)


class ProviderError(Exception):
    pass


# This relay's 404 message for "no channel in the account group can serve this
# model right now" — measured 2026-11-18 as bursty over hours (the identical
# request answered 200 four times, then 404 nine times, then 200 again). It is
# transient, and terminal handling of it poisons every retry-free path.
TRANSIENT_GROUP_404 = "not supported by any configured account"


def _to_openai_messages(messages: list[LLMMessage]) -> list[dict]:
    out = []
    for m in messages:
        item: dict = {"role": m.role, "content": m.content}
        if m.role == "tool":
            item = {"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content}
        elif m.role == "assistant" and m.tool_calls:
            item["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.name,
                              "arguments": json.dumps(tc.arguments, ensure_ascii=False)}}
                for tc in m.tool_calls
            ]
        out.append(item)
    return out


def _tools_openai(req: LLMRequest) -> list[dict] | None:
    if not req.tools:
        return None
    return [
        {"type": "function", "function": {"name": t.name, "description": t.description,
         "parameters": t.parameters}}
        for t in req.tools
    ]


class OpenAICompatProvider:
    name = "openai_compat"

    def __init__(self, client: httpx.AsyncClient, base_url: str, api_key: str, model: str,
                 max_retries: int = 2):
        self.client = client
        self.base = base_url.rstrip("/")
        self.key = api_key
        self.model = model
        self.max_retries = max_retries

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}

    def _payload(self, req: LLMRequest, stream: bool) -> dict:
        p: dict = {
            "model": req.model or self.model,
            "messages": _to_openai_messages(req.messages),
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
            "stream": stream,
        }
        # Ask for usage on the terminal chunk in both modes. Live probe 2026-11-21
        # (gpt-6.2-sol via api.aizzz.xyz/v1, through the 7897 mixed proxy) showed the
        # gateway returns `prompt_tokens_details.cached_tokens` on NON-streaming calls
        # too (4180/4391 on a warm repeat, 95%) — the older 2026-11-18 note claiming
        # non-stream never carries the detail no longer holds. We still route
        # `complete()` through the streaming shape below: it is byte-for-byte the same
        # answer, the detail is guaranteed on the terminal event, and it keeps one code
        # path for usage. `stream_options` is harmless when stream is false.
        p["stream_options"] = {"include_usage": True}
        if req.cache_key:
            # Routing hint for gateways that shard by key. Live probe 2026-11-21 proved
            # this gateway's prefix cache is NOT sharded that way: two different
            # long sessions interleaved under ONE `careeros-engine` key each held 95.7%
            # independently, and temperature 0/0.2/0.7 all hit 95.9% on the same prefix.
            # So the key is kept only as a forward-compatible hint; the real cache
            # driver is a byte-identical prefix (see app.core.preamble), not this key
            # and not temperature. Never key per-request or per-call — that would shard.
            p["prompt_cache_key"] = req.cache_key
        tools = _tools_openai(req)
        if tools:
            p["tools"] = tools
        if req.json_mode and not tools:
            p["response_format"] = {"type": "json_object"}
        return p

    async def _consume_stream(self, req: LLMRequest) -> tuple[str, list[ToolCall], Usage]:
        """Drive one streaming exchange and return what the model answered.

        Non-stream calls on this relay answer without `prompt_tokens_details`:
        the token block is absent, so the reported cache figure reads as 0
        for every un-streamed call and one-shot engines under-report forever.
        The wire shape is identical — the same deltas, assembled here — so the
        reply is byte-for-byte what a non-stream call returns, only with the
        detail the reader is owed.
        """
        payload = self._payload(req, stream=True)

        text_parts: list[str] = []
        calls: dict[int, ToolCall] = {}
        arg_fragments: dict[int, list[str]] = {}
        final_usage = Usage()
        last_failure: str | None = None
        for attempt in range(self.max_retries + 1):
            async with self.client.stream(
                "POST", f"{self.base}/chat/completions", json=payload,
                headers=self._headers(), timeout=180.0,
            ) as r:
                if r.status_code >= 400:
                    body = (await r.aread()).decode(errors="replace")
                    retriable = (r.status_code == 404 and TRANSIENT_GROUP_404 in body) \
                        or r.status_code == 429 or r.status_code >= 500
                    if retriable:
                        # The same transient-establishment retry lane as the
                        # blocking path: back off and retry the establishment.
                        last_failure = f"{r.status_code}: {body[:200]}"
                        await asyncio_sleep(1.5 * (attempt + 1))
                        continue
                    raise ProviderError(f"LLM stream error {r.status_code}: {body[:400]}")
                async for line in r.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    chunk = line[5:].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        data = json.loads(chunk)
                    except json.JSONDecodeError:
                        continue
                    if data.get("usage"):
                        u = data["usage"]
                        final_usage = Usage(
                            u.get("prompt_tokens", 0), u.get("completion_tokens", 0),
                            (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0))
                    delta = (data.get("choices") or [{}])[0].get("delta") or {}
                    text = delta.get("content") or ""
                    if text:
                        text_parts.append(text)
                    for fragment in delta.get("tool_calls") or []:
                        index = int(fragment.get("index") or 0)
                        function = fragment.get("function") or {}
                        call = calls.setdefault(index, ToolCall(
                            id=fragment.get("id") or f"call_{index}", name="", arguments={}))
                        if fragment.get("id"):
                            call.id = fragment["id"]
                        if function.get("name"):
                            call.name = function["name"]
                        if function.get("arguments"):
                            arg_fragments.setdefault(index, []).append(function["arguments"])
                break
        else:
            # The retry lane ran dry without a 200 (the relay answered transient
            # failures for every attempt, or never answered). Staying silent here
            # reads as "the model said nothing"; say what failed instead.
            raise ProviderError(f"LLM request failed after retries: {last_failure}")
        for index, call in calls.items():
            raw = "".join(arg_fragments.get(index, []))
            call.arguments = _safe_json(raw) if raw else {}
        return "".join(text_parts), [calls[i] for i in sorted(calls)], final_usage

    async def complete(self, req: LLMRequest) -> LLMResponse:
        started = time.monotonic()
        text, tool_calls, usage = await self._consume_stream(req)
        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            usage=usage,
            model=req.model or self.model,
            latency_ms=int((time.monotonic() - started) * 1000),
            finish_reason="stop",
        )

    async def stream(self, req: LLMRequest) -> AsyncIterator[StreamDelta]:
        payload = self._payload(req, stream=True)
        final_usage = Usage()
        # Tool calls arrive as index-keyed fragments: id, then name, then the arguments
        # string in as many chunks as the model likes. They are reassembled here and
        # handed over on the closing delta, so a streamed step can still call a tool.
        calls: dict[int, ToolCall] = {}
        arg_fragments: dict[int, list[str]] = {}
        last_failure: str | None = None
        for attempt in range(self.max_retries + 1):
            async with self.client.stream(
                "POST", f"{self.base}/chat/completions", json=payload,
                headers=self._headers(), timeout=180.0,
            ) as r:
                if r.status_code >= 400:
                    body = (await r.aread()).decode(errors="replace")
                    retriable = (r.status_code == 404 and TRANSIENT_GROUP_404 in body) \
                        or r.status_code == 429 or r.status_code >= 500
                    if retriable:
                        # Rate limit, server fault, transient group-404: same backoff
                        # lane the whole provider rides.
                        last_failure = f"{r.status_code}: {body[:200]}"
                        await asyncio_sleep(1.5 * (attempt + 1))
                        continue
                    raise ProviderError(f"LLM stream error {r.status_code}: {body[:400]}")
                async for line in r.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    chunk = line[5:].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        data = json.loads(chunk)
                    except json.JSONDecodeError:
                        continue
                    if data.get("usage"):
                        u = data["usage"]
                        final_usage = Usage(
                            u.get("prompt_tokens", 0), u.get("completion_tokens", 0),
                            (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0))
                    delta = (data.get("choices") or [{}])[0].get("delta") or {}
                    text = delta.get("content") or ""
                    if text:
                        yield StreamDelta(text=text)
                    for fragment in delta.get("tool_calls") or []:
                        index = int(fragment.get("index") or 0)
                        function = fragment.get("function") or {}
                        call = calls.setdefault(index, ToolCall(
                            id=fragment.get("id") or f"call_{index}", name="", arguments={}))
                        if fragment.get("id"):
                            call.id = fragment["id"]
                        if function.get("name"):
                            call.name = function["name"]
                        if function.get("arguments"):
                            arg_fragments.setdefault(index, []).append(function["arguments"])
                break
        else:
            raise ProviderError(f"LLM request failed after retries: {last_failure}")
        for index, call in calls.items():
            raw = "".join(arg_fragments.get(index, []))
            call.arguments = _safe_json(raw) if raw else {}
        yield StreamDelta(usage=final_usage, done=True,
                          tool_calls=[calls[i] for i in sorted(calls)])

    async def embed(self, texts: list[str], model: str, dim: int) -> list[list[float]]:
        payload: dict = {"model": model, "input": texts, "encoding_format": "float"}
        if "3-small" in model or "3-large" in model:
            payload["dimensions"] = dim
        r = await self._post_chat_free(payload)
        items = sorted(r.json()["data"], key=lambda d: d["index"])
        return [it["embedding"] for it in items]

    async def _post_chat_free(self, payload: dict) -> httpx.Response:
        r = await self.client.post(
            f"{self.base}/embeddings", json=payload, headers=self._headers(), timeout=60.0)
        if r.status_code >= 400:
            raise ProviderError(f"embedding error {r.status_code}: {r.text[:400]}")
        return r


def _safe_json(s: str) -> dict:
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return {}


async def asyncio_sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)
