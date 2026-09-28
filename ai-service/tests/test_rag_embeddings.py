"""POST /internal/rag/embeddings: one text in, a vector (or nothing) out.

This is the backend's only way to get a query vector for its own hybrid `/jobs` SQL,
so the contract that matters is the degradation path: a provider that is unconfigured
or errors has to come back as an empty list, never as an exception that would turn a
job search the user typed into a text box into a 502. The vector itself is then bound
(not interpolated) by `JobSearchRepository`, which is pinned over there.
"""

import pytest
from pydantic import ValidationError

from app.api import rag
from app.providers import registry


class _Embedder:
    def __init__(self, vectors):
        self._vectors = vectors

    async def embed(self, texts):
        if not self._vectors:
            return []
        return [self._vectors[0] for _ in texts]


def _vec(*values):
    return [float(v) for v in values]


async def test_a_provider_answer_comes_back_as_the_embedding(monkeypatch):
    monkeypatch.setattr(registry, "get_embeddings", lambda _s: _Embedder([_vec(1, 2, 3)]))

    out = await rag.rag_embeddings(rag.EmbedReq(text="payments platform"), None)

    assert out == {"embedding": _vec(1, 2, 3)}


async def test_a_provider_that_cannot_answer_degrades_to_an_empty_list(monkeypatch):
    def boom(_settings):
        raise RuntimeError("no embedding provider configured")

    monkeypatch.setattr(registry, "get_embeddings", boom)

    out = await rag.rag_embeddings(rag.EmbedReq(text="payments platform"), None)

    # The caller reads `[]` as "no vector" and keeps its keyword pass; a raised
    # ConfigError here would surface as an AI-service error on a plain search.
    assert out == {"embedding": []}


async def test_a_provider_returning_nothing_is_also_an_empty_list(monkeypatch):
    monkeypatch.setattr(registry, "get_embeddings", lambda _s: _Embedder([]))

    out = await rag.rag_embeddings(rag.EmbedReq(text="payments platform"), None)

    assert out == {"embedding": []}


def test_blank_text_is_rejected_before_a_provider_is_asked():
    # Embedding blank text answers "what is nothing nearest to", which is noise the
    # caller would then rank above real keyword matches.
    with pytest.raises(ValidationError):
        rag.EmbedReq(text="")

    with pytest.raises(ValidationError):
        rag.EmbedReq(text="x" * 4001)
