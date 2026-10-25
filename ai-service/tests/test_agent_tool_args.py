"""The agent's tool handlers must degrade on a malformed argument, not error.

The model is asked for JSON that matches each tool's schema, and it mostly
complies -- but `limit: "5"`, `kinds: "resume"`, `top_k: null` all happen. Every
one of those used to raise inside the handler, which the orchestrator converts
into a tool error the model then has to retry: a wasted round trip and a worse
answer, when the right response is to use a sane default. These tests pin the
normalisation the handlers now do before touching the database.
"""

import pytest

from app.agents import tools


def test_clamp_limit_degrades_a_string_float_or_none_to_the_default():
    assert tools._clamp_limit("5", 10) == 5        # numeric string is usable
    assert tools._clamp_limit(7.9, 10) == 7        # float truncates, no raise
    assert tools._clamp_limit(None, 10) == 10
    assert tools._clamp_limit("lots", 10) == 10
    assert tools._clamp_limit([], 10) == 10


def test_clamp_limit_bounds_both_ends():
    assert tools._clamp_limit(0, 10) == 1          # a zero page is not a page
    assert tools._clamp_limit(-5, 10) == 1
    assert tools._clamp_limit(10_000, 10) == 25    # a page is not a dump


def test_clamp_limit_honours_a_larger_cap_where_a_tool_allows_one():
    assert tools._clamp_limit(40, 15, 50) == 40
    assert tools._clamp_limit(999, 15, 50) == 50


def test_clean_kinds_wraps_a_lone_string():
    # A bare string is the model reading "array of strings" as "string"; it is a
    # usable filter, not an error.
    assert tools._clean_kinds("resume") == ["resume"]
    assert tools._clean_kinds(" resume ") == ["resume"]


def test_clean_kinds_drops_non_string_entries_and_blanks():
    assert tools._clean_kinds(["resume", "", None, 3, "project"]) == ["resume", "project"]


def test_clean_kinds_means_no_filter_rather_than_match_nothing():
    # An empty filter bound to `= ANY('{}')` matches nothing at all, which reads as
    # "the corpus has no evidence" instead of "no filter was asked for".
    assert tools._clean_kinds([]) is None
    assert tools._clean_kinds(None) is None
    assert tools._clean_kinds(["", "  "]) is None
    assert tools._clean_kinds(42) is None
    assert tools._clean_kinds({"a": 1}) is None


@pytest.mark.asyncio
async def test_search_knowledge_base_normalises_kinds_before_retrieve(monkeypatch):
    seen: dict = {}

    async def fake_retrieve(query, *, user_id, top_k, kinds):
        seen["kinds"] = kinds
        seen["top_k"] = top_k
        return {"evidence": [], "context_block": ""}

    monkeypatch.setattr("app.rag.pipeline.retrieve", fake_retrieve)
    # The model's literal payload: a string filter and a string top_k.
    await tools.search_knowledge_base("u1", query="kafka", top_k="4",
                                      kinds="resume")
    assert seen["kinds"] == ["resume"]
    assert seen["top_k"] == 4


@pytest.mark.asyncio
async def test_search_knowledge_base_with_a_useless_kinds_drops_the_filter(monkeypatch):
    seen: dict = {}

    async def fake_retrieve(query, *, user_id, top_k, kinds):
        seen["kinds"] = kinds
        return {"evidence": [], "context_block": ""}

    monkeypatch.setattr("app.rag.pipeline.retrieve", fake_retrieve)
    await tools.search_knowledge_base("u1", query="kafka", kinds=[None, 7])
    assert seen["kinds"] is None


@pytest.mark.asyncio
async def test_search_resume_clamps_a_bad_top_k(monkeypatch):
    seen: dict = {}

    async def fake_retrieve(query, *, user_id, top_k, kinds):
        seen["top_k"] = top_k
        return {"evidence": []}

    monkeypatch.setattr("app.rag.pipeline.retrieve", fake_retrieve)
    await tools.search_resume("u1", query="kafka", top_k=None)
    assert seen["top_k"] == 6  # the tool's own default, not a crash in rerank


