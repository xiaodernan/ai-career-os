"""Health endpoints relied on by compose/CI/ops must exist.

ai-service exposes `GET /health` (compose/ops probes); backend exposes
`/api/v1/health` (SecurityConfig permits it) and actuator health
(application.yml/compose). This gate asserts the key wiring is present.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_ai_service_health_route_exists() -> None:
    text = (ROOT / "ai-service" / "app" / "main.py").read_text(encoding="utf-8")
    assert '@app.get("/health")' in text or "@app.get('/health')" in text
    assert '"status"' in text or "'status'" in text


def test_backend_public_health_is_permitted_and_actuator_configured() -> None:
    sec = (ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "config" / "SecurityConfig.java").read_text(encoding="utf-8")
    assert '"/api/v1/health"' in sec and "permitAll" in sec
    yml = (ROOT / "backend" / "src" / "main" / "resources" / "application.yml").read_text(encoding="utf-8")
    assert "health" in yml and "prometheus" in yml
