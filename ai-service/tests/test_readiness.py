"""Target-Role Readiness: the verdict a candidate acts on, and its hard-blocker cap.

The route (`POST /readiness` in app/api/features.py) has shipped since it was
committed, and `compose` had no dedicated test — the only reference was the
forward-features contract gate, which checks the route exists, not what the
verdict says. What the product is really for lives in the two rules here: the
threshold over the gap report's own coverage, and the **cap** that stops a high
average from hiding a required skill with no evidence (a "ready" with a blocker
is a "borderline", never a "ready"). The market half is reported beside the
skill half, never blended into it — averaging skills and pay would produce a
number that means neither.
"""

from app.features.readiness import compose, must_gaps, skill_verdict


def _gap(coverage=0.8, gaps=None, plan=None, target="Backend Engineer",
         seniority="senior", covered=6, gapCount=2):
    return {
        "targetRole": target,
        "seniority": seniority,
        "coverage": coverage,
        "coveredCount": covered,
        "gapCount": gapCount,
        "gaps": gaps if gaps is not None else [
            {"skill": "Kubernetes", "importance": "must", "evidence": []},
        ],
        "developmentPlan": plan if plan is not None else [
            {"focus": "close", "skill": "Kubernetes", "priority": 1},
            {"focus": "stretch", "skill": "Kafka", "priority": 2},
            {"focus": "close", "skill": "Terraform", "priority": 3},
        ],
    }


# --------------------------------- the thresholds ---------------------------------


def test_the_threshold_boundaries_are_the_documented_ones():
    assert skill_verdict(1.0) == "ready"
    assert skill_verdict(0.75) == "ready"          # the boundary is inclusive
    assert skill_verdict(0.7499) == "borderline"
    assert skill_verdict(0.5) == "borderline"       # ...and so is this one
    assert skill_verdict(0.4999) == "not_ready"
    assert skill_verdict(0.0) == "not_ready"


# ------------------------------ the hard-blocker cap ------------------------------


def test_a_required_skill_with_no_evidence_caps_ready_at_borderline():
    """The whole point of the module: coverage 0.9 invites 'ready', but a must-have
    skill with no evidence is a blocker, and a high average must not hide it."""
    out = compose(_gap(coverage=0.9))

    assert out["skillVerdict"] == "ready"      # the raw threshold, uncapped
    assert out["verdict"] == "borderline"      # ...capped by the blocker
    assert out["skillVerdict"] != out["verdict"], (
        "the two verdicts must be able to differ — that difference is the blocker")
    assert out["mustGaps"] == ["Kubernetes"]
    assert out["blockers"] == ["Required skills with no evidence: Kubernetes"]


def test_a_high_coverage_with_no_required_gaps_is_ready_and_blocker_free():
    out = compose(_gap(coverage=0.9, gaps=[{"skill": "Terraform", "importance": "nice",
                                             "evidence": []}]))
    assert out["verdict"] == "ready"
    assert out["skillVerdict"] == "ready"
    assert out["blockers"] == []
    assert out["mustGaps"] == []


def test_the_cap_only_ever_downgrades_a_ready():
    """borderline + blocker stays borderline; the cap is not a second threshold."""
    out = compose(_gap(coverage=0.6))
    assert out["verdict"] == "borderline"
    assert compose(_gap(coverage=0.3))["verdict"] == "not_ready"


def test_only_must_importance_counts_as_a_blocker():
    out = compose(_gap(coverage=0.9, gaps=[
        {"skill": "NiceToHave", "importance": "nice", "evidence": []},
        {"skill": "Preferred", "importance": "preferred", "evidence": []},
    ]))
    assert out["verdict"] == "ready", "a nice-to-have gap is not a hard blocker"
    assert out["blockers"] == []


def test_a_skill_with_evidence_is_not_a_gap():
    out = compose(_gap(coverage=0.9, gaps=[
        {"skill": "Kubernetes", "importance": "must", "evidence": ["ran k8s"]},
    ]))
    assert out["mustGaps"] == []


# ---------------------------- the lists are bounded ----------------------------


def test_the_blocker_message_names_five_and_must_gaps_stay_eight():
    musts = [{"skill": f"S{i}", "importance": "must", "evidence": []} for i in range(12)]
    out = compose(_gap(coverage=0.9, gaps=musts))
    assert out["mustGaps"] == [f"S{i}" for i in range(8)]
    assert out["blockers"][0] == (
        "Required skills with no evidence: S0, S1, S2, S3, S4")


def test_actions_carry_the_first_five_plan_entries_mapped():
    plan = [{"focus": f"f{i}", "skill": f"k{i}", "priority": i, "extra": "dropped"}
            for i in range(8)]
    out = compose(_gap(plan=plan))
    assert out["actions"] == [
        {"focus": "f0", "skill": "k0", "priority": 0},
        {"focus": "f1", "skill": "k1", "priority": 1},
        {"focus": "f2", "skill": "k2", "priority": 2},
        {"focus": "f3", "skill": "k3", "priority": 3},
        {"focus": "f4", "skill": "k4", "priority": 4},
    ]
    assert "extra" not in out["actions"][0]


# --------------------- the market half is beside, not blended ---------------------


def test_the_salary_verdict_is_reported_alongside_not_averaged_in():
    """Skills and pay are different questions; the salary verdict never moves the
    skill verdict, however good or bad the market looks."""
    salary = {"position": {"verdict": "underpaid", "median": 100000},
              "sampleSize": 37}
    out = compose(_gap(coverage=0.9, gaps=[]), salary)
    assert out["salaryVerdict"] == "underpaid"
    assert out["verdict"] == "ready"
    assert out["salarySampleSize"] == 37
    # ...and a favourable market cannot waive a hard skill blocker either.
    poor = compose(_gap(coverage=0.9), {"position": {"verdict": "overpaid"}})
    assert poor["verdict"] == "borderline"


def test_a_salary_report_with_no_position_says_nothing():
    out = compose(_gap(), {"sampleSize": 0})
    assert out["salaryVerdict"] is None
    assert out["salarySampleSize"] == 0


# --------------------------------- shape safety ---------------------------------


def test_missing_keys_degrade_to_zero_and_none_not_to_a_crash():
    out = compose({})
    assert out["skillReadiness"] == 0.0
    assert out["verdict"] == "not_ready"
    assert out["mustGaps"] == []
    assert out["actions"] == []
    assert out["targetRole"] == ""
    assert out["salaryVerdict"] is None
    assert out["salarySampleSize"] == 0


def test_a_null_coverage_reads_as_zero_rather_than_crashing():
    out = compose(_gap(coverage=None))
    assert out["skillReadiness"] == 0.0
    assert out["skillVerdict"] == "not_ready"


def test_the_counts_pass_through_and_coverage_is_rounded():
    out = compose(_gap(coverage=0.8333333, covered=10, gapCount=4))
    assert out["coveredCount"] == 10 and out["gapCount"] == 4
    assert out["skillReadiness"] == 0.833


def test_must_gaps_reads_the_gap_report_alone():
    report = {"gaps": [
        {"skill": "A", "importance": "must"},
        {"skill": "", "importance": "must"},
        {"skill": "B", "importance": "must", "evidence": ["yes"]},
    ]}
    assert must_gaps(report) == ["A"]
