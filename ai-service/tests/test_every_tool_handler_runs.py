"""Every tool handler must actually be executed by at least one test.

`tools.compare_offers` called `benchmark(...)` without importing it, so every
"which offer leads?" request raised NameError and came back as a tool error. The
suite was green because every offers test went through `features.offers` -- the
engine -- and none went through the tool. Importing a module is not the same as
calling it, and a handler nobody calls is a handler nobody has run.

This file is the smoke gate for the handlers that had no caller: each one is
invoked with its dependencies stubbed, and the result is checked for an `error`
key. It is deliberately shallow -- it proves the body runs, not that the feature
is right; the feature has its own tests.
"""

import re
from pathlib import Path

import pytest

from app.agents import tools
from app.features import cover_letter, jd_analyze, prioritize, tailor

JOB = {"id": "j1", "title": "Backend Engineer", "description": "Kafka and Spring",
       "company_name": "Acme", "company_overview": "A payments platform"}
RESUME = {"id": "rv1", "structured": {"profile": {"headline": "Backend engineer"},
                                     "skills": [{"name": "Java"}],
                                     "experience": []},
          "plaintext": "Backend engineer with 6 years on Kafka."}


@pytest.fixture()
def deps(monkeypatch):
    async def get_job(job_id):
        return dict(JOB)

    async def get_resume(user_id):
        return dict(RESUME)

    monkeypatch.setattr(tools.domain, "get_job", get_job)
    monkeypatch.setattr(tools.domain, "get_current_resume_version", get_resume)
    return monkeypatch


@pytest.mark.asyncio
async def test_analyze_jd_handler_runs(monkeypatch):
    async def fake(raw_text, *, user_id=None, run_id=None):
        return {"requiredSkills": [{"name": "Kafka"}]}

    monkeypatch.setattr(jd_analyze, "analyze_jd", fake)
    out = await tools.analyze_jd("u1", raw_text="We need Kafka.")
    assert "error" not in out and out["jd"]["requiredSkills"]


@pytest.mark.asyncio
async def test_generate_resume_handler_runs(deps, monkeypatch):
    async def fake_jd(raw_text, *, user_id=None, run_id=None):
        return {"requiredSkills": [{"name": "Kafka"}]}

    async def fake_tailor(structured, text, jd, *, user_id, job_title="", run_id=None):
        return {"tailored": {"profile": {}}, "diff": [], "notes": [], "stats": {}}

    monkeypatch.setattr(jd_analyze, "analyze_jd", fake_jd)
    monkeypatch.setattr(tailor, "tailor", fake_tailor)

    out = await tools.generate_resume("u1", job_id="j1")
    assert "error" not in out
    assert set(out) >= {"tailored", "diff", "notes", "stats", "job_id"}
    assert out["job_id"] == "j1"


@pytest.mark.asyncio
async def test_generate_cover_letter_handler_runs(deps, monkeypatch):
    async def fake_jd(raw_text, *, user_id=None, run_id=None):
        return {"requiredSkills": [{"name": "Kafka"}]}

    async def fake_generate(structured, text, jd, company, goal, *, user_id, **kw):
        assert company == {"name": "Acme", "overview": "A payments platform"}
        return {"cover_letter": "Dear Acme..."}

    monkeypatch.setattr(jd_analyze, "analyze_jd", fake_jd)
    monkeypatch.setattr(cover_letter, "generate", fake_generate)

    out = await tools.generate_cover_letter("u1", job_id="j1")
    assert "error" not in out and out["cover_letter"].startswith("Dear")


@pytest.mark.asyncio
async def test_create_interview_handler_runs(deps, monkeypatch):
    captured: dict = {}

    async def fake_fetchrow(query, *args):
        captured["sql"], captured["args"] = query, args
        return {"id": "s1"}

    monkeypatch.setattr(tools.db, "fetchrow", fake_fetchrow)

    out = await tools.create_interview("u1", job_id="j1", max_questions="9")
    assert out["session_id"] == "s1"
    assert out["job"] == "Backend Engineer"
    # `"9"` arrives as a string from the model; `_clamp_limit` must land an int in the
    # jsonb config rather than passing the string through to the session row.
    assert '"max_questions": 9' in captured["args"][-1]


@pytest.mark.asyncio
async def test_save_job_handler_runs(monkeypatch):
    calls: list[str] = []

    async def fake_execute(query, *args):
        calls.append(" ".join(query.split()))
        return "INSERT 0 1"

    monkeypatch.setattr(tools.db, "execute", fake_execute)
    out = await tools.save_job("u1", job_id="j1", note="referral")
    assert out == {"saved": True, "job_id": "j1"}
    assert any("saved_jobs" in c for c in calls)
    assert any("applications" in c for c in calls)


@pytest.mark.asyncio
async def test_benchmark_salary_handler_runs(monkeypatch):
    async def fake_samples():
        return [{"title": "Backend Engineer", "location": "Shanghai",
                 "salary_min": 300000, "salary_max": 500000,
                 "salary_currency": "CNY", "experience_years": 6}]

    monkeypatch.setattr(tools, "_job_samples", fake_samples)
    out = await tools.benchmark_salary("u1", role="Backend Engineer",
                                       location="Shanghai", target_salary=420000)
    assert "error" not in out
    assert out["sampleSize"] == 1, "the sample should match the role it was built for"
    assert out["percentiles"]["p50"] > 0
    assert "position" in out, "a target salary must be placed against the band"


@pytest.mark.asyncio
async def test_learning_priority_handler_runs(deps, monkeypatch):
    async def fake_samples():
        return [{"title": "Backend Engineer", "skills": ["Java", "Kafka"]}]

    async def fake_plan(*, target_role, resume_structured, samples, seniority=None,
                        user_id=None):
        assert target_role == "Backend Engineer"
        assert resume_structured.get("skills"), "the profile must reach the engine"
        return {"plan": [{"skill": "Kafka", "why": "in demand"}]}

    monkeypatch.setattr(tools, "_job_skill_samples", fake_samples)
    monkeypatch.setattr(prioritize, "plan_learning_priority", fake_plan)

    out = await tools.learning_priority("u1", target_role="Backend Engineer")
    assert "error" not in out and out["plan"]


def test_every_shipped_tool_handler_is_called_somewhere():
    """The durable version of the audit that found `compare_offers`.

    A handler no test calls is a handler no test has run, and `compare_offers`
    proved that can survive a green suite indefinitely. This gate reads the test
    corpus (this file included) and fails when a shipped tool has no caller -- so
    adding a tool without exercising it turns the suite red instead of shipping a
    path nobody has executed.

    The `\\b` matters: a loose match let `plan_learning_priority(` count as a call to
    `learning_priority`, which is how that handler stayed uncalled while an earlier
    audit reported it covered.
    """
    corpus = "\n".join(p.read_text(encoding="utf-8", errors="replace")
                       for p in Path(__file__).resolve().parent.glob("*.py"))
    uncalled = [t.name for t in tools.ALL_TOOLS
                if not re.search(rf"\b{re.escape(t.handler.__name__)}\s*\(", corpus)]
    assert uncalled == [], (
        f"no test calls the handler for {uncalled} -- add a case to this file; "
        "importing a module is not the same as calling it")
