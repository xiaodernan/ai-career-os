"""RAG evaluation runner — `python -m app.eval.run_eval --user-id <uuid>`.

Runs the golden set through the real retrieval pipeline (and optionally the
answer generator), scores retrieval + generation, and writes JSON/Markdown
reports to evals/reports/ so experiments can be compared (PRD §32).
"""

import argparse
import asyncio
import json
import statistics
import time
import uuid
from pathlib import Path

from app.core import db
from app.core.config import get_settings
from app.eval.dataset import GOLDEN_SET, EvalCase, load_dataset
from app.eval.metrics import llm_judge, score_case
from app.providers.pricing import estimate_cost
from app.rag.pipeline import retrieve

METRIC_KEYS = ["recall_at_k", "precision_at_k", "mrr", "ndcg_at_k", "hit_at_k",
               "context_relevance", "answer_relevance", "faithfulness",
               "citation_correctness"]

# The metrics a retrieval-only run can honestly report: everything derived from the query
# and the retrieved chunks. `answer_relevance` and `faithfulness` need an answer to score,
# so without `--answer` they are absent rather than zero.
RETRIEVAL_METRIC_KEYS = ["recall_at_k", "precision_at_k", "mrr", "ndcg_at_k", "hit_at_k",
                         "context_relevance"]


def measured_metric_keys(answer_requested: bool) -> list[str]:
    """The metrics a run may average, given whether it asked for an answer at all."""
    return [m for m in METRIC_KEYS if answer_requested or m in RETRIEVAL_METRIC_KEYS]

ANSWER_SYSTEM = """You are a career assistant answering strictly from the provided
evidence. Cite [n]. If evidence is missing, say so. Be concise."""

# A second answer voice for the prompt experiments (PRD §32), offered alongside the
# fixed default so a run can ask whether the wording changes the groundedness score.
ANSWER_SYSTEM_VARIANT = """You are a career assistant. Answer ONLY from the evidence
below. Every claim must carry its citation as [n]; if the evidence does not cover the
question, say the evidence does not cover it. Be concise."""


async def _relevant_ids(user_id: str, case: EvalCase) -> set[str]:
    if not case.keywords:
        return set()
    ors = " OR ".join(f"text ILIKE ${i + 2} ESCAPE '!'" for i in range(len(case.keywords)))
    rows = await db.fetch(
        f"""SELECT id::text AS id FROM document_chunks
            WHERE user_id = $1::uuid AND ({ors})""",
        user_id, *[db.like_contains(k) for k in case.keywords])
    return {r["id"] for r in rows}


