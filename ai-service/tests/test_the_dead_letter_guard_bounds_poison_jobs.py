"""`DlqGuard`: a Redis-ZSET cooldown that stops a dead-lettered job being re-born.

Epic 139, measured against the honest bound left by Epic 138. Epic 138 caps *one*
message lineage (re-queue with rising ``attempts``, dead-letter after the limit),
but the embed producer re-selects ``embedding IS NULL`` every tick and ``XADD``s a
*fresh, attempts-less* message — so a permanently-poison job started a new lineage
each tick, was never dead-lettered from the producer's view, and kept burning one
model call per tick. The real-Redis check in Epic 138 observed exactly this
(live ``attempts`` values ``['0','0','1','1']`` after two producer ticks).

``DlqGuard`` cools a job **id** down for a bounded window after it is dead-lettered.
The producer excludes cooling ids in SQL; the consumer ACKs leftover duplicate copies
without a model call. The claims pinned here:

* marking suppresses an id, and the expiry travels with the member (ZSET score);
* ``active()`` returns only ids whose window is still open, and prunes the rest;
* a suppressed id heals on its own when the window lapses — no permanent tombstone,
  so a transient provider outage cannot silently drop recall;
* ``release()`` / ``release_all()`` let an operator requeue early;
* every Redis failure is fail-open — ``active()`` returns empty ("suppress nothing")
  and ``mark()`` is a no-op, so a guard outage costs suppression, never recall;
* the guard is inert when ``cooldown_s == 0`` (pure Epic 138 behaviour);
* ids are validated as uuids before entering a SQL ``= ANY($n::uuid[])`` bind.

The ``FakePool`` is a small ZSET model, not a byte-level server: it keeps the tests
about the guard's *decisions* (which id, which score, when to prune) rather than the
RESP codec, which the cache suite pins separately. The full command path is also
exercised against a real local Redis in the epic's end-to-end check.
"""

from __future__ import annotations

import pytest

from app.core import resp
from app.core.dlq_guard import DlqGuard


class FakePool:
    """A one-key ZSET model with just enough RESP semantics for the guard.

    ``execute`` takes already-decoded tokens and returns the shapes Redis returns
    (integers for ZADD/ZREM/ZCARD/ZREMRANGEBYSCORE, bytes for ZSCORE, list[bytes]
    for ZRANGEBYSCORE). ``pipeline`` runs each command through ``execute`` in order
    and returns the list of replies, matching ``RespPool.pipeline``.
    """

    def __init__(self, *, down: bool = False) -> None:
        self.zset: dict[str, float] = {}  # member -> expiry epoch (the ZSET score)
        self.down = down
        self.commands: list[list[str]] = []

    async def execute(self, *args):
        self.commands.append([str(a) for a in args])
        if self.down:
            raise resp.RespUnavailable("down")
        a = [str(x) for x in args]
        cmd = a[0].upper()
        if cmd == "ZADD":
            # ZADD key score member [score member ...] -- score at a[i], member a[i+1]
            new = 0
            for i in range(2, len(a) - 1, 2):
                member, score = a[i + 1], float(a[i])
                if member not in self.zset:
                    new += 1
                self.zset[member] = score
            return new
        if cmd == "ZSCORE":
            score = self.zset.get(a[2])
            return None if score is None else str(score).encode()
        if cmd == "ZRANGEBYSCORE":
            # key min max ; min may be "(<n>" (exclusive), max may be "+inf".
            lo, hi = a[2], a[3]
            exclusive = lo.startswith("(")
            lo_val = float(lo[1:]) if exclusive else (float("-inf") if lo == "-inf" else float(lo))
            hi_val = float("inf") if hi == "+inf" else float(hi)
            out = []
            for member, score in self.zset.items():
                above = score > lo_val if exclusive else score >= lo_val
                if above and score <= hi_val:
                    out.append(member.encode())
            return out
        if cmd == "ZREMRANGEBYSCORE":
            lo, hi = a[2], a[3]
            lo_val = float("-inf") if lo == "-inf" else float(lo)
            hi_val = float("inf") if hi == "+inf" else float(hi)
            gone = [m for m, s in self.zset.items() if lo_val <= s <= hi_val]
            for m in gone:
                del self.zset[m]
            return len(gone)
        if cmd == "ZREM":
            gone = [m for m in a[2:] if self.zset.pop(m, None) is not None]
            return len(gone)
        if cmd == "ZCARD":
            return len(self.zset)
        raise AssertionError(f"unexpected command: {a}")

    async def pipeline(self, commands):
        replies = []
        for cmd in commands:
            replies.append(await self.execute(*cmd))
        return replies


class Clock:
    """A manually advanced clock so expiry is tested without sleeping."""

    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


JOBS = [
    "00000000-0000-0000-0000-000000000001",
    "00000000-0000-0000-0000-000000000002",
    "00000000-0000-0000-0000-000000000003",
]


def _guard(pool, *, cooldown_s=900, clock=None) -> DlqGuard:
    return DlqGuard(pool, key="cooldown", cooldown_s=cooldown_s,
                    clock=clock or Clock())


# --------------------------------------------------------------- mark / suppress
async def test_mark_suppresses_an_id_and_active_reads_it_back():
    pool = FakePool()
    clock = Clock()
    g = _guard(pool, cooldown_s=900, clock=clock)
    assert await g.mark([JOBS[0]]) == 1
    assert pool.zset[JOBS[0]] == clock.now + 900
    assert await g.active(now=clock.now) == {JOBS[0]}
    assert await g.is_suppressed(JOBS[0], now=clock.now) is True


