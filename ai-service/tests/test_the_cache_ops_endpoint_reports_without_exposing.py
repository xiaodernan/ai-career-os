"""GET /internal/ops/cache: authorised, well-shaped, and never a 500.

The endpoint is the control-plane face of Epic 143. It must be reachable only with
the shared internal token (same contract as every ``/internal/*`` route), return the
health report's full shape so a monitor can scrape it, and degrade to an *unknown*
report if the collector itself ever throws -- a control-plane endpoint must never
turn an observer's bad day into a 500 that looks like the service died.

``TestClient`` is deliberately not used as a context manager, so the app lifespan
(which opens Postgres) never runs; the collector is patched, so no cache I/O.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.ops import cache_status

TOKEN = get_settings().internal_api_token
USER = "00000000-0000-0000-0000-0000000000aa"
AUTH = {"X-Internal-Token": TOKEN, "X-User-Id": USER}

client = TestClient(app)

REPORT_KEYS = {"verdict", "alerts", "backend", "enabled", "cache",
               "single_flight", "thresholds"}


def _report(verdict="healthy", **over):
    base = {
        "verdict": verdict,
        "alerts": [],
        "backend": "memory",
        "enabled": True,
        "cache": {"lookups": 40, "hits": 30, "misses": 10, "writes": 40,
                  "errors": 0, "evictions": 0, "l2_hits": 0, "hit_rate": 0.75,
                  "breaker_trips": 0},
        "single_flight": {"leaders": 2, "joined": 5, "inflight": 0},
        "thresholds": {"min_lookups": 20, "hit_rate_warn": 0.5},
    }
    base.update(over)
    return base


@pytest.fixture(autouse=True)
def _patch_collector(monkeypatch):
    def _ok():
        return _report()

    monkeypatch.setattr(cache_status, "read_health", _ok)
    yield


# --------------------------------------------------------------- auth
def test_missing_internal_token_is_401():
    r = client.get("/internal/ops/cache", headers={"X-User-Id": USER})
    assert r.status_code == 401


def test_missing_user_header_is_400():
    r = client.get("/internal/ops/cache", headers={"X-Internal-Token": TOKEN})
    assert r.status_code == 400


def test_a_wrong_token_is_401():
    r = client.get("/internal/ops/cache",
                   headers={"X-Internal-Token": "not-the-token", "X-User-Id": USER})
    assert r.status_code == 401


# --------------------------------------------------------------- shape / status
def test_an_authorised_read_returns_the_full_report_with_200():
    r = client.get("/internal/ops/cache", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert REPORT_KEYS <= set(body)
    assert body["verdict"] == "healthy"


@pytest.mark.parametrize("verdict", ["off", "cold", "ineffective", "unknown"])
def test_a_non_healthy_verdict_is_still_a_200_not_a_5xx(monkeypatch, verdict):
    """Health travels in the verdict, not the HTTP status -- monitors scrape 200
    even when the honest answer is 'caching has never been switched on'."""
    monkeypatch.setattr(cache_status, "read_health", lambda: _report(verdict))
    r = client.get("/internal/ops/cache", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["verdict"] == verdict


def test_an_off_cache_report_carries_its_explanatory_alert(monkeypatch):
    monkeypatch.setattr(
        cache_status, "read_health",
        lambda: _report("off", enabled=False,
                        alerts=["Caching has never been switched on."]))
    r = client.get("/internal/ops/cache", headers=AUTH)
    assert r.json()["alerts"]


# --------------------------------------------------------------- last-resort fail-open
def test_a_collector_that_raises_becomes_an_unknown_report_not_a_500(monkeypatch):
    def _boom():
        raise RuntimeError("the observer had a bad day")

    monkeypatch.setattr(cache_status, "read_health", _boom)
    r = client.get("/internal/ops/cache", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "unknown"
    assert body["observation_error"] == "endpoint-fallback"
    assert REPORT_KEYS <= set(body)


def test_the_route_is_read_only():
    """Only GET is registered; there is no control action on this surface."""
    r = client.post("/internal/ops/cache", headers=AUTH)
    assert r.status_code == 405
