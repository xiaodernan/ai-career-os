"""Persistence helpers for observability: usage events, agent runs, trace steps."""

import uuid
from typing import Any

import asyncpg

from app.core import db


async def record_usage(user_id: str | None, run_id: str | None, model: str, provider: str,
                       kind: str, in_tok: int, out_tok: int, cached: int, cost: float,
                       latency_ms: int) -> None:
    if not user_id:
        return
    await db.execute(
        """INSERT INTO ai_usage_events(user_id, run_id, model, provider, kind,
               input_tokens, output_tokens, cached_tokens, cost_usd, latency_ms)
           VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7, $8, $9, $10)""",
        user_id, run_id, model, provider, kind, in_tok, out_tok, cached, cost, latency_ms)


async def create_run(user_id: str, agent: str, trigger: str, model: str = "",
                     root_run_id: str | None = None,
                     conversation_id: str | None = None) -> str:
    run_id = str(uuid.uuid4())
    await db.execute(
        """INSERT INTO agent_runs(id, user_id, root_run_id, conversation_id, agent, trigger,
               status, model)
           VALUES ($1::uuid, $2::uuid, $3::uuid, $4::uuid, $5, $6, 'running', $7)""",
        run_id, user_id, root_run_id, conversation_id, agent, trigger, model)
    return run_id


async def finish_run(run_id: str, status: str, in_tok: int = 0, out_tok: int = 0,
                     cached: int = 0, cost: float = 0.0, latency_ms: int = 0,
                     error: str | None = None) -> None:
    await db.execute(
        """UPDATE agent_runs SET status=$2, input_tokens=input_tokens+$3,
               output_tokens=output_tokens+$4, cached_tokens=cached_tokens+$5,
               cost_usd=cost_usd+$6, latency_ms=latency_ms+$7, error=$8, finished_at=now()
           WHERE id=$1::uuid""",
        run_id, status, in_tok, out_tok, cached, cost, latency_ms, error)


_trace_seq: dict[str, int] = {}


async def trace(run_id: str | None, kind: str, agent: str,
                payload: dict[str, Any]) -> None:
    if not run_id:
        return
    seq = _trace_seq.get(run_id, 0) + 1
    _trace_seq[run_id] = seq
    await db.execute(
        """INSERT INTO agent_traces(run_id, seq, kind, agent, payload)
           VALUES ($1::uuid, $2, $3, $4, $5::jsonb)""",
        run_id, seq, kind, agent, db.jsonb(payload))


async def get_run(run_id: str) -> asyncpg.Record | None:
    return await db.fetchrow("SELECT * FROM agent_runs WHERE id=$1::uuid", run_id)


def release_trace_seq(run_id: str) -> None:
    _trace_seq.pop(run_id, None)
