"""Persistence helpers for observability: usage events, agent runs, trace steps."""

import logging
import uuid
from typing import Any

import asyncpg

from app.core import db

log = logging.getLogger("db.observability")


async def _best_effort(what: str, awaitable) -> None:
    """Await a telemetry write, logging instead of raising.

    Traces and usage rows *observe* a request; a failure to record one must never fail
    the request itself. `trace()` is awaited on every step of every copilot turn --
    including from `_exec_tool`, where a failed INSERT on `agent_traces` aborted a turn
    that had already produced its answer -- and `finish_run` is called from `except`
    handlers, where raising replaced the original exception with the telemetry error.
    Both are the observer breaking the observed. Writes that are load-bearing
    (`create_run` returns the id every later write needs) deliberately do not use this.
    """
    try:
        await awaitable
    except Exception as e:
        log.warning("%s failed (telemetry, not raised): %s", what, e)


async def record_usage(user_id: str | None, run_id: str | None, model: str, provider: str,
                       kind: str, in_tok: int, out_tok: int, cached: int, cost: float,
                       latency_ms: int) -> None:
    if not user_id:
        return
    await _best_effort("record_usage", db.execute(
        """INSERT INTO ai_usage_events(user_id, run_id, model, provider, kind,
               input_tokens, output_tokens, cached_tokens, cost_usd, latency_ms)
           VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7, $8, $9, $10)""",
        user_id, run_id, model, provider, kind, in_tok, out_tok, cached, cost, latency_ms))


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


RUN_USAGE_SQL = """SELECT coalesce(sum(input_tokens), 0), coalesce(sum(output_tokens), 0),
       coalesce(sum(cached_tokens), 0), coalesce(sum(cost_usd), 0)
  FROM ai_usage_events WHERE run_id = $1::uuid"""


async def _usage_of(run_id: str) -> tuple[int, int, int, float]:
    """The totals a run's own LLM calls already recorded.

    Most callers finish a run with only a latency (the copilot turn — the priciest path in the
    product, up to eight model calls — never passes tokens at all), which left agent_runs'
    rollup columns at zero while ai_usage_events held the real usage. The dashboard and the
    activity page read the rollup, so they displayed a free-looking run that cost thousands of
    tokens. Deriving it here means the number cannot be forgotten.
    """
    row = await db.fetchrow(RUN_USAGE_SQL, run_id)
    if not row:
        return 0, 0, 0, 0.0
    return int(row[0]), int(row[1]), int(row[2]), float(row[3])


async def finish_run(run_id: str, status: str, in_tok: int = 0, out_tok: int = 0,
                     cached: int = 0, cost: float = 0.0, latency_ms: int = 0,
                     error: str | None = None) -> None:
    # First terminal write wins. Every total below is `col = col + $n`, so a second finish
    # of the same run would bill and time it twice — and the one caller that finishes
    # 'completed' inside a try and 'failed' in its except makes that reachable.
    # A caller that supplies any usage figure owns all of them; passing one and leaving the
    # rest to the ledger would double-count the one it named.
    try:
        if not (in_tok or out_tok or cached or cost):
            in_tok, out_tok, cached, cost = await _usage_of(run_id)
        await db.execute(
            """UPDATE agent_runs SET status=$2, input_tokens=input_tokens+$3,
                   output_tokens=output_tokens+$4, cached_tokens=cached_tokens+$5,
                   cost_usd=cost_usd+$6, latency_ms=latency_ms+$7, error=$8, finished_at=now()
               WHERE id=$1::uuid AND status NOT IN ('completed','failed')""",
            run_id, status, in_tok, out_tok, cached, cost, latency_ms, error)
    except Exception as e:
        # Finalising a run is telemetry, and this is called from `except` handlers:
        # raising here would replace the error that actually failed the request.
        log.warning("finish_run failed for %s (telemetry, not raised): %s", run_id, e)


_trace_seq: dict[str, int] = {}


async def trace(run_id: str | None, kind: str, agent: str,
                payload: dict[str, Any]) -> None:
    if not run_id:
        return
    seq = _trace_seq.get(run_id, 0) + 1
    _trace_seq[run_id] = seq
    await _best_effort("trace", db.execute(
        """INSERT INTO agent_traces(run_id, seq, kind, agent, payload)
           VALUES ($1::uuid, $2, $3, $4, $5::jsonb)""",
        run_id, seq, kind, agent, db.jsonb(payload)))


async def get_run(run_id: str) -> asyncpg.Record | None:
    return await db.fetchrow("SELECT * FROM agent_runs WHERE id=$1::uuid", run_id)


def release_trace_seq(run_id: str) -> None:
    _trace_seq.pop(run_id, None)
