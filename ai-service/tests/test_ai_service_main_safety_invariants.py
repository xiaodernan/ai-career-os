"""ai-service main app must keep key safety invariants.

Source-level gate: ai-service is an internal-only service (backend calls it with
X-Internal-Token; browsers never reach it). It must not install permissive CORS,
and it must refuse mock LLM/voice providers in production at startup.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "ai-service" / "app" / "main.py"


def test_ai_service_does_not_install_cors_middleware() -> None:
    text = MAIN.read_text(encoding="utf-8")
    assert "CORSMiddleware" not in text and "allow_origins" not in text, (
        "ai-service is internal-only; do not add CORS middleware (backend is the browser-facing boundary)"
    )


def test_ai_service_forbids_mock_providers_in_prod() -> None:
    text = MAIN.read_text(encoding="utf-8")
    assert 'mock LLM provider forbidden in prod' in text, "prod must refuse mock LLM provider"
    assert 'mock voice provider forbidden in prod' in text, "prod must refuse mock voice provider"
    assert 'settings.app_env == "prod"' in text or "app_env" in text, (
        "prod guards must be tied to app_env"
    )
