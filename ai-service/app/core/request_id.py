"""One id for a request, and for every line it logs.

The backend mints an id per request (32.1) and sends it here as ``X-Request-Id``.
This middleware echoes it on the answer and puts it in a context variable the JSON
log formatter reads, so a turn that fails upstream is one grep across both services'
logs instead of two clocks compared by eye.

The value is echoed only when it is 8-64 characters of the same alphabet the
backend accepts, because it is written to a log line: an unvalidated header could
carry a line break. Anything else -- a caller outside a request, a malformed value
-- is replaced by a fresh UUID rather than refused; the id is diagnostics, not a
credential, and it must never be the reason a request fails.

Epic 104 extends the same hop with W3C ``traceparent`` propagation: a valid trace
context is preserved and echoed, otherwise a fresh one is minted so the engine
participates in the same distributed trace as the gateway and backend.
"""

import re
import secrets
import uuid
from contextvars import ContextVar

from starlette.types import ASGIApp, Message, Receive, Scope, Send

HEADER = "x-request-id"
TRACEPARENT_HEADER = "traceparent"
_ACCEPTED = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}")
_TRACEPARENT = re.compile(r"^[0-9a-f]{2}-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$")

request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
traceparent: ContextVar[str | None] = ContextVar("traceparent", default=None)


def _mint_traceparent() -> str:
    return "00-" + secrets.token_hex(16) + "-" + secrets.token_hex(8) + "-01"


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        inbound = None
        inbound_tp = None
        for key, value in scope.get("headers", []):
            lk = key.lower()
            if lk == HEADER.encode():
                inbound = value.decode("latin-1")
            elif lk == TRACEPARENT_HEADER.encode():
                inbound_tp = value.decode("latin-1")
        rid = inbound if inbound is not None and _ACCEPTED.fullmatch(inbound) else str(uuid.uuid4())
        tp = (
            inbound_tp.lower()
            if inbound_tp is not None and _TRACEPARENT.fullmatch(inbound_tp.lower())
            else _mint_traceparent()
        )
        state = scope.setdefault("state", {})
        state["request_id"] = rid
        state["traceparent"] = tp

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((HEADER.encode(), rid.encode("latin-1")))
                headers.append((TRACEPARENT_HEADER.encode(), tp.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        token = request_id.set(rid)
        tp_token = traceparent.set(tp)
        try:
            await self.app(scope, receive, send_with_id)
        finally:
            # The event loop reuses the task; the next request must not inherit this context.
            traceparent.reset(tp_token)
            request_id.reset(token)
