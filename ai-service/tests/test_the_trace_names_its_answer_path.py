"""The trace tells the reader which transport answered every model call.

Before this change, `llm_call` rows were indistinguishable between the two paths --
the only way to tell a streaming copilot step from a one-shot feature call was to
grep the orchestrator source. The `mode` field is set at the call site so the
AI Activity timeline can print `step_2 · gpt-6-sol · stream`, and a reader who
wonders "why is this row zero cached?" can answer it by looking at the trace.
"""

import pytest
from app.core import ai
from app.db import observability
from app.providers.base import LLMRequest, LLMResponse, StreamDelta, ToolCall, Usage


class CountingCompleteProvider:
    name = "counting"
    model = "gpt-6-sol"

    async def complete(self, req):
        return LLMResponse(
            text="done",
            tool_calls=[],
            usage=Usage(11, 5),
            model="gpt-6-sol",
            latency_ms=42,
        )


class CountingStreamProvider:
    name = "counting-stream"
    model = "gpt-6-sol"

    async def stream(self, req):
        for chunk in ("ok ", "then ", "stream "):
            yield StreamDelta(text=chunk)
        yield StreamDelta(usage=Usage(11, 5), done=True)


@pytest.fixture
def quiet(monkeypatch):
    """No DB behind observability; recorded traces are all we want."""
    recorded: list[dict] = []

    async def fake_trace(run_id, kind, agent, payload):
        recorded.append({"run_id": run_id, "trace_kind": kind, "agent": agent, **payload})

    async def fake_usage(*args, **kwargs):
        return None

    monkeypatch.setattr(observability, "trace", fake_trace)
    monkeypatch.setattr(observability, "record_usage", fake_usage)
    return recorded


async def test_a_non_streaming_call_is_labelled_complete(monkeypatch, quiet):
    monkeypatch.setattr(ai, "get_llm", lambda settings=None: CountingCompleteProvider())
    await ai.ask(LLMRequest(messages=[]), run_id="r1", agent="test-agent", kind="k")
    trace = next(r for r in quiet if r["trace_kind"] == "llm_call")
    assert trace["mode"] == "complete", f"non-stream answer labelled as {trace.get('mode')!r}"


async def test_a_streaming_call_is_labelled_stream(monkeypatch, quiet):
    monkeypatch.setattr(ai, "get_llm", lambda settings=None: CountingStreamProvider())
    await ai.ask_stream(LLMRequest(messages=[]), run_id="r2", agent="test-agent", kind="k")
    trace = next(r for r in quiet if r["trace_kind"] == "llm_call")
    assert trace["mode"] == "stream", f"streaming answer labelled as {trace.get('mode')!r}"


async def test_stream_with_usage_null_still_traces_the_mode(monkeypatch, quiet):
    class UsagelessStream(CountingStreamProvider):
        async def stream(self, req):
            for chunk in ("bare",):
                yield StreamDelta(text=chunk)
            yield StreamDelta(usage=None, done=True)

    monkeypatch.setattr(ai, "get_llm", lambda settings=None: UsagelessStream())
    await ai.ask_stream(LLMRequest(messages=[]), run_id="r3", agent="test-agent", kind="k")
    trace = next(r for r in quiet if r["trace_kind"] == "llm_call")
    assert trace["mode"] == "stream"


async def test_a_failed_stream_records_the_attempt(monkeypatch, quiet):
    class BrokenStreamProvider:
        name = "broken"
        model = "gpt-6-sol"

        async def stream(self, req):
            raise RuntimeError("boom")
            yield  # pragma: no cover

    monkeypatch.setattr(ai, "get_llm", lambda settings=None: BrokenStreamProvider())
    monkeypatch.setattr(ai, "get_llm", lambda settings=None: BrokenStreamProvider())
    monkeypatch.setattr(ai.observability, "get_settings", lambda *a, **kw: None, raising=False)
    with pytest.raises(RuntimeError):
        await ai.ask_stream(LLMRequest(messages=[]), run_id="r4", agent="test-agent", kind="k")
    trace = next(r for r in quiet if r["trace_kind"] == "error")
    assert trace["stage"] == "k"
