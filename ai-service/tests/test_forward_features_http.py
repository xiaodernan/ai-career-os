"""HTTP-level contract tests for the forward ``/internal/features`` routes.

The engine unit tests prove the maths and ``test_forward_features_contract.py`` pins
the route *shape* (path, method, auth dependency, required fields, engine key set).
Neither drives a real request through the stack, so a wiring bug -- a route that never
calls its engine, a Pydantic field that does not round-trip, a response that fails to
serialise -- would slip past both. This file closes that gap for the eight engines added
for Epics 14 / 15 / 16.1: it authenticates with the internal token, sends a real body,
and asserts the JSON the caller would actually receive.

No database: ``X-Run-Id`` short-circuits ``_run`` (so no run row is created) and
``finish_run`` is patched to a no-op. ``TestClient`` is deliberately *not* used as a
context manager, so the app's lifespan (which opens a Postgres pool) never runs.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db import observability
from app.main import app

TOKEN = get_settings().internal_api_token
USER = "00000000-0000-0000-0000-0000000000aa"
RUN = "00000000-0000-0000-0000-0000000000bb"
AUTH = {"X-Internal-Token": TOKEN, "X-User-Id": USER, "X-Run-Id": RUN}

client = TestClient(app)


@pytest.fixture(autouse=True)
def _no_db(monkeypatch):
    async def _noop(*args, **kwargs):
        return None
    monkeypatch.setattr(observability, "finish_run", _noop)
    monkeypatch.setattr(observability, "create_run", _noop)
    yield


def _post(path: str, body: dict, headers: dict | None = None):
    return client.post(f"/internal/features/{path}", json=body,
                       headers=AUTH if headers is None else headers)


# ---------------- auth ----------------

def test_missing_internal_token_is_401():
    r = _post("pipeline-funnel", {"applications": [{"id": "a", "status": "applied"}]},
              headers={"X-User-Id": USER})
    assert r.status_code == 401


def test_missing_user_header_is_400():
    r = _post("pipeline-funnel", {"applications": [{"id": "a", "status": "applied"}]},
              headers={"X-Internal-Token": TOKEN})
    assert r.status_code == 400


def test_missing_required_field_is_422():
    # A route whose request model requires a field answers 422 without it.
    # The funnel's list is not one of those fields any more: a workspace with
    # no applications is a real state, and the engine answers with an empty
    # funnel rather than with a refusal. The route that still requires a
    # field is the one below.
    r = _post("pipeline-funnel", {})
    assert r.status_code == 200
    assert r.json()["totalApplications"] == 0

    r = _post("gap-analysis", {})
    assert r.status_code == 422


# ---------------- 15.x analytics ----------------

def test_pipeline_funnel_roundtrip():
    r = _post("pipeline-funnel", {"applications": [
        {"id": "a1", "status": "applied"},
        {"id": "a2", "status": "offer"},
    ]})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"pipeline", "appliedCount", "savedCount", "rejectedCount",
                         "totalApplications"}
    assert body["appliedCount"] == 2


def test_response_rate_roundtrip():
    r = _post("response-rate", {"applications": [
        {"id": "a1", "status": "applied"},
        {"id": "a2", "status": "interview", "applied_at": "2026-01-01",
         "interview_at": "2026-01-05"},
    ]})
    assert r.status_code == 200
    assert set(r.json()) == {"appliedCount", "respondedCount", "responseRate",
                             "offerCount", "offerRate", "interviewCount",
                             "interviewRate", "timeInStage"}


def test_insight_digest_roundtrip():
    r = _post("insight-digest", {"applications": [{"id": "a1", "status": "applied"}],
                                 "stale_days": 7})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"generatedAt", "windowDays", "totalApplications",
                         "activePipeline", "stageCounts", "responseRate", "offerRate",
                         "stalledCount", "stalled", "signals"}
    assert body["windowDays"] == 7


# ---------------- 14.x ingestion ----------------

def test_dedupe_jobs_roundtrip():
    r = _post("dedupe-jobs", {"postings": [
        {"id": "a", "company": "C", "title": "T", "location": "L"},
        {"id": "b", "company": "C", "title": "T", "location": "L"},
    ]})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"unique", "duplicates", "inputCount", "uniqueCount",
                         "duplicateCount"}
    assert body["uniqueCount"] == 1 and body["duplicateCount"] == 1


def test_freshness_sweep_roundtrip():
    r = _post("freshness-sweep", {"postings": [{"id": "a", "posted_at": "2020-01-01"}]})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"fresh", "stale", "expired", "undated", "counts"}
    assert body["counts"]["expired"] == 1


def test_plan_ingest_roundtrip():
    r = _post("plan-ingest", {"postings": [
        {"title": "Backend", "company": "Acme", "location": "Shanghai"}]})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"source", "create", "update", "close", "duplicates", "counts"}
    assert body["counts"]["create"] == 1


def test_parse_board_roundtrip():
    r = _post("parse-board", {"payload": '{"jobs": [{"title": "A"}, {"title": "B"}]}'})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2 and [p["title"] for p in body["postings"]] == ["A", "B"]


# ---------------- 16.1 monitoring ----------------

def test_health_report_roundtrip():
    r = _post("health-report", {"runs": [{"status": "completed", "latency_ms": 10}]})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"summary", "regressions", "alerts", "verdict"}
    assert body["verdict"] == "healthy"
