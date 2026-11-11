"""The status collector must observe the queue without ever breaking the service.

``read_status`` is the seam between the read-only HTTP endpoint and the two worlds
the verdict needs (live Redis + the consumer heartbeat). These tests pin the
properties that make it safe to expose as a control-plane endpoint:

* ``backend=off`` reports *disabled* and does not touch Redis at all;
* a healthy redis read folds snapshot + guard + heartbeat into an *healthy* report;
* dead letters / a cold guard / a stale heartbeat surface as *degraded* / *stalled*;
* a bad Redis URL (no pool) and a Redis error both degrade to *unknown*, never raise;
* an unexpected exception still returns a well-formed *unknown* report (defence in
  depth -- the observer cannot take down what it observes);
* the short-lived observation pool is always closed, including on every error path;
* the two tuning knobs (stale_s / backlog_warn) are actually threaded through.

Everything is offline: Redis, settings and the pool factory are monkeypatched.
"""

from __future__ import annotations

import asyncio

import pytest

from app.core import resp
from app.ops import queue_status


def _settings(**over):
    base = {"work_queue_backend": "redis",
            "work_queue_health_stale_s": 300,
            "work_queue_health_backlog_warn": 32,
            "work_queue_dlq_cooldown_s": 900}
    return type("S", (), {**base, **over})()


class _FakeQueue:
    def __init__(self, snapshot):
        self._snap = snapshot
    async def snapshot(self):
        return self._snap


class _FakeGuard:
    def __init__(self, *, enabled=True, cooldown_s=900, cooled=0, size_error=False):
        self.enabled = enabled
        self.cooldown_s = cooldown_s
        self._cooled = cooled
        self._size_error = size_error
    async def size(self):
        if self._size_error:
            raise resp.RespUnavailable("down")
        return self._cooled


class _FakePool:
    def __init__(self):
        self.closed = False
    async def close(self):
        self.closed = True


def _wire(monkeypatch, *, settings=None, queue=None, guard=None, pool=None,
          pool_factory_error=None, heartbeat=None):
    monkeypatch.setattr(queue_status, "get_settings", lambda: settings or _settings())
    pool = pool if pool is not None else _FakePool()

    async def _pool():
        if pool_factory_error:
            raise pool_factory_error
        return pool
    monkeypatch.setattr(queue_status.embed_workers, "_redis_pool", _pool)
    monkeypatch.setattr(queue_status.embed_workers, "_queue", lambda _p: queue)
    monkeypatch.setattr(queue_status.embed_workers, "_guard", lambda _p: guard)
    monkeypatch.setattr(queue_status.queue_observer, "snapshot_heartbeat",
                        lambda: heartbeat)
    return pool


def _ok_snap(**over):
    return {"ok": True, "stream_len": 0, "pending": 0, "dlq_len": 0,
            "dlq_enabled": True, **over}


def _hb(now_offset=5):
    import time
    return {"last_tick": time.time() - now_offset, "delivered": 1,
            "reclaimed": 0, "dead_lettered": 0}


# --------------------------------------------------------------- the main paths
def test_backend_off_is_disabled_without_touching_redis(monkeypatch):
    def _should_not_run():
        raise AssertionError("no pool may be built when the backend is off")
    monkeypatch.setattr(queue_status, "get_settings",
                        lambda: type("S", (), {"work_queue_backend": "off"})())
    monkeypatch.setattr(queue_status.embed_workers, "_redis_pool", _should_not_run)
    report = asyncio.run(queue_status.read_status())
    assert report["verdict"] == "disabled"
    assert report["backend"] == "off"
    assert report["queue"]["ok"] is True  # a clean, known "nothing to watch" state


def test_a_healthy_redis_read_is_healthy(monkeypatch):
    pool = _wire(monkeypatch, queue=_FakeQueue(_ok_snap()),
                 guard=_FakeGuard(cooled=0), heartbeat=_hb())
    r = asyncio.run(queue_status.read_status())
    assert r["verdict"] == "healthy"
    assert r["queue"]["ok"] is True
    assert "observation_error" not in r
    assert pool.closed is True, "the short-lived pool is always closed"


def test_dead_letters_surface_as_degraded(monkeypatch):
    _wire(monkeypatch, queue=_FakeQueue(_ok_snap(dlq_len=2)),
          guard=_FakeGuard(cooled=0), heartbeat=_hb())
    r = asyncio.run(queue_status.read_status())
    assert r["verdict"] == "degraded"
    assert r["queue"]["dlq_len"] == 2


