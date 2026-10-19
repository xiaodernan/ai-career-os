"""Regression: forward engines degrade on hostile rows instead of raising.

These mirror the discipline of ``test_forward_features_robustness.py`` but target the
Epic 10.11 (progression) and Epic 10.13 (interview prep) pure builders specifically --
the ones the health check showed still raised ``TypeError`` / ``AttributeError`` on
``None`` / empty / wrong-shaped input. A malformed payload from a peer service or a
stale cached row must produce an empty/safe result, never crash the request path.
"""

from app.features import interview_prep, progression


# --- progression.build_stepping_stones -------------------------------------

def test_stepping_stones_none_families_and_gaps():
    assert progression.build_stepping_stones(None, None, None) == []


def test_stepping_stones_none_gap_lists_with_families():
    fams = [{"family": "f", "topDemands": ["x"], "coverage": 0.2, "postings": 3}]
    # No gaps to build -> nothing qualifies, but it must not raise.
    assert progression.build_stepping_stones(fams, None, None) == []


def test_stepping_stones_none_family_entry_is_skipped():
    fams = [None, {"family": "f", "topDemands": ["x"], "coverage": 0.2, "postings": 3}]
    # The None entry must be skipped (no crash), leaving only the real family.
    stones = progression.build_stepping_stones(fams, ["x"], [])
    assert [s["family"] for s in stones] == ["f"]


def test_stepping_stones_non_str_gap_entries_ignored():
    fams = [{"family": "f", "topDemands": ["x"], "coverage": 0.2, "postings": 3}]
    # A non-string gap must not break the set comprehension; only "x" survives.
    stones = progression.build_stepping_stones(fams, ["x", 12, None], [])
    assert len(stones) == 1
    assert stones[0]["family"] == "f"
    assert stones[0]["buildsSkills"] == ["x"]
    assert stones[0]["buildsCount"] == 1


def test_stepping_stones_topdemands_none_skips_family():
    fams = [{"family": "f", "topDemands": None, "coverage": 0.2, "postings": 3}]
    assert progression.build_stepping_stones(fams, ["x"], []) == []


def test_stepping_stones_real_match_produces_stone():
    fams = [{"family": "data", "topDemands": ["sql", "python"], "coverage": 0.5, "postings": 10}]
    stones = progression.build_stepping_stones(fams, ["sql", "python"], ["sql"])
    assert len(stones) == 1
    assert stones[0]["family"] == "data"
    assert stones[0]["buildsMustCount"] == 1
    assert stones[0]["bridgeScore"] > 0


# --- progression.build_advice ----------------------------------------------

def test_build_advice_none_must_gaps_no_crash():
    lines = progression.build_advice(0.4, 2, None)
    assert isinstance(lines, list) and lines


def test_build_advice_none_coverage_no_crash():
    lines = progression.build_advice(None, 0, [])
    assert isinstance(lines, list) and lines


def test_build_advice_non_numeric_coverage_coerced():
    # A non-float coverage must not raise on comparison.
    lines = progression.build_advice("high", 0, [])
    assert isinstance(lines, list)


def test_build_advice_must_gaps_and_readiness_lines():
    lines = progression.build_advice(0.85, 1, ["distributed-systems"])
    joined = " ".join(lines)
    assert "hard-requirement gap" in joined
    assert "85%" in joined


# --- interview_prep.build_prep_plan ----------------------------------------

def test_prep_plan_none_inputs_returns_safe_dict():
    plan = interview_prep.build_prep_plan(None, None)
    assert plan["weakAreaCount"] == 0
    assert plan["coverage"] == 0.0
    assert plan["weakAreas"] == []
    assert plan["storyBankSize"] == 0


def test_prep_plan_empty_dicts_returns_safe_dict():
    plan = interview_prep.build_prep_plan({}, {})
    assert plan["weakAreaCount"] == 0
    assert plan["coverage"] == 0.0


def test_prep_plan_present_none_value_keys_handled():
    # A key present but set to None must behave like missing.
    report = {"gaps": None, "covered": None, "responsibilities": None}
    plan = interview_prep.build_prep_plan(report, {"stories": None})
    assert plan["weakAreaCount"] == 0
    assert plan["likelyTopics"] == []


def test_prep_plan_non_dict_gap_entry_filtered():
    report = {"gaps": [None, "not-a-dict", {"skill": "sql", "importance": "must"}]}
    plan = interview_prep.build_prep_plan(report, {})
    assert plan["weakAreaCount"] == 1
    assert plan["weakAreas"][0]["skill"] == "sql"


def test_prep_plan_gap_missing_skill_uses_unknown():
    report = {"gaps": [{"importance": "should"}]}
    plan = interview_prep.build_prep_plan(report, {})
    assert plan["weakAreas"][0]["skill"] == "unknown"
