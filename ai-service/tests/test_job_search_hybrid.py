"""Hybrid job search: keyword/tsv fused with vector similarity.

Covers the fusion and the degradation path. The DB and the embedder are stubbed —
these are about *which* queries run and how the two ranked lists merge, not about
Postgres. `_search_params` itself is pinned separately in test_like_literal.py.
"""

from app.agents import tools as tools_mod
from app.agents.tools import _fuse_rrf, search_jobs


def _row(job_id: str, title: str = "Role") -> dict:
    return {"id": job_id, "title": title, "company": "Acme", "location": "Shanghai",
            "remote_type": "hybrid", "salary_min": 300000, "salary_max": 450000,
            "skills": ["Java"]}


class _FakeEmbedder:
    async def embed(self, texts):
        return [[0.0] * 4 for _ in texts]


# ------------------------------- fusion -------------------------------

def test_a_job_both_retrievers_found_outranks_one_a_single_list_found():
    # "both" sits mid-list in each; "kw-only" is rank 0 of keyword only. Agreement
    # must beat a single retriever's top hit, which is the reason to run two at all.
    keyword = [_row("kw-only"), _row("a"), _row("b"), _row("both")]
    semantic = [_row("x"), _row("y"), _row("z"), _row("both")]

    out = _fuse_rrf(keyword, semantic, 10)

    assert str(out[0]["id"]) == "both"


def test_with_no_semantic_hits_the_keyword_order_is_untouched():
    # This is the no-embeddings case: behaviour must be exactly what it was before
    # semantic search existed, or a provider outage would silently reorder results.
    keyword = [_row("1"), _row("2"), _row("3")]

    out = _fuse_rrf(keyword, [], 10)

    assert [str(r["id"]) for r in out] == ["1", "2", "3"]


def test_a_job_found_by_both_retrievers_appears_once():
    out = _fuse_rrf([_row("dup")], [_row("dup")], 10)

    assert len(out) == 1
    assert str(out[0]["id"]) == "dup"


def test_the_merged_list_is_cut_to_the_limit():
    out = _fuse_rrf([_row(str(i)) for i in range(10)], [], 3)

    assert len(out) == 3


def test_fusion_keeps_the_row_payload_it_was_given():
    # The fused rows are handed straight to the tool response, so a row must survive
    # the merge intact rather than being rebuilt from ids.
    keyword = [_row("k", title="Backend Engineer")]

    out = _fuse_rrf(keyword, [], 10)

    assert out[0]["title"] == "Backend Engineer"
    assert out[0]["salary_min"] == 300000


# ---------------------------- degradation ----------------------------

async def test_search_falls_back_to_keyword_when_the_embedder_is_unavailable(monkeypatch):
    sqls: list[str] = []

    async def fake_fetch(sql, *args):
        sqls.append(sql)
        return [_row("k1")]

    def boom(*_a, **_k):
        raise RuntimeError("no embedding provider configured")

    monkeypatch.setattr(tools_mod.db, "fetch", fake_fetch)
    monkeypatch.setattr("app.providers.registry.get_embeddings", boom)

    result = await search_jobs("u", query="backend")

    assert [j["id"] for j in result["jobs"]] == ["k1"]
    # Only the keyword query ran — the semantic pass must not raise the tool call.
    assert len(sqls) == 1
    assert "ts_rank" in sqls[0]


async def test_a_blank_query_skips_the_semantic_pass(monkeypatch):
    sqls: list[str] = []

    async def fake_fetch(sql, *args):
        sqls.append(sql)
        return []

    monkeypatch.setattr(tools_mod.db, "fetch", fake_fetch)
    monkeypatch.setattr("app.providers.registry.get_embeddings", lambda _s: _FakeEmbedder())

    await search_jobs("u", query="   ", location="Shanghai")

    # Browsing with only filters is not a semantic query; embedding blank text would
    # return whatever the model thinks "nothing" is nearest to.
    assert len(sqls) == 1
    assert all("<=>" not in s for s in sqls)


# --------------------------- both passes ---------------------------

async def test_both_retrievers_run_and_their_results_are_merged(monkeypatch):
    sqls: list[str] = []

    async def fake_fetch(sql, *args):
        sqls.append(sql)
        return [_row("kw")] if "ts_rank" in sql else [_row("vec")]

    monkeypatch.setattr(tools_mod.db, "fetch", fake_fetch)
    monkeypatch.setattr("app.providers.registry.get_embeddings", lambda _s: _FakeEmbedder())

    result = await search_jobs("u", query="payments platform")

    assert {j["id"] for j in result["jobs"]} == {"kw", "vec"}
    assert len(sqls) == 2
    assert any("<=>" in s for s in sqls), "the semantic pass must order by vector distance"


async def test_the_semantic_pass_reuses_the_users_filters(monkeypatch):
    # Without the filters the vector pass would return roles the user's constraints
    # exclude, and fusion could then rank them above ones that actually match.
    captured: dict = {}

    async def fake_fetch(sql, *args):
        if "<=>" in sql:
            captured["sql"] = sql
            captured["args"] = args
        return []

    monkeypatch.setattr(tools_mod.db, "fetch", fake_fetch)
    monkeypatch.setattr("app.providers.registry.get_embeddings", lambda _s: _FakeEmbedder())

    await search_jobs("u", query="x", location="Shanghai", remote="hybrid", min_salary=300000)

    sql = captured["sql"]
    assert "j.location ILIKE" in sql
    assert "j.remote_type = " in sql
    assert "j.salary_max >= " in sql
    assert "j.status = 'open'" in sql
    # A job with no vector cannot be ranked by distance; it belongs to keyword search.
    assert "j.embedding IS NOT NULL" in sql


async def test_the_query_vector_is_bound_not_interpolated(monkeypatch):
    captured: dict = {}

    async def fake_fetch(sql, *args):
        if "<=>" in sql:
            captured["sql"] = sql
            captured["args"] = args
        return []

    monkeypatch.setattr(tools_mod.db, "fetch", fake_fetch)
    monkeypatch.setattr("app.providers.registry.get_embeddings", lambda _s: _FakeEmbedder())

    await search_jobs("u", query="'; DROP TABLE jobs;--")

    # The query text never reaches the SQL — only the placeholder index does, and the
    # vector is handed to asyncpg as a bound literal.
    assert "DROP TABLE" not in captured["sql"]
    assert "jobs;--" not in captured["sql"]
    assert captured["args"][0].startswith("["), "the vector literal must be a bound arg"
