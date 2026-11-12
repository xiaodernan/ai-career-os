"""Three live-gateway protocols the offline provider cannot express (Epic 156).

Epic 155 proved the *transport seam*: the app's own ``get_llm(Settings`` factory
reaches a real model and returns a grounded answer. But it exercised only
``complete()`` with plain text. Three protocol shapes the shipped product leans on
were still attested only by the ``mock`` provider, which by construction can never
misbehave:

* **structured output** (``json_mode`` -> ``response_format: json_object``), which
  ten ``ask_json`` call sites depend on, and whose reply the project's own
  ``_coerce_json`` must be able to eat;
* **server-sent streaming** (``stream()``), whose frame sequence a real gateway
  decorates with an opening frame carrying no content and a *different* id from
  the frames that follow -- a shape a hand-written mock "stream" (a fixed string
  cut into 24-char slices) never produces;
* **tool calling** (``tools=``), whose ``tool_call.id`` the agent loop echoes back
  verbatim as ``tool_call_id`` on the next turn, and whose ``arguments`` must
  arrive as a dict, not a half-parsed JSON string.

A mock cannot contradict any of those, so the offline suite cannot tell us the
live path still works. This file does, and it is the *same* production
``OpenAICompatProvider`` class doing the parsing -- not a curl, not a hand-built
HTTP client.

It is inert unless the operator opts in:

    CAREEROS_REAL_LLM=1 pytest tests/test_the_live_gateway_speaks_three_protocols.py -q

With the switch off (the default, every CI job, the dev loop) pytest skips the
module *before any socket opens*. The key is resolved only from the process
environment / gitignored ``.env``, the way production does; this file contains no
token. ``LLM_BASE_URL`` must include ``/v1`` and ``LLM_MODEL`` must be the id
served by that gateway's ``/v1/models`` (the marketing name is not always the
wire id).

**Why a self-managed client, not ``registry.get_llm``.** Epic 155 drives the
module-level ``@lru_cache`` client in ``registry``, which binds to the event loop
that first used it and is never closed. Two opt-in modules with two
function-scoped loops sharing that one cached client would close its connections
on an already-closed loop. This file therefore builds the *production provider
class* with its own ``httpx.AsyncClient`` inside a single async test / single
loop. The two opt-in files can then coexist in one opt-in run without leaking
loop-bound state into each other. It is dependency injection through the
provider's real constructor, not a second implementation of the protocol.

**What is asserted, and what is deliberately not.** The assertions are protocol
invariants -- a JSON object came back and the project's parser accepts it; the
streamed fragments reassemble into the whole reply and the closing frame carries
real usage; a tool reply carries a stable id and dict arguments. They do *not*
assert the model's wording, that it picked a particular score, or that it called
exactly one tool: those are model behaviour, and pinning them would turn this
into a flaky test that claims more than a measurement supports. The measurements
recorded in ``DEPLOYMENT.md`` are the evidence; this file keeps them re-checkable.
"""

from __future__ import annotations

import os

import pytest

# Read once at import, before any provider is built. Off by default so a plain
# `pytest` (CI, dev loop, pre-commit) skips the module without opening a socket.
_OPT_IN = os.environ.get("CAREEROS_REAL_LLM") == "1"

pytestmark = pytest.mark.skipif(
    not _OPT_IN,
    reason="opt-in only: set CAREEROS_REAL_LLM=1 with a real LLM_PROVIDER/LLM_API_KEY",
)


