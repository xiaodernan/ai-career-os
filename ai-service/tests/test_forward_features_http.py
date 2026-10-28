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
    # The reader's language is a request field; absent means the product default.
    assert any("No replies yet" in s for s in body["signals"])


def test_insight_digest_answers_in_the_language_the_request_names():
    """The route binds `locale`, so the reader's screen decides the sentences.

    The engine's default is English; a zh reader's page asks for zh and the same
    digest comes back said in Chinese. Before the field existed, posting it was
    silently dropped and the answer stayed English for everyone.
    """
    r = _post("insight-digest", {"applications": [{"id": "a1", "status": "applied"}],
                                 "locale": "zh"})
    assert r.status_code == 200
    assert any("还没有回复记录" in s for s in r.json()["signals"])


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


def test_plan_ingest_carries_the_boards_company_through_the_route():
    """`company` is the board's name (19.8), and the route has to forward it."""
    r = _post("plan-ingest", {
        "feed": '[{"text": "Backend Engineer", "categories": {"location": "Berlin"}}]',
        "source": "lever", "company": "Acme"})
    assert r.status_code == 200
    row = r.json()["create"][0]
    assert row["title"] == "Backend Engineer"
    assert row["company"] == "Acme"
    assert row["location"] == "Berlin"


def test_parse_board_roundtrip():
    r = _post("parse-feed", {"payload": '{"jobs": [{"title": "A"}, {"title": "B"}]}'})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2 and [p["title"] for p in body["postings"]] == ["A", "B"]
    assert body["format"] == "board"


def test_parse_feed_roundtrip_takes_an_rss_document_too():
    """The ingestion page promises both shapes, so the route has to take both.

    The shape is detected from the text: a payload that begins with ``<``
    is XML, whatever the caller labelled it. Before this the bridge only
    reached the JSON parser, so an RSS feed -- the first thing the page's
    own copy offers -- failed with a parse error.
    """
    xml = (
        '<?xml version="1.0"?><rss version="2.0"><channel><title>Jobs</title>'
        "<item><title>Platform Engineer</title>"
        "<link>https://acme.test/jobs/1</link>"
        "<description>Kubernetes and Go.</description>"
        "<pubDate>Mon, 01 Oct 2026 00:00:00 GMT</pubDate></item>"
        "</channel></rss>"
    )
    r = _post("parse-feed", {"payload": xml, "source": "rss"})
    assert r.status_code == 200
    body = r.json()
    assert body["format"] == "rss"
    assert body["count"] == 1
    assert body["postings"][0]["title"] == "Platform Engineer"


def test_a_broken_feed_is_refused_rather_than_parsed_into_nothing():
    r = _post("parse-feed", {"payload": "<rss><channel><item>"})
    assert r.status_code == 400, (
        "a feed the parser cannot read has to be refused: a sweep that saw an "
        "empty success would ingest nothing and say it had worked")


# ---------------- 13.1 render ----------------

def test_the_markdown_half_of_the_bundle_is_served_by_the_route():
    # The Markdown view was a library function nothing called: the route
    # served the HTML and the PDF, so the operator's quick look existed only
    # for someone already inside Python. It is a format of the route now.
    r = _post("render-bundle", {
        "bundle": {
            "data": {"profile": {"display_name": "Reader"}},
            "manifest": {"schema_version": "1.2.0", "counts": {"profile": 1}},
        },
        "format": "markdown",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["format"] == "markdown"
    assert body["markdown"].startswith("# ")
    assert "## Profile" in body["markdown"]
    assert "Reader" in body["markdown"]


def test_the_markdown_is_in_the_readers_language():
    r = _post("render-bundle", {
        "bundle": {"data": {}, "manifest": {"schema_version": "1.2.0"}},
        "format": "markdown",
        "locale": "zh",
    })
    assert r.status_code == 200
    # The words come from the same table the print-ready HTML reads, so the
    # quick look is the reader's document too -- not a Chinese document an
    # English reader cannot read, and not an English one a Chinese one can't.
    assert any("一" <= ch <= "鿿" for ch in r.json()["markdown"])


# ---------------- 16.1 monitoring ----------------

def test_health_report_roundtrip():
    r = _post("health-report", {"runs": [{"status": "completed", "latency_ms": 10}]})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"summary", "regressions", "alerts", "verdict"}
    assert body["verdict"] == "healthy"
