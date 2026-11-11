"""What the retrieval pipeline remembers, and why each key is the key it is.

Two caches, two different questions:

* **The retrieval result** — "has this reader already asked this exact question?"
  The key must therefore carry everything that can change the answer: the reader, the
  normalised query, the summary the rewriter resolves pronouns against, the top_k, the
  source filter, the document filter, the channel strategy and the expansion cap. Leave
  one out and a narrowed question gets a broad answer from the cache.
* **An embedding** — "has this text already been embedded by this model?"  The key is
  the provider, the model, the dimension *and* the text, because a vector from a
  different model is a different vector in the same shape: reuse would silently rank
  by the wrong geometry.

Both keys carry the reader's **epoch** (a counter bumped when their knowledge changes).
A TTL alone would answer a question about a resume that no longer says that, for as
long as the TTL; the epoch makes an ingest invalidate immediately.

Vectors are stored as base64 of the raw float64 buffer rather than JSON. A 1536-dim
vector is 12 KB of doubles — 16 KB base64 against ~30 KB of JSON — and, more
importantly, the round trip is *exact*: `array('d')` returns the same bits, so a
cached vector ranks identically to a recomputed one.
"""

from __future__ import annotations

import base64
import hashlib
from array import array
from typing import Any, Iterable, Sequence

from app.core import cache as cache_mod
from app.core.config import get_settings

EPOCH_PREFIX = "careeros:rag:epoch"
EMBED_PREFIX = "careeros:emb:v1"
RETRIEVAL_PREFIX = "careeros:rag:v1"
EPOCH_TTL = 7 * 24 * 3600


def _digest(parts: Iterable[str]) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(part.encode("utf-8"))
        h.update(b"\x1f")  # a separator no caller can smuggle into a field
    return h.hexdigest()[:40]


def normalise(text: str | None) -> str:
    """Whitespace-collapsed, case-folded: `What is Kafka?` and `what is  kafka?` are one question."""
    return " ".join((text or "").split()).casefold()


def epoch_key(user_id: str) -> str:
    return f"{EPOCH_PREFIX}:{user_id}"


async def epoch(user_id: str) -> int:
    """The reader's cache generation. A missing counter is generation 0, not an error.

    This is one extra round trip per retrieval and it is deliberate: a one-second
    in-process memo would make a freshly ingested resume invisible for a second, which
    is exactly the moment a reader is most likely to ask about it.
    """
    cache = cache_mod.get_cache()
    if not cache.enabled:
        return 0
    return await cache.counter(epoch_key(user_id))


async def invalidate_user(user_id: str) -> int:
    """Bump the generation: every key under it becomes unreadable at once.

    Cheaper and safer than deleting by pattern (`SCAN` + `UNLINK` walks the whole
    keyspace), and it cannot miss an entry written by another replica a moment ago.
    """
    cache = cache_mod.get_cache()
    if not cache.enabled:
        return 0
    return await cache.incr(epoch_key(user_id), ttl=EPOCH_TTL)


def retrieval_key(*, user_id: str, generation: int, query: str, top_k: int,
                  kinds: Sequence[str] | None, document_ids: Sequence[str] | None,
                  context_summary: str, strategy: str, max_expansions: int | None) -> str:
    scope = _digest([
        normalise(query),
        normalise(context_summary),
        str(int(top_k)),
        ",".join(sorted(k.strip().lower() for k in (kinds or []) if k and k.strip())),
        ",".join(sorted(str(d) for d in (document_ids or []))),
        normalise(strategy),
        "" if max_expansions is None else str(int(max_expansions)),
    ])
    return f"{RETRIEVAL_PREFIX}:{user_id}:{generation}:{scope}"


def model_identity() -> str:
    s = get_settings()
    return f"{s.embedding_provider}|{s.embedding_model}|{s.embedding_dim}"


def embedding_key(text: str) -> str:
    return f"{EMBED_PREFIX}:{_digest([model_identity(), normalise(text)])}"


def encode_vector(values: Sequence[float]) -> str:
    buf = array("d", (float(v) for v in values))
    return f"{len(buf)}:{base64.b64encode(buf.tobytes()).decode('ascii')}"


def decode_vector(text: Any) -> list[float] | None:
    """A stored vector, or None when the payload is not one this build can trust."""
    if not isinstance(text, str) or ":" not in text:
        return None
    head, _, body = text.partition(":")
    try:
        expected = int(head)
        raw = base64.b64decode(body.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError):
        return None
    if expected <= 0 or len(raw) != expected * 8:
        return None
    buf = array("d")
    buf.frombytes(raw)
    return [float(v) for v in buf]


async def cached_vectors(texts: Sequence[str]) -> list[list[float] | None]:
    """Look every text up in one MGET; a miss is `None`, never an exception."""
    cache = cache_mod.get_cache()
    out: list[list[float] | None] = [None] * len(texts)
    if not cache.enabled or not texts:
        return out
    keys = [embedding_key(t) for t in texts]
    try:
        rows = await cache.get_many(keys)
    except Exception:  # a cache lookup may never take the embedding path down
        return out
    for i, raw in enumerate(rows[:len(texts)]):
        out[i] = decode_vector(raw)
    return out


async def remember_vectors(texts: Sequence[str], vectors: Sequence[Sequence[float]]) -> None:
    cache = cache_mod.get_cache()
    if not cache.enabled:
        return
    items = [(embedding_key(t), encode_vector(v))
             for t, v in zip(texts, vectors) if v]
    if not items:
        return
    try:
        await cache.set_many(items)
    except Exception:
        return


async def embed_with_cache(embedder, texts: Sequence[str]) -> list[list[float]]:
    """Embed only the texts this process has not embedded before, in one batched call.

    The saving is not only provider latency: the miss batch keeps the caller's order,
    so a query whose four expansions were all seen earlier costs zero provider calls,
    and a query with one new expansion costs one call for one text.
    """
    texts = list(texts)
    if not texts:
        return []
    cached = await cached_vectors(texts)
    missing_idx = [i for i, v in enumerate(cached) if not v]
    if not missing_idx:
        return [v or [] for v in cached]
    fresh = await embedder.embed([texts[i] for i in missing_idx])
    fresh = [v for v in (fresh or []) if isinstance(v, list) and v]
    # A provider that answers with fewer vectors than inputs has broken its contract;
    # pairing by position would then attach one text's vector to another's key, which
    # is worse than a miss. Only a full-length answer is trusted.
    if len(fresh) == len(missing_idx):
        for slot, vector in zip(missing_idx, fresh):
            cached[slot] = vector
        await remember_vectors([texts[i] for i in missing_idx], fresh)
    return [v or [] for v in cached]


async def lookup_retrieval(key: str) -> dict[str, Any] | None:
    cache = cache_mod.get_cache()
    if not cache.enabled:
        return None
    raw = await cache.get(key)
    payload = cache_mod.loads(raw)
    if isinstance(payload, dict) and isinstance(payload.get("evidence"), list):
        return payload
    return None


async def remember_retrieval(key: str, payload: dict[str, Any], *, ttl: int | None = None) -> None:
    cache = cache_mod.get_cache()
    if not cache.enabled:
        return
    await cache.set(key, cache_mod.dumps(payload), ttl=ttl)


def describe() -> dict[str, Any]:
    cache = cache_mod.get_cache()
    flight = cache_mod.get_single_flight()
    data = cache.describe()
    data["single_flight"] = {"leaders": flight.leaders, "joined": flight.joined,
                             "inflight": len(flight)}
    data["embedding_model"] = model_identity()
    return data
