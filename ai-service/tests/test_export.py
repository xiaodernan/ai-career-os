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
- the backend-owned sections (``applications``, ``growth_plans``) travel in the
  bundle since 1.1.0 -- the bridge hands them over, and the hash still covers
  the whole document.
"""

import json
from uuid import UUID

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
        "job_descriptions": 1, "interviews": 1, "memories": 1,
        "applications": 0, "growth_plans": 0, "notes": 0, "contacts": 0}
    assert m["anonymized"] is False
    assert isinstance(m["content_hash"], str) and len(m["content_hash"]) == 64


def test_a_bundle_of_real_rows_serializes():
    """The rows come out of Postgres, so their ids are `uuid.UUID` and not strings.

    The fixture above uses `"r1"`, because a fixture is easier to read -- and
    that is exactly why the real export failed: the canonical serializer
    refused a UUID, so the first real workspace with a row in it could not
    produce a bundle at all. The ids are the bundle's whole point, so they
    have to survive the hash.

    This is the case the mocked fetches cannot reach, and it is the one the
    end-to-end suite reaches on every run.
    """
    raw = _sample_raw()
    raw["resumes"][0]["id"] = UUID("11111111-1111-1111-1111-111111111111")
    raw["knowledge"][0]["id"] = UUID("22222222-2222-2222-2222-222222222222")
    raw["interviews"][0]["id"] = UUID("33333333-3333-3333-3333-333333333333")
    raw["interviews"][0]["turns"][0]["session_id"] = UUID(
        "33333333-3333-3333-3333-333333333333")
    raw["profile"]["id"] = UUID("44444444-4444-4444-4444-444444444444")

    bundle = ex.build_bundle("u1", raw)

    # The canonical form is where the hash is computed, and it is where the
    # UUID has to become a string: the bundle's whole point is to carry the
    # ids, and a serializer that refused them could not hash a bundle at all.
    canonical = ex.canonical_json(bundle["data"])
    assert "11111111-1111-1111-1111-111111111111" in canonical
    assert "33333333-3333-3333-3333-333333333333" in canonical
    # And the hash is computed over exactly that.
    assert bundle["manifest"]["content_hash"] == ex.content_hash(bundle["data"])
    # The same rows hashed twice are the same hash: a UUID's string form is
    # stable, which is what "unchanged data exports to the same hash" needs.
    assert ex.build_bundle("u1", raw)["manifest"]["content_hash"] == \
        bundle["manifest"]["content_hash"]


def test_the_backend_sections_come_from_the_bridge():
    """Since 1.1.0 the backend's own sections travel in the bundle.

    The ai-service cannot read them -- it does not write `applications` or
    `growth_plans` -- so the bridge hands them over and the hash is computed
    here, over the whole bundle. Without them an export is a reading list and
    not a record of the search.
    """
    bundle = ex.build_bundle("u1", _sample_raw(), extra={
        "applications": [{"id": "a1", "status": "applied"}],
        "growth_plans": [{"id": "g1", "target_role": "Backend Engineer"}],
    })
    assert bundle["data"]["applications"] == [{"id": "a1", "status": "applied"}]
    assert bundle["data"]["growth_plans"] == [
        {"id": "g1", "target_role": "Backend Engineer"}]
    assert bundle["manifest"]["counts"]["applications"] == 1
    assert bundle["manifest"]["counts"]["growth_plans"] == 1
    # And the hash covers them: the whole bundle is one hashed document.
    assert bundle["manifest"]["content_hash"] == ex.content_hash(bundle["data"])


def test_a_section_the_bridge_did_not_send_stays_absent():
    """Absent and null are different facts.

    "the user has no applications" and "the bridge did not ask" are not the
    same claim, and the import path has to know which one it is looking at --
    so a section that was not handed over is not filled with a null.
    """
    bundle = ex.build_bundle("u1", _sample_raw())
    assert bundle["data"]["applications"] is None
    assert bundle["data"]["growth_plans"] is None
    assert bundle["manifest"]["counts"]["applications"] == 0


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
    """The quick look at a bundle, in the language it was asked for.

    The default is English, like the printable half and like the rest of the
    product; the caller says which language it wants. Both are checked here,
    because a view that only ever renders one language is the defect this
    exists to prevent.
    """
    bundle = ex.build_bundle("u1", _sample_raw())
    english = ex.to_markdown(bundle, "en")
    for header in ("AI Career OS", "Profile", "Resumes", "Knowledge base",
                   "Job descriptions", "Mock interviews", "Long-term memories"):
        assert header in english

    chinese = ex.to_markdown(bundle, "zh")
    for header in ("AI Career OS", "个人档案", "简历版本", "知识库",
                   "职位描述", "模拟面试", "长期记忆"):
        assert header in chinese

    # And the default is the product's default.
    assert ex.to_markdown(bundle) == english


def test_to_markdown_marks_anonymized():
    bundle = ex.anonymize(ex.build_bundle("u1", _sample_raw()))
    assert "已匿名" in ex.to_markdown(bundle, "zh")
    assert "anonymized" in ex.to_markdown(bundle, "en")


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

    async def fake_evaluations(ids):  # noqa: ANN001
        return {str(s["id"]): s["evaluation"] for s in raw["interviews"]
                if s.get("evaluation")}

    async def fake_memories(uid):  # noqa: ANN001
        return raw["memories"]

    monkeypatch.setattr(ex, "fetch_profile", fake_profile)
    monkeypatch.setattr(ex, "fetch_resume_versions", fake_resumes)
    monkeypatch.setattr(ex, "fetch_documents", fake_docs)
    monkeypatch.setattr(ex, "fetch_jds", fake_jds)
    monkeypatch.setattr(ex, "fetch_interview_sessions", fake_sessions)
    monkeypatch.setattr(ex, "fetch_interview_turns", fake_turns)
    monkeypatch.setattr(ex, "fetch_interview_evaluations", fake_evaluations)
    monkeypatch.setattr(ex, "fetch_memories", fake_memories)

    bundle = await ex.export_bundle("u1")
    assert bundle["data"]["resumes"][0]["id"] == "r1"
    # turns are merged back onto their session
    assert bundle["data"]["interviews"][0]["turns"][0]["question"] == "q"
    assert bundle["manifest"]["counts"]["memories"] == 1


# ---------------- serialization / validation (13.1 JSON + 13.2 import) ----------------


def test_serialize_parse_roundtrip():
    bundle = ex.build_bundle("u1", _sample_raw())
    text = ex.serialize_bundle(bundle)
    assert isinstance(text, str)
    parsed = ex.parse_bundle(text)
    assert parsed["manifest"]["content_hash"] == bundle["manifest"]["content_hash"]
    assert parsed["data"]["memories"][0]["content"] == "Prefers remote"


def test_validate_bundle_passes_for_well_formed():
    bundle = ex.build_bundle("u1", _sample_raw())
    assert ex.validate_bundle(bundle) == []


def test_validate_bundle_reports_missing_keys():
    bundle = ex.build_bundle("u1", _sample_raw())
    del bundle["manifest"]["content_hash"]
    del bundle["data"]["memories"]
    errs = ex.validate_bundle(bundle)
    assert any("content_hash" in e for e in errs)
    assert any("memories" in e for e in errs)


def test_validate_bundle_catches_tampered_hash():
    bundle = ex.build_bundle("u1", _sample_raw())
    bundle["data"]["profile"]["headline"] = "Tampered"
    # manifest hash no longer matches the mutated data
    assert any("content_hash" in e for e in ex.validate_bundle(bundle))


def test_write_read_bundle_roundtrip(tmp_path):
    bundle = ex.build_bundle("u1", _sample_raw())
    p = str(tmp_path / "export.json")
    ex.write_bundle(bundle, p)
    loaded = ex.read_bundle(p)
    assert ex.validate_bundle(loaded) == []
    assert loaded["data"]["resumes"][0]["id"] == "r1"


def test_a_bundle_written_before_the_bridge_is_still_valid():
    """A 1.0.0 backup predates the backend sections, and it is still a bundle.

    The required set is read off the bundle's OWN schema version, so a user who
    exports today and restores next year is not told their backup is broken
    because the format grew two sections.
    """
    bundle = ex.build_bundle("u1", _sample_raw())
    legacy = {
        "schema_version": "1.0.0",
        "generator": ex.GENERATOR,
        "generated_at": bundle["generated_at"],
        "user": bundle["user"],
        "manifest": dict(bundle["manifest"], schema_version="1.0.0"),
        "data": {s: bundle["data"][s] for s in ex.LEGACY_SECTIONS},
    }
    legacy["manifest"]["content_hash"] = ex.content_hash(legacy["data"])
    assert ex.validate_bundle(legacy) == []


def test_a_current_bundle_missing_a_backend_section_is_rejected():
    """A 1.1.0 bundle without the backend sections was truncated.

    The two facts -- "the user has no applications" (an empty list) and "the
    section is missing" (a truncated export) -- are different, and the import
    path has to be able to tell them apart.
    """
    bundle = ex.build_bundle("u1", _sample_raw())
    del bundle["data"]["applications"]
    bundle["manifest"]["content_hash"] = ex.content_hash(bundle["data"])
    errs = ex.validate_bundle(bundle)
    assert any("applications" in e for e in errs)


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

    async def fake_evaluations(ids):  # noqa: ANN001
        return {str(s["id"]): s["evaluation"] for s in raw["interviews"]
                if s.get("evaluation")}

    async def fake_memories(uid):  # noqa: ANN001
        return raw["memories"]

    monkeypatch.setattr(ex, "fetch_profile", fake_profile)
    monkeypatch.setattr(ex, "fetch_resume_versions", fake_resumes)
    monkeypatch.setattr(ex, "fetch_documents", fake_docs)
    monkeypatch.setattr(ex, "fetch_jds", fake_jds)
    monkeypatch.setattr(ex, "fetch_interview_sessions", fake_sessions)
    monkeypatch.setattr(ex, "fetch_interview_turns", fake_turns)
    monkeypatch.setattr(ex, "fetch_interview_evaluations", fake_evaluations)
    monkeypatch.setattr(ex, "fetch_memories", fake_memories)

    gathered = await ex.gather_raw("u1")
    # The gathered raw covers the sections the ai-service reads for itself; the
    # backend's two are not among them (it cannot read them), so they arrive
    # through `extra` instead.
    assert gathered.keys() == set(ex.AI_SECTIONS)
    rebuilt = ex.build_bundle("u1", gathered)
    assert rebuilt["manifest"]["counts"]["interviews"] == 1


async def test_gather_raw_decodes_the_json_columns_and_carries_the_report(monkeypatch):
    """A jsonb column is an object in the bundle, and the report travels.

    This is the defect the unit fixtures could not see: asyncpg hands a
    ``jsonb`` column back as its text, and a fixture that writes the shape
    the bundle *should* have hides that. The restore writes the bundle back
    through a map, so a parsed posting, a session's config, an answer's
    evaluation and the interview report all arrived as strings and were
    dropped. The bundle is a document: the columns the schema calls ``jsonb``
    are objects in it.

    So this test starts at the database boundary -- the fake returns the
    rows the way asyncpg would, strings and all -- rather than at the
    fetchers, which are where the decoding lives.
    """
    from app.core import db as core_db
    from app.db import domain

    async def fake_profile(uid):  # noqa: ANN001
        return {"id": "u1", "headline": "BE",
                "links": '{"github": "https://github.com/ada"}',
                "target_roles": '["Backend Engineer"]'}

    async def fake_fetch(query, *args):  # noqa: ANN001
        if "resume_versions" in query:
            return [{"id": "r1", "resume_title": "Main", "plaintext": "Exp",
                     "structured": '{"skills": ["java"]}', "diff": None,
                     "score": '{"total": 9}'}]
        if "FROM documents" in query:
            return [{"id": "d1", "title": "Notes", "text_excerpt": "x",
                     "meta": '{"kind": "note"}'}]
        if "job_jds" in query:
            return [{"id": "j1", "raw_text": "JD", "parsed": '{"title": "BE"}'}]
        if "FROM interview_sessions" in query:
            return [{"id": "s1", "status": "completed",
                     "config": '{"style": "deep"}'}]
        if "FROM interview_turns" in query:
            return [{"id": "t1", "session_id": "s1", "seq": 1, "content": "q",
                     "question_meta": '{"topic": "db"}',
                     "evaluation": '{"score": 3}'}]
        if "FROM interview_evaluations" in query:
            return [{"session_id": "s1",
                     "dims": '{"technical_accuracy": 0.8}',
                     "summary": '{"well": ["indexes"]}',
                     "trajectory": '["q1", "q2"]'}]
        if "user_memories" in query:
            return []
        raise AssertionError(f"unexpected query: {query}")

    async def fake_list_memories(uid, limit=1000):  # noqa: ANN001
        return []

    monkeypatch.setattr(domain, "get_profile", fake_profile)
    monkeypatch.setattr(core_db, "fetch", fake_fetch)
    monkeypatch.setattr(ex, "fetch_memories", fake_list_memories)

    raw = await ex.gather_raw("u1")

    assert raw["profile"]["links"] == {"github": "https://github.com/ada"}
    assert raw["profile"]["target_roles"] == ["Backend Engineer"]
    assert raw["resumes"][0]["structured"] == {"skills": ["java"]}
    assert raw["resumes"][0]["diff"] is None
    assert raw["knowledge"][0]["meta"] == {"kind": "note"}
    assert raw["job_descriptions"][0]["parsed"] == {"title": "BE"}
    session = raw["interviews"][0]
    assert session["config"] == {"style": "deep"}
    assert session["turns"][0]["question_meta"] == {"topic": "db"}
    assert session["turns"][0]["evaluation"] == {"score": 3}
    # The session's report, which the restore reads off the session -- and
    # which the export did not carry at all before: a restored interview had
    # a transcript and no verdict.
    assert session["evaluation"]["dims"] == {"technical_accuracy": 0.8}
    assert session["evaluation"]["summary"] == {"well": ["indexes"]}
    assert session["evaluation"]["trajectory"] == ["q1", "q2"]


async def test_a_session_without_a_report_carries_no_evaluation(monkeypatch):
    """An interview that was never graded has no report -- not an empty one.

    The restore writes an evaluation only when the bundle carries one, and
    the report is the one table that is written after the session ends. An
    empty object would make "no report yet" and "a report of nothing" the
    same row.
    """
    from app.core import db as core_db
    from app.db import domain

    async def no_profile(uid):  # noqa: ANN001
        return None

    async def fake_fetch(query, *args):  # noqa: ANN001
        if "FROM interview_sessions" in query:
            return [{"id": "s1", "status": "active", "config": "{}"}]
        if "FROM interview_turns" in query or "FROM interview_evaluations" in query:
            return []
        if "job_jds" in query or "FROM documents" in query or "resume_versions" in query:
            return []
        if "user_memories" in query:
            return []
        raise AssertionError(f"unexpected query: {query}")

    async def empty_memories(uid, limit=1000):  # noqa: ANN001
        return []

    monkeypatch.setattr(domain, "get_profile", no_profile)
    monkeypatch.setattr(core_db, "fetch", fake_fetch)
    monkeypatch.setattr(ex, "fetch_memories", empty_memories)

    raw = await ex.gather_raw("u1")
    assert "evaluation" not in raw["interviews"][0]
