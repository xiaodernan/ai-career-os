"""Unit tests for the deterministic pieces of the match engine (PRD §10).

Only the pure, I/O-free helpers are exercised here, plus one ``compute_match`` driver
with the LLM and the RAG store stubbed — the builders that fill the job panel's
"why" bullets and preparation card have to be shown to be *called*, not only correct.
These also lock the date-parsing behaviour that silently under-counted experience
when resumes carried year-only ranges.
"""

import ast
import inspect
import re
from datetime import date

import pytest

from app.features import match as match_mod
from app.features.match import (_OVERALL_WEIGHTS, _education_score, _edu_rank,
                                _experience_score, _matched_missing, _min_degree,
                                _overall, _preparation, _preparation_worths, _projects_score,
                                _skill_gaps, _skill_set, _technical_denominator,
                                _technical_score,
                                _user_years, _why_match, _year_month, compute_match)


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


# ---------------- _skill_gaps ----------------


def test_skill_gap_carries_the_jds_own_priority_and_phrase():
    # The panel colours the badge from `importance` and prints `reason` as the posting's own
    # wording, so both must come from the requirement, not from a constant.
    gaps = _skill_gaps([{"name": "Kubernetes", "priority": "should",
                         "evidence_phrase": "production experience with Kubernetes"}],
                       {"Java"})
    assert gaps == [{"skill": "Kubernetes", "importance": "should",
                     "reason": "production experience with Kubernetes"}]


def test_skill_gap_defaults_to_must_only_when_the_jd_says_nothing():
    assert [g["importance"] for g in _skill_gaps([{"name": "Go"}], set())] == ["must"]
    assert [g["importance"] for g in _skill_gaps(
        [{"name": "Go", "priority": "nice"}], set())] == ["nice"]


def test_skill_gap_reason_is_empty_when_the_jd_gave_no_phrase():
    # The mock provider and the deterministic backfill both emit requirements without an
    # evidence_phrase; the card then shows the skill alone rather than a made-up sentence. The
    # paired row is what makes this a statement about the producer: in one call, the requirement
    # with a phrase must carry it and the one without must be empty. Asserting the bare row alone
    # would stay green for a producer that hardcodes "" and never reads the key at all.
    gaps = _skill_gaps([{"name": "Rust", "priority": "must"},
                        {"name": "Go", "evidence_phrase": "go concurrency experience"}], set())
    assert gaps == [{"skill": "Rust", "importance": "must", "reason": ""},
                    {"skill": "Go", "importance": "must",
                     "reason": "go concurrency experience"}]


def test_skill_gaps_follow_the_jds_order_not_alphabetical():
    # `missingSkills` is sorted for the chip row; the gap cards keep the posting's own ranking, so
    # the two lists deliberately differ and a shared sorted() would silently re-order the panel.
    gaps = _skill_gaps([{"name": "Kubernetes"}, {"name": "Go", "priority": "nice"}], set())
    assert [g["skill"] for g in gaps] == ["Kubernetes", "Go"]


def test_skill_gaps_only_cover_required_skills_the_resume_lacks():
    gaps = _skill_gaps([{"name": "Java"}, {"name": "Go"}], {"Java"})
    assert [g["skill"] for g in gaps] == ["Go"]


def test_skill_gaps_dedup_a_skill_listed_twice_and_drop_the_blank_name():
    # Two spellings of one skill normalize to the same name, and the JD can list it twice; the
    # card keeps the first mention's priority, which is why `seen` is checked before appending.
    gaps = _skill_gaps([{"name": "Kubernetes", "priority": "must"}, {"name": "kubernetes"},
                        {"name": "Kubernetes", "priority": "nice"}, {"name": ""}], set())
    assert [g["skill"] for g in gaps] == ["Kubernetes"]
    assert gaps[0]["importance"] == "must"


def test_skill_gaps_empty_when_everything_is_covered():
    assert _skill_gaps([], {"Java"}) == []


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


# ---------------- compute_match result ↔ persist_match SQL contract ----------------
# persist_match is only exercised end-to-end by the Docker *ITs, and every one of its drift
# classes is silent: a column listed without a bind argument raises at runtime, a bind argument
# fed into the wrong column stores the wrong value with no error at all, and a column left out of
# the ON CONFLICT DO UPDATE list keeps the *previous* match's text forever — which is what a
# re-match of the same resume/job pair always is. So the far side of this gate is parsed out of
# persist_match's own source rather than copied here; a hand-mirrored list could only ever catch
# drift on the side someone remembered to write down.


