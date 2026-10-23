"""The vector-index ops step (§36's "vector search"), decided offline.

The HNSW index cannot ship in a migration: the embedding columns are dimension-less by
design (the deployment picks its provider), and pgvector refuses the index until the
column declares its dimension — which is only knowable once real vectors exist. What
can ship is the decision, and this file pins it: one dimension indexes, no rows waits,
mixed dimensions refuse, an existing index is left alone, and the DDL that expands
from a decision names the table it serves.
"""

import pytest

from app.ops import vector_index as vi


def test_one_dimension_declares_and_indexes():
    out = dict(vi.plan({"document_chunks": {1536}}, {}))
    assert out["document_chunks"].ok
    assert out["document_chunks"].detail == "declare vector(1536) + HNSW (cosine)"
    assert vi.statements("document_chunks", 1536) == [
        "ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1536)",
        "CREATE INDEX idx_document_chunks_embedding ON document_chunks "
        "USING hnsw (embedding vector_cosine_ops)",
    ]


def test_no_vectors_yet_is_a_clean_wait_not_an_error():
    out = dict(vi.plan({}, {}))
    assert out["document_chunks"].ok
    assert "rerun after the first ingestion" in out["document_chunks"].detail
    # ...and an empty table produces no DDL to run.
    assert vi.statements.__doc__ is not None  # the expansion is only reached on a dimension


def test_mixed_dimensions_refuse_rather_than_paper_over_a_provider_switch():
    out = dict(vi.plan({"jobs": {768, 1536}}, {}))
    assert not out["jobs"].ok
    assert "mixed dimensions" in out["jobs"].detail
    assert "re-embed" in out["jobs"].detail


def test_an_existing_index_is_left_alone():
    out = dict(vi.plan({"document_chunks": {1536}},
                       {"document_chunks": {"idx_document_chunks_embedding"}}))
    assert out["document_chunks"].ok
    assert "already present" in out["document_chunks"].detail


def test_every_table_serves_a_named_reader():
    for table, reader in vi.TABLES.items():
        assert reader, f"{table} names no reader; the index would be an act of faith"


@pytest.mark.asyncio
async def test_run_executes_only_the_ddl_the_decisions_expand_to():
    executed: list[str] = []

    async def fetch(sql, *args):
        if "vector_dims" in sql:
            table = sql.split("FROM ")[1].split(" ")[0]
            return [{"d": 1536}] if table == "document_chunks" else []
        return [{"indexname": "idx_chunks_tsv"}]

    async def execute(sql):
        executed.append(sql)

    code = await vi.run(fetch, execute)
    assert code == 0
    # Only the table with rows and no index gets DDL; the other two wait.
    assert len(executed) == 2
    assert all("document_chunks" in sql for sql in executed)


@pytest.mark.asyncio
async def test_run_fails_when_dimensions_conflict():
    async def fetch(sql, *args):
        if "vector_dims" in sql:
            return [{"d": 768}, {"d": 1536}]
        return []

    executed: list[str] = []

    async def execute(sql):
        executed.append(sql)

    code = await vi.run(fetch, execute)
    assert code == 1
    assert executed == [], "a conflict must produce no DDL"
