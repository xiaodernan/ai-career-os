"""Long-term memory is a prompt enhancement, so it may not decide whether a turn runs.

`build_memory_context` is awaited at the very start of every copilot turn, before
any tool. It read `m["kind"]` / `m["content"]` directly and let a DB error
propagate, so a memory read failure -- or one row missing a column -- aborted the
turn before the first tool call. The write side (`extract_and_store`) was already
documented as best-effort; these tests hold the read side to the same rule.
"""

import logging

import pytest

from app.agents import memory


class Recorder:
    def __init__(self, rows=None, exc=None):
        self.rows, self.exc = rows, exc

    async def __call__(self, user_id, limit=40):
        if self.exc:
            raise self.exc
        return self.rows


def _patch(monkeypatch, rows=None, exc=None):
    monkeypatch.setattr(memory.domain, "get_memories", Recorder(rows, exc))


@pytest.mark.asyncio
async def test_a_failed_read_yields_no_context_instead_of_failing_the_turn(monkeypatch, caplog):
    _patch(monkeypatch, exc=ConnectionError("db reset"))
    with caplog.at_level(logging.WARNING, logger="agents.memory"):
        assert await memory.build_memory_context("u1") == ""
    assert any("memory context" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_malformed_rows_are_skipped_rather_than_raising(monkeypatch):
    _patch(monkeypatch, rows=[
        "not a row",
        None,
        {"kind": "skill"},                      # no content
        {"kind": "skill", "content": None},      # present but null
        {"kind": "skill", "content": "   "},     # blank
        {"kind": "skill", "content": "Kafka"},   # the one usable row
    ])
    ctx = await memory.build_memory_context("u1")
    assert "Kafka" in ctx
    assert ctx.count("- [") == 1


@pytest.mark.asyncio
async def test_the_prompt_keeps_the_label_and_the_key(monkeypatch):
    _patch(monkeypatch, rows=[
        {"kind": "skill", "key": "streaming", "content": "Kafka and Flink"},
        {"kind": "goal", "content": "Move to a platform team"},
    ])
    ctx = await memory.build_memory_context("u1")
    assert "## Long-term memory about this user" in ctx
    assert "- [Skills] streaming: Kafka and Flink" in ctx
    assert "- [Goals] Move to a platform team" in ctx


@pytest.mark.asyncio
async def test_an_unknown_kind_is_its_own_label(monkeypatch):
    _patch(monkeypatch, rows=[{"kind": "unexpected", "content": "x"}])
    ctx = await memory.build_memory_context("u1")
    assert "- [unexpected] x" in ctx


@pytest.mark.asyncio
async def test_no_usable_rows_means_no_header_only_block(monkeypatch):
    # A bare "## Long-term memory" header with nothing under it is noise in the
    # system prompt; an empty string lets the caller skip the section entirely.
    _patch(monkeypatch, rows=[{"kind": "skill"}, None])
    assert await memory.build_memory_context("u1") == ""


@pytest.mark.asyncio
async def test_no_memories_is_an_empty_string(monkeypatch):
    _patch(monkeypatch, rows=[])
    assert await memory.build_memory_context("u1") == ""
