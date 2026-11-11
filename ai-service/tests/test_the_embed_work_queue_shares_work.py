"""`work_queue_backend=redis`: N replicas share job embedding instead of N× billing.

The single-process `embed_loop` scans `jobs WHERE embedding IS NULL` on **every**
replica. Three replicas = the same NULL rows embedded three times (three model
calls, three bills) and no recovery for a replica that dies mid-batch. This file
pins the opt-in work-queue path that fixes that, without touching the default:

* the producer enqueues only ids of jobs still needing a vector (small stream, the
  text/embedding work stays with the consumer);
* a consumer embeds its claimed share and ACKs;
* the handler is idempotent — a re-claimed job already written costs a SELECT, not
  a second embedding call, and the UPDATE itself carries `AND embedding IS NULL`;
* malformed messages are ACKed (do not poison the PEL), provider failures stay
  pending for XAUTOCLAIM;
* Redis-down is fail-open: the caller keeps its DB-scan fallback;
* `main` chooses the distributed loop only when the knob says `redis`.

At-least-once is the honest contract; the idempotence above is what makes it safe.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.core import resp, workqueue
from app.ops import embed_workers
from app.ops.embed_workers import embed_one, producer_pass, consumer_pass


class _Row(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key) from None


class _FakeEmbedder:
    def __init__(self, n=1, dim=3):
        self.n, self.dim = n, dim
        self.calls = 0

    async def embed(self, texts):
        self.calls += 1
        # Return exactly `n` vectors, independent of the number of texts -- lets a
        # test simulate a provider that answers the wrong count.
        return [[0.1] * self.dim for _ in range(self.n)]


class _FakeQueue:
    def __init__(self, *, down=False, dead_lettered_ids=(), parked=(), parked_error=None):
        self.down = down
        self.enqueued = []
        self.acked = []
        self.items = []
        self.drained_with = None
        # When set, drain() reports these as dead-lettered, so consumer_pass cools them.
        self.dead_lettered_ids = tuple(dead_lettered_ids)
        # Epic 145: ids waiting out a retry backoff. These must be suppressed in BOTH
        # passes exactly like cooldown ids; a separate failure injection proves the two
        # sources are read independently (one outage must not blank the other).
        self.parked = set(parked)
        self.parked_error = parked_error
        self.parked_calls = 0

    async def enqueue(self, fields):
        if self.down:
            raise resp.RespUnavailable("down")
        self.enqueued.append(fields)
        return f"{len(self.enqueued)}-0"

    async def parked_ids(self):
        self.parked_calls += 1
        if self.parked_error:
            raise self.parked_error
        return set(self.parked)

    async def drain(self, handler):
        self.drained_with = handler
        results = [await handler(item) for item in self.items]
        ok = [it.stream_id for it, good in zip(self.items, results) if good]
        self.acked.extend(ok)
        return workqueue.ClaimStats(
            delivered=len(self.items), ack_failed=sum(not r for r in results),
            dead_lettered=len(self.dead_lettered_ids),
            dead_lettered_ids=self.dead_lettered_ids)

    async def ensure_group(self):
        if self.down:
            raise resp.RespUnavailable("down")


class _StubGuard:
    """Only the guard surface the embed passes use; its own semantics are pinned in
    test_the_dead_letter_guard_bounds_poison_jobs.py."""

    def __init__(self, *, enabled=True, active=(), cooldown_s=900, active_error=None):
        self.enabled = enabled
        self.cooldown_s = cooldown_s
        self._active = set(active)
        self.active_error = active_error
        self.marked = []
        self.active_calls = 0

    async def active(self):
        self.active_calls += 1
        if self.active_error:
            raise self.active_error
        return set(self._active)

    async def mark(self, ids, *, now=None):
        self.marked.append(tuple(ids))
        self._active.update(ids)
        return len(list(ids))


def _item(job_id, sid="1-0"):
    return workqueue.WorkItem(sid, {"job_id": job_id})


JOB_A = "00000000-0000-0000-0000-000000000001"
JOB_B = "00000000-0000-0000-0000-000000000002"


# --------------------------------------------------------------- producer
async def test_producer_enqueues_only_the_ids_of_jobs_needing_vectors(monkeypatch):
    rows = [_Row(id="a"), _Row(id="b")]
    sqls = []

    async def fake_fetch(sql, *args):
        sqls.append(sql)
        return rows

    monkeypatch.setattr(embed_workers.db, "fetch", fake_fetch)
    q = _FakeQueue()
    assert await producer_pass(q) == 2
    assert q.enqueued == [{"job_id": "a"}, {"job_id": "b"}]
    assert "embedding IS NULL" in sqls[0]
    assert "j.id::text" in sqls[0], "the stream carries ids, not full rows"


async def test_producer_limits_the_scan_when_asked(monkeypatch):
    args_seen = []

    async def fake_fetch(sql, *args):
        args_seen.append(args)
        return []

    monkeypatch.setattr(embed_workers.db, "fetch", fake_fetch)
    await producer_pass(_FakeQueue(), limit=5)
    assert args_seen == [(5,)]


async def test_producer_is_fail_open_on_redis_down(monkeypatch):
    async def fake_fetch(sql, *args):
        return [_Row(id="a"), _Row(id="b")]

    monkeypatch.setattr(embed_workers.db, "fetch", fake_fetch)
    q = _FakeQueue(down=True)
    assert await producer_pass(q) == 0, "it reports what it sent; the loop falls back"


# --------------------------------------------------------------- Epic 139: producer suppression
async def test_producer_pushes_suppressed_ids_into_sql_not_a_python_filter(monkeypatch):
    """A SQL LIMIT must count only ELIGIBLE rows; a post-filter would let suppressed
    ids fill the batch and starve older embeddable jobs."""
    calls = []

    async def fake_fetch(sql, *args):
        calls.append((sql, args))
        return []

    monkeypatch.setattr(embed_workers.db, "fetch", fake_fetch)
    guard = _StubGuard(active={JOB_A})
    await producer_pass(_FakeQueue(), limit=5, guard=guard)
    sql, args = calls[0]
    assert "NOT (j.id = ANY($1::uuid[]))" in sql, sql
    assert "embedding IS NULL" in sql
    assert args[0] == [JOB_A] and args[1] == 5, "suppression binds before LIMIT"
    assert "LIMIT $2" in sql, sql
    assert guard.active_calls == 1, "one batched guard read per pass"


async def test_producer_without_suppression_keeps_the_original_sql(monkeypatch):
    """Backward compatible: no suppressed ids -> no array bind, LIMIT stays $1."""
    calls = []

    async def fake_fetch(sql, *args):
        calls.append((sql, args))
        return []

    monkeypatch.setattr(embed_workers.db, "fetch", fake_fetch)
    await producer_pass(_FakeQueue(), limit=5, guard=_StubGuard(active=set()))
    sql, args = calls[0]
    assert "ANY(" not in sql, sql
    assert "LIMIT $1" in sql and args == (5,)


async def test_producer_works_with_no_guard_at_all(monkeypatch):
    """Pure Epic 138 behaviour when the guard is not wired in (default/off)."""
    calls = []

    async def fake_fetch(sql, *args):
        calls.append((sql, args))
        return []

    monkeypatch.setattr(embed_workers.db, "fetch", fake_fetch)
    await producer_pass(_FakeQueue(), limit=5)
    sql, args = calls[0]
    assert "ANY(" not in sql and args == (5,)


async def test_producer_drops_malformed_suppressed_ids_before_the_uuid_bind(monkeypatch):
    calls = []

    async def fake_fetch(sql, *args):
        calls.append((sql, args))
        return []

    monkeypatch.setattr(embed_workers.db, "fetch", fake_fetch)
    guard = _StubGuard(active={JOB_A, "not-a-uuid"})
    await producer_pass(_FakeQueue(), guard=guard)
    sql, args = calls[0]
    assert "ANY(" in sql
    assert args == ([JOB_A],), "only a valid uuid reaches the ::uuid[] bind"


async def test_producer_is_fail_open_when_the_guard_read_errors(monkeypatch):
    """A guard outage degrades to 'enqueue everything', never to lost recall."""
    calls = []

    async def fake_fetch(sql, *args):
        calls.append((sql, args))
        return []

    monkeypatch.setattr(embed_workers.db, "fetch", fake_fetch)
    guard = _StubGuard(active_error=resp.RespUnavailable("down"))
    await producer_pass(_FakeQueue(), limit=5, guard=guard)
    sql, args = calls[0]
    assert "ANY(" not in sql and args == (5,), "the suppression clause vanished"


# --------------------------------------------------------------- Epic 145: dual-source suppression
async def test_producer_suppresses_both_cooldown_and_parked_ids(monkeypatch):
    """The producer must exclude BOTH sources in SQL. A parked job still has
    embedding IS NULL, so re-selecting it next tick would XADD a fresh attempts=0
    copy and bypass the backoff Epic 144 just built."""
    calls = []

    async def fake_fetch(sql, *args):
        calls.append((sql, args))
        return []

    monkeypatch.setattr(embed_workers.db, "fetch", fake_fetch)
    guard = _StubGuard(active={JOB_A})
    q = _FakeQueue(parked={JOB_B})
    await producer_pass(q, guard=guard)
    sql, args = calls[0]
    assert "NOT (j.id = ANY($1::uuid[]))" in sql
    assert set(args[0]) == {JOB_A, JOB_B}, "both sources unioned before the uuid bind"


async def test_producer_merges_overlapping_sources_without_duplicates(monkeypatch):
    """An id that is both cooling down and parked must not be bound twice — the
    ::uuid[] array is a set, and duplication would only waste bind width."""
    calls = []

    async def fake_fetch(sql, *args):
        calls.append((sql, args))
        return []

    monkeypatch.setattr(embed_workers.db, "fetch", fake_fetch)
    guard = _StubGuard(active={JOB_A, JOB_B})
    q = _FakeQueue(parked={JOB_B})
    await producer_pass(q, guard=guard)
    args = calls[0][1]
    assert sorted(args[0]) == [JOB_A, JOB_B]


async def test_producer_parked_read_error_still_honours_the_guard(monkeypatch):
    """Independent reads: an outage in parked_ids must NOT blank the cooldown source
    (nor vice versa). Suppressing only one still closes that source's storm hole."""
    calls = []

    async def fake_fetch(sql, *args):
        calls.append((sql, args))
        return []

    monkeypatch.setattr(embed_workers.db, "fetch", fake_fetch)
    guard = _StubGuard(active={JOB_A})
    q = _FakeQueue(parked_error=resp.RespUnavailable("delay zset down"))
    await producer_pass(q, guard=guard)
    args = calls[0][1]
    assert args[0] == [JOB_A], "cooldown survives the parked read failing"


