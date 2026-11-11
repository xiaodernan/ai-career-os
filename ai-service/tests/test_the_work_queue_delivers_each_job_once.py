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
        self.dlq: list[dict[str, str]] = []  # XADDs to a key != the main stream
        self.key = "jobs"  # the main stream key; other keys (DLQ) are recorded separately
        self.seq = 0
        self.groups: set[str] = set()
        # id -> (fields, delivered_to_consumer|None, delivered_at_ms, delivery_count)
        self.pel: dict[str, tuple[dict[str, str], str | None, int, int]] = {}
        self.acked: list[str] = []
        self.clock_ms = 1_000_000
        self.down = down
        self.commands: list[list[str]] = []
        self.xadd_fail = False  # simulate a Redis failure on the DLQ XADD

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
            stream_key = a[1]
            # Optional `MAXLEN ~ N` sits between the key and the `*`.
            rest = a[2:]
            if rest and rest[0].upper() == "MAXLEN":
                assert rest[1] == "~"
                rest = rest[3:]  # drop MAXLEN, ~, N
            assert rest and rest[0] == "*", f"unexpected XADD shape: {a}"
            fields = _to_fields(rest[1:])
            self.seq += 1
            sid = f"{self.seq}-0"
            if stream_key != self.key:
                if self.xadd_fail:
                    raise resp.RespUnavailable("down")
                # A DLQ (or other sidecar) stream: record it, no consumer group.
                self.dlq.append(fields)
                return sid.encode()
            self.stream.append((sid, fields))
            self.pel[sid] = (fields, None, self.clock_ms, 0)
            return sid.encode()
        if cmd == "XREADGROUP":
            # '>' => only messages never delivered to anyone
            n = int(a[a.index("COUNT") + 1])
            out = []
            for sid, (fields, owner, _, count) in list(self.pel.items()):
                if owner is None and len(out) < n:
                    consumer = a[a.index("GROUP") + 2]
                    self.pel[sid] = (fields, consumer, self.clock_ms, count + 1)
                    out.append((sid.encode(), _to_resp_fields(fields)))
            return [[b"stream", out]] if out else None
        if cmd == "XAUTOCLAIM":
            n = int(a[a.index("COUNT") + 1])
            idle = int(a[4])
            consumer = a[3]
            out = []
            for sid, (fields, owner, at, count) in list(self.pel.items()):
                if owner is not None and owner != consumer and (self.clock_ms - at) > idle and len(out) < n:
                    self.pel[sid] = (fields, consumer, self.clock_ms, count + 1)
                    out.append((sid.encode(), _to_resp_fields(fields)))
            return [b"0-0", out]
        if cmd == "XACK":
            ids = a[3:]
            for sid in ids:
                self.pel.pop(sid, None)
                self.acked.append(sid)
            return len(ids)
        if cmd == "XPENDING":
            # Only *delivered-but-unacked* messages are in a consumer group's PEL.
            # A plain XADD leaves the message on the stream with owner=None; it
            # enters the PEL on XREADGROUP/XAUTOCLAIM. Real XPENDING therefore
            # skips owner=None entries -- and so must this model, otherwise a
            # just-re-queued retry would look "pending" before anyone claims it.
            pending = [(sid, owner, count)
                       for sid, (_, owner, _, count) in self.pel.items()
                       if owner is not None]
            # Summary form (4 args): [count, min, max, consumers]
            if len(a) <= 4:
                return [len(pending), b"0-0", b"0-0", []]
            # Detailed form (6+ args): [[id, consumer, idle_ms, delivery_count], ...]
            return [[sid.encode(), owner.encode(), 0, count]
                    for sid, owner, count in pending]
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


async def test_drain_acks_successes_and_requeues_failures():
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
    assert stats.dead_lettered == 0
    assert stats.ack_failed == 0, "the failed job was re-queued, not dropped or stuck"
    # The three successes are gone; the one failure is re-queued with attempts=1.
    assert await q.pending() == 0, "re-queue ACKs the old PEL entry"
    requeued = [f for _, f in pool.stream if f.get("attempts")]
    assert len(requeued) == 1 and requeued[0]["job_id"] == "2"
    assert requeued[0]["attempts"] == "1"


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
    assert stats.ack_failed == 0
    # The raising job was re-queued for a later attempt; the other two completed.
    requeued = [f for _, f in pool.stream if f.get("attempts")]
    assert len(requeued) == 1 and requeued[0]["job_id"] == "0"


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


