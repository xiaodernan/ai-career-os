"""Core observability and error-handling wiring must remain installed.

ai-service: RequestIdMiddleware and refusal/error handlers registered in main.
backend: RequestIdFilter exists (adds request correlation id to responses/logs).
These are foundational for Epic 75-style observability and consistent error
behavior; removing them silently degrades diagnosability.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_ai_service_wires_request_id_and_error_handlers() -> None:
    main = (ROOT / "ai-service" / "app" / "main.py").read_text(encoding="utf-8")
    assert "RequestIdMiddleware" in main and "add_middleware(RequestIdMiddleware)" in main
    assert "register_refusal_handlers" in main
    assert (ROOT / "ai-service" / "app" / "core" / "request_id.py").is_file()
    assert (ROOT / "ai-service" / "app" / "core" / "errors.py").is_file()


def test_backend_request_id_filter_exists() -> None:
    p = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "common" / "RequestIdFilter.java"
    assert p.is_file(), "backend RequestIdFilter missing"
    text = p.read_text(encoding="utf-8", errors="replace")
    # Should participate in filter chain / set a request id (implementation detail flexible).
    assert "request" in text.lower() and ("id" in text.lower() or "X-Request-Id" in text or "X-Request-ID" in text)
