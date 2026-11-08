"""Backend application.yml must preserve key runtime/schema safety invariants.

Source-level gate: schema changes go through Flyway (not Hibernate auto-DDL),
Open Session in View stays off, graceful shutdown is configured, and API docs
paths remain consistent with SecurityConfig/ops expectations.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_YML = ROOT / "backend" / "src" / "main" / "resources" / "application.yml"


def test_backend_application_config_safety_invariants() -> None:
    text = APP_YML.read_text(encoding="utf-8")
    assert re.search(r"(?m)^\s*ddl-auto:\s*none\s*$", text), "Hibernate ddl-auto must be none (Flyway owns schema)"
    assert re.search(r"(?m)^\s*open-in-view:\s*false\s*$", text), "spring.jpa.open-in-view must be false"
    assert re.search(r"(?m)^\s*shutdown:\s*graceful\s*$", text), "server.shutdown must be graceful"
    assert re.search(r"(?m)^\s*flyway:\s*$", text) and re.search(r"(?m)^\s*enabled:\s*true\s*$", text), (
        "Flyway must be enabled"
    )
    # Docs paths the security config permits.
    assert "api-docs.path: /api-docs" in text
    assert "swagger-ui.path: /api-docs/ui" in text