async def run(args: argparse.Namespace) -> dict:
    from app.core.ai import ask
    from app.providers.base import LLMMessage, LLMRequest

    s = get_settings()
    if args.rerank:
        s.rerank_mode = args.rerank
    # `--chunk-target-tokens` only takes effect against a freshly ingested corpus; it
    # is recorded in the report either way so a run that forgot to re-ingest is legible.
    if args.chunk_target_tokens:
        s.chunk_target_tokens = args.chunk_target_tokens
    strategy = args.strategy or "hybrid"
    max_expansions = args.max_expansions if args.max_expansions >= 0 else None
    answer_prompt = {"default": ANSWER_SYSTEM, "variant": ANSWER_SYSTEM_VARIANT,
                     "strict": ANSWER_SYSTEM_VARIANT}.get(args.prompt or "default", ANSWER_SYSTEM)
    cases = load_dataset(args.dataset) if args.dataset else GOLDEN_SET
    if args.tags:
        wanted = set(args.tags.split(","))
        cases = [c for c in cases if wanted & set(c.tags)]

    results, skipped = [], []
    total_in = total_out = 0
    total_cost = 0.0
    for case in cases:
        relevant = await _relevant_ids(args.user_id, case)
        if not relevant:
            skipped.append({"id": case.id, "reason": "no_ground_truth"})
            continue
        t0 = time.monotonic()
        r = await retrieve(case.query, user_id=args.user_id, top_k=args.top_k,
                           strategy=strategy, max_expansions=max_expansions)
        retrieval_ms = int((time.monotonic() - t0) * 1000)
        evidence = r.get("evidence") or []
        retrieved_ids = [e["chunk_id"] for e in evidence]
        contexts = [e["quote"] for e in evidence]

        answer = ""
        judged = None
        answer_ms = 0
        if args.answer and contexts:
            t1 = time.monotonic()
            resp = await ask(LLMRequest(
                messages=[LLMMessage("system", answer_prompt),
                          LLMMessage("user", f"Question: {case.query}\n\n"
                                             + r.get("context_block", ""))],
                temperature=0.2, max_tokens=900),
                user_id=args.user_id, agent="eval", kind="eval_answer")
            answer = resp.text
            total_in += resp.usage.input_tokens
            total_out += resp.usage.output_tokens
            # The answer call is the product's own cost; the judge below is harness
            # overhead and is deliberately not billed to the product's number.
            total_cost += estimate_cost(
                resp.model or s.llm_model,
                resp.usage.input_tokens,
                resp.usage.output_tokens,
                resp.usage.cached_tokens)
            if s.llm_provider != "mock":
                judged = await llm_judge(case.query, contexts, answer,
                                         user_id=args.user_id)
            answer_ms = int((time.monotonic() - t1) * 1000)
        # Pass the answer as generated -- never a stand-in. This used to be
        # `answer or " ".join(contexts)[:1200]`, which fed the retrieved context back in
        # as the "answer" whenever no answer was requested. Faithfulness then compared the
        # context against itself and reported a tautological 1.0, so a retrieval-only run
        # published a perfect groundedness score for a generator that was never called.
        row = score_case(case.query, retrieved_ids, relevant, contexts,
                         answer, args.k, judged)
        row.update({"case": case.id, "query": case.query, "mode": "eval",
                    "retrieval_ms": retrieval_ms, "answer_ms": answer_ms,
                    "n_evidence": len(evidence),
                    "relevant": len(relevant),
                    "judge": (judged or {}).get("judge", "lexical")})
        results.append(row)

    # Aggregate only what this run measured. Without `--answer` no generation happened,
    # so `answer_relevance` and `faithfulness` have no value to average -- reporting them
    # as 0.0 would read as a failed generator, and reporting the old context-vs-itself
    # numbers read as a perfect one. Neither is a measurement, so neither is published.
    measured = measured_metric_keys(args.answer)
    aggregate = {m: round(statistics.mean(x[m] for x in results), 4)
                 for m in measured} if results else {}
    config = {"k": args.k, "top_k": args.top_k, "answer": args.answer,
              "rerank_mode": s.rerank_mode, "llm_provider": s.llm_provider,
              "llm_model": s.llm_model,
              "embedding_provider": s.embedding_provider,
              "embedding_model": s.embedding_model,
              "chunk_target_tokens": s.chunk_target_tokens,
              "strategy": strategy,
              "max_expansions": max_expansions if max_expansions is not None else -1,
              "answer_prompt": args.prompt or "default"}
    report = {
        "experiment": args.experiment,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "config": config,
        "n_cases": len(results), "skipped": skipped,
        "aggregate": aggregate,
        "caveat": _provider_caveat(config),
        "tokens": {"input": total_in, "output": total_out},
        "cost": {"usd": round(total_cost, 4), "model": s.llm_model,
                 "note": "answer generation only; the judge call is harness overhead"},
        "avg_retrieval_ms": round(statistics.mean(x["retrieval_ms"] for x in results), 1)
        if results else 0,
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


def _provider_caveat(config: dict) -> list[str]:
    """Say which numbers a reader may trust, when the providers cannot produce them.

    This matters more than the metrics do. `faithfulness: 0.0` beside
    `recall_at_k: 1.0` reads as "the generator is broken", when it means "no model was
    asked"; and a perfect recall looks like a semantic claim even though the vector
    half of the hybrid ranking was hash noise. Left unsaid, the report flatters the
    retrieval path and libels the generation one — both wrong, in opposite directions.
    """
    llm = str(config.get("llm_provider", ""))
    emb = str(config.get("embedding_provider", ""))
    offline = {"mock", "hash"}
    notes: list[str] = []
    if not config.get("answer", True):
        notes.append(
            "- **Generation was not run.** `--answer` was not passed, so `answer_relevance` "
            "and `faithfulness` are absent from the table rather than zero — there was no "
            "answer to score. The retrieval metrics are unaffected and complete.")
    if llm in offline:
        notes.append(
            f"- **Generation is unmeasured.** `llm_provider={llm}` answers from a stub that "
            "never reads the retrieved context, so `answer_relevance` and `faithfulness` "
            "describe the stub. Only the retrieval metrics above carry information.")
    if emb in offline:
        notes.append(
            f"- **Retrieval here is keyword-driven in effect.** `embedding_provider={emb}` "
            "produces no semantic signal, so the vector half of the hybrid ranking "
            "contributes noise and these scores reflect the keyword/trigram path. Re-run "
            "with a real embedding provider before reading them as semantic retrieval.")
    if not notes:
        return []
    return ["## What these numbers mean", ""] + notes + [""]


def _markdown(report: dict) -> str:
    lines = [f"# RAG evaluation — {report['experiment']}", "",
             f"- cases: {report['n_cases']} (skipped: {len(report['skipped'])})",
             f"- config: `{json.dumps(report['config'], ensure_ascii=False)}`", ""]
    agg = report["aggregate"]
    if agg:
        lines += ["| metric | value |", "|---|---|"]
        lines += [f"| {m} | {v} |" for m, v in agg.items()]
        lines += [f"| avg_retrieval_ms | {report['avg_retrieval_ms']} |", ""]
    tokens = report.get("tokens") or {}
    if tokens:
        lines += [f"- tokens: {tokens['input']} in / {tokens['output']} out", ""]
    cost = report.get("cost") or {}
    if cost:
        lines += [f"- cost: ${cost['usd']:.4f} ({cost['model']})", ""]
    if report.get("caveat"):
        # Blank line first: without it the heading is absorbed into the table above.
        lines += [""] + report["caveat"]
    lines += ["| case | recall@k | precision | MRR | nDCG | faithfulness | judge |",
              "|---|---|---|---|---|---|---|"]
    for c in report["cases"]:
        lines.append(f"| {c['case']} | {c['recall_at_k']} | {c['precision_at_k']} "
                     f"| {c['mrr']} | {c['ndcg_at_k']} | {c['faithfulness']} "
                     f"| {c['judge']} |")
    if report["skipped"]:
        lines += ["", "## Skipped", ""]
        lines += [f"- {s['id']}: {s['reason']}" for s in report["skipped"]]
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--user-id", required=True)
    p.add_argument("--experiment", default=f"exp-{uuid.uuid4().hex[:6]}")
    p.add_argument("--k", type=int, default=5, help="cutoff for @k metrics")
    p.add_argument("--top-k", type=int, default=8, help="retrieval depth")
    p.add_argument("--rerank", choices=["llm", "none"], default=None)
    p.add_argument("--answer", action="store_true", help="also score generation")
    p.add_argument("--dataset", default=None, help="jsonl override for golden set")
    p.add_argument("--tags", default=None, help="comma-separated tag filter")
    p.add_argument("--strategy", default=None,
                   choices=["hybrid", "vector", "keyword", "trigram", "vector,keyword",
                            "keyword,trigram"],
                   help="retrieval channels to fuse (default: hybrid = all three)")
    p.add_argument("--max-expansions", type=int, default=-1,
                   help="cap query expansions; -1 leaves the pipeline default alone")
    p.add_argument("--prompt", default=None, choices=["default", "variant", "strict"],
                   help="answer prompt variant to test against the same evidence")
    p.add_argument("--chunk-target-tokens", type=int, default=0,
                   help="chunk size to record for this experiment (needs re-ingest)")
    p.add_argument("--diff", default=None,
                   help="compare this run's reported metrics against that JSON report")
    p.add_argument("--out", default="evals/reports")
    return p.parse_args(argv)


def assert_something_was_measured(report: dict) -> None:
    """Refuse to let a run that measured nothing pass as a clean one.

    The summary used to print `"n_cases": 0, "aggregate": {}` and exit 0, so a corpus that
    never landed (the cp936 ingest bug, or a user with no knowledge chunks) read exactly
    like a successful run -- and an empty aggregate cannot be told from a perfect one by
    anyone skimming. Skipping *some* cases is normal and passes; skipping all of them means
    the measurement did not happen.
    """
    if report["n_cases"]:
        return
    skipped = len(report["skipped"])
    raise SystemExit(
        f"\n0 of {skipped} cases scored -- nothing was measured.\n"
        "  Every case skipped as `no_ground_truth`, which means the corpus holds no\n"
        "  chunk matching any case keyword. The golden set is tuned to the corpus\n"
        "  `scripts/smoke-fullstack.sh` writes, so check that its ingest step\n"
        "  reported `ready` for this user before reading anything into this run.\n"
        "  The empty aggregate in this run's summary is an absence, not a score.\n"
    )


def diff_reports(against_path: str, current: dict) -> list[str]:
    """Compare this run's aggregate against an earlier report's, as markdown lines.

    Every experiment had to be judged by opening two files side by side, so a question
    like "does the reranker actually help?" stayed unanswered by the harness that asked
    it. The diff only covers metrics both runs measured: comparing a retrieval-only run
    against an `--answer` run would report generation metrics that never existed there.
    """
    try:
        with open(against_path, encoding="utf-8") as f:
            before = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return [f"- **diff unavailable** — `{against_path}` could not be read: {e}"]

    a, b = before.get("aggregate") or {}, current.get("aggregate") or {}
    shared = [k for k in a if k in b]
    lines = ["## Diff vs " + Path(against_path).name, "",
             "| metric | before | now | delta |", "|---|---|---|---|"]
    if not shared:
        lines.append("| (no metrics measured by both runs) | — | — | — |")
    for k in shared:
        delta = round(b[k] - a[k], 4)
        lines.append(f"| {k} | {a[k]} | {b[k]} | {delta:+} |")
    return lines


async def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    await db.init_db()
    try:
        report = await run(args)
    finally:
        await db.close_db()
    if args.diff:
        report["diff"] = diff_reports(args.diff, report)
        # Append the comparison to the markdown report so the claim survives the run.
        mpath = Path(report["_files"][1])
        existing = mpath.read_text(encoding="utf-8") if mpath.exists() else ""
        mpath.write_text(existing + "\n" + "\n".join(report["diff"]) + "\n",
                         encoding="utf-8")
    print(json.dumps({"experiment": report["experiment"],
                      "n_cases": report["n_cases"],
                      "aggregate": report["aggregate"],
                      "files": report["_files"]}, ensure_ascii=False, indent=2))
    assert_something_was_measured(report)


if __name__ == "__main__":
    asyncio.run(main())
