"""A cache seam: off, process-local, or Redis — chosen by configuration, never by import.

The rule this module exists to enforce: **a cache may not break the product**. Every
backend answers a `get` with a value or `None`, and the Redis one turns a dead server,
a refused command and a timeout into `None` after counting the failure. A retrieval
that misses is slower; a retrieval that raises because the cache is down is a broken
product.

Three shapes, one interface:

* `NullCache` — the default. It is a real backend rather than "no cache" so callers
  never branch on whether caching is on.
* `MemoryCache` — an LRU with per-entry expiry, bounded by entries. Process-local, so
  a second replica has its own; that is the right default for a single-laptop dev
  stack and the wrong one for a fleet.
* `RedisCache` — shared, so every replica sees the entry one of them computed. Its
  transport is `app.core.resp` (no dependency), and it carries a breaker: after a
  failure the socket is left alone for `cooldown` seconds, so an outage costs one
  timeout rather than one per request.
* `LayeredCache` — memory in front of Redis. Hit rates are reported per layer,
  because "the cache is hitting" and "the cache is hitting *locally*" are different
  claims and only the second one makes a fleet cheap.

`SingleFlight` is the other half of the story. A cache that is cold is a cache that
lets ten concurrent readers compute the same expensive answer ten times — the
thundering herd. `SingleFlight.run` lets the first caller compute and the rest await
its result, so a cold key costs one model call, not ten.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import OrderedDict
from dataclasses import asdict, dataclass
from typing import Any, Callable, Iterable, Sequence

from app.core import resp

log = logging.getLogger("core.cache")

_MISSING = object()


@dataclass
class CacheStats:
    """Counters a reader can trust: each is incremented where the event happens."""

    hits: int = 0
    misses: int = 0
    writes: int = 0
    errors: int = 0
    evictions: int = 0
    l2_hits: int = 0
    joined: int = 0

    @property
    def lookups(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        return round(self.hits / self.lookups, 4) if self.lookups else 0.0

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["lookups"] = self.lookups
        data["hit_rate"] = self.hit_rate
        return data


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def loads(text: str | bytes | None) -> Any:
    if text is None:
        return _MISSING
    if isinstance(text, bytes):
        try:
            text = text.decode("utf-8")
        except UnicodeDecodeError:
            return _MISSING
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return _MISSING


class Cache:
    """The interface every backend answers. `enabled` is a fact, not a guess."""

    name = "null"
    enabled = False

    def __init__(self) -> None:
        self.stats = CacheStats()

    async def get(self, key: str) -> str | None:  # pragma: no cover - interface
        raise NotImplementedError

    async def get_many(self, keys: Sequence[str]) -> list[str | None]:
        return [await self.get(k) for k in keys]

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        raise NotImplementedError

    async def set_many(self, items: Iterable[tuple[str, str]], ttl: int | None = None) -> None:
        for key, value in items:
            await self.set(key, value, ttl)

    async def delete(self, *keys: str) -> None:
        return None

    async def incr(self, key: str, ttl: int | None = None) -> int:
        return 0

    async def counter(self, key: str) -> int:
        """Read a counter without creating it. A missing counter is 0, not an error."""
        return 0

    async def close(self) -> None:
        return None

    def describe(self) -> dict[str, Any]:
        return {"backend": self.name, "enabled": self.enabled, "stats": self.stats.as_dict()}


class NullCache(Cache):
    """Caching off, spelled as a backend so no caller needs `if cache:`."""

    name = "off"

    async def get(self, key: str) -> str | None:
        self.stats.misses += 1
        return None

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        return None


class MemoryCache(Cache):
    """LRU with per-entry expiry, bounded by `max_entries`.

    The eviction order is the access order (`OrderedDict.move_to_end` on every hit),
    so the entry that leaves is the one nobody has read for longest. Expiry is checked
    on read rather than on a timer: a background sweeper would be a task per process
    for a structure whose size is already bounded.
    """

    name = "memory"
    enabled = True

    def __init__(self, max_entries: int = 2048, ttl: int = 300,
                 clock: Callable[[], float] = time.monotonic):
        super().__init__()
        self.max_entries = max(1, int(max_entries))
        self.ttl = max(1, int(ttl))
        self._clock = clock
        self._rows: OrderedDict[str, tuple[float, str]] = OrderedDict()
        # Counters live outside the LRU on purpose. An epoch that the LRU evicted
        # would read as generation 0, which makes every entry written before the
        # eviction readable again -- a cache that silently un-invalidates itself.
        self._counters: dict[str, tuple[float, int]] = {}

    def _live(self, key: str) -> str | None:
        row = self._rows.get(key)
        if row is None:
            return None
        expires_at, value = row
        if expires_at <= self._clock():
            self._rows.pop(key, None)
            return None
        self._rows.move_to_end(key)
        return value

    async def get(self, key: str) -> str | None:
        value = self._live(key)
        if value is None:
            self.stats.misses += 1
        else:
            self.stats.hits += 1
        return value

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        self._rows[key] = (self._clock() + (ttl or self.ttl), value)
        self._rows.move_to_end(key)
        while len(self._rows) > self.max_entries:
            self._rows.popitem(last=False)
            self.stats.evictions += 1
        self.stats.writes += 1

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self._rows.pop(key, None)
            self._counters.pop(key, None)

    async def incr(self, key: str, ttl: int | None = None) -> int:
        expires_at, value = self._counters.get(key, (0.0, 0))
        now = self._clock()
        value = (value if expires_at > now else 0) + 1
        self._counters[key] = (now + (ttl or self.ttl), value)
        return value

    async def counter(self, key: str) -> int:
        expires_at, value = self._counters.get(key, (0.0, 0))
        return value if expires_at > self._clock() else 0

    def __len__(self) -> int:
        return len(self._rows)


class RedisCache(Cache):
    """Redis behind a breaker: a failure costs `cooldown` seconds, not one per request."""

    name = "redis"
    enabled = True

    def __init__(self, pool: resp.RespPool, ttl: int = 300, *, cooldown: float = 5.0,
                 clock: Callable[[], float] = time.monotonic):
        super().__init__()
        self.pool = pool
        self.ttl = max(1, int(ttl))
        self.cooldown = max(0.0, float(cooldown))
        self._clock = clock
        self._down_until = 0.0
        self.breaker_trips = 0

    def _available(self) -> bool:
        return self._clock() >= self._down_until

    def _failed(self, error: BaseException) -> None:
        self.stats.errors += 1
        self._down_until = self._clock() + self.cooldown
        self.breaker_trips += 1
        log.warning("cache redis unavailable (%s); serving misses for %.1fs",
                    type(error).__name__, self.cooldown)

    async def _call(self, *args: Any) -> Any:
        try:
            return await self.pool.execute(*args)
        except (resp.RespUnavailable, resp.RespError, OSError) as e:
            self._failed(e)
            return None

    async def get(self, key: str) -> str | None:
        if not self._available():
            self.stats.misses += 1
            return None
        raw = await self._call("GET", key)
        if raw is None:
            self.stats.misses += 1
            return None
        self.stats.hits += 1
        return raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)

    async def get_many(self, keys: Sequence[str]) -> list[str | None]:
        keys = list(keys)
        if not keys:
            return []
        if not self._available():
            self.stats.misses += len(keys)
            return [None] * len(keys)
        try:
            replies = await self.pool.execute("MGET", *keys)
        except (resp.RespUnavailable, resp.RespError, OSError) as e:
            self._failed(e)
            return [None] * len(keys)
        if not isinstance(replies, list):
            return [None] * len(keys)
        out: list[str | None] = []
        for raw in replies:
            if raw is None:
                out.append(None)
                self.stats.misses += 1
            else:
                out.append(raw.decode("utf-8", "replace") if isinstance(raw, bytes)
                           else str(raw))
                self.stats.hits += 1
        return out

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        if not self._available():
            return
        await self._call("SET", key, value, "EX", int(ttl or self.ttl))
        self.stats.writes += 1

    async def set_many(self, items: Iterable[tuple[str, str]], ttl: int | None = None) -> None:
        batch = list(items)
        if not batch or not self._available():
            return
        commands = [("SET", key, value, "EX", int(ttl or self.ttl)) for key, value in batch]
        try:
            # One round trip for N writes: the pipelining property `resp` exists for.
            await self.pool.pipeline(commands)
        except (resp.RespUnavailable, resp.RespError, OSError) as e:
            self._failed(e)
            return
        self.stats.writes += len(batch)

    async def delete(self, *keys: str) -> None:
        if keys and self._available():
            await self._call("DEL", *keys)

    async def incr(self, key: str, ttl: int | None = None) -> int:
        """A monotonic counter for cache epochs (bump = invalidate everything under it)."""
        if not self._available():
            return 0
        try:
            replies = await self.pool.pipeline([("INCR", key),
                                                ("EXPIRE", key, int(ttl or self.ttl))])
        except (resp.RespUnavailable, resp.RespError, OSError) as e:
            self._failed(e)
            return 0
        value = replies[0] if replies else 0
        return int(value) if isinstance(value, int) else 0

    async def counter(self, key: str) -> int:
        if not self._available():
            return 0
        raw = await self._call("GET", key)
        if raw is None:
            return 0
        if isinstance(raw, bytes):
            raw = raw.decode("ascii", "replace")
        try:
            return int(raw)
        except (TypeError, ValueError):
            return 0

    async def close(self) -> None:
        await self.pool.close()

    def describe(self) -> dict[str, Any]:
        """The transport's own health, which ``CacheStats`` cannot express.

        ``breaker_trips`` used to be written but never read: it lives on this
        object, not in ``stats``, so ``/internal/rag/cache`` never showed it and
        a Redis outage looked like a clean run of misses. Epic 143 surfaces it
        (plus whether the breaker is currently open) so the health fold can tell
        "cold cache" from "cache whose shared layer is down".
        """
        data = super().describe()
        data["breaker"] = {
            "trips": self.breaker_trips,
            "open": not self._available(),
            "cooldown_s": self.cooldown,
        }
        return data


class LayeredCache(Cache):
    """Memory in front of Redis. The front layer is short-lived; the back one is shared."""

    name = "layered"
    enabled = True

    def __init__(self, local: Cache, shared: Cache):
        super().__init__()
        self.local = local
        self.shared = shared

    async def get(self, key: str) -> str | None:
        hit = await self.local.get(key)
        if hit is not None:
            self.stats.hits += 1
            return hit
        hit = await self.shared.get(key)
        if hit is None:
            self.stats.misses += 1
            return None
        # Fill the front layer with the back layer's answer: the next hit in this
        # process is a dictionary lookup instead of a socket round trip.
        await self.local.set(key, hit)
        self.stats.hits += 1
        self.stats.l2_hits += 1
        return hit

    async def get_many(self, keys: Sequence[str]) -> list[str | None]:
        keys = list(keys)
        out: list[str | None] = []
        missing: list[tuple[int, str]] = []
        for index, key in enumerate(keys):
            hit = await self.local.get(key)
            out.append(hit)
            if hit is None:
                missing.append((index, key))
        if missing:
            fetched = await self.shared.get_many([k for _, k in missing])
            for (index, key), value in zip(missing, fetched):
                out[index] = value
                if value is not None:
                    self.stats.l2_hits += 1
                    await self.local.set(key, value)
        for value in out:
            if value is None:
                self.stats.misses += 1
            else:
                self.stats.hits += 1
        return out

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        await self.local.set(key, value, ttl)
        await self.shared.set(key, value, ttl)
        self.stats.writes += 1

    async def set_many(self, items: Iterable[tuple[str, str]], ttl: int | None = None) -> None:
        batch = list(items)
        if not batch:
            return
        await self.local.set_many(batch, ttl)
        await self.shared.set_many(batch, ttl)
        self.stats.writes += len(batch)

    async def delete(self, *keys: str) -> None:
        await self.local.delete(*keys)
        await self.shared.delete(*keys)

    async def incr(self, key: str, ttl: int | None = None) -> int:
        # The counter has to live where every replica can see it; the front layer's
        # copy is dropped so this process cannot answer from a stale epoch.
        await self.local.delete(key)
        return await self.shared.incr(key, ttl)

    async def counter(self, key: str) -> int:
        # Read-through is wrong for a counter: the front layer would happily serve a
        # generation this process already knows is stale.
        return await self.shared.counter(key)

    async def close(self) -> None:
        await self.local.close()
        await self.shared.close()

    def describe(self) -> dict[str, Any]:
        data = super().describe()
        data["local"] = self.local.describe()
        data["shared"] = self.shared.describe()
        return data


class SingleFlight:
    """Collapse concurrent computations of the same key into one.

    `joined` counts the callers who waited instead of computing, which is the number
    that says whether this is doing anything: on a warm cache it stays at zero.
    """

    def __init__(self) -> None:
        self._inflight: dict[str, asyncio.Future] = {}
        self.joined = 0
        self.leaders = 0

    def __len__(self) -> int:
        return len(self._inflight)

    async def run(self, key: str, factory: Callable[[], Any]) -> Any:
        existing = self._inflight.get(key)
        if existing is not None:
            self.joined += 1
            return await asyncio.shield(existing)
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        # A future nobody awaits must not warn on the way out; retrieving the
        # exception in a done-callback marks it as observed.
        future.add_done_callback(lambda f: f.cancelled() or f.exception())
        self._inflight[key] = future
        self.leaders += 1
        try:
            value = await factory()
        except asyncio.CancelledError:
            # The leader's task went away. Followers are not cancelled -- they asked
            # for a value and deserve an answer they can retry from.
            if not future.done():
                future.set_exception(RuntimeError("single-flight leader cancelled"))
            raise
        except BaseException as e:
            if not future.done():
                future.set_exception(e)
            raise
        else:
            if not future.done():
                future.set_result(value)
            return value
        finally:
            self._inflight.pop(key, None)


_cache: Cache = NullCache()
_flight = SingleFlight()


def get_cache() -> Cache:
    return _cache


def get_single_flight() -> SingleFlight:
    return _flight


def build_cache(settings) -> Cache:
    """The backend the settings name. A bad Redis URL degrades to memory, loudly."""
    backend = (getattr(settings, "cache_backend", "off") or "off").strip().lower()
    ttl = int(getattr(settings, "cache_ttl_s", 300) or 300)
    entries = int(getattr(settings, "cache_max_entries", 2048) or 2048)
    if backend in ("off", "none", "false", ""):
        return NullCache()
    if backend == "memory":
        return MemoryCache(max_entries=entries, ttl=ttl)
    if backend != "redis":
        log.warning("unknown CACHE_BACKEND %r; caching stays off", backend)
        return NullCache()
    url = getattr(settings, "redis_url", "") or ""
    try:
        pool = resp.RespPool.from_url(
            url, size=int(getattr(settings, "redis_pool_size", 4) or 4),
            connect_timeout=float(getattr(settings, "redis_connect_timeout_s", 0.5) or 0.5),
            command_timeout=float(getattr(settings, "redis_timeout_s", 0.5) or 0.5))
    except (ValueError, OSError) as e:
        log.warning("CACHE_BACKEND=redis but REDIS_URL is unusable (%s); using memory", e)
        return MemoryCache(max_entries=entries, ttl=ttl)
    # The front layer is deliberately shorter-lived than the shared one: it exists to
    # save a round trip, not to become the authority on freshness.
    return LayeredCache(
        MemoryCache(max_entries=entries, ttl=max(1, min(ttl, 30))),
        RedisCache(pool, ttl=ttl))


async def init_cache(settings=None) -> Cache:
    global _cache
    if settings is None:
        from app.core.config import get_settings
        settings = get_settings()
    await close_cache()
    _cache = build_cache(settings)
    log.info("cache backend=%s", _cache.name)
    return _cache


async def close_cache() -> None:
    global _cache
    previous, _cache = _cache, NullCache()
    try:
        await previous.close()
    except Exception:  # closing a broken transport must not fail shutdown
        log.debug("cache close failed", exc_info=True)


def install_cache(cache: Cache) -> None:
    """Replace the process cache (tests, and the settings-driven path in `init_cache`)."""
    global _cache
    _cache = cache
