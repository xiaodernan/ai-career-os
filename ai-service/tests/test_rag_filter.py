"""Retrieval metadata filters must be enforced by *every* hybrid channel.

retrieve() fans out to vector ∪ keyword ∪ trigram and fuses the lists with RRF.
A channel that ignores the caller's `kinds` / `document_ids` restriction does not
merely add noise: RRF scores each list by rank only, so an unfiltered channel's
rank-1 hit (1/61) outranks a filtered channel's tail hit (1/85) and displaces
legitimate evidence out of the final top-k that gets quoted to the model.
"""

import re

import app.core.db as db
from app.rag import pipeline
from app.rag import store


class SqlCapture:
    def __init__(self):
        self.calls = []

    async def __call__(self, sql, *args):
        self.calls.append((sql, args))
        return []


def chunk(cid, source_kind, text="led a team of 6"):
    return {"id": cid, "document_id": f"doc-{cid}", "text": text,
            "section_path": "resume > experience", "kind": "bullet_group",
            "meta": {}, "doc_title": f"{source_kind} doc", "doc_id": f"doc-{cid}",
            "source_kind": source_kind}


# ---------------- store.trigram_search: filter parity ----------------


async def test_trigram_search_binds_kinds_as_a_parameter(monkeypatch):
    cap = SqlCapture()
    monkeypatch.setattr(db, "fetch", cap)
    await store.trigram_search("11111111-1111-1111-1111-111111111111", "Kafka",
                               kinds=["resume", "project"])
    sql, args = cap.calls[0]
    assert "ks.kind = ANY(" in sql, "trigram channel silently ignores the kinds filter"
    assert ["resume", "project"] in args
    assert "'resume'" not in sql, "filter value must be bound, not interpolated"


async def test_trigram_search_binds_document_ids_as_a_parameter(monkeypatch):
    cap = SqlCapture()
    monkeypatch.setattr(db, "fetch", cap)
    await store.trigram_search("u", "Kafka", document_ids=["aaaaaaaa-1111-1111-1111-111111111111"])
    sql, args = cap.calls[0]
    assert "c.document_id = ANY(" in sql
    assert any(a and str(a[0]).startswith("aaaaaaaa") for a in args if isinstance(a, list))
    assert "aaaaaaaa-1111" not in sql


async def test_trigram_search_without_filters_adds_no_clauses(monkeypatch):
    """Unrestricted retrieval must keep documents that have no knowledge_sources row:
    the kinds clause is `ks.kind = ANY(...)` over a LEFT JOIN, so adding it unconditionally
    would silently drop every source-less document."""
    cap = SqlCapture()
    monkeypatch.setattr(db, "fetch", cap)
    await store.trigram_search("u", "Kafka")
    sql, _ = cap.calls[0]
    assert "ks.kind = ANY(" not in sql
    assert "c.document_id = ANY(" not in sql


async def test_vector_search_skill_filter_casts_the_jsonb_not_the_key(monkeypatch):
    """`c.meta->'skills'::text` parses as c.meta -> ('skills'::text), so the LIKE would
    get jsonb on its left side and Postgres rejects the whole statement."""
    cap = SqlCapture()
    monkeypatch.setattr(db, "fetch", cap)
    await store.vector_search("u", [0.1, 0.2], skill="Kafka")
    sql, args = cap.calls[0]
    assert "(c.meta->'skills')::text LIKE" in sql
    assert "Kafka" not in sql, "skill pattern must be bound, not interpolated"
    assert '%"Kafka"%' in args


