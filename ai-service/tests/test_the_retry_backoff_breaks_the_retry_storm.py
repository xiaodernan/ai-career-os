"""A failed job waits out a jittered delay instead of hammering the provider.

Epic 144's integration contract, pinned against an in-memory Redis model that
speaks the sorted-set commands the delay queue needs. The claims that matter:

* with backoff OFF (the default), a failure is XADD-ed straight back — and, the
  zero-drift proof, **no ZSET command is issued at all** (the fake raises on any
  one it does not model, so an accidental ZCARD here would fail the test);
* with backoff ON, a failed job is parked in the delay ZSET with a `not_before`
  score = now + full_jitter(attempts), and is NOT on the main stream, so the next
  tick's `XREADGROUP >` cannot re-claim it immediately;
* `promote_due` returns a job only once `now >= not_before`, and puts it back on
  the stream for a normal claim;
* a poison job (attempts >= max_deliveries) goes straight to the DLQ — backoff
  never delays a known-bad job;
* the two-step promote is failure-safe: a failed XADD leaves the member parked
  (never ZREM-before-XADD), and a corrupt member is dropped so it cannot block
  the head of the range forever.

The clock and rng are injected, so every timing assertion is deterministic and
offline — no sleeps, no real random, no Redis server.
"""

import asyncio
import json

import pytest

from app.core import resp, workqueue
from app.core.workqueue import WorkItem, WorkQueue


