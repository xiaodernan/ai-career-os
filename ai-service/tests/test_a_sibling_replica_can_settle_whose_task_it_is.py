"""A task's owner is now decidable on any replica, not only the one that made it.

Epic 131 mirrored the task feed into a Redis stream so a subscriber on any node can
replay and follow a task another node owns. The one thing that still pinned a task to
its home node was the ownership gate: `owner()` read only the in-process dictionary,
so a request routed to a sibling replica answered 404 -- indistinguishable from a task
that never existed. The backend relay absorbed that by trying every door until one
stopped refusing, but a refusal is a slow, ambiguous way to ask "who owns this?".

Now the owner travels with the mirrored events (a top-level field beside event/data/ts),
and `aowner()` memory-firsts on the home node, then reads the mirror elsewhere. The
in-process feed and the frames the browser receives are byte-for-byte unchanged: the
SSE generator forwards `event` and `data` only, so ownership never widens a wire frame.

What this file measures, rather than asserts in prose:

* the home replica answers from memory without a new wire command;
* a sibling that never saw the task resolves the same owner from the mirror;
* the sibling still refuses a stranger and an ownerless task -- the gate got a new
  reader, not a looser answer;
* with the mirror down, a sibling fails closed instead of guessing;
* the ownership field stays off the frames `subscribe()` yields and off `state()`.
"""

import asyncio
import json
import time

import pytest
from fastapi import HTTPException

from app.api import tasks
from app.core import taskbus
from app.core.config import get_settings
from app.core.deps import Ctx

OWNER = "11111111-1111-1111-1111-111111111111"
STRANGER = "22222222-2222-2222-2222-222222222222"


def _load_fixture(name: str):
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_scaleout = _load_fixture("test_the_task_bus_can_scale_out_through_redis_streams.py")
FakeStreamsRedis = _scaleout.FakeStreamsRedis


@pytest.fixture
async def streams():
    server = FakeStreamsRedis()
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
async def redis_env(streams, monkeypatch):
    """Point the bus's backplane at the fake, and forget it cleanly afterwards."""
    monkeypatch.setenv("TASK_BUS_BACKEND", "redis")
    monkeypatch.setenv("REDIS_URL", f"redis://127.0.0.1:{streams.port}/0")
    get_settings.cache_clear()
    taskbus._reset_backplane_for_tests()
    yield streams
    get_settings.cache_clear()
    taskbus._reset_backplane_for_tests()


async def _drained(streams, task_id: str, want: int, timeout_s: float = 2.0) -> None:
    deadline = time.monotonic() + timeout_s
    key = f"careeros:tasks:{task_id}".encode()
    while time.monotonic() < deadline:
        if len(streams.streams.get(key, [])) >= want:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"mirror never drained {want} events for {task_id}")


def _as_sibling(task_id: str) -> None:
    """Forget a task locally, as a replica that never ran it would."""
    taskbus._TASKS.pop(task_id, None)


async def _refused(route, task_id: str, user_id: str):
    """Return the HTTPException a route raises for `user_id`, or None when it answers."""
    try:
        await route(task_id, Ctx(user_id=user_id))
    except HTTPException as exc:
        return exc
    return None


# ------------------------------------------------------- the home replica: no new work

async def test_the_home_replica_answers_from_memory_without_a_new_wire_command(redis_env):
    streams = redis_env
    task_id = taskbus.new_task("agent_chat", OWNER)
    taskbus.publish(task_id, "token", {"text": "hi"})
    await _drained(streams, task_id, 1)
    before = len([c for c in streams.commands if c[0].upper() == b"XREVRANGE"])

    assert await taskbus.aowner(task_id) == OWNER

    after = len([c for c in streams.commands if c[0].upper() == b"XREVRANGE"])
    assert after == before, (
        "the replica that owns the task asked the wire who owns it: the common path must "
        "stay in memory, or every SSE request grows a network round-trip"
    )
    assert taskbus.owner(task_id) == OWNER, "the synchronous memory-only form must not drift"


# ------------------------------------------------------- the sibling replica: same answer

async def test_a_sibling_that_never_saw_the_task_resolves_the_owner_from_the_mirror(redis_env):
    streams = redis_env
    task_id = taskbus.new_task("agent_chat", OWNER)
    taskbus.publish(task_id, "token", {"text": "hi"})
    taskbus.finish(task_id, True, result={"answer": "ok"})
    await _drained(streams, task_id, 2)
    _as_sibling(task_id)

    assert taskbus.owner(task_id) is None, "the precondition: the sibling has no local record"
    assert await taskbus.aowner(task_id) == OWNER, (
        "the mirror carries the owner on its events; a sibling must read it there"
    )


