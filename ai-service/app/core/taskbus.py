"""In-process task event bus for AI pipeline progress + SSE streaming.

Defaults to the single-instance in-process feed (documented tradeoff).
Set ``TASK_BUS_BACKEND=redis`` to mirror the live feed into a Redis Stream
so a subscriber on any replica can follow a task another replica owns -- the
scale-out path. Memory behaviour is unchanged in both modes (same event
shapes, same order, one writer per task); the stream is a mirror, never a
second source of truth the local reader must disagree with.
"""

import asyncio
import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from app.core import resp

log = logging.getLogger(__name__)

_TASKS: dict[str, dict[str, Any]] = {}
_MAX_HISTORY = 400
# A mirrored task stream is a live-handoff aid, not an archive: the terminal event
# is replayable for as long as any relay could still be following it, then the key
# is allowed to expire so a long-lived service does not accumulate one Redis key
# per task forever. Every write (including the terminal one) pushes this window
# out again, so an active task never expires under a subscriber; only a task that
# went quiet for a whole window does. 3600s is well past the relay's 10-minute
# read budget and the 15s stream wait, and matches the in-memory gc's max age.
# This is a module constant, like _MAX_HISTORY -- not an operator knob: no caller
# needs to tune it, and a knob nobody would read is a knob that does nothing.
_MIRROR_TTL_S = 3600

# ----------------------- the Redis Streams backplane (opt-in) -----------------------

_BACKPLANE_STREAM_PREFIX = "careeros:tasks:"
_BACKPLANE: "_Backplane | None" = None
_BACKPLANE_BUILT = False
_DRAINER: asyncio.Task | None = None
_MIRROR_QUEUE: asyncio.Queue[tuple[str, dict]] | None = None


class _Backplane:
    """The mirror of the task feed in a Redis stream (one stream per task).

    Each task has exactly one writer (the replica that runs it), so events
    interleave only across tasks, never within one. A subscriber on a different
    replica replays the backlog from the stream and then follows it with
    ``XREAD BLOCK``; a subscriber on the owning replica gets the same stream
    protocol, which keeps the two paths from diverging.
    """

    def __init__(self, pool: resp.RespPool) -> None:
        self.pool = pool

    @staticmethod
    def _key(task_id: str) -> str:
        return f"{_BACKPLANE_STREAM_PREFIX}{task_id}"

    @staticmethod
    def _event(fields) -> dict | None:
        try:
            return json.loads(fields[1])
        except (ValueError, IndexError, TypeError):
            return None

    @staticmethod
    def _id(entry_id) -> str:
        return entry_id.decode() if isinstance(entry_id, bytes) else str(entry_id)

    async def write(self, task_id: str, payload: dict) -> None:
        # Two commands, one round trip: append the event, then push the key's
        # expiry out to a full window. Non-atomic (no MULTI in this client), but
        # the drainer is the only writer, so an XADD is always followed by its
        # PEXPIRE in order -- a mirror that is being written never lapses.
        await self.pool.pipeline([
            ("XADD", self._key(task_id), "MAXLEN", "~", str(_MAX_HISTORY), "*",
             "data", json.dumps(payload, ensure_ascii=False, default=str)),
            ("PEXPIRE", self._key(task_id), str(_MIRROR_TTL_S * 1000)),
        ])

    async def backlog(self, task_id: str) -> list[tuple[str, dict]]:
        rows = await self.pool.execute("XRANGE", self._key(task_id), "-", "+", "COUNT", str(_MAX_HISTORY)) or []
        out: list[tuple[str, dict]] = []
        for entry_id, fields in rows:
            event = self._event(fields)
            if event is not None:
                out.append((self._id(entry_id), event))
        return out

    async def tail(self, task_id: str, after_id: str, block_ms: int):
        rows = await self.pool.execute(
            "XREAD", "BLOCK", str(block_ms), "COUNT", "100", "STREAMS",
            self._key(task_id), after_id)
        if not rows:
            return "timeout", []
        entries = rows[0][1]
        out: list[tuple[str, dict]] = []
        for entry_id, fields in entries:
            event = self._event(fields)
            if event is not None:
                out.append((self._id(entry_id), event))
        return "ok", out

    async def peek(self, task_id: str) -> tuple[int, bool]:
        """(number of entries, whether the last entry ends the task) -- best effort."""
        rows = await self.pool.execute("XREVRANGE", self._key(task_id), "+", "-", "COUNT", "1") or []
        length = await self.pool.execute("XLEN", self._key(task_id)) or 0
        if not rows:
            return int(length), False
        event = self._event(rows[0][1])
        return int(length), bool(event and event.get("event") in ("done", "error"))

    async def holder(self, task_id: str) -> str | None:
        """The user id recorded on the stream, or None when the mirror has no owner yet.

        Ownership travels on the event payload itself (not a second redis key), so the
        same XREVRANGE that `peek` uses to answer state can answer who may read it. A
        task with no mirrored event has no holder yet -- the caller fails closed.
        """
        rows = await self.pool.execute("XREVRANGE", self._key(task_id), "+", "-", "COUNT", "1") or []
        if not rows:
            return None
        event = self._event(rows[0][1])
        return event.get("owner") if event else None


