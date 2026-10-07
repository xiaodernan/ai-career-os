"""Agent evaluation runner (PRD §34 "Agent Evaluation").

    python -m app.eval.run_agent_eval --user-id <uuid> [--tags zh,match] [--limit 5]

Runs the scripted scenarios through the **real** Career Orchestrator against
whatever LLM provider is configured, then scores tool selection, artifact
completion, grounding, handoff correctness and side-effect safety, and writes
JSON/Markdown reports to `evals/reports/`.

Honest note on offline mode: with `LLM_PROVIDER=mock` the provider only knows a
three-keyword heuristic (`mock.py: TOOL_HINTS`), so most scenarios will score low
on tool selection. That is the *correct* result and it proves the harness
discriminates — it is not a pass/fail gate. Point it at a real provider to
measure model quality (same contract as the RAG eval's hash embeddings).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from pathlib import Path

from app.core import db
from app.core.config import get_settings
from app.db import observability
from app.eval.agent_dataset import AGENT_SCENARIOS, load_scenarios
from app.eval.agent_metrics import (
    AgentScenario,
    RunObservation,
    aggregate,
    aggregate_by_tag,
    score_run,
)

RUN_TRIGGER = "agent_eval"


def _fill(template: str, subs: dict) -> str:
    """Replace known `{key}` placeholders, leaving unknown ones untouched."""
    out = template
    for key, value in subs.items():
        out = out.replace("{" + key + "}", str(value))
    return out


async def _pick_job() -> dict | None:
    """A stable, evidence-rich open job to anchor job-scoped scenarios."""
    row = await db.fetchrow(
        """SELECT j.id, j.title, c.name AS company
           FROM jobs j JOIN companies c ON c.id = j.company_id
           WHERE j.status = 'open'
           ORDER BY cardinality(j.skills) DESC, j.posted_at DESC
           LIMIT 1""")
    if not row:
        return None
    return {"job_id": str(row["id"]), "job_title": row["title"],
            "company": row["company"]}


async def _handoffs(run_id: str) -> list[str]:
    rows = await db.fetch(
        """SELECT payload FROM agent_traces
           WHERE run_id = $1::uuid AND kind = 'handoff' ORDER BY seq""", run_id)
    out = []
    for r in rows:
        payload = r["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        to = (payload or {}).get("to")
        if to:
            out.append(to)
    return out


async def _usage(run_id: str) -> tuple[int, int, float]:
    row = await db.fetchrow(
        """SELECT COALESCE(SUM(input_tokens),0) AS i, COALESCE(SUM(output_tokens),0) AS o,
                  COALESCE(SUM(cost_usd),0) AS c
           FROM ai_usage_events WHERE run_id = $1::uuid""", run_id)
    return int(row["i"]), int(row["o"]), float(row["c"])


async def _run_one(user_id: str, scenario: AgentScenario, subs: dict) -> dict:
    from app.agents.orchestrator import career_turn

    message = _fill(scenario.message, subs)
    context = dict(scenario.context or {})
    if scenario.needs_job and subs.get("job_id"):
        context.setdefault("job_id", subs["job_id"])
        context.setdefault("job_title", subs.get("job_title"))
        context.setdefault("company", subs.get("company"))

    run_id = await observability.create_run(user_id, "career", RUN_TRIGGER)
    obs = RunObservation()
    started = time.monotonic()
    try:
        out = await career_turn(user_id=user_id, message=message,
                                history=scenario.history, context=context or None,
                                run_id=run_id)
        obs.answer = out.answer
        obs.tools_used = list(out.tools_used)
        obs.artifact_types = [a.get("type") for a in out.artifacts if a.get("type")]
        obs.steps = out.steps
    except Exception as e:  # a failed run is a data point, not a crash
        obs.error = f"{type(e).__name__}: {e}"[:400]
    obs.latency_ms = int((time.monotonic() - started) * 1000)
    obs.handoffs = await _handoffs(run_id)
    obs.input_tokens, obs.output_tokens, obs.cost_usd = await _usage(run_id)
    await observability.finish_run(run_id, "failed" if obs.error else "completed",
                                   obs.input_tokens, obs.output_tokens, 0,
                                   obs.cost_usd, obs.latency_ms, obs.error)
    observability.release_trace_seq(run_id)

    row = score_run(scenario, obs)
    row["run_id"] = run_id
    return row


def _provider_caveat(config: dict) -> list[str]:
    """Move the module's honest note to where the numbers are.

    The docstring already says a stub provider scores low on tool selection and that this
    is the correct result, proving the harness discriminates. The report said none of
    that, so `tool_f1 0.19` read as a verdict on the agent. A reader who only ever sees
    the artifact should not have to go find the docstring — the same reason the RAG report
    now carries its own caveat.
    """
    if str(config.get("llm_provider", "")) != "mock":
        return []
    return ["## What these numbers mean", "",
            "- **Tool selection is unmeasured.** `llm_provider=mock` picks from a "
            "three-keyword heuristic (`providers/llm/mock.py: TOOL_HINTS`) while the "
            "orchestrator offers 15 tools, and it emits at most one call per turn. "
            "`tool_recall`, `tool_precision`, `tool_f1` and `completed` therefore describe "
            "the stub, not the agent. What this run does establish is that the harness "
            "discriminates — the scores move with the scenarios, `forbidden_violations` and "
            "`errors` are measured, and 0 of each is a real result. Point it at a real "
            "provider to measure model quality.", ""]


def _markdown(report: dict) -> str:
    agg = report["aggregate"]
    lines = [
        f"# Agent evaluation — {report['experiment']}", "",
        f"- scenarios: {report['n_scenarios']} (skipped: {len(report['skipped'])})",
        f"- provider: `{report['config']['llm_provider']}` / `{report['config']['llm_model']}`",
        f"- user: `{report['config']['user_id']}`", "",
        "## Aggregate", "",
        "| metric | value |", "|---|---|",
    ]
    lines += [f"| {k} | {v} |" for k, v in agg.items()]
    if report.get("caveat"):
        # The blank line matters: without it the heading is absorbed into the table.
        lines += [""] + report["caveat"]
    lines += ["", "## By tag", "", "| tag | completed | tool_f1 | artifact_rate |",
              "|---|---|---|---|"]
    for tag, a in report["by_tag"].items():
        lines.append(f"| {tag} | {a['completed']} | {a['tool_f1']} "
                     f"| {a['artifact_rate']} |")
    lines += ["", "## Scenarios", "",
              "| id | tools used | expected | recall | art | ground | completed |",
              "|---|---|---|---|---|---|---|"]
    for c in report["cases"]:
        lines.append(
            f"| {c['scenario']} | {', '.join(c['tools_used']) or '—'} "
            f"| {', '.join(c['expected_tools']) or '—'} | {c['tool_recall']} "
            f"| {c['artifact_rate']} | {c['grounding_rate']} "
            f"| {'yes' if c['completed'] else 'no'} |")
    fails = [c for c in report["cases"] if not c["completed"]]
    if fails:
        lines += ["", "## Why the incomplete runs failed", ""]
        for c in fails:
            reasons = []
            if c["tool_recall"] < 1.0:
                reasons.append(f"missing tools: "
                               f"{sorted(set(c['expected_tools']) - set(c['tools_used']))}")
            if c["forbidden_hit"]:
                reasons.append(f"forbidden tools fired: {c['forbidden_hit']}")
            if c["artifact_rate"] < 1.0:
                reasons.append(f"missing artifacts: "
                               f"{sorted(set(c['expected_artifacts']) - set(c['artifacts_seen']))}")
            if c["grounding_rate"] < 1.0:
                reasons.append(f"answer did not mention: "
                               f"{sorted(set(c['must_mention']) - set(c['mentioned']))}")
            if not c["handoff_ok"]:
                reasons.append(f"expected handoff to {c['expected_handoff_to']}, "
                               f"got {c['handoffs'] or 'none'}")
            if c["error"]:
                reasons.append(f"error: {c['error']}")
            if not c["answer_preview"]:
                reasons.append("empty answer")
            lines.append(f"- **{c['scenario']}** — " + "; ".join(reasons or ["unknown"]))
    if report["skipped"]:
        lines += ["", "## Skipped", ""]
        lines += [f"- {s['id']}: {s['reason']}" for s in report["skipped"]]
    return "\n".join(lines) + "\n"


async def run(args: argparse.Namespace) -> dict:
    from app.agents.orchestrator import MAX_STEPS

    s = get_settings()
    scenarios = load_scenarios(args.dataset) if args.dataset else AGENT_SCENARIOS
    if args.tags:
        wanted = {t.strip() for t in args.tags.split(",") if t.strip()}
        scenarios = [c for c in scenarios if wanted & set(c.tags)]
    if args.limit:
        scenarios = scenarios[:args.limit]

    job = await _pick_job()
    subs = job or {"job_id": "", "job_title": "", "company": ""}

    results, skipped = [], []
    for scenario in scenarios:
        if scenario.needs_job and not job:
            skipped.append({"id": scenario.id, "reason": "no_open_job_in_corpus"})
            continue
        results.append(await _run_one(args.user_id, scenario, subs))

    config = {
        "user_id": args.user_id,
        "llm_provider": s.llm_provider,
        "llm_model": s.llm_model,
        "anchor_job": job,
        "max_steps": MAX_STEPS,
    }
    report = {
        "experiment": args.experiment,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "config": config,
        "n_scenarios": len(results),
        "skipped": skipped,
        "aggregate": aggregate(results),
        "by_tag": aggregate_by_tag(results),
        "caveat": _provider_caveat(config),
        "cases": results,
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--user-id", required=True,
                   help="user whose resume/knowledge base the scenarios run against")
    p.add_argument("--experiment", default=f"agent-{uuid.uuid4().hex[:6]}")
    p.add_argument("--tags", default=None, help="comma-separated tag filter")
    p.add_argument("--dataset", default=None, help="JSON scenario override file")
    p.add_argument("--limit", type=int, default=0, help="run only the first N scenarios")
    p.add_argument("--out", default="evals/reports")
    return p.parse_args(argv)


def assert_something_was_measured(report: dict) -> None:
    """Refuse to let a run that ran no scenario pass as a clean one.

    The RAG runner has the same guard for the same reason: a summary of
    `"n_scenarios": 0, "aggregate": {}` exiting 0 is indistinguishable from a successful
    run to anyone skimming, and "0 errors, 0 violations" reads as *good* when it actually
    means *nothing ran*. An empty `--dataset`, or a `--tags` filter matching none of the
    scenarios, is the way this happens.
    """
    if report["n_scenarios"]:
        return
    raise SystemExit(
        "\n0 scenarios ran -- nothing was measured.\n"
        "  Either the scenario set is empty or `--tags` matched none of it. The default\n"
        "  set is `app/eval/agent_dataset.py`; `--tags` and `--limit` narrow it, and an\n"
        "  override file is read from `--dataset`. Note that `errors: 0` and\n"
        "  `forbidden_violations: 0` below are vacuously true of an empty run, not a\n"
        "  result -- nothing was asked, so nothing could fail.\n"
    )


async def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    await db.init_db()
    try:
        report = await run(args)
    finally:
        await db.close_db()
    print(json.dumps({"experiment": report["experiment"],
                      "n_scenarios": report["n_scenarios"],
                      "aggregate": report["aggregate"],
                      "files": report["_files"]}, ensure_ascii=False, indent=2))
    assert_something_was_measured(report)


if __name__ == "__main__":
    asyncio.run(main())