async def test_the_sibling_serves_the_owner_and_still_refuses_a_stranger(redis_env):
    streams = redis_env
    task_id = taskbus.new_task("agent_chat", OWNER)
    taskbus.publish(task_id, "token", {"text": "hi"})
    taskbus.finish(task_id, True, result={"answer": "ok"})
    await _drained(streams, task_id, 2)
    _as_sibling(task_id)

    # The state route answers the rightful owner from the mirror-backed peek.
    state = await tasks.task_state(task_id, Ctx(user_id=OWNER))
    assert state is not None and state["done"] is True

    # The refusal is not softened by the new reader: a stranger gets the exact answer
    # a missing task gets, on both routes and on the spelling the relay actually calls.
    for route in (tasks.task_state, tasks.task_stream, tasks.task_stream_alias):
        foreign = await _refused(route, task_id, STRANGER)
        missing = await _refused(route, "33333333-3333-3333-3333-333333333333", STRANGER)
        assert foreign is not None and missing is not None
        assert (foreign.status_code, foreign.detail) == (missing.status_code, missing.detail), (
            f"{route.__name__} distinguishes a foreign task from an absent one on the sibling: "
            "that difference is what a guessing attack needs"
        )
        assert foreign.status_code == 404


# ------------------------------------------------------- fail-closed, not softened

async def test_a_task_with_no_recorded_owner_is_nobodys_even_with_a_mirror(redis_env):
    streams = redis_env
    task_id = taskbus.new_task("agent_chat")  # no user_id, as a producer bug leaves
    taskbus.publish(task_id, "token", {"text": "orphan"})
    await _drained(streams, task_id, 1)
    _as_sibling(task_id)

    assert await taskbus.aowner(task_id) is None, (
        "an ownerless task reached the mirror; that must not become anybody's task"
    )
    assert await _refused(tasks.task_state, task_id, OWNER) is not None


async def test_with_the_mirror_down_a_sibling_fails_closed(redis_env, monkeypatch):
    streams = redis_env
    task_id = taskbus.new_task("agent_chat", OWNER)
    taskbus.publish(task_id, "token", {"text": "hi"})
    await _drained(streams, task_id, 1)

    # A sibling whose mirror is unreachable cannot settle ownership.
    _as_sibling(task_id)
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:1/0")
    get_settings.cache_clear()
    taskbus._reset_backplane_for_tests()

    assert await taskbus.aowner(task_id) is None, (
        "an unreachable mirror must not be read as 'no owner, let everyone in' or as "
        "a guess -- the gate fails closed exactly as it did before the mirror existed"
    )
    assert await _refused(tasks.task_state, task_id, OWNER) is not None


# ------------------------------------------------------- zero wire/frame drift

async def test_the_owner_field_never_reaches_a_frame_or_the_state_projection(redis_env):
    streams = redis_env
    task_id = taskbus.new_task("agent_chat", OWNER)
    taskbus.publish(task_id, "token", {"text": "hi"})
    taskbus.finish(task_id, True, result={"answer": "ok"})
    await _drained(streams, task_id, 2)

    # The mirrored payload carries the owner ...
    entries = streams.streams[f"careeros:tasks:{task_id}".encode()]
    bodies = [json.loads(v) for _, v in entries]
    assert all(body.get("owner") == OWNER for body in bodies)

    # ... but neither the memory feed's frames nor `state()` expose it.
    for frame in taskbus.state(task_id)["last"], *taskbus._TASKS[task_id]["events"]:
        assert set(frame) == {"event", "data", "ts"}, (
            f"{sorted(frame)}: the in-process feed gained a field the browser would see"
        )
    assert set(taskbus.state(task_id)) == {"kind", "done", "events", "last"}

    # A foreign subscriber's frames are the same three keys: subscribe yields the
    # mirrored event, and the SSE generator forwards only event/data, never owner.
    _as_sibling(task_id)
    events = [ev async for ev in taskbus.subscribe(task_id)]
    assert events, "the sibling replayed nothing"
    wire = [{"event": ev["event"], "data": ev["data"]} for ev in events]
    assert wire[-1]["event"] == "done"
    assert all(set(item) == {"event", "data"} for item in wire), (
        "the frame the browser gets widened with the ownership field"
    )