def _backplane_enabled() -> bool:
    from app.core.config import get_settings

    settings = get_settings()
    return getattr(settings, "task_bus_backend", "memory").strip().lower() == "redis"


async def _get_backplane() -> _Backplane | None:
    global _BACKPLANE, _BACKPLANE_BUILT
    if _BACKPLANE_BUILT:
        return _BACKPLANE
    _BACKPLANE_BUILT = True
    if not _backplane_enabled():
        return None
    from app.core.config import get_settings

    settings = get_settings()
    url = getattr(settings, "redis_url", "") or ""
    try:
        pool = resp.RespPool.from_url(
            url, size=int(getattr(settings, "redis_pool_size", 2) or 2),
            connect_timeout=float(getattr(settings, "redis_connect_timeout_s", 0.5) or 0.5),
            command_timeout=float(getattr(settings, "redis_timeout_s", 0.5) or 0.5))
    except (ValueError, OSError) as e:
        log.warning("TASK_BUS_BACKEND=redis but REDIS_URL is unusable (%s); the feed stays in-process", e)
        return None
    _BACKPLANE = _Backplane(pool)
    return _BACKPLANE


def _mirror(task_id: str, payload: dict) -> None:
    """Enqueue one event for the stream, off the request's critical path.

    Order is preserved by having exactly one drainer; a full queue sheds the
    mirror, never the caller. A Redis that is down degrades the mirror to a
    warn-and-drop, exactly like the cache degrades to memory.
    """
    global _MIRROR_QUEUE, _DRAINER
    if not _backplane_enabled():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    if _MIRROR_QUEUE is None:
        _MIRROR_QUEUE = asyncio.Queue(maxsize=1000)
    try:
        _MIRROR_QUEUE.put_nowait((task_id, payload))
    except asyncio.QueueFull:
        log.warning("task feed mirror queue full; dropping the mirror of %s", task_id)
        return
    if _DRAINER is None or _DRAINER.done():
        _DRAINER = loop.create_task(_drain())


async def _drain() -> None:
    backplane = await _get_backplane()
    while True:
        task_id, payload = await _MIRROR_QUEUE.get()
        if backplane is None:
            continue  # memory mode keeps working; the mirror is just absent
        try:
            await backplane.write(task_id, payload)
        except (resp.RespUnavailable, resp.RespError, OSError) as e:
            log.warning("task feed mirror write failed for %s: %s", task_id, e)


def _reset_backplane_for_tests() -> None:
    """Test hook: cancel the drainer, drop the queue, forget the pool."""
    global _BACKPLANE, _BACKPLANE_BUILT, _DRAINER, _MIRROR_QUEUE
    if _DRAINER is not None:
        _DRAINER.cancel()
    _BACKPLANE = None
    _BACKPLANE_BUILT = False
    _DRAINER = None
    _MIRROR_QUEUE = None


def new_task(kind: str, user_id: str | None = None) -> str:
    task_id = str(uuid.uuid4())
    _TASKS[task_id] = {"kind": kind, "user_id": user_id, "events": [], "done": False,
                       "created": time.time(), "waiters": set()}
    return task_id


def publish(task_id: str, event: str, data: dict) -> None:
    t = _TASKS.get(task_id)
    if not t:
        return
    payload = {"event": event, "data": data, "ts": time.time()}
    t["events"].append(payload)
    if len(t["events"]) > _MAX_HISTORY:
        t["events"].pop(0)
    for q in list(t["waiters"]):
        q.put_nowait(payload)
    # The in-memory feed and the frames built from it keep the exact three keys they
    # always had. Ownership rides only on the mirrored copy, as a top-level field next
    # to event/data/ts; the SSE generator forwards `event` and `data`, never this field,
    # so a foreign replica can settle ownership without changing a single wire frame.
    _mirror(task_id, {**payload, "owner": t["user_id"]})


def finish(task_id: str, ok: bool, result: dict | None = None, error: str | None = None) -> None:
    publish(task_id, "done" if ok else "error",
            {"result": result, "error": error} if not ok else {"result": result})
    t = _TASKS.get(task_id)
    if t:
        t["done"] = True


def is_done(task_id: str) -> bool:
    t = _TASKS.get(task_id)
    return bool(t and t["done"])


def state(task_id: str) -> dict | None:
    t = _TASKS.get(task_id)
    if not t:
        return None
    return {"kind": t["kind"], "done": t["done"], "events": len(t["events"]),
            "last": t["events"][-1] if t["events"] else None}


async def astate(task_id: str) -> dict | None:
    """The async-native peek: memory first, then best effort at the stream.

    A synchronous caller cannot suspend on the wire, so `state()` answers from
    memory only; callers running in the loop (the API handlers) use this and get
    the foreign task's answer from the mirror when memory says nothing.
    """
    t = _TASKS.get(task_id)
    if t is not None:
        return {"kind": t["kind"], "done": t["done"], "events": len(t["events"]),
                "last": t["events"][-1] if t["events"] else None}
    backplane = await _get_backplane()
    if backplane is None:
        return None
    try:
        length, done = await backplane.peek(task_id)
    except Exception:
        return None
    if length == 0:
        return None
    return {"kind": "task", "done": done, "events": length, "last": None}


