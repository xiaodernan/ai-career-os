"""POST /internal/rag/cache/invalidate: a delete the reader cannot keep quoting.

Finding B, open since Epic 143: a note / source / resume delete retires its documents
(``status='retired'``) but never tells the RAG cache, so a retrieval cached before the
delete keeps quoting text the user removed until TTL. The fix is a generation bump:
every cached key is namespaced by a per-user epoch, so retiring the whole generation
makes all of them unreadable at once — on every replica, because the epoch counter
lives in the shared store (Redis / layered), not in process memory.

What this file pins, offline and with no live service:

* the route carries the same internal-token + X-User-Id door as every /internal route;
  ``invalidate_user``'s fail-open shape means a cache that is off, or a store that is
  down, answers honestly ("nothing was invalidated") and never a 5xx over a delete
  that already committed;
* with a real cache installed, one call bumps the generation by one and a retrieval
  key written under the old generation is no longer the one the reader addresses;
* the endpoint is scoped to its own ``ctx.user_id`` — a caller cannot name another
  user's epoch to invalidate, because the route takes no body at all;
* the endpoint has a *real* backend caller, and the backend calls it only after the
  delete transaction commits. A write endpoint nobody consumes is exactly the orphan
  machine Epic 143 refused to build; this is the gate that would have caught it.

The after-commit half is pinned by the backend's own unit tests
(``RagCacheInvalidatorTest``); this file owns the ai-service surface and the seam.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core import cache as cache_mod
from app.core.config import get_settings
from app.main import app
from app.rag import caching

TOKEN = get_settings().internal_api_token
USER = "00000000-0000-0000-0000-0000000000aa"
AUTH = {"X-Internal-Token": TOKEN, "X-User-Id": USER}
PATH = "/internal/rag/cache/invalidate"

# Not a context manager: the app lifespan opens Postgres, which this offline seam never needs.
client = TestClient(app)


@pytest.fixture(autouse=True)
def _isolate_process_cache():
    """Every test owns the global cache slot and restores it, so none leaks to another."""
    previous = cache_mod.get_cache()
    yield
    cache_mod.install_cache(previous)


# --------------------------------------------------------------- auth (the shared door)
def test_no_internal_token_is_refused():
    r = client.post(PATH, headers={"X-User-Id": USER})
    assert r.status_code == 401


def test_a_valid_token_without_a_user_id_is_refused():
    r = client.post(PATH, headers={"X-Internal-Token": TOKEN})
    assert r.status_code == 400, "a cache bump must be scoped to a user"


# --------------------------------------------------------------- fail-open: cache off
async def test_with_the_cache_off_nothing_is_invalidated_and_it_is_not_an_error():
    cache_mod.install_cache(cache_mod.NullCache())
    r = client.post(PATH, headers=AUTH)
    assert r.status_code == 200
    assert r.json() == {"invalidated": False, "generation": 0}, (
        "off is an honest 'nothing to invalidate', never a 5xx over a committed delete")


# --------------------------------------------------------------- the real effect
async def test_one_call_bumps_the_generation_by_one():
    cache = cache_mod.MemoryCache(max_entries=128, ttl=300)
    cache_mod.install_cache(cache)
    assert await caching.epoch(USER) == 0

    r = client.post(PATH, headers=AUTH)
    assert r.status_code == 200
    assert r.json() == {"invalidated": True, "generation": 1}
    assert await caching.epoch(USER) == 1


async def test_a_repeat_call_keeps_bumping_so_a_second_delete_also_invalidates():
    cache_mod.install_cache(cache_mod.MemoryCache(max_entries=128, ttl=300))
    client.post(PATH, headers=AUTH)
    r = client.post(PATH, headers=AUTH)
    assert r.json()["generation"] == 2, "each delete retires the generation written before it"


async def test_the_old_generations_retrieval_key_is_no_longer_the_readers_key():
    """The mechanism, not just the counter: a cached retrieval's key embeds the epoch,
    so after a bump the reader addresses a *different* key and cannot quote the old value."""
    cache = cache_mod.MemoryCache(max_entries=128, ttl=300)
    cache_mod.install_cache(cache)

    gen0 = await caching.epoch(USER)
    old_key = caching.retrieval_key(
        user_id=USER, generation=gen0, query="summer internship", top_k=8,
        kinds=None, document_ids=None, context_summary="", strategy="hybrid",
        max_expansions=None)
    await cache.set(old_key, "text the user just deleted")

    client.post(PATH, headers=AUTH)
    gen1 = await caching.epoch(USER)
    new_key = caching.retrieval_key(
        user_id=USER, generation=gen1, query="summer internship", top_k=8,
        kinds=None, document_ids=None, context_summary="", strategy="hybrid",
        max_expansions=None)

    assert new_key != old_key, "the generation is in the key; the old value is unreachable"
    assert await cache.get(new_key) is None, "the reader starts fresh after the delete"


async def test_it_only_invalidates_the_calling_users_generation():
    """The route takes no body, so the only user it can touch is the header's own."""
    cache_mod.install_cache(cache_mod.MemoryCache(max_entries=128, ttl=300))
    other = "00000000-0000-0000-0000-0000000000bb"

    client.post(PATH, headers=AUTH)  # USER bumps
    assert await caching.epoch(USER) == 1
    assert await caching.epoch(other) == 0, "a caller cannot reach another user's cache"


# --------------------------------------------------------------- fail-open: store down
async def test_a_bump_that_did_not_take_is_reported_not_assumed():
    """When an enabled backend cannot write the counter (a Redis blip: its ``incr``
    fails open to 0), the endpoint must say ``invalidated=False`` — never claim a
    retirement it did not achieve. The honest worst case is that the stale entry
    expires on its own TTL; the delete that already committed still stands, and the
    RedisCache's real down-path is separately pinned by the cache suite."""
    class Blipped(cache_mod.MemoryCache):
        enabled = True

        async def incr(self, key, ttl=None):
            return 0  # exactly what RedisCache.incr returns when the store is unavailable

    cache_mod.install_cache(Blipped())
    r = client.post(PATH, headers=AUTH)
    assert r.status_code == 200
    assert r.json() == {"invalidated": False, "generation": 0}, (
        "a bump that returned 0 is reported as 'not invalidated', not silently called a success")


# --------------------------------------------------------------- no orphan endpoint
def test_the_write_endpoint_has_a_real_backend_caller():
    """The discipline that shaped Epic 143, inverted: a write endpoint nobody calls is
    a machine built for nobody. This route must be driven by the backend's delete path,
    and only after that transaction commits."""
    root = Path(__file__).resolve().parents[2]
    client_src = (root / "backend" / "src" / "main" / "java" / "com" / "careeros"
                  / "ai" / "HttpAiServiceClient.java").read_text(encoding="utf-8")
    assert "/internal/rag/cache/invalidate" in client_src, "the backend must build this call"

    root_pkg = root / "backend" / "src" / "main" / "java" / "com" / "careeros" / "knowledge" / "service"
    invalidator = root_pkg / "RagCacheInvalidator.java"
    assert invalidator.exists(), "the after-commit invalidator must exist"
    src = invalidator.read_text(encoding="utf-8")
    assert "afterCommit" in src, "the bump must run AFTER the delete commits, not inside it"
    assert "invalidateCache" in src, "the invalidator must go through the typed client"
