"""Unit tests for selective section redaction (Epic 13.3).

And for the three things that made a redacted bundle unusable, which is
the whole point of the feature: a bundle you deliberately made shareable
has to still be a bundle the product can restore.
"""

import pytest

from app.features import export as ex
from app.features import export_redact as rd
from app.features import import_plan as ip


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


def _existing() -> dict:
    """A target that already has its own rows, including its own knowledge."""
    raw = {
        "profile": {"id": "u2", "display_name": "Someone Else"},
        "resumes": [{"id": "r9", "resume_title": "Theirs", "version": 1,
                     "plaintext": "y"}],
        "knowledge": [{"id": "d9", "title": "THEIR OWN NOTE",
                       "media_type": "text/markdown", "status": "ready"}],
        "job_descriptions": [],
        "interviews": [],
        "memories": [],
    }
    return ex.build_bundle("u2", raw)


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


# --------------------------------------------------------------------------- #
# A redacted bundle is still a bundle.
# --------------------------------------------------------------------------- #


def test_the_redacted_bundle_still_validates():
    """The redaction must not make the file the reader is about to share unusable.

    The import path validates the bundle before it plans anything, and it
    validates it against the sections a bundle of this schema version has
    to carry. A redaction removes one of them -- on purpose -- so the
    validator has to know that a withheld section is not a missing one.
    Without that, the reader redacts a section, hands the file over, and
    the person on the other end is told the file is broken.
    """
    out = rd.redact_bundle(_bundle(), ["knowledge"])
    assert ex.validate_bundle(out) == [], (
        f"the redacted bundle does not validate: {ex.validate_bundle(out)}"
    )


def test_a_bundle_that_is_merely_truncated_still_fails_to_validate():
    # The other half of the rule: a section that is *missing* and was never
    # withheld is still a truncated bundle, and the validator must still
    # say so. A validator that forgave every missing section would let a
    # half-written backup through.
    b = _bundle()
    del b["data"]["knowledge"]
    assert any("knowledge" in e for e in ex.validate_bundle(b)), (
        f"a truncated bundle must not validate: {ex.validate_bundle(b)}"
    )


def test_the_counts_stop_claiming_the_rows_the_bundle_dropped():
    """The manifest's counts are what the export screen shows and what the
    printable document ends with.

    A count that still says "knowledge: 1" after the reader asked for the
    knowledge to be gone tells the reader their data is still in the file
    they are about to share -- the exact opposite of what they asked for,
    and the exact thing they will not notice until it is too late.
    """
    b = _bundle()
    out = rd.redact_bundle(b, ["knowledge"])
    counts = out["manifest"]["counts"]
    assert counts["knowledge"] == 0, f"the counts still claim the dropped rows: {counts}"
    # And the counts of the sections that stayed are the ones they were.
    assert counts["resumes"] == b["manifest"]["counts"]["resumes"]
    assert counts["interviews"] == b["manifest"]["counts"]["interviews"]
    # Every section still has a count: the manifest describes the whole
    # bundle, and a missing key would read as "unknown" rather than "none".
    assert set(counts) == set(ex.SECTIONS)


def test_the_printable_document_stops_counting_the_dropped_rows():
    # The Markdown view is what the reader actually shares, and its last
    # line is the counts. A stale count there is the one that travels.
    out = rd.redact_bundle(_bundle(), ["knowledge"])
    md = ex.to_markdown(out)
    assert "knowledge=0" in md, f"the printable view still counts the dropped rows:\n{md}"
    assert "knowledge=1" not in md, f"the printable view still counts the dropped rows:\n{md}"


def test_a_redacted_bundle_can_still_be_restored():
    """The redaction's whole point is a file the reader can hand over.

    So the redacted file has to survive the path that restores it: the
    plan is computed from the bundle, and a bundle that raises here is a
    file nobody can import.
    """
    out = rd.redact_bundle(_bundle(), ["knowledge"])
    plan = ip.plan_import(out, existing=_existing())
    assert "knowledge" not in plan["sections"], (
        "a withheld section must not be planned at all: "
        f"{plan['sections'].get('knowledge')}"
    )


def test_a_withheld_section_does_not_delete_the_target_s_rows():
    """The dangerous one.

    The plan reads "the bundle carries no rows of this section" as "delete
    every row of this section at the target". For a section the sharer
    *withheld* that reading destroys data the bundle never claimed to
    carry -- the target's own knowledge, gone, because the sharer chose
    not to share theirs.
    """
    out = rd.redact_bundle(_bundle(), ["knowledge"])
    plan = ip.plan_import(out, existing=_existing())
    deletes = [op for ops in plan["sections"].values() for op in ops
               if op["op"] == "delete"]
    assert all(op["id"] != "d9" for op in deletes), (
        f"the plan deletes the target's own knowledge: {deletes}"
    )


def test_a_section_that_was_not_withheld_still_deletes_what_the_bundle_omits():
    # The other half of the rule, so the fix cannot have turned the import
    # into a no-op: a bundle that genuinely carries fewer rows than the
    # target still plans the deletes. The difference is the manifest's
    # record, not the emptiness.
    # The honest comparison: a bundle that never had the knowledge, and so
    # never withheld it either.
    plain = ex.build_bundle("u1", {
        "profile": {"id": "u1", "display_name": "Ada"},
        "resumes": [{"id": "r1", "resume_title": "Main", "version": 1,
                     "plaintext": "x"}],
        "knowledge": [],
        "job_descriptions": [],
        "interviews": [],
        "memories": [],
    })
    plan = ip.plan_import(plain, existing=_existing())
    deletes = [op for ops in plan["sections"].values() for op in ops
               if op["op"] == "delete"]
    assert any(op["id"] == "d9" for op in deletes), (
        f"an empty section must still plan the delete: {deletes}"
    )