def _fetchrow_call() -> tuple[str, list[ast.expr]]:
    tree = ast.parse(inspect.getsource(match_mod))
    fn = next((n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)
               and n.name == "persist_match"), None)
    assert fn is not None, "persist_match is gone from app.features.match; this gate has no subject"
    call = next((n for n in ast.walk(fn) if isinstance(n, ast.Call)
                 and getattr(n.func, "attr", "") == "fetchrow"), None)
    assert call is not None, "persist_match no longer builds its statement with db.fetchrow"
    assert isinstance(call.args[0], ast.Constant), "persist_match's SQL is no longer a literal"
    return call.args[0].value, list(call.args[1:])


def _split_list(text: str) -> list[str]:
    return [part.strip() for part in text.split(",")]


def _insert_columns(sql: str) -> list[str]:
    return _split_list(re.search(r"INSERT INTO job_matches\((.*?)\)", sql, re.S).group(1))


def _bind_args(sql: str) -> list[str]:
    return _split_list(re.search(r"VALUES\s*\((.*?)\)", sql, re.S).group(1))


def _arg_source(node: ast.expr) -> str:
    """Where a bind argument comes from: the local parameter name, or the ``result`` key."""
    if isinstance(node, ast.Constant):       # result.get("model")
        assert isinstance(node.value, str), "a non-string literal in persist_match's bind list"
        return node.value
    if isinstance(node, ast.Call):           # db.jsonb(result["x"]) / result.get("model")
        if getattr(node.func, "attr", "") in ("jsonb", "get"):
            return _arg_source(node.args[0])
        return f"<call {ast.dump(node)}>"
    if isinstance(node, ast.Subscript):
        assert isinstance(node.value, ast.Name) and node.value.id == "result"
        assert isinstance(node.slice, ast.Constant)
        return node.slice.value
    if isinstance(node, ast.Name):
        return node.id
    return f"<expr {ast.dump(node)}>"


_IDENTITY_COLUMNS = ["user_id", "job_id", "resume_version_id"]
# MatchResult fields persist_match deliberately does not store. Each one is re-derivable from a
# row that IS stored elsewhere and the consumer's fallback resolves, so widening this row would buy
# nothing — but each must be *declared*, because "the schema grew a field nobody persists" is
# otherwise invisible offline. This registry only shrinks: storing a field means deleting its entry.
UNPERSISTED_MATCH_FIELDS = {
    # Measured 2026-09-26, and this is the one that stays: interview_topics is a property of the
    # JD, not of this resume/job pair, and the analysis already carries it — jdParsed.interviewTopics
    # is a live source, unlike the skill-gaps fallback, which read a key no producer ever emitted.
    "interviewTopics": "the JD's own list, not a property of this resume/job pair; it is stored "
                       "with the analysis in job_jds.parsed and jobs/[id]/page.tsx falls back to "
                       "jdParsed.interviewTopics, which does resolve.",
}


def test_persist_statement_binds_one_argument_per_column():
    sql, args = _fetchrow_call()
    cols, binds = _insert_columns(sql), _bind_args(sql)
    assert [c for c in cols if c in _IDENTITY_COLUMNS] == _IDENTITY_COLUMNS
    assert len(cols) == 16, "the measured column list this gate was written against"
    assert cols == list(dict.fromkeys(cols)), "a column listed twice in the INSERT"
    assert len(binds) == len(cols) == len(args)
    assert [int(re.match(r"\$(\d+)", b).group(1)) for b in binds] == list(range(1, len(cols) + 1))


def _camel(snake: str) -> str:
    """job_matches column name -> the MatchResult field name that feeds it."""
    head, *rest = snake.split("_")
    return head + "".join(p.title() for p in rest)


def test_each_column_is_fed_the_result_key_named_after_it():
    sql, args = _fetchrow_call()
    cols = _insert_columns(sql)
    assert len(cols) == len(args)
    drift = []
    for col, node in zip(cols, args):
        want = col if col in _IDENTITY_COLUMNS else _camel(col)
        if _arg_source(node) != want:
            drift.append(f"{col} <- {_arg_source(node)}")
    assert drift == [], f"columns bound from a differently-named source: {drift}"


