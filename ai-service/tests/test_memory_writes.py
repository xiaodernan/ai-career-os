"""Long-term memory: the write paths (PRD §17).

No DB and no LLM. `domain.upsert_memory` / `observability.trace` are stubbed on the
modules `memory` imported, so a failure inside either never raises here.
"""

from app.agents import memory


def _stub(monkeypatch, store, traces):
    async def fake_upsert(user_id, kind, key, content, source, importance):
        store.append({"user_id": user_id, "kind": kind, "key": key,
                      "content": content, "source": source, "importance": importance})

    async def fake_trace(run_id, kind, agent, payload):
        traces.append({"run_id": run_id, "kind": kind, "agent": agent, "payload": payload})

    monkeypatch.setattr(memory.domain, "upsert_memory", fake_upsert)
    monkeypatch.setattr(memory.observability, "trace", fake_trace)


def _eval(**override):
    base = {
        "what_you_did_well": ["Clear structure."],
        "what_was_weak": ["No rollback plan", "Shallow on backpressure"],
        "missing_concepts": ["bulkheads", "load shedding"],
        "better_answers": [],
        "follow_up_questions_to_prepare": [],
        "recommended_study": [],
    }
    base.update(override)
    return base


def test_interview_outcome_is_stored_as_interview_kind_memory(monkeypatch):
    store, traces = [], []
    _stub(monkeypatch, store, traces)

    saved = __import__("asyncio").run(memory.record_interview_outcome(
        "u1", "session-abcdef0123", _eval(), run_id="r1"))

    assert saved == 1
    assert len(store) == 1
    row = store[0]
    assert row["kind"] == "interview"
    assert row["source"] == "interview"
    assert row["key"] == "interview:session-abcd"
    assert row["importance"] == 0.7
    # Only the verdict, capped -- never the transcript.
    assert "No rollback plan" in row["content"]
    assert "bulkheads" in row["content"]
    assert traces and traces[0]["payload"]["stage"] == "memory_write"


def test_an_interview_with_no_findings_writes_nothing(monkeypatch):
    """A clean report has no weak areas and no missing concepts; storing an empty
    memory is noise, and the answer is not a 1 to keep the rate honest."""
    store, traces = [], []
    _stub(monkeypatch, store, traces)

    saved = __import__("asyncio").run(memory.record_interview_outcome(
        "u1", "s", _eval(what_was_weak=[], missing_concepts=[]), run_id="r1"))
    assert saved == 0
    assert store == []
    assert traces == []


def test_only_strengths_is_not_a_finding(monkeypatch):
    store, traces = [], []
    _stub(monkeypatch, store, traces)
    saved = __import__("asyncio").run(memory.record_interview_outcome(
        "u1", "s", _eval(what_was_weak=[], missing_concepts=[]), run_id="r1"))
    assert saved == 0
    assert store == []


def test_a_write_failure_is_best_effort(monkeypatch):
    """A failed memory write must not fail the finalize the user is waiting on."""
    traces = []

    async def boom(*args, **kwargs):
        raise RuntimeError("db down")

    async def fake_trace(run_id, kind, agent, payload):
        traces.append(payload)

    monkeypatch.setattr(memory.domain, "upsert_memory", boom)
    monkeypatch.setattr(memory.observability, "trace", fake_trace)

    saved = __import__("asyncio").run(memory.record_interview_outcome(
        "u1", "s", _eval(), run_id="r1"))
    assert saved == 0


def test_the_three_caps_hold(monkeypatch):
    store, traces = [], []
    _stub(monkeypatch, store, traces)
    loud = _eval(what_was_weak=[f"w{i}" for i in range(10)],
                 missing_concepts=[f"c{i}" for i in range(10)])
    __import__("asyncio").run(memory.record_interview_outcome("u", "s", loud))
    assert store
    # 3 + 3 items, not 10 + 10.
    assert store[0]["content"].count(";") == 4
