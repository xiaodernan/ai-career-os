"""Ingestion pipeline: source bytes -> parse -> clean -> chunk -> tag -> embed -> store.

Progress is published on the task bus (SSE) with steps matching the frontend
ProcessingSteps UI: extracting → cleaning → chunking → embedding → indexing.
"""

import json

from app.core import db, taskbus
from app.core.config import get_settings
from app.core.skills import extract_skills
from app.db import documents as docs_repo
from app.ingestion.clean import clean
from app.ingestion.chunking import chunk_document
from app.ingestion.parsers import ParseError, extract_text


async def _fetch_bytes(file_key: str) -> bytes:
    import httpx

    from app.core.config import get_settings as gs

    s = gs()
    url = f"{s.backend_base_url}/api/internal/files/{file_key}"
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(url, headers={"X-Internal-Token": s.internal_api_token})
        r.raise_for_status()
        return r.content


async def ingest_document(doc_id: str, task_id: str) -> dict:
    s = get_settings()
    doc = await docs_repo.get_document(doc_id)
    if not doc:
        taskbus.finish(task_id, False, error="document not found")
        return {"error": "not found"}
    source_id = doc["source_id"]
    await docs_repo.set_status(doc_id, "indexing")
    try:
        taskbus.publish(task_id, "status", {"step": "extracting", "state": "active"})
        if doc["file_key"]:
            data = await _fetch_bytes(doc["file_key"])
            text = extract_text(data, doc["media_type"])
        else:
            inline = (doc.get("meta") or {})
            if isinstance(inline, str):
                inline = json.loads(inline)
            text = inline.get("inline_text") or doc.get("text_excerpt") or ""
            if not text:
                raise ParseError("no file_key and no inline text")
        taskbus.publish(task_id, "status", {"step": "extracting", "state": "done"})

        taskbus.publish(task_id, "status", {"step": "cleaning", "state": "active"})
        text = clean(text)
        taskbus.publish(task_id, "status", {"step": "cleaning", "state": "done"})

        taskbus.publish(task_id, "status", {"step": "chunking", "state": "active"})
        chunks = chunk_document(text, s.chunk_target_tokens, s.chunk_overlap_tokens)
        payload = []
        for c in chunks:
            skills = extract_skills(c.text)
            meta = dict(c.meta)
            if skills:
                meta["skills"] = skills
            meta["embedding_provider"] = s.embedding_provider
            payload.append({"ordinal": c.ordinal, "text": c.text,
                            "token_count": c.token_count, "section_path": c.section_path,
                            "kind": c.kind, "meta": meta})
        taskbus.publish(task_id, "status", {"step": "chunking", "state": "done",
                                            "count": len(chunks)})

        taskbus.publish(task_id, "status", {"step": "embedding", "state": "active"})
        from app.providers.registry import get_embeddings

        embedder = get_embeddings(s)
        batch = 64
        for i in range(0, len(payload), batch):
            texts = [p["text"] for p in payload[i:i + batch]]
            vecs = await embedder.embed(texts)
            for p, v in zip(payload[i:], vecs):
                p["embedding"] = v
            taskbus.publish(task_id, "progress",
                            {"step": "embedding", "done": min(i + batch, len(payload)),
                             "total": len(payload)})
        taskbus.publish(task_id, "status", {"step": "embedding", "state": "done"})

        taskbus.publish(task_id, "status", {"step": "indexing", "state": "active"})
        n = await docs_repo.replace_chunks(doc_id, str(doc["user_id"]), payload)
        await docs_repo.set_status(doc_id, "ready", text_excerpt=text)
        await docs_repo.mark_source_ready(str(source_id) if source_id else None, doc_id)
        taskbus.publish(task_id, "status", {"step": "indexing", "state": "done"})

        result = {"document_id": doc_id, "chunks": n, "chars": len(text)}
        taskbus.finish(task_id, True, result=result)
        return result
    except Exception as e:  # noqa: BLE001 — record & surface via status
        await docs_repo.set_status(doc_id, "failed", error=str(e)[:500])
        await docs_repo.mark_source_failed(str(source_id) if source_id else None, str(e)[:500])
        taskbus.finish(task_id, False, error=f"{type(e).__name__}: {e}")
        raise
