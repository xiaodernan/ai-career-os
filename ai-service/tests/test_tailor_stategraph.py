"""The tailor loop on the StateGraph spine (Epic 269).

Every test below runs the real deterministic verifier — the whole point of the
graph is that the LLM gets a second chance to earn its edit, or the original
wording ships. The LLM and retrieval are canned; the gate is not.
"""

import pytest

from app.features import tailor as tailor_module

RESUME_STRUCTURED = {
    "profile": {"name": "Ada", "headline": "systems engineer", "summary": "old"},
    "experience": [{"company": "Acme", "bullets": ["Led the PostgreSQL migration", "Cut p95 latency"]}],
    "projects": [{"name": "Migration", "bullets": ["Ran the cutover"]}],
    "skills": [{"name": "PostgreSQL"}, {"name": "Go"}],
}
RESUME_TEXT = "Led the PostgreSQL migration at Acme; cut p95 latency; Go microservices; cutover automation."

JD = {"title": "Database engineer", "requiredSkills": [{"name": "PostgreSQL"}],
      "preferredSkills": [{"name": "Go"}]}


def _canned_responses(responses):
    calls = []

    async def fake_ask_json(req, **kw):
        calls.append(req)
        idx = min(len(calls) - 1, len(responses) - 1)
        return responses[idx]

    return calls, fake_ask_json


async def fake_retrieve(query, **kw):
    return {"context_block": "CONTEXT", "evidence": [{"id": "src-1"}]}


def _any_rejected_change():
    return [
        {"section": "experience", "index": 0,
         "before": "Led the PostgreSQL migration",
         "after": "Ran the Kubernetes operator migration end to end",
         "reason": "JD mentions operators"},
    ]


def _clean_change():
    return [
        {"section": "experience", "index": 0,
         "before": "Cut p95 latency",
         "after": "Trimmed p95 latency across the migration cohort",
         "reason": "keep the JD's number-first posture"},
    ]


@pytest.mark.asyncio
async def test_invented_edit_is_rejected_then_revised(monkeypatch):
    responses = [
        {"changes": _any_rejected_change(), "summary": "old", "skillOrder": [], "notes": []},
        {"changes": _clean_change(), "summary": "old", "skillOrder": [],
         "notes": ["double-check one metric"]},
    ]
    calls, fake = _canned_responses(responses)
    monkeypatch.setattr(tailor_module, "ask_json", fake)
    monkeypatch.setattr(tailor_module, "retrieve", fake_retrieve)

    out = await tailor_module.tailor(RESUME_STRUCTURED, RESUME_TEXT, JD, user_id="u-1",
                                     job_title="DBA", run_id=None)

    assert len(calls) == 2, "the verifier sent it back exactly once"
    assert [c["section"] for c in out["diff"]["accepted"]] == ["experience"]
    assert out["diff"]["rejected"][0]["verifier_reject"].startswith("invented")
    assert out["stats"] == {"accepted": 1, "rejected": 1}
    assert out["notes"] == ["double-check one metric"]
    assert out["evidence"] == [{"id": "src-1"}]


@pytest.mark.asyncio
async def test_clean_first_draft_costs_exactly_one_call(monkeypatch):
    responses = [{"changes": _clean_change(), "summary": "", "skillOrder": [], "notes": []}]
    calls, fake = _canned_responses(responses)
    monkeypatch.setattr(tailor_module, "ask_json", fake)
    monkeypatch.setattr(tailor_module, "retrieve", fake_retrieve)

    out = await tailor_module.tailor(RESUME_STRUCTURED, RESUME_TEXT, JD, user_id="u-1",
                                     job_title="DBA", run_id=None)

    assert len(calls) == 1
    assert out["stats"] == {"accepted": 1, "rejected": 0}
    assert out["diff"]["rejected"] == []


@pytest.mark.asyncio
async def test_a_both_rejected_world_still_renders_without_a_crash(monkeypatch):
    responses = [
        {"changes": _any_rejected_change(), "summary": "", "skillOrder": [], "notes": []},
        {"changes": _any_rejected_change(), "summary": "", "skillOrder": [], "notes": []},
    ]
    calls, fake = _canned_responses(responses)
    monkeypatch.setattr(tailor_module, "ask_json", fake)
    monkeypatch.setattr(tailor_module, "retrieve", fake_retrieve)

    out = await tailor_module.tailor(RESUME_STRUCTURED, RESUME_TEXT, JD, user_id="u-1",
                                     job_title="DBA", run_id=None)

    assert len(calls) == 2, "bounded: exactly two drafts, never more"
    assert out["stats"] == {"accepted": 0, "rejected": 2}
    assert out["tailored"]["experience"][0]["bullets"][0] == "Led the PostgreSQL migration"


def test_the_verifier_itself_names_inventions():
    rejected = tailor_module.verify_no_fabrication(
        RESUME_TEXT, "", "Ran the Kubernetes operator migration")
    assert rejected is not None and rejected.startswith("invented")
    assert tailor_module.verify_no_fabrication(RESUME_TEXT, "", "Trimmed p95 latency") is None