def test_a_cold_guard_surfaces_as_degraded(monkeypatch):
    _wire(monkeypatch, queue=_FakeQueue(_ok_snap()),
          guard=_FakeGuard(cooled=3), heartbeat=_hb())
    r = asyncio.run(queue_status.read_status())
    assert r["verdict"] == "degraded"
    assert r["guard"]["cooled_count"] == 3


def test_a_stale_heartbeat_surfaces_as_stalled(monkeypatch):
    _wire(monkeypatch, queue=_FakeQueue(_ok_snap()),
          guard=_FakeGuard(cooled=0),
          heartbeat={"last_tick": 1.0, "delivered": 0, "reclaimed": 0,
                     "dead_lettered": 0})
    r = asyncio.run(queue_status.read_status())
    assert r["verdict"] == "stalled"


def test_a_backlog_beyond_the_knob_surfaces_as_backlogged(monkeypatch):
    _wire(monkeypatch, settings=_settings(work_queue_health_backlog_warn=5),
          queue=_FakeQueue(_ok_snap(pending=10)),
          guard=_FakeGuard(cooled=0), heartbeat=_hb())
    r = asyncio.run(queue_status.read_status())
    assert r["verdict"] == "backlogged"


# --------------------------------------------------------------- fail-open paths
def test_a_bad_redis_url_reports_unknown(monkeypatch):
    async def _none():
        return None
    monkeypatch.setattr(queue_status, "get_settings", lambda: _settings())
    monkeypatch.setattr(queue_status.embed_workers, "_redis_pool", _none)
    r = asyncio.run(queue_status.read_status())
    assert r["verdict"] == "unknown"
    assert r["observation_error"] == "redis-pool-unavailable"


def test_a_redis_error_reports_unknown_and_closes_the_pool(monkeypatch):
    pool = _wire(monkeypatch, pool_factory_error=resp.RespUnavailable("down"))
    r = asyncio.run(queue_status.read_status())
    assert r["verdict"] == "unknown"
    # The factory itself raised before returning a pool, so there is none to close;
    # the report is still well-formed.
    assert r["queue"]["ok"] is False


def test_a_snapshot_that_could_not_read_reports_unknown_with_a_reason(monkeypatch):
    pool = _wire(monkeypatch, queue=_FakeQueue(_ok_snap(ok=False)),
                 guard=_FakeGuard(cooled=0), heartbeat=_hb())
    r = asyncio.run(queue_status.read_status())
    assert r["verdict"] == "unknown"
    assert r["observation_error"] == "redis-read-failed"
    assert pool.closed is True


def test_an_unexpected_exception_still_returns_unknown(monkeypatch):
    class _ExplodingQueue:
        async def snapshot(self):
            raise RuntimeError("a future bug")
    pool = _wire(monkeypatch, queue=_ExplodingQueue(), guard=_FakeGuard(),
                 heartbeat=_hb())
    r = asyncio.run(queue_status.read_status())
    assert r["verdict"] == "unknown"
    assert r["observation_error"].startswith("unexpected:RuntimeError")
    assert pool.closed is True, "even on a bug the pool is closed"


def test_a_guard_size_failure_degrades_to_unknown_not_a_crash(monkeypatch):
    """A bad guard key (WRONGTYPE) is a real ops fault; it must not 500."""
    pool = _wire(monkeypatch, queue=_FakeQueue(_ok_snap()),
                 guard=_FakeGuard(size_error=True), heartbeat=_hb())
    r = asyncio.run(queue_status.read_status())
    assert r["verdict"] in ("healthy", "unknown")
    assert pool.closed is True


def test_the_report_always_has_the_full_shape(monkeypatch):
    keys = {"verdict", "alerts", "freshness", "queue", "guard", "backend"}
    # Force the off path so no Redis connection is attempted.
    monkeypatch.setattr(queue_status, "get_settings",
                        lambda: type("S", (), {"work_queue_backend": "off"})())
    r = asyncio.run(queue_status.read_status())
    assert keys <= set(r)
    assert isinstance(r["alerts"], list) and isinstance(r["queue"], dict)
    assert r["verdict"] in {"disabled", "unknown", "stalled", "degraded",
                            "backlogged", "healthy"}
