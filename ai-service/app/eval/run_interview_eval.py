"""Interview evaluation runner (PRD §15, §34).

    python -m app.eval.run_interview_eval [--experiment iv-baseline] [--out evals/reports]

Scores the scripted golden transcripts in `interview_dataset.py` through the pure
scorers in `interview_metrics.py` and writes JSON/Markdown reports to `evals/reports/`.
No DB, no LLM, no provider: what is measured is *shape*, not judgement — whether a
report still separates its dimensions, whether a follow-up still carries a question,
whether a weakness still points at its transcript.

This is the third harness in `app/eval/`, and until now the only one with no way to
be run: RAG has `run_eval.py`, the agent path has `run_agent_eval.py`, and the
interview path — the feature with the product's declared eight-dimension report —
could only be scored from inside pytest, so no human ever saw the discrimination
report the fixtures were built to produce. A harness nobody can run is a harness
nobody reads.

The runner enforces the one invariant the fixture set encodes: the golden set must
*not* all receive the same verdict. Every fixture is a shape an interviewer can
legitimately produce, and the set deliberately contains shapes that must fail (the
flat report, the empty follow-up, the out-of-band ladder, the fabricated weakness).
If they all pass, the scorer became a rubber stamp; if they all fail, the scorer
broke. Both refuse to exit 0, the same contract `run_agent_eval.assert_something
_was_measured` applies to a run that measured nothing.
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path

from app.eval.interview_dataset import load_interviews
from app.eval.interview_metrics import (
    aggregate,
    score_interview,
)

# Why a fixture is expected to fail, keyed by the metric that vetoes it. A reader
# who sees `flat: not passed` needs to know it is discrimination and not, say,
# completeness — the same reason the agent runner lists per-scenario failure reasons.
_VETO_BY_METRIC = {
    "discrimination": "eight identical dimension scores — the evaluator declined to evaluate",
    "follow_up_discipline": "a followup move carried no question",
    "difficulty_discipline": "the adaptive ladder left the [0.1, 0.95] clamp band",
    "grounding": "a reported weakness named nothing the candidate ever said",
}

# The blocking metrics that veto `passed` (see `score_interview`); `adapted` and
# the diagnostic scalars are reported but do not veto.
_BLOCKING = (
    "discrimination", "follow_up_discipline", "difficulty_discipline", "grounding",
)


def score_set(transcripts) -> list[dict]:
    """One row per transcript, carrying the fixture's id for the report."""
    rows = []
    for t in transcripts:
        row = score_interview(t)
        row["id"] = t.id or "(unnamed)"
        rows.append(row)
    return rows


def _why_failing(row: dict) -> list[str]:
    reasons = []
    for metric in _BLOCKING:
        if row.get(metric) == 0.0 or (
                metric != "discrimination" and metric != "grounding"
                and row.get(metric, 1.0) < 1.0):
            reasons.append(f"{metric}: {_VETO_BY_METRIC[metric]}")
    if not reasons and row.get("report_completeness", 1.0) < 1.0:
        reasons.append("report_completeness: a §15 section was left empty")
    return reasons or ["unknown (no blocking metric scored 0 — check the fixture)"]


