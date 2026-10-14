"""Tests for the Epic 16.1 monitoring engine (offline, deterministic)."""

from app.features import monitoring as M


def _run(status, **kw):
    d = {"status": status}
    d.update(kw)
    return d


# ---------------- summarize_runs ----------------


def test_summarize_empty():
    s = M.summarize_runs([])
    assert s["totalRuns"] == 0 and s["finished"] == 0
    assert s["errorRate"] == 0.0 and s["successRate"] == 0.0
    assert s["latencyMs"] == {"p50": None, "p95": None, "max": None}
    assert s["totalCostUsd"] == 0.0


def test_summarize_error_rate_and_denominator():
    runs = [_run("completed"), _run("completed"), _run("failed"), _run("running")]
    s = M.summarize_runs(runs)
    assert s["totalRuns"] == 4
    assert s["finished"] == 3          # running excluded from the denominator
    assert s["errorRate"] == round(1 / 3, 4)
    assert s["successRate"] == round(2 / 3, 4)
    assert s["byStatus"] == {"completed": 2, "failed": 1, "running": 1}


def test_summarize_latency_percentiles_and_cost():
    runs = [_run("completed", latency_ms=v, cost_usd=0.01, input_tokens=100,
                 output_tokens=50) for v in (100, 200, 300, 400, 500)]
    s = M.summarize_runs(runs)
    assert s["latencyMs"]["max"] == 500
    assert s["latencyMs"]["p50"] == 300     # nearest-rank
    assert s["latencyMs"]["p95"] == 500
    assert s["totalCostUsd"] == round(0.05, 6)
    assert s["totalTokens"] == 5 * 150


def test_summarize_ignores_non_dict_and_bad_numbers():
    s = M.summarize_runs([_run("completed", latency_ms="nope"), None, "x"])
    assert s["totalRuns"] == 1 and s["finished"] == 1


# ---------------- cost_by ----------------


def test_cost_by_groups_and_sorts():
    events = [
        {"agent": "career", "cost_usd": 0.05, "input_tokens": 10, "output_tokens": 5},
        {"agent": "career", "cost_usd": 0.02},
        {"agent": "resume", "cost_usd": 0.10},
    ]
    out = M.cost_by(events, "agent")
    assert list(out) == ["resume", "career"]           # cost desc
    assert out["career"]["calls"] == 2
    assert out["career"]["costUsd"] == round(0.07, 6)
    assert out["career"]["tokens"] == 15
    assert out["resume"]["calls"] == 1


def test_cost_by_missing_key_is_unknown():
    out = M.cost_by([{"cost_usd": 1}], "kind")
    assert "unknown" in out


# ---------------- detect_regressions ----------------


def test_detect_flags_error_rate_rising():
    regs = M.detect_regressions({"errorRate": 0.30}, {"errorRate": 0.10})
    assert len(regs) == 1
    assert regs[0]["metric"] == "errorRate" and regs[0]["direction"] == "up"
    assert regs[0]["changePct"] == 200.0 and regs[0]["severity"] == "high"


def test_detect_flags_success_rate_falling():
    regs = M.detect_regressions({"successRate": 0.6}, {"successRate": 0.9})
    assert len(regs) == 1 and regs[0]["direction"] == "down"


def test_detect_ignores_improvement_and_small_change():
    assert M.detect_regressions({"errorRate": 0.05}, {"errorRate": 0.10}) == []
    assert M.detect_regressions({"errorRate": 0.11}, {"errorRate": 0.10}) == []  # +10% < 20%


def test_detect_skips_zero_or_missing_baseline():
    assert M.detect_regressions({"errorRate": 0.5}, {"errorRate": 0}) == []
    assert M.detect_regressions({"unknownMetric": 9}, {}) == []


# ---------------- health_report ----------------


def test_health_report_healthy():
    runs = [_run("completed", latency_ms=100)] * 10
    rep = M.health_report(runs)
    assert rep["verdict"] == "healthy" and rep["regressions"] == []
    assert "costByAgent" not in rep


def test_health_report_regressed_and_alerts():
    runs = [_run("failed")] * 3 + [_run("completed")]
    # a nonzero baseline error rate (1%) is required for the relative check to fire
    baseline = M.summarize_runs([_run("completed")] * 99 + [_run("failed")])
    rep = M.health_report(runs, baseline_summary=baseline)
    assert rep["verdict"] == "regressed"
    assert any("errorRate" in a for a in rep["alerts"])
    assert any("Error rate" in a for a in rep["alerts"])


def test_health_report_folds_eval_metrics_and_cost():
    rep = M.health_report(
        [_run("completed")], usage_events=[{"agent": "career", "cost_usd": 0.02}],
        current_metrics={"tool_recall": 0.30}, baseline_metrics={"tool_recall": 0.61})
    assert any(r["metric"] == "tool_recall" for r in rep["regressions"])
    assert rep["costByAgent"]["career"]["calls"] == 1
    assert rep["verdict"] == "regressed"  # 0.61 -> 0.30 is a high-severity drop
