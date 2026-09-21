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


async def retrieve(query: str, *, user_id: str, run_id: str | None = None,
                   context_summary: str = "", top_k: int = 8,
                   kinds: list[str] | None = None,
                   document_ids: list[str] | None = None,
                   task_id: str | None = None) -> dict[str, Any]:
    """Retrieve evidence for a query. Returns understanding + evidence (citable)."""
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
    queries = [u["rewritten"]] + u["expansions"]
    vecs = []
    for q in queries:
        vecs.extend(await embedder.embed([q]))

    filter_kinds = kinds or (u.get("filters") or {}).get("kinds") or None

    lists = []
    for v in vecs:
        lists.append(await store.vector_search(user_id, v, k=25, kinds=filter_kinds,
                                               document_ids=document_ids))
    kw_terms = u["rewritten"] + " " + " ".join(u["keywords"])
    lists.append(await store.keyword_search(user_id, kw_terms, k=25, kinds=filter_kinds,
                                            document_ids=document_ids))
    lists.append(await store.trigram_search(user_id, u["rewritten"], k=10))

    merged = store.rrf_merge(lists)
    if run_id:
        await observability.trace(run_id, "retrieval", "rag", {
            "stage": "hybrid", "channels": len(lists), "merged": len(merged),
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
    return {"understanding": u, "evidence": evidence,
            "context_block": evidence_block([{"chunk_id": e["chunk_id"],
                                              "source": e["doc_title"],
                                              "section": e["section"],
                                              "text": e["quote"]} for e in evidence])}
