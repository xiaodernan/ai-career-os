"""Orchestrator unit tests: tool loop, subagent handoff, artifacts/sources/actions.

No DB / no LLM: ai.ask is scripted and observability.trace is recorded in-memory.
"""

import json

import pytest

from app.agents import orchestrator
from app.agents.tools import TOOL_INDEX
from app.providers.base import LLMMessage, LLMResponse, ToolCall, Usage


def _resp(tool_calls=None, text=""):
    return LLMResponse(text=text, tool_calls=tool_calls or [],
                       usage=Usage(10, 5), model="mock-model")


@pytest.fixture
def env(monkeypatch):
    traces: list[tuple[str, str, dict]] = []
    calls: list[dict] = []

    async def fake_trace(run_id, kind, agent, payload):
        traces.append((kind, agent, payload))

    monkeypatch.setattr(orchestrator.observability, "trace", fake_trace)

    async def fake_memory(user_id):
        return ""

    monkeypatch.setattr(orchestrator.memory, "build_memory_context", fake_memory)
    return traces, calls


async def test_tool_loop_produces_artifacts_and_actions(env, monkeypatch):
    traces, _ = env
    script = iter([
        _resp(tool_calls=[ToolCall(id="c1", name="search_jobs",
                                   arguments={"query": "backend"})]),
        _resp(text="Found 1 matching role for you."),
    ])
    seen_msgs: list[list[LLMMessage]] = []

    async def fake_ask(req, **kw):
        seen_msgs.append(req.messages)
        return next(script)

    async def fake_handler(user_id, **kw):
        return {"jobs": [{"id": "j1", "title": "BE", "company": "X", "location": "SH",
                          "remote": "remote", "salary": [1, 2], "skills": ["Java"]}]}

    monkeypatch.setattr(orchestrator.ai, "ask", fake_ask)
    monkeypatch.setattr(TOOL_INDEX["search_jobs"], "handler", fake_handler)

    out = await orchestrator.career_turn(user_id="u1", message="find jobs", run_id="r1")

    assert out.answer == "Found 1 matching role for you."
    assert out.tools_used == ["search_jobs"]
    assert out.artifacts[0]["type"] == "job_list"
    assert out.actions[0]["kind"] == "open_job" and out.actions[0]["job_id"] == "j1"
    kinds = [t[0] for t in traces]
    assert "tool_call" in kinds and "tool_result" in kinds and "final" in kinds
    # tool result must be replayed back to the model as a tool message
    tool_msgs = [m for m in seen_msgs[-1] if m.role == "tool"]
    assert tool_msgs and json.loads(tool_msgs[0].content)["jobs"]


async def test_subagent_handoff(env, monkeypatch):
    traces, _ = env
    # career -> transfer_to(job_research) -> sub search_jobs -> sub report -> career final
    script = iter([
        _resp(tool_calls=[ToolCall(id="t1", name="transfer_to",
                                   arguments={"agent": "job_research",
                                              "task": "find remote Java jobs"})]),
        _resp(tool_calls=[ToolCall(id="c1", name="search_jobs",
                                   arguments={"query": "java"})]),
        _resp(text="SUBREPORT: 3 remote Java roles found"),
        _resp(text="I searched remote Java roles via the job research agent."),
    ])
    tool_names_seen: list[list[str]] = []

    async def fake_ask(req, **kw):
        tool_names_seen.append([t.name for t in (req.tools or [])])
        return next(script)

    async def fake_handler(user_id, **kw):
        return {"jobs": [{"id": "j9", "title": "Java Dev", "company": "Y",
                          "location": "Remote", "remote": "remote",
                          "salary": None, "skills": ["Java"]}]}

    monkeypatch.setattr(orchestrator.ai, "ask", fake_ask)
    monkeypatch.setattr(TOOL_INDEX["search_jobs"], "handler", fake_handler)

    out = await orchestrator.career_turn(user_id="u1", message="找远程 Java 岗位",
                                         run_id="r2")

    assert "job research agent" in out.answer
    handoffs = [t for t in traces if t[0] == "handoff"]
    assert handoffs and handoffs[0][2]["to"] == "job_research"
    # subagent must NOT see transfer_to (no recursive handoff) and gets a
    # restricted tool surface
    sub_call = tool_names_seen[1]
    assert "transfer_to" not in sub_call
    assert set(sub_call) <= set(orchestrator.SUBAGENT_TOOLS["job_research"])
    assert out.tools_used == ["search_jobs"]  # only from the sub run


async def test_step_budget_guard(env, monkeypatch):
    traces, _ = env

    async def endless(req, **kw):
        return _resp(tool_calls=[ToolCall(id="x", name="save_job",
                                          arguments={"job_id": "j1"})])

    async def fake_save(user_id, **kw):
        return {"saved": True}

    async def final_ish(req, **kw):  # finalize call after budget
        return _resp(text="Summary after budget.")

    state = {"n": 0}

    async def router(req, **kw):
        state["n"] += 1
        return await (endless(req) if "Step budget reached" not in
                      req.messages[-1].content else final_ish(req))

    monkeypatch.setattr(orchestrator.ai, "ask", router)
    monkeypatch.setattr(TOOL_INDEX["save_job"], "handler", fake_save)
    monkeypatch.setattr(orchestrator, "MAX_STEPS", 3)

    out = await orchestrator.career_turn(user_id="u1", message="save it", run_id="r3")
    assert out.answer == "Summary after budget."
    assert out.steps == 3


async def test_tool_error_is_reported_not_raised(env, monkeypatch):
    traces, _ = env

    async def boom(req, **kw):
        if any(m.role == "tool" for m in req.messages):
            err = json.loads(req.messages[-1].content)
            return _resp(text=f"recovered: {err['error']}")
        return _resp(tool_calls=[ToolCall(id="c1", name="get_job",
                                         arguments={"job_id": "nope"})])

    async def bad_handler(user_id, **kw):
        raise RuntimeError("db exploded")

    monkeypatch.setattr(orchestrator.ai, "ask", boom)
    monkeypatch.setattr(TOOL_INDEX["get_job"], "handler", bad_handler)

    out = await orchestrator.career_turn(user_id="u1", message="job?", run_id="r4")
    assert "db exploded" in out.answer
    result = [t for t in traces if t[0] == "tool_result"][0]
    assert result[2]["ok"] is False
