"""Epic 118 — the cache's transport, pinned against a server that misbehaves on purpose.

A Redis client is easy to write and hard to write *correctly*, because the interesting
cases are all transport cases: a reply split across packets, an error reply that leaves
the socket healthy, a server that stops answering, a pool that must not hand a
half-read socket to the next caller. None of those can be produced by a healthy Redis,
so this file runs its own server and makes it do them.

Measured here rather than claimed:

* a three-command pipeline reaches the server in **one** read (one round trip);
* the same three commands sent one at a time reach it in three reads;
* a reply written one byte at a time is parsed as one reply;
* `TCP_NODELAY` is set on the socket asyncio opened (the accessor exists so this is a
  property of the transport, not a hope about Nagle);
* an error reply does not cost the connection, and a timeout does.
"""

from __future__ import annotations

import asyncio
import socket

import pytest

from app.core import resp


class FakeRedis:
    """Enough Redis for this file, plus a few ways to be difficult."""

    def __init__(self) -> None:
        self.data: dict[bytes, bytes] = {}
        self.reads = 0            # read() calls that returned bytes
        self.commands: list[list[bytes]] = []
        self.delay = 0.0         # before the first reply
        self.fragment = False    # write the reply one byte at a time
        self._server: asyncio.AbstractServer | None = None
        self._tasks: set[asyncio.Task] = set()
        self.port = 0

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _handle(self, reader: asyncio.StreamReader,
                      writer: asyncio.StreamWriter) -> None:
        task = asyncio.current_task()
        if task is not None:
            self._tasks.add(task)
        buffer = b""
        try:
            while True:
                # Give a pipelining client the chance to land every command in one
                # write before the first read, so "how many reads" measures batching
                # rather than scheduler luck.
                if not buffer:
                    await asyncio.sleep(0.03 if self.reads == 0 else 0.0)
                chunk = await reader.read(65536)
                if not chunk:
                    return
                self.reads += 1
                buffer += chunk
                while True:
                    if not buffer:
                        break
                    parsed = _take_command(buffer)
                    if parsed is None:
                        break
                    args, buffer = parsed
                    self.commands.append(args)
                    reply = self._apply(args)
                    await self._write(writer, reply)
        except (ConnectionResetError, asyncio.CancelledError):
            return
        finally:
            if task is not None:
                self._tasks.discard(task)
            try:
                writer.close()
            except (OSError, RuntimeError):
                pass

    async def _write(self, writer: asyncio.StreamWriter, payload: bytes) -> None:
        if self.delay:
            await asyncio.sleep(self.delay)
            self.delay = 0.0
        if self.fragment:
            for i in range(len(payload)):
                writer.write(payload[i:i + 1])
                await writer.drain()
                await asyncio.sleep(0)
        else:
            writer.write(payload)
            await writer.drain()

    def _apply(self, args: list[bytes]) -> bytes:
        name = args[0].upper()
        if name == b"PING":
            return b"+PONG\r\n"
        if name == b"SET":
            self.data[args[1]] = args[2]
            return b"+OK\r\n"
        if name == b"GET":
            value = self.data.get(args[1])
            return b"$-1\r\n" if value is None else _bulk(value)
        if name == b"MGET":
            out = [b"*%d\r\n" % (len(args) - 1)]
            for key in args[1:]:
                value = self.data.get(key)
                out.append(b"$-1\r\n" if value is None else _bulk(value))
            return b"".join(out)
        if name == b"DEL":
            removed = len([k for k in args[1:] if self.data.pop(k, None) is not None])
            return b":%d\r\n" % removed
        if name == b"INCR":
            value = int(self.data.get(args[1], b"0")) + 1
            self.data[args[1]] = str(value).encode()
            return b":%d\r\n" % value
        if name == b"EXPIRE":
            return b":1\r\n"
        if name == b"ECHO":
            return _bulk(args[1])
        if name == b"BOOM":
            return b"-WRONGTYPE Operation against a key holding the wrong kind of value\r\n"
        return b"-ERR unknown command\r\n"


def _bulk(value: bytes) -> bytes:
    return b"$%d\r\n%s\r\n" % (len(value), value)


