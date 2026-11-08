"""Grade an evaluation report against the checked-in baseline, in the right order.

A real-provider run whose every inference crashed once produced a report with 15
scored cases, zero skips and every metric at 0.1333. Read the aggregate first and
it looks like a catastrophic ranking regression; read the provider signals first
and it is an outage. Another run scored 3 of 15 cases and still printed 1.0 across
the board, because an average over the cases that happened to land says nothing
about the twelve that did not. Both shapes are in the project's history.

So the order here is the product: **errors -> population -> skipped -> shared
metrics**. Nothing is averaged until all four gates have agreed that this run is
a measurement. `app.eval.run_eval.assert_something_was_measured` grades the
empty run and `--require-all-cases` grades the partial one; this module is the
operator's last check before a run is allowed to become a baseline or a verdict.

Baselines are never invented. `--write-baseline` derives one from a real report,
and the checked-in `evals/baseline.json` records the report and date it came from.

Exit codes: 0 verdict is clean, 1 the run regressed or is not a measurement,
2 the CLI/file contract is broken (missing or malformed JSON).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

DEFAULT_BASELINE = "evals/baseline.json"
DEFAULT_TOLERANCE = 0.05
OFFLINE_PROVIDERS = {"mock", ""}
NON_METRIC_KEYS = {"errors", "infra_errors", "agent_errors", "n_scenarios",
                   "forbidden_violations", "avg_steps", "avg_latency_ms",
                   "input_tokens", "output_tokens", "cost_usd"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="verify-eval-baseline",
        description="Grade an eval report against the checked-in baseline.")
    p.add_argument("--report", required=True, help="path to an eval report JSON")
    p.add_argument("--baseline", default=DEFAULT_BASELINE,
                   help=f"path to the baseline JSON (default {DEFAULT_BASELINE})")
    p.add_argument("--tolerance", type=float, default=None,
                   help="allowed absolute delta per metric (default: the baseline's own)")
    p.add_argument("--write-baseline", action="store_true",
                   help="write a new baseline from this report instead of comparing")
    return p.parse_args(argv)


def read_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} holds a JSON {type(data).__name__}, not a report object")
    return data


def population(report: dict) -> int:
    """RAG reports say `n_cases`; agent reports say `n_scenarios`."""
    for key in ("n_cases", "n_scenarios"):
        value = report.get(key)
        if isinstance(value, int):
            return value
    return 0


def preflight(report: dict) -> list[str]:
    """The four reasons a report must not be compared at all.

    The provider-fallback check is the one that catches the historical all-error
    run: a real provider was configured with generation on, yet 13 of 15 cases
    were judged `lexical` (the offline fallback), because most inferences never
    came back. Two happened to succeed, so "every case fell back" would have
    missed it; with `--answer` on a real provider, *any* fallback is a signal.
    """
    problems: list[str] = []
    agg = report.get("aggregate") or {}
    for key in ("errors", "infra_errors", "agent_errors"):
        value = agg.get(key)
        if isinstance(value, (int, float)) and value > 0:
            problems.append(
                f"aggregate.{key}={value}: read errors before any aggregate; "
                "this run lost inferences, it did not lose ranking quality")
    top = report.get("errors")
    if isinstance(top, (int, float)) and top > 0:
        problems.append(f"errors={top}: the report itself recorded failed inferences")

    if population(report) == 0:
        problems.append("0 cases scored -- nothing was measured, so no baseline can be graded")

    skipped = report.get("skipped") or []
    if skipped:
        ids = ", ".join(str(s.get("id", "?")) for s in skipped if isinstance(s, dict))
        problems.append(
            f"{len(skipped)} case(s) skipped ({ids}): a baseline needs the whole golden set; "
            "re-run with --require-all-cases after seeding the corpus")

    config = report.get("config") or {}
    provider = str(config.get("llm_provider") or "")
    cases = [c for c in (report.get("cases") or []) if isinstance(c, dict)]
    judges = [c.get("judge") for c in cases]
    if (provider and provider not in OFFLINE_PROVIDERS
            and bool(config.get("answer")) and judges):
        fell_back = sum(1 for j in judges if j == "lexical")
        if fell_back:
            problems.append(
                f"llm_provider={provider} with generation on, but {fell_back}/{len(judges)} "
                "cases fell back to the 'lexical' judge: some inferences never came back, "
                "so the aggregate describes an outage, not ranking quality")
    return problems


def compare(baseline: dict, report: dict, tolerance: float) -> list[str]:
    """Only metrics both runs measured, and only metrics the baseline names.

    An `--answer` run adds generation metrics a retrieval-only baseline never had;
    inventing zeros for them would read as a failed generator. A missing shared
    set is a contract error, not a pass.
    """
    before = {k: v for k, v in (baseline.get("aggregate") or {}).items()
              if k not in NON_METRIC_KEYS and isinstance(v, (int, float))}
    now = report.get("aggregate") or {}
    shared = sorted(k for k in before if isinstance(now.get(k), (int, float)))
    if not shared:
        return [f"no metric in common with the baseline ({sorted(before)}): "
                "the two runs answer different questions"]
    out = []
    for key in shared:
        delta = now[key] - before[key]
        if abs(delta) > tolerance:
            out.append(f"{key}: {before[key]} -> {now[key]} ({delta:+} "
                       f"exceeds tolerance {tolerance})")
    return out


def write_baseline(path: str, report: dict, source: str) -> dict:
    """Derive a baseline from a real report; never fabricate a score."""
    agg = {k: v for k, v in (report.get("aggregate") or {}).items()
           if k not in NON_METRIC_KEYS and isinstance(v, (int, float))}
    config = report.get("config") or {}
    payload = {
        "schema": 1,
        "source": source,
        # The baseline describes the run it came from, not the day someone typed
        # the command; dating it today would hide how old the reference is.
        "recorded_at": str(report.get("generated_at") or time.strftime("%Y-%m-%d")),
        "provider": f"{config.get('llm_provider', '?')}/{config.get('embedding_provider', '?')}",
        "n_cases": population(report),
        "tolerance": DEFAULT_TOLERANCE,
        "aggregate": agg,
        "note": "Derived from a real report by --write-baseline. Update deliberately, "
                "with the date and the reason in the commit; never edit a number to "
                "make a red run green.",
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = read_json(args.report)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"verify-eval-baseline: cannot read report: {e}", file=sys.stderr)
        return 2

    problems = preflight(report)
    if problems:
        for p in problems:
            print(f"REFUSE {p}", file=sys.stderr)
        return 1

    if args.write_baseline:
        payload = write_baseline(args.baseline, report, args.report)
        print(f"baseline written: {args.baseline} "
              f"({payload['n_cases']} cases, {len(payload['aggregate'])} metrics, "
              f"from {payload['source']})")
        return 0

    try:
        baseline = read_json(args.baseline)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"verify-eval-baseline: cannot read baseline: {e}. "
              "Derive one from a known-good report with --write-baseline.",
              file=sys.stderr)
        return 2
    tolerance = args.tolerance if args.tolerance is not None else float(
        baseline.get("tolerance", DEFAULT_TOLERANCE))
    regressions = compare(baseline, report, tolerance)
    if regressions:
        for r in regressions:
            print(f"REGRESSION {r}", file=sys.stderr)
        return 1
    print(f"OK {report.get('experiment', 'run')}: "
          f"{population(report)} cases, 0 errors, 0 skipped, "
          f"all shared metrics within {tolerance}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