async def test_producer_guard_error_still_honours_parked_ids(monkeypatch):
    """The mirror case: a guard outage must NOT blank the parked/backoff source."""
    calls = []

    async def fake_fetch(sql, *args):
        calls.append((sql, args))
        return []

    monkeypatch.setattr(embed_workers.db, "fetch", fake_fetch)
    guard = _StubGuard(active_error=resp.RespUnavailable("guard down"))
    q = _FakeQueue(parked={JOB_B})
    await producer_pass(q, guard=guard)
    args = calls[0][1]
    assert args[0] == [JOB_B], "backoff suppression survives the guard read failing"


async def test_consumer_acks_a_parked_duplicate_without_a_model_call(monkeypatch):
    """At-least-once copies of a backing-off job can still sit on the stream. The
    consumer must ACK them for free, or a parked job gets embedded on every tick
    despite the delay ZSET — the exact hole this Epic closes on the consumer side."""
    monkeypatch.setattr("app.providers.registry.embeddings_ready", lambda _s: True)
    called = []

    async def fake_embed_one(job_id):
        called.append(job_id)
        return True

    monkeypatch.setattr(embed_workers, "embed_one", fake_embed_one)
    q = _FakeQueue(parked={JOB_A})
    q.items = [_item(JOB_A, "1-0"), _item(JOB_B, "2-0")]
    await consumer_pass(q)
    assert called == [JOB_B], "the parked id never reached the provider"
    assert q.acked == ["1-0", "2-0"], "both copies leave the PEL"


