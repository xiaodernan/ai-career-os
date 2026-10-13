"""Agent evaluation scoring (PRD §34 "Agent Evaluation").

Pure functions — no DB, no LLM — so the math is unit-testable and the harness can
be trusted before it is pointed at a real provider.

What is measured per scenario:
  * **tool selection** — precision / recall / F1 of the tools the agent actually
    called against the tools a correct run should call;
  * **forbidden tools** — side-effecting tools that must NOT fire (e.g. saving a
    job during small talk) — any hit is a hard failure;
  * **artifact completion** — did the run produce the structured artifacts the
    UI needs (match card, job list, tailored resume, interview session…);
  * **grounding** — did the answer actually mention the required facts, i.e. is
    it traceable to tool output rather than invented;
  * **handoff** — when a specialty is expected, did the orchestrator delegate to
    the right subagent;
  * plus cost/latency telemetry (steps, tokens, ms, USD).

`completed` is the strict all-criteria-passed flag; the individual rates are kept
so a partially-correct run is still diagnosable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentScenario:
    id: str
    message: str
    expected_tools: list[str] = field(default_factory=list)
    forbidden_tools: list[str] = field(default_factory=list)
    expected_artifacts: list[str] = field(default_factory=list)
    must_mention: list[str] = field(default_factory=list)
    expect_handoff_to: str | None = None
    needs_job: bool = False
    context: dict | None = None
    history: list[dict] | None = None
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    # Per-tool argument requirements: {tool_name: [param names that must be present and
    # non-empty}. Scoring names alone cannot tell a sane `search_jobs` from one whose
    # filter payload is empty or nonsense.
    required_args: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class RunObservation:
    """What one agent run actually did (collected by the runner)."""

    tools_used: list[str] = field(default_factory=list)
    # {tool, args} pairs, so argument requirements can be scored, not just names.
    tool_calls: list[dict] = field(default_factory=list)
    artifact_types: list[str] = field(default_factory=list)
    answer: str = ""
    handoffs: list[str] = field(default_factory=list)
    steps: int = 0
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    error: str | None = None
    error_kind: str | None = None


_INFRA_MARKERS = (
    "timeout", "timed out", "connection", "connect", "cuda", "out of memory",
    "oom", "rate limit", "429", "500", "502", "503", "504", "unavailable",
    "temporarily", "overloaded", "insufficient", "remote end", "reset by peer",
)


def classify_error(error: BaseException) -> str:
    """`infra` when a retry could plausibly help, `agent` when it cannot.

    The distinction matters because the two failures need opposite responses. An
    infrastructure failure (a dropped connection, a CUDA OOM, a provider 5xx) is
    transient, so the scenario deserves a second attempt before it counts against the
    agent. An agent failure is deterministic -- the same prompt and tools fail the
    same way -- so retrying it only burns budget and double-counts the defect.
    """
    text = f"{type(error).__name__}: {error}".lower()
    return "infra" if any(m in text for m in _INFRA_MARKERS) else "agent"


def _ratio(hit: int, total: int) -> float:
    """1.0 when there is nothing to miss (vacuously satisfied)."""
    return 1.0 if total == 0 else hit / total


def _present(value: Any) -> bool:
    """A named parameter was actually handed a usable value.

    Missing, empty, blank and null all count as absent: a `search_jobs` call with
    `{"skills": []}` or `{"keyword": "  "}` asked for nothing, and the tool will answer
    "no results" -- a run that looks successful because the model spelled the name
    right is exactly what this rejects.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def argument_score(scenario: AgentScenario, tool_calls: list[dict]) -> float:
    """Share of required (tool, param) pairs that carried a usable value.

    Names alone cannot tell `search_jobs` with a real filter from the same call with
    an empty one, so a scenario may declare `required_args` per tool. Only calls that
    actually fired are judged: a scenario whose tool never ran is already punished by
    tool_recall, and counting its missing parameters here would charge the same defect
    twice.
    """
    wanted = scenario.required_args
    if not wanted:
        return 1.0
    by_tool: dict[str, list[dict]] = {}
    for call in tool_calls or []:
        by_tool.setdefault(call.get("tool") or "", []).append(call.get("args") or {})
    total = hit = 0
    for tool, params in wanted.items():
        calls = by_tool.get(tool, [])
        if not calls:
            continue
        for args in calls:
            for p in params:
                total += 1
                if _present(args.get(p)):
                    hit += 1
    return _ratio(hit, total)


