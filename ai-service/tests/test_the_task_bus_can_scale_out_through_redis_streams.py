"""The task feed can fan out through a Redis stream, and stay correct when it does.

Epic 131, the scale-out path for the SSE task bus. The in-process feed already
works (same events, same order, one writer per task); this file pins the mirror:
``TASK_BUS_BACKEND=redis`` turns every ``publish`` into an ``XADD`` on
``careeros:tasks:<id>`` (MAXLEN ~400), and a subscriber -- anywhere -- can replay
the backlog and follow the tail with ``XREAD BLOCK``.

Measured here rather than claimed:

* the mirror preserves order across a burst of publishes;
* a subscriber that never saw the publishing replica replays the whole backlog
  in order and stops at the terminal event;
* a task that already finished answers without hanging on ``XREAD BLOCK``;
* a task nobody ever owned answers with an error, not a hung stream;
* with Redis down the bus behaves exactly like the pre-backplane one
  (memory feed, same order, same terminal semantics);
* the drainer never crashes the caller: a full queue sheds the mirror, the
  request path is untouched.
"""

import asyncio
import json
import time

import pytest

from app.core import resp, taskbus
from app.core.config import get_settings

USER = "00000000-0000-0000-0000-0000000000aa"


def _bulk(value: bytes) -> bytes:
    return b"$%d\r\n%s\r\n" % (len(value), value)


def _entry(entry_id: bytes, value: bytes) -> bytes:
    return b"*2\r\n" + _bulk(entry_id) + b"*2\r\n" + _bulk(b"data") + _bulk(value)


class FakeStreamsRedis:
    """Enough RESP for the mirror; blocks exactly as long as the client asked."""

    def __init__(self) -> None:
        self.streams: dict[bytes, list[tuple[bytes, bytes]]] = {}
        self.seq = 0
        self.commands: list[list[bytes]] = []
        self.block_calls = 0
        self._tasks: set[asyncio.Task] = set()
        self.host = "127.0.0.1"
        self.port = 0

    async def start(self) -> None:
        self.server = await asyncio.start_server(self._handle, self.host, 0)
        self.port = self.server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        self.server.close()
        await self.server.wait_closed()
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        task = asyncio.current_task()
        if task is not None:
            self._tasks.add(task)
        buffer = b""
        try:
            while True:
                chunk = await reader.read(65536)
                if not chunk:
                    return
                buffer += chunk
                while True:
                    if not buffer:
                        break
                    parsed = _take_command(buffer)
                    if parsed is None:
                        break
                    args, buffer = parsed
                    self.commands.append(args)
                    writer.write(await self._apply(args))
                    await writer.drain()
        except (ConnectionResetError, BrokenPipeError):
            return

    async def _apply(self, args: list[bytes]) -> bytes:
        name = args[0].upper()
        if name == b"PING":
            return b"+PONG\r\n"
        if name == b"XADD":
            key = args[1]
            index = 2
            maxlen = None
            if args[index].upper() == b"MAXLEN":
                # MAXLEN ~ 400 -- the project's own history cap, mirrored into the stream
                assert args[index + 1] == b"~"
                maxlen = int(args[index + 2])
                index += 3
            assert args[index] == b"*"
            index += 1
            field = args[index]
            value = args[index + 1]
            self.seq += 1
            entry_id = f"{self.seq:013d}-0".encode()
            stream = self.streams.setdefault(key, [])
            stream.append((entry_id, value))
            if maxlen is not None and len(stream) > maxlen:
                del stream[: len(stream) - maxlen]
            return _bulk(entry_id)
        if name == b"XRANGE":
            key = args[1]
            rows = self.streams.get(key, [])
            out = [b"*%d\r\n" % len(rows)]
            for entry_id, value in rows:
                out.append(_entry(entry_id, value))
            return b"".join(out)
        if name == b"XREVRANGE":
            key = args[1]
            rows = self.streams.get(key, [])
            count = int(args[-1]) if len(args) >= 5 and args[-2].upper() == b"COUNT" else 1
            tail = rows[-count:][::-1] if count else []
            out = [b"*%d\r\n" % len(tail)]
            for entry_id, value in tail:
                out.append(_entry(entry_id, value))
            return b"".join(out)
        if name == b"XLEN":
            return b":%d\r\n" % len(self.streams.get(args[1], []))
        if name == b"XREAD":
            self.block_calls += 1
            index = 1
            block_ms = 0
            while args[index].upper() in (b"BLOCK", b"COUNT"):
                value = int(args[index + 1])
                if args[index].upper() == b"BLOCK":
                    block_ms = value
                index += 2
            assert args[index].upper() == b"STREAMS"
            key, after = args[index + 1], args[index + 2]
            after_seq = int(after.split(b"-", 1)[0])
            rows = self.streams.get(key, [])
            fresh = [(entry_id, value) for entry_id, value in rows
                     if int(entry_id.split(b"-", 1)[0]) > after_seq]
            if not fresh:
                if block_ms:
                    await asyncio.sleep(block_ms / 1000)
                return b"*-1\r\n"  # Redis answers a BLOCK timeout with a null array
            out = [b"*1\r\n", b"*2\r\n", _bulk(key), b"*%d\r\n" % len(fresh)]
            for entry_id, value in fresh:
                out.append(_entry(entry_id, value))
            return b"".join(out)
        return b"-ERR unknown command\r\n"


