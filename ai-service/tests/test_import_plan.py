"""Unit tests for the import planner (Epic 13.2, apply half)."""

import pytest

from app.features import export as ex
from app.features import import_plan as pl


def _bundle_with(resumes=("r1",), memories=("m1",)) -> dict:
    raw = {
        "profile": {"id": "u1", "display_name": "Ada"},
        "resumes": [{"id": r, "resume_title": r, "version": 1, "plaintext": r}
                    for r in resumes],
        "knowledge": [],
        "job_descriptions": [],
        "interviews": [],
        "memories": [{"id": m, "kind": "preference", "content": m} for m in memories],
    }
    return ex.build_bundle("u1", raw)


def _edited(bundle: dict) -> dict:
    """A bundle whose data was changed by the test, re-sealed the honest way.

    ``validate_bundle`` refuses a payload whose manifest hash no longer matches,
    so a test that edits a row has to recompute the hash at the same time as it
    edits -- which is also what a real exporter does.
    """
    bundle["manifest"]["content_hash"] = ex.content_hash(bundle["data"])
    return bundle


def test_plan_all_creates_without_existing():
    out = pl.plan_import(_bundle_with())
    assert out["op_counts"]["delete"] == 0
    assert out["op_counts"]["create"] == out["op_counts"]["total"]
    # every op is a create
    for sec, ops in out["sections"].items():
        assert all(o["op"] == "create" for o in ops)


def test_plan_update_and_delete_with_existing():
    existing = _bundle_with(resumes=("r1", "r2"), memories=("m1",))
    incoming = _bundle_with(resumes=("r1", "r3"), memories=("m1",))
    # r1 is the same row in both bundles, so its own op is a skip; give it a
    # new version to keep this case about the update it is named for.
    incoming["data"]["resumes"][0]["version"] = 2
    _edited(incoming)
    out = pl.plan_import(incoming, existing=existing)
    resume_ops = {o["id"]: o["op"] for o in out["sections"]["resumes"]}
    assert resume_ops["r1"] == "update"
    assert resume_ops["r3"] == "create"
    # r2 was in existing but not in incoming -> delete
    assert resume_ops["r2"] == "delete"


def test_plan_invalid_bundle_raises():
    b = _bundle_with()
    b["manifest"]["content_hash"] = "tampered"
    with pytest.raises(ValueError) as exc:
        pl.plan_import(b)
    assert "content_hash" in str(exc.value)


def test_plan_profile_upsert():
    without = pl.plan_import(_bundle_with())
    assert without["sections"]["profile"][0]["op"] == "create"
    same = pl.plan_import(_bundle_with(), existing=_bundle_with())
    assert same["sections"]["profile"][0]["op"] == "skip", (
        "the same profile in and out is not a write"
    )
    changed = _bundle_with()
    changed["data"]["profile"]["display_name"] = "Ada Lovelace"
    _edited(changed)
    out = pl.plan_import(changed, existing=_bundle_with())
    assert out["sections"]["profile"][0]["op"] == "update"


def test_plan_an_identical_reimport_is_all_skips_and_writes_nothing():
    """The preview's promise: unchanged rows are skipped.

    Re-importing the bundle the workspace itself exported changes nothing,
    so every row of it is a skip -- not an update, which the backend would
    execute as a write. This is the assertion the copy in the product's own
    "Your data" panel depends on.
    """
    b = _bundle_with()
    out = pl.plan_import(b, existing=b)
    assert out["op_counts"]["delete"] == 0
    assert out["op_counts"]["create"] == 0
    assert out["op_counts"]["update"] == 0
    assert out["op_counts"]["skip"] == out["op_counts"]["total"] > 0
    assert all(o["op"] == "skip" for sec in out["sections"].values() for o in sec)


def test_plan_counts_the_skips_alongside_the_writes():
    existing = _bundle_with(resumes=("r1", "r2"), memories=("m1",))
    incoming = _bundle_with(resumes=("r1", "r3"), memories=("m1",))
    incoming["data"]["resumes"][0]["version"] = 2
    incoming["data"]["profile"]["display_name"] = "Ada Lovelace"
    _edited(incoming)
    counts = pl.plan_import(incoming, existing=existing)["op_counts"]
    assert counts["create"] == 1          # r3
    assert counts["update"] == 2          # r1, profile
    assert counts["delete"] == 1          # r2
    assert counts["skip"] == 1            # memory m1
    assert counts["total"] == counts["create"] + counts["update"] + counts["delete"] + counts["skip"]


def test_plan_a_changed_row_is_an_update_not_a_skip():
    existing = _bundle_with(memories=("m1",))
    incoming = _bundle_with(memories=("m1",))
    incoming["data"]["memories"][0]["content"] = "now prefers on-site"
    _edited(incoming)
    op = pl.plan_import(incoming, existing=existing)["sections"]["memories"][0]
    assert op["op"] == "update", f"a changed row was not planned as a write: {op}"


def test_plan_the_stamps_a_restore_does_not_write_are_not_a_change():
    """``updated_at`` is stamped by the database, not by the bundle.

    The first apply bumps it, so comparing whole rows would make every row
    the import had just written look changed on the next run -- the plan
    would keep writing and "unchanged rows are skipped" would never hold.
    The comparison covers the fields the apply writes, and the stamps are
    not among them.
    """
    existing = _bundle_with()
    incoming = _bundle_with()
    for rows in (existing["data"]["resumes"], incoming["data"]["resumes"]):
        rows[0]["created_at"] = "2026-01-01T00:00:00Z"
        rows[0]["updated_at"] = "2026-01-02T00:00:00Z"
    for rows in (existing["data"]["memories"], incoming["data"]["memories"]):
        rows[0]["created_at"] = "2026-01-01T00:00:00Z"
        rows[0]["updated_at"] = "2026-01-02T00:00:00Z"
    incoming["data"]["resumes"][0]["updated_at"] = "2026-10-27T09:00:00Z"
    _edited(incoming)
    ops = {o["id"]: o["op"] for o in
           pl.plan_import(incoming, existing=existing)["sections"]["resumes"]}
    assert ops["r1"] == "skip"


def test_plan_per_item_content_hash_is_stable():
    b = _bundle_with()
    out = pl.plan_import(b)
    h1 = next(o["content_hash"] for o in out["sections"]["resumes"] if o["id"] == "r1")
    out2 = pl.plan_import(b)
    h2 = next(o["content_hash"] for o in out2["sections"]["resumes"] if o["id"] == "r1")
    assert h1 == h2 and h1 is not None
