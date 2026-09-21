import json
import time
from collections.abc import AsyncIterator

import httpx

from app.providers.base import LLMRequest, LLMResponse, StreamDelta, ToolCall, Usage
from app.providers.llm.openai_compat import ProviderError, _safe_json


class AnthropicProvider:
    """Anthropic Messages API. Tool-calling normalized to the shared schema."""

    name = "anthropic"

    def __init__(self, client: httpx.AsyncClient, base_url: str, api_key: str, model: str):
        self.client = client
        self.base = (base_url or "https://api.anthropic.com").rstrip("/")
        self.key = api_key
        self.model = model

    def _headers(self) -> dict:
        return {
            "x-api-key": self.key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def _payload(self, req: LLMRequest, stream: bool) -> dict:
        system = "\n\n".join(m.content for m in req.messages if m.role == "system")
        messages = []
        for m in req.messages:
            if m.role == "system":
                continue
            if m.role == "tool":
                messages.append({
                    "role": "user",
                    "content": [{"type": "tool_result", "tool_use_id": m.tool_call_id,
                                 "content": m.content}],
                })
            elif m.role == "assistant":
                messages.append({"role": "assistant", "content": m.content})
            else:
                messages.append({"role": "user", "content": m.content})
        p: dict = {
            "model": req.model or self.model,
            "system": system or None,
            "messages": messages,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "stream": stream,
        }
        if req.tools:
            p["tools"] = [
                {"name": t.name, "description": t.description,
                 "input_schema": t.parameters} for t in req.tools
            ]
        return {k: v for k, v in p.items() if v is not None}

    async def complete(self, req: LLMRequest) -> LLMResponse:
        started = time.monotonic()
        r = await self.client.post(f"{self.base}/v1/messages",
                                   json=self._payload(req, False),
                                   headers=self._headers(), timeout=120.0)
        if r.status_code >= 400:
            raise ProviderError(f"anthropic error {r.status_code}: {r.text[:400]}")
        data = r.json()
        text, tool_calls = "", []
        for block in data.get("content", []):
            if block["type"] == "text":
                text += block["text"]
            elif block["type"] == "tool_use":
                tool_calls.append(ToolCall(id=block["id"], name=block["name"],
                                           arguments=block.get("input") or {}))
        u = data.get("usage", {})
        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            usage=Usage(
                input_tokens=u.get("input_tokens", 0),
                output_tokens=u.get("output_tokens", 0),
                cached_tokens=u.get("cache_read_input_tokens", 0),
            ),
            model=data.get("model", req.model or self.model),
            latency_ms=int((time.monotonic() - started) * 1000),
            finish_reason=data.get("stop_reason") or "stop",
        )

    async def stream(self, req: LLMRequest) -> AsyncIterator[StreamDelta]:
        usage = Usage()
        async with self.client.stream("POST", f"{self.base}/v1/messages",
                                      json=self._payload(req, True),
                                      headers=self._headers(), timeout=180.0) as r:
            if r.status_code >= 400:
                body = (await r.aread()).decode(errors="replace")
                raise ProviderError(f"anthropic stream error {r.status_code}: {body[:400]}")
            async for line in r.aiter_lines():
                if not line.startswith("data:"):
                    continue
                try:
                    ev = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                t = ev.get("type")
                if t == "content_block_delta" and ev.get("delta", {}).get("type") == "text_delta":
                    yield StreamDelta(text=ev["delta"]["text"])
                elif t == "message_delta":
                    usage.output_tokens = ev.get("usage", {}).get("output_tokens", 0)
                elif t == "message_start":
                    u = ev.get("message", {}).get("usage", {})
                    usage.input_tokens = u.get("input_tokens", 0)
        usage.cached_tokens = 0
        yield StreamDelta(usage=usage, done=True)
