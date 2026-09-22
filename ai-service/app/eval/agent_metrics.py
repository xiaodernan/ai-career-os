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


@dataclass
class RunObservation:
    """What one agent run actually did (collected by the runner)."""

    tools_used: list[str] = field(default_factory=list)
    artifact_types: list[str] = field(default_factory=list)
    handoffs: list[str] = field(default_factory=list)
    answer: str = ""
    steps: int = 0
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    error: str | None = None


def _ratio(hit: int, total: int) -> float:
    """1.0 when there is nothing to miss (vacuously satisfied)."""
    return 1.0 if total == 0 else hit / total


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
        "completed": completed,
        "answer_preview": (obs.answer or "")[:400],
    }


SCALAR_METRICS = [
    "tool_recall", "tool_precision", "tool_f1", "artifact_rate",
    "grounding_rate", "completed",
]


def aggregate(rows: list[dict]) -> dict:
    """Mean of every scalar metric + totals. `completed` is averaged as a rate."""
    if not rows:
        return {}
    out: dict = {}
    for key in SCALAR_METRICS:
        out[key] = round(sum(1.0 if r[key] is True else (0.0 if r[key] is False
                                                        else r[key]) for r in rows)
                         / len(rows), 4)
    out["n_scenarios"] = len(rows)
    out["forbidden_violations"] = sum(1 for r in rows if r["forbidden_hit"])
    out["errors"] = sum(1 for r in rows if r["error"])
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
