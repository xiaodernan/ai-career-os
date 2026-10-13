"""Unit tests for the portable export composition (forward Epic 13.1 / 13.2 / 13.3).

The composition layer is deliberately split into pure helpers (``build_bundle``,
``content_hash``, ``anonymize``, ``diff_bundles``, ``to_markdown``) and an I/O
driver (``gather_raw`` / ``export_bundle``) whose fetch functions are
module-level and monkeypatched here — so the whole contract is held offline with
no database. The contract this file pins:

- a fixed top-level shape and ``manifest`` (schema_version / generator / counts /
  content_hash / anonymized);
- ``content_hash`` is computed over ``data`` only and is stable across re-exports
  of unchanged data (the primitive idempotent re-import needs);
- ``anonymize`` strips the reserved PII fields and re-stamps the hash;
- ``diff_bundles`` reports added / removed / changed per section;
- backend-owned sections (``applications``, ``growth_plans``) are *reserved*
  (absent) until the bridge fills them.
"""

import json

import pytest

from app.features import export as ex


# ---------------- fixtures ----------------


def _sample_raw() -> dict:
    return {
        "profile": {
            "id": "u1",
            "email": "a@b.com",
            "display_name": "Ada",
            "headline": "Backend Engineer",
            "summary": "Built things.",
        },
        "resumes": [
            {"id": "r1", "resume_title": "Main", "version": 2, "plaintext": "Exp at X"},
        ],
        "knowledge": [
            {"id": "d1", "title": "Notes", "media_type": "text/markdown",
             "status": "ready"},
        ],
        "job_descriptions": [
            {"id": "j1", "title": "BE", "company": "Acme", "raw_text": "JD text"},
        ],
        "interviews": [
            {"id": "s1", "job_title": "BE", "status": "done",
             "turns": [{"seq": 1, "question": "q", "answer": "a"}]},
        ],
        "memories": [
            {"id": "m1", "kind": "preference", "content": "Prefers remote"},
        ],
    }


# ---------------- build_bundle / shape ----------------


def test_bundle_shape_and_manifest():
    bundle = ex.build_bundle("u1", _sample_raw())
    assert set(bundle) == {
        "schema_version", "generator", "generated_at", "user", "manifest", "data"}
    assert bundle["schema_version"] == ex.SCHEMA_VERSION
    assert bundle["generator"] == ex.GENERATOR
    m = bundle["manifest"]
    assert m["schema_version"] == ex.SCHEMA_VERSION
    assert m["generator"] == ex.GENERATOR
    assert m["counts"] == {
        "profile": 1, "resumes": 1, "knowledge": 1,
        "job_descriptions": 1, "interviews": 1, "memories": 1}
    assert m["anonymized"] is False
    assert isinstance(m["content_hash"], str) and len(m["content_hash"]) == 64


def test_backend_sections_reserved_not_present():
    bundle = ex.build_bundle("u1", _sample_raw())
    assert "applications" not in bundle["data"]
    assert "growth_plans" not in bundle["data"]


def test_empty_bundle_counts_zero():
    bundle = ex.build_bundle("u1", {})
    assert all(v == 0 for v in bundle["manifest"]["counts"].values())


# ---------------- content_hash stability ----------------


def test_content_hash_stable_across_reexport():
    a = ex.build_bundle("u1", _sample_raw())
    b = ex.build_bundle("u1", _sample_raw())
    assert a["manifest"]["content_hash"] == b["manifest"]["content_hash"]


def test_content_hash_changes_when_data_changes():
    base = _sample_raw()
    a = ex.build_bundle("u1", base)
    mutated = _sample_raw()
    mutated["profile"]["headline"] = "Staff Engineer"
    b = ex.build_bundle("u1", mutated)
    assert a["manifest"]["content_hash"] != b["manifest"]["content_hash"]


def test_content_hash_ignores_generated_at_and_hash():
    # Recompute the hash from the data payload only.
    data = {s: _sample_raw().get(s) for s in ex.SECTIONS}
    h1 = ex.content_hash(data)
    h2 = ex.content_hash(json.loads(json.dumps(data)))  # round-trip, same content
    assert h1 == h2


# ---------------- anonymize (13.3) ----------------


def test_anonymize_strips_pii_and_restamps():
    bundle = ex.build_bundle("u1", _sample_raw())
    anon = ex.anonymize(bundle)
    assert anon["user"]["anonymized"] is True
    assert anon["manifest"]["anonymized"] is True
    profile = anon["data"]["profile"]
    assert profile["email"] is None
    assert profile["display_name"] is None
    # non-PII fields survive
    assert profile["headline"] == "Backend Engineer"


def test_anonymize_does_not_mutate_original():
    bundle = ex.build_bundle("u1", _sample_raw())
    ex.anonymize(bundle)
    assert bundle["data"]["profile"]["email"] == "a@b.com"


def test_anonymize_with_custom_fields():
    bundle = ex.build_bundle("u1", _sample_raw())
    anon = ex.anonymize(bundle, drop=("headline",))
    assert anon["data"]["profile"]["headline"] is None
    assert anon["data"]["profile"]["email"] == "a@b.com"