def _take_command(buffer: bytes):
    """Parse one RESP array of bulk strings off the front, or None when incomplete."""
    if not buffer.startswith(b"*"):
        raise AssertionError(f"client sent something that is not an array: {buffer[:40]!r}")
    end = buffer.find(b"\r\n")
    if end < 0:
        return None
    try:
        count = int(buffer[1:end])
    except ValueError:
        raise AssertionError(f"bad array header: {buffer[:20]!r}")
    pos = end + 2
    args: list[bytes] = []
    for _ in range(count):
        if len(buffer) < pos + 2 or buffer[pos:pos + 1] != b"$":
            return None
        line_end = buffer.find(b"\r\n", pos)
        if line_end < 0:
            return None
        try:
            length = int(buffer[pos + 1:line_end])
        except ValueError:
            raise AssertionError(f"bad bulk header: {buffer[pos:pos + 20]!r}")
        start = line_end + 2
        if len(buffer) < start + length + 2:
            return None
        args.append(buffer[start:start + length])
        pos = start + length + 2
    return args, buffer[pos:]


@pytest.fixture
async def fake():
    server = FakeRedis()
    await server.start()
    yield server
    await server.stop()


# ------------------------------------------------------------------ the protocol

async def test_a_reply_split_across_packets_is_one_reply(fake):
    fake.fragment = True
    pool = resp.RespPool("127.0.0.1", fake.port, size=1, command_timeout=2.0)
    try:
        assert await pool.execute("SET", "greeting", "hello world") == "OK"
        assert await pool.execute("GET", "greeting") == b"hello world"
    finally:
        await pool.close()


async def test_a_value_carrying_crlf_and_nul_survives_verbatim(fake):
    pool = resp.RespPool("127.0.0.1", fake.port, size=1)
    payload = "line1\r\nline2\x00tail"
    try:
        await pool.execute("SET", "k", payload)
        assert await pool.execute("GET", "k") == payload.encode()
    finally:
        await pool.close()


async def test_an_error_reply_keeps_the_connection(fake):
    pool = resp.RespPool("127.0.0.1", fake.port, size=1)
    try:
        with pytest.raises(resp.RespError) as excinfo:
            await pool.execute("BOOM")
        assert "WRONGTYPE" in str(excinfo.value)
        # The link answered; only the command was refused. The next command reuses it.
        assert await pool.execute("PING") == "PONG"
        assert pool.stats["discarded"] == 0
        assert pool.stats["created"] == 1
    finally:
        await pool.close()


async def test_null_bulk_and_null_array_are_none_not_empty(fake):
    pool = resp.RespPool("127.0.0.1", fake.port, size=1)
    try:
        assert await pool.execute("GET", "missing") is None
        assert await pool.execute("MGET", "missing", "also-missing") == [None, None]
    finally:
        await pool.close()


# ---------------------------------------------------------------- the round trips

async def test_a_pipeline_is_one_round_trip_and_a_loop_is_three(fake):
    pool = resp.RespPool("127.0.0.1", fake.port, size=1)
    try:
        await pool.pipeline([("SET", "a", "1"), ("SET", "b", "2"), ("SET", "c", "3")])
        assert fake.reads == 1, (
            f"three pipelined commands reached the server in {fake.reads} reads; a "
            "pipeline that writes command-by-command is three round trips wearing the "
            "name")
        assert len(fake.commands) == 3

        fake.reads = 0
        await pool.execute("GET", "a")
        await pool.execute("GET", "b")
        await pool.execute("GET", "c")
        assert fake.reads == 3, (
            "three sequential commands reached the server in one read, which would mean "
            "the batching assertion above measures nothing")
    finally:
        await pool.close()


async def test_one_connection_is_reused_across_executes(fake):
    pool = resp.RespPool("127.0.0.1", fake.port, size=1)
    try:
        for _ in range(20):
            assert await pool.execute("PING") == "PONG"
        assert pool.stats["created"] == 1, (
            f"20 commands opened {pool.stats['created']} sockets; a pool that reconnects "
            "per command is not a pool")
        assert pool.stats["reused"] == 19
    finally:
        await pool.close()


