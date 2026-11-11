"""Read-only operational endpoints for the AI service's own background machinery.

Everything under ``/internal/ops`` carries ``require_internal``: this is a control
plane the backend reaches with the shared internal token, never a public surface.
The read-only health reports here answer two questions that, before Epics 140 and
143, only a ``redis-cli`` session or a log grep could begin to answer: "is the
embed work queue and its dead-letter pipeline actually working?" and "is the RAG
cache actually earning its keep, or has it never been switched on?".

The endpoints add no logic of their own: collection is fail-open in
``app.ops.queue_status`` / ``app.ops.cache_status`` and each verdict is a pure
function in ``app.features.work_queue_health`` / ``cache_health``. Their one job
is auth plus a last-resort catch so that even an unforeseen collection bug
degrades to an *unknown* report rather than a 500 that would look like the
service itself is down.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.core.deps import Ctx, require_internal
from app.ops import cache_status, queue_status

log = logging.getLogger("api.ops")

router = APIRouter(prefix="/internal/ops", tags=["ops"])


@router.get("/workqueue")
async def workqueue_status(ctx: Ctx = Depends(require_internal)) -> dict:
    """One snapshot of the embed work queue: verdict, alerts, and raw readings.

    ``backend=off`` -> ``disabled``; Redis unreachable -> ``unknown``; stale
    consumer -> ``stalled``; dead letters -> ``degraded``; deep PEL ->
    ``backlogged``; otherwise ``healthy``. Always 200 with a well-formed report
    (the verdict, not the HTTP status, carries the health), so a monitor can
    scrape it without treating a degraded queue as a crashed service.
    """
    try:
        return await queue_status.read_status()
    except Exception:
        # Defence in depth: read_status is already total, but a control-plane
        # endpoint must never 500 because an observer had a bad day.
        log.warning("workqueue_status collection escaped fail-open", exc_info=True)
        return {
            "verdict": "unknown",
            "alerts": ["The health observation itself failed; queue state is unknown."],
            "freshness": {"fresh": False, "age_s": None, "last_tick": None,
                          "stale_after_s": 0},
            "queue": {"stream_len": 0, "pending": 0, "dlq_len": 0,
                      "dlq_enabled": False, "ok": False},
            "guard": {"enabled": False, "cooldown_s": 0, "cooled_count": 0},
            "backend": "unknown",
            "observation_error": "endpoint-fallback",
        }


@router.get("/cache")
async def cache_health_status(ctx: Ctx = Depends(require_internal)) -> dict:
    """One snapshot of the RAG cache: verdict, alerts, and the raw counters.

    ``cache_backend=off`` (the shipped default) -> ``off``: the "second question
    is free" optimisation has never run here. Enabled but no lookups -> ``cold``;
    real lookups below the hit-rate line -> ``ineffective``; backend errors or a
    tripped Redis breaker -> ``unknown``; otherwise ``healthy``. Always 200 with a
    well-formed report (the verdict, not the HTTP status, carries the health), so
    a monitor can scrape it without treating an off/ineffective cache as a crash.
    """
    try:
        return cache_status.read_health()
    except Exception:
        # Defence in depth: read_health is already total, but a control-plane
        # endpoint must never 500 because an observer had a bad day.
        log.warning("cache_health_status collection escaped fail-open", exc_info=True)
        return {
            "verdict": "unknown",
            "alerts": ["The cache health observation itself failed; state is unknown."],
            "backend": "unknown",
            "enabled": False,
            "cache": {"lookups": 0, "hits": 0, "misses": 0, "writes": 0,
                      "errors": 0, "evictions": 0, "l2_hits": 0, "hit_rate": 0.0,
                      "breaker_trips": 0},
            "single_flight": {"leaders": 0, "joined": 0, "inflight": 0},
            "thresholds": {"min_lookups": 20, "hit_rate_warn": 0.5},
            "observation_error": "endpoint-fallback",
        }
