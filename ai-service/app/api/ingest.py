
from fastapi import APIRouter, Depends, HTTPException

from app.api.tasks import run_in_task
from app.core import taskbus
from app.core.deps import Ctx, require_internal
from app.db import documents as docs_repo
from app.ingestion.pipeline import ingest_document

router = APIRouter(prefix="/internal/ingest", tags=["ingest"])


@router.post("/document/{doc_id}")
async def start_ingest(doc_id: str, ctx: Ctx = Depends(require_internal)):
    doc = await docs_repo.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "document not found")
    if str(doc["user_id"]) != ctx.user_id:
        raise HTTPException(403, "not your document")
    task_id = taskbus.new_task("ingest", ctx.user_id)
    run_in_task(ingest_document(doc_id, task_id), task_id)
    return {"task_id": task_id, "document_id": doc_id}


@router.post("/text")
async def ingest_text(payload: dict, ctx: Ctx = Depends(require_internal)):
    """Register + ingest plain text (notes, pasted JDs, company blurbs).

    body: {title, text, kind, ref_id?, source_id?}
    """
    from app.core.config import get_settings
    from app.core import db

    s = get_settings()
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(422, "text required")
    kind = payload.get("kind", "note")
    src = await db.fetchrow(
        """INSERT INTO knowledge_sources(user_id, kind, ref_id, title, status)
           VALUES ($1::uuid,$2,$3::uuid,$4,'ingesting') RETURNING id""",
        ctx.user_id, kind, payload.get("ref_id"), (payload.get("title") or "Untitled")[:200])
    content_hash = docs_repo.sha256(text.encode())
    doc_id = await docs_repo.create_document(
        ctx.user_id, str(src["id"]), None, "text/plain",
        payload.get("title") or "Untitled", content_hash,
        {"inline_text": text[:200000], "kind": kind}, text_excerpt=text[:2000])
    await docs_repo.set_status(doc_id, "indexing")
    task_id = taskbus.new_task("ingest", ctx.user_id)
    run_in_task(ingest_document(str(doc_id), task_id), task_id)
    return {"task_id": task_id, "document_id": doc_id, "source_id": str(src["id"]),
            "embedding_provider": s.embedding_provider}
