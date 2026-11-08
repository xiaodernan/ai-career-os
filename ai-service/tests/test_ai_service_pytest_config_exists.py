"""ai-service pytest config must exist and keep CI-critical settings.

CI runs `python -m pytest -q` from `ai-service/`. The config ensures asyncio
tests run correctly and the default test path is `tests/`.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTEST_INI = ROOT / "ai-service" / "pytest.ini"


def test_ai_service_pytest_ini_has_required_settings() -> None:
    assert PYTEST_INI.is_file(), "ai-service/pytest.ini missing"
    text = PYTEST_INI.read_text(encoding="utf-8")
    assert "asyncio_mode" in text and "auto" in text, "pytest.ini must set asyncio_mode = auto"
    assert "testpaths" in text and "tests" in text, "pytest.ini must set testpaths = tests"