# --------------------------------------------------------------- dead letter (Epic 138)
def _dlq_queue(pool, *, max_deliveries=3, consumer="w", min_idle_ms=60_000):
    return WorkQueue(pool, stream="jobs", group="g", consumer=consumer, batch=8,
                     min_idle_ms=min_idle_ms,
                     max_deliveries=max_deliveries, dlq_stream="jobs:dlq")


async def test_pending_counts_reads_delivery_count_from_the_pel():
    pool = FakePool()
    q = _dlq_queue(pool)
    await q.enqueue({"job_id": "a"})
    await q.enqueue({"job_id": "b"})
    ids = [x.stream_id for x in await q.claim()]  # first delivery -> count 1
    counts = await q.pending_counts()
    assert set(counts) == set(ids)
    assert all(c == 1 for c in counts.values())


async def test_pending_counts_reflect_redelivery():
    """An observability metric: XAUTOCLAIM raises a PEL entry's delivery count.

    Only another consumer can claim a message out of this consumer's PEL -- which
    is exactly why drain() does NOT use this number for its retry limit (a
    live-but-failing worker never triggers XAUTOCLAIM). It remains a true statement
    about crashed-worker recovery.
    """
    pool = FakePool()
    w1 = _dlq_queue(pool, min_idle_ms=1_000)
    w1.consumer = "w1"
    await w1.enqueue({"job_id": "a"})
    (item,) = await w1.claim()  # w1 delivery 1
    assert (await w1.pending_counts())[item.stream_id] == 1
    pool.clock_ms += 5000
    w2 = _dlq_queue(pool, min_idle_ms=1_000)
    w2.consumer = "w2"
    (again,) = await w2.claim()  # w2 XAUTOCLAIMs w1's orphan -> delivery 2
    assert again.stream_id == item.stream_id
    assert (await w2.pending_counts())[item.stream_id] == 2


async def test_a_poison_job_is_dead_lettered_after_the_retry_limit():
    pool = FakePool()
    q = _dlq_queue(pool, max_deliveries=2)
    await q.enqueue({"job_id": "poison"})
    # Attempt 1 fails -> re-queued (a NEW stream message with attempts="1"); the
    # old copy is ACKed out of the PEL.
    stats1 = await q.drain(lambda _i: _false())
    assert stats1.delivered == 1 and stats1.dead_lettered == 0
    assert pool.dlq == [], "not yet at the limit"
    assert pool.stream[-1][1]["attempts"] == "1", "re-queued with an attempt counter"
    # Attempt 2 fails -> attempts=2 reaches the limit -> dead-lettered, not re-queued.
    stats2 = await q.drain(lambda _i: _false())
    assert stats2.dead_lettered == 1
    assert len(pool.dlq) == 1, "exactly one DLQ entry"
    assert pool.dlq[0]["job_id"] == "poison"
    assert pool.dlq[0]["attempts"] == "2"
    assert pool.dlq[0]["origin_stream"] == "jobs"
    assert pool.dlq[0]["origin_id"], "the DLQ entry names where it came from"
    assert "dlq_at" in pool.dlq[0]
    assert pool.acked, "both old copies were ACKed out of the main PEL"


async def _false():
    return False


async def test_drain_reports_dead_lettered_job_ids_when_id_field_is_set():
    """Epic 139: drain surfaces the ids of poisoned jobs so the caller can cool them
    down upstream. The generic queue stays unaware of the guard — it just reports ids
    from a named field. Without id_field, the tuple stays empty (no config, no cost).
    """
    pool = FakePool()
    q = WorkQueue(pool, stream="jobs", group="g", consumer="w", batch=8,
                  min_idle_ms=1000, max_deliveries=1, dlq_stream="jobs:dlq",
                  id_field="job_id")
    await q.enqueue({"job_id": "poison-a"})
    await q.enqueue({"job_id": "poison-b"})
    stats = await q.drain(lambda _i: _false())
    assert stats.dead_lettered == 2
    assert set(stats.dead_lettered_ids) == {"poison-a", "poison-b"}


