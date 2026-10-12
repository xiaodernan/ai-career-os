"""Unit tests for the composed growth report (forward Epic 10.8).

The aggregate endpoint's shape is the object the backend client and the frontend
will be written against, so it is pinned here (and in the contract gate) rather than
left inline in the route where it could drift unwired.
"""

from app.features.growth import build_growth_report

GAP = {"targetRole": "Senior Backend Engineer", "coverage": 0.5,
       "covered": [{"skill": "Java"}], "partial": [],
       "gaps": [{"skill": "Rust", "importance": "must", "category": "language"}],
       "developmentPlan": [{"focus": "Build evidence for Rust", "skill": "Rust",
                            "priority": "must"}]}
SALARY = {"sampleSize": 3, "currency": "CNY",
          "percentiles": {"min": 300000, "p25": 350000, "p50": 400000,
                          "p75": 500000, "max": 600000}}


def test_growth_report_composes_all_five_parts():
    r = build_growth_report(GAP, SALARY)
    assert set(r) == {"readiness", "gap", "salary", "learningPlan", "progress"}
    assert r["gap"] is GAP and r["salary"] is SALARY
    assert r["readiness"]["verdict"] == "borderline"     # a must-gap caps a "ready"
    assert r["learningPlan"]["totalItems"] == 1
    assert r["progress"]["baseline"] is True


def test_growth_report_progress_uses_the_previous_report():
    prev = {"covered": [], "gaps": [{"skill": "Rust", "importance": "must"}]}
    cur = {"coverage": 0.5, "covered": [{"skill": "Rust"}], "gaps": []}
    r = build_growth_report(cur, SALARY, prev)
    assert r["progress"]["baseline"] is False
    assert r["progress"]["closed"] == ["Rust"]


def test_growth_report_salary_is_optional():
    r = build_growth_report(GAP)
    assert r["salary"] is None
    assert r["readiness"]["salaryVerdict"] is None
