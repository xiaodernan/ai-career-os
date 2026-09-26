"""Unit tests for the deterministic resume-score rubric (PRD §3, Resume Score).

``compute_resume_score`` is pure (no LLM/DB) and load-bearing: its map is persisted verbatim by
the backend and read by the frontend ``normalizeResumeScore``. It answers ``{total, detail}`` plus
one 0-100 figure per rubric dimension (#131 gave the resume panel's five bars a producer; the
dimension each criterion belongs to is declared once, in ``_DIMENSION_OF``). These lock every
criterion's boundary and the ``total == sum(points where met)`` invariant, and *document* (not
"fix") that the ten criteria sum to 110 — the UI clamps this to 100 via ``pct()``,
so the extra headroom only compresses the very top of the distribution rather than
showing a broken number. Changing the weights would move every stored score, which
is a product decision, so the max is asserted as-is.
"""

from app.features.resume_parse import (
    DIMENSIONS,
    _DIMENSION_OF,
    _merge_skills,
    compute_resume_score,
    parse_resume,
)

_CRITERIA = {
    "has_contact", "has_summary", "has_experience", "experience_has_bullets",
    "quantified_impact", "has_projects", "has_education", "has_skills",
    "years_experience_stated", "dates_present",
}


def _perfect() -> dict:
    return {
        "profile": {"email": "a@b.co", "summary": "senior eng", "yearsExperience": 5},
        "experience": [{"company": "X", "title": "T", "start": "2019-01", "end": "2022-01",
                        "bullets": ["led 3 squads", "cut latency 20%", "shipped v2"]}],
        "projects": [{"name": "p"}],
        "education": [{"school": "s"}],
        "skills": [{"name": f"s{i}"} for i in range(5)],
    }


def test_score_detail_lists_every_criterion_and_sums_to_total():
    out = compute_resume_score(_perfect())
    assert {d["criterion"] for d in out["detail"]} == _CRITERIA
    assert out["total"] == sum(d["points"] for d in out["detail"] if d["met"])
    assert all(set(d) == {"criterion", "met", "points"} for d in out["detail"])


def test_score_perfect_resume_is_110_documents_scale():
    # Real max is 110 (UI clamps to 100 via pct()). Asserted to pin the rubric,
    # NOT a regression — see module docstring.
    assert compute_resume_score(_perfect())["total"] == 110


def test_score_empty_resume_is_zero():
    out = compute_resume_score({})
    assert out["total"] == 0
    assert all(d["met"] is False for d in out["detail"])


# ---------------- dimensions (#131: the resume panel's five bars) ----------------


def test_every_criterion_is_credited_to_exactly_one_dimension():
    # The grouping table is the only place a criterion can be assigned, so both directions have to
    # agree with the rubric the function actually runs: no criterion outside the table (it would be
    # counted in `total` but in no bar), no dimension with nothing in it (it would render 0/0).
    out = compute_resume_score(_perfect())
    assert {d["criterion"] for d in out["detail"]} == set(_DIMENSION_OF)
    assert {_DIMENSION_OF[d["criterion"]] for d in out["detail"]} == set(DIMENSIONS)


def test_perfect_and_empty_resume_sit_at_the_ends_of_every_dimension():
    perfect = compute_resume_score(_perfect())
    assert {d: perfect[d] for d in DIMENSIONS} == dict.fromkeys(DIMENSIONS, 100)
    empty = compute_resume_score({})
    assert {d: empty[d] for d in DIMENSIONS} == dict.fromkeys(DIMENSIONS, 0)


def test_a_dimension_is_scored_on_its_own_points_not_as_a_share_of_the_total():
    # `keywords` is one 10-point criterion of the 110-point rubric, so a skills-only resume is 9% of
    # its total and 100% of that dimension. Reporting the share of `total` would read 9 on a bar the
    # panel labels "Keyword coverage", which is a different claim than the rubric makes.
    only_skills = compute_resume_score({"skills": [{"name": f"s{i}"} for i in range(5)]})
    assert only_skills["total"] == 10
    assert only_skills["keywords"] == 100
    assert {d: only_skills[d] for d in DIMENSIONS if d != "keywords"} == dict.fromkeys(
        [d for d in DIMENSIONS if d != "keywords"], 0)


def test_a_half_filled_dimension_reports_its_own_percentage():
    # has_contact(15) + has_summary(10) of the 65 points `structure` holds: 38, not 25/110 = 23.
    half = compute_resume_score({"profile": {"email": "a@b.co", "summary": "senior eng"}})
    assert half["total"] == 25
    assert half["structure"] == 38


