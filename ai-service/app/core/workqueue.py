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

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.core import backoff, resp

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
    dead_lettered: int = 0  # poison jobs moved out of the PEL into the DLQ
    delayed: int = 0        # failures parked in the delay ZSET (Epic 144; 0 when off)
    promoted: int = 0       # due jobs moved from the delay ZSET back to the stream
    # The ids of jobs that were dead-lettered, read from the item field named by
    # WorkQueue's `id_field` (empty tuple when no id_field is configured). The embed
    # worker uses these to cool the ids down in its DlqGuard so the producer cannot
    # immediately re-inject them. Kept on the stats rather than a callback so the
    # generic queue stays unaware of the guard and the handler stays pure.
    dead_lettered_ids: tuple[str, ...] = ()


class WorkQueue:
    """A consumer group over one Redis stream.

    Parameters are plain values so the whole class is testable against a fake
    ``RespPool`` with no Redis: ``pool`` speaks ``execute(*args)``; ``stream`` is
    the key; ``group`` the consumer group; ``consumer`` this worker's name;
    ``min_idle_ms`` the after-which-a-job-is-presumed-dead visibility timeout;
    ``batch`` the max messages to take per call; ``max_deliveries`` (0 = off) the
    number of deliveries after which a still-failing job is moved to ``dlq_stream``
    instead of being re-claimed forever. ``id_field`` (default empty) names the
    payload field whose value identifies the job; when set, ``drain`` reports the
    ids of dead-lettered jobs in ``ClaimStats.dead_lettered_ids`` so a caller can
    suppress them upstream, without this generic queue knowing about that store.

    ``backoff_base_ms`` (0 = off, the default) enables delayed retries: instead of
    ``XADD``-ing a failed job straight back onto the stream for the next tick to
    re-claim, it is parked in a Redis sorted set ``delay_zset`` (default
    ``<stream>:delayed``) with a score of ``now + full_jitter(attempts)``. ``drain``
    calls ``promote_due`` first each pass to move matured entries back. With the
    default 0 the failure path is byte-for-byte the pre-Epic-144 ``XADD`` path:
    no sorted-set command is ever issued, so existing callers and fakes are inert.
    ``backoff_cap_ms`` bounds the exponential ceiling (see ``app.core.backoff``).
    """

    def __init__(self, pool: resp.RespPool, *, stream: str, group: str, consumer: str,
                 min_idle_ms: int = 60_000, batch: int = 16, maxlen: int = 0,
                 max_deliveries: int = 0, dlq_stream: str = "",
                 id_field: str = "", backoff_base_ms: int = 0,
                 backoff_cap_ms: int = backoff.DEFAULT_CAP_MS,
                 delay_zset: str = "", now_ms: Callable[[], int] | None = None,
                 rng: backoff.Rng | None = None) -> None:
        if min_idle_ms <= 0 or batch <= 0:
            raise ValueError("min_idle_ms and batch must be positive")
        if maxlen < 0:
            raise ValueError("maxlen must be >= 0 (0 disables trimming)")
        if max_deliveries < 0:
            raise ValueError("max_deliveries must be >= 0 (0 disables the DLQ)")
        if max_deliveries and not dlq_stream:
            raise ValueError("max_deliveries needs a dlq_stream to move poison jobs to")
        if backoff_base_ms < 0 or backoff_cap_ms < 0:
            raise ValueError("backoff_base_ms / backoff_cap_ms must be >= 0")
        self.pool = pool
        self.stream = stream
        self.group = group
        self.consumer = consumer
        self.min_idle_ms = min_idle_ms
        self.batch = batch
        self.maxlen = maxlen
        self.max_deliveries = max_deliveries
        self.dlq_stream = dlq_stream
        self.id_field = id_field
        # Epic 144: 0 keeps the old immediate-requeue path. Injected clock/rng keep
        # the whole delay schedule deterministic and offline-testable.
        self.backoff_base_ms = int(backoff_base_ms)
        self.backoff_cap_ms = int(backoff_cap_ms)
        self.delay_zset = delay_zset or f"{stream}:delayed"
        self._now_ms = now_ms or (lambda: int(time.time() * 1000))
        self._rng = rng
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

    # ---------------------------------------------------------- delayed retries (Epic 144)
    async def promote_due(self) -> int:
        """Move matured entries from the delay ZSET back onto the main stream.

        A failed job is parked with score ``now + full_jitter(attempts)``. Once
        that instant passes, its member must return to the stream for ``claim``
        to pick up. This is the promote half, called at the top of every ``drain``
        pass so a matured job costs no extra tick. Returns how many were promoted.

        The move is deliberately TWO non-atomic commands, not a Lua script:

            ZRANGEBYSCORE delay -inf now LIMIT 0 batch   -> matured members
            XADD stream * <fields> ; ZREM delay member   -> per member

        Redis has no transaction spanning a ZSET and a stream, and embedding a Lua
        script would be a second, unauditable implementation of the same protocol
        for the dependency-free transport. The queue's existing at-least-once +
        idempotent-handler contract already covers both failure orders:
        XADD-then-ZREM-fails leaves a duplicate (a cheap no-op SELECT in the embed
        handler); a crash in between replays the same parked job next pass. What
        must NEVER happen is ZREM-before-XADD, which could *drop* a job — hence the
        order here.

        With backoff off this is a zero-command no-op, so the default path stays
        byte-for-byte the pre-Epic-144 behaviour.
        """
        if self.backoff_base_ms <= 0:
            return 0
        now = self._now_ms()
        try:
            members = await self.pool.execute(
                "ZRANGEBYSCORE", self.delay_zset, "-inf", str(now),
                "LIMIT", "0", str(self.batch)) or []
        except (resp.RespUnavailable, resp.RespError, OSError) as e:
            log.warning("work queue promote_due read failed: %s (parked jobs stay put)", e)
            return 0

        promoted = 0
        for member in members:
            raw = member.decode() if isinstance(member, bytes) else str(member)
            try:
                origin_id, payload = raw.split("\x1f", 1)
                fields = json.loads(payload)
                if not isinstance(fields, dict):
                    raise ValueError("payload is not a JSON object")
            except (ValueError, TypeError) as e:
                # A corrupt member would sit at the head of the score range forever
                # and block every later promote. Drop it. At-least-once means the
                # DB's embedding-IS-NULL source of truth re-enqueues any still-live
                # job, so dropping a *record* cannot lose *work*.
                log.error("work queue dropping a corrupt delay member: %s (%s)",
                          raw[:120], e)
                try:
                    # Use the decoded string, not the raw RESP bytes: the member we
                    # wrote via ZADD was a str, and matching on a consistent str
                    # avoids a bytes/str mismatch on transports that decode replies.
                    await self.pool.execute("ZREM", self.delay_zset, raw)
                except (resp.RespUnavailable, resp.RespError, OSError):
                    pass
                continue

            flat: list[Any] = []
            for k, v in fields.items():
                flat.extend((k, v))
            cmd: list[Any] = [self.stream]
            if self.maxlen:
                cmd += ["MAXLEN", "~", str(self.maxlen)]
            try:
                await self.pool.execute("XADD", *cmd, "*", *flat)
            except (resp.RespUnavailable, resp.RespError, OSError) as e:
                # XADD failed: leave the member parked for the next pass. ZREM must
                # never run before a successful XADD, or the job would be lost.
                log.warning("work queue promote XADD failed for %s: %s (stays parked)",
                            origin_id, e)
                continue
            try:
                # `raw` is the decoded member (a str), exactly what ZADD wrote.
                # Passing the decoded form is symmetric with the write and robust
                # to transports that hand back reply bytes.
                await self.pool.execute("ZREM", self.delay_zset, raw)
            except (resp.RespUnavailable, resp.RespError, OSError) as e:
                # Duplicate-later, never loss: the idempotent handler absorbs it.
                log.warning("work queue promote ZREM failed for %s: %s (duplicate "
                            "possible; handler is idempotent)", origin_id, e)
            promoted += 1
        return promoted

    async def delayed_len(self) -> int:
        """Entries parked in the delay ZSET (fail-open, read-only). Off -> 0.

        Non-zero means jobs are inside their backoff window, NOT that they are
        stuck: ``promote_due`` returns them to the stream once ``not_before``
        passes. A *persistently growing* value with a fresh consumer heartbeat is
        the signal an operator watches (a provider is failing repeatedly), and it
        is why the delay set is observable rather than a silent black hole.
        """
        if self.backoff_base_ms <= 0:
            return 0
        try:
            return int(await self.pool.execute("ZCARD", self.delay_zset) or 0)
        except Exception:
            return 0

    async def pending_counts(self) -> dict[str, int]:
        """`{stream_id: delivery_count}` for this group's PEL, from Redis.

        `XPENDING <stream> <group> - + <count>` is the *detailed* form: each row is
        `[id, consumer, idle_ms, delivery_count]`. This is an **observability**
        metric ("how many PEL entries, redelivered how often"), useful for an
        operator watching for stuck jobs.

        It is deliberately **not** the retry/DLQ counter. A live-but-failing worker
        leaves its failed message in *its own* PEL, and XAUTOCLAIM only re-claims
        **other** consumers' orphans — so that message's Redis count stays at 1 no
        matter how many times the handler fails. That is why `drain` maintains an
        explicit ``attempts`` field on re-queued messages for the DLQ decision,
        instead of trusting this number. Counts for messages absent from the PEL
        default to 0; a Redis failure yields an empty dict (fail-open).
        """
        try:
            rows = await self.pool.execute(
                "XPENDING", self.stream, self.group, "-", "+", str(self.batch * 4)) or []
        except (resp.RespUnavailable, resp.RespError, OSError):
            return {}
        out: dict[str, int] = {}
        for row in rows:
            if not isinstance(row, (list, tuple)) or len(row) < 4:
                continue
            sid = row[0].decode() if isinstance(row[0], bytes) else str(row[0])
            try:
                out[sid] = int(row[3])
            except (TypeError, ValueError):
                out[sid] = 0
        return out

    async def drain(self, handler: Callable[[WorkItem], Awaitable[bool]]) -> ClaimStats:
        """Claim, run ``handler`` on each job, ACK the ones it reports success.

        ``handler(item) -> True`` means done (ACK). On failure the message is
        **re-queued**: `XADD` it back to the main stream with an incremented
        ``attempts`` field, then `XACK` the old copy. This explicit retry is
        deliberate, because relying on XAUTOCLAIM for retries has a hole: a worker
        that stays alive but whose handler keeps failing would leave the message in
        *its own* PEL, and XAUTOCLAIM only re-claims **other** consumers' orphans --
        so a poison job could never reach a retry limit. Re-queueing also makes the
        attempt count travel with the message, so it stays correct across a worker
        crash (the orphan XAUTOCLAIM later picks up carries its ``attempts`` field).

        With ``backoff_base_ms`` set (Epic 144), a *non-poison* failure is parked in
        ``delay_zset`` with score ``now + full_jitter(attempts)`` instead of being
        XADD-ed straight back onto the stream. ``promote_due`` at the top of each
        pass returns matured entries to the stream. This spaces out retries so a
        transient provider blip can heal instead of burning all ``max_deliveries``
        within five ticks. With the default 0 the failure path is the original
        immediate-XADD, byte for byte.

        With ``max_deliveries`` set, a job whose re-queued attempt reaches the limit
        is moved to ``dlq_stream`` instead: XADD the DLQ entry **first**, then ACK
        the main-stream copy, so a failed DLQ write leaves it pending (never dropped).
        Backoff never delays a poison job's trip to the DLQ — a known-bad job has
        nothing to wait for. Without a DLQ, ``max_deliveries=0`` keeps the original
        behaviour: a failed job is re-queued (or parked) indefinitely, its attempts
        still visible for an operator.

        Both the retry re-queues and the DLQ adds are trimmed with ``MAXLEN ~ maxlen``.
        That matters because the DB (``embedding IS NULL``) is the source of truth: a
        producer that re-injects a still-NULL poison job every tick starts a *fresh*
        ``attempts=0`` lineage, so without a DLQ cap a permanently-bad row would grow
        the dead-letter stream without bound. Trimming a dead-letter drops only its
        *record* — the still-NULL row is re-enqueued by the next producer pass, so no
        job is permanently lost. (Suppressing that re-injection entirely is a
        producer-side decision, deliberately kept out of this generic queue.)
        """
        await self.ensure_group()
        # Epic 144: return any matured parked jobs to the stream BEFORE claiming,
        # so they are eligible in this same pass. Off => zero-command no-op.
        promoted = await self.promote_due()
        items = await self.claim()
        acked: list[str] = []
        dead_lettered = 0
        dead_lettered_ids: list[str] = []
        delayed = 0
        failed = 0
        for item in items:
            try:
                ok = await handler(item)
            except Exception:
                log.warning("work queue handler raised for %s; will retry", item.stream_id,
                            exc_info=True)
                ok = False
            if ok:
                acked.append(item.stream_id)
                continue
            try:
                attempts = int(item.value("attempts", "0")) + 1
            except (TypeError, ValueError):
                attempts = 1
            poison = bool(self.max_deliveries and attempts >= self.max_deliveries)
            target = self.dlq_stream if poison else self.stream
            fields = dict(item.fields)
            fields["attempts"] = str(attempts)
            if poison:
                fields.update({
                    "origin_stream": self.stream,
                    "origin_id": item.stream_id,
                    "dlq_at": str(int(time.time())),
                })
            # Epic 144: a NON-poison failure with backoff on is parked in the delay
            # ZSET instead of being XADD-ed straight back. It stays out of the main
            # stream (so `XREADGROUP >` cannot re-claim it) until `not_before`.
            # Poison jobs deliberately skip this: a known-bad job has nothing to
            # wait for, and the DLQ + DlqGuard cooldown already pace it.
            if not poison and self.backoff_base_ms > 0:
                payload = json.dumps(fields, sort_keys=True, separators=(",", ":"))
                member = f"{item.stream_id}\x1f{payload}"
                delay = backoff.full_jitter_ms(
                    attempts, base_ms=self.backoff_base_ms,
                    cap_ms=self.backoff_cap_ms, rng=self._rng)
                not_before = self._now_ms() + delay
                try:
                    await self.pool.execute(
                        "ZADD", self.delay_zset, str(not_before), member)
                except (resp.RespUnavailable, resp.RespError, OSError) as e:
                    # Park failed: leave the message pending so XAUTOCLAIM can
                    # recover it. Never ACK; a lost park would lose the retry.
                    log.warning("work queue delay ZADD failed for %s: %s (stays pending)",
                                item.stream_id, e)
                    failed += 1
                    continue
                # Park succeeded: the old copy can leave the PEL; the retry now
                # lives in the delay set, not on the stream.
                acked.append(item.stream_id)
                delayed += 1
                continue
            flat: list[Any] = []
            for k, v in fields.items():
                flat.extend((k, v))
            try:
                cmd: list[Any] = [target]
                # Bound the stream we write to, whether it is the main retry stream
                # or the DLQ. A poison job re-injected by the producer each tick
                # would otherwise grow the DLQ forever (see the drain docstring).
                if self.maxlen:
                    cmd += ["MAXLEN", "~", str(self.maxlen)]
                await self.pool.execute("XADD", *cmd, "*", *flat)
            except (resp.RespUnavailable, resp.RespError, OSError) as e:
                # Re-queue / DLQ write failed: leave the message pending so the
                # PEL still holds it and XAUTOCLAIM can recover it. Never ACK.
                log.warning("work queue retry XADD failed for %s: %s (stays pending)",
                            item.stream_id, e)
                failed += 1
                continue
            acked.append(item.stream_id)  # old copy leaves the PEL; new copy is queued
            if poison:
                dead_lettered += 1
                if self.id_field:
                    jid = item.value(self.id_field)
                    if jid:
                        dead_lettered_ids.append(jid)
                log.error("work queue job %s dead-lettered after %d attempts",
                          item.stream_id, attempts)
            # A re-queued job is still in the system, just back on the stream; it is
            # not counted as a failure here because the retry itself succeeded.
        ack_count = 0
        if acked:
            try:
                ack_count = await self.ack(*acked)
            except (resp.RespUnavailable, resp.RespError, OSError) as e:
                log.warning("work queue ACK failed for %d jobs: %s (they stay pending; "
                            "a duplicate re-queue is harmless to an idempotent handler)",
                            len(acked), e)
        return ClaimStats(delivered=len(items), reclaimed=0,
                          ack_failed=len(acked) - ack_count + failed,
                          dead_lettered=dead_lettered,
                          dead_lettered_ids=tuple(dead_lettered_ids),
                          delayed=delayed, promoted=promoted)

    async def pending(self) -> int:
        """Best-effort PEL length for this group (observability)."""
        try:
            rows = await self.pool.execute("XPENDING", self.stream, self.group) or []
            # XPENDING summary: [count, min_id, max_id, consumers]
            return int(rows[0]) if rows else 0
        except Exception:
            return 0

    # ------------------------------------------------------------ observation
    # Everything below is READ-ONLY and fail-open. An observer must never change
    # consumer state (no XREADGROUP, no XACK) and a Redis outage must read as
    # "unknown", never raise into the request that is trying to report on it.

    async def _xlen(self, key: str) -> int:
        """``XLEN key`` -> row count, or 0 on any Redis failure (fail-open)."""
        if not key:
            return 0
        try:
            return int(await self.pool.execute("XLEN", key) or 0)
        except Exception:
            return 0

    async def queue_len(self) -> int:
        """Entries currently on the main stream (fail-open, read-only).

        A non-zero value is *not* automatically a backlog: re-queued retries and
        the producer's per-tick re-injection both leave entries on the stream that
        a consumer has already ACKed (``XACK`` removes from the PEL, not the
        stream). Read this alongside ``pending()``: the PEL is the real "work not
        yet done" signal; the stream length is "messages retained", which the
        ``MAXLEN ~`` trim bounds.
        """
        return await self._xlen(self.stream)

    async def dlq_len(self) -> int:
        """Entries on the dead-letter stream (fail-open, read-only).

        0 when no DLQ is configured. This is the number an operator alerts on:
        a growing DLQ means jobs are failing past ``max_deliveries`` and being
        suppressed by the DlqGuard's cooldown until a human looks at them.
        """
        return await self._xlen(self.dlq_stream)

    async def snapshot(self) -> dict[str, int | bool]:
        """One coherent, read-only read of this queue's observable state.

        Returns a plain dict so it can cross the JSON/HTTP boundary and be folded
        into the pure-function health report without carrying a Redis client:

        ``stream_len``     — entries retained on the main stream (``XLEN``).
        ``pending``        — entries in this group's PEL (``XPENDING`` summary).
        ``dlq_len``        — entries on the dead-letter stream (``XLEN``).
        ``dlq_enabled``    — whether a DLQ is configured at all.
        ``delayed_len``    — jobs parked in the backoff ZSET (``ZCARD``; Epic 144).
        ``delayed_enabled``— whether backoff is on at all.
        ``ok``             — whether **all** reads succeeded.

        ``delayed_len`` is important for honesty: a parked job is on *none* of the
        stream / PEL / DLQ, so without this reading a growing delay set would be a
        silent black hole — the queue would look healthy while work waited out its
        backoff. Non-zero is not itself unhealthy (it is the expected cost of
        spacing retries); a persistent climb with a fresh heartbeat is the signal.
        With backoff off, ``delayed_enabled=False`` and no ``ZCARD`` is issued, so
        pre-Epic-144 observers see an unchanged command set.

        ``ok`` is the honest part. A fail-open 0 is indistinguishable from a
        genuinely empty queue, so an observer that only returned zeroes could not
        tell "Redis is down" from "nothing is pending" — and would report a dead
        queue as healthy. Each numeric field still degrades to 0 independently
        (fail-open), but any failure flips ``ok`` to False so the health report can
        say *unknown* instead of *healthy*. This never creates a consumer group
        and never claims or ACKs a job.
        """
        async def _observe(awaitable) -> tuple[int, bool]:
            """One int-valued reading -> (value, succeeded); failure degrades to 0."""
            try:
                return int(await awaitable), True
            except Exception:
                return 0, False

        async def _xlen(key: str) -> tuple[int, bool]:
            if not key:
                return 0, True  # no DLQ configured is a valid, known state
            return await _observe(self.pool.execute("XLEN", key))

        async def _pending() -> tuple[int, bool]:
            async def read() -> int:
                try:
                    rows = await self.pool.execute(
                        "XPENDING", self.stream, self.group) or []
                except resp.RespError as e:
                    # A queue that has never been consumed has no group yet, and
                    # Redis answers NOGROUP. That is a *known* state (nothing is
                    # pending), not a failed read: treating it as ok=False would
                    # make every freshly deployed queue report "unknown" until the
                    # first job arrives. Any other RESP error still fails open.
                    if "NOGROUP" in str(e).upper():
                        return 0
                    raise
                return int(rows[0]) if rows else 0
            return await _observe(read())

        async def _delayed() -> tuple[int, bool]:
            # Backoff off is a known state, not a failed read: return 0 WITHOUT a
            # ZCARD so an off queue issues exactly the pre-Epic-144 command set.
            if self.backoff_base_ms <= 0:
                return 0, True
            return await _observe(self.pool.execute("ZCARD", self.delay_zset))

        # Independent reads; asyncio.gather keeps the observer to one event-loop
        # round-trip instead of summing network latencies. Each degrades on its own
        # so a partial failure blanks one number, not the whole report.
        (stream_len, ok1), (pending, ok2), (dlq_len, ok3), (delayed_len, ok4) = \
            await asyncio.gather(
                _xlen(self.stream), _pending(), _xlen(self.dlq_stream), _delayed(),
            )
        return {
            "stream_len": stream_len,
            "pending": pending,
            "dlq_len": dlq_len,
            "dlq_enabled": bool(self.dlq_stream),
            "delayed_len": delayed_len,
            "delayed_enabled": self.backoff_base_ms > 0,
            "ok": ok1 and ok2 and ok3 and ok4,
        }