async def ais_done(task_id: str) -> bool:
    """The async-native form of `is_done`, with the same memory-first order."""
    t = _TASKS.get(task_id)
    if t is not None:
        return bool(t["done"])
    backplane = await _get_backplane()
    if backplane is None:
        return False
    try:
        _, done = await backplane.peek(task_id)
    except Exception:
        return False
    return bool(done)


async def subscribe(task_id: str, heartbeat_s: float = 15.0) -> AsyncIterator[dict]:
    if _backplane_enabled():
        backplane = await _get_backplane()
        if backplane is not None:
            async for ev in _subscribe_backplane(backplane, task_id, heartbeat_s):
                yield ev
            return
    async for ev in _subscribe_memory(task_id, heartbeat_s):
        yield ev


async def _subscribe_memory(task_id: str, heartbeat: float) -> AsyncIterator[dict]:
    t = _TASKS.get(task_id)
    if not t:
        yield {"event": "error", "data": {"error": "task not found"}}
        return
    queue: asyncio.Queue = asyncio.Queue()
    for ev in list(t["events"]):
        yield ev
    t["waiters"].add(queue)
    try:
        while True:
            if t["done"] and queue.empty():
                break
            try:
                ev = await asyncio.wait_for(queue.get(), timeout=heartbeat)
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": {}}
                continue
            yield ev
            if ev.get("event") in ("done", "error"):
                break
    finally:
        t["waiters"].discard(queue)


async def _subscribe_backplane(backplane: _Backplane, task_id: str,
                                heartbeat: float) -> AsyncIterator[dict]:
    """The stream protocol every subscriber follows when the mirror is on.

    Backlog first (everything the owner wrote, in order), then XREAD BLOCK on
    the tail. A task that already finished replays its terminal event and
    returns without blocking forever; a task nobody ever owned answers with an
    empty backlog and an error rather than a hung stream.
    """
    try:
        backlog = await backplane.backlog(task_id)
    except (resp.RespUnavailable, resp.RespError, OSError) as e:
        log.warning("task feed backlog read failed for %s: %s", task_id, e)
        async for ev in _subscribe_memory(task_id, heartbeat):
            yield ev
        return

    if not backlog:
        if task_id in _TASKS:
            # The mirror is on but this task never got far enough to write; the
            # memory path is the direct line, and it knows this task exists.
            async for ev in _subscribe_memory(task_id, heartbeat):
                yield ev
            return
        yield {"event": "error", "data": {"error": "task not found"}}
        return

    last_id = "0-0"
    for entry_id, event in backlog:
        last_id = entry_id
        yield event
        if event.get("event") in ("done", "error"):
            return

    block_ms = max(1, int(heartbeat * 1000))
    while True:
        try:
            status, rows = await backplane.tail(task_id, last_id, block_ms)
        except (resp.RespUnavailable, resp.RespError, OSError) as e:
            log.warning("task feed tail read failed for %s: %s", task_id, e)
            yield {"event": "error", "data": {"error": "task feed unavailable"}}
            return
        if status != "ok":
            yield {"event": "ping", "data": {}}
            continue
        for entry_id, event in rows:
            last_id = entry_id
            yield event
            if event.get("event") in ("done", "error"):
                return


def owner(task_id: str) -> str | None:
    """Whose task this is, as recorded when it was made -- or None if no task or no owner.

    The synchronous, memory-only form: it answers the owning replica without touching
    the wire. Deliberately not a field of `state()`: that projection is the body
    `GET /internal/tasks/{id}` answers with, and an owner id belongs in a decision,
    not in a response. Callers in the event loop use `aowner()` to also reach a task
    whose owner is a different replica.
    """
    t = _TASKS.get(task_id)
    return None if t is None else t["user_id"]


async def aowner(task_id: str) -> str | None:
    """The async-native owner lookup: memory first, then best effort at the mirror.

    A request that lands on the replica which owns the task is answered locally, so
    the common path adds no network round-trip. A request routed elsewhere reads the
    owner the owning replica wrote onto the stream. Unresolvable (no mirror, redis
    down, no owner recorded) stays None and the caller fails closed, exactly as it
    did before the mirror existed.
    """
    local = owner(task_id)
    if task_id in _TASKS or local is not None:
        return local
    backplane = await _get_backplane()
    if backplane is None:
        return None
    try:
        return await backplane.holder(task_id)
    except Exception:
        return None


def gc_old_tasks(max_age_s: float = 3600) -> None:
    cutoff = time.time() - max_age_s
    for k in [k for k, v in _TASKS.items() if v["created"] < cutoff and v["done"]]:
        _TASKS.pop(k, None)


def sse(event: dict) -> str:
    # "message" is the SSE spec's own default event name, so a payload that
    # carries no "event" key still emits a well-formed frame instead of raising
    name = (event.get("event") if isinstance(event, dict) else None) or "message"
    data = event.get("data") if isinstance(event, dict) else None
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
