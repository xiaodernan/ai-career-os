"""The deployed stack must name its commit (Epic 78).

NEXT_HORIZON Epic 78: a golden-journey run against a stale image is worse than no
run, yet nothing in `/health` named the code. This gate wires the sha end to end:
image build arg -> container env -> /health payload -> journey report line.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HEALTH_SERVICE = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "health" / "HealthService.java"
AI_MAIN = ROOT / "ai-service" / "app" / "main.py"
AI_CONFIG = ROOT / "ai-service" / "app" / "core" / "config.py"
BACKEND_DOCKERFILE = ROOT / "backend" / "Dockerfile"
AI_DOCKERFILE = ROOT / "ai-service" / "Dockerfile"
DEV_COMPOSE = ROOT / "docker-compose.yml"
PROD_COMPOSE = ROOT / "docker-compose.prod.yml"
JOURNEY = ROOT / "scripts" / "journey_api.py"


def test_backend_health_reports_build_sha() -> None:
    text = HEALTH_SERVICE.read_text(encoding="utf-8")
    assert "APP_BUILD_SHA" in text
    assert 'body.put("buildSha"' in text


def test_ai_service_health_reports_build_sha() -> None:
    cfg = AI_CONFIG.read_text(encoding="utf-8")
    main = AI_MAIN.read_text(encoding="utf-8")
    assert "app_build_sha" in cfg
    assert "build_sha" in main


def test_dockerfiles_bake_build_sha_env() -> None:
    for path in (BACKEND_DOCKERFILE, AI_DOCKERFILE):
        text = path.read_text(encoding="utf-8")
        assert "ARG APP_BUILD_SHA=dev" in text, f"{path} must declare ARG APP_BUILD_SHA"
        assert "ENV APP_BUILD_SHA=${APP_BUILD_SHA}" in text, f"{path} must export APP_BUILD_SHA"


def test_compose_files_pass_build_sha_arg() -> None:
    for path in (DEV_COMPOSE, PROD_COMPOSE):
        text = path.read_text(encoding="utf-8")
        assert "APP_BUILD_SHA" in text, f"{path} must pass APP_BUILD_SHA to app image builds"


def test_journey_api_prints_build_sha_from_health() -> None:
    text = JOURNEY.read_text(encoding="utf-8")
    assert "== build:" in text and "/health" in text
