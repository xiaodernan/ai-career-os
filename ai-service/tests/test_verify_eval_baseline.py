"""The eval-baseline verifier grades a run before it grades a number.

Nothing here runs a retrieval. The fixtures are the shapes the project's own
history actually produced: a 15/15 report with every metric at 1.0, an ollama
run where 13 of 15 cases fell back to the lexical judge after an inference
outage, and a 3-of-15 run that still printed 1.0 across the board.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.ops import verify_eval_baseline as vb

AI = Path(__file__).resolve().parents[1]
BASELINE = AI / "evals" / "baseline.json"


def _report(**overrides) -> dict:
    report = {
        "experiment": "fixture",
        "generated_at": "2026-11-09T00:00:00+0000",
        "config": {"llm_provider": "mock", "embedding_provider": "hash",
                   "answer": False},
        "n_cases": 15,
        "skipped": [],
        "aggregate": {"recall_at_k": 1.0, "mrr": 1.0, "context_relevance": 0.9333},
        "cases": [{"judge": "lexical"} for _ in range(15)],
    }
    report.update(overrides)
    return report


def _write(tmp_path, name, payload) -> str:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def _argv(report: str, baseline: str | None = None) -> list[str]:
    args = ["--report", report]
    if baseline is not None:
        args += ["--baseline", baseline]
    return args


# ------------------------------------------------------------------ preflight

def test_a_clean_report_has_nothing_to_refuse():
    assert vb.preflight(_report()) == []


@pytest.mark.parametrize("key,value", [
    ("aggregate", {"errors": 2, "recall_at_k": 1.0}),
    ("aggregate", {"infra_errors": 1, "recall_at_k": 1.0}),
    ("aggregate", {"agent_errors": 3, "recall_at_k": 1.0}),
    ("errors", 4),
])
def test_an_error_count_is_read_before_any_metric(key, value):
    problems = vb.preflight(_report(**{key: value}))
    assert problems and "errors" in problems[0].lower()


def test_zero_cases_is_refused_even_with_a_perfect_aggregate():
    problems = vb.preflight(_report(n_cases=0))
    assert any("0 cases scored" in p for p in problems)


def test_skipped_cases_are_refused_by_name():
    skipped = [{"id": "gs-01", "reason": "no_ground_truth"},
               {"id": "gs-04", "reason": "no_ground_truth"}]
    problems = vb.preflight(_report(skipped=skipped))
    assert any("gs-01" in p and "gs-04" in p and "--require-all-cases" in p
               for p in problems)


def test_a_real_provider_with_partial_lexical_fallback_is_an_outage():
    """13 of 15 fell back: 'every case fell back' would have missed this."""
    cases = [{"judge": "lexical"} for _ in range(13)] + [{"judge": "llm"} for _ in range(2)]
    report = _report(config={"llm_provider": "ollama", "embedding_provider": "hash",
                             "answer": True}, cases=cases)
    problems = vb.preflight(report)
    assert len(problems) == 1 and "13/15" in problems[0] and "outage" in problems[0]


def test_a_real_provider_whose_judges_all_answered_is_not_an_outage():
    report = _report(config={"llm_provider": "ollama", "embedding_provider": "hash",
                             "answer": True},
                     cases=[{"judge": "llm"} for _ in range(15)])
    assert vb.preflight(report) == []


def test_an_offline_mock_provider_legitimately_uses_the_lexical_judge():
    assert vb.preflight(_report()) == []


def test_population_reads_both_report_spellings():
    assert vb.population(_report()) == 15
    assert vb.population(_report(n_cases=None, n_scenarios=43)) == 43


# --------------------------------------------------------------------- compare

def test_a_small_delta_passes_and_a_large_one_is_named():
    baseline = {"aggregate": {"recall_at_k": 1.0, "mrr": 1.0}}
    assert vb.compare(baseline, _report(aggregate={"recall_at_k": 0.98,
                                                   "mrr": 1.0}), 0.05) == []
    out = vb.compare(baseline, _report(aggregate={"recall_at_k": 0.2,
                                                  "mrr": 1.0}), 0.05)
    assert len(out) == 1 and "recall_at_k: 1.0 -> 0.2" in out[0]


def test_metrics_only_the_baseline_names_are_compared():
    """An --answer run adds metrics a retrieval-only baseline never measured."""
    baseline = {"aggregate": {"recall_at_k": 1.0}}
    report = _report(aggregate={"recall_at_k": 1.0, "faithfulness": 0.0})
    assert vb.compare(baseline, report, 0.05) == []


def test_no_shared_metric_is_a_contract_error_not_a_pass():
    out = vb.compare({"aggregate": {"tool_recall": 1.0}},
                     _report(aggregate={"recall_at_k": 1.0}), 0.05)
    assert out and "no metric in common" in out[0]


# ------------------------------------------------------------------ CLI / main

def test_main_passes_a_clean_run(tmp_path, capsys):
    base = _write(tmp_path, "baseline.json", {"tolerance": 0.05,
                                              "aggregate": {"recall_at_k": 1.0,
                                                            "mrr": 1.0,
                                                            "context_relevance": 0.9333}})
    report = _write(tmp_path, "report.json", _report())
    assert vb.main(_argv(report, base)) == 0
    assert "OK fixture" in capsys.readouterr().out


def test_main_refuses_a_regression_without_writing_anything(tmp_path, capsys):
    base = _write(tmp_path, "baseline.json", {"tolerance": 0.05,
                                              "aggregate": {"recall_at_k": 1.0}})
    report = _write(tmp_path, "report.json", _report(aggregate={"recall_at_k": 0.2}))
    assert vb.main(_argv(report, base)) == 1
    assert "REGRESSION recall_at_k" in capsys.readouterr().err


def test_main_reports_a_contract_error_for_a_missing_baseline(tmp_path, capsys):
    report = _write(tmp_path, "report.json", _report())
    assert vb.main(_argv(report, str(tmp_path / "absent.json"))) == 2
    assert "--write-baseline" in capsys.readouterr().err


def test_main_reports_a_contract_error_for_a_malformed_report(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert vb.main(_argv(str(bad))) == 2


def test_write_baseline_dates_from_the_report_not_from_today(tmp_path):
    report_path = _write(tmp_path, "report.json", _report())
    out = tmp_path / "new-baseline.json"
    rc = vb.main(["--report", report_path, "--baseline", str(out),
                  "--write-baseline"])
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["recorded_at"] == "2026-11-09T00:00:00+0000"
    assert payload["n_cases"] == 15 and payload["schema"] == 1
    assert "errors" not in payload["aggregate"]
    # the written baseline can grade the very report it came from
    assert vb.main(_argv(report_path, str(out))) == 0


# --------------------------------------------------- the checked-in baseline

def test_the_checked_in_baseline_names_a_real_source_and_a_full_population():
    """A baseline nobody can trace is a number someone typed, not a measurement."""
    payload = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert payload["schema"] == 1
    assert payload["n_cases"] == 15
    assert payload["provider"] == "mock/hash"
    assert payload["source"].startswith("evals/reports/")
    assert payload["recorded_at"].startswith("2026-10-14")
    assert payload["tolerance"] == 0.05
    assert payload["aggregate"]["recall_at_k"] == 1.0
    assert set(payload["aggregate"]) == {
        "recall_at_k", "precision_at_k", "mrr", "ndcg_at_k", "hit_at_k",
        "context_relevance"}
