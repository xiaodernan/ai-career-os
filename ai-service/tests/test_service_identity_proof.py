"""Epic 436 — the opt-in, time-bound proof of WHICH service called the internal door.

The shared token answers "may this caller use /internal/*"; it never expires and
says nothing about the caller, so a leaked literal lets anyone forge any X-User-Id.
This gate drives the single dependency every internal route shares, directly and
without a database, a lifespan, a Docker network or a model call. It also pins the
fixed HMAC vector against the Java signer so the two languages cannot drift.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core import deps

ROOT = Path(__file__).resolve().parents[2]  # the repository root
TOKEN = "shared-secret-between-backend-and-ai-service"
KEY = "a-separate-signing-key-not-the-shared-token"
CLIENT = "career-os-backend"
PATH = "/internal/agents/chat"


def settings(key: str = "") -> SimpleNamespace:
    return SimpleNamespace(
        internal_api_token=TOKEN,
        service_signing_key=key,
        internal_client_id=CLIENT,
        service_signature_skew_s=300,
    )


def request(method: str = "POST", path: str = PATH) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
        }
    )


def proof(key: str, user: str, at_ms: str | None = None, path: str = PATH,
          method: str = "POST", service: str = CLIENT) -> tuple[str, str, str]:
    ts = at_ms or str(int(time.time() * 1000))
    canonical = f"{ts}\n{method.upper()}\n{path}\n{user}"
    sig = hmac.new(key.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    return service, ts, sig


async def call(**overrides):
    """Call the dependency as FastAPI would: every header is a plain string."""
    kwargs = dict(
        request=request(),
        x_internal_token=TOKEN,
        x_user_id="",
        x_run_id="",
        x_service_id="",
        x_service_timestamp="",
        x_service_signature="",
    )
    kwargs.update(overrides)
    return await deps.require_internal(**kwargs)


@pytest.fixture
def no_settings(monkeypatch):
    monkeypatch.setattr(deps, "get_settings", lambda: settings())
    return monkeypatch


@pytest.fixture
def with_key(monkeypatch):
    monkeypatch.setattr(deps, "get_settings", lambda: settings(KEY))
    return monkeypatch


@pytest.mark.asyncio
async def test_legacy_behaviour_is_unchanged_when_no_key_is_configured(no_settings) -> None:
    # Token only, no user: the old 400 still arrives; the new headers are ignored.
    with pytest.raises(HTTPException) as err:
        await call()
    assert err.value.status_code == 400
    assert err.value.detail == "X-User-Id required"

    ctx = await call(x_user_id="u-1")
    assert ctx.user_id == "u-1"


@pytest.mark.asyncio
async def test_a_valid_proof_is_accepted(with_key) -> None:
    sid, ts, sig = proof(KEY, "u-1")
    ctx = await call(
        x_user_id="u-1",
        x_service_id=sid,
        x_service_timestamp=ts,
        x_service_signature=sig,
    )
    assert ctx.user_id == "u-1"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda p: (None, p[1], p[2]), id="missing-id"),
        pytest.param(lambda p: ("someone-else", p[1], p[2]), id="wrong-id"),
        pytest.param(lambda p: (p[0], "1000", p[2]), id="stale"),
        pytest.param(lambda p: (p[0], str(int(time.time() * 1000) + 600_000), p[2]), id="future"),
        pytest.param(lambda p: (p[0], p[1], "0" * 64), id="tampered-signature"),
        pytest.param(lambda p: proof(KEY, "u-2", p[1]), id="signed-for-another-user"),
        pytest.param(lambda p: proof(KEY, "u-1", p[1], path="/internal/other"), id="signed-for-another-path"),
    ],
)
async def test_bad_proofs_are_refused(with_key, mutate) -> None:
    base = proof(KEY, "u-1")
    sid, ts, sig = mutate(base)
    with pytest.raises(HTTPException) as err:
        await call(
            x_user_id="u-1",
            x_service_id=sid or "",
            x_service_timestamp=ts,
            x_service_signature=sig,
        )
    assert err.value.status_code == 401
    assert err.value.detail == "invalid service identity"


@pytest.mark.asyncio
async def test_a_leaked_shared_token_alone_cannot_open_the_door(with_key) -> None:
    with pytest.raises(HTTPException) as err:
        await call(x_user_id="u-1")
    assert err.value.status_code == 401
    assert err.value.detail == "invalid service identity"


def test_cross_language_vector_matches_the_java_signer() -> None:
    canonical = "1700000000000\nPOST\n/internal/agents/chat\nu-1"
    assert hmac.new(b"k", canonical.encode(), hashlib.sha256).hexdigest() == (
        "c39ab0411f4e844efd9e1f8422c4dc90a875f33828d80d042ae4d812033ec377"
    )
    java_test = ROOT / "backend/src/test/java/com/careeros/ai/ServiceIdentitySignerTest.java"
    assert java_test.exists()
    source = java_test.read_text(encoding="utf-8")
    assert "c39ab0411f4e844efd9e1f8422c4dc90a875f33828d80d042ae4d812033ec377" in source
    assert '1700000000000\\nPOST\\n/internal/agents/chat\\nu-1' in source


def test_both_hops_stamp_the_same_headers() -> None:
    client_src = (
        ROOT / "backend/src/main/java/com/careeros/ai/HttpAiServiceClient.java"
    ).read_text(encoding="utf-8")
    relay_src = (
        ROOT / "backend/src/main/java/com/careeros/ai/SseRelayService.java"
    ).read_text(encoding="utf-8")
    for source in (client_src, relay_src):
        assert "ServiceIdentitySigner.forRequest(" in source
        assert "ServiceIdentitySigner.HEADER_ID" in source
        assert "ServiceIdentitySigner.HEADER_SIGNATURE" in source
    # Exactly one stamping site per hop — the interceptor and the SSE relay. The
    # anonymous health probe is a separate client and must never gain a signature.
    assert client_src.count("ServiceIdentitySigner.forRequest(") == 1
    assert relay_src.count("ServiceIdentitySigner.forRequest(") == 1


def test_verification_uses_constant_time_compare() -> None:
    source = (ROOT / "ai-service/app/core/deps.py").read_text(encoding="utf-8")
    assert "secrets.compare_digest(expected, signature.lower())" in source
    assert "secrets.compare_digest(service_id, expected_id)" in source
    assert "service_signing_key" in source
