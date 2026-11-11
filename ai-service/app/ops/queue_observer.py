"""In-memory observer registry for the running embed work-queue loop (Epic 140).

Why a registry at all
---------------------
The health report needs two kinds of truth that live in different places:

* **live Redis state** (stream / PEL / DLQ depth, cooldown size) -- read on demand
  by the status endpoint through a short-lived pool built from config;
* **consumer liveness** -- which lives *only* in the loop itself. An idle Redis
  stream looks the same whether a healthy worker just drained it or the worker
  died an hour ago. The loop stamps a heartbeat each tick; the endpoint reads it.

The registry is that second half: a tiny, single-writer, module-level slot the
consumer loop writes to and the read-only endpoint reads from. It deliberately
stores **no Redis connection** -- the loop owns its pool's lifetime (closing it in
``finally``), so a reader must not hold a reference to it. Connection
construction stays in the caller, from config, via ``embed_workers._redis_pool``.

It also stores **no mode**: whether the queue is enabled is a fact owned by
``Settings.work_queue_backend``, read directly by the endpoint. Keeping one author
for that fact means a ``backend=off`` deployment reports "disabled" without any
heartbeat, and a ``backend=redis`` deployment with a stale heartbeat reports
"stalled" -- no ambiguous mode flag that could disagree with the config.

Everything here is fail-open and total: a missing heartbeat is a valid state
("never ticked"), never an exception. This is an observer; it must be incapable
of breaking the loop it is observing. The GIL plus the loop's single serial
``while`` make the plain module dict a sufficient store -- no lock, no plumbing.
"""

from __future__ import annotations

import time
from typing import Any

# Written by embed_loop_distributed once per tick; read by the ops endpoint.
_heartbeat: dict[str, Any] | None = None


def record_tick(*, delivered: int = 0, reclaimed: int = 0, dead_lettered: int = 0,
                now: float | None = None) -> None:
    """Stamp one completed pass. Called by the consumer loop only.

    Holds **liveness + last-tick throughput only**. The current cooldown/DLQ
    counts are deliberately NOT here: they are read live from Redis by the
    endpoint (``guard.size()`` / ``queue.snapshot()``), so there is exactly one
    author for each number and a stale heartbeat cannot disagree with a fresh
    Redis read.

    ``now`` is injectable for tests; production uses ``time.time()`` (wall clock,
    because the health report compares it to an endpoint's wall clock, not a
    monotonic timer that would be meaningless across processes).
    """
    global _heartbeat
    _heartbeat = {
        "last_tick": time.time() if now is None else now,
        "delivered": max(0, int(delivered or 0)),
        "reclaimed": max(0, int(reclaimed or 0)),
        "dead_lettered": max(0, int(dead_lettered or 0)),
    }


def snapshot_heartbeat() -> dict[str, Any] | None:
    """A copy of the last tick, or None if the loop has never reported one.

    Returned as a copy so a reader cannot mutate the loop's slot.
    """
    return dict(_heartbeat) if _heartbeat else None


def reset() -> None:
    """Clear the heartbeat. For tests and for a loop restart."""
    global _heartbeat
    _heartbeat = None