class ZsetFakePool:
    """The Epic 140 stream fake plus a sorted set, with deterministic time.

    Deliberately minimal: it models only the commands the backoff path uses and
    RAISES on anything else. That is the zero-drift tripwire — if the off path
    ever starts touching a ZSET, these tests fail loudly rather than silently.
    """

    def __init__(self, *, rng_value: float = 0.0, zadd_fail: bool = False,
                 xadd_fail_for_promote: bool = False) -> None:
        self.now_ms = 1_000_000
        self._rng_value = rng_value
        self.zadd_fail = zadd_fail
        self.xadd_fail_for_promote = xadd_fail_for_promote
        self.zcards: dict[str, list[tuple[float, str]]] = {}  # key -> [(score, member)]
        self.stream: list[tuple[str, dict[str, str]]] = []
        self.dlq: list[dict[str, str]] = []
        self.key = "jobs"
        self.seq = 0
        self.groups: set[str] = set()
        self.pel: dict[str, tuple[dict[str, str], str | None, int, int]] = {}
        self.acked: list[str] = []
        self.commands: list[list[str]] = []

    def clock(self) -> int:
        return self.now_ms

    async def execute(self, *args):
        self.commands.append([str(a) for a in args])
        cmd = str(args[0]).upper()
        a = [str(x) for x in args]

        # ---- sorted set (the delay queue) ----
        if cmd == "ZADD":
            if self.zadd_fail:
                raise resp.RespUnavailable("down")
            key, score, member = a[1], float(a[2]), a[3]
            # ZADD updates the score if the member already exists (Redis semantics).
            bucket = self.zcards.setdefault(key, [])
            for i, (s, m) in enumerate(bucket):
                if m == member:
                    bucket[i] = (score, member)
                    break
            else:
                bucket.append((score, member))
            return 1
        if cmd == "ZRANGEBYSCORE":
            key, lo, hi = a[1], a[2], a[3]
            lo_v = float("-inf") if lo == "-inf" else float(lo)
            hi_v = float("inf") if hi == "+inf" else float(hi)
            rows = sorted((s, m) for s, m in self.zcards.get(key, []) if lo_v <= s <= hi_v)
            limit_n = int(a[a.index("LIMIT") + 2]) if "LIMIT" in a else len(rows)
            return [m.encode() for _, m in rows[:limit_n]]
        if cmd == "ZREM":
            key, member = a[1], a[2]
            bucket = self.zcards.get(key, [])
            before = len(bucket)
            self.zcards[key] = [(s, m) for s, m in bucket if m != member]
            return 1 if len(self.zcards[key]) < before else 0
        if cmd == "ZCARD":
            return len(self.zcards.get(a[1], []))

        # ---- streams (same model as Epic 140) ----
        if cmd == "XGROUP" and a[1].upper() == "CREATE":
            group = a[3]
            if group in self.groups:
                raise resp.RespError("BUSYGROUP Consumer Group name already exists")
            self.groups.add(group)
            return "OK"
        if cmd == "XADD":
            stream_key = a[1]
            rest = a[2:]
            if rest and rest[0].upper() == "MAXLEN":
                assert rest[1] == "~"
                rest = rest[3:]
            assert rest and rest[0] == "*", f"unexpected XADD shape: {a}"
            fields = _to_fields(rest[1:])
            # A promote XADD may be told to fail, to pin never-ZREM-before-XADD.
            if self.xadd_fail_for_promote and stream_key == self.key and fields.get("attempts", "0") != "0":
                raise resp.RespUnavailable("down")
            self.seq += 1
            sid = f"{self.seq}-0"
            if stream_key != self.key:
                self.dlq.append(fields)
                return sid.encode()
            self.stream.append((sid, fields))
            self.pel[sid] = (fields, None, self.now_ms, 0)
            return sid.encode()
        if cmd == "XREADGROUP":
            n = int(a[a.index("COUNT") + 1])
            out = []
            for sid, (fields, owner, _, count) in list(self.pel.items()):
                if owner is None and len(out) < n:
                    consumer = a[a.index("GROUP") + 2]
                    self.pel[sid] = (fields, consumer, self.now_ms, count + 1)
                    out.append((sid.encode(), _to_resp_fields(fields)))
            return [[b"stream", out]] if out else None
        if cmd == "XAUTOCLAIM":
            n = int(a[a.index("COUNT") + 1])
            idle = int(a[4])
            consumer = a[3]
            out = []
            for sid, (fields, owner, at, count) in list(self.pel.items()):
                if owner is not None and owner != consumer and (self.now_ms - at) > idle and len(out) < n:
                    self.pel[sid] = (fields, consumer, self.now_ms, count + 1)
                    out.append((sid.encode(), _to_resp_fields(fields)))
            return [b"0-0", out]
        if cmd == "XACK":
            ids = a[3:]
            for sid in ids:
                self.pel.pop(sid, None)
                self.acked.append(sid)
            return len(ids)
        if cmd == "XPENDING":
            if len(a) >= 3 and a[2] not in self.groups:
                raise resp.RespError(f"NOGROUP No such key '{a[1]}'")
            pending = [(sid, owner, count)
                       for sid, (_, owner, _, count) in self.pel.items()
                       if owner is not None]
            if len(a) <= 4:
                return [len(pending), b"0-0", b"0-0", []]
            return [[sid.encode(), owner.encode(), 0, count]
                    for sid, owner, count in pending]
        if cmd == "XLEN":
            key = a[1]
            if key == self.key:
                return len(self.stream)
            return len(self.dlq)
        if cmd == "PING":
            return "PONG"
        raise AssertionError(f"unexpected command (zero-drift tripwire): {a}")


def _to_fields(tokens: list[str]) -> dict[str, str]:
    return {tokens[i]: tokens[i + 1] for i in range(0, len(tokens), 2)}


def _to_resp_fields(fields: dict[str, str]) -> list[bytes]:
    out: list[bytes] = []
    for k, v in fields.items():
        out.extend((k.encode(), v.encode()))
    return out


def _queue(pool, *, consumer="w1", **backoff) -> WorkQueue:
    """Default backoff OFF; tests opt in explicitly."""
    return WorkQueue(pool, stream="jobs", group="g", consumer=consumer,
                     batch=8, min_idle_ms=1000,
                     now_ms=pool.clock, rng=lambda: pool._rng_value, **backoff)


async def _false(_item: WorkItem) -> bool:
    return False


async def _true(_item: WorkItem) -> bool:
    return True