async def test_consumer_guard_error_still_acks_parked_duplicates(monkeypatch):
    """Consumer-side independence: even with the guard down, a parked duplicate is
    still recognised and ACKed for free by the backoff source."""
    monkeypatch.setattr("app.providers.registry.embeddings_ready", lambda _s: True)
    called = []

    async def fake_embed_one(job_id):
        called.append(job_id)
        return True

    monkeypatch.setattr(embed_workers, "embed_one", fake_embed_one)
    q = _FakeQueue(parked={JOB_A})
    q.items = [_item(JOB_A, "1-0")]
    guard = _StubGuard(active_error=resp.RespUnavailable("guard down"))
    await consumer_pass(q, guard=guard)
    assert called == [], "parked suppression survives the guard read failing"
    assert q.acked == ["1-0"]


async def test_parked_ids_is_not_read_when_backoff_is_disabled(monkeypatch):
    """Zero-drift at the call site: a queue built with backoff off returns no parked
    ids and the pass behaves exactly as Epic 138/139 (no backoff coupling)."""
    calls = []

    async def fake_fetch(sql, *args):
        calls.append((sql, args))
        return []

    monkeypatch.setattr(embed_workers.db, "fetch", fake_fetch)
    await producer_pass(_FakeQueue(), limit=5, guard=_StubGuard(active=set()))
    sql, args = calls[0]
    assert "ANY(" not in sql and args == (5,)