async def test_drain_reports_no_ids_when_id_field_is_unset():
    pool = FakePool()
    q = _dlq_queue(pool, max_deliveries=1)  # no id_field
    await q.enqueue({"job_id": "poison"})
    stats = await q.drain(lambda _i: _false())
    assert stats.dead_lettered == 1
    assert stats.dead_lettered_ids == (), "opt-in: default queue reports no ids"


async def test_drain_skips_empty_id_field_values():
    """A malformed message with no id must not produce an empty cooldown member."""
    pool = FakePool()
    q = WorkQueue(pool, stream="jobs", group="g", consumer="w", batch=8,
                  min_idle_ms=1000, max_deliveries=1, dlq_stream="jobs:dlq",
                  id_field="job_id")
    await q.enqueue({"job_id": ""})
    stats = await q.drain(lambda _i: _false())
    assert stats.dead_lettered == 1
    assert stats.dead_lettered_ids == (), "no empty string leaks into the guard"


async def test_dlq_add_is_bounded_too_so_a_poison_job_cannot_grow_it_forever():
    """A producer re-injecting a poison job each tick starts many lineages; the DLQ
    must be trimmed like the main stream, or it grows without bound. The DB keeps
    the still-NULL row as the source of truth, so a trimmed dead-letter is not lost.
    """
    pool = FakePool()
    q = WorkQueue(pool, stream="jobs", group="g", consumer="w", batch=8,
                  min_idle_ms=1000, maxlen=500, max_deliveries=1, dlq_stream="jobs:dlq")
    await q.enqueue({"job_id": "poison"})
    await q.drain(lambda _i: _false())
    xadds = [c for c in pool.commands if c[0] == "XADD"]
    dlq_add = [c for c in xadds if c[1] == "jobs:dlq"]
    assert len(dlq_add) == 1, dlq_add
    assert dlq_add[0][1:6] == ["jobs:dlq", "MAXLEN", "~", "500", "*"], dlq_add[0]
    # The retry re-queue (main stream) stays bounded as before.
    main_adds = [c for c in xadds if c[1] == "jobs"]
    assert all(c[1:6] == ["jobs", "MAXLEN", "~", "500", "*"] for c in main_adds)


async def test_dlq_write_failure_leaves_the_job_pending_never_dropped():
    pool = FakePool()
    q = _dlq_queue(pool, max_deliveries=1)
    await q.enqueue({"job_id": "poison"})
    # Delivered once; on failure it is already at the limit, so it tries the DLQ.
    pool.xadd_fail = True
    stats = await q.drain(lambda _i: _false())
    assert stats.dead_lettered == 0, "no successful DLQ write"
    assert await q.pending() == 1, "the poison job stays pending -- never silently dropped"
    assert pool.dlq == []


async def test_a_successful_job_is_never_dead_lettered():
    pool = FakePool()
    q = _dlq_queue(pool, max_deliveries=1)  # very low limit
    await q.enqueue({"job_id": "fine"})
    stats = await q.drain(lambda _i: _true())
    assert stats.dead_lettered == 0
    assert stats.ack_failed == 0
    assert pool.dlq == []
    assert await q.pending() == 0


async def _true():
    return True


async def test_without_a_dlq_a_failing_job_is_retried_but_never_dead_lettered():
    """Backward-compatible: no DLQ means retry forever, attempts still visible."""
    pool = FakePool()
    q = _queue(pool)  # no DLQ
    await q.enqueue({"job_id": "poison"})
    for _ in range(4):
        stats = await q.drain(lambda _i: _false())
        assert stats.delivered == 1
        assert stats.dead_lettered == 0
    assert pool.dlq == []
    # Each failure re-queued a fresh message with a rising attempt counter.
    assert pool.stream[-1][1]["attempts"] == "4"
    assert len(pool.stream) == 5, "the original + 4 re-queues"


def test_max_deliveries_requires_a_dlq_stream():
    pool = FakePool()
    with pytest.raises(ValueError):
        WorkQueue(pool, stream="s", group="g", consumer="c", max_deliveries=3)
    with pytest.raises(ValueError):
        WorkQueue(pool, stream="s", group="g", consumer="c", max_deliveries=-1)


async def test_pending_counts_is_fail_open_on_redis_down():
    q = _dlq_queue(FakePool(down=True))
    assert await q.pending_counts() == {}
