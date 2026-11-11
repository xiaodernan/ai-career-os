"""The cache status collector is total, honest, and does no I/O.

``read_health()`` is the one seam between the control-plane endpoint and the
cache's own ``describe()``. Three properties are pinned here:

* **No I/O / no pool.** Every number is a process-local counter; the collector
  never opens a Redis connection or touches the hot path. A dead Redis shows up
  as ``breaker_trips`` in the counters, not as a connection attempt here.
* **Two truths, both reported.** Configured mode comes from ``Settings`` (intent);
  ``describe()`` reports what was actually built. A ``redis`` config degraded to
  ``memory`` must surface as ``degraded_to``, not be silently reconciled away.
* **Total fail-open.** A raising ``describe()`` becomes an *unknown* report, never
  an exception into the request.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.ops import cache_status

_DESCRIBE = {
    "backend": "memory",
    "enabled": True,
    "stats": {"hits": 30, "misses": 10, "writes": 40, "errors": 0,
              "evictions": 0, "l2_hits": 0},
    "single_flight": {"leaders": 2, "joined": 5, "inflight": 0},
    "embedding_model": "mock|mock|8",
}


def _settings(mode: str):
    return SimpleNamespace(cache_backend=mode)


@pytest.fixture
def _cfg(monkeypatch):
    def use(mode: str):
        monkeypatch.setattr(cache_status, "get_settings", lambda: _settings(mode))
    return use


# ------------------------------------------------------- the happy path
def test_a_clean_read_returns_a_full_health_report(monkeypatch, _cfg):
    _cfg("memory")
    monkeypatch.setattr(cache_status.caching, "describe", lambda: dict(_DESCRIBE))
    report = cache_status.read_health()
    assert report["verdict"] == "healthy"
    assert report["backend"] == "memory"
    assert report["cache"]["hit_rate"] == 0.75
    assert "degraded_to" not in report


def test_the_mode_is_the_configured_intent(monkeypatch, _cfg):
    _cfg("redis")
    monkeypatch.setattr(cache_status.caching, "describe", lambda: dict(_DESCRIBE))
    report = cache_status.read_health()
    assert report["backend"] == "redis", "report must carry the operator's configured mode"


# ------------------------------------------------------- two truths
def test_a_configured_redis_that_degraded_to_memory_is_reported(monkeypatch, _cfg):
    """A bad REDIS_URL makes build_cache() fall back to memory. Hiding that would
    let a fleet believe it shares entries when each replica computes alone -- the
    exact 'second question is not free across replicas' lie."""
    _cfg("redis")
    monkeypatch.setattr(cache_status.caching, "describe", lambda: dict(_DESCRIBE))
    report = cache_status.read_health()
    assert report["degraded_to"] == "memory"


def test_when_intent_and_reality_agree_there_is_no_degraded_to(monkeypatch, _cfg):
    _cfg("memory")
    monkeypatch.setattr(cache_status.caching, "describe", lambda: dict(_DESCRIBE))
    assert "degraded_to" not in cache_status.read_health()


# ------------------------------------------------------- the off default
def test_the_off_default_reports_off_without_touching_anything(monkeypatch, _cfg):
    _cfg("off")
    off = {"backend": "off", "enabled": False,
           "stats": {"hits": 0, "misses": 0, "writes": 0, "errors": 0}}
    called = {"n": 0}

    def describe():
        called["n"] += 1
        return off

    monkeypatch.setattr(cache_status.caching, "describe", describe)
    report = cache_status.read_health()
    assert report["verdict"] == "off"
    assert called["n"] == 1, "the collector must read describe() exactly once"


# ------------------------------------------------------- total fail-open
def test_a_raising_describe_becomes_unknown_not_an_exception(monkeypatch, _cfg):
    _cfg("redis")

    def boom():
        raise RuntimeError("describe is broken")

    monkeypatch.setattr(cache_status.caching, "describe", boom)
    report = cache_status.read_health()
    assert report["verdict"] == "unknown"
    assert report["observation_error"] == "describe-failed:RuntimeError"
    assert {"verdict", "alerts", "backend", "cache"} <= set(report)


def test_a_malformed_describe_is_unknown_not_a_crash(monkeypatch, _cfg):
    _cfg("memory")
    monkeypatch.setattr(cache_status.caching, "describe", lambda: {"enabled": True})
    report = cache_status.read_health()
    assert report["verdict"] == "unknown"


def test_a_settings_failure_still_returns_a_report(monkeypatch):
    def bad_settings():
        raise RuntimeError("settings unavailable")

    monkeypatch.setattr(cache_status, "get_settings", bad_settings)
    monkeypatch.setattr(cache_status.caching, "describe", lambda: dict(_DESCRIBE))
    report = cache_status.read_health()
    assert report["verdict"] == "healthy"
    assert report["backend"] == "unknown", "an unreadable mode must not be invented"


# ------------------------------------------------------- the breaker survives the seam
def test_a_layered_redis_outage_is_not_silenced_by_the_seam(monkeypatch, _cfg):
    _cfg("redis")
    snap = {
        "backend": "layered", "enabled": True,
        "stats": {"hits": 30, "misses": 10, "errors": 0, "writes": 40},
        "local": {"backend": "memory", "enabled": True,
                  "stats": {"hits": 30, "misses": 10, "errors": 0}},
        "shared": {"backend": "redis", "enabled": True,
                   "stats": {"hits": 0, "misses": 0, "errors": 2},
                   "breaker": {"trips": 1, "open": True, "cooldown_s": 5.0}},
    }
    monkeypatch.setattr(cache_status.caching, "describe", lambda: snap)
    report = cache_status.read_health()
    assert report["verdict"] == "unknown"
    assert report["cache"]["errors"] == 2
    assert report["cache"]["breaker_trips"] == 1
