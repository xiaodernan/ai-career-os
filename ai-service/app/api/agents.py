"""Career Agent HTTP surface: copilot chat + run/trace queries (AI Activity)."""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.agents import memory
from app.agents.orchestrator import career_turn
from app.api.tasks import run_in_task
from app.core import db, taskbus
from app.core.config import get_settings
from app.core.deps import Ctx, require_internal
from app.db import observability

log = logging.getLogger("agents.api")

router = APIRouter(prefix="/internal/agents", tags=["agents"])


class ChatReq(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    history: list[dict] = Field(default_factory=list)
    conversation_id: str | None = None
    context: dict = Field(default_factory=dict)


@router.post("/chat")
async def chat(req: ChatReq, ctx: Ctx = Depends(require_internal)):
    s = get_settings()
    run_id = ctx.run_id or await observability.create_run(
        ctx.user_id, "career", "chat", model=s.llm_model,
        conversation_id=req.conversation_id)
    task_id = taskbus.new_task("agent_chat", ctx.user_id)

    async def work():
        started = time.monotonic()
        try:
            out = await career_turn(user_id=ctx.user_id, message=req.message,
                                    history=req.history, context=req.context,
                                    run_id=run_id, task_id=task_id, stream=True)
            await observability.finish_run(run_id, "completed",
                                           latency_ms=int((time.monotonic() - started)
                                                          * 1000))
            taskbus.finish(task_id, True, out.to_dict())
            try:
                await memory.extract_and_store(ctx.user_id, req.message, out.answer,
                                               run_id=run_id)
            except Exception:
                log.warning("memory extraction crashed", exc_info=True)
        except Exception as e:
            log.exception("agent chat turn failed")
            await observability.finish_run(run_id, "failed", error=str(e)[:500],
                                           latency_ms=int((time.monotonic() - started)
                                                          * 1000))
            taskbus.finish(task_id, False, error=str(e)[:500])
        finally:
            observability.release_trace_seq(run_id)

    run_in_task(work(), task_id)
    return {"task_id": task_id, "run_id": run_id}


@router.post("/chat/sync")
async def chat_sync(req: ChatReq, ctx: Ctx = Depends(require_internal)):
    """Blocking variant used by the backend relay and E2E tests."""
    s = get_settings()
    run_id = ctx.run_id or await observability.create_run(
        ctx.user_id, "career", "chat", model=s.llm_model,
        conversation_id=req.conversation_id)
    started = time.monotonic()
    try:
        out = await career_turn(user_id=ctx.user_id, message=req.message,
                                history=req.history, context=req.context,
                                run_id=run_id)
    except Exception as e:
        await observability.finish_run(run_id, "failed", error=str(e)[:500])
        raise HTTPException(502, f"agent run failed: {str(e)[:300]}") from e
    await observability.finish_run(run_id, "completed",
                                   latency_ms=int((time.monotonic() - started) * 1000))
    # The streaming path writes durable memory; this one is the pair the eval harness and
    # the e2e suite drive, so a turn that only ever took that path learned nothing.
    # Best-effort for the same reason the streaming path is: a failed extraction must
    # never turn a answered turn into an error.
    try:
        await memory.extract_and_store(ctx.user_id, req.message, out.answer, run_id=run_id)
    except Exception:
        log.warning("memory extraction crashed", exc_info=True)
    return out.to_dict()


@router.get("/runs")
async def list_runs(ctx: Ctx = Depends(require_internal),
                    limit: int = Query(default=30, ge=1, le=100),
                    agent: str | None = None):
    rows = await db.fetch(
        """SELECT id, agent, trigger, status, model, input_tokens, output_tokens,
                  cached_tokens, cost_usd, latency_ms, error, started_at, finished_at,
                  root_run_id, conversation_id
             FROM agent_runs WHERE user_id=$1::uuid AND ($2::text IS NULL OR agent=$2)
             ORDER BY started_at DESC LIMIT $3""",
        ctx.user_id, agent, limit)
    return {"runs": [dict(r) for r in rows]}


@router.get("/runs/{run_id}")
async def run_detail(run_id: str, ctx: Ctx = Depends(require_internal)):
    run = await db.fetchrow(
        """SELECT id, agent, trigger, status, model, input_tokens, output_tokens,
                  cached_tokens, cost_usd, latency_ms, error, started_at, finished_at,
                  root_run_id, conversation_id
             FROM agent_runs WHERE id=$1::uuid AND user_id=$2::uuid""",
        run_id, ctx.user_id)
    if not run:
        raise HTTPException(404, "run not found")
    traces = await db.fetch(
        "SELECT seq, kind, agent, payload, created_at FROM agent_traces "
        "WHERE run_id=$1::uuid ORDER BY seq", run_id)
    return {"run": dict(run), "traces": [dict(t) for t in traces]}
