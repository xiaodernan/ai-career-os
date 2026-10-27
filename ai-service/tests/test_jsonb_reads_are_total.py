"""jsonb reads must be total: the column is text, and it may not be an object.

No JSON codec is registered on the pool, so asyncpg hands jsonb back as a *string*;
and the column can hold valid JSON that is not an object -- a list, a number, a
truncated document. Six call sites parsed the resume structure with
`if isinstance(x, str): json.loads(x)` and then called `.get(...)` on the result, so
a non-object column raised AttributeError inside the tool. `calculate_match` is the
one that mattered: instead of answering "no parsed resume", it crashed, and the
orchestrator reported an error the model could not act on.
"""

import json

import pytest

from app.agents import tools

JOB = {"id": "j1", "title": "Backend Engineer", "description": "Kafka and Spring"}


def _patch_resume(monkeypatch, structured):
    async def get_job(job_id):
        return dict(JOB)

    async def get_resume(user_id):
        return {"id": "rv1", "structured": structured, "plaintext": "text"}

    monkeypatch.setattr(tools.domain, "get_job", get_job)
    monkeypatch.setattr(tools.domain, "get_current_resume_version", get_resume)


def test_json_dict_accepts_the_shapes_a_column_can_hold():
    assert tools._json_dict({"a": 1}) == {"a": 1}
    assert tools._json_dict('{"a": 1}') == {"a": 1}      # text, no codec on the pool
    assert tools._json_dict(None) == {}
    assert tools._json_dict("[1, 2]") == {}              # JSON, but not an object
    assert tools._json_dict(7) == {}
    assert tools._json_dict("{not json") == {}           # malformed degrades


@pytest.mark.asyncio
async def test_calculate_match_answers_no_resume_instead_of_crashing(monkeypatch):
    _patch_resume(monkeypatch, "[1, 2]")  # a list where a structure belongs
    out = await tools.calculate_match("u1", job_id="j1")
    assert out == {"error": "no parsed resume; ask the user to upload one"}


@pytest.mark.asyncio
async def test_calculate_match_answers_no_resume_on_malformed_text(monkeypatch):
    _patch_resume(monkeypatch, "{not json")
    out = await tools.calculate_match("u1", job_id="j1")
    assert out == {"error": "no parsed resume; ask the user to upload one"}


@pytest.mark.asyncio
async def test_resume_payload_treats_a_non_object_structure_as_absent(monkeypatch):
    async def get_resume(user_id):
        return {"id": "rv1", "structured": json.dumps([1, 2]), "plaintext": "text"}

    monkeypatch.setattr(tools.domain, "get_current_resume_version", get_resume)
    structured, text = await tools._resume_payload("u1", None)
    assert structured is None, "the growth tools must report 'no parsed resume'"
    assert text == "text"


@pytest.mark.asyncio
async def test_get_user_profile_survives_a_malformed_structure(monkeypatch):
    async def get_profile(user_id):
        return {"headline": "x"}

    async def get_user(user_id):
        return {"id": "u1", "email": "a@b.c"}

    async def get_memories(user_id, limit=15):
        return []

    async def get_resume(user_id):
        return {"id": "rv1", "structured": "{not json"}

    monkeypatch.setattr(tools.domain, "get_profile", get_profile)
    monkeypatch.setattr(tools.domain, "get_user", get_user)
    monkeypatch.setattr(tools.domain, "get_memories", get_memories)
    monkeypatch.setattr(tools.domain, "get_current_resume_version", get_resume)

    out = await tools.get_user_profile("u1")
    assert out["resume_headline"] is None and out["skills"] == []
    assert out["profile"] == {"headline": "x"}      # the profile itself still answers


@pytest.mark.asyncio
async def test_get_user_profile_reads_a_well_formed_structure(monkeypatch):
    async def get_profile(user_id):
        return {}

    async def get_user(user_id):
        return {}

    async def get_memories(user_id, limit=15):
        return []

    async def get_resume(user_id):
        return {"id": "rv1", "structured": json.dumps(
            {"profile": {"headline": "Backend engineer"},
             "skills": [{"name": "Kafka"}, {"name": "Java"}, "not a dict"]})}

    monkeypatch.setattr(tools.domain, "get_profile", get_profile)
    monkeypatch.setattr(tools.domain, "get_user", get_user)
    monkeypatch.setattr(tools.domain, "get_memories", get_memories)
    monkeypatch.setattr(tools.domain, "get_current_resume_version", get_resume)

    out = await tools.get_user_profile("u1")
    assert out["resume_headline"] == "Backend engineer"
    assert out["skills"] == ["Kafka", "Java"]       # the non-dict entry is skipped
