"""Read-only operational endpoints for the AI service's own background machinery.

Everything under ``/internal/ops`` carries ``require_internal``: this is a control
plane the backend reaches with the shared internal token, never a public surface.
The read-only health report here is the answer to "is the embed work queue and its
dead-letter pipeline actually working?" -- a question that, before Epic 140, only
a ``redis-cli`` session or a log grep could begin to answer.

The endpoint adds no logic of its own: collection is fail-open in
``app.ops.queue_status.read_status`` and the verdict is a pure function in
``app.features.work_queue_health``. Its one job is auth plus a last-resort catch so
that even an unforeseen collection bug degrades to an *unknown* report rather than
a 500 that would look like the service itself is down.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.core.deps import Ctx, require_internal
from app.ops import queue_status

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
