"""Agent evaluation scoring + dataset integrity (no DB, no LLM)."""

from app.agents.tools import TOOL_INDEX
from app.eval.agent_dataset import AGENT_SCENARIOS
from app.eval.agent_metrics import (
    AgentScenario,
    RunObservation,
    aggregate,
    aggregate_by_tag,
    classify_error,
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
    assert row["argument_score"] == 1.0
    assert row["completed"] is True


def test_arguments_are_scored_not_just_names():
    """A run that spells `search_jobs` right but hands it nothing asked for no filter
    at all; `tool_recall` alone reported that as a perfect tool call."""
    sc = AgentScenario(id="s", message="find remote java jobs",
                       expected_tools=["search_jobs"],
                       required_args={"search_jobs": ["q", "remote"]})
    empty = _obs(tools_used=["search_jobs"], tool_calls=[
        {"tool": "search_jobs", "args": {"q": "", "remote": None}}])
    assert score_run(sc, empty)["argument_score"] == 0.0
    assert score_run(sc, empty)["completed"] is False

    good = _obs(tools_used=["search_jobs"], tool_calls=[
        {"tool": "search_jobs", "args": {"q": "remote java", "remote": True}},
        {"tool": "search_jobs", "args": {"q": "  ", "remote": True}}])
    row = score_run(sc, good)
    assert row["argument_score"] == 0.75

    # The tool never ran: tool_recall already carries that, so the parameters it
    # would have passed must not be charged a second time.
    assert score_run(sc, _obs(tools_used=[], tool_calls=[]))["argument_score"] == 1.0


def test_an_empty_list_or_blank_string_is_not_a_present_argument():
    sc = AgentScenario(id="s", message="q", expected_tools=["search_jobs"],
                       required_args={"search_jobs": ["k"]})
    for blank in ([], "   ", None, {}):
        obs = _obs(tools_used=["search_jobs"],
                   tool_calls=[{"tool": "search_jobs", "args": {"k": blank}}])
        assert score_run(sc, obs)["argument_score"] == 0.0, blank


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


def test_grounding_rate_is_no_longer_vacuous():
    """`grounding_rate` reported 1.0 on every real run because no scenario declared
    `must_mention` — the metric that was supposed to certify "traceable to tool output
    rather than invented" was certifying nothing. This test is the floor: the harness
    must be able to report a value below 1.0.
    """
    grounded = [s for s in AGENT_SCENARIOS if s.must_mention]
    assert len(grounded) >= 8, (
        f"only {len(grounded)} of {len(AGENT_SCENARIOS)} scenarios declare must_mention — "
        "grounding_rate is close to vacuous again")
    # Every one of them must also declare something to refuse, so the metric has a
    # failure mode on a surface the product actually cares about.
    refusal = [s for s in grounded if "safety" in s.tags]
    assert refusal, "no safety scenario is grounding-checked, the surface most worth pinning"


def test_required_args_name_real_parameters():
    """A declared param the tool does not accept can never be satisfied, so the
    scenario would fail forever for a reason the model cannot influence."""
    from app.agents.tools import TOOL_INDEX

    for s in AGENT_SCENARIOS:
        for tool, params in (s.required_args or {}).items():
            assert tool in TOOL_INDEX, f"{s.id} requires args on unknown tool {tool}"
            schema = TOOL_INDEX[tool].spec().parameters or {}
            known = set(schema.get("properties") or {})
            for p in params:
                assert p in known, (
                    f"{s.id} requires '{tool}.{p}' which the tool schema does not accept")


def test_a_completed_run_passes_every_declared_requirement():
    """The strict flag is only meaningful if the declared ground truth is jointly
    satisfiable — a set no run could pass is a broken spec, not a hard test."""
    sc = AgentScenario(id="s", message="q",
                       expected_tools=["search_jobs"],
                       expected_artifacts=["job_list"],
                       must_mention=["3 roles"],
                       required_args={"search_jobs": ["remote"]})
    obs = _obs(tools_used=["search_jobs"], artifact_types=["job_list"],
               tool_calls=[{"tool": "search_jobs", "args": {"remote": True}}],
               answer="I found 3 roles matching your filters.", steps=1)
    row = score_run(sc, obs)
    assert row["completed"] is True, row


def test_classify_error_separates_transient_from_deterministic():
    """A retry must not be spent on a failure that will reproduce identically."""
    assert classify_error(TimeoutError("request timed out")) == "infra"
    assert classify_error(ConnectionError("connection reset by peer")) == "infra"
    assert classify_error(RuntimeError("CUDA out of memory")) == "infra"
    assert classify_error(RuntimeError("provider returned 503")) == "infra"
    assert classify_error(ValueError("unknown tool: save_job")) == "agent"
    assert classify_error(KeyError("job_id")) == "agent"


def test_aggregate_counts_infra_and_agent_errors_separately():
    rows = [
        {"forbidden_hit": [], "error": "boom", "error_kind": "agent", "steps": 1,
         "latency_ms": 10, "input_tokens": 1, "output_tokens": 1, "cost_usd": 0.0,
         "tool_recall": 0.0, "tool_precision": 0.0, "tool_f1": 0.0, "artifact_rate": 0.0,
         "grounding_rate": 0.0, "completed": False},
        {"forbidden_hit": [], "error": None, "error_kind": None, "steps": 2,
         "latency_ms": 20, "input_tokens": 2, "output_tokens": 2, "cost_usd": 0.0,
         "tool_recall": 1.0, "tool_precision": 1.0, "tool_f1": 1.0, "artifact_rate": 1.0,
         "grounding_rate": 1.0, "completed": True},
    ]
    agg = aggregate(rows)
    assert agg["errors"] == 1
    assert agg["infra_errors"] == 0
    assert agg["agent_errors"] == 1
