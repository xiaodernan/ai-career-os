"""Epic 274 -- the Interview Story Forge.

The point of this feature is twofold: an LLM-driven *state transition* (writer →
skeptical interviewer → writer again) and a deterministic verifier that strikes
any figure the reader's own note did not carry. These tests stub the LLM at the
module boundary so the graph, the routing and the verifier are all exercised
offline, exactly like the other StateGraph features.
"""

import pytest

from app.features import story_forge as forge


def test_note_numbers_collects_digit_runs():
    # p99's "99" is a digit-run too -- the verifier is intentionally conservative:
    # it allow-lists every run it sees rather than guessing which are "metrics".
    assert forge._note_numbers("cut p99 by 30% in 2 weeks, from 400ms") == {
        "99", "30%", "2", "400"}


def test_story_fields_tolerates_degenerate_replies():
    assert forge._story_fields(None) == {"situation": "", "task": "", "action": "", "result": ""}
    assert forge._story_fields({"action": 42, "result": "kept"}) == {
        "situation": "", "task": "", "action": "", "result": "kept"}


def _stub_sequence(monkeypatch, replies):
    """Feed one LLM reply per node call, in graph order (draft, challenge, revise)."""
    calls = {"n": 0}

    async def fake_ask_json(req, *, user_id=None, run_id=None, agent="system", kind="chat"):
        i = calls["n"]
        calls["n"] += 1
        return replies[min(i, len(replies) - 1)]

    monkeypatch.setattr(forge, "ask_json", fake_ask_json)
    return calls


@pytest.mark.asyncio
async def test_forge_runs_every_graph_node_and_traces_them(monkeypatch):
    """draft→challenge→revise→verify→render all execute; open challenges survive."""
    _stub_sequence(monkeypatch, [
        {"situation": "S", "task": "T", "action": "A", "result": "cut latency 30%"},
        {"challenges": [{"target": "action", "question": "How exactly?",
                         "closable": "no", "hint": ""}]},
        {"situation": "S", "task": "T", "action": "A", "result": "cut latency 30%",
         "closed": [], "open": [{"question": "How exactly?", "reason": "note is vague"}]},
    ])
    out = await forge.forge_story("I cut latency 30% on the payment service.")
    assert out["story"]["result"] == "cut latency 30%"
    assert out["open"] == [{"question": "How exactly?", "reason": "note is vague"}]
    assert out["complete"] is False  # an open challenge means the story is not defensible yet


@pytest.mark.asyncio
async def test_verifier_strikes_an_invented_figure(monkeypatch):
    """A number the note never carried is struck from the field that carries it."""
    _stub_sequence(monkeypatch, [
        {"situation": "S", "task": "T", "action": "A", "result": "cut latency 90%"},
        {"challenges": []},
        {"situation": "S", "task": "T", "action": "A", "result": "cut latency 90%",
         "closed": [], "open": []},
    ])
    out = await forge.forge_story("I cut latency 30% on the payment service.")
    # 90% is not in the note -> the result field is emptied and flagged.
    assert out["story"]["result"] == ""
    assert "result" in out["struck_fields"]


@pytest.mark.asyncio
async def test_verifier_keeps_a_sourced_figure(monkeypatch):
    _stub_sequence(monkeypatch, [
        {"situation": "S", "task": "T", "action": "A", "result": "cut latency 30%"},
        {"challenges": []},
        {"situation": "S", "task": "T", "action": "A", "result": "cut latency 30%",
         "closed": ["any?"], "open": []},
    ])
    out = await forge.forge_story("I cut latency 30% on the payment service.")
    assert out["story"]["result"] == "cut latency 30%"
    assert out["struck_fields"] == []
    assert out["complete"] is True


@pytest.mark.asyncio
async def test_forge_survives_degenerate_llm_output(monkeypatch):
    """Garbage from the model still yields a shaped result, never an exception."""
    _stub_sequence(monkeypatch, [{"answer": "nonsense"}])
    out = await forge.forge_story("I did a thing.")
    assert set(out) >= {"story", "open", "closed", "struck_fields", "complete", "locale"}
    assert out["story"] == {"situation": "", "task": "", "action": "", "result": ""}
    assert out["complete"] is False