async def test_all_channel_placeholders_match_their_argument_list(monkeypatch):
    """Adding a clause without appending its argument (or in the wrong order) silently
    re-binds every later placeholder to the wrong value; numbering must be dense 1..n."""
    cap = SqlCapture()
    monkeypatch.setattr(db, "fetch", cap)
    doc = "aaaaaaaa-1111-1111-1111-111111111111"
    await store.vector_search("u", [0.1], kinds=["resume"], document_ids=[doc], skill="Kafka")
    await store.keyword_search("u", "kafka", kinds=["resume"], document_ids=[doc])
    await store.trigram_search("u", "kafka", kinds=["resume"], document_ids=[doc])
    assert len(cap.calls) == 3
    for sql, args in cap.calls:
        nums = sorted({int(n) for n in re.findall(r"\$(\d+)", sql)})
        assert nums == list(range(1, len(args) + 1)), f"placeholder/arg drift: {nums} vs {len(args)}"


# ---------------- pipeline.retrieve: wiring ----------------


class Recorder:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    async def __call__(self, *args, **kwargs):
        self.calls.append({"args": args, "kwargs": kwargs})
        return self.rows


class FakeEmbedder:
    async def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def _patch_pipeline(monkeypatch, understanding, rows):
    vec = Recorder(rows)
    kw = Recorder(rows)
    tri = Recorder(rows)
    monkeypatch.setattr(pipeline.store, "vector_search", vec)
    monkeypatch.setattr(pipeline.store, "keyword_search", kw)
    monkeypatch.setattr(pipeline.store, "trigram_search", tri)

    async def fake_understand(*a, **k):
        return understanding

    async def fake_rerank(query, chunks, top_n=8, **k):
        return chunks[:top_n]

    monkeypatch.setattr(pipeline, "understand", fake_understand)
    monkeypatch.setattr(pipeline, "get_embeddings", lambda *a, **k: FakeEmbedder())
    monkeypatch.setattr(pipeline, "rerank", fake_rerank)
    monkeypatch.setattr(pipeline, "compress", lambda terms, chunks: chunks)
    return vec, kw, tri


def _understanding(**filters):
    return {"rewritten": "backend experience with Kafka", "expansions": ["messaging"],
            "intent": "personal_fact", "keywords": ["Kafka", "Spring Boot"],
            "needs_personal_evidence": True, "filters": filters, "original": "q"}


async def test_retrieve_applies_caller_filters_to_every_channel(monkeypatch):
    vec, kw, tri = _patch_pipeline(monkeypatch, _understanding(), [chunk("c1", "resume")])
    await pipeline.retrieve("kafka experience", user_id="u", top_k=5,
                            kinds=["resume", "project"], document_ids=["doc-1"])
    assert len(vec.calls) >= 1 and len(kw.calls) == 1 and len(tri.calls) == 1
    for rec in (vec, kw, tri):
        assert rec.calls[0]["kwargs"].get("kinds") == ["resume", "project"], \
            "a hybrid channel escaped the kinds restriction"
        assert rec.calls[0]["kwargs"].get("document_ids") == ["doc-1"], \
            "a hybrid channel escaped the document scope"


async def test_retrieve_applies_understanding_derived_filters_to_every_channel(monkeypatch):
    """Even when the caller passes nothing, query understanding can restrict kinds;
    the derived filter must bind all three channels too."""
    vec, kw, tri = _patch_pipeline(monkeypatch, _understanding(kinds=["goal"]),
                                   [chunk("c1", "goal")])
    await pipeline.retrieve("career goal", user_id="u")
    for rec in (vec, kw, tri):
        assert rec.calls[0]["kwargs"].get("kinds") == ["goal"]


async def test_rrf_lets_an_unfiltered_channel_tail_hit_outrank_filtered_evidence():
    """Why the leak matters: a chunk only the unfiltered channel found at rank 0 fuses
    above a legitimately-filtered chunk sitting at the tail of the filtered list."""
    filtered = [chunk(f"f{i}", "resume") for i in range(25)]
    leaked = [chunk("leaked", "jd")]
    merged = store.rrf_merge([filtered, leaked])
    ranks = [str(m["id"]) for m in merged]
    assert ranks.index("leaked") < ranks.index("f24"), \
        "unfiltered rank-1 should (by design of RRF) beat filtered tail hits"
    assert merged[ranks.index("leaked")]["source_kind"] == "jd"
