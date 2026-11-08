"""Backend ProductionGuard must exist to refuse unsafe prod startup.

The backend refuses to boot in prod on published defaults/placeholders (JWT,
internal token, DB/object-store/mail/CORS/web-base secrets/config). This is a
critical safety net; its removal silently allows unsafe deployments.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "config" / "ProductionGuard.java"


def test_backend_production_guard_exists_and_checks_internal_token() -> None:
    assert GUARD.is_file(), "ProductionGuard.java missing"
    text = GUARD.read_text(encoding="utf-8")
    assert "INTERNAL_API_TOKEN" in text, "ProductionGuard must guard INTERNAL_API_TOKEN"
    assert "offender" in text.lower() or "IllegalStateException" in text, (
        "ProductionGuard must refuse unsafe prod config"
    )
    assert "@Component" in text or "class ProductionGuard" in text
