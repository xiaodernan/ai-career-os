"""Retirement is terminal: an ingest that finishes after the reader deleted its
source must not put the document back in front of retrieval.

The backend writes `documents.status = 'retired'` when a resume, source or note is
deleted; all three hybrid retrieval channels admit a chunk only while its document
reads 'ready'. These tests pin the predicates and the pipeline's refusals without a
database, through a fake pool.
"""

import asyncio

import app.core.db as db
from app.db import documents
from app.ingestion import pipeline


class Row(dict):
    """Stand-in for asyncpg.Record."""
    __getattr__ = dict.get


class _Conn:
    def __init__(self, row, capture, tags):
        self.row = row
        self.capture = capture
        self.tags = tags

    async def fetchrow(self, query, *args):
        self.capture.append(("fetchrow", query, args))
        return Row(self.row) if self.row else None

    async def execute(self, query, *args):
        self.capture.append(("execute", query, args))
        return self.tags.get("execute", "UPDATE 1")

    async def executemany(self, query, rows):
        self.capture.append(("executemany", query, rows))


class FakePool:
    def __init__(self, row=None, tags=None):
        self.row = row
        self.tags = tags or {}
        self.capture: list = []

    def acquire(self):
        outer = self

        class _Ctx:
            async def __aenter__(self):
                return _Conn(outer.row, outer.capture, outer.tags)

            async def __aexit__(self, *exc):
                return False

        return _Ctx()


def _install(monkeypatch, pool):
    monkeypatch.setattr(db, "get_pool", lambda: pool)


def _chunk():
    return {"ordinal": 0, "text": "hello", "token_count": 1,
            "section_path": "resume > summary", "kind": "paragraph",
            "meta": {"skills": []}, "embedding": [0.1, 0.2]}


# --------------------------- the repository's writes ------------------------


def test_a_late_ready_write_keeps_the_retirement(monkeypatch):
    pool = FakePool(tags={"execute": "UPDATE 0"})
    _install(monkeypatch, pool)

    applied = asyncio.run(
        documents.set_status("d1", "ready", text_excerpt="the deleted text"))

    # 'ready' is the gate; a write that lands after the delete must answer that
    # it did not move the row, so the pipeline cannot claim the ingest finished.
    assert applied is False
    _kind, sql, args = pool.capture[-1]
    assert "status <> 'retired'" in sql
    assert "text_excerpt=$4" in sql
    assert args == ("d1", "ready", None, "the deleted text")


def test_the_indexing_write_carries_the_same_guard(monkeypatch):
    pool = FakePool(tags={"execute": "UPDATE 0"})
    _install(monkeypatch, pool)

    applied = asyncio.run(documents.set_status("d1", "indexing"))

    assert applied is False
    _kind, sql, args = pool.capture[-1]
    assert "status <> 'retired'" in sql
    assert "text_excerpt" not in sql, "the excerpt-free write has its own statement"
    assert args == ("d1", "indexing", None)


def test_a_live_document_still_moves(monkeypatch):
    pool = FakePool(tags={"execute": "UPDATE 1"})
    _install(monkeypatch, pool)

    assert asyncio.run(documents.set_status("d1", "ready")) is True


def test_a_retired_document_gets_no_new_chunks(monkeypatch):
    pool = FakePool(row={"status": "retired"})
    _install(monkeypatch, pool)

    n = asyncio.run(documents.replace_chunks("d1", "u1", [_chunk()]))

    # The chunks it died with stay as the audit record, and a late ingest may
    # neither delete them nor add quotable new ones.
    assert n == 0
    assert [entry[0] for entry in pool.capture] == ["fetchrow"]


def test_a_missing_document_gets_no_chunks(monkeypatch):
    pool = FakePool(row=None)
    _install(monkeypatch, pool)

    n = asyncio.run(documents.replace_chunks("d1", "u1", [_chunk()]))

    assert n == 0
    assert [entry[0] for entry in pool.capture] == ["fetchrow"]


def test_a_live_document_still_has_its_chunks_replaced(monkeypatch):
    pool = FakePool(row={"status": "ready"})
    _install(monkeypatch, pool)

    n = asyncio.run(documents.replace_chunks("d1", "u1", [_chunk()]))

    assert n == 1
    assert [entry[0] for entry in pool.capture] == ["fetchrow", "execute", "executemany"]
    _kind, delete_sql, delete_args = pool.capture[1]
    assert delete_sql.startswith("DELETE FROM document_chunks")
    assert delete_args == ("d1",)
    _kind, insert_sql, rows = pool.capture[2]
    assert "INSERT INTO document_chunks" in insert_sql
    assert rows == [("d1", "u1", 0, "hello", 1, "resume > summary", "paragraph",
                     '{"skills": []}', "[0.1000000,0.2000000]")]