# --------------------------------------------------------------- ZERO DRIFT (off)
async def test_backoff_off_requeues_immediately_with_no_zset_command():
    """The off path is byte-for-byte the pre-Epic-144 XADD retry.

    The fake raises on any ZSET command it does not expect, so this fails loudly
    if the off path ever touches a sorted set. This is the zero-drift guarantee
    that every existing caller inherits without change.
    """
    pool = ZsetFakePool()
    q = _queue(pool)
    await q.enqueue({"job_id": "a"})
    stats = await q.drain(_false)
    assert stats.delayed == 0 and stats.promoted == 0
    assert stats.delivered == 1
    # Back on the main stream with attempts=1, NOT parked in a ZSET.
    requeued = [f for _, f in pool.stream if f.get("attempts") == "1"]
    assert len(requeued) == 1 and requeued[0]["job_id"] == "a"
    assert pool.zcards == {}, "off path must not create or touch a delay set"
    assert not any(c[0].startswith("Z") for c in pool.commands), pool.commands


async def test_backoff_off_snapshot_issues_no_zcard():
    pool = ZsetFakePool()
    q = _queue(pool)
    snap = await q.snapshot()
    assert snap["delayed_enabled"] is False
    assert snap["delayed_len"] == 0
    assert not any(c[0] == "ZCARD" for c in pool.commands), pool.commands


# --------------------------------------------------------------- ON: park + promote
async def test_failed_job_is_parked_not_immediately_requeued():
    pool = ZsetFakePool(rng_value=0.0)  # delay = 0, but STILL parked until promote
    q = _queue(pool, backoff_base_ms=1000, backoff_cap_ms=30_000)
    await q.enqueue({"job_id": "a"})
    stats = await q.drain(_false)
    assert stats.delayed == 1
    assert stats.promoted == 0
    # Not on the main stream as a retry — the only stream entry is the original
    # (XACK leaves it retained but out of the PEL).
    assert all(f.get("attempts") != "1" for _, f in pool.stream)
    # Parked in the delay set with attempts=1.
    members = pool.zcards["jobs:delayed"]
    assert len(members) == 1
    score, member = members[0]
    assert score == pool.now_ms + 0, "rng=0 => zero jitter, parked at now"
    payload = json.loads(member.split("\x1f", 1)[1])
    assert payload["job_id"] == "a" and payload["attempts"] == "1"
    # Not claimable: PEL is empty after ACK, and there is no new stream message.
    assert await q.pending() == 0


async def test_promote_waits_until_not_before_then_returns_the_job_to_the_stream():
    pool = ZsetFakePool(rng_value=1.0)  # delay = full ceiling = base (attempt 1)
    q = _queue(pool, backoff_base_ms=2000, backoff_cap_ms=30_000)
    await q.enqueue({"job_id": "a"})
    await q.drain(_false)
    assert len(pool.zcards["jobs:delayed"]) == 1

    # Before not_before: promote moves nothing, member stays parked.
    pool.now_ms += 1999
    assert await q.promote_due() == 0
    assert len(pool.zcards["jobs:delayed"]) == 1
    assert all(f.get("attempts") != "1" for _, f in pool.stream)

    # At not_before: promoted back onto the stream, member removed.
    pool.now_ms += 1
    assert await q.promote_due() == 1
    assert pool.zcards["jobs:delayed"] == []
    assert any(f.get("attempts") == "1" and f["job_id"] == "a"
               for _, f in pool.stream)


async def test_drain_promotes_matured_jobs_in_the_same_pass():
    """drain() calls promote_due first, so a matured job costs no extra tick."""
    pool = ZsetFakePool(rng_value=0.0)
    q = _queue(pool, backoff_base_ms=1000)
    await q.enqueue({"job_id": "a"})
    await q.drain(_false)               # parked at now
    pool.now_ms += 10                   # now matured
    seen = []

    async def handler(item: WorkItem) -> bool:
        seen.append(item.value("job_id"))
        return True

    stats = await q.drain(handler)      # should promote AND claim in this pass
    assert stats.promoted == 1
    assert seen == ["a"], "the promoted retry was claimed in the same drain"
    assert pool.zcards["jobs:delayed"] == []


