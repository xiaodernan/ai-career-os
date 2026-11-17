"""Epic 316: the match narrative may state only numbers the wire computed.

The match engine computes every number (overall, the four subscores, years of
experience, the JD's bar, the skill counts) and then let a model recite prose
over them without looking at what it actually said. These tests pin the
replacement contract: a draft that recites an invented percentage or an invented
year count is rejected once, rewritten once, and — if it still invents — replaced
with the computed facts themselves. The accepted prose is verified byte-consistent
with the computed set ±0.5 of float slack, never with vibes.
"""
from __future__ import annotations

import pytest

from app.features import match as match_mod
from app.features.match import compute_match


_RESUME = {"skills": [{"name": "Java"}],
           "experience": [{"company": "X", "title": "Engineer",
                           "start": "2019-01", "end": "present",
                           "bullets": ["Java services"]}],
           "projects": [],
           "education": [{"degree": "bachelor"}],
           "profile": {}}

_JD = {"title": "Senior Java Engineer", "company": "Rosette",
       "experienceYears": 3,
       "education": {"minDegree": "bachelor"},
       "requiredSkills": [{"name": "Kubernetes", "priority": "must", "evidence_phrase": "k8s"}],
       "preferredSkills": [{"name": "Rust", "priority": "nice"}],
       "interviewTopics": []}


def _stub_io(monkeypatch, calls: list, responses: list[str]):
    from app.providers.base import LLMResponse

    state = {"n": 0}

    async def fake_ask(req, *, user_id=None, run_id=None, agent="system", kind="chat"):
        calls.append(("ask", agent, kind))
        idx = min(state["n"], len(responses) - 1)
        text = responses[idx]
        state["n"] += 1
        return LLMResponse(text=text, model="mock-model")

    async def fake_keyword_search(user_id, term, k=5, kinds=None):
        calls.append(("search", term))
        return [{"id": "chunk-1", "text": f"built {term} at work",
                 "doc_title": "Resume", "section_path": "experience"}]

    monkeypatch.setattr(match_mod, "ask", fake_ask)
    monkeypatch.setattr(match_mod.store, "keyword_search", fake_keyword_search)


def test_clean_narrative_is_accepted(monkeypatch):
    calls: list = []
    _stub_io(monkeypatch, calls,
             ["Overall 45%. Six years of experience against their three. Fastest win: ship Rust."])
    result = _run(monkeypatch)
    assert result["narrative"].startswith("Overall 45%")
    assert result["model"] == "mock-model"
    assert calls.count(("ask", "jd_analyst", "match_narrative")) == 1


def test_invented_percentage_is_rejected_once_then_revised(monkeypatch):
    calls: list = []
    _stub_io(monkeypatch, calls, ["94% match with flair.", "45% overall; 6 of 3 years."])
    result = _run(monkeypatch)
    assert result["narrative"].startswith("45% overall")
    assert calls.count(("ask", "jd_analyst", "match_narrative")) == 2  # one bounded revision


def test_invented_percentage_retry_included_falls_back_to_facts(monkeypatch):
    calls: list = []
    _stub_io(monkeypatch, calls, ["94% match.", "81% is my take."])
    result = _run(monkeypatch)
    assert result["narrative"].startswith("Computed scores")  # the computed facts, not the invention
    assert result["model"] == ""
    assert calls.count(("ask", "jd_analyst", "match_narrative")) == 2


def test_invented_years_are_rejected(monkeypatch):
    calls: list = []
    _stub_io(monkeypatch, calls, ["Nine years against their three.", "6 years against the 3 required. 45%."])
    result = _run(monkeypatch)
    assert result["narrative"].startswith("6 years")  # retry accepted
    assert calls.count(("ask", "jd_analyst", "match_narrative")) == 2


def test_provider_failure_falls_back_to_the_computed_facts(monkeypatch):
    from app.providers.base import LLMMessage  # noqa: F401  (kept for symmetry with the stub harness)

    calls: list = []

    async def boom(req, **kw):
        calls.append(("ask-failed",))
        raise RuntimeError("provider down")

    async def fake_keyword_search(user_id, term, k=5, kinds=None):
        return []

    monkeypatch.setattr(match_mod, "ask", boom)
    monkeypatch.setattr(match_mod.store, "keyword_search", fake_keyword_search)
    result = _run(monkeypatch)
    assert result["narrative"].startswith("Computed scores")
    assert result["model"] == ""


def test_the_auditor_itself():
    from app.features.match import _audit_narrative_numbers

    ok = _audit_narrative_numbers("45% and 6 years, 3 years required, of 3 skills",
                                  {45, 0, 100, 35}, [6.0, 3.0])
    assert ok == []
    flagged = _audit_narrative_numbers("94% and 9 years", {45, 0, 100, 35}, [6.0, 3.0])
    assert flagged == ["94%", "9 years"]
    word = _audit_narrative_numbers("Nine years versus their three.",
                                    {45, 0, 100, 35}, [6.0, 3.0])
    assert word == ["Nine years"]
    chinese = _audit_narrative_numbers("约九年经验，要求三年。", {45, 0, 100, 35}, [6.0, 3.0])
    assert chinese == ["九年"]


def _run(monkeypatch):
    import asyncio
    return asyncio.run(compute_match(_RESUME, _JD, user_id="u-1"))
