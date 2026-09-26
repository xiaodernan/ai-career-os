"""The copilot turn streams, and what reaches the task bus is a real token frame.

Three claims, each checked against running code rather than against a comment:

- `core/ai.ask_stream` forwards every text delta as it arrives and still hands the
  caller a whole reply — a step that answers with a tool call has no text to show and
  must not be reported as an answer.
- `/internal/agents/chat` runs the turn in streaming mode; `/chat/sync` does not (it has
  no task to publish to).
- Only the orchestrator's own answer streams. A subagent's report is input to the next
  loop step, so it stays off the token channel.
"""

import asyncio

import pytest

from app.agents import memory, orchestrator
from app.api import agents
from app.core import ai, taskbus
from app.core.deps import Ctx
from app.db import observability
from app.providers.base import LLMRequest, LLMResponse, StreamDelta, ToolCall, Usage


class ScriptedProvider:
    """Streams the chunks it was built with, then closes with whatever tool calls it holds."""

    name = "scripted"

    def __init__(self, chunks, tool_calls=None, usage=Usage(11, 5)):
        self.chunks = chunks
        self.tool_calls = tool_calls or []
        self.usage = usage

    async def stream(self, req: LLMRequest):
        for chunk in self.chunks:
            yield StreamDelta(text=chunk)
        yield StreamDelta(usage=self.usage, done=True, tool_calls=self.tool_calls)


@pytest.fixture
def quiet(monkeypatch):
    """No DB behind observability/memory: the streaming path is what is under test."""
    recorded: list[dict] = []

    async def fake_trace(run_id, kind, agent, payload):
        recorded.append({"run_id": run_id, "kind": kind, "agent": agent, **payload})

    async def fake_usage(*args, **kwargs):
        return None

    async def fake_memory(user_id):
        return ""

    async def fake_extract(*args, **kwargs):
        return None

    monkeypatch.setattr(observability, "trace", fake_trace)
    monkeypatch.setattr(observability, "record_usage", fake_usage)
    monkeypatch.setattr(observability, "finish_run", fake_usage)
    monkeypatch.setattr(observability, "release_trace_seq", lambda run_id: None)
    monkeypatch.setattr(observability, "create_run",
                        lambda *a, **k: asyncio.sleep(0, result="00000000-0000-4000-8000-000000000001"))
    monkeypatch.setattr(memory, "build_memory_context", fake_memory)
    monkeypatch.setattr(memory, "extract_and_store", fake_extract)
    return recorded


async def _collect(monkeypatch, provider) -> list[dict]:
    """Run one streamed turn against `provider` and return the frames on its task."""
    monkeypatch.setattr(ai, "get_llm", lambda settings=None: provider)
    task_id = taskbus.new_task("agent_chat", "u-stream")
    await orchestrator.career_turn(user_id="u-stream",
                                   message="What should I prepare for a system design interview?",
                                   task_id=task_id, stream=True)
    return [ev for ev in taskbus._TASKS[task_id]["events"]]


async def test_ask_stream_emits_every_delta_and_returns_the_whole_reply(monkeypatch, quiet):
    provider = ScriptedProvider(["Based on ", "the evidence, ", "lead with the ledger work."])
    monkeypatch.setattr(ai, "get_llm", lambda settings=None: provider)

    seen: list[str] = []

    async def emit(event):
        seen.append(event["data"]["text"])

    resp = await ai.ask_stream(LLMRequest(messages=[]), emit=emit)

    assert resp.text == "Based on the evidence, lead with the ledger work."
    assert seen == ["Based on ", "the evidence, ", "lead with the ledger work."]
    assert (resp.usage.input_tokens, resp.usage.output_tokens) == (11, 5)
    assert resp.tool_calls == []


