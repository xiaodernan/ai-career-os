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
        tools = _tools_openai(req)
        if tools:
            p["tools"] = tools
        if req.json_mode and not tools:
            p["response_format"] = {"type": "json_object"}
        return p

    async def _post(self, payload: dict) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                r = await self.client.post(
                    f"{self.base}/chat/completions",
                    json=payload,
                    headers=self._headers(),
                    timeout=120.0,
                )
                if r.status_code == 429 or r.status_code >= 500:
                    last_exc = ProviderError(f"upstream {r.status_code}: {r.text[:300]}")
                    await asyncio_sleep(1.5 * (attempt + 1))
                    continue
                if r.status_code >= 400:
                    raise ProviderError(f"LLM error {r.status_code}: {r.text[:500]}")
                return r
            except httpx.HTTPError as e:
                last_exc = e
                await asyncio_sleep(1.0 * (attempt + 1))
        raise ProviderError(f"LLM request failed after retries: {last_exc}")

    async def complete(self, req: LLMRequest) -> LLMResponse:
        started = time.monotonic()
        payload = self._payload(req, stream=False)
        r = await self._post(payload)
        data = r.json()
        choice = data["choices"][0]["message"]
        usage = data.get("usage", {})
        tool_calls = [
            ToolCall(
                id=tc["id"],
                name=tc["function"]["name"],
                arguments=_safe_json(tc["function"].get("arguments") or "{}"),
            )
            for tc in (choice.get("tool_calls") or [])
        ]
        return LLMResponse(
            text=choice.get("content") or "",
            tool_calls=tool_calls,
            usage=Usage(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                cached_tokens=(usage.get("prompt_tokens_details") or {}).get(
                    "cached_tokens", 0),
            ),
            model=data.get("model", req.model or self.model),
            latency_ms=int((time.monotonic() - started) * 1000),
            finish_reason=data["choices"][0].get("finish_reason") or "stop",
        )

    async def stream(self, req: LLMRequest) -> AsyncIterator[StreamDelta]:
        payload = self._payload(req, stream=True)
        final_usage = Usage()
        # Tool calls arrive as index-keyed fragments: id, then name, then the arguments
        # string in as many chunks as the model likes. They are reassembled here and
        # handed over on the closing delta, so a streamed step can still call a tool.
        calls: dict[int, ToolCall] = {}
        arg_fragments: dict[int, list[str]] = {}
        async with self.client.stream(
            "POST", f"{self.base}/chat/completions", json=payload,
            headers=self._headers(), timeout=180.0,
        ) as r:
            if r.status_code >= 400:
                body = (await r.aread()).decode(errors="replace")
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
