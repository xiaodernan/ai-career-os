"""Interview evaluation: the metric math and the discrimination it is built for (PRD §15).

No DB, no LLM. The transcript fixtures are scripted shapes an interviewer can
legitimately produce, so each score can be checked against a known answer.
"""

from app.eval.interview_dataset import (
    FABRICATED_WEAKNESS_REPORT,
    FLAT_REPORT,
    FLAT_TURNS,
    MISSING_QUESTION_MOVES,
    OUT_OF_BAND_MOVES,
    STRONG_MOVES,
    STRONG_REPORT,
    STRONG_TURNS,
    WEAK_REPORT,
    WEAK_TURNS,
    ZH_FABRICATED_REPORT,
    ZH_HONEST_REPORT,
    ZH_TURNS,
    load_interviews,
)
from app.eval.interview_metrics import (
    InterviewTranscript,
    adapted,
    dimension_discrimination,
    difficulty_discipline,
    follow_up_discipline,
    grounding,
    report_completeness,
    score_interview,
)


def _t(turns, moves, report):
    return InterviewTranscript(turns=turns, moves=moves, report=report)


# --------------------------- dimension discrimination ---------------------------


def test_a_flat_report_does_not_discriminate():
    """Eight identical scores is the defect the metric exists for: the numbers look
    complete and the report has said nothing about the candidate."""
    assert dimension_discrimination(FLAT_REPORT) == 0.0


def test_a_spread_report_discriminates():
    assert dimension_discrimination(STRONG_REPORT) > 0.0
    assert dimension_discrimination(WEAK_REPORT) > 0.0


def test_discrimination_tracks_the_size_of_the_spread():
    narrow = {"dims": {"a": 0.79, "b": 0.8}}                      # 0.01 spread
    wide = {"dims": {"a": 0.2, "b": 0.9}}                          # 0.7 spread
    assert dimension_discrimination(narrow) == 0.0
    assert dimension_discrimination(wide) == 1.0


def test_a_report_with_fewer_than_two_dimensions_cannot_discriminate():
    assert dimension_discrimination({"dims": {"a": 0.9}}) == 0.0
    assert dimension_discrimination({"dims": {}}) == 0.0


# ------------------------------ follow-up discipline ----------------------------


def test_a_follow_up_without_a_question_is_not_a_follow_up():
    assert follow_up_discipline(MISSING_QUESTION_MOVES) == 0.0
    assert follow_up_discipline(STRONG_MOVES) == 1.0


def test_no_follow_ups_is_not_a_failure():
    """A session that asked only fresh questions still did its job; the metric is
    about the follow-ups that happened, not the ones that did not."""
    assert follow_up_discipline([{"action": "next_topic", "question": "q"}]) == 1.0
    assert follow_up_discipline([]) == 1.0


def test_a_partially_asked_ladder_scores_the_share():
    moves = [
        {"action": "followup", "question": "real question"},
        {"action": "followup", "question": ""},
    ]
    assert follow_up_discipline(moves) == 0.5


# ---------------------------- difficulty discipline -----------------------------


def test_a_ladder_that_left_the_clamp_band_fails():
    """Two of three moves outside the band is 2/3 of the ladder non-compliant, which
    the metric reports as a partial score rather than all-or-nothing."""
    assert difficulty_discipline(OUT_OF_BAND_MOVES, _t([], OUT_OF_BAND_MOVES, {})) < 1.0
    assert difficulty_discipline(OUT_OF_BAND_MOVES,
                                 _t([], OUT_OF_BAND_MOVES, {})) == round(1 - 2 / 3, 4)
    assert difficulty_discipline(STRONG_MOVES, _t([], STRONG_MOVES, {})) == 1.0


def test_a_non_numeric_difficulty_is_ignored_rather_than_charged():
    moves = [{"action": "next_topic", "difficulty": None},
             {"action": "next_topic", "difficulty": 0.4}]
    assert difficulty_discipline(moves, _t([], moves, {})) == 1.0


def test_adapted_detects_a_ladder_that_actually_moved():
    assert adapted(STRONG_MOVES) is True
    flat = [{"action": "next_topic", "difficulty": 0.5, "question": "q"} for _ in range(3)]
    assert adapted(flat) is False


# ----------------------------- report completeness ------------------------------


def test_a_full_six_section_report_is_complete():
    assert report_completeness(STRONG_REPORT) == 1.0


def test_an_empty_list_section_is_not_a_filled_section():
    thin = {**STRONG_REPORT, "missing_concepts": [], "recommended_study": []}
    assert report_completeness(thin) < 1.0
    assert report_completeness({}) == 0.0


# ------------------------------------- grounding ---------------------------------


def test_a_weakness_naming_nothing_in_the_transcript_is_invented():
    """The fabricated weakness mentions Raft and quorum rollback; the candidate never
    said either. This is the tailoring verifier's rule applied to the interviewer."""
    score = grounding(FABRICATED_WEAKNESS_REPORT, _t(STRONG_TURNS, STRONG_MOVES,
                                                     FABRICATED_WEAKNESS_REPORT))
    assert score == 0.0, "a weakness with no transcript support must score 0"


def test_a_supported_weakness_is_grounded():
    score = grounding(WEAK_REPORT, _t(WEAK_TURNS, STRONG_MOVES, WEAK_REPORT))
    assert score > 0.0


