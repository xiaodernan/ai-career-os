"""A Redis-Streams work queue: at-least-once job delivery with crash recovery.

This is a *work queue*, not a pub/sub fan-out. The distinction matters and is easy
to get wrong:

* ``taskbus`` is a **broadcast** — every browser subscribing to a task must see
  every progress event, so it uses plain ``XADD`` + ``XREAD`` and deliberately has
  no consumer group (a consumer group would deliver each event to only one reader
  and break SSE).
* This module is a **work queue** — a job such as "embed job <uuid>" must be done
  by exactly one worker, and if that worker dies mid-job another must pick it up.
  That is what a Redis consumer group is for.

The contract, stated honestly:

* **At-least-once, not exactly-once.** A worker that finishes a job but crashes
  before ``XACK`` leaves the message pending; ``XAUTOCLAIM`` will hand it to
  another worker, so the job runs twice. The handler *must be idempotent*. The
  embed handler is: ``UPDATE jobs SET embedding = .. WHERE id = $1`` converges,
  and the worker re-checks ``embedding IS NULL`` before spending a model call.
  Exactly-once would need a transaction spanning Redis + the embedding provider
  + Postgres, which does not exist; at-least-once + idempotence is the honest,
  standard answer.
* **Crash recovery via a visibility timeout.** ``XREADGROUP`` delivers a message
  into the consumer's PEL (pending entries list). If it is not ACKed within
  ``min_idle_ms``, ``XAUTOCLAIM`` moves it to another consumer. A healthy job
  longer than that timeout may be claimed twice — hence idempotence, again. The
  timeout is an operator-tuned upper bound on job duration, not a guarantee.
* **Fail-open.** The queue is an optimisation over the database-as-source-of-
  truth (``embedding IS NULL``). If Redis is unavailable the caller falls back to
  its own scan; the queue never makes a job un-processable.

Everything speaks RESP2 through the dependency-free `app.core.resp` pool already
used by the cache and the task bus. No new dependency, no new infrastructure.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.core import resp

log = logging.getLogger(__name__)

XGROUP_CREATE = ("XGROUP", "CREATE")


@dataclass(frozen=True)
class WorkItem:
    """A claimed message: its stream id (for ACK) and its payload fields."""

    stream_id: str
    fields: dict[str, str]

    def value(self, key: str, default: str = "") -> str:
        return self.fields.get(key, default)


@dataclass(frozen=True)
class ClaimStats:
    """What one drain pass did — useful for logs and for the tests."""

    delivered: int = 0      # fresh XREADGROUP deliveries
    reclaimed: int = 0      # recovered from another consumer's PEL
    ack_failed: int = 0


class WorkQueue:
    """A consumer group over one Redis stream.

    Parameters are plain values so the whole class is testable against a fake
    ``RespPool`` with no Redis: ``pool`` speaks ``execute(*args)``; ``stream`` is
    the key; ``group`` the consumer group; ``consumer`` this worker's name;
    ``min_idle_ms`` the after-which-a-job-is-presumed-dead visibility timeout;
    ``batch`` the max messages to take per call.
    """

    def __init__(self, pool: resp.RespPool, *, stream: str, group: str, consumer: str,
                 min_idle_ms: int = 60_000, batch: int = 16, maxlen: int = 0) -> None:
        if min_idle_ms <= 0 or batch <= 0:
            raise ValueError("min_idle_ms and batch must be positive")
        if maxlen < 0:
            raise ValueError("maxlen must be >= 0 (0 disables trimming)")
        self.pool = pool
        self.stream = stream
        self.group = group
        self.consumer = consumer
        self.min_idle_ms = min_idle_ms
        self.batch = batch
        self.maxlen = maxlen
        self._group_ready = False

    # -------------------------------------------------------------- wire helpers
    @staticmethod
    def _fields(entry_id: Any, fields: Any) -> tuple[str, dict[str, str]]:
        sid = entry_id.decode() if isinstance(entry_id, bytes) else str(entry_id)
        flat = list(fields or [])
        decoded: dict[str, str] = {}
        for i in range(0, len(flat) - 1, 2):
            k, v = flat[i], flat[i + 1]
            key = k.decode() if isinstance(k, bytes) else str(k)
            val = v.decode() if isinstance(v, bytes) else str(v)
            decoded[key] = val
        return sid, decoded

    @staticmethod
    def _entries(rows: Any) -> list[tuple[Any, Any]]:
        """Normalise the nested XREADGROUP / XAUTOCLAIM shape to entry pairs."""
        if not rows:
            return []
        first = rows[0]
        # XREADGROUP: [[stream_key, [[id, fields], ...]]]
        if isinstance(first, (list, tuple)) and len(first) == 2 and isinstance(first[1], (list, tuple)):
            entries = first[1]
        else:
            # XAUTOCLAIM: [next_start_id, [[id, fields], ...]] -- sometimes 3-tuple
            # with a list of deleted ids appended; the entries are the list of pairs.
            entries = rows[1] if len(rows) > 1 else []
        return [e for e in (entries or []) if isinstance(e, (list, tuple)) and len(e) >= 2]

    # -------------------------------------------------------------- group setup
    async def ensure_group(self, *, start_id: str = "0") -> None:
        """Create the group if absent. ``MKSTREAM`` makes an empty stream legal.

        ``BUSYGROUP`` means another worker created it first — the normal, expected
        race at startup, not an error. Any other RESP error propagates to the
        caller's fail-open handler.
        """
        if self._group_ready:
            return
        try:
            await self.pool.execute("XGROUP", "CREATE", self.stream, self.group,
                                    start_id, "MKSTREAM")
        except resp.RespError as e:
            if "BUSYGROUP" not in str(e):
                raise
        self._group_ready = True

    # -------------------------------------------------------------- produce
    async def enqueue(self, fields: dict[str, str]) -> str:
        """``XADD`` one job. Returns the stream id (used by tests / tracing).

        With ``maxlen`` set, the `XADD` is ``MAXLEN ~ N``: Redis trims older
        entries approximately (cheap, not an exact cut), so a long-lived producer
        cannot grow the stream without bound. A job trimmed before a consumer
        claims it is simply re-enqueued by the next producer pass — the DB's
        ``embedding IS NULL`` remains the source of truth, so trimming can never
        lose a job permanently.

        The caller decides dedup (e.g. only enqueue a job id once). This queue
        intentionally does not: at-least-once means duplicate enqueues are safe
        for an idempotent handler, and a dedup index would be a second source of
        truth to keep coherent.
        """
        flat: list[Any] = []
        for k, v in fields.items():
            flat.extend((k, v))
        prefix: list[Any] = ([self.stream, "MAXLEN", "~", str(self.maxlen), "*"]
                             if self.maxlen else [self.stream, "*"])
        sid = await self.pool.execute("XADD", *prefix, *flat)
        # Redis replies in bytes; hand the caller the same str shape as
        # WorkItem.stream_id so ids can be compared/logged without decoding.
        return sid.decode() if isinstance(sid, bytes) else str(sid)

    # -------------------------------------------------------------- consume
    async def claim(self) -> list[WorkItem]:
        """Take up to ``batch`` jobs: fresh deliveries first, then claimed orphans.

        Fresh jobs come from ``XREADGROUP`` (``>`` = not-yet-delivered to anyone).
        Orphans come from ``XAUTOCLAIM``: messages sitting in *any* consumer's PEL
        longer than ``min_idle_ms``. Combining both in one call is what gives a
        single ``claim()`` the two behaviours a worker needs each tick.
        """
        await self.ensure_group()
        out: list[WorkItem] = []
        rows = await self.pool.execute(
            "XREADGROUP", "GROUP", self.group, self.consumer, "COUNT", str(self.batch),
            "STREAMS", self.stream, ">")
        for entry_id, fields in self._entries(rows):
            sid, decoded = self._fields(entry_id, fields)
            out.append(WorkItem(sid, decoded))

        if len(out) < self.batch:
            claimed = await self.pool.execute(
                "XAUTOCLAIM", self.stream, self.group, self.consumer,
                str(self.min_idle_ms), "0-0", "COUNT", str(self.batch - len(out)))
            for entry_id, fields in self._entries(claimed):
                sid, decoded = self._fields(entry_id, fields)
                out.append(WorkItem(sid, decoded))
        return out

    async def ack(self, *stream_ids: str) -> int:
        """Acknowledge completed jobs. Returns how many ids were acked."""
        if not stream_ids:
            return 0
        return int(await self.pool.execute("XACK", self.stream, self.group, *stream_ids) or 0)

    async def drain(self, handler: Callable[[WorkItem], Awaitable[bool]]) -> ClaimStats:
        """Claim, run ``handler`` on each job, ACK the ones it reports success.

        ``handler(item) -> True`` means done (ACK). ``False`` / an exception leaves
        the message pending, so the next ``min_idle_ms`` cycle re-claims it. The
        drain never lets one bad job stop the others: a failing handler is logged
        and its message left for recovery, which is the point of a PEL.
        """
        await self.ensure_group()
        items = await self.claim()
        acked: list[str] = []
        failed = 0
        for item in items:
            try:
                ok = await handler(item)
            except Exception:
                log.warning("work queue handler raised for %s; leaving pending", item.stream_id,
                            exc_info=True)
                ok = False
            if ok:
                acked.append(item.stream_id)
            else:
                failed += 1
        ack_count = 0
        if acked:
            try:
                ack_count = await self.ack(*acked)
            except (resp.RespUnavailable, resp.RespError, OSError) as e:
                log.warning("work queue ACK failed for %d jobs: %s (will be re-claimed)",
                            len(acked), e)
        return ClaimStats(delivered=len(items), reclaimed=0,
                          ack_failed=len(acked) - ack_count + failed)

    async def pending(self) -> int:
        """Best-effort PEL length for this group (observability)."""
        try:
            rows = await self.pool.execute("XPENDING", self.stream, self.group) or []
            # XPENDING summary: [count, min_id, max_id, consumers]
            return int(rows[0]) if rows else 0
        except Exception:
            return 0
