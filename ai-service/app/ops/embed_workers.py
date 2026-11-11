"""Distributed job embedding over a Redis work queue (Epic 136).

The problem this solves
-----------------------
`embed_loop` sweeps `jobs WHERE embedding IS NULL` on **every replica**. With three
replicas that is the same batch embedded three times -- three model calls, three
bills, three writes racing to the same rows -- and a replica that dies mid-batch
simply leaves its share for the next tick (if it ever comes back). The `embedding
IS NULL` predicate is an idempotence *barrier*, not a *claim*: two readers can both
see NULL before either writes.

`work_queue_backend=redis` changes the coordination without changing the source of
truth. The DB (`embedding IS NULL`) remains authoritative; Redis only decides
*which worker does which job*:

* a **producer** pass selects the ids of jobs still needing a vector and `XADD`s
  them (one message per job, fields carry `job_id`);
* **consumers** on each replica `XREADGROUP` a batch, embed their share, write the
  vector, and `XACK`;
* a consumer that crashes before ACK leaves the message in the PEL; after
  `work_queue_claim_ms`, `XAUTOCLAIM` hands it to a live consumer.

Why this is safe (and where it is not)
--------------------------------------
At-least-once: a message may be delivered twice (finish-then-crash-before-ACK). The
handler is therefore idempotent in two ways -- it re-checks `embedding IS NULL`
under the row's UPDATE, and the UPDATE itself converges. A re-claimed job that was
already written costs one cheap `SELECT`, not a second embedding call.

Producer enqueue is also intentionally at-least-once: it may `XADD` the same job id
twice across ticks (no dedup index -- that would be a second truth to keep
coherent). Duplicate messages are harmless for the same reason. The stream is
trimmed with `MAXLEN ~` so a long-lived deployment cannot grow it without bound.

`work_queue_backend=off` (default) keeps `embed_loop` byte-for-byte as it was: one
process scanning the table, no Redis involvement. Redis-down is fail-open: the
consumer loop logs and falls back to the original single-process `embed_jobs()`
sweep, so a cache outage costs parallelism, never recall.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Iterable
from typing import Any

from app.core import db, dlq_guard, resp, workqueue
from app.core.config import get_settings
from app.ops import queue_observer

log = logging.getLogger("ops.embed_workers")

STREAM = "careeros:jobs:embed"
GROUP = "embed-workers"
# The field that identifies a job on the stream and in the cooldown guard. Kept in
# one place so the queue's id_field and the guard's keys cannot drift apart.
JOB_ID_FIELD = "job_id"


def _consumer_name() -> str:
    """One stable name per process, so a PEL is attributable across restarts."""
    return f"{uuid.uuid4().hex[:12]}"


def _queue(pool: resp.RespPool) -> workqueue.WorkQueue:
    settings = get_settings()
    max_deliveries = int(getattr(settings, "work_queue_max_deliveries", 5) or 0)
    return workqueue.WorkQueue(
        pool, stream=STREAM, group=GROUP, consumer=_consumer_name(),
        min_idle_ms=int(getattr(settings, "work_queue_claim_ms", 120_000) or 120_000),
        batch=16,
        maxlen=int(getattr(settings, "work_queue_maxlen", 10_000) or 10_000),
        max_deliveries=max_deliveries,
        dlq_stream=(getattr(settings, "work_queue_dlq_stream", "")
                    if max_deliveries else ""),
        # When the DLQ is on, name the id field so drain() reports dead-lettered job
        # ids for consumer_pass to cool down. With the DLQ off this is inert.
        id_field=JOB_ID_FIELD if max_deliveries else "",
        # Epic 144: pace retries so a transient blip can heal. The cap bounds the
        # exponential ceiling; the full-jitter shape itself is a pure function in
        # app.core.backoff (a measurement constant, not a config knob).
        backoff_base_ms=int(getattr(settings, "work_queue_backoff_base_ms", 500) or 0),
        backoff_cap_ms=int(getattr(settings, "work_queue_backoff_cap_ms", 30_000) or 0))


def _guard(pool: resp.RespPool) -> dlq_guard.DlqGuard:
    """Build the producer-suppression guard from config.

    It shares ``pool`` with the queue (same Redis, one connection budget). Disabled
    (``enabled == False``) when ``cooldown_s <= 0``, in which case every method is an
    inert no-op and the producer behaves exactly as in Epic 138.
    """
    settings = get_settings()
    cooldown_s = int(getattr(settings, "work_queue_dlq_cooldown_s", 900) or 0)
    key = str(getattr(settings, "work_queue_dlq_guard_key", "")
              or "careeros:jobs:embed:dlq:cooldown")
    return dlq_guard.DlqGuard(pool, key=key, cooldown_s=cooldown_s)


async def _redis_pool() -> resp.RespPool | None:
    """Build a pool from config, or None when Redis is unconfigured/unusable."""
    from app.core.config import get_settings as gs

    settings = gs()
    url = getattr(settings, "redis_url", "") or ""
    try:
        pool = resp.RespPool.from_url(
            url, size=int(getattr(settings, "redis_pool_size", 4) or 4),
            connect_timeout=float(getattr(settings, "redis_connect_timeout_s", 0.5) or 0.5),
            command_timeout=float(getattr(settings, "redis_timeout_s", 0.5) or 0.5))
        return pool
    except (ValueError, OSError) as e:
        log.warning("work queue configured but REDIS_URL unusable (%s); using the DB scan", e)
        return None


async def producer_pass(queue: workqueue.WorkQueue, *, limit: int | None = None,
                        guard: dlq_guard.DlqGuard | None = None) -> int:
    """Enqueue the ids of jobs that still need a vector. Returns how many were sent.

    Scoping the SELECT to *ids* (not full rows) keeps the stream small and makes the
    fan-out cheap: the heavy text + embedding stays with the consumer, where the
    job actually lands. `MAXLEN` trimming is done once at group creation time via
    the queue's stream; here we only add.

    Suppressed ids come from two sources, unioned by ``_suppressed``: ids inside their
    dead-letter cooldown (``guard``, Epic 139) and ids waiting out a retry backoff
    (``queue.parked_ids()``, Epic 145). They are excluded **in SQL**
    (``NOT j.id = ANY($n::uuid[])``), not filtered in Python afterward. That detail
    matters: a Python filter after ``LIMIT`` would let a handful of suppressed ids fill
    the batch and starve older, embeddable jobs — and for a parked job it would re-add
    a fresh ``attempts=0`` copy next tick, bypassing the backoff. Pushing it into the
    WHERE clause makes ``LIMIT`` count only eligible rows. Both reads are independent
    and fail-open, so a Redis outage degrades to "enqueue everything" (Epic 138
    behaviour), never to lost recall.
    """
    suppressed: set[str] = await _suppressed(queue, guard)
    sql = ("SELECT j.id::text AS id FROM jobs j WHERE j.embedding IS NULL")
    args: list[Any] = []
    if suppressed:
        # Each suppressed id is a uuid text; cast the array once and compare as uuid.
        # A malformed (non-uuid) id must not blow up the whole producer pass, so keep
        # only parseable uuids here — a job id on this stream is always a uuid.
        valid = [s for s in suppressed if _is_uuid(s)]
        if valid:
            args.append(valid)
            sql += f" AND NOT (j.id = ANY(${len(args)}::uuid[]))"
    sql += " ORDER BY j.posted_at DESC NULLS LAST"
    if limit:
        args.append(limit)
        sql += f" LIMIT ${len(args)}"
    rows = await db.fetch(sql, *args)
    sent = 0
    for row in rows:
        try:
            await queue.enqueue({JOB_ID_FIELD: row["id"]})
            sent += 1
        except (resp.RespUnavailable, resp.RespError, OSError) as e:
            log.warning("work queue enqueue failed for %s: %s", row["id"], e)
            break  # fail-open: the DB-scan fallback in the loop picks it up next tick
    return sent


def _is_uuid(value: str) -> bool:
    """Guard the SQL uuid[] bind against a malformed cooldown member (defensive:
    job ids come from the DB and are always uuids, but the guard key is shared)."""
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


async def _suppressed(queue: workqueue.WorkQueue,
                      guard: dlq_guard.DlqGuard | None) -> set[str]:
    """Fail-open union of the TWO "do not re-enqueue yet" sources.

    * ``DlqGuard.active()`` — ids past their dead-letter cooldown (Epic 139).
    * ``queue.parked_ids()`` — ids waiting out a retry backoff (Epic 145). This is
      the fix for the gap Epic 144 left: a parked job still has ``embedding IS
      NULL``, so without this the producer re-selects it next tick and XADDs a
      fresh ``attempts=0`` message, bypassing the backoff entirely.

    The two sources are read **independently** and merged: an outage/failure in one
    must not blank the other (that would re-open the storm hole for whichever one
    broke). Each is an optimisation over the DB scan, never a correctness
    dependency: any error escapes as "suppress nothing", i.e. exact Epic 138
    behaviour, so a Redis outage costs suppression, never recall. ``parked_ids`` is
    fetched defensively via ``getattr`` so a custom/older queue fake without the
    method (backoff disabled) contributes nothing and keeps the old behaviour.
    """
    out: set[str] = set()
    if guard and guard.enabled:
        try:
            out |= await guard.active()
        except Exception:
            log.warning("dlq guard active() escaped its fail-open; continuing without "
                        "its suppression", exc_info=True)
    parked = getattr(queue, "parked_ids", None)
    if callable(parked):
        try:
            out |= await parked()
        except Exception:
            log.warning("queue parked_ids() escaped its fail-open; continuing without "
                        "backoff suppression", exc_info=True)
    return out


async def embed_one(job_id: str) -> bool:
    """Embed a single job if it still needs it. Idempotent; returns True if done.

    The `WHERE embedding IS NULL` re-check is the crux: a re-claimed message whose
    job was already written short-circuits here with zero model cost. Returns False
    only on a real failure, so the message stays pending for XAUTOCLAIM.
    """
    from app.providers.registry import get_embeddings

    row = await db.fetchrow(
        "SELECT j.id, j.title, j.location, j.remote_type, j.employment_type, "
        "j.description, j.requirements, j.nice_to_have, j.responsibilities, j.skills "
        "FROM jobs j WHERE j.id = $1::uuid AND j.embedding IS NULL", job_id)
    if row is None:
        return True  # already written (or deleted) -- idempotent no-op, safe to ACK

    from app.ops.embed_jobs import job_embedding_text

    text = job_embedding_text(row)
    if not text:
        return True  # nothing to embed; not a failure
    settings = get_settings()
    vectors = await get_embeddings(settings).embed([text])
    if len(vectors) != 1:
        return False
    await db.execute("UPDATE jobs SET embedding = $2::vector WHERE id = $1::uuid AND embedding IS NULL",
                     job_id, db.vec(vectors[0]))
    return True


async def consumer_pass(queue: workqueue.WorkQueue,
                        guard: dlq_guard.DlqGuard | None = None) -> workqueue.ClaimStats:
    """Claim a batch, embed each job idempotently, ACK the successes.

    Suppression comes from two independent, fail-open sources merged by ``_suppressed``
    at one batched read per pass: ids inside their dead-letter cooldown (Epic 139), and
    ids waiting out a retry backoff in the delay ZSET (Epic 145). Both may still have
    at-least-once duplicate copies sitting on the stream from earlier ticks; those must
    be ACKed without a model call, because their authoritative copy returns on its own
    (cooldown lapse / ``promote_due``) and re-embedding a leftover now would burn a call
    — and, for a parked job, restart its ``attempts`` lineage. After ``drain`` reports
    dead-lettered ids, they are marked into the guard so the *next* producer pass
    excludes them in SQL. Every read is fail-open, so a Redis outage degrades to plain
    Epic 138 behaviour, never to lost recall.
    """
    from app.providers.registry import embeddings_ready

    if not embeddings_ready(get_settings()):
        log.debug("no embedding provider configured; leaving work queued")
        return workqueue.ClaimStats()

    # One batched read for the whole pass; fail-open returns a set() on Redis error.
    suppressed: set[str] = await _suppressed(queue, guard)

    async def handler(item: workqueue.WorkItem) -> bool:
        job_id = item.value(JOB_ID_FIELD)
        if not job_id:
            return True  # malformed message: nothing to do, do not poison the PEL forever
        if job_id in suppressed:
            # Cooling down: ACK it for free. The DB still has embedding IS NULL, so
            # the producer re-enqueues it when the window lapses — no job is lost.
            log.debug("job %s is in its dead-letter cooldown; skipping without a model call",
                      job_id)
            return True
        try:
            return await embed_one(job_id)
        except Exception:
            log.warning("embedding job %s failed; leaving pending for recovery", job_id,
                        exc_info=True)
            return False

    stats = await queue.drain(handler)
    if guard and guard.enabled and stats.dead_lettered_ids:
        marked = await guard.mark(stats.dead_lettered_ids)
        log.warning("dead-lettered %d job(s); cooled %d down for %ss "
                    "(producer will skip them until the window lapses)",
                    stats.dead_lettered, marked, guard.cooldown_s)
    return stats


async def embed_loop_distributed(interval: float = 60.0,
                                 stop: asyncio.Event | None = None) -> None:
    """The opt-in, multi-replica loop. Each tick: produce ids, then consume a share.

    Every replica runs the producer (enqueue is at-least-once and cheap); the
    consumer group guarantees each message is handled by one replica. Redis-down
    falls back to the original single-process `embed_jobs()` sweep so the queue can
    never take recall away.
    """
    from app.ops.embed_jobs import embed_jobs

    pool = await _redis_pool()
    if pool is None:
        await _fallback_loop(interval, stop, embed_jobs)
        return
    queue = _queue(pool)
    guard = _guard(pool)
    try:
        while True:
            try:
                await queue.ensure_group()
                await producer_pass(queue, guard=guard)
                stats = await consumer_pass(queue, guard=guard)
                # Liveness heartbeat for the read-only ops endpoint (Epic 140).
                # Stamped after a *complete* pass, so a fresh tick means the whole
                # produce->consume->drain cycle finished, not just that the loop woke.
                # On the Redis-down / exception paths below it is NOT stamped, so the
                # endpoint sees a stale heartbeat and can report "stalled".
                queue_observer.record_tick(
                    delivered=stats.delivered, reclaimed=stats.reclaimed,
                    dead_lettered=stats.dead_lettered)
                if stats.delivered or stats.reclaimed:
                    log.info("embed work queue: delivered=%d reclaimed=%d ack_failed=%d "
                             "dead_lettered=%d", stats.delivered, stats.reclaimed,
                             stats.ack_failed, stats.dead_lettered)
            except (resp.RespUnavailable, resp.RespError, OSError) as e:
                log.warning("embed work queue unavailable (%s); running the DB-scan fallback", e)
                try:
                    await embed_jobs()
                except Exception:
                    log.warning("DB-scan fallback embed pass failed", exc_info=True)
            except Exception:
                log.warning("embed distributed pass failed; retrying in %ss", interval, exc_info=True)
            if stop is None:
                await asyncio.sleep(interval)
                continue
            try:
                await asyncio.wait_for(stop.wait(), timeout=interval)
            except asyncio.TimeoutError:
                continue
            return
    finally:
        await pool.close()


async def _fallback_loop(interval, stop, embed_jobs) -> None:
    """Run the original loop when Redis is not usable (single-process scan)."""
    while True:
        try:
            await embed_jobs()
        except Exception:
            log.warning("job embedding pass failed; retrying in %ss", interval, exc_info=True)
        if stop is None:
            await asyncio.sleep(interval)
            continue
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue
        return


# --------------------------------------------------------------- operator controls
async def release_cooldowns(job_ids: Iterable[str] | None = None) -> int:
    """Let an operator requeue cooled-down jobs early (the "requeue it" half of the
    Epic 139 contract). Pass specific ids after fixing them, or ``None`` to clear the
    entire cooldown set — e.g. right after restoring a flaky embedding provider so the
    next producer tick can retry every suppressed job at once.

    Returns how many ids were released. The jobs' DB rows are still ``embedding IS
    NULL``, so the ordinary producer re-enqueues them on its next tick; this only
    removes the suppression, it does not enqueue directly (one source of truth).

    Equivalent redis-cli, for an operator without a Python shell::

        ZREM careeros:jobs:embed:dlq:cooldown <job-uuid> [...]
        ZREMRANGEBYSCORE careeros:jobs:embed:dlq:cooldown -inf +inf   # release all
    """
    pool = await _redis_pool()
    if pool is None:
        log.warning("cannot release cooldowns: Redis is unavailable")
        return 0
    try:
        guard = _guard(pool)
        return (await guard.release_all() if job_ids is None
                else await guard.release(job_ids))
    finally:
        await pool.close()
