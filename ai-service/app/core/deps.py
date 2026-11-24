import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass

from fastapi import Header, HTTPException, Request

from app.core.config import get_settings


@dataclass
class Ctx:
    user_id: str
    run_id: str | None = None


def _verify_service_identity(
    settings,
    request: Request,
    user_id: str,
    service_id: str,
    timestamp: str,
    signature: str,
) -> None:
    """Epic 436 — verify the opt-in, time-bound proof of *which service* called.

    The shared token still opens the door; this says who is holding it. A blank
    key keeps every existing dev/offline deployment byte-for-byte identical.
    The canonical string is the Java signer's verbatim — a cross-language test
    vector pins it so the two halves cannot drift apart silently.
    """
    key = (getattr(settings, "service_signing_key", "") or "").strip()
    if not key:
        return
    if not service_id or not timestamp or not signature:
        raise HTTPException(status_code=401, detail="invalid service identity")
    expected_id = (getattr(settings, "internal_client_id", "") or "").strip()
    if not expected_id or not secrets.compare_digest(service_id, expected_id):
        raise HTTPException(status_code=401, detail="invalid service identity")
    try:
        sent_at = int(timestamp)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="invalid service identity")
    skew_ms = max(1, int(getattr(settings, "service_signature_skew_s", 300) or 300)) * 1000
    if abs(int(time.time() * 1000) - sent_at) > skew_ms:
        raise HTTPException(status_code=401, detail="invalid service identity")
    canonical = f"{timestamp}\n{request.method.upper()}\n{request.url.path}\n{user_id}"
    expected = hmac.new(
        key.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not secrets.compare_digest(expected, signature.lower()):
        raise HTTPException(status_code=401, detail="invalid service identity")


async def require_internal(
    request: Request,
    x_internal_token: str = Header(default=""),
    x_user_id: str = Header(default="", alias="X-User-Id"),
    x_run_id: str = Header(default="", alias="X-Run-Id"),
    x_service_id: str = Header(default="", alias="X-Service-Id"),
    x_service_timestamp: str = Header(default="", alias="X-Service-Timestamp"),
    x_service_signature: str = Header(default="", alias="X-Service-Signature"),
) -> Ctx:
    s = get_settings()
    expected = (s.internal_api_token or "").strip()
    if not expected or not secrets.compare_digest(x_internal_token, expected):
        raise HTTPException(status_code=401, detail="invalid internal token")
    user_id = (x_user_id or "").strip()
    # Sign over the header exactly as the Java side sent it; only the Ctx uses the
    # stripped value. Stripping before signing would make a padded header unfixable.
    _verify_service_identity(
        s, request, x_user_id or "", x_service_id, x_service_timestamp, x_service_signature
    )
    if not user_id:
        raise HTTPException(status_code=400, detail="X-User-Id required")
    return Ctx(user_id=user_id, run_id=x_run_id or None)