async def test_the_socket_asks_for_no_nagle_delay():
    pool = resp.RespPool("127.0.0.1", 16380, size=1, connect_timeout=0.5)
    if not await pool.ping():
        await pool.close()
        pytest.skip("no Redis on 127.0.0.1:16380 to inspect")
    try:
        async with pool._borrow() as conn:
            assert conn.tcp_nodelay is True, (
                "the cache's socket is riding Nagle: every one-line reply would wait for "
                "an ACK it does not need")
    finally:
        await pool.close()


# ------------------------------------------------------------------- the failures

async def test_a_timeout_is_unavailable_and_the_socket_is_discarded(fake):
    fake.delay = 0.5
    pool = resp.RespPool("127.0.0.1", fake.port, size=1, command_timeout=0.1)
    try:
        with pytest.raises(resp.RespUnavailable):
            await pool.execute("PING")
        assert pool.stats["discarded"] >= 1, (
            "a socket whose reply never arrived was kept in the idle list; the next "
            "caller would read this call's late reply as its own")
        # The server is healthy again; a discarded socket means a new one answers.
        fake.delay = 0.0
        assert await pool.execute("PING") == "PONG"
        assert pool.stats["created"] == 2
    finally:
        await pool.close()


async def test_connect_to_nothing_is_unavailable_not_a_stack_trace():
    pool = resp.RespPool("127.0.0.1", 1, size=1, connect_timeout=0.2)
    with pytest.raises(resp.RespUnavailable):
        await pool.execute("PING")
    await pool.close()


async def test_a_closed_pool_refuses_rather_than_hanging():
    pool = resp.RespPool("127.0.0.1", 1, size=1)
    await pool.close()
    with pytest.raises(resp.RespUnavailable):
        await pool.execute("PING")


# -------------------------------------------------------------------- the address

def test_from_url_reads_host_port_and_db():
    pool = resp.RespPool.from_url("redis://cache.internal:6380/3", size=2)
    assert (pool.host, pool.port, pool.db) == ("cache.internal", 6380, 3)
    assert resp.RespPool.from_url("redis://:secret@h:6379/0").password == "secret"


def test_a_non_redis_scheme_is_refused_at_construction():
    with pytest.raises(ValueError):
        resp.RespPool.from_url("rediss://secure:6379/0")
    with pytest.raises(ValueError):
        resp.RespPool.from_url("http://not-a-cache:6379/0")


@pytest.mark.parametrize("args,expected", [
    (("PING",), b"*1\r\n$4\r\nPING\r\n"),
    (("SET", "k", "v"), b"*3\r\n$3\r\nSET\r\n$1\r\nk\r\n$1\r\nv\r\n"),
    (("GET", b"\x00\xff"), b"*2\r\n$3\r\nGET\r\n$2\r\n\x00\xff\r\n"),
    (("EXPIRE", "k", 30), b"*3\r\n$6\r\nEXPIRE\r\n$1\r\nk\r\n$2\r\n30\r\n"),
])
def test_encoding_is_length_prefixed(args, expected):
    assert resp.encode(*args) == expected


def test_a_type_that_is_not_a_command_argument_is_refused():
    with pytest.raises(TypeError):
        resp.encode("SET", {"not": "scalar"})


# --------------------------------------------------------------- the real server

async def test_the_client_against_the_compose_redis():
    """The protocol above is pinned by a fake; this proves it against the real thing."""
    pool = resp.RespPool.from_url("redis://127.0.0.1:16380/0", size=2,
                                  connect_timeout=0.5, command_timeout=1.0)
    if not await pool.ping():
        await pool.close()
        pytest.skip("the dev Redis (127.0.0.1:16380) is not running")
    key = "careeros:test:resp"
    try:
        assert await pool.execute("SET", key, "value", "EX", 30) == "OK"
        assert await pool.execute("GET", key) == b"value"
        assert await pool.execute("MGET", key, key + ":absent") == [b"value", None]
        assert await pool.execute("INCR", key + ":n") == 1
        assert await pool.execute("DEL", key, key + ":n") == 2
    finally:
        await pool.close()