async def test_repeated_failures_bump_attempts_and_widen_the_window():
    """Each failure re-parks with attempts+1; ceiling grows exponentially."""
    pool = ZsetFakePool(rng_value=1.0)  # delay == ceiling, so scores are exact
    q = _queue(pool, backoff_base_ms=100, backoff_cap_ms=100_000)
    await q.enqueue({"job_id": "a"})

    expected = [100, 200, 400, 800]  # base * 2**(attempts-1), the ceiling per attempt
    for i, want in enumerate(expected, start=1):
        # Advance past the previously parked job's not_before so drain promotes it.
        # For i=1 there is nothing parked yet; the advance is harmless.
        pool.now_ms += want
        stats = await q.drain(_false)
        assert stats.promoted == (1 if i > 1 else 0), "prior attempt matured and returned"
        assert stats.delayed == 1, "this failure re-parked with attempts+1"
        bucket = pool.zcards["jobs:delayed"]
        assert len(bucket) == 1
        score, member = bucket[0]
        payload = json.loads(member.split("\x1f", 1)[1])
        assert payload["attempts"] == str(i)
        # The job was parked at the current `now`; full jitter with rng=1.0 draws
        # the WHOLE ceiling. So not_before - park_now == this attempt's ceiling,
        # which doubles each iteration: 100, 200, 400, 800.
        assert score == pool.now_ms + want, f"attempt {i} window should be {want}ms"


# --------------------------------------------------------------- ON: failure safety
async def test_poison_job_skips_backoff_and_goes_straight_to_dlq():
    """Backoff paces retries; it must not delay a known-bad job's dead-letter."""
    pool = ZsetFakePool(rng_value=0.0)
    q = WorkQueue(pool, stream="jobs", group="g", consumer="w", batch=8,
                  min_idle_ms=1000, backoff_base_ms=5000,
                  max_deliveries=1, dlq_stream="jobs:dlq")
    await q.enqueue({"job_id": "poison"})
    stats = await q.drain(_false)
    assert stats.dead_lettered == 1
    assert stats.delayed == 0, "poison bypassed the delay set"
    assert len(pool.dlq) == 1 and pool.dlq[0]["job_id"] == "poison"
    assert pool.zcards == {}, "no parked entry for a dead-lettered job"


async def test_failed_zadd_keeps_the_job_pending_never_dropped():
    pool = ZsetFakePool(zadd_fail=True)
    q = _queue(pool, backoff_base_ms=1000)
    await q.enqueue({"job_id": "a"})
    stats = await q.drain(_false)
    assert stats.delayed == 0
    assert stats.ack_failed >= 1, "a failed park is reported, job stays in PEL"
    assert await q.pending() == 1, "never ACKed — XAUTOCLAIM can recover it"
    assert pool.zcards == {}


async def test_failed_promote_xadd_leaves_the_member_parked():
    """ZREM must never run before a successful XADD — a lose-on-crash bug."""
    pool = ZsetFakePool(rng_value=0.0, xadd_fail_for_promote=True)
    q = _queue(pool, backoff_base_ms=1000)
    await q.enqueue({"job_id": "a"})
    await q.drain(_false)               # parked
    pool.now_ms += 10
    assert await q.promote_due() == 0, "promote failed, nothing moved"
    assert len(pool.zcards["jobs:delayed"]) == 1, "member stays parked, not dropped"


async def test_corrupt_member_is_dropped_so_it_cannot_block_the_head():
    pool = ZsetFakePool(rng_value=0.0)
    q = _queue(pool, backoff_base_ms=1000)
    # Inject a malformed member at a very early score.
    pool.zcards["jobs:delayed"] = [(0.0, "garbage-no-separator")]
    assert await q.promote_due() == 0
    assert pool.zcards["jobs:delayed"] == [], "the poison member was cleared"


