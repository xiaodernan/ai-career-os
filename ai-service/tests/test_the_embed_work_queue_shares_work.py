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
    def __init__(self, *, down=False):
        self.down = down
        self.enqueued = []
        self.acked = []
        self.items = []
        self.drained_with = None

    async def enqueue(self, fields):
        if self.down:
            raise resp.RespUnavailable("down")
        self.enqueued.append(fields)
        return f"{len(self.enqueued)}-0"

    async def drain(self, handler):
        self.drained_with = handler
        results = [await handler(item) for item in self.items]
        ok = [it.stream_id for it, good in zip(self.items, results) if good]
        self.acked.extend(ok)
        return workqueue.ClaimStats(delivered=len(self.items),
                                    ack_failed=sum(not r for r in results))

    async def ensure_group(self):
        if self.down:
            raise resp.RespUnavailable("down")


def _item(job_id, sid="1-0"):
    return workqueue.WorkItem(sid, {"job_id": job_id})


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
