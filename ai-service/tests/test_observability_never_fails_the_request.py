"""Telemetry must never fail the request it observes.

`trace()` runs on every step of every copilot turn, `record_usage()` after every
model call, and `finish_run()` at the end -- often from inside an `except`
handler. All three wrote to Postgres with no protection, so a failed INSERT on
`agent_traces` aborted a turn that had already produced its answer, and a failed
`finish_run` in an `except` handler replaced the exception that actually failed
the request. These tests pin the rule: a telemetry write logs and returns.

`create_run` is the deliberate exception: it returns the id every later write
needs, so a silent failure there would hand the caller an id nothing accepts.
"""

import logging

import pytest

import app.core.db as db
from app.agents import orchestrator
from app.agents.orchestrator import Outcome
from app.agents.tools import Tool
from app.api import agents as agents_api
from app.core.deps import Ctx
from app.db import observability

RUN = "33333333-3333-3333-3333-333333333333"


@pytest.fixture()
def dead_db(monkeypatch):
    async def boom(query, *args):
        raise ConnectionError("connection reset by peer")

    monkeypatch.setattr(db, "execute", boom)
    monkeypatch.setattr(db, "fetchrow", boom)
    return boom


@pytest.mark.asyncio
async def test_trace_does_not_raise_when_its_insert_fails(dead_db, caplog):
    with caplog.at_level(logging.WARNING, logger="db.observability"):
        await observability.trace(RUN, "tool_call", "career", {"tool": "search_jobs"})
    assert any("trace" in r.message for r in caplog.records), \
        "a dropped trace must be logged, not silently discarded"


@pytest.mark.asyncio
async def test_record_usage_does_not_raise_when_its_insert_fails(dead_db):
    await observability.record_usage(
        "u1", RUN, "mock", "mock", "chat", 10, 5, 0, 0.0, 120)


@pytest.mark.asyncio
async def test_finish_run_does_not_raise_when_its_update_fails(dead_db):
    await observability.finish_run(RUN, "completed", in_tok=10, out_tok=5)


@pytest.mark.asyncio
async def test_finish_run_does_not_raise_when_the_ledger_read_fails(dead_db):
    # The totals come from a read; that read is as fallible as the write.
    await observability.finish_run(RUN, "completed", latency_ms=900)


@pytest.mark.asyncio
async def test_a_failed_finish_does_not_replace_the_error_that_failed_the_request(monkeypatch):
    async def boom(query, *args):
        raise ConnectionError("db gone")

    monkeypatch.setattr(db, "execute", boom)

    # This is the shape of every caller's `except` block: if finish_run raises, the
    # caller's original error is replaced by the telemetry error.
    try:
        raise ValueError("the real failure")
    except ValueError:
        await observability.finish_run(RUN, "failed", error="the real failure")


@pytest.mark.asyncio
async def test_create_run_still_raises_because_its_id_is_load_bearing(dead_db):
    with pytest.raises(ConnectionError):
        await observability.create_run("u1", "career", "chat")


@pytest.mark.asyncio
async def test_a_dead_trace_does_not_corrupt_a_successful_tool_result(dead_db):
    async def handler(user_id, **kw):
        return {"jobs": [{"id": "j1"}]}

    tool = Tool("search_jobs", "", {"type": "object", "properties": {}}, handler)
    out = Outcome()

    result = await orchestrator._exec_tool(tool, "u1", {}, run_id=RUN,
                                           agent="career", task_id=None, out=out)
    assert result == {"jobs": [{"id": "j1"}]}, \
        "a failed trace must not turn a successful tool call into an error"


@pytest.mark.asyncio
async def test_chat_sync_releases_the_trace_sequence_it_used(monkeypatch):
    class Out:
        answer = "hi"

        def to_dict(self):
            return {"answer": "hi"}

    async def fake_turn(**kw):
        return Out()

    async def noop(*a, **k):
        return None

    monkeypatch.setattr(agents_api, "career_turn", fake_turn)
    monkeypatch.setattr(observability, "finish_run", noop)
    monkeypatch.setattr(agents_api.memory, "extract_and_store", noop)
    observability._trace_seq[RUN] = 3  # what a real turn's traces leave behind

    await agents_api.chat_sync(agents_api.ChatReq(message="hi"),
                               Ctx(user_id="u1", run_id=RUN))
    assert RUN not in observability._trace_seq


@pytest.mark.asyncio
async def test_chat_sync_releases_the_sequence_even_when_the_turn_fails(monkeypatch):
    from fastapi import HTTPException

    async def fake_turn(**kw):
        raise RuntimeError("provider down")

    async def noop(*a, **k):
        return None

    monkeypatch.setattr(agents_api, "career_turn", fake_turn)
    monkeypatch.setattr(observability, "finish_run", noop)
    observability._trace_seq[RUN] = 7

    with pytest.raises(HTTPException):
        await agents_api.chat_sync(agents_api.ChatReq(message="hi"),
                                   Ctx(user_id="u1", run_id=RUN))
    assert RUN not in observability._trace_seq, \
        "the failure path is exactly where a leaked sequence would survive"