def _real_settings():
    """This deployment's config, only when it names a usable gateway.

    Lazy on purpose (never at import): an offline collection must not even parse
    `.env`. Each refusal is a skip, not a failure -- this is a live-provider
    probe, not a claim that every machine is wired to the internet.
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


async def test_the_live_gateway_honours_json_tools_and_stream():
    """Three protocol shapes, one loop, one self-managed client, the real gateway.

    All three calls share one ``async`` test on purpose: the production provider
    takes an injected ``httpx.AsyncClient``, and keeping one client on one loop
    mirrors the lifetime FastAPI gives it. Splitting these into separate
    function-scoped-loop tests is exactly the trap Epic 155 recorded.
    """
    import httpx

    from app.core.ai import _coerce_json
    from app.providers.base import LLMMessage, LLMRequest, ToolSpec
    from app.providers.llm.openai_compat import OpenAICompatProvider

    s = _real_settings()
    async with httpx.AsyncClient() as client:
        provider = OpenAICompatProvider(
            client, s.llm_base_url, s.llm_api_key, s.llm_model)

        # --- 1. structured output: json_mode must yield an object the app can eat. ---
        # This is the exact system shape `rag/rerank.py` sends, so the probe also
        # grades the gateway against a real call site rather than an invented one.
        structured = await provider.complete(LLMRequest(
            messages=[
                LLMMessage("system",
                           "You score how relevant each numbered evidence snippet is to the "
                           "user's need. JSON only: "
                           '{"scores": {"<index>": 0.0-1.0}}. Be strict: unrelated = 0.'),
                LLMMessage("user",
                           "Query context: How did I cut latency with Redis?\n\n"
                           "Snippets:\n"
                           "[0] (resume/experience) Rebuilt the idempotent Redis consumer; "
                           "cut P99 from 400ms to 50ms.\n"
                           "[1] (resume/education) BSc Computer Science, graduated 2020.\n"
                           "[2] (note/notes) Weekend hiking trip plan."),
            ],
            json_mode=True, temperature=0.0, max_tokens=200,
        ))
        assert structured.finish_reason == "stop", (
            f"a short JSON reply must finish cleanly, got {structured.finish_reason!r}; "
            "a 'length' finish would mean max_tokens truncated the object")
        assert structured.usage.total > 0, "a live reply must carry real token usage"
        assert structured.model == s.llm_model, (
            f"gateway answered with {structured.model!r}, deployment named {s.llm_model!r}")
        parsed = _coerce_json(structured.text)
        assert isinstance(parsed, dict) and "scores" in parsed, (
            f"json_mode reply is not a scores object the app can consume: "
            f"{structured.text[:200]!r}")
        assert all(isinstance(v, (int, float)) for v in (parsed["scores"] or {}).values()), (
            "the project's rerank fold needs numeric scores keyed by string index")

        # --- 2. stream: the real frame sequence reassembles into the whole reply. ---
        pieces: list[str] = []
        frames = 0
        closing = None
        async for delta in provider.stream(LLMRequest(
            messages=[LLMMessage(
                "user", "Count from 1 to 5, separated by commas, nothing else.")],
            temperature=0.0, max_tokens=40,
        )):
            frames += 1
            if delta.text:
                pieces.append(delta.text)
            if delta.done:
                closing = delta
        assembled = "".join(pieces)
        assert frames > 2, (
            f"a real stream is many frames, not one blob (got {frames}); an opening frame "
            "with no content and a different id never appears in the mock's sliced string")
        assert all(str(i) in assembled for i in range(1, 6)), (
            f"the streamed fragments did not reassemble into the reply: {assembled[:120]!r}")
        assert closing is not None and closing.usage is not None, (
            "the closing frame must carry aggregated usage -- that is what bills the run")
        assert closing.usage.output_tokens > 0, "a completed stream must consume output tokens"

        # --- 3. tools: id comes back verbatim, arguments arrive as a dict. ---
        tool_reply = await provider.complete(LLMRequest(
            messages=[LLMMessage("user", "What is the weather in Beijing? Use the tool.")],
            tools=[ToolSpec(
                name="get_weather",
                description="Get the current weather for a city",
                parameters={"type": "object",
                            "properties": {"city": {"type": "string"}},
                            "required": ["city"]},
            )],
            temperature=0.0, max_tokens=128,
        ))
        assert tool_reply.finish_reason == "tool_calls", (
            f"a tool step must finish with 'tool_calls', got {tool_reply.finish_reason!r}; "
            "measured on this gateway 2026-11-12 -- if a replacement gateway reports it "
            "differently, re-read the agent loop before re-numbering this pin")
        assert tool_reply.tool_calls, "the gateway answered a tool request with no tool call"
        call = tool_reply.tool_calls[0]
        assert call.id, "tool_call.id must be present: the agent echoes it back as tool_call_id"
        assert call.name == "get_weather", f"unexpected tool name: {call.name!r}"
        assert isinstance(call.arguments, dict) and call.arguments.get("city"), (
            f"tool arguments must resolve to a dict with the requested field, got "
            f"{call.arguments!r}; a half-parsed JSON string would break the handler")