# --------------------------------------------------------------- ON: observability
async def test_delay_set_is_observable_and_counts_parked_jobs():
    pool = ZsetFakePool(rng_value=1.0)
    q = _queue(pool, backoff_base_ms=1000)
    assert await q.delayed_len() == 0
    await q.enqueue({"job_id": "a"})
    await q.drain(_false)
    assert await q.delayed_len() == 1
    snap = await q.snapshot()
    assert snap["delayed_enabled"] is True
    assert snap["delayed_len"] == 1
    assert snap["ok"] is True, "reading the delay set is a known, healthy state"
    pool.now_ms += 1000  # rng=1.0 => the parked job's not_before is now reached
    assert await q.promote_due() == 1
    assert await q.delayed_len() == 0


async def test_delayed_len_is_fail_open():
    class Down(ZsetFakePool):
        async def execute(self, *args):
            if str(args[0]).upper() == "ZCARD":
                raise resp.RespUnavailable("down")
            return await super().execute(*args)

    q = _queue(Down(), backoff_base_ms=1000)
    assert await q.delayed_len() == 0, "a failed ZCARD degrades to 0, never raises"
    snap = await q.snapshot()
    assert snap["delayed_len"] == 0
    assert snap["ok"] is False, "but ok flips so the health report says unknown"


# --------------------------------------------------------------- construction
def test_rejects_negative_backoff_knobs():
    pool = ZsetFakePool()
    with pytest.raises(ValueError):
        _queue(pool, backoff_base_ms=-1)
    with pytest.raises(ValueError):
        _queue(pool, backoff_base_ms=100, backoff_cap_ms=-5)


def test_delay_zset_key_is_derived_from_the_stream_by_default():
    q = _queue(ZsetFakePool(), backoff_base_ms=1000)
    assert q.delay_zset == "jobs:delayed"
    q2 = WorkQueue(ZsetFakePool(), stream="jobs", group="g", consumer="w",
                   backoff_base_ms=1000, delay_zset="custom:delay")
    assert q2.delay_zset == "custom:delay"


# --------------------------------------------------------------- the real worker wiring
def test_the_real_worker_factory_turns_backoff_on_from_settings(monkeypatch):
    """The value claim of Epic 144: a shipped worker has backoff ON by default.

    Without this seam test, a wiring slip (a forgotten kwarg) would silently leave
    production on the old immediate-requeue path while every unit test still passed
    — the exact "a knob nothing reads" failure the env census cannot catch. We
    assert the factory builds a WorkQueue carrying the Settings values.
    """
    from types import SimpleNamespace

    from app.ops import embed_workers

    monkeypatch.setattr(
        embed_workers, "get_settings",
        lambda: SimpleNamespace(
            work_queue_claim_ms=120_000, work_queue_maxlen=10_000,
            work_queue_max_deliveries=5,
            work_queue_dlq_stream="jobs:dlq",
            work_queue_backoff_base_ms=750,
            work_queue_backoff_cap_ms=45_000))
    q = embed_workers._queue(ZsetFakePool())
    assert q.backoff_base_ms == 750, "the factory must pass the base through"
    assert q.backoff_cap_ms == 45_000, "the factory must pass the cap through"
    assert q.delay_zset == "careeros:jobs:embed:delayed"


def test_the_worker_factory_defaults_to_backoff_on_when_settings_lack_the_field(monkeypatch):
    """A half-rolled-out Settings (old image, new code) still gets the fix.

    ``getattr(settings, ..., 500)`` is deliberate: an older deployment whose env
    predates Epic 144 must not silently fall back to the storm behaviour. The
    constructor default 0 (zero drift for direct callers/fakes) and the worker
    default 500 (fix on for production) are two *different* intentional defaults.
    """
    from types import SimpleNamespace

    from app.ops import embed_workers

    monkeypatch.setattr(
        embed_workers, "get_settings",
        lambda: SimpleNamespace(work_queue_claim_ms=120_000,
                                work_queue_maxlen=10_000,
                                work_queue_max_deliveries=0))
    q = embed_workers._queue(ZsetFakePool())
    assert q.backoff_base_ms == 500
    assert q.backoff_cap_ms == 30_000