def test_score_contact_from_phone_only():
    detail = {d["criterion"]: d["met"] for d in compute_resume_score(
        {"profile": {"phone": "123"}})["detail"]}
    assert detail["has_contact"] is True


def test_score_quantified_impact_needs_digit_or_percent():
    def impact(bullets):
        d = compute_resume_score({"experience": [{"start": "2019", "bullets": bullets}]})
        return next(x["met"] for x in d["detail"] if x["criterion"] == "quantified_impact")
    assert impact(["improved by 20%"]) is True       # ascii percent
    assert impact(["提升了２０％"]) is True             # full-width percent
    assert impact(["grew traffic 3x"]) is True       # a digit
    assert impact(["built a dashboard"]) is False     # no number, no percent


def test_score_experience_bullets_boundary_is_three():
    def met(n):
        parsed = {"experience": [{"start": "2019", "bullets": ["b"] * n}]}
        return next(x["met"] for x in compute_resume_score(parsed)["detail"]
                    if x["criterion"] == "experience_has_bullets")
    assert met(2) is False
    assert met(3) is True


def test_score_has_skills_boundary_is_five():
    def met(n):
        return next(x["met"] for x in compute_resume_score(
            {"skills": [{"name": f"s{i}"} for i in range(n)]})["detail"]
            if x["criterion"] == "has_skills")
    assert met(4) is False
    assert met(5) is True


def test_score_dates_present_requires_start_on_every_role():
    def met(exp):
        return next(x["met"] for x in compute_resume_score({"experience": exp})["detail"]
                    if x["criterion"] == "dates_present")
    assert met([{"start": "2019"}, {"start": "2020"}]) is True
    assert met([{"start": "2019"}, {"start": ""}]) is False
    assert met([]) is False   # no experience -> vacuously not credited


# ---------------- _merge_skills ----------------


def test_merge_skills_preserves_explicit_category_and_proficiency():
    # An explicit category from the model wins even if it disagrees with the
    # canonical vocabulary; the name is still normalised.
    out = _merge_skills([{"name": "react", "category": "lang", "proficiency": 5}], [])
    assert out == [{"name": "React", "category": "lang", "proficiency": 5}]


def test_merge_skills_text_only_falls_back_to_canonical_category():
    out = _merge_skills([], ["Python"])
    assert out == [{"name": "Python", "category": "language", "proficiency": None}]


def test_merge_skills_dedups_and_lets_llm_entry_win():
    # LLM skills are seen first, so "Python" is kept once with its proficiency.
    out = _merge_skills([{"name": "Python", "proficiency": 3}], ["Python"])
    assert len(out) == 1
    assert out[0] == {"name": "Python", "category": "language", "proficiency": 3}


def test_merge_skills_collapses_aliases_to_one_canonical():
    out = _merge_skills([{"name": "react.js"}], ["React"])
    assert [s["name"] for s in out] == ["React"]


def test_merge_skills_dedups_case_insensitively():
    out = _merge_skills([{"name": "AWS"}, {"name": "aws"}], [])
    assert [s["name"] for s in out] == ["AWS"]


def test_merge_skills_empty_inputs():
    assert _merge_skills([], []) == []


# ---------------- parse_resume null-collection guard ----------------


async def test_parse_resume_survives_null_missingsections_and_warnings(monkeypatch):
    # Regression: the model may emit "missingSections": null / "warnings": null
    # (JSON-mode does this when it finds nothing). The old raw.setdefault(...) only
    # defaulted *missing* keys, so a present-null stayed None and the
    # missingSections append crashed with AttributeError. parse_resume must coerce
    # present-null to [] exactly like its sibling raw.get("skills") or [] guards.
    async def fake_ask_json(*a, **k):
        return {"profile": {"name": "Ada"}, "missingSections": None, "warnings": None}
    monkeypatch.setattr("app.features.resume_parse.ask_json", fake_ask_json)
    out = await parse_resume("Built dashboards with Python and React.")
    assert isinstance(out["missingSections"], list)
    assert isinstance(out["warnings"], list)
    # sections absent from the parsed output are recorded, not swallowed.
    assert "experience" in out["missingSections"]
    assert "projects" in out["missingSections"]


async def test_parse_resume_keeps_populated_missingsections(monkeypatch):
    async def fake_ask_json(*a, **k):
        return {"profile": {"name": "Ada"}, "missingSections": ["achievements"],
                "warnings": []}
    monkeypatch.setattr("app.features.resume_parse.ask_json", fake_ask_json)
    out = await parse_resume("Ran Kafka pipelines.")
    assert "achievements" in out["missingSections"]
