"""Unit tests for the deterministic pieces of the match engine (PRD §10).

Only the pure, I/O-free helpers are exercised here — the weighted-score
orchestration lives in ``compute_match`` which needs the LLM/DB and is covered by
integration tests. These lock the date-parsing behaviour that silently
under-counted experience when resumes carried year-only ranges.
"""

from datetime import date

import pytest

from app.features.match import (_OVERALL_WEIGHTS, _education_score, _edu_rank,
                                _experience_score, _matched_missing, _overall,
                                _projects_score, _skill_set, _technical_score,
                                _user_years, _year_month)


# ---------------- _year_month ----------------


def test_year_month_parses_separated_forms():
    assert _year_month("2019-05", 1) == (2019, 5)
    assert _year_month("2019/5", 1) == (2019, 5)
    assert _year_month("2019.11", 1) == (2019, 11)
    assert _year_month("  2021-12 ", 1) == (2021, 12)


def test_year_month_bare_year_uses_default_month():
    assert _year_month("2019", 1) == (2019, 1)
    assert _year_month("2022", 12) == (2022, 12)


def test_year_month_clamps_month_and_rejects_garbage():
    assert _year_month("2019-20", 1)[1] == 12          # month clamped into 1..12
    assert _year_month("20195", 1) is None              # 5-digit run is not a year+month
    assert _year_month("Mar 2020", 1) is None           # no leading 4-digit year
    assert _year_month("", 12) is None
    assert _year_month(None, 1) is None


# ---------------- _user_years ----------------


def test_user_years_prefers_explicit_profile_field():
    parsed = {"profile": {"yearsExperience": 7.5},
              "experience": [{"start": "2019", "end": "2020"}]}
    assert _user_years(parsed) == 7.5


def test_user_years_counts_bare_year_ranges():
    # Regression: these used to be skipped entirely (regex demanded a month) -> 0.0.
    parsed = {"experience": [{"start": "2019", "end": "2022"}]}
    assert _user_years(parsed) == 3.9  # Jan 2019 .. Dec 2022 = 47 months


def test_user_years_sums_multiple_roles():
    parsed = {"experience": [{"start": "2018", "end": "2020"},
                             {"start": "2020", "end": "2021"}]}
    # Jan-of-start .. Dec-of-end: 35 + 23 = 58 months = 4.8y
    assert _user_years(parsed) == 4.8


def test_user_years_caps_a_single_role_at_six_years():
    parsed = {"experience": [{"start": "2000-01", "end": "2020-12"}]}
    assert _user_years(parsed) == 6.0


def test_user_years_handles_present_marker():
    parsed = {"experience": [{"start": "2020", "end": "Present"}]}
    today = date.today()
    expected = round(min(max(0, (today.year - 2020) * 12 + (today.month - 1)), 72) / 12.0, 1)
    assert _user_years(parsed) == expected
    assert _user_years(parsed) > 0


def test_user_years_zero_when_nothing_parseable():
    assert _user_years({"experience": []}) == 0.0
    assert _user_years({"experience": [{"start": "unknown", "end": ""}]}) == 0.0


# ---------------- _technical_score ----------------


def test_technical_score_neutral_when_jd_lists_no_skills():
    # Regression: the `or 1.0` guard made the intended 0.6 neutral fallback
    # unreachable, so an empty JD scored technical=0.
    assert _technical_score([], [], {"Python"}) == 0.6


def test_technical_score_full_required_coverage():
    req = [{"name": "Python", "priority": "must"}, {"name": "Go", "priority": "must"}]
    assert _technical_score(req, [], {"Python", "Go"}) == 1.0


def test_technical_score_partial_required_coverage():
    req = [{"name": "Python", "priority": "must"}, {"name": "Go", "priority": "must"}]
    assert _technical_score(req, [], {"Python"}) == 0.5


def test_technical_score_weights_priority_levels():
    # must=3, should=2. Matching only the "should" skill => 2 / (3+2) = 0.4.
    req = [{"name": "Python", "priority": "must"}, {"name": "Go", "priority": "should"}]
    assert _technical_score(req, [], {"Go"}) == 0.4


