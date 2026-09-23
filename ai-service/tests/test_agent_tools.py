"""Agent tool handler tests: DB/LLM are stubbed so the pure glue is verifiable.

Guards two crash families that only bite on the *happy* path (a user who already
has a resume):
  * calculate_match used to tuple-unpack the dict returned by
    domain.get_*_resume_version, raising ``ValueError: too many values to unpack``
    whenever a resume existed.
  * get_user_profile read ``skills`` with ``.get("skills", [])``, which returns
    ``None`` for a *present-null* jsonb key (the backend owns that write) and then
    crashed on ``for s in None``.
"""

import app.db.domain as domain_mod
import app.features.jd_analyze as jd_mod
import app.features.match as match_mod
from app.agents.tools import calculate_match, get_user_profile

# A realistic resume_versions row: get_resume_version/get_current_resume_version do
# ``SELECT rv.*`` so the dict has many columns — exactly what broke the tuple unpack.
RV = {"id": "rv-1", "resume_id": "r-1", "version_no": 3, "score": 72,
      "plaintext": "LEE ...", "structured": {"skills": [{"name": "Java"}]}}


def _patch_resume(monkeypatch, rv, *, by_id=None):
    async def fake_current(user_id):
        return rv
    async def fake_by_id(rv_id, user_id):
        return by_id if by_id is not None else rv
    monkeypatch.setattr(domain_mod, "get_current_resume_version", fake_current)
    monkeypatch.setattr(domain_mod, "get_resume_version", fake_by_id)


def _patch_match(monkeypatch, captured):
    async def fake_get_job(job_id):
        return {"id": job_id, "title": "Backend Engineer", "company_name": "Acme",
                "description": "we need java"}
    async def fake_analyze(raw, **kw):
        return {"title": "Backend Engineer"}
    async def fake_compute(structured, jd, **kw):
        captured["structured"] = structured
        return {"overall": 0.5, "matchedSkills": ["Java"]}
    async def fake_persist(user_id, job_id, rv_id, result):
        captured["persist"] = (user_id, job_id, rv_id)
        return "m-1"
    monkeypatch.setattr(domain_mod, "get_job", fake_get_job)
    monkeypatch.setattr(jd_mod, "analyze_jd", fake_analyze)
    monkeypatch.setattr(match_mod, "compute_match", fake_compute)
    monkeypatch.setattr(match_mod, "persist_match", fake_persist)


# ---------------- calculate_match ----------------


async def test_calculate_match_survives_multi_column_resume_row(monkeypatch):
    cap = {}
    _patch_resume(monkeypatch, RV)
    _patch_match(monkeypatch, cap)
    out = await calculate_match("u1", job_id="j1")
    assert out["match"] == {"overall": 0.5, "matchedSkills": ["Java"]}
    assert out["job"] == {"id": "j1", "title": "Backend Engineer", "company": "Acme"}
    # persisted against the SAME version whose structured we matched
    assert cap["persist"] == ("u1", "j1", "rv-1")
    assert cap["structured"] == {"skills": [{"name": "Java"}]}


async def test_calculate_match_uses_explicit_resume_version_id(monkeypatch):
    cap = {}
    explicit = {**RV, "id": "rv-9", "structured": {"skills": [{"name": "Go"}]}}
    _patch_resume(monkeypatch, RV, by_id=explicit)
    _patch_match(monkeypatch, cap)
    await calculate_match("u1", job_id="j1", resume_version_id="rv-9")
    assert cap["persist"] == ("u1", "j1", "rv-9")
    assert cap["structured"] == {"skills": [{"name": "Go"}]}


async def test_calculate_match_parses_stringified_structured(monkeypatch):
    cap = {}
    _patch_resume(monkeypatch, {**RV, "structured": '{"skills": [{"name": "Kafka"}]}'})
    _patch_match(monkeypatch, cap)
    await calculate_match("u1", job_id="j1")
    assert cap["structured"] == {"skills": [{"name": "Kafka"}]}


async def test_calculate_match_errors_without_resume(monkeypatch):
    cap = {}
    _patch_resume(monkeypatch, None)
    _patch_match(monkeypatch, cap)
    out = await calculate_match("u1", job_id="j1")
    assert "error" in out and "persist" not in cap


async def test_calculate_match_errors_when_job_missing(monkeypatch):
    async def no_job(job_id):
        return None
    monkeypatch.setattr(domain_mod, "get_job", no_job)
    out = await calculate_match("u1", job_id="j1")
    assert out == {"error": "job not found"}


# ---------------- get_user_profile ----------------


def _patch_profile(monkeypatch, rv):
    async def fake_profile(user_id):
        return None
    async def fake_user(user_id):
        return {"id": user_id}
    async def fake_memories(user_id, **kw):
        return []
    async def fake_current(user_id):
        return rv
    monkeypatch.setattr(domain_mod, "get_profile", fake_profile)
    monkeypatch.setattr(domain_mod, "get_user", fake_user)
    monkeypatch.setattr(domain_mod, "get_memories", fake_memories)
    monkeypatch.setattr(domain_mod, "get_current_resume_version", fake_current)


async def test_get_user_profile_survives_present_null_skills(monkeypatch):
    _patch_profile(monkeypatch, {"structured": {"profile": None, "skills": None}})
    out = await get_user_profile("u1")
    assert out["skills"] == []
    assert out["resume_headline"] is None


async def test_get_user_profile_ignores_non_dict_skill_entries(monkeypatch):
    _patch_profile(monkeypatch, {"structured": {
        "skills": [{"name": "Java"}, "Go", 7, None, {"no_name": 1}]}})
    out = await get_user_profile("u1")
    assert out["skills"] == ["Java", None]  # dict without name -> None, junk dropped


async def test_get_user_profile_parses_stringified_structured(monkeypatch):
    _patch_profile(monkeypatch, {"structured": '{"skills": [{"name": "Kafka"}]}'})
    out = await get_user_profile("u1")
    assert out["skills"] == ["Kafka"]


async def test_get_user_profile_tolerates_no_resume(monkeypatch):
    _patch_profile(monkeypatch, None)
    out = await get_user_profile("u1")
    assert out["skills"] == [] and out["resume_headline"] is None