async def test_a_whole_batch_is_marked_in_one_zadd_round_trip():
    pool = FakePool()
    g = _guard(pool, cooldown_s=900)
    assert await g.mark(JOBS) == 3
    zadds = [c for c in pool.commands if c[0] == "ZADD"]
    assert len(zadds) == 1, "one XADD-style batched write, not N round trips"
    assert zadds[0][1] == "cooldown"
    assert await g.active(now=1000.0) == set(JOBS)
    assert await g.size() == 3


async def test_remarking_an_id_refreshes_its_window_back_off():
    pool = FakePool()
    clock = Clock()
    g = _guard(pool, cooldown_s=100, clock=clock)
    await g.mark([JOBS[0]])
    first_expiry = pool.zset[JOBS[0]]
    clock.advance(60)  # still inside the first window
    assert await g.mark([JOBS[0]]) == 1
    assert pool.zset[JOBS[0]] == first_expiry + 60, "a repeat dead-letter pushes the window out"
    assert await g.is_suppressed(JOBS[0], now=clock.now) is True


# --------------------------------------------------------------- self-healing
async def test_a_suppressed_id_heals_when_its_window_lapses():
    """The core anti-tombstone guarantee: no permanent recall loss after a blip."""
    pool = FakePool()
    clock = Clock()
    g = _guard(pool, cooldown_s=100, clock=clock)
    await g.mark([JOBS[0]])
    assert await g.active(now=clock.now) == {JOBS[0]}
    clock.advance(101)
    # active() reads only ids whose expiry is strictly in the future, and prunes.
    assert await g.active(now=clock.now) == set()
    assert pool.zset == {}, "the lapsed member was pruned, so the set cannot grow forever"
    assert await g.is_suppressed(JOBS[0], now=clock.now) is False


async def test_active_prunes_in_the_same_pipeline_as_the_read():
    pool = FakePool()
    clock = Clock()
    g = _guard(pool, cooldown_s=10, clock=clock)
    await g.mark([JOBS[0], JOBS[1]])
    clock.advance(11)
    await g.mark([JOBS[1]])  # JOBS[1] cooling again; JOBS[0] still lapsed
    clock.advance(1)
    assert await g.active(now=clock.now) == {JOBS[1]}
    assert pool.zset == {JOBS[1]: pytest.approx(clock.now + 9)}
    asserts = [c for c in pool.commands if c[0] in ("ZREMRANGEBYSCORE", "ZRANGEBYSCORE")]
    assert asserts, "prune + read both issued"


async def test_prune_explicitly_returns_how_many_expired():
    pool = FakePool()
    clock = Clock()
    g = _guard(pool, cooldown_s=10, clock=clock)
    await g.mark([JOBS[0], JOBS[1]])
    clock.advance(11)
    assert await g.prune(now=clock.now) == 2
    assert pool.zset == {}


# --------------------------------------------------------------- operator release
async def test_release_lets_an_operator_requeue_specific_jobs_early():
    pool = FakePool()
    g = _guard(pool, cooldown_s=900)
    await g.mark(JOBS)
    assert await g.release([JOBS[0], JOBS[2]]) == 2
    assert await g.active(now=1000.0) == {JOBS[1]}
    assert await g.release(["not-even-in-the-set"]) == 0, "release is idempotent"


async def test_release_all_clears_the_set_after_an_incident():
    pool = FakePool()
    g = _guard(pool, cooldown_s=900)
    await g.mark(JOBS)
    assert await g.release_all() == 3
    assert await g.active(now=1000.0) == set()
    assert await g.size() == 0


# --------------------------------------------------------------- fail-open
async def test_redis_down_is_fail_open_for_reads_and_writes():
    pool = FakePool(down=True)
    g = _guard(pool, cooldown_s=900)
    assert await g.mark([JOBS[0]]) == 0, "mark is a no-op"
    assert await g.active(now=1000.0) == set(), "suppress nothing -> producer enqueues all"
    assert await g.is_suppressed(JOBS[0], now=1000.0) is False
    assert await g.prune() == 0
    assert await g.release([JOBS[0]]) == 0
    assert await g.release_all() == 0
    assert await g.size() == 0


async def test_a_resp_error_on_the_second_pipeline_step_is_fail_open():
    """A partial/failed pipeline must not half-suppress the producer."""
    pool = FakePool()
    g = _guard(pool, cooldown_s=900)
    await g.mark([JOBS[0]])

    async def broken_pipeline(_cmds):
        raise resp.RespError("WRONGTYPE key is not a sorted set")

    pool.pipeline = broken_pipeline
    assert await g.active(now=1000.0) == set()


# --------------------------------------------------------------- disabled / validation
async def test_a_zero_cooldown_is_inert_even_with_no_redis():
    g = _guard(FakePool(down=True), cooldown_s=0)
    assert g.enabled is False
    assert await g.mark([JOBS[0]]) == 0
    assert await g.active(now=1000.0) == set()
    assert await g.is_suppressed(JOBS[0], now=1000.0) is False
    assert await g.release_all() == 0


def test_rejects_invalid_construction():
    pool = FakePool()
    with pytest.raises(ValueError):
        DlqGuard(pool, key="cooldown", cooldown_s=-1)
    with pytest.raises(ValueError):
        DlqGuard(pool, key="", cooldown_s=900)


async def test_mark_ignores_empty_or_malformed_ids():
    """A malformed field must not become a ZSET member (it would break the SQL bind)."""
    pool = FakePool()
    g = _guard(pool, cooldown_s=900)
    assert await g.mark(["", JOBS[0]]) == 1
    assert set(pool.zset) == {JOBS[0]}
