"""Regression: eval/rag/agent pure helpers degrade on hostile input.

These modules sit on request or evaluation paths where a malformed row (a peer
service payload, a stale cached entry, or a model that handed the wrong arg type)
must produce a safe empty/zero result rather than raise and abort the path.

Mirrors the discipline of ``test_forward_features_hostile_input.py`` and
``test_rag_strategy.py`` but targets the remaining pure helpers the hardening
sweep had not yet covered: the RAG fusion, the eval metrics, and the agent's
tool-call parameter builders.
"""

import pytest

from app.agents import tools as agent_tools
from app.eval import metrics
from app.rag import store


# --- app.rag.store.rrf_merge ------------------------------------------------

def test_rrf_merge_none_lists_is_empty():
    assert store.rrf_merge(None) == []


def test_rrf_merge_non_dict_rows_skipped():
    # A Record-shaped dict fuses; a None / non-id entry is skipped, not raised.
    good = {"id": "a", "text": "x"}
    bad = None
    out = store.rrf_merge([[good, bad], [{"id": "a"}]], k=60)
    assert len(out) == 1
    assert out[0]["id"] == "a"


def test_rrf_merge_mixed_dict_and_record():
    class Rec:
        id = "r"

    out = store.rrf_merge([[{"id": "d"}], [Rec()]], k=60)
    ids = {item["id"] for item in out}
    assert ids == {"d", "r"}


# --- app.eval.metrics -------------------------------------------------------

def test_recall_none_inputs():
    assert metrics.recall_at_k(None, None, 5) == 1.0
    assert metrics.precision_at_k(None, None, 5) == 0.0
    assert metrics.mrr(None, None) == 0.0
    assert metrics.ndcg(None, None, 5) == 0.0


def test_recall_relevant_none_is_vacuous():
    # Nothing to find => retrieval cannot be blamed, even with a real list.
    assert metrics.recall_at_k(["a", "b"], None, 5) == 1.0


def test_tokens_non_string_is_empty():
    assert metrics._tokens(None) == set()
    assert metrics._tokens(123) == set()
    assert metrics._tokens(["x"]) == set()


def test_faithfulness_non_string_answer():
    assert metrics.faithfulness(None, ["context about caching"]) == 0.0
    assert metrics.faithfulness(42, ["context about caching"]) == 0.0


def test_faithfulness_non_string_contexts():
    # A non-string context element must not crash; it contributes no tokens.
    assert metrics.faithfulness("This is a long enough sentence about caching.",
                                [None, 7, "caching is good"]) >= 0.0


def test_citation_correctness_non_string_answer():
    assert metrics.citation_correctness(None, ["ctx1", "ctx2"]) == 0.0


def test_lexical_context_relevance_non_string_contexts():
    assert metrics.lexical_context_relevance(
        "caching", [None, "caching penetration handling"]) >= 0.0


def test_answer_relevance_non_string_args():
    assert metrics.answer_relevance(None, "caching is good") == 0.0
    assert metrics.answer_relevance("caching", None) == 0.0


# --- app.agents.tools parameter builders ------------------------------------

def test_search_params_bad_limit_coerced():
    # A string / None / float limit must not raise and must stay clamped.
    where, args = agent_tools._search_params(query="go", limit="oops")
    assert args[-1] == 10  # default window, not a crash
    where, args = agent_tools._search_params(query="go", limit=None)
    assert args[-1] == 10
    where, args = agent_tools._search_params(query="go", limit=3.9)
    assert args[-1] == 3


def test_filter_fragments_skills_non_list_ignored():
    # A scalar/None `skills` must not trigger `for s in skills` nor a bad bind.
    out = agent_tools._filter_fragments(skills="not-a-list")
    assert all("skills &&" not in sql for sql, _ in out)


def test_filter_fragments_min_salary_non_numeric_ignored():
    out = agent_tools._filter_fragments(min_salary="lots")
    assert all("salary_max >=" not in sql for sql, _ in out)


def test_fuse_rrf_none_rows():
    assert agent_tools._fuse_rrf(None, None, 10) == []
    assert agent_tools._fuse_rrf([], None, 10) == []


def test_fuse_rrf_non_dict_rows_skipped():
    good = {"id": "j1", "title": "Go engineer"}
    out = agent_tools._fuse_rrf([good, None, 123], [], 10)
    assert len(out) == 1
    assert out[0]["id"] == "j1"
