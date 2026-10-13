"""The RAG experiment runner's new knobs and its two-report diff (PRD §32).

Nothing here runs a retrieval: the runner needs a database and a provider. What is
pinned is the arithmetic and the argument surface, so an experiment's flag cannot
silently stop varying the thing it claims to vary.
"""

import json

from app.eval import run_eval as ev


def _write(path, aggregate):
    path.write_text(json.dumps({"aggregate": aggregate}), encoding="utf-8")


def test_diff_reports_only_metrics_both_runs_measured(tmp_path):
    """Comparing a retrieval-only run against an `--answer` run would otherwise
    report generation metrics that never existed on one side."""
    a = tmp_path / "before.json"
    _write(a, {"recall_at_k": 0.8, "mrr": 0.5, "answer_relevance": 0.4})
    lines = ev.diff_reports(str(a), {"aggregate": {"recall_at_k": 0.9, "mrr": 0.5,
                                                  "hit_at_k": 1.0}})
    body = "\n".join(lines)
    assert "recall_at_k" in body and "| 0.8 | 0.9 | +0.1 |" in body
    assert "mrr" in body
    # one-sided metrics are not invented as zero
    assert "answer_relevance" not in body
    assert "hit_at_k" not in body


def test_a_negative_delta_is_signed(tmp_path):
    a = tmp_path / "before.json"
    _write(a, {"recall_at_k": 0.9})
    lines = "\n".join(ev.diff_reports(str(a), {"aggregate": {"recall_at_k": 0.8}}))
    assert "-0.1" in lines


def test_two_runs_with_no_metric_in_common_degrade_to_a_stated_row(tmp_path):
    a = tmp_path / "before.json"
    _write(a, {"recall_at_k": 0.8})
    lines = "\n".join(ev.diff_reports(str(a), {"aggregate": {"mrr": 0.5}}))
    assert "no metrics measured by both runs" in lines


def test_an_unreadable_baseline_says_so_rather_than_crashing(tmp_path):
    lines = "\n".join(ev.diff_reports(str(tmp_path / "nope.json"), {"aggregate": {}}))
    assert "diff unavailable" in lines


def test_the_new_experiment_flags_exist():
    argv = ev.parse_args(["--user-id", "u"])
    assert argv.strategy is None
    assert argv.max_expansions == -1
    assert argv.prompt is None
    assert argv.chunk_target_tokens == 0
    assert argv.diff is None


def test_the_new_flags_reach_the_parsed_namespace():
    argv = ev.parse_args(["--user-id", "u", "--strategy", "keyword",
                          "--max-expansions", "1", "--prompt", "variant",
                          "--chunk-target-tokens", "500", "--diff", "/x.json"])
    assert argv.strategy == "keyword"
    assert argv.max_expansions == 1
    assert argv.prompt == "variant"
    assert argv.chunk_target_tokens == 500
    assert argv.diff == "/x.json"


def test_measured_metric_keys_keep_citation_out_of_retrieval_only_runs():
    """`citation_correctness` needs an answer to cite anything; averaging it over a
    retrieval-only run would publish 0.0 as a measurement."""
    assert "citation_correctness" in ev.measured_metric_keys(True)
    assert "citation_correctness" not in ev.measured_metric_keys(False)
