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
from app.rag.pipeline import retrieve

METRIC_KEYS = ["recall_at_k", "precision_at_k", "mrr", "ndcg_at_k", "hit_at_k",
               "context_relevance", "answer_relevance", "faithfulness"]

ANSWER_SYSTEM = """You are a career assistant answering strictly from the provided
evidence. Cite [n]. If evidence is missing, say so. Be concise."""


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
    cases = load_dataset(args.dataset) if args.dataset else GOLDEN_SET
    if args.tags:
        wanted = set(args.tags.split(","))
        cases = [c for c in cases if wanted & set(c.tags)]

    results, skipped = [], []
    total_in = total_out = 0
    for case in cases:
        relevant = await _relevant_ids(args.user_id, case)
        if not relevant:
            skipped.append({"id": case.id, "reason": "no_ground_truth"})
            continue
        t0 = time.monotonic()
        r = await retrieve(case.query, user_id=args.user_id, top_k=args.top_k)
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
                messages=[LLMMessage("system", ANSWER_SYSTEM),
                          LLMMessage("user", f"Question: {case.query}\n\n"
                                             + r.get("context_block", ""))],
                temperature=0.2, max_tokens=900),
                user_id=args.user_id, agent="eval", kind="eval_answer")
            answer = resp.text
            total_in += resp.usage.input_tokens
            total_out += resp.usage.output_tokens
            if s.llm_provider != "mock":
                judged = await llm_judge(case.query, contexts, answer,
                                         user_id=args.user_id)
            answer_ms = int((time.monotonic() - t1) * 1000)
        row = score_case(case.query, retrieved_ids, relevant, contexts,
                         answer or " ".join(contexts)[:1200], args.k, judged)
        row.update({"case": case.id, "query": case.query, "mode": "eval",
                    "retrieval_ms": retrieval_ms, "answer_ms": answer_ms,
                    "n_evidence": len(evidence),
                    "relevant": len(relevant),
                    "judge": (judged or {}).get("judge", "lexical")})
        results.append(row)

    aggregate = {m: round(statistics.mean(x[m] for x in results), 4)
                 for m in METRIC_KEYS} if results else {}
    config = {"k": args.k, "top_k": args.top_k, "answer": args.answer,
              "rerank_mode": s.rerank_mode, "llm_provider": s.llm_provider,
              "llm_model": s.llm_model,
              "embedding_provider": s.embedding_provider,
              "embedding_model": s.embedding_model,
              "chunk_target_tokens": s.chunk_target_tokens}
    report = {
        "experiment": args.experiment,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "config": config,
        "n_cases": len(results), "skipped": skipped,
        "aggregate": aggregate,
        "caveat": _provider_caveat(config),
        "tokens": {"input": total_in, "output": total_out},
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
    if llm not in offline and emb not in offline:
        return []
    out = ["## What these numbers mean", ""]
    if llm in offline:
        out.append(
            f"- **Generation is unmeasured.** `llm_provider={llm}` answers from a stub that "
            "never reads the retrieved context, so `answer_relevance` and `faithfulness` "
            "describe the stub. Only the retrieval metrics above carry information.")
    if emb in offline:
        out.append(
            f"- **Retrieval here is keyword-driven in effect.** `embedding_provider={emb}` "
            "produces no semantic signal, so the vector half of the hybrid ranking "
            "contributes noise and these scores reflect the keyword/trigram path. Re-run "
            "with a real embedding provider before reading them as semantic retrieval.")
    out.append("")
    return out


def _markdown(report: dict) -> str:
    lines = [f"# RAG evaluation — {report['experiment']}", "",
             f"- cases: {report['n_cases']} (skipped: {len(report['skipped'])})",
             f"- config: `{json.dumps(report['config'], ensure_ascii=False)}`", ""]
    agg = report["aggregate"]
    if agg:
        lines += ["| metric | value |", "|---|---|"]
        lines += [f"| {m} | {v} |" for m, v in agg.items()]
        lines += [f"| avg_retrieval_ms | {report['avg_retrieval_ms']} |", ""]
    lines += report.get("caveat") or []
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
    p.add_argument("--out", default="evals/reports")
    return p.parse_args(argv)


async def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    await db.init_db()
    try:
        report = await run(args)
    finally:
        await db.close_db()
    print(json.dumps({"experiment": report["experiment"],
                      "n_cases": report["n_cases"],
                      "aggregate": report["aggregate"],
                      "files": report["_files"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