def _markdown(report: dict) -> str:
    agg = report["aggregate"]
    lines = [
        f"# Interview evaluation — {report['experiment']}", "",
        f"- fixtures: {report['n_interviews']} scripted transcripts",
        "- scorer: `app/eval/interview_metrics.py` (pure functions, no provider)",
        f"- generated: {report['generated_at']}", "",
        "## Aggregate", "",
        "| metric | value |", "|---|---|",
    ]
    lines += [f"| {k} | {v} |" for k, v in agg.items()]
    lines += ["", "## What these numbers mean", "",
              "- The fixture set is *scripted shapes*, not live model output. A pass "
              "here means the harness still discriminates the shapes it was built "
              "for — not that any particular interview was good.",
              "- `discrimination` measures spread, not quality: a bad candidate also "
              "spreads across the eight dimensions. `overall` separates strong from "
              "weak, which is why the golden set contains both.",
              "- `grounding` counts only *distinctive* tokens (CJK-aware bigrams, "
              "ASCII ≥5 chars), so a weakness containing \"the\" and \"you\" cannot "
              "match every transcript ever recorded.", ""]
    lines += ["## Cases", "",
              "| id | discrimination | follow_up | difficulty | completeness "
              "| grounding | adapted | passed |", "|---|---|---|---|---|---|---|---|"]
    for r in report["cases"]:
        lines.append(
            f"| {r['id']} | {r['discrimination']} | {r['follow_up_discipline']} "
            f"| {r['difficulty_discipline']} | {r['report_completeness']} "
            f"| {r['grounding']} | {'yes' if r['adapted'] else 'no'} "
            f"| {'yes' if r['passed'] else 'no'} |")
    fails = [r for r in report["cases"] if not r["passed"]]
    if fails:
        lines += ["", "## Why the failing fixtures fail", ""]
        for r in fails:
            lines.append(f"- **{r['id']}** — " + "; ".join(_why_failing(r)))
    return "\n".join(lines) + "\n"


def run(args: argparse.Namespace) -> dict:
    transcripts = load_interviews()
    rows = score_set(transcripts)
    report = {
        "experiment": args.experiment,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "config": {"scorer": "app.eval.interview_metrics", "provider": None},
        "n_interviews": len(rows),
        "aggregate": aggregate(rows),
        "cases": rows,
    }
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    jpath = out_dir / f"{stamp}_{args.experiment}.json"
    jpath.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    mpath = out_dir / f"{stamp}_{args.experiment}.md"
    mpath.write_text(_markdown(report), encoding="utf-8")
    report["_files"] = [str(jpath), str(mpath)]
    return report


def assert_something_was_measured(report: dict) -> None:
    """Refuse to let a run that measured nothing — or measured the same thing
    everywhere — pass as a clean one.

    The golden set is built so the harness *must* discriminate: `strong`, `weak`
    and `zh_honest` are shapes that should pass, `flat` / `missing_question` /
    `out_of_band` / `fabricated` / `zh_fabricated` are shapes that must fail. Two
    degenerate outcomes hide behind a green-looking summary:

    1. **every fixture got the same verdict** — the scorer became a rubber stamp
       (all pass) or broke entirely (all fail). `aggregate["pass_rate"]` would be
       1.0 or 0.0, and either reads as a result when it means the harness can no
       longer tell the shapes apart. This is the interview-path equivalent of
       `run_agent_eval`'s all-scenarios-errored guard: the report is *full* of
       numbers computed off a degenerate set.
    2. **the set is empty** — `load_interviews()` returned nothing, so
       `n_interviews == 0` and the aggregate is `{}`. "0 failures" reads as good
       when it means nothing was asked.
    """
    n = report.get("n_interviews", 0)
    if not n:
        raise SystemExit(
            "\n0 fixtures scored — nothing was measured.\n"
            "  `load_interviews()` returned an empty set. The golden set lives in\n"
            "  `app/eval/interview_dataset.py`; a run over nothing is not a result.\n"
        )
    verdicts = {bool(r.get("passed")) for r in report.get("cases", [])}
    if len(verdicts) < 2:
        raise SystemExit(
            f"\nall {n} fixtures received the same verdict — the harness cannot tell "
            f"them apart.\n"
            "  The golden set deliberately contains shapes that must fail (the flat\n"
            "  report, the empty follow-up, the out-of-band ladder, the fabricated\n"
            "  weakness). If they all pass, the scorer became a rubber stamp; if they\n"
            "  all fail, the scorer broke. Either way this run measured nothing a\n"
            "  reader can act on. Check `dimension_discrimination`'s spread threshold\n"
            "  and the blocking metrics in `score_interview` before re-running.\n"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--experiment", default=f"iv-{uuid.uuid4().hex[:6]}")
    p.add_argument("--out", default="evals/reports")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    report = run(args)
    assert_something_was_measured(report)
    print(json.dumps({"experiment": report["experiment"],
                      "n_interviews": report["n_interviews"],
                      "aggregate": report["aggregate"],
                      "files": report["_files"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
