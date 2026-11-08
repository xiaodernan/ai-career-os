"""scripts/journey_api.py must propagate a stable X-Request-Id across the journey.

Epic 75: the golden journey doubles as a full-stack probe; every HTTP call must
carry one correlation id so a failure line in the script output can be matched to
the backend/ai-service logs. Source gate (no stack required).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "journey_api.py"


def test_journey_api_sets_one_request_id_on_every_call() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "X-Request-Id" in text, "journey_api.py must set X-Request-Id"
    assert "REQUEST_ID" in text, "journey_api.py must define a REQUEST_ID constant"
    assert '"X-Request-Id", REQUEST_ID' in text, "call() must send the journey-wide REQUEST_ID"
    assert text.count("X-Request-Id") >= 2, "X-Request-Id must appear in the call() helper and in the intro line"
    # The id must be printed with the first line so the operator can grep it.
    assert "X-Request-Id: {REQUEST_ID}" in text, "journey header line must print REQUEST_ID"
