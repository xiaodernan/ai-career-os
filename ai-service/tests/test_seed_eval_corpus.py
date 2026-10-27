"""Tests for the eval-corpus seeding ops script.

The DB and provider halves of a pass are exercised by running the script against
the stack (the nightly's corpus step is exactly that run); these tests hold the
CLI contract and the polling halves: a corpus that never lands must exit 1 where
it happens, not travel to the eval runner and red there as ``0 of N scored``.
"""

from __future__ import annotations

import json

import pytest
from fastapi import HTTPException

from app.ops import seed_eval_corpus as mod


@pytest.fixture()
def corpus_file(tmp_path):
    def write(body) -> str:
        path = tmp_path / "corpus.json"
        path.write_text(json.dumps(body), encoding="utf-8")
        return str(path)
    return write


def _argv(corpus: str) -> list[str]:
    return ["--user-id", "00000000-0000-0000-0000-000000000000", "--corpus", corpus]


def test_missing_corpus_file_is_a_contract_error(capsys):
    rc = mod.main(_argv("no-such-corpus.json"))
    assert rc == 2
    assert "FileNotFoundError" in capsys.readouterr().err


def test_malformed_corpus_json_is_a_contract_error(tmp_path, capsys):
    path = tmp_path / "corpus.json"
    path.write_text("{not json", encoding="utf-8")
    rc = mod.main(_argv(str(path)))
    assert rc == 2
    assert "JSONDecodeError" in capsys.readouterr().err


def test_corpus_without_text_is_refused_before_any_database_work(corpus_file, capsys):
    rc = mod.main(_argv(corpus_file({"kind": "resume", "title": "Main Resume"})))
    assert rc == 2
    assert "carries no text" in capsys.readouterr().err


def test_an_ingest_refusal_is_reported_as_a_contract_error(corpus_file, capsys, monkeypatch):
    async def refuse(payload, ctx):
        raise HTTPException(status_code=422, detail={"code": "TEXT_REQUIRED",
                                                     "message": "text required"})
    async def no_user(user_id):
        return False
    async def no_rows(query, *args):
        return None
    async def broken_pool():
        return None
    async def closed_pool():
        return None
    # The pool must never be real: on a machine without a database init_db
    # raises before the ingest is ever reached, and the refusal this test
    # charges never prints (that exact red shipped once -- CI has no postgres).
    monkeypatch.setattr(mod.db, "init_db", broken_pool)
    monkeypatch.setattr(mod.db, "close_db", closed_pool)
    monkeypatch.setattr(mod.db, "fetchrow", no_rows)
    monkeypatch.setattr(mod, "_ensure_eval_user", no_user)
    monkeypatch.setattr("app.api.ingest.ingest_text", refuse)
    rc = mod.main(_argv(corpus_file({"kind": "resume", "title": "T", "text": "x"})))
    assert rc == 2
    assert "TEXT_REQUIRED" in capsys.readouterr().err


def test_a_failed_ingest_is_reported_where_it_happened(corpus_file, capsys, monkeypatch):
    async def ingest(payload, ctx):
        return {"document_id": "d1", "source_id": "s1", "embedding_provider": "hash"}
    async def broken_pool():
        return None
    async def closed_pool():
        return None
    async def get_document(doc_id):
        return {"id": doc_id, "status": "failed", "error": "embedding exploded"}
    async def no_user(user_id):
        return False
    async def no_rows(query, *args):
        return None
    monkeypatch.setattr(mod.db, "fetchrow", no_rows)
    monkeypatch.setattr(mod, "_ensure_eval_user", no_user)
    monkeypatch.setattr("app.api.ingest.ingest_text", ingest)
    monkeypatch.setattr(mod.db, "init_db", broken_pool)
    monkeypatch.setattr(mod.db, "close_db", closed_pool)
    monkeypatch.setattr(mod.docs_repo, "get_document", get_document)
    rc = mod.main(_argv(corpus_file({"kind": "resume", "title": "T", "text": "x"})))
    assert rc == 1
    assert "embedding exploded" in capsys.readouterr().err


