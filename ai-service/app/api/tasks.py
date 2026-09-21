import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.core import taskbus
from app.core.deps import Ctx, require_internal

log = logging.getLogger("tasks")

router = APIRouter(prefix="/internal/tasks", tags=["tasks"])


@router.get("/{task_id}")
async def task_state(task_id: str, ctx: Ctx = Depends(require_internal)):
    st = taskbus.state(task_id)
    if not st:
        raise HTTPException(404, "task not found or expired")
    return st


@router.get("/{task_id}/stream")
async def task_stream(task_id: str, ctx: Ctx = Depends(require_internal)):
    if not taskbus.state(task_id):
        raise HTTPException(404, "task not found or expired")

    async def gen():
        async for ev in taskbus.subscribe(task_id):
            yield {"event": ev["event"], "data": _json(ev["data"])}

    return EventSourceResponse(gen())


def _json(data) -> str:
    import json

    return json.dumps(data, ensure_ascii=False, default=str)


def run_in_task(coro, task_id: str):
    """Spawn a background pipeline run; completion reported on the task bus."""

    async def _wrap():
        try:
            await coro
        except Exception:
            log.exception("background task %s crashed", task_id)

    asyncio.create_task(_wrap())
