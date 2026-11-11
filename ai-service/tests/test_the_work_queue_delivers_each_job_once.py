"""`WorkQueue`: a job goes to one worker, and a dead worker's job comes back.

This is the work-queue counterpart to the task bus's broadcast. The claims pinned
here are the ones that matter for a distributed worker pool (embed_loop running on
more than one replica is the concrete consumer):

* a consumer group delivers each fresh message to exactly ONE consumer (no double
  model calls across replicas);
* an un-ACKed message that has sat past the visibility timeout is re-claimed by
  another consumer (a crashed worker loses no job);
* `XACK` removes a message from the pending list; a handler that fails leaves it;
* the group is created exactly once (BUSYGROUP startup race is benign);
* Redis failure is fail-open — the caller keeps its DB fallback.

Honest bound: delivery is **at-least-once**. A worker that finishes but crashes
before ACK is re-claimed and runs twice; the handler must be idempotent. This file
pins the protocol behaviour, not a fictitious exactly-once guarantee. The commands
are also exercised against a real local Redis in a separate check.
"""

import asyncio

import pytest

from app.core import resp, workqueue
from app.core.workqueue import WorkItem, WorkQueue


# --------------------------------------------------------------- in-memory Redis
class FakePool:
    """A stream+consumer-group model with just enough RESP command semantics.

    It is deliberately a *model*, not a byte-level server: `execute(*args)` takes
    already-decoded tokens and returns the shapes Redis returns. That keeps the
    tests about the queue's decisions (which group, which id, when to ack) rather
    than about the RESP codec, which the cache suite pins separately.
    """

    def __init__(self, *, down: bool = False) -> None:
        self.stream: list[tuple[str, dict[str, str]]] = []
        self.seq = 0
        self.groups: set[str] = set()
        # id -> (fields, delivered_to_consumer|None, delivered_at_ms)
        self.pel: dict[str, tuple[dict[str, str], str | None, int]] = {}
        self.acked: list[str] = []
        self.clock_ms = 1_000_000
        self.down = down
        self.commands: list[list[str]] = []

    async def execute(self, *args):
        self.commands.append([str(a) for a in args])
        if self.down:
            raise resp.RespUnavailable("down")
        cmd = str(args[0]).upper()
        a = [str(x) for x in args]
        if cmd == "XGROUP" and a[1].upper() == "CREATE":
            group = a[3]
            if group in self.groups:
                raise resp.RespError("BUSYGROUP Consumer Group name already exists")
            self.groups.add(group)
            return "OK"
        if cmd == "XADD":
            # Optional `MAXLEN ~ N` sits between the key and the `*`.
            rest = a[2:]
            if rest and rest[0].upper() == "MAXLEN":
                assert rest[1] == "~"
                rest = rest[3:]  # drop MAXLEN, ~, N
            assert rest and rest[0] == "*", f"unexpected XADD shape: {a}"
            fields = _to_fields(rest[1:])
            self.seq += 1
            sid = f"{self.seq}-0"
            self.stream.append((sid, fields))
            self.pel[sid] = (fields, None, self.clock_ms)
            return sid.encode()
        if cmd == "XREADGROUP":
            # '>' => only messages never delivered to anyone
            n = int(a[a.index("COUNT") + 1])
            out = []
            for sid, (fields, owner, _) in list(self.pel.items()):
                if owner is None and len(out) < n:
                    consumer = a[a.index("GROUP") + 2]
                    self.pel[sid] = (fields, consumer, self.clock_ms)
                    out.append((sid.encode(), _to_resp_fields(fields)))
            return [[b"stream", out]] if out else None
        if cmd == "XAUTOCLAIM":
            n = int(a[a.index("COUNT") + 1])
            idle = int(a[4])
            consumer = a[3]
            out = []
            for sid, (fields, owner, at) in list(self.pel.items()):
                if owner is not None and owner != consumer and (self.clock_ms - at) > idle and len(out) < n:
                    self.pel[sid] = (fields, consumer, self.clock_ms)
                    out.append((sid.encode(), _to_resp_fields(fields)))
            return [b"0-0", out]
        if cmd == "XACK":
            ids = a[3:]
            for sid in ids:
                self.pel.pop(sid, None)
                self.acked.append(sid)
            return len(ids)
        if cmd == "XPENDING":
            return [len(self.pel), b"0-0", b"0-0", []]
        raise AssertionError(f"unexpected command: {a}")


def _to_fields(tokens: list[str]) -> dict[str, str]:
    return {tokens[i]: tokens[i + 1] for i in range(0, len(tokens), 2)}


def _to_resp_fields(fields: dict[str, str]) -> list[bytes]:
    out: list[bytes] = []
    for k, v in fields.items():
        out.extend((k.encode(), v.encode()))
    return out


def _queue(pool, *, consumer="w1", min_idle_ms=1000, batch=8) -> WorkQueue:
    return WorkQueue(pool, stream="jobs", group="embedders", consumer=consumer,
                     min_idle_ms=min_idle_ms, batch=batch)


# --------------------------------------------------------------- produce / group
async def test_group_is_created_once_and_busygroup_race_is_benign():
    pool = FakePool()
    w1, w2 = _queue(pool, consumer="a"), _queue(pool, consumer="b")
    await asyncio.gather(w1.ensure_group(), w2.ensure_group())
    creates = [c for c in pool.commands if c[:2] == ["XGROUP", "CREATE"]]
    assert len(creates) == 2, "both workers raced to create; one got BUSYGROUP"
    assert pool.groups == {"embedders"}
    # Each worker cached readiness: a second call is a no-op.
    before = len(pool.commands)
    await w1.ensure_group()
    assert len(pool.commands) == before


