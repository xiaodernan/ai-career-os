"""scripts/verify_gates.ps1 provides a documented offline gate runner.

This is additive tooling (not a CI replacement). The gate checks the script
exists, references pytest and key representative gates, and states it is not a
substitute for full suites/*IT/E2E.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "verify_gates.ps1"


def test_verify_gates_script_exists_and_is_representative() -> None:
    assert SCRIPT.is_file(), "scripts/verify_gates.ps1 missing"
    text = SCRIPT.read_text(encoding="utf-8", errors="replace")
    assert "pytest" in text
    assert "test_every_internal_route_requires_internal_auth.py" in text
    assert "not a substitute" in text.lower() or "full suites" in text.lower()
    assert "*IT" in text or "E2E" in text or "Docker" in text
