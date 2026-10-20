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
    _require_owner(task_id, ctx)
    return taskbus.state(task_id)


@router.get("/{task_id}/stream")
async def task_stream(task_id: str, ctx: Ctx = Depends(require_internal)):
    _require_owner(task_id, ctx)

    async def gen():
        async for ev in taskbus.subscribe(task_id):
            yield {"event": ev["event"], "data": _json(ev["data"])}

    return EventSourceResponse(gen())


def _require_owner(task_id: str, ctx: Ctx) -> None:
    """Refuse a task the caller does not own with the same answer a missing task gets.

    The relay hands over the id the browser put in the URL, so the only thing standing between one
    user and another user's frames is this comparison. A task with no owner recorded is nobody's,
    so the check fails closed: a call site that forgets to pass the user id breaks loudly here
    rather than opening the stream.
    """
    if taskbus.owner(task_id) != ctx.user_id:
        raise HTTPException(404, "task not found or expired")


# alias the backend SSE relay calls (architecture.md §9)
alias_router = APIRouter(prefix="/internal", tags=["tasks"])


@alias_router.get("/stream/{task_id}")
async def task_stream_alias(task_id: str, ctx: Ctx = Depends(require_internal)):
    return await task_stream(task_id, ctx)


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