def test_a_report_with_no_weakness_has_nothing_to_ground():
    assert grounding({"what_was_weak": []}, _t(STRONG_TURNS, [], {})) == 1.0


# ------------------------- CJK grounding (the zh pair) --------------------------


def test_a_zh_honest_weakness_is_grounded():
    """Regression: `_tokens` used to keep a whole CJK clause as one unmatchable
    lexeme, so an honest Chinese report shared no distinctive tokens with its own
    transcript and was scored as fabricated -- silently, on half the product's traffic."""
    score = grounding(ZH_HONEST_REPORT, _t(ZH_TURNS, STRONG_MOVES, ZH_HONEST_REPORT))
    assert score == 1.0, (
        "an honest zh weakness quoting the candidate's own words must be grounded")


def test_a_zh_fabricated_weakness_is_not_grounded():
    """The other direction of the same fix: Raft machinery the candidate never
    mentioned must still read as invented after CJK bigramming."""
    score = grounding(ZH_FABRICATED_REPORT,
                      _t(ZH_TURNS, STRONG_MOVES, ZH_FABRICATED_REPORT))
    assert score == 0.0, (
        "a zh weakness naming nothing from the transcript must score 0")


def test_the_zh_fixtures_are_scored_in_the_golden_set():
    """Both zh transcripts joined the golden set, so the aggregate the runner prints
    now covers Chinese grounding."""
    by_report = {id(t.report): t for t in load_interviews()}
    assert id(ZH_HONEST_REPORT) in by_report and id(ZH_FABRICATED_REPORT) in by_report


# ------------------------ the scorer measures what ships ------------------------


def test_the_eval_scores_the_dimensions_the_product_actually_asks_for():
    """Schema drift guard: the product prompt (features.interview.DIMENSIONS) names
    the eight keys the LLM is told to emit. The scorer hand-copied three different
    names (system_design / trade_off_analysis / domain_knowledge), so a live report's
    dims were measured against keys it never carried -- and nothing tied the two
    lists together, because the finalize lock only pins FINALIZE_FIELDS to the prompt.
    """
    from app.eval.interview_metrics import DIMENSIONS, REPORT_SECTIONS
    from app.features.interview import DIMENSIONS as FEATURE_DIMS, FINALIZE_FIELDS

    assert tuple(DIMENSIONS) == tuple(FEATURE_DIMS), (
        "the scorer's eight dimensions drifted from the prompt's")
    # The completeness metric may only ask for sections the prompt actually produces.
    assert set(REPORT_SECTIONS) <= set(FINALIZE_FIELDS), (
        "report_completeness asks for sections the prompt no longer writes")


# ------------------------------- the harness as a whole -------------------------


def test_the_golden_set_discriminates():
    """The whole point: the same scorer returns different verdicts for transcripts
    that differ in the way a real evaluator would notice. If every fixture passed,
    the harness would be a rubber stamp."""
    rows = [score_interview(t) for t in load_interviews()]
    assert len({r["passed"] for r in rows}) > 1, (
        f"every fixture passed — the harness cannot tell them apart: {rows}")
    strong = score_interview(_t(STRONG_TURNS, STRONG_MOVES, STRONG_REPORT))
    weak = score_interview(_t(WEAK_TURNS, STRONG_MOVES, WEAK_REPORT))
    assert strong["discrimination"] > 0 and strong["report_completeness"] == 1.0
    # Discrimination is spread, not quality: a bad candidate also scores spread across
    # the eight dimensions, so the strong/weak difference lives in the level, which is
    # `overall`. Asserting the wrong property here would make the harness lie.
    assert STRONG_REPORT["overall"] > WEAK_REPORT["overall"]
    assert weak["report_completeness"] == 1.0
    assert strong["passed"] is True and weak["passed"] is True


def test_the_flat_fixture_is_the_one_that_fails():
    flat = score_interview(_t(FLAT_TURNS, STRONG_MOVES, FLAT_REPORT))
    assert flat["passed"] is False
    assert flat["discrimination"] == 0.0


def test_every_fixture_carries_a_defect_it_is_named_for():
    by_name = {
        "missing_question": score_interview(_t(STRONG_TURNS, MISSING_QUESTION_MOVES,
                                               STRONG_REPORT)),
        "out_of_band": score_interview(_t(STRONG_TURNS, OUT_OF_BAND_MOVES, STRONG_REPORT)),
        "fabricated": score_interview(_t(STRONG_TURNS, STRONG_MOVES,
                                         FABRICATED_WEAKNESS_REPORT)),
    }
    assert by_name["missing_question"]["follow_up_discipline"] == 0.0
    assert by_name["out_of_band"]["difficulty_discipline"] < 1.0
    assert by_name["fabricated"]["grounding"] == 0.0


def test_the_score_row_carries_every_metric_key():
    row = score_interview(_t(STRONG_TURNS, STRONG_MOVES, STRONG_REPORT))
    for key in ("discrimination", "follow_up_discipline", "difficulty_discipline",
                "report_completeness", "grounding", "adapted", "n_turns", "n_moves",
                "passed"):
        assert key in row, key


def test_aggregate_counts_the_pass_rate():
    rows = [score_interview(t) for t in load_interviews()]
    from app.eval.interview_metrics import aggregate

    agg = aggregate(rows)
    assert agg["n_interviews"] == len(load_interviews())
    assert 0.0 <= agg["pass_rate"] <= 1.0
    assert agg["passed"] == sum(1 for r in rows if r["passed"])
