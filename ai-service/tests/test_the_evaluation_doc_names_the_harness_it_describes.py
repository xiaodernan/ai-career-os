"""EVALUATION.md names the harness it describes: the sets, the flags, the metrics.

The evaluation document makes claims a reader acts on. "The golden set is 15 cases"
is how someone decides whether a new run is comparable to the recorded baseline. The
metric tables are how someone reads a report at all -- a metric the doc names and the
scorer does not return is a column that will never fill, and one the scorer returns and
the doc does not name is a number nobody knows to look at. The runner flags are how
someone reproduces an experiment, and a flag the doc documents that the parser rejects
is a command that fails on the first paste.

None of that is checked anywhere, and all of it is the kind of claim that drifts the
moment a case is added or a metric is renamed.

The scenario count is deliberately *not* gated here. `AGENT_SCENARIOS` is growing under
a concurrent change, and pinning the doc's "27 scripted user turns" to the working tree
would make this gate red for a reason that has nothing to do with the doc being wrong.
Whoever lands those scenarios updates the sentence, exactly as the other census pins in
this suite are maintained.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
AI = ROOT / "ai-service"
DOC = ROOT / "docs" / "EVALUATION.md"
DATASET = AI / "app" / "eval" / "dataset.py"
AGENT_DATASET = AI / "app" / "eval" / "agent_dataset.py"
METRICS = AI / "app" / "eval" / "metrics.py"
AGENT_METRICS = AI / "app" / "eval" / "agent_metrics.py"
RUN_EVAL = AI / "app" / "eval" / "run_eval.py"
RUN_AGENT_EVAL = AI / "app" / "eval" / "run_agent_eval.py"
RUN_INTERVIEW_EVAL = AI / "app" / "eval" / "run_interview_eval.py"
AGENT_TESTS = TESTS / "test_agent_eval.py"
INTERVIEW_TESTS = TESTS / "test_interview_eval.py"
INTERVIEW_RUNNER_TESTS = TESTS / "test_interview_eval_runner.py"

RAG_METRICS = [
    "recall_at_k",
    "precision_at_k",
    "mrr",
    "ndcg_at_k",
    "hit_at_k",
    "context_relevance",
    "answer_relevance",
    "faithfulness",
]
AGENT_METRIC_NAMES = [
    "tool_recall",
    "tool_precision",
    "tool_f1",
    "forbidden_hit",
    "artifact_rate",
    "grounding_rate",
    "handoff_ok",
    "completed",
]


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def test_the_golden_set_is_the_size_the_doc_states():
    text = read(DATASET)
    cases = len(re.findall(r"(?m)^\s+EvalCase\(", text))
    assert cases >= 10, f"only {cases} EvalCase entries parsed from dataset.py"
    claimed = re.search(r"GOLDEN_SET` \((\d+) bilingual cases", read(DOC))
    assert claimed, "EVALUATION.md no longer states the golden set's size"
    assert int(claimed.group(1)) == cases, (
        f"EVALUATION.md says the golden set holds {claimed.group(1)} cases and "
        f"dataset.py defines {cases} -- a reader comparing a new run against the "
        f"recorded baseline is comparing against a set of a different size"
    )


def test_the_agent_eval_unit_count_is_the_one_the_doc_states():
    tests = len(re.findall(r"(?m)^\s*def test_", read(AGENT_TESTS)))
    assert tests >= 10, f"only {tests} tests parsed from test_agent_eval.py"
    claimed = re.search(r"test_agent_eval\.py` \((\d+) tests\)", read(DOC))
    assert claimed, "EVALUATION.md no longer states how many tests cover the scorer"
    assert int(claimed.group(1)) == tests, (
        f"EVALUATION.md says the scorer is covered by {claimed.group(1)} tests and "
        f"test_agent_eval.py holds {tests}"
    )


def test_the_interview_unit_count_is_the_one_the_doc_states():
    tests = len(re.findall(r"(?m)^\s*def test_", read(INTERVIEW_TESTS)))
    assert tests >= 10, f"only {tests} tests parsed from test_interview_eval.py"
    claimed = re.search(r"tests/test_interview_eval\.py` \((\d+) tests\)", read(DOC))
    assert claimed, "EVALUATION.md no longer states how many tests cover the interview scorer"
    assert int(claimed.group(1)) == tests, (
        f"EVALUATION.md says the interview scorer is covered by {claimed.group(1)} "
        f"tests and test_interview_eval.py holds {tests}"
    )


def test_the_interview_runner_test_count_is_the_one_the_doc_states():
    tests = len(re.findall(r"(?m)^\s*def test_", read(INTERVIEW_RUNNER_TESTS)))
    assert tests >= 5, f"only {tests} tests parsed from test_interview_eval_runner.py"
    claimed = re.search(r"test_interview_eval_runner\.py` \((\d+) tests\)", read(DOC))
    assert claimed, "EVALUATION.md no longer states how many tests cover the interview runner"
    assert int(claimed.group(1)) == tests, (
        f"EVALUATION.md says the interview runner is covered by {claimed.group(1)} "
        f"tests and test_interview_eval_runner.py holds {tests}"
    )


def test_every_flag_the_doc_documents_is_a_flag_a_runner_accepts():
    documented = set()
    for runner in re.findall(
        r"python -m app\.eval\.(run_eval|run_agent_eval)([^`\n]*)", read(DOC)
    ):
        documented |= set(re.findall(r"--[a-z-]+", runner[1]))
    for block in re.findall(r"python -m app\.eval\.\w+[^\n]*", read(DOC)):
        documented |= set(re.findall(r"--[a-z-]+", block))
    accepted = set()
    for runner in (RUN_EVAL, RUN_AGENT_EVAL, RUN_INTERVIEW_EVAL):
        accepted |= set(re.findall(r'add_argument\("(--[a-z-]+)"', read(runner)))
    assert len(documented) >= 5, f"only {sorted(documented)} flags parsed from the doc"
    missing = sorted(documented - accepted)
    assert missing == [], (
        f"EVALUATION.md documents flags no runner accepts: {missing} -- the command it "
        f"prints fails on the first paste"
    )


def test_the_metric_tables_name_the_metrics_the_scorers_return():
    text = read(DOC)
    for name in RAG_METRICS:
        assert f"`{name}`" in text, (
            f"EVALUATION.md no longer names the RAG metric {name}"
        )
        assert re.search(rf'"{name}"', read(METRICS)), (
            f"metrics.py no longer returns {name}, which EVALUATION.md tabulates"
        )
    for name in AGENT_METRIC_NAMES:
        assert f"`{name}`" in text, (
            f"EVALUATION.md no longer names the agent metric {name}"
        )
        assert re.search(rf'"{name}"', read(AGENT_METRICS)), (
            f"agent_metrics.py no longer returns {name}, which EVALUATION.md tabulates"
        )


def test_the_no_ground_truth_skip_the_doc_describes_is_in_the_runner():
    """The one behaviour the doc argues for at length, pinned to the code that does it."""
    runner = read(RUN_EVAL)
    assert "no_ground_truth" in runner, (
        "run_eval.py no longer skips cases with no relevant chunk, which EVALUATION.md "
        "describes as the guard against a query with no ground truth scoring full marks"
    )
    assert re.search(r'"skipped":\s*skipped', runner), (
        "run_eval.py no longer reports the skipped cases it collected"
    )
    assert "no_ground_truth" in read(DOC)
