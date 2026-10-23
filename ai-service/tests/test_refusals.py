"""The refusals the ai-service answers with, as the caller receives them.

A refused request is not a stack trace and not a bare ``{"detail": "..."}``
string: it is a stable **code** plus the one sentence that code means, so the
backend can map the code to its own vocabulary and the reader still gets a
sentence about their own file. The engines raise ``RefusalError`` (a
``ValueError`` subclass, so every existing ``pytest.raises(ValueError)`` still
holds) and the API layer turns it into
``{"detail": {"code": ..., "message": ...}}``.

This file drives the real routes with ``TestClient`` (no lifespan, so no
database) and asserts the wire shape end to end: which code, which status, and
-- where the refusal names the offender -- which extras ride along. The status
is the contract the client's error path reads, so a refusal that used to be a
422 stays a 422.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.errors import (
    INGEST_BOARD_INVALID,
    INGEST_BOARD_NOT_ARRAY,
    INGEST_BOARD_NO_ARRAY,
    INGEST_FEED_EMPTY,
    INGEST_FEED_INVALID,
    RefusalError,
    refusal_exception_handler,
)
from app.core.config import get_settings
from app.db import observability
from app.features import ingestion as ingestion_mod
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


def _refusal(response) -> dict:
    assert response.status_code != 500, response.text
    return response.json()["detail"]


# ---------------- the engines raise refusals, not bare ValueErrors ----------------

def test_a_refusal_is_still_a_valueerror():
    # Every test and caller that caught ValueError keeps working: the typed
    # refusal is a subclass, so the narrow contract did not break the wide one.
    with pytest.raises(ValueError) as excinfo:
        raise RefusalError(INGEST_FEED_EMPTY)
    assert excinfo.value.refusal.code == "INGEST_FEED_EMPTY"


def test_the_empty_feed_refusal_names_itself():
    with pytest.raises(RefusalError) as excinfo:
        ingestion_mod.parse_feed("")
    assert excinfo.value.refusal.code == "INGEST_FEED_EMPTY"


# ---------------- ingestion refusals, over HTTP ----------------

def test_an_unreadable_feed_is_a_400_with_a_code():
    r = client.post("/internal/features/parse-feed",
                    json={"payload": "<rss"}, headers=AUTH)
    assert r.status_code == 400
    assert _refusal(r) == {"code": "INGEST_FEED_INVALID", "message": "invalid feed xml"}


def test_a_board_payload_with_no_posting_array_names_the_keys_it_looked_for():
    r = client.post("/internal/features/parse-feed",
                    json={"payload": '{"nothing": 1}'}, headers=AUTH)
    assert r.status_code == 400
    assert _refusal(r)["code"] == "INGEST_BOARD_NO_ARRAY"


def test_a_board_payload_that_is_not_an_array_is_refused():
    # A JSON scalar: no key can hold the array, and the payload itself is
    # not one -- the engine's second refusal, not its first.
    r = client.post("/internal/features/parse-feed",
                    json={"payload": '"nope"'}, headers=AUTH)
    assert r.status_code == 400
    assert _refusal(r)["code"] == "INGEST_BOARD_NOT_ARRAY"


def test_a_feed_that_is_neither_shape_is_refused_by_the_engine_not_the_router():
    r = client.post("/internal/features/parse-feed",
                    json={"payload": "not xml at all"}, headers=AUTH)
    assert r.status_code == 400
    assert _refusal(r)["code"] == "INGEST_BOARD_INVALID"


# ---------------- the sweep plan's own refusals ----------------

@pytest.mark.parametrize("body", [
    {"postings": [{"title": "x"}], "feed": "<rss/>"},   # both
    {},                                                  # neither
])
def test_the_plan_route_refuses_a_request_that_names_both_or_neither(body):
    r = client.post("/internal/features/plan-ingest", json=body, headers=AUTH)
    assert r.status_code == 400
    assert _refusal(r) == {
        "code": "EXPORT_SEND_ONE",
        "message": "send exactly one of postings / feed",
    }


def test_a_plan_over_an_unreadable_feed_reports_the_engine_s_code():
    r = client.post("/internal/features/plan-ingest",
                    json={"feed": "<rss"}, headers=AUTH)
    assert r.status_code == 400
    assert _refusal(r)["code"] == "INGEST_FEED_INVALID"


# ---------------- import / export refusals ----------------

def test_an_invalid_bundle_refusal_carries_what_is_wrong_with_the_file():
    r = client.post("/internal/features/import-plan", json={"bundle": {}},
                    headers=AUTH)
    assert r.status_code == 400
    detail = _refusal(r)
    assert detail["code"] == "IMPORT_BUNDLE_INVALID"
    # The reader's file is the input, so the answer names what is wrong with it.
    assert detail["errors"]


def test_an_unknown_section_refusal_names_the_offender():
    r = client.post("/internal/features/redact-bundle",
                    json={"bundle": {}, "drop": ["nope"]}, headers=AUTH)
    assert r.status_code == 400
    detail = _refusal(r)
    assert detail["code"] == "EXPORT_SECTIONS_UNKNOWN"
    assert detail["invalid"] == ["nope"]


# ---------------- the older routes keep their sentence and their status ----------------

def test_a_blank_memory_content_is_refused_before_any_row_is_touched():
    # The refusal fires before the database call: no pool is open in this
    # test, so a write that got through would be a 500, not this 400.
    r = client.patch("/internal/memories/00000000-0000-0000-0000-0000000000aa",
                     json={"content": "   "}, headers=AUTH)
    assert r.status_code == 400
    assert _refusal(r) == {
        "code": "MEMORY_CONTENT_BLANK",
        "message": "memory content cannot be blank \u2014 delete it instead",
    }


def test_a_missing_ingest_text_keeps_its_422():
    # The status is what the client's error path reads, so the refusal keeps
    # the status the route always answered with -- not the 400 default.
    r = client.post("/internal/ingest/text", json={"text": "  "}, headers=AUTH)
    assert r.status_code == 422
    assert _refusal(r) == {"code": "TEXT_REQUIRED", "message": "text required"}


# ---------------- the handler agrees with the API layer ----------------

def test_the_handler_answers_the_same_shape_as_to_http_exception():
    # A refusal that escapes a route uncaught reaches the exception handler;
    # it must not lose the extras the API-layer path carries.
    from app.core.errors import IMPORT_BUNDLE_INVALID, Refusal

    exc = RefusalError(IMPORT_BUNDLE_INVALID.with_detail({"errors": ["no data"]}))
    response = asyncio.run(refusal_exception_handler(None, exc))
    import json
    body = json.loads(response.body)
    assert response.status_code == 400
    assert body["detail"] == {
        "code": "IMPORT_BUNDLE_INVALID",
        "message": "invalid bundle",
        "errors": ["no data"],
    }
