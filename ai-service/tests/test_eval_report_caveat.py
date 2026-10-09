"""The RAG report has to say which of its own numbers mean anything.

`run_eval` is routinely run with the offline providers (`mock` / `hash`) because that is
the only configuration that needs no API keys — and that is exactly the configuration
whose generation metrics are meaningless. Without the caveat the report reads as a
product claim: `faithfulness: 0.0` looks like a broken generator and `recall_at_k: 1.0`
looks like semantic retrieval, when neither is being measured.
"""

import pytest

from app.eval.run_eval import (
    METRIC_KEYS,
    _markdown,
    _provider_caveat,
    assert_something_was_measured,
    measured_metric_keys,
)
from app.eval.run_agent_eval import (
    _markdown as agent_markdown,
    _provider_caveat as agent_caveat,
    assert_something_was_measured as agent_measured,
)


def test_a_real_provider_pair_gets_no_caveat():
    assert _provider_caveat({"llm_provider": "openai_compat",
                             "embedding_provider": "openai"}) == []


def test_a_stub_llm_disclaims_only_the_generation_metrics():
    out = " ".join(_provider_caveat({"llm_provider": "mock",
                                     "embedding_provider": "openai"}))
    assert "Generation is unmeasured" in out
    assert "answer_relevance" in out and "faithfulness" in out
    # The retrieval numbers are still earned, so they must not be disclaimed too.
    assert "keyword-driven" not in out


def test_a_hash_embedder_disclaims_the_semantic_claim():
    out = " ".join(_provider_caveat({"llm_provider": "openai_compat",
                                     "embedding_provider": "hash"}))
    assert "keyword-driven" in out
    assert "Generation is unmeasured" not in out


def test_both_offline_disclaims_both():
    out = " ".join(_provider_caveat({"llm_provider": "mock",
                                     "embedding_provider": "hash"}))
    assert "Generation is unmeasured" in out and "keyword-driven" in out


def test_a_missing_config_does_not_crash_or_invent_a_caveat():
    assert _provider_caveat({}) == []


# ------------------------------------------- a run that measured nothing is not a result

def test_a_run_that_scored_nothing_refuses_to_pass():
    """The summary used to print `n_cases: 0, aggregate: {}` and exit 0, so a corpus that
    never landed read exactly like a clean run — and an empty aggregate cannot be told
    from a perfect one by anyone skimming."""
    report = {"n_cases": 0, "skipped": [{"id": f"gs-{i:02d}"} for i in range(1, 16)]}
    with pytest.raises(SystemExit) as exit_info:
        assert_something_was_measured(report)
    message = str(exit_info.value)
    assert "0 of 15 cases scored" in message
    assert "absence, not a score" in message
    # It has to name the thing to check, or the reader is left with a number and no move.
    assert "smoke-fullstack" in message and "no_ground_truth" in message


def test_a_run_that_scored_something_passes():
    assert assert_something_was_measured({"n_cases": 13, "skipped": []}) is None


def test_partial_skips_are_normal_and_must_not_fail():
    """Two of fifteen skipping is the documented behaviour (the seeded resume has no
    internship section for those cases), so this guard must not fire on it."""
    skipped = [{"id": "gs-03"}, {"id": "gs-05"}]
    assert assert_something_was_measured({"n_cases": 13, "skipped": skipped}) is None


def test_an_agent_run_that_ran_nothing_refuses_to_pass():
    """`errors: 0` and `forbidden_violations: 0` are vacuously true of an empty run, which
    makes an empty agent report read as a *good* one rather than an absent one."""
    with pytest.raises(SystemExit) as exit_info:
        agent_measured({"n_scenarios": 0})
    message = str(exit_info.value)
    assert "0 scenarios ran" in message
    assert "vacuously true" in message and "nothing was asked" in message


def test_an_agent_run_that_ran_scenarios_passes():
    assert agent_measured({"n_scenarios": 3}) is None