async def test_enqueue_adds_a_job_with_its_fields():
    pool = FakePool()
    q = _queue(pool)
    assert await q.enqueue({"job_id": "abc", "text": "hello"}) == "1-0"
    assert pool.stream == [("1-0", {"job_id": "abc", "text": "hello"})]


async def test_enqueue_trims_with_maxlen_when_bounded():
    """A long-lived producer must not grow the stream without bound."""
    pool = FakePool()
    q = WorkQueue(pool, stream="jobs", group="g", consumer="c", maxlen=1000)
    await q.enqueue({"job_id": "abc"})
    cmd = [c for c in pool.commands if c[0] == "XADD"][0]
    assert cmd[:6] == ["XADD", "jobs", "MAXLEN", "~", "1000", "*"], cmd
    assert cmd[6:] == ["job_id", "abc"]


async def test_an_unbounded_queue_does_not_send_maxlen():
    pool = FakePool()
    q = _queue(pool)  # maxlen defaults to 0
    await q.enqueue({"job_id": "abc"})
    cmd = [c for c in pool.commands if c[0] == "XADD"][0]
    assert "MAXLEN" not in cmd, cmd


# --------------------------------------------------------------- work queue core
async def test_each_fresh_job_goes_to_exactly_one_consumer():
    pool = FakePool()
    a, b = _queue(pool, consumer="a"), _queue(pool, consumer="b")
    for i in range(6):
        await pool.execute("XADD", "jobs", "*", "job_id", str(i))
    got_a = await a.claim()
    got_b = await b.claim()
    ids = [x.value("job_id") for x in got_a + got_b]
    assert sorted(ids) == [str(i) for i in range(6)], "no job lost"
    assert len({x.stream_id for x in got_a + got_b}) == 6, "no job delivered twice"


async def test_ack_removes_jobs_from_pending():
    pool = FakePool()
    q = _queue(pool)
    await q.enqueue({"job_id": "1"})
    await q.enqueue({"job_id": "2"})
    items = await q.claim()
    assert await q.pending() == 2
    assert await q.ack(items[0].stream_id) == 1
    assert await q.pending() == 1
    assert pool.acked == ["1-0"]


async def test_an_unacked_job_is_reclaimed_after_the_visibility_timeout():
    pool = FakePool()
    dead = _queue(pool, consumer="dead", min_idle_ms=1000)
    alive = _queue(pool, consumer="alive", min_idle_ms=1000)
    await pool.execute("XADD", "jobs", "*", "job_id", "orphan")
    claimed = await dead.claim()
    assert len(claimed) == 1 and claimed[0].value("job_id") == "orphan"
    # Not idle long enough: a second worker gets nothing.
    assert await alive.claim() == []
    # The dead worker never ACKed. Advance the clock past min_idle_ms.
    pool.clock_ms += 1001
    recovered = await alive.claim()
    assert len(recovered) == 1 and recovered[0].value("job_id") == "orphan"
    assert recovered[0].stream_id == claimed[0].stream_id, "same job, re-claimed"


async def test_drain_acks_successes_and_leaves_failures_pending():
    pool = FakePool()
    q = _queue(pool)
    for i in range(4):
        await q.enqueue({"job_id": str(i)})
    seen = []

    async def handler(item: WorkItem) -> bool:
        seen.append(item.value("job_id"))
        return item.value("job_id") != "2"  # job 2 fails

    stats = await q.drain(handler)
    assert sorted(seen) == ["0", "1", "2", "3"]
    assert stats.delivered == 4
    assert stats.ack_failed == 1, "one handler reported failure"
    assert await q.pending() == 1, "the failed job stays pending for recovery"


async def test_a_handler_that_raises_does_not_stop_the_batch():
    pool = FakePool()
    q = _queue(pool)
    for i in range(3):
        await q.enqueue({"job_id": str(i)})

    async def handler(item: WorkItem) -> bool:
        if item.value("job_id") == "0":
            raise RuntimeError("provider exploded")
        return True

    stats = await q.drain(handler)
    assert stats.delivered == 3
    assert stats.ack_failed == 1
    assert await q.pending() == 1


# --------------------------------------------------------------- fail-open
async def test_redis_down_is_fail_open_for_produce_and_claim():
    pool = FakePool(down=True)
    q = _queue(pool)
    with pytest.raises(resp.RespUnavailable):
        await q.enqueue({"job_id": "x"})
    with pytest.raises(resp.RespUnavailable):
        await q.claim()
    # The caller (embed_loop) catches this and runs its DB-scan fallback; the
    # queue itself never swallows the outage, so the fallback is an explicit choice.


async def test_pending_is_best_effort_when_redis_down():
    q = _queue(FakePool(down=True))
    assert await q.pending() == 0


# --------------------------------------------------------------- construction
def test_rejects_nonpositive_knobs():
    pool = FakePool()
    with pytest.raises(ValueError):
        WorkQueue(pool, stream="s", group="g", consumer="c", min_idle_ms=0)
    with pytest.raises(ValueError):
        WorkQueue(pool, stream="s", group="g", consumer="c", batch=0)
    with pytest.raises(ValueError):
        WorkQueue(pool, stream="s", group="g", consumer="c", maxlen=-1)