def _take_command(buffer: bytes):
    if not buffer.startswith(b"*"):
        raise AssertionError(f"client sent something that is not an array: {buffer[:40]!r}")
    end = buffer.find(b"\r\n")
    if end < 0:
        return None
    count = int(buffer[1:end])
    pos = end + 2
    args: list[bytes] = []
    for _ in range(count):
        if len(buffer) < pos + 2 or buffer[pos:pos + 1] != b"$":
            return None
        line_end = buffer.find(b"\r\n", pos)
        if line_end < 0:
            return None
        length = int(buffer[pos + 1:line_end])
        start = line_end + 2
        if len(buffer) < start + length + 2:
            return None
        args.append(buffer[start:start + length])
        pos = start + length + 2
    return args, buffer[pos:]


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


def _task(kind: str = "ingest", user_id: str = USER) -> str:
    return taskbus.new_task(kind, user_id)


async def _drained(streams: FakeStreamsRedis, task_id: str, want: int, timeout_s: float = 2.0) -> None:
    """Wait until the mirror has landed `want` events for the task, or fail."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        key = f"careeros:tasks:{task_id}".encode()
        if len(streams.streams.get(key, [])) >= want:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"mirror never drained: {len(streams.streams.get(f'careeros:tasks:{task_id}'.encode(), []))} entries")


async def test_a_burst_publishes_into_the_stream_in_order(redis_env):
    streams = redis_env
    task_id = _task()
    for i in range(5):
        taskbus.publish(task_id, "status", {"step": f"s{i}", "state": "active"})
    await _drained(streams, task_id, 5)

    key = f"careeros:tasks:{task_id}".encode()
    entries = streams.streams[key]
    events = [json.loads(v)["data"]["step"] for _, v in entries]
    assert events == ["s0", "s1", "s2", "s3", "s4"]
    # The mirror carries whole events, not a lossy projection.
    bodies = [json.loads(v) for _, v in entries]
    assert all(body["event"] == "status" for body in bodies)
    assert [body["ts"] for body in bodies] == sorted(body["ts"] for body in bodies)


async def test_a_foreign_replica_replays_the_backlog_and_stops_at_done(redis_env):
    streams = redis_env
    task_id = _task()
    for i in range(3):
        taskbus.publish(task_id, "status", {"step": f"s{i}", "state": "active"})
    taskbus.finish(task_id, True, result={"ok": True})
    await _drained(streams, task_id, 4)

    # A different replica never saw this task: forget it locally.
    taskbus._TASKS.pop(task_id, None)

    events = [ev async for ev in taskbus.subscribe(task_id, heartbeat_s=0.05)]

    kinds = [ev["event"] for ev in events]
    assert kinds == ["status", "status", "status", "done"]
    assert events[-1]["data"]["result"] == {"ok": True}
    # The terminal event ends the stream; no tail wait happens.
    assert streams.block_calls == 0


async def test_an_unknown_task_answers_with_an_error(redis_env):
    events = [ev async for ev in taskbus.subscribe("no-such-task", heartbeat_s=0.05)]
    assert events == [{"event": "error", "data": {"error": "task not found"}}]


async def test_with_redis_down_the_bus_behaves_like_memory(redis_env, monkeypatch):
    # Point the backplane at a port nobody is listening on.
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:1/0")
    get_settings.cache_clear()
    taskbus._reset_backplane_for_tests()
    task_id = _task()
    taskbus.publish(task_id, "status", {"step": "still-works", "state": "active"})
    taskbus.finish(task_id, True, result={"ok": True})

    events = [ev async for ev in taskbus.subscribe(task_id, heartbeat_s=0.05)]

    assert [ev["event"] for ev in events] == ["status", "done"]
    assert taskbus.is_done(task_id)


async def test_the_mirror_queue_sheds_instead_of_blocking_the_caller(redis_env, monkeypatch):
    """A full mirror queue drops the mirror, never the request."""
    task_id = _task()
    want = asyncio.Queue(maxsize=1)
    want.put_nowait(("other-task", {"event": "status", "data": {}, "ts": 1}))
    monkeypatch.setattr(taskbus, "_MIRROR_QUEUE", want)
    # A drainer that never empties the queue, so the next publish must shed.
    monkeypatch.setattr(taskbus, "_DRAINER", None)

    taskbus.publish(task_id, "status", {"step": "survives", "state": "active"})

    # The memory feed is whole even though the mirror sheds the event.
    assert taskbus.state(task_id)["events"] == 1
    assert taskbus.state(task_id)["last"]["data"]["step"] == "survives"


async def test_a_foreign_task_reads_state_and_done_from_the_stream(redis_env):
    streams = redis_env
    task_id = _task()
    taskbus.publish(task_id, "status", {"step": "s0", "state": "active"})
    taskbus.finish(task_id, True, result={"ok": True})
    await _drained(streams, task_id, 2)
    taskbus._TASKS.pop(task_id, None)  # the foreign replica's view

    assert await taskbus.ais_done(task_id) is True
    state = await taskbus.astate(task_id)
    assert state is not None
    assert state["done"] is True
    assert state["events"] == 2