# --------------------------------------------------------------- handler idempotence
async def test_a_reclaimed_job_already_written_costs_no_model_call(monkeypatch):
    async def fake_fetchrow(sql, *args):
        assert "embedding IS NULL" in sql, "the re-check is the idempotence barrier"
        return None  # already written by the worker that crashed before ACK

    monkeypatch.setattr(embed_workers.db, "fetchrow", fake_fetchrow)
    monkeypatch.setattr("app.providers.registry.get_embeddings",
                        lambda _s: pytest.fail("provider must not be touched"))
    assert await embed_one("job-1") is True


async def test_an_empty_job_is_acked_without_a_model_call(monkeypatch):
    async def fake_fetchrow(sql, *args):
        return _Row(title="", skills=[], description=None)

    monkeypatch.setattr(embed_workers.db, "fetchrow", fake_fetchrow)
    monkeypatch.setattr("app.providers.registry.get_embeddings",
                        lambda _s: pytest.fail("no text, no embed"))
    assert await embed_one("job-1") is True


async def test_a_real_job_is_embedded_and_written_with_the_null_guard(monkeypatch):
    async def fake_fetchrow(sql, *args):
        return _Row(title="Backend", skills=["Go"], description="Build things",
                    location="Shanghai", remote_type="hybrid", employment_type="full_time",
                    requirements=None, nice_to_have=None, responsibilities=None)

    updates = []
    async def fake_execute(sql, *args):
        updates.append((sql, args))

    embedder = _FakeEmbedder(n=1)
    monkeypatch.setattr(embed_workers.db, "fetchrow", fake_fetchrow)
    monkeypatch.setattr(embed_workers.db, "execute", fake_execute)
    monkeypatch.setattr(embed_workers.db, "vec", lambda v: "[" + ",".join(map(str, v)) + "]")
    monkeypatch.setattr("app.providers.registry.get_embeddings", lambda _s: embedder)

    assert await embed_one("job-1") is True
    assert embedder.calls == 1
    assert "AND embedding IS NULL" in updates[0][0], "a concurrent writer cannot be overwritten"
    assert updates[0][1][0] == "job-1"


async def test_a_provider_returning_the_wrong_count_fails_the_job(monkeypatch):
    async def fake_fetchrow(sql, *args):
        return _Row(title="Backend", skills=["Go"])

    monkeypatch.setattr(embed_workers.db, "fetchrow", fake_fetchrow)
    monkeypatch.setattr("app.providers.registry.get_embeddings",
                        lambda _s: _FakeEmbedder(n=2))
    assert await embed_one("job-1") is False, "stays pending for recovery"


# --------------------------------------------------------------- consumer
async def test_consumer_does_nothing_when_no_provider_is_configured(monkeypatch):
    monkeypatch.setattr("app.providers.registry.embeddings_ready", lambda _s: False)
    q = _FakeQueue()
    stats = await consumer_pass(q)
    assert stats.delivered == 0
    assert q.drained_with is None, "it must not claim work it cannot do"


async def test_consumer_acks_successes_and_leaves_failures_pending(monkeypatch):
    monkeypatch.setattr("app.providers.registry.embeddings_ready", lambda _s: True)
    q = _FakeQueue()
    q.items = [_item("ok", "1-0"), _item("bad", "2-0"), _item("", "3-0")]

    async def fake_embed_one(job_id):
        return job_id != "bad"

    monkeypatch.setattr(embed_workers, "embed_one", fake_embed_one)
    stats = await consumer_pass(q)
    assert stats.delivered == 3
    assert q.acked == ["1-0", "3-0"], "the bad job stays pending; malformed is acked"


async def test_consumer_survives_a_handler_exception(monkeypatch):
    monkeypatch.setattr("app.providers.registry.embeddings_ready", lambda _s: True)
    q = _FakeQueue()
    q.items = [_item("boom", "1-0"), _item("fine", "2-0")]

    async def flaky(job_id):
        if job_id == "boom":
            raise RuntimeError("provider exploded")
        return True

    monkeypatch.setattr(embed_workers, "embed_one", flaky)
    stats = await consumer_pass(q)
    assert q.acked == ["2-0"]
    assert stats.ack_failed == 1


