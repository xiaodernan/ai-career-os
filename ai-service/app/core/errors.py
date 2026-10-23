"""Typed refusals the ai-service can answer with.

Each refusal carries a stable code and a fixed sentence. The FastAPI
exception handler emits them as {"detail": {"code": "...", "message": "..."}}.
The Java boundary reads the code and maps it to its own vocabulary.

The feature functions raise RefusalError (a ValueError subclass) so that
existing tests catching ValueError still work. The API layer catches
RefusalError and extracts the Refusal to build the HTTP response.
"""

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request


@dataclass(frozen=True, slots=True)
class Refusal:
    """A refusal the ai-service answers with.

    Attributes:
        code: The stable code (e.g. "INGEST_FEED_EMPTY").
        message: The fixed sentence for this refusal.
        status: HTTP status (default 400).
        detail: Optional dynamic detail to include in the response.
    """
    code: str
    message: str
    status: int = 400
    detail: dict | None = None

    def to_http_exception(self) -> HTTPException:
        detail = {"code": self.code, "message": self.message}
        if self.detail:
            detail.update(self.detail)
        return HTTPException(
            status_code=self.status,
            detail=detail,
        )

    def with_detail(self, detail: dict) -> "Refusal":
        """Return a copy with the given detail merged in."""
        return Refusal(self.code, self.message, self.status, detail)


class RefusalError(ValueError):
    """A ValueError that carries a Refusal.

    Feature functions raise this so that:
    - Tests catching ValueError still work (it's a subclass)
    - The API layer can extract the Refusal and emit the structured detail
    """
    def __init__(self, refusal: Refusal):
        super().__init__(refusal.message)
        self.refusal = refusal

    def __str__(self) -> str:
        if self.refusal.detail:
            # Include detail in string representation for backwards compat with tests
            return self.refusal.message + " " + str(self.refusal.detail)
        return self.refusal.message


# ---------------- ingestion refusals ----------------
INGEST_FEED_EMPTY = Refusal("INGEST_FEED_EMPTY", "feed is empty")
INGEST_FEED_TOO_LARGE = Refusal("INGEST_FEED_TOO_LARGE", "feed exceeds the size cap")
INGEST_FEED_INVALID = Refusal("INGEST_FEED_INVALID", "invalid feed xml")
INGEST_BOARD_EMPTY = Refusal("INGEST_BOARD_EMPTY", "board payload is empty")
INGEST_BOARD_TOO_LARGE = Refusal("INGEST_BOARD_TOO_LARGE", "board payload exceeds the size cap")
INGEST_BOARD_INVALID = Refusal("INGEST_BOARD_INVALID", "invalid board json")
INGEST_BOARD_NO_ARRAY = Refusal("INGEST_BOARD_NO_ARRAY", "no posting array found")
INGEST_BOARD_NOT_ARRAY = Refusal("INGEST_BOARD_NOT_ARRAY", "expected a JSON array of postings")
INGEST_FORMAT_UNKNOWN = Refusal("INGEST_FORMAT_UNKNOWN", "feed must be raw XML text or a list of posting dicts")

# ---------------- import / export refusals ----------------
IMPORT_BUNDLE_INVALID = Refusal("IMPORT_BUNDLE_INVALID", "invalid bundle")
EXPORT_SECTIONS_UNKNOWN = Refusal("EXPORT_SECTIONS_UNKNOWN", "Unknown sections to drop")
EXPORT_SEND_ONE = Refusal("EXPORT_SEND_ONE", "send exactly one of postings / feed")
MEMORY_CONTENT_BLANK = Refusal("MEMORY_CONTENT_BLANK", "memory content cannot be blank — delete it instead")
TEXT_REQUIRED = Refusal("TEXT_REQUIRED", "text required", status=422)

# Convenience: return a RefusalError to raise
def raise_refusal(refusal: Refusal) -> RefusalError:
    """Return a RefusalError with the given refusal, ready to raise."""
    return RefusalError(refusal)


# ---------------- FastAPI handler ----------------
async def refusal_exception_handler(request: Request, exc: RefusalError) -> JSONResponse:
    """Handle RefusalError raised anywhere in the ai-service.

    The shape is the one ``to_http_exception`` builds, extras included: a
    refusal that escapes a route without being caught answers the reader the
    same structured detail the API layer builds by hand.
    """
    detail = {"code": exc.refusal.code, "message": exc.refusal.message}
    if exc.refusal.detail:
        detail.update(exc.refusal.detail)
    return JSONResponse(status_code=exc.refusal.status, content={"detail": detail})


def register_refusal_handlers(app) -> None:
    """Register the refusal handler on a FastAPI app."""
    app.add_exception_handler(RefusalError, refusal_exception_handler)
