"""A Redis ZSET cooldown that stops a dead-lettered job being re-injected forever.

The problem (found measuring Epic 138 against real Redis)
---------------------------------------------------------
Epic 138 caps *one message lineage*: a job whose handler keeps failing is re-queued
with a rising ``attempts`` counter and dead-lettered after ``max_deliveries``. But
the embed producer re-selects ``jobs WHERE embedding IS NULL`` on **every tick** and
``XADD``s a *fresh, attempts-less* message. A permanently-unembeddable row therefore
starts a new lineage each tick, was never dead-lettered from the producer's point of
view, and kept spending one model call per tick — the DLQ stream grew one dead-letter
per tick (bounded by MAXLEN after Epic 138, but the *work* was unbounded).

What this module does
---------------------
``DlqGuard`` is a bounded, self-healing suppression set keyed by **job id**, backed by
one Redis sorted set:

* ``ZADD <key> <expiry_epoch> <job_id>`` — a dead-lettered job id is cooled down
  until ``now + cooldown_s``;
* ``ZRANGEBYSCORE <key> (now +inf`` — the ids suppressed *right now*;
* ``ZREMRANGEBYSCORE <key> -inf now`` — prune expired members so the set stays small.

The producer drops suppressed ids from its ``SELECT`` (via ``NOT id = ANY(...)`` in
SQL, so a SQL ``LIMIT`` cannot be defeated by post-filtering), and ``consumer_pass``
marks ids that ``drain`` reports as dead-lettered. Together they turn "one model
call per tick, forever" into "one model call per ``cooldown_s`` window".

Why a cooldown and not a permanent tombstone
--------------------------------------------
The obvious fix — suppress dead-lettered ids forever until an operator clears them —
silently drops recall after a *transient* provider outage: a 10-minute blip could
dead-letter hundreds of perfectly good jobs, and a permanent set would leave them
un-embedded until a human noticed. A **bounded cooldown** heals on its own: after
``cooldown_s`` the id leaves the set and the next producer tick re-enqueues it. An
operator can still ``release()`` an id early (e.g. after fixing the bad row or the
provider), and ``release_all()`` clears the set after an incident. The DB column
``embedding IS NULL`` remains the source of truth; the guard only decides *when* a
job is eligible to be tried, so a pruned/released entry can never lose a job.

Honest contract
---------------
* **Fail-open.** The guard is an optimisation over the DB scan. Any Redis error in
  ``mark`` / ``active`` / ``prune`` is swallowed (logged) with a safe default:
  ``active()`` returns an empty set (so the producer enqueues everything, i.e. exact
  Epic 138 behaviour) and ``mark`` is a no-op. A guard outage costs suppression, not
  recall.
* **Approximate across replicas.** Every replica shares the same ZSET, so suppression
  is global. There is no leader: two replicas may both ``ZADD`` the same id (idempotent
  — same member, last expiry wins) or both read the same active set. That is fine for
  a *cooldown*; a job may be tried at most once per window per replica in the worst
  case, which is still bounded and far below "once per tick".
* **Wall-clock, not monotonic.** ZSET scores must be comparable across processes, so
  the clock is ``time.time`` (unix epoch seconds), injectable for tests.

Everything speaks RESP2 through the dependency-free ``app.core.resp`` pool already
used by the cache, task bus and work queue. No new dependency, no new infrastructure.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Iterable

from app.core import resp

log = logging.getLogger(__name__)


class DlqGuard:
    """A self-healing job-id cooldown backed by one Redis sorted set.

    ``pool`` speaks ``execute(*args)`` / ``pipeline([...])``; ``key`` is the ZSET;
    ``cooldown_s`` is how long a marked id stays suppressed (<= 0 disables the guard
    entirely — every method then short-circuits to its inert default). ``clock`` is
    injectable so expiry can be tested without sleeping.
    """

    def __init__(self, pool: resp.RespPool, *, key: str, cooldown_s: int,
                 clock: Callable[[], float] = time.time) -> None:
        if cooldown_s < 0:
            raise ValueError("cooldown_s must be >= 0 (0 disables the guard)")
        if not key:
            raise ValueError("a dlq guard needs a redis key")
        self.pool = pool
        self.key = key
        self.cooldown_s = cooldown_s
        self._clock = clock

    @property
    def enabled(self) -> bool:
        return self.cooldown_s > 0

    # -------------------------------------------------------------- wire helpers
    @staticmethod
    def _decode(value: Any) -> str:
        return value.decode() if isinstance(value, bytes) else str(value)

    # -------------------------------------------------------------- write
    async def mark(self, job_ids: Iterable[str], *, now: float | None = None) -> int:
        """Cool down ``job_ids`` until ``now + cooldown_s``. Returns how many marked.

        A single ``ZADD`` carries all pairs, so marking a whole batch is one round
        trip. Marking an already-suppressed id refreshes its expiry — a job that
        somehow dead-letters again within the window pushes the window out, which is
        the right back-off behaviour. Fail-open: a Redis error logs and returns 0 so
        the caller never treats a guard outage as "job done".
        """
        if not self.enabled:
            return 0
        ids = [str(j) for j in job_ids if j]  # guard against empty/malformed fields
        if not ids:
            return 0
        until = (self._clock() if now is None else now) + self.cooldown_s
        flat: list[Any] = [self.key]
        for jid in ids:
            flat.extend((repr(until), jid))
        try:
            # ZADD returns the number of NEW members; a refresh of an existing member
            # returns 0, which is not a failure. Report "marked" as ids submitted.
            await self.pool.execute("ZADD", *flat)
        except (resp.RespUnavailable, resp.RespError, OSError) as e:
            log.warning("dlq guard mark failed for %d job(s): %s (suppression skipped)",
                        len(ids), e)
            return 0
        return len(ids)

    # -------------------------------------------------------------- read
    async def active(self, *, now: float | None = None,
                     prune: bool = True) -> set[str]:
        """Ids suppressed *right now* (expiry strictly in the future).

        By default this also prunes expired members in the **same pipeline round
        trip** (``ZREMRANGEBYSCORE`` then ``ZRANGEBYSCORE``), so a long-lived guard
        never accumulates dead ids. ``prune=False`` is for observers/tests that want
        a pure read. Fail-open: a Redis error returns an empty set, i.e. "suppress
        nothing" — the producer then behaves exactly as it did before this guard.
        """
        if not self.enabled:
            return set()
        at = self._clock() if now is None else now
        cmds: list[list[Any]] = []
        if prune:
            cmds.append(["ZREMRANGEBYSCORE", self.key, "-inf", repr(at)])
        cmds.append(["ZRANGEBYSCORE", self.key, f"({repr(at)}", "+inf"])
        try:
            replies = await self.pool.pipeline(cmds)
        except (resp.RespUnavailable, resp.RespError, OSError) as e:
            log.warning("dlq guard active read failed: %s (suppression skipped)", e)
            return set()
        members = replies[-1] or []
        # ZRANGEBYSCORE without WITHSCORE returns a flat array of member bytes.
        return {self._decode(m) for m in members}

    async def is_suppressed(self, job_id: str, *,
                            now: float | None = None) -> bool:
        """Single-id check (``ZSCORE``). Convenient for handlers/ops; the hot producer
        path should prefer ``active()`` so it pays one round trip for the whole batch.
        """
        if not self.enabled or not job_id:
            return False
        at = self._clock() if now is None else now
        try:
            score = await self.pool.execute("ZSCORE", self.key, str(job_id))
        except (resp.RespUnavailable, resp.RespError, OSError) as e:
            log.warning("dlq guard zscore failed for %s: %s (treated as not suppressed)",
                        job_id, e)
            return False
        if score is None:
            return False
        try:
            return float(self._decode(score)) > at
        except (TypeError, ValueError):
            return False

    # -------------------------------------------------------------- maintenance
    async def prune(self, *, now: float | None = None) -> int:
        """Drop expired members explicitly. Returns how many were removed. Used by
        an operator/maintenance task; ``active()`` already prunes opportunistically.
        """
        if not self.enabled:
            return 0
        at = self._clock() if now is None else now
        try:
            return int(await self.pool.execute(
                "ZREMRANGEBYSCORE", self.key, "-inf", repr(at)) or 0)
        except (resp.RespUnavailable, resp.RespError, OSError) as e:
            log.warning("dlq guard prune failed: %s", e)
            return 0

    async def release(self, job_ids: Iterable[str]) -> int:
        """Let an operator retry specific ids early (e.g. after fixing the bad row).
        Returns how many members were actually removed.
        """
        if not self.enabled:
            return 0
        ids = [str(j) for j in job_ids if j]
        if not ids:
            return 0
        try:
            return int(await self.pool.execute("ZREM", self.key, *ids) or 0)
        except (resp.RespUnavailable, resp.RespError, OSError) as e:
            log.warning("dlq guard release failed for %d job(s): %s", len(ids), e)
            return 0

    async def release_all(self) -> int:
        """Clear the whole cooldown set after an incident (e.g. provider restored).
        Returns how many members were removed.
        """
        if not self.enabled:
            return 0
        try:
            return int(await self.pool.execute("ZREMRANGEBYSCORE", self.key,
                                               "-inf", "+inf") or 0)
        except (resp.RespUnavailable, resp.RespError, OSError) as e:
            log.warning("dlq guard release_all failed: %s", e)
            return 0

    async def size(self) -> int:
        """Total members (including not-yet-pruned expired ones), for observability."""
        if not self.enabled:
            return 0
        try:
            return int(await self.pool.execute("ZCARD", self.key) or 0)
        except (resp.RespUnavailable, resp.RespError, OSError) as e:
            log.warning("dlq guard size failed: %s", e)
            return 0
