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
