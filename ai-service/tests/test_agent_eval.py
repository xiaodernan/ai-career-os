"""Agent evaluation scoring + dataset integrity (no DB, no LLM)."""

from app.agents.tools import TOOL_INDEX
from app.eval.agent_dataset import AGENT_SCENARIOS
from app.eval.agent_metrics import (
    AgentScenario,
    RunObservation,
    aggregate,
    aggregate_by_tag,
    score_run,
)


def _obs(**kw) -> RunObservation:
    return RunObservation(**kw)


def test_perfect_run_scores_completed():
    sc = AgentScenario(id="s", message="find jobs", expected_tools=["search_jobs"],
                       expected_artifacts=["job_list"], must_mention=["Agent"])
    obs = _obs(tools_used=["search_jobs"], artifact_types=["job_list"],
               answer="Found 3 Agent roles for you.", steps=2)
    row = score_run(sc, obs)
    assert row["tool_recall"] == 1.0 and row["tool_precision"] == 1.0
    assert row["artifact_rate"] == 1.0 and row["grounding_rate"] == 1.0
    assert row["completed"] is True


def test_missing_tool_and_artifact_fails_with_metrics_kept():
    sc = AgentScenario(id="s", message="q", expected_tools=["calculate_match", "get_job"],
                       expected_artifacts=["match"], must_mention=["87"])
    obs = _obs(tools_used=["get_job"], artifact_types=[],
               answer="This job looks like a good fit.")
    row = score_run(sc, obs)
    assert row["tool_recall"] == 0.5
    assert row["artifact_rate"] == 0.0
    assert row["grounding_rate"] == 0.0
    assert row["completed"] is False
    # a partially-correct run stays diagnosable
    assert row["tool_precision"] == 1.0


def test_forbidden_tool_is_a_hard_failure_even_when_otherwise_perfect():
    sc = AgentScenario(id="s", message="hi", expected_tools=[],
                       forbidden_tools=["save_job"])
    obs = _obs(tools_used=["save_job"], answer="Hello!")
    row = score_run(sc, obs)
    assert row["forbidden_hit"] == ["save_job"]
    assert row["completed"] is False


def test_no_tool_call_smalltalk_is_vacuously_perfect():
    """A run that correctly calls nothing must not be punished for precision."""
    sc = AgentScenario(id="s", message="hi", expected_tools=[],
                       forbidden_tools=["save_job"])
    row = score_run(sc, _obs(answer="I can help with jobs, resumes and interviews."))
    assert row["tool_precision"] == 1.0
    assert row["tool_recall"] == 1.0
    assert row["completed"] is True


def test_handoff_expectation_is_enforced():
    sc = AgentScenario(id="s", message="q", expected_tools=[],
                       expect_handoff_to="job_research")
    assert score_run(sc, _obs(answer="ok"))["completed"] is False
    assert score_run(sc, _obs(answer="ok", handoffs=["job_research"]))["completed"] is True


def test_error_never_completes_but_is_reported():
    sc = AgentScenario(id="s", message="q", expected_tools=[])
    row = score_run(sc, _obs(answer="", error="RuntimeError: db down"))
    assert row["completed"] is False
    assert "db down" in row["error"]


def test_tool_f1_balances_precision_and_recall():
    sc = AgentScenario(id="s", message="q", expected_tools=["search_jobs", "get_job"])
    obs = _obs(tools_used=["search_jobs", "compile_report"], answer="x")
    row = score_run(sc, obs)
    # recall 1/2, precision 1/2 -> f1 0.5
    assert row["tool_recall"] == 0.5 and row["tool_precision"] == 0.5
    assert row["tool_f1"] == 0.5


def test_aggregate_means_and_totals():
    rows = [
        {"tool_recall": 1.0, "tool_precision": 1.0, "tool_f1": 1.0, "artifact_rate": 1.0,
         "grounding_rate": 1.0, "completed": True, "forbidden_hit": [], "error": None,
         "steps": 2, "latency_ms": 100, "input_tokens": 10, "output_tokens": 5,
         "cost_usd": 0.01, "tags": ["a"]},
        {"tool_recall": 0.0, "tool_precision": 0.5, "tool_f1": 0.0, "artifact_rate": 0.0,
         "grounding_rate": 0.0, "completed": False, "forbidden_hit": ["save_job"],
         "error": "boom", "steps": 4, "latency_ms": 300, "input_tokens": 20,
         "output_tokens": 15, "cost_usd": 0.02, "tags": ["a", "b"]},
    ]
    agg = aggregate(rows)
    assert agg["completed"] == 0.5
    assert agg["tool_recall"] == 0.5
    assert agg["forbidden_violations"] == 1
    assert agg["errors"] == 1
    assert agg["avg_steps"] == 3.0
    assert agg["input_tokens"] == 30 and agg["output_tokens"] == 20
    assert agg["cost_usd"] == 0.03
    by_tag = aggregate_by_tag(rows)
    assert set(by_tag) == {"a", "b"}
    assert by_tag["b"]["n_scenarios"] == 1 and by_tag["a"]["n_scenarios"] == 2


def test_aggregate_empty_is_safe():
    assert aggregate([]) == {}


# --------------------------------- dataset integrity ---------------------------------

def test_scenarios_have_unique_ids():
    ids = [s.id for s in AGENT_SCENARIOS]
    assert len(ids) == len(set(ids))


def test_every_referenced_tool_exists_in_the_registry():
    """Ground truth must not drift from the real tool surface (PRD §18)."""
    for s in AGENT_SCENARIOS:
        for name in s.expected_tools + s.forbidden_tools:
            assert name in TOOL_INDEX, f"{s.id} references unknown tool {name}"


def test_safety_scenarios_have_no_expected_tools():
    """Injection / small-talk scenarios assert *restraint*, not tool usage."""
    for s in AGENT_SCENARIOS:
        if "safety" in s.tags:
            assert s.expected_tools == []
            assert s.forbidden_tools, f"{s.id} must forbid something"


def test_job_scoped_scenarios_declare_the_dependency():
    """A scenario reading {job_id} must set needs_job so the runner can skip it."""
    for s in AGENT_SCENARIOS:
        if "{job_id}" in s.message:
            assert s.needs_job, f"{s.id} uses {{job_id}} without needs_job"
        if s.needs_job:
            # A job-anchored scenario is either tool-driven or gives the work to a
            # subagent — but it must never be a no-op turn.
            assert s.expected_tools or s.expect_handoff_to, \
                f"{s.id} needs_job but has neither expected tools nor a handoff"


def test_every_scenario_has_a_tag_and_a_note():
    for s in AGENT_SCENARIOS:
        assert s.tags, f"{s.id} has no tags"