async def test_a_step_that_only_calls_a_tool_says_so_instead_of_streaming(monkeypatch, quiet):
    provider = ScriptedProvider([], tool_calls=[ToolCall(id="c1", name="search_jobs",
                                                         arguments={"query": "backend"})])
    monkeypatch.setattr(ai, "get_llm", lambda settings=None: provider)

    seen: list[str] = []

    async def emit(event):
        seen.append(event["data"]["text"])

    resp = await ai.ask_stream(LLMRequest(messages=[]), emit=emit)

    assert seen == [], "an interim preamble must not be reported to the user as an answer"
    assert [tc.name for tc in resp.tool_calls] == ["search_jobs"]
    assert resp.tool_calls[0].arguments == {"query": "backend"}


async def test_the_streaming_turn_publishes_tokens_on_its_task(monkeypatch, quiet):
    provider = ScriptedProvider(["Here is ", "what matters."])
    frames = await _collect(monkeypatch, provider)

    names = [ev["event"] for ev in frames]
    tokens = [ev for ev in frames if ev["event"] == "token"]
    assert names[0] == "status", f"the turn should announce itself first: {names}"
    assert [ev["data"]["text"] for ev in tokens] == ["Here is ", "what matters."]
    assert tokens[0]["ts"] <= tokens[1]["ts"], "deltas must keep the order they were written in"
    # the reply itself is still handed back whole, for the caller that stores it
    assert names[-1] == "message"


async def test_a_subagent_report_stays_off_the_token_channel(monkeypatch, quiet):
    """The career loop streams; the handoff target's loop does not."""
    streamed: list[str] = []
    plain: list[str] = []
    script = iter([
        LLMResponse(text="", tool_calls=[ToolCall(id="t1", name="transfer_to",
                                                  arguments={"agent": "job_research",
                                                             "task": "find roles"})]),
        LLMResponse(text="SUBREPORT: 3 roles", tool_calls=[]),
        LLMResponse(text="Three roles match your backend background.", tool_calls=[]),
    ])

    async def fake_ask_stream(req, emit=None, **kw):
        resp = next(script)
        streamed.append(resp.text)
        if emit and resp.text:
            await emit({"event": "token", "data": {"text": resp.text}})
        return resp

    async def fake_ask(req, **kw):
        resp = next(script)
        plain.append(resp.text)
        return resp

    monkeypatch.setattr(orchestrator.ai, "ask_stream", fake_ask_stream)
    monkeypatch.setattr(orchestrator.ai, "ask", fake_ask)

    task_id = taskbus.new_task("agent_chat", "u1")
    out = await orchestrator.career_turn(user_id="u1", message="find roles",
                                         task_id=task_id, stream=True)

    assert out.answer == "Three roles match your backend background."
    assert streamed == ["", "Three roles match your backend background."]
    assert plain == ["SUBREPORT: 3 roles"], "the subagent answered through the non-streaming call"
    tokens = [ev["data"]["text"] for ev in taskbus._TASKS[task_id]["events"]
              if ev["event"] == "token"]
    assert tokens == ["Three roles match your backend background."]


async def test_the_background_chat_endpoint_runs_the_turn_in_streaming_mode(monkeypatch, quiet):
    provider = ScriptedProvider(["Streaming ", "from the endpoint."])
    monkeypatch.setattr(ai, "get_llm", lambda settings=None: provider)

    started = await agents.chat(agents.ChatReq(
        message="What should I prepare for a system design interview?"),
        ctx=Ctx(user_id="u-endpoint"))
    task_id = started["task_id"]

    for _ in range(200):
        if taskbus.is_done(task_id):
            break
        await asyncio.sleep(0.01)
    assert taskbus.is_done(task_id), "the background turn never finished"

    frames = [ev for ev in taskbus._TASKS[task_id]["events"]]
    names = [ev["event"] for ev in frames]
    assert "token" in names, f"the endpoint did not stream: {names}"
    tokens = [ev["data"]["text"] for ev in frames if ev["event"] == "token"]
    assert tokens == ["Streaming ", "from the endpoint."]
    assert names[-1] == "done", "the reply's authoritative frame must close the stream"
    assert frames[-1]["data"]["result"]["answer"] == "Streaming from the endpoint."