# ---------------- diff_bundles (13.2) ----------------


def test_diff_detects_added_changed_removed():
    old = ex.build_bundle("u1", _sample_raw())
    new_raw = _sample_raw()
    # change one memory
    new_raw["memories"][0]["content"] = "Prefers hybrid"
    # add a memory
    new_raw["memories"].append({"id": "m2", "kind": "fact", "content": "Knows Go"})
    # remove a resume
    new_raw["resumes"] = []
    new = ex.build_bundle("u1", new_raw)

    diff = ex.diff_bundles(old, new)
    mem = diff["sections"]["memories"]
    assert "m1" in mem["changed"]
    assert "m2" in mem["added"]
    assert "r1" in diff["sections"]["resumes"]["removed"]


def test_diff_empty_when_identical():
    old = ex.build_bundle("u1", _sample_raw())
    new = ex.build_bundle("u1", _sample_raw())
    diff = ex.diff_bundles(old, new)
    for section in ex.SECTIONS:
        s = diff["sections"][section]
        assert s["added"] == [] and s["changed"] == [] and s["removed"] == []


# ---------------- to_markdown ----------------


def test_to_markdown_renders_every_section():
    bundle = ex.build_bundle("u1", _sample_raw())
    md = ex.to_markdown(bundle)
    for header in ("AI Career OS", "个人档案", "简历版本", "知识库",
                   "职位描述", "模拟面试", "长期记忆"):
        assert header in md


def test_to_markdown_marks_anonymized():
    bundle = ex.anonymize(ex.build_bundle("u1", _sample_raw()))
    md = ex.to_markdown(bundle)
    assert "已匿名" in md


# ---------------- async driver with monkeypatched I/O ----------------


async def test_export_bundle_assembles_from_fetch_layer(monkeypatch):
    raw = _sample_raw()

    async def fake_profile(uid):  # noqa: ANN001
        return raw["profile"]

    async def fake_resumes(uid):  # noqa: ANN001
        return raw["resumes"]

    async def fake_docs(uid):  # noqa: ANN001
        return raw["knowledge"]

    async def fake_jds(uid):  # noqa: ANN001
        return raw["job_descriptions"]

    async def fake_sessions(uid):  # noqa: ANN001
        return [s for s in raw["interviews"]]

    async def fake_turns(ids):  # noqa: ANN001
        return {sid: s.get("turns", []) for sid, s in
                zip([str(s["id"]) for s in raw["interviews"]], raw["interviews"])}

    async def fake_memories(uid):  # noqa: ANN001
        return raw["memories"]

    monkeypatch.setattr(ex, "fetch_profile", fake_profile)
    monkeypatch.setattr(ex, "fetch_resume_versions", fake_resumes)
    monkeypatch.setattr(ex, "fetch_documents", fake_docs)
    monkeypatch.setattr(ex, "fetch_jds", fake_jds)
    monkeypatch.setattr(ex, "fetch_interview_sessions", fake_sessions)
    monkeypatch.setattr(ex, "fetch_interview_turns", fake_turns)
    monkeypatch.setattr(ex, "fetch_memories", fake_memories)

    bundle = await ex.export_bundle("u1")
    assert bundle["data"]["resumes"][0]["id"] == "r1"
    # turns are merged back onto their session
    assert bundle["data"]["interviews"][0]["turns"][0]["question"] == "q"
    assert bundle["manifest"]["counts"]["memories"] == 1


async def test_gather_raw_is_the_async_preimage_of_build(monkeypatch):
    raw = _sample_raw()

    async def fake_profile(uid):  # noqa: ANN001
        return raw["profile"]

    async def fake_resumes(uid):  # noqa: ANN001
        return raw["resumes"]

    async def fake_docs(uid):  # noqa: ANN001
        return raw["knowledge"]

    async def fake_jds(uid):  # noqa: ANN001
        return raw["job_descriptions"]

    async def fake_sessions(uid):  # noqa: ANN001
        return raw["interviews"]

    async def fake_turns(ids):  # noqa: ANN001
        return {str(s["id"]): s["turns"] for s in raw["interviews"]}

    async def fake_memories(uid):  # noqa: ANN001
        return raw["memories"]

    monkeypatch.setattr(ex, "fetch_profile", fake_profile)
    monkeypatch.setattr(ex, "fetch_resume_versions", fake_resumes)
    monkeypatch.setattr(ex, "fetch_documents", fake_docs)
    monkeypatch.setattr(ex, "fetch_jds", fake_jds)
    monkeypatch.setattr(ex, "fetch_interview_sessions", fake_sessions)
    monkeypatch.setattr(ex, "fetch_interview_turns", fake_turns)
    monkeypatch.setattr(ex, "fetch_memories", fake_memories)

    gathered = await ex.gather_raw("u1")
    assert gathered.keys() == set(ex.SECTIONS)
    rebuilt = ex.build_bundle("u1", gathered)
    assert rebuilt["manifest"]["counts"]["interviews"] == 1