# --------------------------------------------------------------- Epic 139: consumer cooldown
async def test_consumer_acks_a_cooling_down_duplicate_without_a_model_call(monkeypatch):
    """Producer stops new enqueues, but at-least-once duplicates may already sit in
    the stream. They must be ACKed for free, not spend another embedding call."""
    monkeypatch.setattr("app.providers.registry.embeddings_ready", lambda _s: True)
    called = []

    async def fake_embed_one(job_id):
        called.append(job_id)
        return True

    monkeypatch.setattr(embed_workers, "embed_one", fake_embed_one)
    q = _FakeQueue()
    q.items = [_item(JOB_A, "1-0"), _item(JOB_B, "2-0")]
    guard = _StubGuard(active={JOB_A})
    await consumer_pass(q, guard=guard)
    assert called == [JOB_B], "the cooling-down id never reached the provider"
    assert q.acked == ["1-0", "2-0"], "both copies leave the PEL"
    assert guard.active_calls == 1, "one batched read for the whole pass"


async def test_consumer_marks_dead_lettered_ids_into_the_guard(monkeypatch):
    """The other half of the loop: drain's dead-lettered ids become cooldown members
    so the NEXT producer pass excludes them in SQL."""
    monkeypatch.setattr("app.providers.registry.embeddings_ready", lambda _s: True)
    q = _FakeQueue(dead_lettered_ids=(JOB_A, JOB_B))
    guard = _StubGuard(active=set(), cooldown_s=900)
    await consumer_pass(q, guard=guard)
    assert guard.marked == [(JOB_A, JOB_B)]
    assert await guard.active() == {JOB_A, JOB_B}, "marked ids are now suppressed"


async def test_consumer_is_fail_open_when_the_guard_read_errors(monkeypatch):
    """A guard outage must not stop the consumer doing its real work."""
    monkeypatch.setattr("app.providers.registry.embeddings_ready", lambda _s: True)
    called = []

    async def fake_embed_one(job_id):
        called.append(job_id)
        return True

    monkeypatch.setattr(embed_workers, "embed_one", fake_embed_one)
    q = _FakeQueue()
    q.items = [_item(JOB_A, "1-0")]
    guard = _StubGuard(active_error=resp.RespUnavailable("down"))
    await consumer_pass(q, guard=guard)
    assert called == [JOB_A], "the job was still embedded despite the guard outage"


async def test_consumer_with_no_guard_is_pure_epic_138(monkeypatch):
    """Backward compatible: no guard -> every item goes to the handler."""
    monkeypatch.setattr("app.providers.registry.embeddings_ready", lambda _s: True)
    called = []

    async def fake_embed_one(job_id):
        called.append(job_id)
        return True

    monkeypatch.setattr(embed_workers, "embed_one", fake_embed_one)
    q = _FakeQueue()
    q.items = [_item(JOB_A, "1-0")]
    await consumer_pass(q)
    assert called == [JOB_A]


async def test_a_disabled_guard_is_inert_in_both_passes(monkeypatch):
    """cooldown_s=0 (the off knob) -> no suppression, no marking, no active read."""
    calls = []

    async def fake_fetch(sql, *args):
        calls.append((sql, args))
        return []

    monkeypatch.setattr(embed_workers.db, "fetch", fake_fetch)
    guard = _StubGuard(enabled=False, active={JOB_A})
    await producer_pass(_FakeQueue(), limit=5, guard=guard)
    assert "ANY(" not in calls[0][0]
    assert guard.active_calls == 0, "a disabled guard is not even read"


# --------------------------------------------------------------- wiring
def test_main_chooses_the_distributed_loop_only_when_the_knob_is_redis():
    """Read it back from main's source so a wiring regression is caught offline."""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "app" / "main.py").read_text(encoding="utf-8")
    assert 'work_queue_backend' in src
    assert 'embed_loop_distributed' in src
    assert "== \"redis\"" in src, "the switch must be gated on the redis value"


def test_consumer_name_is_stable_per_process_format():
    name = embed_workers._consumer_name()
    assert isinstance(name, str) and len(name) == 12
    assert name != embed_workers._consumer_name(), "each process gets its own PEL identity"


