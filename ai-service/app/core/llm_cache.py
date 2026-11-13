"""Exact-match cache for deterministic model calls (Epic 174).

The provider's prefix cache fires on a shared *prefix* and cannot help a
prompt whose fixed prefix is smaller than the gateway's minimum cacheable
block (measured: a ~150-token system prefix returns `cached_tokens = 0` on
every call). It also cannot help on retries and re-runs of the same
deterministic call -- `jd_analyze`, `resume_parse`, `reply_classify`,
`gap_analysis`, `rerank` never benefit, no matter how warm the gateway is.

This module serves those calls from Redis instead: a byte-identical prompt
is byte-identical work, so a repeated one costs the second caller a lookup,
not a model. It is deliberately narrow:

* only ``temperature == 0.0`` (the engine's deterministic calls) and
  only calls that do not ask for tools (a tool call is a decision, not an
  answer);
* keys are hashes of the full request, so a hit is a *verbatim* replay --
  nothing is re-worded, nothing is guessed;
* it rides the cache backend the operator already chose (``CACHE_BACKEND``).
  With caching off this module stores nothing and every call goes to the
  model exactly as before. ``NullCache`` is the default, so an absent config
  is a no-op, not a behavior change;
* any failure -- dead Redis, timeout, a malformed entry -- is a miss. The
  cache layer itself already fails open; this module trusts it.

Telemetry: a hit is recorded with the whole prompt reported as cached, at
``$0`` cost and ~0 latency, and the ``llm_call`` trace carries
``served_from: "exact_cache"`` so a dashboard counting cached tokens sees
real numbers, not fabricated ones.
"""

from __future__ import annotations

import hashlib
import json
import logging

from app.core import cache as cache_mod
from app.providers.base import LLMRequest, LLMResponse, Usage

log = logging.getLogger("core.llm_cache")

_PREFIX = "llm:v1:"
# A stored reply larger than this buys nothing on a cache hit that a retry
# would not also buy, and it would bloat a shared store; the deterministic
# JSON features are far below the limit.
_MAX_VALUE_BYTES = 256 * 1024


def eligible(req: LLMRequest) -> bool:
    """True when replaying this exact request later is safe."""
    if abs(req.temperature) > 0.0:
        return False
    if req.tools:
        return False
    if not req.messages:
        return False
    return True


def exact_cache_key(req: LLMRequest, model: str) -> str:
    """Content-addressed key over everything the model would see."""
    material = {
        "model": req.model or model,
        "messages": [[m.role, m.content] for m in req.messages],
        "max_tokens": req.max_tokens,
        "json_mode": bool(req.json_mode),
    }
    blob = json.dumps(material, ensure_ascii=False, sort_keys=True)
    return _PREFIX + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _serialize(resp: LLMResponse) -> str | None:
    if not resp.text or resp.tool_calls:
        return None
    value = {
        "t": resp.text,
        "model": resp.model,
        "in": resp.usage.input_tokens,
        "out": resp.usage.output_tokens,
    }
    blob = json.dumps(value, ensure_ascii=False)
    if len(blob.encode("utf-8")) > _MAX_VALUE_BYTES:
        return None
    return blob


def _deserialize(raw: str) -> dict | None:
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(value, dict):
        return None
    text = value.get("t")
    if not isinstance(text, str) or not text:
        return None
    return value


async def get(req: LLMRequest, model: str) -> LLMResponse | None:
    """A replay hit: the full prompt reported cached, at zero marginal cost."""
    if not eligible(req):
        return None
    try:
        raw = await cache_mod.get_cache().get(exact_cache_key(req, model))
    except Exception:
        log.warning("exact llm cache read failed; treating as a miss", exc_info=True)
        return None
    value = _deserialize(raw) if raw else None
    if value is None:
        return None
    return LLMResponse(
        text=value["t"],
        model=value.get("model") or model,
        usage=Usage(input_tokens=int(value.get("in") or 0),
                    output_tokens=int(value.get("out") or 0),
                    cached_tokens=int(value.get("in") or 0)),
        latency_ms=1,
        tool_calls=[])


async def put(req: LLMRequest, resp: LLMResponse) -> None:
    """Store a fresh deterministic answer; oversized/tool-calling ones stay out."""
    if not eligible(req):
        return
    blob = _serialize(resp)
    if blob is None:
        return
    try:
        # Reuse the operator's configured TTL; the cache backend defaults it.
        await cache_mod.get_cache().set(exact_cache_key(req, resp.model), blob, ttl=None)
    except Exception:
        log.warning("exact llm cache write failed; the answer stands", exc_info=True)