def score_run(scenario: AgentScenario, obs: RunObservation) -> dict:
    """Score one scenario/run pair. Always returns every metric key."""
    expected = set(scenario.expected_tools)
    used = set(obs.tools_used)
    matched = expected & used

    tool_recall = _ratio(len(matched), len(expected))
    # Precision is undefined with no calls: a run that correctly calls nothing
    # (small talk) is perfect; a run that calls nothing when tools were required
    # is already punished by recall, so precision stays 1.0 to keep it honest.
    tool_precision = _ratio(len(matched), len(used)) if used else 1.0
    tool_f1 = (0.0 if (tool_precision + tool_recall) == 0
               else 2 * tool_precision * tool_recall / (tool_precision + tool_recall))

    forbidden_hit = sorted(set(scenario.forbidden_tools) & used)
    arg_score = argument_score(scenario, obs.tool_calls)

    art_expected = set(scenario.expected_artifacts)
    art_got = art_expected & set(obs.artifact_types)
    artifact_rate = _ratio(len(art_got), len(art_expected))

    lowered = (obs.answer or "").lower()
    mentions = [m for m in scenario.must_mention if m.lower() in lowered]
    grounding_rate = _ratio(len(mentions), len(scenario.must_mention))

    handoff_ok = (scenario.expect_handoff_to is None
                  or scenario.expect_handoff_to in obs.handoffs)

    answered = bool((obs.answer or "").strip())
    completed = bool(
        obs.error is None
        and answered
        and tool_recall >= 1.0
        and not forbidden_hit
        and artifact_rate >= 1.0
        and grounding_rate >= 1.0
        and arg_score >= 1.0
        and handoff_ok
    )

    return {
        "scenario": scenario.id,
        "message": scenario.message,
        "tags": list(scenario.tags),
        "expected_tools": sorted(expected),
        "tools_used": obs.tools_used,
        "tool_recall": round(tool_recall, 4),
        "tool_precision": round(tool_precision, 4),
        "tool_f1": round(tool_f1, 4),
        "argument_score": round(arg_score, 4),
        "forbidden_hit": forbidden_hit,
        "expected_artifacts": sorted(art_expected),
        "artifacts_seen": sorted(set(obs.artifact_types)),
        "artifact_rate": round(artifact_rate, 4),
        "must_mention": list(scenario.must_mention),
        "mentioned": mentions,
        "grounding_rate": round(grounding_rate, 4),
        "expected_handoff_to": scenario.expect_handoff_to,
        "handoffs": obs.handoffs,
        "handoff_ok": handoff_ok,
        "steps": obs.steps,
        "latency_ms": obs.latency_ms,
        "input_tokens": obs.input_tokens,
        "output_tokens": obs.output_tokens,
        "cost_usd": round(obs.cost_usd, 6),
        "error": obs.error,
        "error_kind": obs.error_kind,
        "completed": completed,
        "answer_preview": (obs.answer or "")[:400],
    }


SCALAR_METRICS = [
    "tool_recall", "tool_precision", "tool_f1", "artifact_rate",
    "grounding_rate", "completed", "argument_score",
]


def aggregate(rows: list[dict]) -> dict:
    """Mean of every scalar metric + totals. `completed` is averaged as a rate."""
    if not rows:
        return {}
    out: dict = {}
    for key in SCALAR_METRICS:
        # `.get` with a neutral value: a row written before this metric existed has no
        # opinion on it, and an aggregate is allowed to outlive one of its columns.
        out[key] = round(sum(1.0 if r.get(key) is True else (0.0 if r.get(key) is False
                                                             else r.get(key, 1.0))
                             for r in rows)
                          / len(rows), 4)
    out["n_scenarios"] = len(rows)
    out["forbidden_violations"] = sum(1 for r in rows if r["forbidden_hit"])
    out["errors"] = sum(1 for r in rows if r["error"])
    out["infra_errors"] = sum(1 for r in rows if r.get("error_kind") == "infra")
    out["agent_errors"] = sum(1 for r in rows if r.get("error_kind") == "agent")
    out["avg_steps"] = round(sum(r["steps"] for r in rows) / len(rows), 2)
    out["avg_latency_ms"] = round(sum(r["latency_ms"] for r in rows) / len(rows), 1)
    out["input_tokens"] = sum(r["input_tokens"] for r in rows)
    out["output_tokens"] = sum(r["output_tokens"] for r in rows)
    out["cost_usd"] = round(sum(r["cost_usd"] for r in rows), 6)
    return out


def aggregate_by_tag(rows: list[dict]) -> dict[str, dict]:
    """Per-tag rollup so weak areas (e.g. 'tracking') stand out."""
    buckets: dict[str, list[dict]] = {}
    for r in rows:
        for tag in r["tags"] or ["untagged"]:
            buckets.setdefault(tag, []).append(r)
    return {tag: aggregate(bucket) for tag, bucket in sorted(buckets.items())}
