"""Fail-open collection for the read-only work-queue health endpoint (Epic 140).

``read_status()`` is the single seam between the HTTP layer and the two worlds the
verdict needs: live Redis (stream / PEL / DLQ / cooldown depth) and the consumer's
in-memory heartbeat. It returns the exact dict ``work_queue_health.health_report``
produces, so the endpoint adds nothing but auth, and a future backend scraper folds
the same numbers into a Micrometer gauge.

Design constraints honoured here:

* **Single source of truth for config.** Which stream / group / DLQ / guard key to
  observe comes from ``embed_workers._queue`` / ``_guard`` -- the *same* factories
  the running loop uses -- not from a second copy that could drift. ``mode`` is
  read straight from ``Settings.work_queue_backend`` (one author).
* **A short-lived pool, never the loop's.** The consumer owns its pool's lifetime;
  a reader builds its own from config and closes it in ``finally``. The endpoint is
  a low-frequency operator call, not a hot path, so one connect per read is fine.
* **Total fail-open.** Redis down, a bad URL, a RESP error, an unexpected exception
  -- every path returns a well-formed *unknown* report, never raises into the
  request. An observer that can 500 is an observer that can take down the service
  it is meant to watch. When ``mode != redis`` it does not touch Redis at all and
  reports *disabled*.
"""

from __future__ import annotations

import logging
import time

from app.core.config import get_settings
from app.features import work_queue_health as health
from app.ops import embed_workers, queue_observer
from app.core import resp

log = logging.getLogger("ops.queue_status")


def _unknown_report(mode: str, *, reason: str = "redis-unavailable") -> dict:
    """A well-formed report whose snapshot says 'we could not read Redis'."""
    report = health.health_report(
        {"ok": False, "stream_len": 0, "pending": 0, "dlq_len": 0,
         "dlq_enabled": False, "delayed_len": 0, "delayed_enabled": False},
        {"enabled": False, "cooldown_s": 0, "cooled_count": 0},
        queue_observer.snapshot_heartbeat(),
        mode=mode, now=time.time(),
        stale_after_s=_stale_s(), backlog_warn=_backlog_warn())
    report["observation_error"] = reason
    return report


def _stale_s() -> int:
    try:
        return max(1, int(getattr(get_settings(), "work_queue_health_stale_s", 300) or 300))
    except (TypeError, ValueError):
        return 300


def _backlog_warn() -> int:
    try:
        return max(1, int(getattr(get_settings(), "work_queue_health_backlog_warn", 32) or 32))
    except (TypeError, ValueError):
        return 32


async def read_status() -> dict:
    """Collect live + heartbeat readings and return the health report dict.

    Completely fail-open: the only way this raises is a bug in the pure health
    function itself, which the endpoint still catches as a last resort.
    """
    settings = get_settings()
    mode = str(getattr(settings, "work_queue_backend", "off") or "off").strip().lower()

    # A queue that is configured off has no consumer to be stale and no Redis
    # state to read. Report "disabled" without opening a connection.
    if mode != "redis":
        return health.health_report(
            {"ok": True, "stream_len": 0, "pending": 0, "dlq_len": 0,
             "dlq_enabled": False, "delayed_len": 0, "delayed_enabled": False},
            {"enabled": False, "cooldown_s": 0, "cooled_count": 0},
            queue_observer.snapshot_heartbeat(), mode=mode,
            now=time.time(), stale_after_s=_stale_s(),
            backlog_warn=_backlog_warn())

    pool: resp.RespPool | None = None
    try:
        pool = await embed_workers._redis_pool()
        if pool is None:
            return _unknown_report(mode, reason="redis-pool-unavailable")

        queue = embed_workers._queue(pool)
        guard = embed_workers._guard(pool)
        snapshot = await queue.snapshot()
        guard_readout = {
            "enabled": bool(guard.enabled),
            "cooldown_s": int(getattr(guard, "cooldown_s", 0) or 0),
            "cooled_count": await guard.size(),
        }
        report = health.health_report(
            snapshot, guard_readout, queue_observer.snapshot_heartbeat(),
            mode=mode, now=time.time(),
            stale_after_s=_stale_s(), backlog_warn=_backlog_warn())
        if not report["queue"]["ok"]:
            report["observation_error"] = "redis-read-failed"
        return report
    except (resp.RespUnavailable, resp.RespError, OSError) as e:
        log.warning("work queue health read failed (%s); reporting unknown", e)
        return _unknown_report(mode, reason="redis-error")
    except Exception as e:
        # The observer must never propagate. Even an unexpected bug (a bad stat,
        # a cancelled pipeline, a future refactor) degrades to "unknown", which is
        # the honest answer when we cannot vouch for the numbers.
        log.warning("work queue health observation raised; reporting unknown", exc_info=True)
        return _unknown_report(mode, reason=f"unexpected:{type(e).__name__}")
    finally:
        if pool is not None:
            try:
                await pool.close()
            except Exception:
                log.debug("closing the observation pool failed (already closing)")
