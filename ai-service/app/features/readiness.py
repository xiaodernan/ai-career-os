"""Target-Role Readiness (forward Epic 10.4).

The synthesis the product is really for: "Am I ready to apply for this role, and
what should I do about it?" It composes the two evidence-bound engines already
built -- the gap analysis (skills) and the salary benchmark (market) -- into one
verdict and one prioritized action list.

Deterministic by construction. Skill readiness is the gap report's own coverage;
the verdict is a threshold over it, *capped* when a required skill has no evidence
(a high average must not hide a hard blocker). The market half is reported
separately rather than blended in, because skills and pay are different questions
and averaging them would produce a number that means neither.
"""


def skill_verdict(coverage: float) -> str:
    if coverage >= 0.75:
        return "ready"
    if coverage >= 0.5:
        return "borderline"
    return "not_ready"


def must_gaps(gap_report: dict) -> list[str]:
    """Required (importance == 'must') skills the candidate has no evidence for.

    `gaps` from the gap report carries no evidence key by construction — the gap
    engine only appends a skill there once it has found no trace of it in the
    candidate's material (`gap_analysis.classify_coverage`). An entry that DOES
    carry evidence is therefore not a no-evidence blocker, whoever composed the
    report: the blocker sentence names "skills with no evidence", and reading the
    field keeps that sentence true for every input rather than for the one this
    producer happens to make.
    """
    return [g.get("skill", "") for g in ((gap_report or {}).get("gaps") or [])
            if isinstance(g, dict) and g.get("importance") == "must"
            and g.get("skill") and not g.get("evidence")]


def compose(gap_report: dict, salary_report: dict | None = None) -> dict:
    gap_report = gap_report or {}
    coverage = float(gap_report.get("coverage") or 0.0)
    required_gaps = must_gaps(gap_report)
    verdict = skill_verdict(coverage)
    # A required skill with no evidence is a hard blocker: it caps a "ready" at
    # "borderline" even when average coverage looks high.
    if required_gaps and verdict == "ready":
        verdict = "borderline"

    blockers: list[str] = []
    if required_gaps:
        blockers.append("Required skills with no evidence: " + ", ".join(required_gaps[:5]))

    salary_verdict = None
    if salary_report and salary_report.get("position"):
        salary_verdict = salary_report["position"].get("verdict")

    return {
        "targetRole": gap_report.get("targetRole", ""),
        "seniority": gap_report.get("seniority", ""),
        "skillReadiness": round(coverage, 3),
        "skillVerdict": skill_verdict(coverage),
        "salaryVerdict": salary_verdict,
        "verdict": verdict,
        "coveredCount": gap_report.get("coveredCount", 0),
        "gapCount": gap_report.get("gapCount", 0),
        "mustGaps": required_gaps[:8],
        "blockers": blockers,
        "actions": [{"focus": i.get("focus", ""), "skill": i.get("skill", ""),
                     "priority": i.get("priority", "")}
                    for i in (gap_report.get("developmentPlan") or [])[:5]],
        "salarySampleSize": (salary_report or {}).get("sampleSize", 0),
    }