# ------------------------------ the pipeline --------------------------------


class _Embedder:
    async def embed(self, texts):
        return [[0.1, 0.2] for _ in texts]


def _doc(status="pending", **overrides):
    doc = {"id": "d1", "user_id": "u1", "source_id": None, "file_key": None,
           "media_type": "text/plain", "title": "note", "status": status,
           "text_excerpt": "hello world", "meta": {"inline_text": "hello world"}}
    doc.update(overrides)
    return doc


def _capture_finish(monkeypatch):
    finishes = []
    monkeypatch.setattr(pipeline.taskbus, "finish",
                        lambda *args, **kw: finishes.append((args, kw)))
    return finishes


def test_a_pipeline_that_starts_on_a_retired_document_writes_nothing(monkeypatch):
    async def get_document(doc_id):
        return _doc("retired")

    def write(*args, **kw):
        raise AssertionError("a retired document must not be written")

    monkeypatch.setattr(pipeline.docs_repo, "get_document", get_document)
    monkeypatch.setattr(pipeline.docs_repo, "set_status", write)
    monkeypatch.setattr(pipeline.docs_repo, "replace_chunks", write)
    finishes = _capture_finish(monkeypatch)

    result = asyncio.run(pipeline.ingest_document("d1", "t1"))

    assert result == {"error": "retired"}
    assert finishes == [(("t1", False), {"error": "document retired"})]


def test_a_pipeline_that_loses_the_row_mid_run_does_not_mark_it_ready(monkeypatch):
    statuses = []

    async def get_document(doc_id):
        return _doc("pending")

    async def set_status(doc_id, status, error=None, text_excerpt=None):
        statuses.append(status)
        return status != "ready"

    async def replace_chunks(doc_id, user_id, chunks):
        return len(chunks)

    async def mark_source_ready(source_id, doc_id):
        raise AssertionError("a retired document has no source left to mark ready")

    monkeypatch.setattr(pipeline.docs_repo, "get_document", get_document)
    monkeypatch.setattr(pipeline.docs_repo, "set_status", set_status)
    monkeypatch.setattr(pipeline.docs_repo, "replace_chunks", replace_chunks)
    monkeypatch.setattr(pipeline.docs_repo, "mark_source_ready", mark_source_ready)
    from app.providers import registry
    monkeypatch.setattr(registry, "get_embeddings", lambda s: _Embedder())
    finishes = _capture_finish(monkeypatch)

    result = asyncio.run(pipeline.ingest_document("d1", "t1"))

    # The embedding work was already in flight; what must not happen is the
    # success report -- the row lost the race at the 'ready' write, and the
    # task says so instead of publishing an indexed document that is not there.
    assert result == {"error": "retired"}
    assert statuses == ["indexing", "ready"]
    assert finishes == [(("t1", False), {"error": "document retired"})]


def test_a_live_pipeline_still_marks_the_document_and_source_ready(monkeypatch):
    events = []

    async def get_document(doc_id):
        return _doc("pending", source_id="s1")

    async def set_status(doc_id, status, error=None, text_excerpt=None):
        events.append(status)
        return True

    async def replace_chunks(doc_id, user_id, chunks):
        return len(chunks)

    async def mark_source_ready(source_id, doc_id):
        events.append(("source", source_id, doc_id))

    monkeypatch.setattr(pipeline.docs_repo, "get_document", get_document)
    monkeypatch.setattr(pipeline.docs_repo, "set_status", set_status)
    monkeypatch.setattr(pipeline.docs_repo, "replace_chunks", replace_chunks)
    monkeypatch.setattr(pipeline.docs_repo, "mark_source_ready", mark_source_ready)
    from app.providers import registry
    monkeypatch.setattr(registry, "get_embeddings", lambda s: _Embedder())
    finishes = _capture_finish(monkeypatch)

    result = asyncio.run(pipeline.ingest_document("d1", "t1"))

    assert result["document_id"] == "d1" and result["chunks"] >= 1
    assert events == ["indexing", "ready", ("source", "s1", "d1")]
    assert finishes[0][0][:2] == ("t1", True)
