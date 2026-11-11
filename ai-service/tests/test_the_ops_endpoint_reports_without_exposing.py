"""GET /internal/ops/workqueue: authorised, well-shaped, and never a 500.

The endpoint is the control-plane face of Epic 140. It must be reachable only with
the shared internal token (same contract as every ``/internal/*`` route), return the
health report's full shape so a monitor can scrape it, and degrade to an *unknown*
report if the collector itself ever throws -- a control-plane endpoint must never
turn an observer's bad day into a 500 that looks like the service died.

``TestClient`` is deliberately not used as a context manager, so the app lifespan
(which opens Postgres) never runs; the collector is patched, so neither is Redis.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.ops import queue_status

TOKEN = get_settings().internal_api_token
USER = "00000000-0000-0000-0000-0000000000aa"
AUTH = {"X-Internal-Token": TOKEN, "X-User-Id": USER}

client = TestClient(app)

REPORT_KEYS = {"verdict", "alerts", "freshness", "queue", "guard", "backend"}


def _report(verdict="healthy", **over):
    base = {
        "verdict": verdict,
        "alerts": [],
        "freshness": {"fresh": True, "age_s": 5.0, "last_tick": 1000.0,
                      "stale_after_s": 300},
        "queue": {"stream_len": 0, "pending": 0, "dlq_len": 0,
                  "dlq_enabled": True, "ok": True},
        "guard": {"enabled": True, "cooldown_s": 900, "cooled_count": 0},
        "backend": "redis",
    }
    base.update(over)
    return base


@pytest.fixture(autouse=True)
def _patch_collector(monkeypatch):
    async def _ok():
        return _report()
    monkeypatch.setattr(queue_status, "read_status", _ok)
    yield


# --------------------------------------------------------------- auth
def test_missing_internal_token_is_401():
    r = client.get("/internal/ops/workqueue", headers={"X-User-Id": USER})
    assert r.status_code == 401


def test_missing_user_header_is_400():
    r = client.get("/internal/ops/workqueue", headers={"X-Internal-Token": TOKEN})
    assert r.status_code == 400


def test_a_wrong_token_is_401():
    r = client.get("/internal/ops/workqueue",
                   headers={"X-Internal-Token": "not-the-token", "X-User-Id": USER})
    assert r.status_code == 401


# --------------------------------------------------------------- shape / status
def test_an_authorised_read_returns_the_full_report_with_200():
    r = client.get("/internal/ops/workqueue", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert REPORT_KEYS <= set(body)
    assert body["verdict"] == "healthy"


def test_a_degraded_verdict_is_still_a_200_not_a_5xx(monkeypatch):
    """Health travels in the verdict, not the HTTP status -- monitors scrape 200."""
    async def _degraded():
        return _report("degraded", alerts=["2 dead-lettered jobs in the DLQ."])
    monkeypatch.setattr(queue_status, "read_status", _degraded)
    r = client.get("/internal/ops/workqueue", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["verdict"] == "degraded"
    assert r.json()["alerts"]


# --------------------------------------------------------------- last-resort fail-open
def test_a_collector_that_raises_becomes_an_unknown_report_not_a_500(monkeypatch):
    async def _boom():
        raise RuntimeError("the observer had a bad day")
    monkeypatch.setattr(queue_status, "read_status", _boom)
    r = client.get("/internal/ops/workqueue", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "unknown"
    assert body["observation_error"] == "endpoint-fallback"
    assert REPORT_KEYS <= set(body)


def test_the_route_is_read_only():
    """Only GET is registered; there is no control action on this surface."""
    r = client.post("/internal/ops/workqueue", headers=AUTH)
    assert r.status_code == 405
