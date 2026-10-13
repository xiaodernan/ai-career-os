"""Full RAG pipeline (PRD §5):

understand → hybrid retrieve (vector ∪ keyword ∪ trigram) → metadata filter →
RRF → rerank → compression → prompt construction with citations.
"""

from typing import Any

from app.core import taskbus
from app.core.ai import evidence_block
from app.db import observability
from app.providers.registry import get_embeddings
from app.rag import store
from app.rag.compress import compress
from app.rag.rerank import rerank
from app.rag.rewrite import understand

# Extra full-text queries beyond the rewritten one. Each is a round trip, so the
# multi-query expansion is bounded even though query understanding may return 8 keywords.
KEYWORD_FANOUT = 4


async def retrieve(query: str, *, user_id: str, run_id: str | None = None,
                   context_summary: str = "", top_k: int = 8,
                   kinds: list[str] | None = None,
                   document_ids: list[str] | None = None,
                   task_id: str | None = None,
                   strategy: str = "hybrid",
                   answer_prompt: str | None = None,
                   max_expansions: int | None = None) -> dict[str, Any]:
    """Retrieve evidence for a query. Returns understanding + evidence (citable).

    `strategy` selects which retrieval channels contribute to the fusion: the full
    `hybrid` default (vector ∪ keyword ∪ trigram), or a single channel on its own
    (`vector`, `keyword`, `trigram`). It exists for the RAG experiments asked for by
    PRD §32 — the reranker was the only switch the harness had, so "is the hybrid
    actually better than keyword alone?" could not be answered by a run.
    """
    if task_id:
        taskbus.publish(task_id, "status", {"step": "understanding_query", "state": "active"})
    u = await understand(query, context_summary, user_id=user_id, run_id=run_id)
    if task_id:
        taskbus.publish(task_id, "status", {"step": "understanding_query", "state": "done",
                                            "intent": u["intent"]})
    if run_id:
        await observability.trace(run_id, "retrieval", "rag", {"stage": "understand", **u})

    if task_id:
        taskbus.publish(task_id, "status", {"step": "hybrid_retrieval", "state": "active"})
    embedder = get_embeddings()
    # `max_expansions` caps the multi-query fan-out for the retrieval experiments, so
    # a run can ask what the expanded queries are actually worth.
    expansions = u["expansions"] if max_expansions is None else u["expansions"][:max_expansions]
    queries = [u["rewritten"]] + expansions
    vecs = []
    for q in queries:
        vecs.extend(await embedder.embed([q]))

    filter_kinds = kinds or (u.get("filters") or {}).get("kinds") or None
    # A caller-supplied `kinds` is a request; the understanding step's is a guess.
    inferred_kinds = not kinds and bool(filter_kinds)

    # Which channels contribute to the fusion. `hybrid` is the product default; the
    # single-channel names exist so an experiment can ask whether the hybrid actually
    # beats keyword alone (PRD §32).
    # An unrecognised (or empty) name must not mean "no channels": it would retrieve
    # nothing at all and report that emptiness as a result.
    channels = [c.strip() for c in strategy.split(",") if c.strip()]
    if not channels or not set(channels) & {"hybrid", "vector", "keyword", "trigram"}:
        channels = ["hybrid"]
    # `hybrid` is an alias for all three, including the fallback above.
    if "hybrid" in channels:
        channels = ["vector", "keyword", "trigram"]

    async def retrieve(kinds_filter: list[str] | None) -> list[dict]:
        lists = []
        if "vector" in channels:
            for v in vecs:
                lists.append(await store.vector_search(user_id, v, k=25, kinds=kinds_filter,
                                                       document_ids=document_ids))
        if "keyword" in channels:
            for phrase in keyword_phrases(u):
                lists.append(await store.keyword_search(user_id, phrase, k=25, kinds=kinds_filter,
                                                        document_ids=document_ids))
        if "trigram" in channels:
            lists.append(await store.trigram_search(user_id, u["rewritten"], k=10,
                                                    kinds=kinds_filter,
                                                    document_ids=document_ids))
        return store.rrf_merge(lists)

    merged = await retrieve(filter_kinds)
    if not merged and inferred_kinds:
        # The understanding step guesses a source-`kinds` filter, and a guess matching
        # nothing empties retrieval silently. A real provider does this: asked "what
        # backend frameworks does the candidate know?", qwen2.5:7b returned
        # `kinds: ["project"]` for a user whose only source is a resume -- and 13 of 15
        # golden cases came back with no evidence at all, which the mock never showed
        # because its canned understanding emitted no filter. An empty result is never
        # more useful than a broader one, so retry once without the guess. A
        # caller-supplied `kinds` is left alone: that is a request, not a guess.
        merged = await retrieve(None)
        if run_id and merged:
            await observability.trace(run_id, "retrieval", "rag", {
                "stage": "kinds_filter_dropped", "guessed": filter_kinds,
                "recovered": len(merged)})

    if run_id:
        await observability.trace(run_id, "retrieval", "rag", {
            "stage": "hybrid", "channels": channels, "merged": len(merged),
            "top": [{"chunk_id": str(m["id"]), "rrf": round(m["rrf"], 5),
                     "source": m.get("doc_title"), "section": m.get("section_path")}
                    for m in merged[:10]]})
    if not merged:
        return {"understanding": u, "evidence": []}

    if task_id:
        taskbus.publish(task_id, "status", {"step": "hybrid_retrieval", "state": "done",
                                            "count": len(merged)})
        taskbus.publish(task_id, "status", {"step": "reranking", "state": "active"})
    top = await rerank(u["rewritten"], merged, top_n=top_k, user_id=user_id, run_id=run_id)
    if task_id:
        taskbus.publish(task_id, "status", {"step": "reranking", "state": "done"})

    compressed = compress([u["rewritten"]] + u["keywords"], top)
    evidence = to_evidence(compressed)
    return {"understanding": u, "evidence": evidence,
            "context_block": evidence_block([{"chunk_id": e["chunk_id"],
                                              "source": e["doc_title"],
                                              "section": e["section"],
                                              "text": e["quote"]} for e in evidence])}


