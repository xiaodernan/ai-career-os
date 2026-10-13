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
    with_existing = pl.plan_import(_bundle_with(), existing=_bundle_with())
    assert with_existing["sections"]["profile"][0]["op"] == "update"


def test_plan_idempotent_reimport_is_all_updates_no_deletes():
    b = _bundle_with()
    out = pl.plan_import(b, existing=b)
    assert out["op_counts"]["delete"] == 0
    assert out["op_counts"]["create"] == 0
    assert out["op_counts"]["update"] == out["op_counts"]["total"]


def test_plan_per_item_content_hash_is_stable():
    b = _bundle_with()
    out = pl.plan_import(b)
    h1 = next(o["content_hash"] for o in out["sections"]["resumes"] if o["id"] == "r1")
    out2 = pl.plan_import(b)
    h2 = next(o["content_hash"] for o in out2["sections"]["resumes"] if o["id"] == "r1")
    assert h1 == h2 and h1 is not None