def test_on_conflict_refreshes_every_stored_column():
    sql, _args = _fetchrow_call()
    assert "DO UPDATE SET" in sql, "persist_match stopped refreshing an existing match row"
    updated = dict(re.findall(r"(\w+)\s*=\s*EXCLUDED\.(\w+)", sql.split("DO UPDATE SET")[1]))
    stored = [c for c in _insert_columns(sql) if c not in _IDENTITY_COLUMNS]
    assert sorted(updated) == sorted(stored), (
        f"stale-on-rewrite columns: {set(stored) - set(updated)} / extra: "
        f"{set(updated) - set(stored)}")
    assert [k for k, v in updated.items() if k != v] == [], \
        "an ON CONFLICT assignment that copies a different column"
    assert "created_at=now()" in sql, "a re-match must not keep the original row's timestamp"


def test_match_result_fields_are_all_persisted_or_declared():
    from app.features.schemas import MatchResult

    sql, args = _fetchrow_call()
    persisted = {_arg_source(node) for col, node in zip(_insert_columns(sql), args)
                 if col not in _IDENTITY_COLUMNS}
    fields = set(MatchResult.model_fields)
    assert sorted(fields - persisted - set(UNPERSISTED_MATCH_FIELDS)) == []
    assert sorted(persisted - fields) == []
    assert all(reason.strip() for reason in UNPERSISTED_MATCH_FIELDS.values())
    assert [k for k, v in UNPERSISTED_MATCH_FIELDS.items() if k not in fields] == []


def test_match_result_nested_evidence_dumps_snake_keys_persist_stores():
    from app.features.schemas import MatchResult

    dumped = MatchResult(
        overall=0.1, technical=0.2, experience=0.3, projects=0.4, education=0.5,
        matchedSkills=["Go"], missingSkills=["Rust"],
        skillGaps=[{"skill": "Rust", "importance": "should",
                    "reason": "production experience with Rust"}],
        evidence=[{"criterion": "skill:Go", "score": 0.2, "chunk_ids": ["c1"],
                   "quote": "q", "source": "Resume", "section": "exp", "reasoning": "r"}],
        whyMatch=["Your resume covers 1 of the 2 skills this JD lists: go."],
        preparation=[{"title": "Add concrete evidence of rust", "reason": "r",
                      "priority": "must"}],
        narrative="n", interviewTopics=["systems"], model="m").model_dump()
    assert dumped["matchedSkills"] == ["Go"] and dumped["missingSkills"] == ["Rust"]
    assert dumped["evidence"][0]["chunk_ids"] == ["c1"]   # snake persisted as jsonb
    # the two explanation columns are persisted straight out of this dump, so what the browser
    # reads back has to be the shape the panel indexes into: a list of sentences and a list of
    # objects with exactly title/reason/priority.
    assert dumped["whyMatch"] == ["Your resume covers 1 of the 2 skills this JD lists: go."]
    assert dumped["preparation"] == [{"title": "Add concrete evidence of rust",
                                      "reason": "r", "priority": "must"}]
    # skill_gaps is persisted out of this same dump, and the panel renders the importance straight
    # as a badge colour, so the JD's own word has to survive the round trip — and the retired
    # `advice` key must not come back as an extra field the browser never reads.
    assert dumped["skillGaps"] == [{"skill": "Rust", "importance": "should",
                                   "reason": "production experience with Rust"}]
    assert dumped["narrative"] == "n" and dumped["model"] == "m"


# ---------------- null-section robustness (Java-owned `structured` jsonb) ----------------

# parse_resume defaults only skills/profile/missingSections/warnings; a stored resume
# version can legitimately carry `"experience": null`, `"education": null` or
# `"projects": null`. The old `.get(k, [])` returned that stored None, so
# `for e in None` (was 57/100) and `None + []` (was 23-24) raised TypeError and 500'd
# the whole compute_match flow. `or []` (matching line 150's existing idiom) is the fix.