def test_a_document_stuck_short_of_ready_times_out_named(corpus_file, capsys, monkeypatch):
    async def ingest(payload, ctx):
        return {"document_id": "d1", "source_id": "s1", "embedding_provider": "hash"}
    async def broken_pool():
        return None
    async def closed_pool():
        return None
    async def get_document(doc_id):
        return {"id": doc_id, "status": "indexing", "error": None}
    async def no_user(user_id):
        return False
    async def no_rows(query, *args):
        return None
    monkeypatch.setattr(mod.db, "fetchrow", no_rows)
    monkeypatch.setattr(mod, "_ensure_eval_user", no_user)
    monkeypatch.setattr("app.api.ingest.ingest_text", ingest)
    monkeypatch.setattr(mod.db, "init_db", broken_pool)
    monkeypatch.setattr(mod.db, "close_db", closed_pool)
    monkeypatch.setattr(mod.docs_repo, "get_document", get_document)
    rc = mod.main(_argv(corpus_file({"kind": "resume", "title": "T", "text": "x"}))
                  + ["--timeout", "0.05"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "did not reach ready" in err
    assert "indexing" in err


def test_a_ready_document_passes_and_names_what_landed(corpus_file, capsys, monkeypatch):
    async def ingest(payload, ctx):
        assert payload["kind"] == "resume", "the golden set filters kinds=[resume]"
        assert payload["text"], "the corpus text must survive the crossing"
        return {"document_id": "d1", "source_id": "s1", "embedding_provider": "hash"}
    async def broken_pool():
        return None
    async def closed_pool():
        return None
    async def get_document(doc_id):
        return {"id": doc_id, "status": "ready", "error": None}
    async def no_user(user_id):
        return False
    async def no_rows(query, *args):
        return None
    monkeypatch.setattr(mod.db, "fetchrow", no_rows)
    monkeypatch.setattr(mod, "_ensure_eval_user", no_user)
    monkeypatch.setattr("app.api.ingest.ingest_text", ingest)
    monkeypatch.setattr(mod.db, "init_db", broken_pool)
    monkeypatch.setattr(mod.db, "close_db", closed_pool)
    monkeypatch.setattr(mod.docs_repo, "get_document", get_document)
    rc = mod.main(_argv(corpus_file({"kind": "resume", "title": "T", "text": "hello corpus"})))
    assert rc == 0
    out = capsys.readouterr().out
    assert "d1" in out and "ready" in out and "hash" in out


def test_a_corpus_already_seeded_is_a_noop_not_a_second_copy(corpus_file, capsys, monkeypatch):
    calls = []
    async def ingest(payload, ctx):
        calls.append(payload)
        return {"document_id": "d2", "source_id": "s2", "embedding_provider": "hash"}
    async def no_user(user_id):
        return False
    async def seeded_row(query, *args):
        assert "content_hash" in query
        return {"id": "d1"}
    async def broken_pool():
        return None
    async def closed_pool():
        return None
    monkeypatch.setattr("app.api.ingest.ingest_text", ingest)
    monkeypatch.setattr(mod.db, "fetchrow", seeded_row)
    monkeypatch.setattr(mod, "_ensure_eval_user", no_user)
    monkeypatch.setattr(mod.db, "init_db", broken_pool)
    monkeypatch.setattr(mod.db, "close_db", closed_pool)
    rc = mod.main(_argv(corpus_file({"kind": "resume", "title": "T", "text": "hello corpus"})))
    assert rc == 0
    assert "already seeded" in capsys.readouterr().out
    assert calls == [], "a second ingest would double-count against the golden set"


def test_the_shipped_corpus_file_carries_a_resume_kind_with_text():
    # The file the nightly points at: the eval's cases filter kinds=["resume"], so
    # the corpus must be kind=resume, and the text is what the keywords judge.
    import pathlib
    corpus = json.loads(
        (pathlib.Path(__file__).resolve().parents[2] / "scripts" / "eval-corpus.json")
        .read_text(encoding="utf-8"))
    assert corpus["kind"] == "resume"
    assert corpus["text"].strip()
    for keyword in ("分布式", "Kafka", "pgvector", "缓存穿透"):
        assert keyword in corpus["text"], f"golden keyword {keyword!r} left the corpus"
