"""An opt-in round trip through a real OpenAI-compatible gateway (Epic 155).

The whole offline suite runs on `llm_provider=mock` + `embedding_provider=hash`:
it is fast, free and deterministic, and that must not change. This file is the
escape hatch that proves the *same* factory the app uses reaches a real model
and comes back with a real answer -- not a curl, not a hand-built HTTP client,
but `registry.get_llm(Settings)` -> `OpenAICompatProvider.complete`, the exact
door every feature and agent walks through.

It is inert unless the operator opts in:

    CAREEROS_REAL_LLM=1 LLM_PROVIDER=openai_compat \
        LLM_BASE_URL=https://<your-gateway>/v1 LLM_MODEL=<id from /v1/models> \
        LLM_API_KEY=<yours> pytest tests/test_a_real_model_round_trip.py -q

Nothing here reads a key from a tracked file, and this file contains no token:
`Settings` resolves the key from the process environment (or the gitignored
`.env`), the same way production does. With the switch off -- the default, and
every CI job -- collection skips the whole module before any socket opens, so a
real-provider bill can never surprise an unattended run.

Two assertions matter beyond "a request succeeded":

* the reply carries the *provider-selected* model id, the real token usage and
  a measured latency, so a mock or a cached fixture cannot satisfy this file;
* the cover-letter case feeds the real `_build_prompt` a resume/JD and asks the
  model for a grounded letter, so the check covers a model-as-product path, not
  only the transport seam. Embeddings and retrieval stay on the offline stack;
  a narrative model call is what is under test here.
"""

from __future__ import annotations

import os

import pytest

# The switch is read once at import, before any provider is built. Off by default:
# a plain `pytest` (CI, dev loop, pre-commit) skips the module without a socket.
_OPT_IN = os.environ.get("CAREEROS_REAL_LLM") == "1"

pytestmark = pytest.mark.skipif(
    not _OPT_IN,
    reason="opt-in only: set CAREEROS_REAL_LLM=1 with a real LLM_PROVIDER/LLM_API_KEY",
)


def _real_settings():
    """The deployment's own config, only when it actually names a usable provider.

    Kept lazy (inside the tests, never at import) so an offline collection does
    not even parse `.env`. Each refusal is a skip, not a failure: this file is a
    live-provider probe, not a claim that every machine is wired to the internet.
    """
    from app.core.config import Settings

    s = Settings()
    if s.llm_provider != "openai_compat":
        pytest.skip(f"LLM_PROVIDER is {s.llm_provider!r}, not 'openai_compat'")
    if not s.llm_api_key:
        pytest.skip("no LLM_API_KEY in the environment / gitignored .env")
    if "/v1" not in s.llm_base_url:
        pytest.skip("LLM_BASE_URL must include the /v1 protocol prefix for this gateway")
    return s


async def test_a_real_model_round_trip_answers_and_writes():
    """Two live calls on ONE loop, through the project's own `get_llm` factory.

    Both the transport seam (a deterministic PONG) and a model-as-product path
    (the real cover-letter prompt builder -> a grounded letter) run inside a
    single async test on purpose. The registry caches one module-level
    `httpx.AsyncClient`, which binds to the loop that first used it; pytest-
    asyncio (`asyncio_mode = auto`) gives a function-scoped loop per test, so
    splitting these into two tests would make the second close cached client
    connections on an already-closed loop. One test, one loop, one client -- the
    same lifetime FastAPI gives it in production.
    """
    from app.features.cover_letter import BASE_SYSTEM, _build_prompt
    from app.providers.base import LLMMessage, LLMRequest
    from app.providers.registry import get_llm

    s = _real_settings()
    provider = get_llm(s)
    assert provider.name == "openai_compat"

    # --- 1. transport seam: a deterministic reply with real, billable usage ---
    ping = await provider.complete(LLMRequest(
        messages=[LLMMessage("user", "Reply with exactly: PONG")],
        temperature=0, max_tokens=32,
    ))
    assert ping.text.strip() == "PONG", f"unexpected live reply: {ping.text[:200]!r}"
    assert ping.model == s.llm_model, (f"the gateway answered with {ping.model!r}, "
                                       f"but the deployment named {s.llm_model!r}")
    assert ping.usage.total > 0, "a live reply must carry real token usage"
    assert ping.latency_ms > 0, "a live round trip must carry a measured latency"
    assert ping.finish_reason == "stop"

    # --- 2. model-as-product: the real prompt builder + the real model ---
    prompt = _build_prompt(
        {"profile": {"name": "Probe Candidate", "headline": "Backend engineer"}},
        {"title": "Staff Platform Engineer", "company": "Acme",
         "requiredSkills": [{"name": "Redis"}, {"name": "Kafka"}]},
        {"name": "Acme", "overview": "A payments scaleup moving to event-driven ingestion."},
        "Move into platform leadership",
        "[Evidence 1] Rebuilt the idempotent consumer; cut P99 from 400ms to 50ms.",
        "confident", "short", "generate", "",
    )
    # The grounded evidence and the role must actually reach the model's prompt.
    assert "idempotent consumer" in prompt and "Staff Platform Engineer" in prompt

    letter = await provider.complete(LLMRequest(
        messages=[LLMMessage("system", BASE_SYSTEM), LLMMessage("user", prompt)],
        temperature=0.4, max_tokens=400,
    ))
    text = letter.text.strip()
    assert len(text) > 80, f"the live model returned too little prose: {text[:200]!r}"
    assert "##" not in text, "the system prompt forbids markdown headers in the letter"
    assert any(k in text.lower() for k in ("platform", "redis", "kafka", "engineer", "payment")), (
        f"the letter is not grounded in the role/evidence: {text[:200]!r}")
    assert letter.model == s.llm_model
    assert letter.usage.output_tokens > 0, "a generated letter must consume output tokens"
