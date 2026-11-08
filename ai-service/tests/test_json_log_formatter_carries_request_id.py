"""JSON logs must carry the request id when one is in context.

Epic 75: a turn that fails upstream must be one grep across both services'
logs. ai-service's JsonFormatter writes `request_id` into every JSON line while
a request is being served. This tests the formatter directly, not just source.
"""

from __future__ import annotations

import io
import json
import logging

from app.core.logging import JsonFormatter
from app.core.request_id import request_id


def _emit(formatter: logging.Formatter, msg: str, ctx: dict | None = None, rid: str | None = None) -> dict:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(formatter)
    logger = logging.getLogger(f"test-json-formatter-{id(formatter)}")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    token = request_id.set(rid) if rid is not None else None
    try:
        if ctx is not None:
            logger.info(msg, extra={"ctx": ctx})
        else:
            logger.info(msg)
    finally:
        if token is not None:
            request_id.reset(token)
    return json.loads(stream.getvalue())


def test_json_log_line_includes_request_id_and_core_fields() -> None:
    payload = _emit(JsonFormatter(), "hello world", rid="rid-abc12345")
    assert payload["request_id"] == "rid-abc12345"
    for key in ("ts", "level", "logger", "msg", "request_id"):
        assert key in payload, f"payload missing {key}: {payload}"
    assert payload["msg"] == "hello world"


def test_json_log_line_includes_ctx_fields() -> None:
    payload = _emit(JsonFormatter(), "with ctx", ctx={"feature": "match", "user_scoped": True}, rid="rid-xyz98765")
    assert payload["feature"] == "match"
    assert payload["user_scoped"] is True
    assert payload["request_id"] == "rid-xyz98765"


def test_json_log_line_omits_request_id_when_no_context() -> None:
    payload = _emit(JsonFormatter(), "boot line", rid=None)
    assert "request_id" not in payload
    assert payload["msg"] == "boot line"
