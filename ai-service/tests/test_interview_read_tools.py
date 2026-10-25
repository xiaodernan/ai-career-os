"""The interview surface could create and grade, but never read.

`create_interview` started a session and `evaluate_answer` graded one answer, so
the agent could run a practice exchange but not answer "how did my last mock
interview go?" or follow the `open_interview` action it emits itself.
`list_interviews` and `get_interview_session` are that read.

jsonb comes back from asyncpg as *text* (no codec is registered on the pool), so
these tests also pin the parsing: a tool that iterated the characters of a JSON
string would hand the model nonsense rather than an error.
"""

import json

import pytest

from app.agents import tools


def _session_row(**kw):
    base = {"id": "s1", "mode": "technical", "status": "completed", "difficulty": 0.5,
            "company_name": "Acme", "position_title": "Backend Engineer",
            "started_at": "2026-10-20T10:00:00", "finished_at": "2026-10-20T10:30:00",
            "turns": 6, "dims": json.dumps({"depth": 0.7, "communication": 0.8})}
    base.update(kw)
    return base


def _turn_row(seq, role="interviewer", content="Tell me about Kafka"):
    return {"id": f"t{seq}", "seq": seq, "role": role, "content": content,
            "question_meta": json.dumps({"topic": "kafka"}),
            "evaluation": json.dumps({"score": 0.6})}


@pytest.mark.asyncio
async def test_list_interviews_returns_the_history_with_parsed_scores(monkeypatch):
    captured: dict = {}

    async def fake_fetch(query, *args):
        captured["sql"], captured["args"] = query, args
        return [_session_row(), _session_row(id="s2", status="active", dims=None,
                                             finished_at=None, turns=2)]

    monkeypatch.setattr(tools.db, "fetch", fake_fetch)
    out = await tools.list_interviews("u1")

    assert [i["session_id"] for i in out["interviews"]] == ["s1", "s2"]
    assert out["interviews"][0]["scores"] == {"depth": 0.7, "communication": 0.8}, \
        "jsonb arrives as text; the tool must parse it, not iterate its characters"
    assert out["interviews"][1]["scores"] is None       # unfinished: no evaluation row
    assert out["interviews"][1]["finished_at"] is None
    assert out["interviews"][0]["turns"] == 6
    assert "ORDER BY s.started_at DESC" in captured["sql"]
    assert captured["args"][0] == "u1"


@pytest.mark.asyncio
async def test_list_interviews_clamps_a_bad_limit(monkeypatch):
    captured: dict = {}

    async def fake_fetch(query, *args):
        captured["args"] = args
        return []

    monkeypatch.setattr(tools.db, "fetch", fake_fetch)
    await tools.list_interviews("u1", limit="lots")
    assert captured["args"][-1] == 10
    await tools.list_interviews("u1", limit=999)
    assert captured["args"][-1] == 25


@pytest.mark.asyncio
async def test_get_interview_session_returns_the_turns_and_their_scores(monkeypatch):
    async def fake_session(session_id, user_id):
        return dict(_session_row(id=session_id))

    async def fake_turns(session_id):
        return [_turn_row(1), _turn_row(2, role="candidate", content="I built a pipeline"),
                _turn_row(3)]

    monkeypatch.setattr(tools.domain, "get_interview_session", fake_session)
    monkeypatch.setattr(tools.domain, "list_turns", fake_turns)

    out = await tools.get_interview_session("u1", session_id="s1")
    assert out["session"]["session_id"] == "s1"
    assert out["session"]["position"] == "Backend Engineer"
    assert out["turns_total"] == 3
    assert [t["seq"] for t in out["turns"]] == [1, 2, 3]
    assert out["turns"][0]["question_meta"] == {"topic": "kafka"}
    assert out["turns"][0]["evaluation"] == {"score": 0.6}


@pytest.mark.asyncio
async def test_get_interview_session_keeps_the_most_recent_turns(monkeypatch):
    async def fake_session(session_id, user_id):
        return dict(_session_row(id=session_id))

    async def fake_turns(session_id):
        return [_turn_row(i) for i in range(1, 21)]

    monkeypatch.setattr(tools.domain, "get_interview_session", fake_session)
    monkeypatch.setattr(tools.domain, "list_turns", fake_turns)

    out = await tools.get_interview_session("u1", session_id="s1", turns=3)
    assert [t["seq"] for t in out["turns"]] == [18, 19, 20], \
        "the recent exchange is what a review asks about, and turns_total says what was cut"
    assert out["turns_total"] == 20


@pytest.mark.asyncio
async def test_an_unknown_session_is_an_error_the_model_can_read(monkeypatch):
    async def no_session(session_id, user_id):
        return None

    monkeypatch.setattr(tools.domain, "get_interview_session", no_session)
    out = await tools.get_interview_session("u1", session_id="missing")
    assert out == {"error": "interview session not found"}


@pytest.mark.asyncio
async def test_a_malformed_jsonb_column_degrades_instead_of_raising(monkeypatch):
    async def fake_session(session_id, user_id):
        return dict(_session_row(id=session_id))

    async def fake_turns(session_id):
        return [{"seq": 1, "role": "candidate", "content": "x",
                 "question_meta": "{not json", "evaluation": None}]

    monkeypatch.setattr(tools.domain, "get_interview_session", fake_session)
    monkeypatch.setattr(tools.domain, "list_turns", fake_turns)

    out = await tools.get_interview_session("u1", session_id="s1")
    assert out["turns"][0]["question_meta"] is None
    assert out["turns"][0]["evaluation"] is None


def test_the_interview_subagent_can_reach_both_read_tools():
    whitelist = tools.SUBAGENT_TOOLS["interview"]
    assert "list_interviews" in whitelist and "get_interview_session" in whitelist