# ---------------- schema validation (before the handler runs) ----------------

_GET_JOB_SCHEMA = {"type": "object", "properties": {"job_id": {"type": "string"}},
                   "required": ["job_id"], "additionalProperties": False}


def test_validate_tool_args_accepts_a_well_formed_call():
    assert tools.validate_tool_args("get_job", _GET_JOB_SCHEMA, {"job_id": "j1"}) is None


def test_validate_tool_args_names_the_missing_required_property():
    # Python's own TypeError says "missing 1 required positional argument" and names
    # no property the model can add back; this one does.
    assert tools.validate_tool_args("get_job", _GET_JOB_SCHEMA, {}) == \
        "missing required property 'job_id'"


def test_validate_tool_args_names_the_unknown_property_and_the_allowed_set():
    problem = tools.validate_tool_args(
        "get_job", _GET_JOB_SCHEMA, {"job_id": "j1", "verbose": True})
    assert problem == "unexpected property 'verbose' (allowed: job_id)"


def test_validate_tool_args_rejects_a_container_of_the_wrong_shape():
    schema = {"type": "object", "properties": {
        "skills": {"type": "array", "items": {"type": "string"}},
        "offers": {"type": "array", "items": {"type": "object"}},
        "equity": {"type": "object"}},
        "additionalProperties": False}
    assert tools.validate_tool_args("search_jobs", schema, {"skills": "go"}) == \
        "property 'skills' must be an array"
    assert tools.validate_tool_args("search_jobs", schema, {"skills": ["go"]}) is None
    # an array-of-objects given a bare string is an array violation, not an object one
    assert tools.validate_tool_args("compare_offers", schema, {"offers": "one"}) == \
        "property 'offers' must be an array"
    assert tools.validate_tool_args("compare_offers", schema,
                                    {"equity": "100 shares"}) == \
        "property 'equity' must be an object"
    assert tools.validate_tool_args("compare_offers", schema,
                                    {"equity": {"shares": 100}}) is None


def test_validate_tool_args_leaves_scalar_coercion_to_the_handler():
    # `limit: "5"` and `top_k: null` are values the handlers normalise; rejecting
    # them here would turn a usable call into an error.
    schema = {"type": "object", "properties": {
        "query": {"type": "string"}, "limit": {"type": "integer", "default": 10}},
        "additionalProperties": False}
    assert tools.validate_tool_args("search_jobs", schema,
                                    {"query": "x", "limit": "5"}) is None
    assert tools.validate_tool_args("search_jobs", schema,
                                    {"query": "x", "limit": None}) is None
    assert tools.validate_tool_args("search_jobs", schema, {"query": "x"}) is None


def test_validate_tool_args_on_every_registered_tool_schema_is_self_consistent():
    # A schema whose `required` names a property it does not define would make the
    # validator reject a call the handler accepts -- so check every shipped schema.
    for tool in tools.ALL_TOOLS:
        schema = tool.parameters
        props = set(schema.get("properties") or {})
        assert set(schema.get("required") or []) <= props, tool.name
        assert isinstance(schema.get("type"), str) and schema["type"] == "object", tool.name


@pytest.mark.asyncio
async def test_compare_offers_handler_actually_runs(monkeypatch):
    """The handler, not just the engine.

    `tools.compare_offers` called `benchmark(...)` without importing it, so every
    "which offer leads?" call raised NameError and came back as a tool error -- the
    engine tests all passed because none of them went through the tool. Importing
    the module is not the same as calling it.
    """
    async def fake_samples():
        return [{"salary_min": 300000, "salary_max": 500000, "location": "Shanghai",
                 "seniority": "senior", "skills": ["Java"]}]

    monkeypatch.setattr(tools, "_job_samples", fake_samples)

    out = await tools.compare_offers(
        "u1", role="Backend Engineer",
        offers=[{"label": "A", "base": 400000},
                {"label": "B", "base": 520000}])
    assert "error" not in out, f"the handler raised: {out.get('error')}"
    assert out.get("ranking") or out.get("offers") or out.get("ranked"), \
        f"no ranking in the tool result: {sorted(out)}"
