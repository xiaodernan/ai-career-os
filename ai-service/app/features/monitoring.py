"""Production monitoring (forward Epic 16.1, internal-only).

A deterministic read over the observability rows the product already writes
(``agent_runs``, ``ai_usage_events``) that answers the three questions an operator
asks: *is the agent failing more?*, *what is it costing?*, and *did a metric
regress against the baseline?* -- computed here, never narrated by a model, so the
numbers a dashboard shows and the numbers an alert fires on are the same numbers.

Pure functions over plain dicts, so the whole thing is offline-verifiable:

* ``summarize_runs`` -- success / error rate, latency percentiles, cost and token
  totals for a window of runs.
* ``cost_by`` -- cost and call counts grouped by any key (agent / kind / model).
* ``detect_regressions`` -- compare a current metric set to a baseline and flag the
  metrics that got *worse* past a tolerance, with the direction encoded (an error
  rate rising is a regression; a success rate falling is one too).
* ``health_report`` -- compose the above into one verdict + an alert list.

The regression checker is generic on purpose: the same function compares agent-run
health (16.1) and the eval harnesses' metric dicts, so "the eval regressed" and "the
agent regressed" are the same judgement applied to the same shape.
"""

from __future__ import annotations

import math

# Metrics for which a *rise* is bad. Everything else is "lower is worse".
HIGHER_IS_WORSE = frozenset({
    "errorRate", "failureRate", "p95LatencyMs", "p50LatencyMs", "avgLatencyMs",
    "maxLatencyMs", "costUsd", "totalCostUsd", "avgCostUsd", "totalTokens",
})

DEFAULT_TOLERANCE = 0.2  # 20% change in the bad direction before it is a regression


def _num(value) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _percentile(values: list[float], p: float) -> float | None:
    """Nearest-rank percentile (deterministic, no interpolation ambiguity)."""
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    k = max(0, min(len(vals) - 1, math.ceil(p * len(vals)) - 1))
    return float(vals[k])


def summarize_runs(runs: list[dict]) -> dict:
    """Success/error rate, latency percentiles, cost and token totals for a window.

    A run counts toward the *finished* denominator only once it is terminal
    (completed / failed); a still-running run must not dilute the error rate.
    ``errorRate`` is 0.0 when nothing has finished yet -- not 1.0 and not a
    division error.
    """
    rows = [r for r in (runs or []) if isinstance(r, dict)]
    total = len(rows)
    by_status: dict[str, int] = {}
    latencies: list[float] = []
    total_cost = 0.0
    total_tokens = 0
    for r in rows:
        status = str(r.get("status") or "unknown")
        by_status[status] = by_status.get(status, 0) + 1
        lat = _num(r.get("latency_ms"))
        if lat and lat > 0:
            latencies.append(lat)
        total_cost += _num(r.get("cost_usd")) or 0.0
        total_tokens += int(_num(r.get("input_tokens")) or 0)
        total_tokens += int(_num(r.get("output_tokens")) or 0)

    completed = by_status.get("completed", 0)
    failed = by_status.get("failed", 0)
    finished = completed + failed
    return {
        "totalRuns": total,
        "byStatus": by_status,
        "finished": finished,
        "completed": completed,
        "failed": failed,
        "errorRate": round(failed / finished, 4) if finished else 0.0,
        "successRate": round(completed / finished, 4) if finished else 0.0,
        "latencyMs": {
            "p50": _percentile(latencies, 0.50),
            "p95": _percentile(latencies, 0.95),
            "max": max(latencies) if latencies else None,
        },
        "totalCostUsd": round(total_cost, 6),
        "avgCostUsd": round(total_cost / finished, 6) if finished else 0.0,
        "totalTokens": total_tokens,
    }


def cost_by(events: list[dict], key: str) -> dict:
    """Group usage events by ``key`` (agent / kind / model): calls, cost, tokens."""
    groups: dict[str, dict] = {}
    for e in events or []:
        if not isinstance(e, dict):
            continue
        name = str(e.get(key) or "unknown")
        g = groups.setdefault(name, {"calls": 0, "costUsd": 0.0, "tokens": 0})
        g["calls"] += 1
        g["costUsd"] += _num(e.get("cost_usd")) or 0.0
        g["tokens"] += int(_num(e.get("input_tokens")) or 0)
        g["tokens"] += int(_num(e.get("output_tokens")) or 0)
    for g in groups.values():
        g["costUsd"] = round(g["costUsd"], 6)
    return dict(sorted(groups.items(), key=lambda kv: (-kv[1]["costUsd"], kv[0])))


