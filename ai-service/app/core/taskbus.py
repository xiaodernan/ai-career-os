"""In-process task event bus for AI pipeline progress + SSE streaming.

Single-instance by design (documented tradeoff); Redis backplane is the scale-out path.
Persisted state lives in documents.status / agent_runs; this bus is only the live feed.
"""

import asyncio
import json
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

_TASKS: dict[str, dict[str, Any]] = {}
_MAX_HISTORY = 400


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


async def subscribe(task_id: str, heartbeat_s: float = 15.0) -> AsyncIterator[dict]:
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
                ev = await asyncio.wait_for(queue.get(), timeout=heartbeat_s)
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": {}}
                continue
            yield ev
            if ev.get("event") in ("done", "error"):
                break
    finally:
        t["waiters"].discard(queue)


def gc_old_tasks(max_age_s: float = 3600) -> None:
    cutoff = time.time() - max_age_s
    for k in [k for k, v in _TASKS.items() if v["created"] < cutoff and v["done"]]:
        _TASKS.pop(k, None)


def sse(event: dict) -> str:
    return f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False, default=str)}\n\n"
