"""Operational security/runbook docs must remain substantive and structured.

These documents are the operator-facing contract for auth boundaries, internal
service auth, secrets handling, and incident/restore procedures. A doc that goes
missing or loses its core sections silently degrades operability. This gate checks
existence and required section markers (not prose quality).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SECURITY = ROOT / "docs" / "SECURITY.md"
RUNBOOK = ROOT / "docs" / "RUNBOOK.md"


def test_security_doc_has_required_sections() -> None:
    assert SECURITY.is_file(), "docs/SECURITY.md is missing"
    text = SECURITY.read_text(encoding="utf-8")
    assert len(text) >= 1500, "SECURITY.md must remain substantive"
    for marker in (
        "User authentication",
        "Service-to-service authentication",
        "X-Internal-Token",
        "INTERNAL_API_TOKEN",
        "Data isolation",
        "user_id",
    ):
        assert marker in text, f"SECURITY.md missing required marker: {marker!r}"


def test_runbook_exists_and_is_substantive() -> None:
    assert RUNBOOK.is_file(), "docs/RUNBOOK.md is missing"
    text = RUNBOOK.read_text(encoding="utf-8")
    assert len(text) >= 800, "RUNBOOK.md must remain substantive"
    # Runbook should cover operational concerns (at least one of these common anchors).
    anchors = ("backup", "restore", "incident", "deploy", "rollback", "health", "monitor")
    assert any(a in text.lower() for a in anchors), (
        "RUNBOOK.md should cover operational procedures (backup/restore/incident/deploy/rollback/health/monitor)"
    )