def detect_regressions(current: dict, baseline: dict, *,
                       higher_is_worse: frozenset[str] = HIGHER_IS_WORSE,
                       tolerance: float = DEFAULT_TOLERANCE) -> list[dict]:
    """Metrics that moved in the *bad* direction past ``tolerance``.

    ``tolerance`` is a relative change against the baseline. A metric absent from
    either side, or whose baseline is zero (no relative change is defined), is
    skipped rather than guessed at. ``severity`` is ``high`` when the bad move is
    more than twice the tolerance, else ``medium``.
    """
    out: list[dict] = []
    for metric, cur in (current or {}).items():
        c = _num(cur)
        b = _num((baseline or {}).get(metric))
        if c is None or b is None or b == 0:
            continue
        rel = (c - b) / abs(b)
        worse = rel > tolerance if metric in higher_is_worse else rel < -tolerance
        if not worse:
            continue
        out.append({
            "metric": metric,
            "baseline": b,
            "current": c,
            "changePct": round(rel * 100, 2),
            "direction": "up" if rel > 0 else "down",
            "severity": "high" if abs(rel) > 2 * tolerance else "medium",
        })
    out.sort(key=lambda r: (-abs(r["changePct"]), r["metric"]))
    return out


def _flatten(summary: dict) -> dict:
    """Pull the comparable scalars out of a ``summarize_runs`` result."""
    return {
        "errorRate": summary.get("errorRate"),
        "successRate": summary.get("successRate"),
        "p50LatencyMs": (summary.get("latencyMs") or {}).get("p50"),
        "p95LatencyMs": (summary.get("latencyMs") or {}).get("p95"),
        "avgCostUsd": summary.get("avgCostUsd"),
        "totalCostUsd": summary.get("totalCostUsd"),
        "totalTokens": summary.get("totalTokens"),
    }


def health_report(runs: list[dict], *, baseline_summary: dict | None = None,
                  usage_events: list[dict] | None = None,
                  current_metrics: dict | None = None,
                  baseline_metrics: dict | None = None,
                  tolerance: float = DEFAULT_TOLERANCE) -> dict:
    """One monitoring snapshot: the summary, the regressions, and a verdict.

    Agent health is compared run-summary to ``baseline_summary``. A caller with an
    arbitrary metric pair (e.g. the eval harness's ``current`` vs ``baseline`` dicts)
    passes ``current_metrics`` / ``baseline_metrics``; those keys are folded into the
    same comparison so "the eval regressed" and "the agent regressed" are judged
    together. The verdict is ``regressed`` if any high-severity regression exists,
    ``warn`` for medium-only or a soft alert, else ``healthy``.
    """
    summary = summarize_runs(runs)
    current = _flatten(summary)
    baseline = _flatten(baseline_summary) if baseline_summary else {}
    if current_metrics:
        current.update({k: _num(v) for k, v in current_metrics.items()
                        if _num(v) is not None})
    if baseline_metrics:
        baseline.update({k: _num(v) for k, v in baseline_metrics.items()
                         if _num(v) is not None})
    regressions = detect_regressions(current, baseline, tolerance=tolerance)

    alerts: list[str] = []
    if summary["errorRate"] and summary["errorRate"] >= 0.25:
        alerts.append(f"Error rate is {round(summary['errorRate'] * 100)}% "
                      f"({summary['failed']}/{summary['finished']} finished runs).")
    for r in regressions:
        if r["severity"] == "high":
            alerts.append(f"{r['metric']} {r['direction']} {abs(r['changePct'])}% "
                          f"vs baseline ({r['baseline']} -> {r['current']}).")

    if any(r["severity"] == "high" for r in regressions):
        verdict = "regressed"
    elif regressions or alerts:
        verdict = "warn"
    else:
        verdict = "healthy"

    out: dict = {
        "summary": summary,
        "regressions": regressions,
        "alerts": alerts,
        "verdict": verdict,
    }
    if usage_events is not None:
        out["costByAgent"] = cost_by(usage_events, "agent")
    return out
