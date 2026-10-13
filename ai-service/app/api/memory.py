"""Long-term memory HTTP surface (PRD §17).

The write path had a route (chat extraction) and the read path had a reader
(the system-prompt context). Nothing let a user look at what the model remembered and
correct it, so a sentence the extractor invented was quoted back on every later turn
with no way to say so.

Three routes: list, patch, delete. All three scope to the caller's own rows in the WHERE
clause, which is the ownership rule the documents describe — an id belonging to somebody
else is a 404, not a 403, because "not yours" and "not there" are the same answer.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.deps import Ctx, require_internal
from app.db import domain

log = logging.getLogger("memory.api")

router = APIRouter(prefix="/internal/memories", tags=["memories"])


class MemoryItem(BaseModel):
    id: str
    kind: str
    key: str
    content: str
    importance: float
    source: str
    createdAt: str | None = None
    updatedAt: str | None = None


class MemoryPatch(BaseModel):
    content: str | None = Field(default=None, max_length=4000)
    importance: float | None = Field(default=None, ge=0.0, le=1.0)


def _memory_row(row: dict) -> dict:
    return {"id": str(row["id"]), "kind": row["kind"], "key": row["key"],
            "content": row["content"], "importance": row["importance"],
            "source": row["source"],
            "createdAt": str(row.get("created_at")) if row.get("created_at") else None,
            "updatedAt": str(row.get("updated_at")) if row.get("updated_at") else None}


@router.get("")
async def list_memories(ctx: Ctx = Depends(require_internal),
                       kinds: str | None = None, limit: int = 100):
    """What the model remembers about this user, newest update first."""
    want = [k.strip() for k in kinds.split(",") if k.strip()] if kinds else None
    rows = await domain.list_memories(ctx.user_id, want, max(1, min(limit, 200)))
    return {"items": [_memory_row(r) for r in rows]}


@router.patch("/{memory_id}")
async def patch_memory(memory_id: str, body: MemoryPatch,
                       ctx: Ctx = Depends(require_internal)):
    """Correct a memory's text, or lower its weight.

    An empty body is allowed and answers with the row unchanged, because lowering
    importance and fixing the content are two different corrections and a caller that
    only wants one should not have to send the other.
    """
    if body.content is not None and not body.content.strip():
        # A blank content is what "forget this sentence" sounds like to a model that
        # would happily store "" next turn.
        raise HTTPException(400, "memory content cannot be blank — delete it instead")
    row = await domain.update_memory(ctx.user_id, memory_id,
                                     content=body.content, importance=body.importance)
    if row is None:
        raise HTTPException(404, "memory not found")
    return _memory_row(row)


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(memory_id: str, ctx: Ctx = Depends(require_internal)):
    """Forget one memory outright."""
    gone = await domain.delete_memory(ctx.user_id, memory_id)
    if not gone:
        raise HTTPException(404, "memory not found")