def test_match_helpers_survive_present_null_sections():
    p = {"skills": None, "experience": None, "projects": None,
         "education": None, "profile": None}
    assert _skill_set(p) == set()
    assert _user_years(p) == 0.0
    assert _edu_rank(p) == -1.0
    # null projects + no experience -> the documented 0.1 floor, not a crash
    assert _projects_score(p, [], [], {}) == 0.1
    assert isinstance(_education_score(p, {}), float)
    # empty JD states no years -> neutral 0.75, exercising the guarded experience read
    exp_score, _note = _experience_score(p, {})
    assert exp_score == 0.75


def test_skill_set_survives_null_experience_with_non_null_projects():
    # the `experience or []` + `projects or []` concatenation used to be `None + [...]`
    p = {"skills": [{"name": "Go"}], "experience": None, "projects": [{"tech": ["Rust"]}]}
    got = _skill_set(p)
    assert "Go" in got and "Rust" in got


# ---------------- _preparation / _preparation_worths ----------------
# The job panel's "Recommended preparation" card promises its items are "ordered by how much
# match score each item is worth", and `MatchResult.preparation` is what feeds it. Nothing
# produced that promise until this unit: the card rendered nothing for every job in the product.
# So the worths are derived from `_technical_score`'s own denominator, and these tests hold that
# to the arithmetic rather than to wording someone liked.


def test_preparation_ranks_gaps_by_worth_then_title():
    req = [{"name": "kubernetes", "priority": "must"},
           {"name": "terraform", "priority": "nice"}]
    pref = [{"name": "rust", "priority": "nice"}]
    scored = _preparation_worths(req, pref, set(), _technical_denominator(req, pref))
    # the titles carry normalize()'s canonical spelling, the same name the skill chips show
    assert [i["title"] for i, _ in scored] == [
        "Add concrete evidence of Kubernetes",
        "Add concrete evidence of Terraform",
        "Add concrete evidence of Rust",
    ]
    # must(3.0) > a required-listed nice(1.0) > a preferred nice(0.3 * 1.0)
    assert [p for _, p in scored] == sorted([p for _, p in scored], reverse=True)
    assert scored[0][1] > scored[1][1] > scored[2][1]


def test_preparation_worths_sum_to_technicals_share_of_overall():
    # The invariant that keeps the shared denominator honest: when the resume covers nothing, the
    # technical score is 0 and the points on offer across all gaps are exactly the 42 points
    # technical is worth inside the overall score. Recompute the denominator in _technical_score
    # or the scaling here and this goes red.
    req = [{"name": "java", "priority": "must"}, {"name": "spring", "priority": "should"}]
    pref = [{"name": "rust", "priority": "nice"}, {"name": "go", "priority": "must"}]
    denom = _technical_denominator(req, pref)
    assert _technical_score(req, pref, set()) == 0.0
    total = sum(points for _, points in _preparation_worths(req, pref, set(), denom))
    assert total == pytest.approx(100 * _OVERALL_WEIGHTS[0], abs=0.2)


def test_preparation_closes_the_loop_when_every_gap_is_closed():
    # The other half of the same arithmetic: matching every listed skill lifts technical to 1.0,
    # which is worth exactly the points the full gap list promised.
    req = [{"name": "java", "priority": "must"}, {"name": "spring", "priority": "should"}]
    pref = [{"name": "rust", "priority": "nice"}]
    denom = _technical_denominator(req, pref)
    promised = sum(points for _, points in _preparation_worths(req, pref, set(), denom))
    covered = {"Java", "Spring", "Rust", "Go"}
    gained = 100 * _OVERALL_WEIGHTS[0] * (
        _technical_score(req, pref, covered) - _technical_score(req, pref, set()))
    assert gained == pytest.approx(promised, abs=0.2)


def test_preparation_is_empty_when_the_jd_lists_no_skill():
    # No denominator means no score to be missing points on, so there is nothing to promise. This
    # is the same condition under which _technical_score falls back to its neutral 0.6.
    assert _technical_score([], [], {"java"}) == 0.6
    assert _preparation_worths([], [], {"java"}, _technical_denominator([], [])) == []
    assert _preparation([], [], {"java"}, _technical_denominator([], [])) == []


def test_preparation_skips_covered_skills_and_one_name_per_gap():
    req = [{"name": "Java"}, {"name": "Kubernetes", "priority": "must"}]
    pref = [{"name": "kubernetes", "priority": "nice"}]   # the JD double-lists one skill
    items = _preparation(req, pref, {"Java"}, _technical_denominator(req, pref))
    assert [i["title"] for i in items] == ["Add concrete evidence of Kubernetes"]
    assert items[0]["priority"] == "must", "the required listing is the one that must be closed"


