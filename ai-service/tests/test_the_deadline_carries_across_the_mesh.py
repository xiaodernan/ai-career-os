"""Epic 128 -- the caller's own deadline travels, and the engine honours it.

The edge stamps every /api/** request with ``X-Request-Deadline-Ms`` (epoch
milliseconds). The backend's AI bridge refuses before dispatch when the budget
is already gone; this middleware carries the same number into the engine, and
the engine has its own backstop at the most expensive route: ``/answer`` refuses
before retrieving a single chunk when the caller is already gone.

A deadline is work conservation, never a permission problem, so a malformed
value is ignored rather than refused -- the engine must serve the request it
was sent, budget or no budget.
"""

import time

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.errors import SERVICE_DEADLINE_EXCEEDED
from app.core.request_id import deadline_ms
from app.main import app

TOKEN = get_settings().internal_api_token
USER = "00000000-0000-0000-0000-0000000000aa"
RUN = "00000000-0000-0000-0000-0000000000bb"
AUTH = {"X-Internal-Token": TOKEN, "X-User-Id": USER, "X-Run-Id": RUN}
DEADLINE = "X-Request-Deadline-Ms"

client = TestClient(app)


@pytest.fixture(autouse=True)
def _no_db(monkeypatch):
    from app.db import observability

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(observability, "finish_run", _noop)
    monkeypatch.setattr(observability, "create_run", _noop)
    yield


def _answer(deadline: str | None):
    headers = dict(AUTH)
    if deadline is not None:
        headers[DEADLINE] = deadline
    return client.post("/internal/rag/answer", json={"query": "hello"}, headers=headers)


def test_a_past_deadline_is_refused_before_the_engine_works(monkeypatch):
    called = []

    async def _explode(*args, **kwargs):
        called.append(1)
        raise AssertionError("retrieve() must not be called when the deadline already passed")

    monkeypatch.setattr("app.api.rag.retrieve", _explode)

    r = _answer(str(int(time.time() * 1000) - 1_000))

    assert r.status_code == 503
    assert r.json()["detail"]["code"] == SERVICE_DEADLINE_EXCEEDED.code
    assert called == []


def test_the_deadline_is_echoed_not_minted(monkeypatch):
    deadline = str(int(time.time() * 1000) + 60_000)

    # Echo check happens on any route: use the cheapest real one.
    r = client.get("/internal/rag/cache", headers={**AUTH, DEADLINE: deadline})

    assert r.headers.get(DEADLINE.lower()) == deadline


def test_garbage_deadline_is_ignored_never_refused():
    r = client.get("/internal/rag/cache", headers={**AUTH, DEADLINE: "tomorrow"})

    # The request is served (mocked stats), not refused, and nothing is echoed.
    assert r.status_code == 200
    assert r.headers.get(DEADLINE.lower()) is None


def test_no_deadline_is_no_budget(monkeypatch):
    deadline_ms.set(None)
    r = client.get("/internal/rag/cache", headers=AUTH)
    assert r.status_code == 200
    assert r.headers.get(DEADLINE.lower()) is None


def test_a_valid_deadline_is_echoed_on_order():
    future = str(int(time.time() * 1000) + 60_000)
    r = client.get("/internal/rag/cache", headers={**AUTH, DEADLINE: future})
    assert r.headers.get(DEADLINE.lower()) == future