def keyword_phrases(u: dict) -> list[str]:
    """Full-text queries to fan out over: the rewritten query plus each keyword.

    One phrase per call, never one concatenation. `plainto_tsquery` ANDs every term it
    is given, and a CJK run without spaces collapses to a *single* tsvector lexeme, so
    `rewritten + all keywords` lets one unmatchable term veto the whole channel
    (measured on live data: 'kafka' hits 5 chunks, '<zh question> Kafka Spring Boot
    微服务' hits 0). Per phrase the AND stays inside a term group -- which is what
    match.py relies on for 'Spring Boot' -- and RRF supplies the OR across them.
    """
    out: list[str] = []
    for raw in [u["rewritten"], *u["keywords"]]:
        phrase = " ".join((raw or "").split())
        if phrase and phrase.lower() not in {p.lower() for p in out}:
            out.append(phrase)
    return out[:KEYWORD_FANOUT + 1]


def to_evidence(compressed: list[dict]) -> list[dict]:
    """Shape post-compression chunks into the citable evidence payload.

    Pure: the displayed score is the best of the rerank / RRF signals (either may be
    absent depending on rerank_mode), quotes are capped, and refs are 1-based so
    downstream prompt citations stay stable.
    """
    evidence = []
    for i, c in enumerate(compressed, 1):
        evidence.append({
            "ref": i,
            "chunk_id": str(c["id"]),
            "document_id": str(c["document_id"]),
            "doc_title": c.get("doc_title"),
            "source_kind": c.get("source_kind"),
            "section": c.get("section_path"),
            "quote": (c.get("text") or "")[:600],
            "score": round(max(c.get("rerank", 0) or 0, c.get("rrf", 0) or 0), 4),
        })
    return evidence