def test_preparation_items_carry_only_what_the_scoring_path_can_defend():
    req = [{"name": "kubernetes", "priority": "must"}]
    items = _preparation(req, [], set(), _technical_denominator(req, []))
    assert [set(i) for i in items] == [{"title", "reason", "priority"}]
    # The UI renders `~{hours}h` and a `resource` link when present. Neither is produced here on
    # purpose: the matcher knows which skill is missing and what that is worth, not where to read
    # it or how long it takes, and a confident "~4h" would be the first number on this panel the
    # service cannot derive.
    assert "hours" not in items[0] and "resource" not in items[0]
    assert items[0]["reason"].startswith("Required by this JD")


def test_preparation_reports_the_worth_it_sorted_by():
    req = [{"name": "java", "priority": "must"}, {"name": "spring", "priority": "nice"}]
    pref = [{"name": "rust", "priority": "should"}]
    denom = _technical_denominator(req, pref)
    for item, points in _preparation_worths(req, pref, set(), denom):
        assert str(points) in item["reason"]


def test_preparation_caps_the_list_without_reordering_it():
    req = [{"name": f"skill{i}", "priority": "must"} for i in range(8)]
    full = [i for i, _ in _preparation_worths(req, [], set(), _technical_denominator(req, []))]
    assert len(full) == 8
    assert _preparation(req, [], set(), _technical_denominator(req, [])) == full[:6]
    assert _preparation(req, [], set(), _technical_denominator(req, []), cap=0) == []


def test_preparation_keeps_the_jds_own_priority_word():
    # An unrecognised priority is scored as the group's default weight (3.0 for required), so the
    # only gap must be worth the whole 42 points — and the badge still says what the JD said.
    req = [{"name": "docker", "priority": "urgent"}]
    denom = _technical_denominator(req, [])
    scored = _preparation_worths(req, [], set(), denom)
    assert scored[0][1] == pytest.approx(42.0)
    assert scored[0][0]["priority"] == "urgent"


# ---------------- _why_match / _min_degree ----------------


def test_min_degree_only_reports_what_the_jd_states():
    assert _min_degree({}) == ""
    assert _min_degree({"education": None}) == ""
    assert _min_degree({"education": "bachelor"}) == ""      # not the shaped object
    assert _min_degree({"education": {}}) == ""
    assert _min_degree({"education": {"minDegree": "Master"}}) == "Master"


def test_why_match_reports_coverage_of_the_skills_the_jd_listed():
    req = [{"name": f"s{i}"} for i in range(3)]
    pref = [{"name": "s3"}]
    bullets = _why_match(["s0", "s1", "s2", "s3"], req, pref, 0.5, "note", 0.5, {})
    assert bullets == ["Your resume covers 4 of the 4 skills this JD lists: s0, s1, s2 (+1 more)."]


def test_why_match_neutral_scores_are_not_offered_as_strengths():
    # 0.75 experience and 0.8 education are what the engine returns when the JD states nothing;
    # calling those strengths would be the panel lying about a fit the facts do not support.
    assert _why_match([], [], [], 0.75, "JD does not state explicit years.", 0.8, {}) == []
    assert _why_match([], [], [], 0.75, "JD does not state explicit years.", 1.0, {}) == []


def test_why_match_experience_bullet_needs_the_bar_not_a_number():
    bullets = _why_match([], [], [], 0.8, "7.0y experience >= required 5y.", 0.5, {})
    assert bullets == ["Experience: 7.0y experience >= required 5y."]
    assert _why_match([], [], [], 0.79, "under the bar", 0.5, {}) == []


def test_why_match_education_bullet_needs_a_stated_minimum():
    assert _why_match([], [], [], 0.5, "n", 1.0, {"education": {"minDegree": "bachelor"}}) == [
        "Education meets the stated minimum (bachelor)."]
    assert _why_match([], [], [], 0.5, "n", 1.0, {}) == []      # neutral: no minimum was stated
    assert _why_match([], [], [], 0.5, "n", 0.9,
                      {"education": {"minDegree": "bachelor"}}) == []