def test_technical_score_preferred_only_is_not_diluted_by_phantom_required():
    # Regression: with no required skills the old code still added a weight of 1.0
    # to the denominator, so a fully-matching preferred-only JD scored ~0.23.
    pref = [{"name": "Docker", "priority": "nice"}]
    assert _technical_score([], pref, {"Docker"}) == 1.0


def test_technical_score_preferred_only_unmatched_is_zero():
    pref = [{"name": "Docker", "priority": "nice"}]
    assert _technical_score([], pref, set()) == 0.0


def test_technical_score_capped_at_one():
    req = [{"name": "Python", "priority": "must"}]
    pref = [{"name": "Docker", "priority": "nice"}]
    assert _technical_score(req, pref, {"Python", "Docker"}) == 1.0


# ---------------- _skill_set ----------------


def test_skill_set_normalizes_declared_skills():
    parsed = {"skills": [{"name": "react"}, {"name": "K8s"}]}
    assert _skill_set(parsed) == {"React", "Kubernetes"}


def test_skill_set_skips_non_dict_and_empty_names():
    parsed = {"skills": [{"name": ""}, {"title": "Python"}, "Python", None]}
    # nothing declared cleanly and no free-text blob -> empty set
    assert _skill_set(parsed) == set()


def test_skill_set_harvests_skills_from_experience_text():
    parsed = {"skills": [], "experience": ["Built a REST API with Python and PostgreSQL"]}
    got = _skill_set(parsed)
    assert {"Python", "PostgreSQL", "REST API"} <= got


# ---------------- _edu_rank ----------------


def test_edu_rank_maps_bachelor():
    assert _edu_rank({"education": [{"degree": "Bachelor of Science"}]}) == 2


def test_edu_rank_takes_maximum_across_entries():
    parsed = {"education": [{"degree": "Associate"}, {"degree": "Master"}]}
    assert _edu_rank(parsed) == 2.5


def test_edu_rank_unknown_is_minus_one():
    assert _edu_rank({"education": []}) == -1
    assert _edu_rank({"education": [{"degree": "Bootcamp"}]}) == -1
    assert _edu_rank({}) == -1


# ---------------- _experience_score ----------------


def test_experience_score_neutral_when_jd_states_no_years():
    score, note = _experience_score({"profile": {"yearsExperience": 9}}, {})
    assert score == 0.75
    assert "does not state" in note
    # a zero/negative requirement is treated the same as "not stated"
    assert _experience_score({}, {"experienceYears": 0})[0] == 0.75


def test_experience_score_meets_requirement():
    score, note = _experience_score({"profile": {"yearsExperience": 3}},
                                    {"experienceYears": 3})
    assert score == pytest.approx(0.9)
    assert note == "3.0y experience >= required 3y."


def test_experience_score_capped_when_over_qualified():
    assert _experience_score({"profile": {"yearsExperience": 10}},
                             {"experienceYears": 3})[0] == 1.0


def test_experience_score_has_a_floor_below_requirement():
    # Regression-style guard: an under-experienced candidate is never zeroed out.
    assert _experience_score({"profile": {"yearsExperience": 1}},
                             {"experienceYears": 4})[0] == pytest.approx(0.25)
    assert _experience_score({}, {"experienceYears": 5})[0] == 0.25


# ---------------- _education_score ----------------


def test_education_score_neutral_when_no_min_degree():
    assert _education_score({}, {}) == 0.8
    # non-dict education block is ignored -> neutral
    assert _education_score({}, {"education": "bachelor"}) == 0.8


def test_education_score_meets_and_exceeds():
    parsed = {"education": [{"degree": "Bachelor of Science"}]}
    assert _education_score(parsed, {"education": {"minDegree": "bachelor"}}) == 1.0


def test_education_score_one_rank_below():
    parsed = {"education": [{"degree": "Associate"}]}
    assert _education_score(parsed, {"education": {"minDegree": "bachelor"}}) == 0.5


def test_education_score_unknown_min_degree_defaults_to_bachelor():
    parsed = {"education": [{"degree": "Master"}]}
    assert _education_score(parsed, {"education": {"minDegree": "SomeDegree"}}) == 1.0


def test_education_score_no_studied_education_hits_floor():
    assert _education_score({}, {"education": {"minDegree": "bachelor"}}) == 0.3


# ---------------- _projects_score ----------------


