"""One id joins the backend's log to this service's.

32.1 gave every backend request an id, printed in its console lines. The reason to
carry it here is the moment a turn fails upstream: the backend writes "AI service
call failed" under that id, and the traceback in this service has to be greppable
by the same value, or the operator is comparing two clocks by eye.

The value is echoed only when it is the same well-formed shape the backend
accepts; anything else is replaced rather than refused, and the id never changes
the status the route would have answered anyway.
"""

import asyncio
import json
import logging
import re

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.logging import JsonFormatter
from app.core.request_id import RequestIdMiddleware, request_id
from app.main import app

TOKEN = get_settings().internal_api_token
USER = "00000000-0000-0000-0000-0000000000aa"
AUTH = {"X-Internal-Token": TOKEN, "X-User-Id": USER}

UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

client = TestClient(app)


def _answer(headers: dict | None = None):
    # An empty body is a 422 before any engine or database is touched; the
    # middleware runs either way, which is the point -- refusals carry the id.
    return client.post("/internal/features/resume/parse", json={}, headers=headers or AUTH)


def test_the_answer_echoes_the_id_the_backend_minted():
    response = _answer({**AUTH, "X-Request-Id": "edge-7c1d4f9a"})
    assert response.status_code == 422
    assert response.headers["x-request-id"] == "edge-7c1d4f9a"


def test_a_malformed_id_is_replaced_rather_than_refused():
    response = _answer({**AUTH, "X-Request-Id": "bad id"})
    assert response.status_code == 422
    assert UUID.fullmatch(response.headers["x-request-id"])
    assert response.headers["x-request-id"] != "bad id"


def _run_fake_request(headers, log_lines):
    async def fake_app(scope, receive, send):
        logging.getLogger("careeros.test.correlation").info("inside the request")
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    class Capture(logging.Handler):
        def emit(self, record):
            log_lines.append(JsonFormatter().format(record))

    logger = logging.getLogger("careeros.test.correlation")
    handler = Capture()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    middleware = RequestIdMiddleware(fake_app)
    scope = {"type": "http", "method": "GET", "path": "/", "headers": headers}
    messages = []

    async def receive():
        return {"type": "http.request"}

    async def send(message):
        messages.append(message)

    try:
        asyncio.run(middleware(scope, receive, send))
    finally:
        logger.removeHandler(handler)
    return messages


def test_the_id_is_in_scope_while_the_request_runs_and_gone_after():
    messages = _run_fake_request([(b"x-request-id", b"edge-7c1d4f9a")], [])
    start = next(m for m in messages if m["type"] == "http.response.start")
    assert (b"x-request-id", b"edge-7c1d4f9a") in start["headers"]
    # The loop's next request must not inherit this one's id.
    assert request_id.get() is None


def test_a_log_line_written_inside_a_request_carries_the_id():
    lines = []
    _run_fake_request([(b"x-request-id", b"edge-7c1d4f9a")], lines)
    assert json.loads(lines[0])["request_id"] == "edge-7c1d4f9a"


def test_a_log_line_outside_any_request_has_no_id():
    formatted = JsonFormatter().format(
        logging.LogRecord("careeros.test.correlation", logging.INFO, __file__, 1, "boot", None, None)
    )
    assert "request_id" not in json.loads(formatted)
