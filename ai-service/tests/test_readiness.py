"""Unit tests for Target-Role Readiness (forward Epic 10.4).

Readiness is a *synthesis* of the gap analysis and the salary benchmark, so the
tests hold the composition: the verdict thresholds, the rule that a required skill
with no evidence caps a "ready", and the integration that feeds a real gap report
and a real benchmark through it.
"""

from app.features import gap_analysis as gap_mod
from app.features.readiness import compose, must_gaps, skill_verdict
from app.features.salary import benchmark


# ---------------- skill_verdict ----------------


def test_skill_verdict_thresholds():
    assert skill_verdict(0.9) == "ready"
    assert skill_verdict(0.75) == "ready"
    assert skill_verdict(0.6) == "borderline"
    assert skill_verdict(0.5) == "borderline"
    assert skill_verdict(0.49) == "not_ready"
    assert skill_verdict(0.0) == "not_ready"


# ---------------- must_gaps ----------------


def test_must_gaps_only_required_with_a_name():
    gaps = [{"skill": "Kubernetes", "importance": "must"},
            {"skill": "Rust", "importance": "nice"},
            {"skill": "", "importance": "must"},
            {"skill": "Go", "importance": "should"}]
    assert must_gaps({"gaps": gaps}) == ["Kubernetes"]


def test_must_gaps_empty_report():
    assert must_gaps({}) == []


# ---------------- compose ----------------


GAP_READY = {
    "targetRole": "Senior Backend Engineer", "seniority": "senior",
    "coverage": 0.8, "coveredCount": 4, "gapCount": 1,
    "gaps": [{"skill": "Go", "importance": "nice"}],
    "developmentPlan": [{"focus": "Build evidence for Go", "skill": "Go", "priority": "nice"}],
}
SALARY = {"sampleSize": 5, "position": {"verdict": "below_market", "percentile": 20.0}}


def test_compose_ready_when_coverage_high_and_no_must_gap():
    r = compose(GAP_READY)
    assert r["verdict"] == "ready"
    assert r["skillVerdict"] == "ready"
    assert r["skillReadiness"] == 0.8
    assert r["mustGaps"] == [] and r["blockers"] == []


def test_compose_caps_ready_when_a_required_skill_has_no_evidence():
    gap = {**GAP_READY, "gaps": [{"skill": "Kubernetes", "importance": "must"}]}
    r = compose(gap)
    assert r["verdict"] == "borderline"          # capped from "ready"
    assert r["skillVerdict"] == "ready"          # the raw skill verdict is unchanged
    assert r["mustGaps"] == ["Kubernetes"]
    assert r["blockers"] and "Kubernetes" in r["blockers"][0]


def test_compose_not_ready_when_coverage_low():
    gap = {**GAP_READY, "coverage": 0.3, "gaps": []}
    assert compose(gap)["verdict"] == "not_ready"


def test_compose_carries_the_salary_half_separately():
    r = compose(GAP_READY, SALARY)
    assert r["salaryVerdict"] == "below_market"
    assert r["salarySampleSize"] == 5


def test_compose_salary_absent_is_none_not_zero():
    r = compose(GAP_READY)
    assert r["salaryVerdict"] is None and r["salarySampleSize"] == 0


def test_compose_actions_come_from_the_development_plan():
    r = compose(GAP_READY)
    assert r["actions"] == [{"focus": "Build evidence for Go", "skill": "Go",
                             "priority": "nice"}]


def test_compose_empty_report_is_not_ready():
    r = compose({})
    assert r["verdict"] == "not_ready"
    assert r["skillReadiness"] == 0.0
    assert r["actions"] == []


# ---------------- integration: real gap analysis + real benchmark ----------------


async def test_compose_over_a_real_gap_and_salary(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"expectedSkills": [
            {"name": "Java", "category": "language", "importance": "must"},
            {"name": "Rust", "category": "language", "importance": "must"}]}

    monkeypatch.setattr(gap_mod, "ask_json", fake_ask_json)
    resume = {"skills": [{"name": "Java"}], "experience": [], "projects": []}
    gap = await gap_mod.analyze_gap("Senior Backend Engineer", "senior", resume, "")

    samples = [{"title": "Backend Engineer", "location": "X", "experience_years": 5,
                "salary_min": 400000, "salary_max": 600000, "salary_currency": "CNY"}]
    salary = benchmark(samples, role="Backend Engineer", currency="CNY", target_salary=450000)

    r = compose(gap, salary)
    assert r["targetRole"] == "Senior Backend Engineer"
    assert r["coveredCount"] == 1 and r["gapCount"] == 1     # Java covered, Rust a gap
    assert r["skillReadiness"] == 0.5                        # 1 of 2 expected
    assert r["mustGaps"] == ["Rust"]
    assert r["salarySampleSize"] == 1 and r["salaryVerdict"] == "below_market"
    assert r["actions"]