def test_projects_score_no_projects_no_experience():
    assert _projects_score({}, [], [], {}) == 0.1


def test_projects_score_no_projects_but_experience():
    assert _projects_score({"experience": [{"start": "2019"}]}, [], [], {}) == 0.35


def test_projects_score_counts_projects_capped_at_three():
    parsed = {"projects": [{"tech": ["Go"]}, {"tech": ["Go"]},
                           {"tech": ["Go"]}, {"tech": ["Go"]}]}
    assert _projects_score(parsed, [], [], {}) == pytest.approx(0.75)


def test_projects_score_adds_jd_term_overlap():
    parsed = {"projects": [{"tech": ["Python", "Redis"], "bullets": ["used Kafka"]}]}
    req = [{"name": "Python"}]
    # 1 project -> 0.25, overlap on {Python} -> +0.1
    assert _projects_score(parsed, req, [], {}) == pytest.approx(0.35)


# ---------------- _matched_missing ----------------


def test_matched_missing_asymmetry():
    # matched draws from required AND preferred; missing only from required.
    req = [{"name": "Python"}, {"name": "Go"}]
    pref = [{"name": "Docker"}]
    matched, missing = _matched_missing(req, pref, {"Python", "Docker"})
    assert matched == ["Docker", "Python"]     # preferred Docker counts as matched
    assert missing == ["Go"]                    # Docker absent but not a required gap


def test_matched_missing_dedups_across_required_and_preferred():
    req = [{"name": "Python"}]
    pref = [{"name": "Python"}]
    matched, missing = _matched_missing(req, pref, {"Python"})
    assert matched == ["Python"]
    assert missing == []


def test_matched_missing_normalizes_skill_names():
    matched, missing = _matched_missing([{"name": "react"}], [], {"React"})
    assert matched == ["React"]
    assert missing == []


def test_matched_missing_empty():
    assert _matched_missing([], [], {"Python"}) == ([], [])


# ---------------- _overall ----------------


def test_overall_weights_sum_to_one():
    assert sum(_OVERALL_WEIGHTS) == pytest.approx(1.0)


def test_overall_is_normalised_at_the_extremes():
    assert _overall(1, 1, 1, 1) == 1.0
    assert _overall(0, 0, 0, 0) == 0.0


def test_overall_technical_weight_only():
    assert _overall(1, 0, 0, 0) == pytest.approx(0.42)


def test_overall_rounds_to_four_places():
    assert _overall(0.33333, 0.33333, 0.33333, 0.33333) == 0.3333


# ---------------- compute_match result ↔ persist_match column contract ----------------
# persist_match indexes these exact keys out of compute_match()'s MatchResult.model_dump();
# the whole INSERT path is otherwise only exercised by Docker *IT. A field renamed in
# schemas.MatchResult (or a key edited in persist_match) without the other would 500 at
# runtime — this locks the two in sync offline.

_PERSIST_INDEXED_KEYS = ["overall", "technical", "experience", "projects", "education",
                         "matchedSkills", "missingSkills", "evidence", "narrative", "model"]


def test_match_result_dump_carries_every_key_persist_match_indexes():
    from app.features.schemas import MatchResult

    dumped = MatchResult(overall=0.5, technical=0.5, experience=0.5, projects=0.5,
                         education=0.5).model_dump()
    assert [k for k in _PERSIST_INDEXED_KEYS if k not in dumped] == []


def test_match_result_nested_evidence_dumps_snake_keys_persist_stores():
    from app.features.schemas import MatchResult

    dumped = MatchResult(
        overall=0.1, technical=0.2, experience=0.3, projects=0.4, education=0.5,
        matchedSkills=["Go"], missingSkills=["Rust"],
        evidence=[{"criterion": "skill:Go", "score": 0.2, "chunk_ids": ["c1"],
                   "quote": "q", "source": "Resume", "section": "exp", "reasoning": "r"}],
        narrative="n", interviewTopics=["systems"], model="m").model_dump()
    assert dumped["matchedSkills"] == ["Go"] and dumped["missingSkills"] == ["Rust"]
    assert dumped["evidence"][0]["chunk_ids"] == ["c1"]   # snake persisted as jsonb
    assert dumped["narrative"] == "n" and dumped["model"] == "m"
