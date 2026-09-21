import json
import time
from collections.abc import AsyncIterator

import httpx

from app.providers.base import LLMRequest, LLMResponse, StreamDelta, ToolCall, Usage
from app.providers.llm.openai_compat import ProviderError


class OllamaProvider:
    """Local Ollama: /api/chat (tools + streaming) and /api/embed."""

    name = "ollama"

    def __init__(self, client: httpx.AsyncClient, base_url: str, model: str):
        self.client = client
        self.base = (base_url or "http://localhost:11434").rstrip("/")
        self.model = model

    def _payload(self, req: LLMRequest, stream: bool) -> dict:
        messages = [{"role": m.role, "content": m.content} for m in req.messages]
        p: dict = {"model": req.model or self.model, "messages": messages, "stream": stream,
                   "options": {"temperature": req.temperature}}
        if req.tools:
            p["tools"] = [{"type": "function", "function": {
                "name": t.name, "description": t.description,
                "parameters": t.parameters}} for t in req.tools]
        if req.json_mode:
            p["format"] = "json"
        return p

    async def complete(self, req: LLMRequest) -> LLMResponse:
        started = time.monotonic()
        r = await self.client.post(f"{self.base}/api/chat",
                                   json=self._payload(req, False), timeout=300.0)
        if r.status_code >= 400:
            raise ProviderError(f"ollama error {r.status_code}: {r.text[:300]}")
        data = r.json()
        msg = data.get("message", {})
        tool_calls = [
            ToolCall(id=f"call_{i}", name=tc["function"]["name"],
                     arguments=tc["function"].get("arguments") or {})
            for i, tc in enumerate(msg.get("tool_calls") or [])
        ]
        return LLMResponse(
            text=msg.get("content") or "",
            tool_calls=tool_calls,
            usage=Usage(data.get("prompt_eval_count", 0), data.get("eval_count", 0)),
            model=data.get("model", req.model or self.model),
            latency_ms=int((time.monotonic() - started) * 1000),
            finish_reason=data.get("done_reason") or "stop",
        )

    async def stream(self, req: LLMRequest) -> AsyncIterator[StreamDelta]:
        usage = Usage()
        async with self.client.stream("POST", f"{self.base}/api/chat",
                                      json=self._payload(req, True), timeout=600.0) as r:
            if r.status_code >= 400:
                body = (await r.aread()).decode(errors="replace")
                raise ProviderError(f"ollama stream error {r.status_code}: {body[:300]}")
            async for line in r.aiter_lines():
                if not line.strip():
                    continue
                ev = json.loads(line)
                delta = (ev.get("message") or {}).get("content") or ""
                if delta:
                    yield StreamDelta(text=delta)
                if ev.get("done"):
                    usage = Usage(ev.get("prompt_eval_count", 0), ev.get("eval_count", 0))
        yield StreamDelta(usage=usage, done=True)

    async def embed(self, texts: list[str], model: str, dim: int) -> list[list[float]]:
        r = await self.client.post(f"{self.base}/api/embed",
                                   json={"model": model, "input": texts}, timeout=120.0)
        if r.status_code >= 400:
            raise ProviderError(f"ollama embed error {r.status_code}: {r.text[:300]}")
        return r.json()["embeddings"]
