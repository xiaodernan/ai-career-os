"""The tracker could write the pipeline but not read it.

`save_job` and `update_application_status` both existed, so the agent could move a
role from `saved` to `interview` -- but "what am I still waiting on?", the question
the tracker exists for, had no tool to answer it. `list_applications` is that read,
and it shares one stage vocabulary with the write tool so a stage the agent can set
is always a stage it can filter on.
"""

import pytest

from app.agents import tools


def _row(**kw):
    base = {"id": "a1", "job_id": "j1", "title": "Backend Engineer",
            "company_name": "Acme", "status": "applied",
            "applied_at": "2026-10-01T00:00:00", "updated_at": "2026-10-02T00:00:00"}
    base.update(kw)
    return base


@pytest.mark.asyncio
async def test_list_applications_returns_the_pipeline_and_the_stage_counts(monkeypatch):
    captured: dict = {}

    async def fake_fetch(query, *args):
        captured["sql"], captured["args"] = query, args
        return [_row(id="a1", status="applied"), _row(id="a2", status="interview",
                                                      job_id=None, applied_at=None)]

    monkeypatch.setattr(tools.db, "fetch", fake_fetch)
    out = await tools.list_applications("u1")

    assert [a["status"] for a in out["applications"]] == ["applied", "interview"]
    assert out["counts_by_status"] == {"applied": 1, "interview": 1}
    assert out["applications"][1]["job_id"] is None
    assert out["applications"][1]["applied_at"] is None
    assert "user_id = $1::uuid" in captured["sql"]
    assert "ORDER BY updated_at DESC" in captured["sql"], \
        "the item a user is chasing is the one that moved last"
    assert captured["args"][0] == "u1"


@pytest.mark.asyncio
async def test_list_applications_filters_by_stage(monkeypatch):
    captured: dict = {}

    async def fake_fetch(query, *args):
        captured["sql"], captured["args"] = query, args
        return []

    monkeypatch.setattr(tools.db, "fetch", fake_fetch)
    await tools.list_applications("u1", status="offer")
    assert "status = $2" in captured["sql"]
    assert captured["args"][1] == "offer"


@pytest.mark.asyncio
async def test_an_unknown_stage_is_rejected_with_the_ones_that_exist(monkeypatch):
    async def must_not_run(query, *args):
        raise AssertionError("an unknown stage reached the database")

    monkeypatch.setattr(tools.db, "fetch", must_not_run)
    out = await tools.list_applications("u1", status="ghosted")
    assert "ghosted" in out["error"]
    assert "offer" in out["error"]  # names a stage the model can retry with


@pytest.mark.asyncio
async def test_list_applications_clamps_a_bad_limit(monkeypatch):
    captured: dict = {}

    async def fake_fetch(query, *args):
        captured["args"] = args
        return []

    monkeypatch.setattr(tools.db, "fetch", fake_fetch)
    await tools.list_applications("u1", limit="lots")
    assert captured["args"][-1] == 20          # the tool's default, not a raise
    await tools.list_applications("u1", limit=999)
    assert captured["args"][-1] == 50          # bounded


def test_the_two_pipeline_tools_share_one_stage_vocabulary():
    by_name = {t.name: t for t in tools.ALL_TOOLS}
    read_enum = by_name["list_applications"].parameters["properties"]["status"]["enum"]
    write_enum = by_name["update_application_status"].parameters["properties"]["status"]["enum"]
    assert read_enum == write_enum == list(tools.APPLICATION_STATUSES), \
        "a stage the write tool accepts must be one the read tool can filter on"


@pytest.mark.asyncio
async def test_the_write_tool_accepts_every_stage_the_read_tool_offers(monkeypatch):
    async def fake_fetchrow(query, *args):
        return {"id": "a1"}

    monkeypatch.setattr(tools.db, "fetchrow", fake_fetchrow)
    for stage in tools.APPLICATION_STATUSES:
        out = await tools.update_application_status("u1", application_id="a1",
                                                    status=stage)
        assert out.get("updated") is True, stage
    bad = await tools.update_application_status("u1", application_id="a1",
                                                status="ghosted")
    assert bad == {"error": "invalid status"}


def test_the_tracker_subagent_can_actually_reach_the_read_tool():
    assert "list_applications" in tools.SUBAGENT_TOOLS["tracker"]
