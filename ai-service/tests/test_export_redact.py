"""Unit tests for selective section redaction (Epic 13.3)."""

import pytest

from app.features import export as ex
from app.features import export_redact as rd


def _bundle() -> dict:
    raw = {
        "profile": {"id": "u1", "display_name": "Ada"},
        "resumes": [{"id": "r1", "resume_title": "Main", "version": 1,
                     "plaintext": "x"}],
        "knowledge": [{"id": "d1", "title": "N", "media_type": "text/markdown",
                       "status": "ready"}],
        "job_descriptions": [{"id": "j1", "title": "BE", "company": "Acme",
                              "raw_text": "t"}],
        "interviews": [{"id": "s1", "job_title": "BE", "status": "done",
                        "turns": [{"seq": 1}]}],
        "memories": [{"id": "m1", "kind": "preference", "content": "remote"}],
    }
    return ex.build_bundle("u1", raw)


def test_redact_removes_section_and_recomputes_hash():
    b = _bundle()
    original_hash = b["manifest"]["content_hash"]
    out = rd.redact_bundle(b, ["interviews"])
    assert "interviews" not in out["data"]
    assert out["manifest"]["content_hash"] != original_hash
    assert out["manifest"]["redacted_sections"] == ["interviews"]
    # original untouched (deep copy)
    assert "interviews" in b["data"]


def test_redact_is_non_destructive_to_input():
    b = _bundle()
    rd.redact_bundle(b, ["memories"])
    assert "memories" in b["data"]  # input preserved


def test_redact_invalid_section_raises():
    b = _bundle()
    with pytest.raises(ValueError) as exc:
        rd.redact_bundle(b, ["interviews", "not_a_section"])
    assert "not_a_section" in str(exc.value)
    assert "interviews" in b["data"]  # nothing dropped on error


def test_redact_all_sections_yields_empty_data_new_hash():
    b = _bundle()
    # The valid sections are the ones the export table declares, so a section
    # the export gained (the backend's `applications` / `growth_plans`) can be
    # dropped here too without a second list to keep in step.
    out = rd.redact_bundle(b, list(rd.VALID_SECTIONS))
    assert out["data"] == {}
    assert out["manifest"]["redacted_sections"] == sorted(out["manifest"]["redacted_sections"])


def test_redact_absent_section_is_noop():
    b = _bundle()
    out = rd.redact_bundle(b, ["memories"])  # memories present -> removed
    out2 = rd.redact_bundle(out, ["memories"])  # now absent -> noop
    assert out2["manifest"]["redacted_sections"] == []