# --------------------------------------------------------------- Epic 139: wiring
def test_queue_names_the_id_field_when_the_dlq_is_on(monkeypatch):
    """drain() can only report dead-lettered job ids if the queue knows the field."""
    settings = SimpleNamespace(work_queue_max_deliveries=5, work_queue_dlq_stream="dlq",
                               work_queue_claim_ms=120_000, work_queue_maxlen=10_000)
    monkeypatch.setattr(embed_workers, "get_settings", lambda: settings)
    q = embed_workers._queue(FakePoolForFactory())
    assert q.id_field == "job_id"
    assert q.max_deliveries == 5 and q.dlq_stream == "dlq"


def test_queue_leaves_id_field_empty_when_the_dlq_is_off(monkeypatch):
    settings = SimpleNamespace(work_queue_max_deliveries=0, work_queue_dlq_stream="dlq",
                               work_queue_claim_ms=120_000, work_queue_maxlen=10_000)
    monkeypatch.setattr(embed_workers, "get_settings", lambda: settings)
    q = embed_workers._queue(FakePoolForFactory())
    assert q.id_field == "", "no DLQ -> drain reports no ids -> nothing to cool down"
    assert q.max_deliveries == 0 and q.dlq_stream == ""


def test_guard_factory_reads_the_cooldown_knobs(monkeypatch):
    settings = SimpleNamespace(work_queue_dlq_cooldown_s=1234,
                               work_queue_dlq_guard_key="my:guard")
    monkeypatch.setattr(embed_workers, "get_settings", lambda: settings)
    g = embed_workers._guard(FakePoolForFactory())
    assert g.enabled is True
    assert g.cooldown_s == 1234 and g.key == "my:guard"


def test_guard_factory_disables_on_zero_cooldown(monkeypatch):
    settings = SimpleNamespace(work_queue_dlq_cooldown_s=0,
                               work_queue_dlq_guard_key="my:guard")
    monkeypatch.setattr(embed_workers, "get_settings", lambda: settings)
    g = embed_workers._guard(FakePoolForFactory())
    assert g.enabled is False, "the off knob gives pure Epic 138 behaviour"


def test_the_loop_wires_one_guard_into_both_passes():
    """Source contract: the guard is built once and threaded to producer + consumer,
    so the two halves of the cooldown loop cannot silently drift apart."""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "app" / "ops" / "embed_workers.py").read_text(
        encoding="utf-8")
    assert "guard = _guard(pool)" in src
    assert "producer_pass(queue, guard=guard)" in src
    assert "consumer_pass(queue, guard=guard)" in src


def test_both_passes_merge_the_two_suppression_sources():
    """Source contract (Epic 145): both passes call the same dual-source merge with
    the queue AND guard. A single-source regression (e.g. consumer still calling
    ``_suppressed(guard)``) would silently reopen the producer re-injection storm."""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "app" / "ops" / "embed_workers.py").read_text(
        encoding="utf-8")
    assert src.count("await _suppressed(queue, guard)") == 2, \
        "producer and consumer must both union parked ids and cooldown ids"
    assert "await _suppressed(guard)" not in src, "no single-source call site may remain"


async def test_operator_release_all_clears_the_cooldown_set(monkeypatch):
    """The documented 'requeue after an incident' path: release_all -> empty set."""
    from app.core import dlq_guard

    pool = _ReleaseFakePool()
    guard = dlq_guard.DlqGuard(pool, key="k", cooldown_s=900)
    await guard.mark([JOB_A, JOB_B])
    assert await guard.release_all() == 2
    assert await guard.active(now=1000.0) == set()


class FakePoolForFactory:
    """The factories only store the pool; no command is issued in these tests."""

    async def execute(self, *args):
        raise AssertionError("factory tests must not touch Redis")


class _ReleaseFakePool:
    """Minimal ZSET for the operator-release path test."""

    def __init__(self):
        self.rows = {}

    async def execute(self, *args):
        a = [str(x) for x in args]
        if a[0] == "ZADD":
            for i in range(2, len(a) - 1, 2):
                self.rows[a[i + 1]] = float(a[i])
            return 2
        if a[0] == "ZREMRANGEBYSCORE":
            gone = list(self.rows)
            self.rows.clear()
            return len(gone)
        if a[0] == "ZRANGEBYSCORE":
            lo = a[2]
            thr = float(lo[1:]) if lo.startswith("(") else 0.0
            return [m.encode() for m, s in self.rows.items() if s > thr]
        raise AssertionError(a)

    async def pipeline(self, cmds):
        return [await self.execute(*c) for c in cmds]