def test_why_match_orders_the_three_bullets_it_can_clear():
    req = [{"name": "java"}, {"name": "rust"}]
    jd = {"education": {"minDegree": "bachelor"}}
    bullets = _why_match(["java"], req, [], 0.9, "5y >= required 3y.", 1.0, jd)
    assert len(bullets) == 3
    assert bullets[0].startswith("Your resume covers 1 of the 2 skills")
    assert bullets[1] == "Experience: 5y >= required 3y."
    assert bullets[2] == "Education meets the stated minimum (bachelor)."


# ---------------- compute_match wiring (LLM + RAG stubbed) ----------------
# The two builders above are only user-visible if compute_match actually calls them and the
# result carries them into the dump. Everything else in this file would stay green if the wiring
# were dropped, so this drives the real coroutine with just the two I/O chokepoints faked.


def _stub_io(monkeypatch, calls: list):
    from app.providers.base import LLMResponse

    async def fake_ask(req, *, user_id=None, run_id=None, agent="system", kind="chat"):
        calls.append(("ask", agent, kind))
        return LLMResponse(text="computed-facts narrative", model="mock-model")

    async def fake_keyword_search(user_id, term, k=5, kinds=None):
        calls.append(("search", term, tuple(kinds or ())))
        return [{"id": "chunk-1", "text": f"built {term} at work", "doc_title": "Resume",
                 "section_path": "experience"}]

    monkeypatch.setattr(match_mod, "ask", fake_ask)
    monkeypatch.setattr(match_mod.store, "keyword_search", fake_keyword_search)


_RESUME = {"skills": [{"name": "Java"}], "experience": [{"company": "X", "title": "Engineer",
           "start": "2019-01", "end": "present", "bullets": ["Java services"]}],
           "projects": [], "education": [{"school": "S", "degree": "bachelor"}], "profile": {}}
_JD = {"title": "Backend Engineer", "company": "Acme", "experienceYears": 3,
       "education": {"minDegree": "bachelor"},
       "requiredSkills": [{"name": "Java", "priority": "must", "evidence_phrase": "java"},
                          {"name": "Kubernetes", "priority": "must", "evidence_phrase": "k8s"}],
       "preferredSkills": [{"name": "Rust", "priority": "nice"}],
       "interviewTopics": ["systems design"]}


async def test_compute_match_emits_both_explanations(monkeypatch):
    calls: list = []
    _stub_io(monkeypatch, calls)
    result = await compute_match(_RESUME, _JD, user_id="u-1")

    assert result["whyMatch"] == [
        "Your resume covers 1 of the 3 skills this JD lists: Java.",
        "Experience: 6.0y experience >= required 3y.",
        "Education meets the stated minimum (bachelor).",
    ]
    assert [i["title"] for i in result["preparation"]] == [
        "Add concrete evidence of Kubernetes", "Add concrete evidence of Rust"]
    assert [i["priority"] for i in result["preparation"]] == ["must", "nice"]
    assert "why_match" not in result and "whyMatch" in result, "the wire key is the camelCase one"


async def test_compute_match_preparation_worths_match_the_score_gap(monkeypatch):
    # The card promises the ordering is by score worth; here the promise is checked against the
    # overall score the same resume/job pair actually produces.
    calls: list = []
    _stub_io(monkeypatch, calls)
    result = await compute_match(_RESUME, _JD, user_id="u-1")
    full_resume = {**_RESUME, "skills": [{"name": "Java"}, {"name": "Kubernetes"},
                                         {"name": "Rust"}]}
    improved = await compute_match(full_resume, _JD, user_id="u-1")
    promised = sum(float(re.search(r"([\d.]+) points", i["reason"]).group(1))
                   for i in result["preparation"])
    assert improved["overall"] - result["overall"] == pytest.approx(promised / 100, abs=0.005)


async def test_compute_match_why_match_is_empty_for_a_thin_jd(monkeypatch):
    # A JD listing no skills and stating no bars: every dimension is neutral, so the panel gets no
    # bullets rather than three invented ones.
    calls: list = []
    _stub_io(monkeypatch, calls)
    result = await compute_match({"skills": [], "experience": [], "projects": [],
                                  "education": [], "profile": {}}, {"title": "Anonymous"},
                                 user_id="u-1")
    assert result["whyMatch"] == []
    assert result["preparation"] == []
