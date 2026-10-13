"""The interview eval runner: the third harness must be runnable, and must refuse
to exit 0 over a degenerate set (PRD §15, §34).

RAG has `run_eval.py`, the agent path has `run_agent_eval.py`; the interview path
until now could only be scored from inside pytest, so no human ever saw the
discrimination report the fixtures were built to produce. These tests hold the
runner's contract: it writes both report formats, every fixture is named in the
markdown with the metric that vetoes it, and the two degenerate outcomes — every
fixture the same verdict, or an empty set — are refused the way
`run_agent_eval.assert_something_was_measured` refuses a run that measured nothing.
"""

import json

import pytest

from app.eval.interview_dataset import load_interviews
from app.eval.run_interview_eval import (
    _markdown,
    assert_something_was_measured,
    parse_args,
    run,
    score_set,
)


def _args(tmp_path, experiment="iv-test"):
    return parse_args(["--experiment", experiment, "--out", str(tmp_path)])


# ----------------------------- the report artifacts ----------------------------


def test_the_runner_writes_a_json_and_a_markdown_report(tmp_path):
    report = run(_args(tmp_path, "artifact-check"))
    jpath, mpath = map(str, report["_files"])
    assert jpath.endswith("artifact-check.json") and mpath.endswith("artifact-check.md")
    loaded = json.loads(open(jpath, encoding="utf-8").read())
    assert loaded["n_interviews"] == len(load_interviews())
    for key in ("discrimination", "follow_up_discipline", "difficulty_discipline",
                "report_completeness", "grounding", "pass_rate", "n_interviews"):
        assert key in loaded["aggregate"], key
    assert loaded["experiment"] == "artifact-check"


def test_the_markdown_names_every_fixture_with_its_verdict(tmp_path):
    report = run(_args(tmp_path, "md-shape"))
    md = open(report["_files"][1], encoding="utf-8").read()
    for t in load_interviews():
        assert f"| {t.id} |" in md, f"fixture {t.id} missing from the cases table"
    assert "## Why the failing fixtures fail" in md


def test_the_markdown_lists_the_metric_that_vetoes_each_known_failure(tmp_path):
    """A reader who sees `flat: no` needs to know the veto was discrimination and
    not, say, completeness — the same contract the agent runner applies when it
    lists per-scenario failure reasons."""
    report = run(_args(tmp_path, "vetoes"))
    md = open(report["_files"][1], encoding="utf-8").read()
    vetoed = {
        "flat": "discrimination",
        "missing_question": "follow_up_discipline",
        "out_of_band": "difficulty_discipline",
        "fabricated": "grounding",
        "zh_fabricated": "grounding",
    }
    for fixture, metric in vetoed.items():
        line = next(l for l in md.splitlines()
                    if l.startswith(f"- **{fixture}**"))
        assert metric in line, f"{fixture} should name {metric}: {line}"


def test_the_markdown_carries_the_honest_caveat(tmp_path):
    """The numbers describe scripted shapes, not model quality; a reader who only
    sees the artifact must not have to hunt for that."""
    report = run(_args(tmp_path, "caveat"))
    md = open(report["_files"][1], encoding="utf-8").read()
    assert "scripted shapes" in md and "not that any particular interview was good" in md


# --------------------------- the discrimination guard ---------------------------


def test_the_real_golden_set_passes_the_discrimination_guard(tmp_path):
    report = run(_args(tmp_path, "golden"))
    assert_something_was_measured(report)  # must not raise
    assert 0 < report["aggregate"]["pass_rate"] < 1, (
        "a golden set where everything (or nothing) passes measured nothing")


def test_an_empty_fixture_set_refuses_to_exit_zero():
    report = {"n_interviews": 0, "cases": [], "aggregate": {}}
    with pytest.raises(SystemExit, match="nothing was measured"):
        assert_something_was_measured(report)


def test_a_rubber_stamp_harness_refuses_to_exit_zero():
    """Every fixture passing is the defect the golden set exists to catch: the
    scorer stopped discriminating, and pass_rate 1.0 would read as good."""
    report = {"n_interviews": 3,
              "cases": [{"passed": True}] * 3,
              "aggregate": {"pass_rate": 1.0}}
    with pytest.raises(SystemExit, match="cannot tell"):
        assert_something_was_measured(report)


def test_a_scorer_that_fails_everything_also_refuses():
    """The other degenerate verdict: the scorer broke, and pass_rate 0.0 reads as
    'every interview was bad' rather than 'nothing can pass'."""
    report = {"n_interviews": 3,
              "cases": [{"passed": False}] * 3,
              "aggregate": {"pass_rate": 0.0}}
    with pytest.raises(SystemExit, match="cannot tell"):
        assert_something_was_measured(report)


# ------------------------------- the score rows -------------------------------


def test_case_rows_carry_the_fixture_id():
    rows = score_set(load_interviews())
    assert [r["id"] for r in rows] == [t.id for t in load_interviews()]
    assert "flat" in {r["id"] for r in rows}


def test_an_unnamed_transcript_is_labelled_rather_than_blank():
    from app.eval.interview_metrics import InterviewTranscript

    rows = score_set([InterviewTranscript()])
    assert rows[0]["id"] == "(unnamed)"


def test_the_markdown_renders_without_any_failing_fixture(tmp_path):
    """A hypothetical all-passing set still renders (the failing section is
    conditional); the refusal lives in the guard, not the formatter."""
    report = {"experiment": "x", "generated_at": "now", "n_interviews": 1,
              "aggregate": {"pass_rate": 1.0},
              "cases": [{"id": "only", "discrimination": 1.0,
                         "follow_up_discipline": 1.0, "difficulty_discipline": 1.0,
                         "report_completeness": 1.0, "grounding": 1.0,
                         "adapted": True, "passed": True}]}
    md = _markdown(report)
    assert "| only |" in md
    assert "Why the failing fixtures fail" not in md
