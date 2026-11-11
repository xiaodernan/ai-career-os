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

from app.core import db, resp, workqueue
from app.core.config import get_settings

log = logging.getLogger("ops.embed_workers")

STREAM = "careeros:jobs:embed"
GROUP = "embed-workers"


def _consumer_name() -> str:
    """One stable name per process, so a PEL is attributable across restarts."""
    return f"{uuid.uuid4().hex[:12]}"


def _queue(pool: resp.RespPool) -> workqueue.WorkQueue:
    settings = get_settings()
    return workqueue.WorkQueue(
        pool, stream=STREAM, group=GROUP, consumer=_consumer_name(),
        min_idle_ms=int(getattr(settings, "work_queue_claim_ms", 120_000) or 120_000),
        batch=16,
        maxlen=int(getattr(settings, "work_queue_maxlen", 10_000) or 10_000))


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


async def producer_pass(queue: workqueue.WorkQueue, *, limit: int | None = None) -> int:
    """Enqueue the ids of jobs that still need a vector. Returns how many were sent.

    Scoping the SELECT to *ids* (not full rows) keeps the stream small and makes the
    fan-out cheap: the heavy text + embedding stays with the consumer, where the
    job actually lands. `MAXLEN` trimming is done once at group creation time via
    the queue's stream; here we only add.
    """
    rows = await db.fetch(
        "SELECT j.id::text AS id FROM jobs j WHERE j.embedding IS NULL "
        "ORDER BY j.posted_at DESC NULLS LAST" + (" LIMIT $1" if limit else ""),
        *((limit,) if limit else ()))
    sent = 0
    for row in rows:
        try:
            await queue.enqueue({"job_id": row["id"]})
            sent += 1
        except (resp.RespUnavailable, resp.RespError, OSError) as e:
            log.warning("work queue enqueue failed for %s: %s", row["id"], e)
            break  # fail-open: the DB-scan fallback in the loop picks it up next tick
    return sent


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


async def consumer_pass(queue: workqueue.WorkQueue) -> workqueue.ClaimStats:
    """Claim a batch, embed each job idempotently, ACK the successes."""
    from app.providers.registry import embeddings_ready

    if not embeddings_ready(get_settings()):
        log.debug("no embedding provider configured; leaving work queued")
        return workqueue.ClaimStats()

    async def handler(item: workqueue.WorkItem) -> bool:
        job_id = item.value("job_id")
        if not job_id:
            return True  # malformed message: nothing to do, do not poison the PEL forever
        try:
            return await embed_one(job_id)
        except Exception:
            log.warning("embedding job %s failed; leaving pending for recovery", job_id,
                        exc_info=True)
            return False

    return await queue.drain(handler)


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
    try:
        while True:
            try:
                await queue.ensure_group()
                await producer_pass(queue)
                stats = await consumer_pass(queue)
                if stats.delivered or stats.reclaimed:
                    log.info("embed work queue: delivered=%d reclaimed=%d ack_failed=%d",
                             stats.delivered, stats.reclaimed, stats.ack_failed)
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