def test_an_agent_run_where_every_scenario_errored_refuses_to_pass():
    """The provider dying mid-run is the worse case: the report is *full*, and prints
    `tool_precision: 1.0` off the failure paths beside `errors: 27, avg_steps: 0`.
    A real instance of this read as "the prompt change hurt recall"."""
    with pytest.raises(SystemExit) as exit_info:
        agent_measured({"n_scenarios": 27,
                        "aggregate": {"errors": 27, "avg_steps": 0.0,
                                      "tool_recall": 0.1852, "tool_precision": 1.0}})
    message = str(exit_info.value)
    assert "all 27 scenarios errored" in message
    assert "artifacts rather than scores" in message
    assert "0xc0000409" in message  # names the cause actually hit on this box


def test_a_few_errors_among_many_is_a_real_result_and_must_pass():
    """The metrics are defined over the runs that completed, so a partial failure is a
    measurement -- refusing it would make the guard worse than none."""
    assert agent_measured({"n_scenarios": 27, "aggregate": {"errors": 2}}) is None


# ------------------------------------------------- an absent answer is not a measurement

def test_a_retrieval_only_run_reports_no_generation_metrics():
    """`--answer` off means no answer was generated, so there is nothing to score."""
    keys = measured_metric_keys(answer_requested=False)
    assert "recall_at_k" in keys and "context_relevance" in keys
    assert "answer_relevance" not in keys and "faithfulness" not in keys


def test_a_generating_run_reports_all_of_them():
    assert set(measured_metric_keys(answer_requested=True)) == set(METRIC_KEYS)


def test_the_report_says_generation_was_not_run():
    out = " ".join(_provider_caveat({"llm_provider": "openai_compat",
                                     "embedding_provider": "openai",
                                     "answer": False}))
    assert "Generation was not run" in out
    # Absent, not zero -- the distinction the report previously got wrong in both
    # directions: it published a tautological 1.0 for faithfulness.
    assert "absent from the table rather than zero" in out


def test_the_answer_note_and_the_stub_note_can_coexist():
    out = " ".join(_provider_caveat({"llm_provider": "mock",
                                     "embedding_provider": "hash",
                                     "answer": False}))
    assert "Generation was not run" in out and "Generation is unmeasured" in out


# ---------------------------------------------------------------- rendering

def _report(**over):
    base = {
        "experiment": "t", "n_cases": 1, "skipped": [], "avg_retrieval_ms": 1.0,
        "config": {"llm_provider": "mock", "embedding_provider": "hash"},
        "aggregate": {"recall_at_k": 1.0},
        "cases": [{"case": "gs-01", "recall_at_k": 1.0, "precision_at_k": 1.0,
                   "mrr": 1.0, "ndcg_at_k": 1.0, "faithfulness": 0.0, "judge": "lexical"}],
    }
    base.update(over)
    base["caveat"] = _provider_caveat(base["config"])
    return base


def test_the_caveat_is_a_separate_block_not_absorbed_into_the_table():
    """A heading with no blank line above it is swallowed by the table in Markdown."""
    md = _markdown(_report())
    assert "\n\n## What these numbers mean\n" in md


def test_no_caveat_leaves_the_report_unchanged():
    md = _markdown(_report(config={"llm_provider": "openai_compat",
                                   "embedding_provider": "openai"}))
    assert "What these numbers mean" not in md


# ---------------------------------------------------------------- the agent report

def test_the_agent_report_disclaims_tool_selection_under_a_stub():
    """Same reasoning as the RAG caveat, different metric: `tool_f1` under `mock`
    measures a three-keyword router against the 15 tools the orchestrator offers."""
    out = " ".join(agent_caveat({"llm_provider": "mock"}))
    assert "Tool selection is unmeasured" in out
    assert "three-keyword" in out and "15 tools" in out
    # What the run DOES establish has to be said too, or 0 violations reads as vacuous.
    assert "forbidden_violations" in out


def test_the_agent_report_is_silent_under_a_real_provider():
    assert agent_caveat({"llm_provider": "openai_compat"}) == []


def test_the_agent_caveat_is_a_separate_block_too():
    report = {"experiment": "t", "n_scenarios": 1, "skipped": [],
              "config": {"llm_provider": "mock", "llm_model": "m", "user_id": "u"},
              "aggregate": {"tool_f1": 0.1}, "by_tag": {}, "cases": [],
              "caveat": agent_caveat({"llm_provider": "mock"})}
    assert "\n\n## What these numbers mean\n" in agent_markdown(report)
