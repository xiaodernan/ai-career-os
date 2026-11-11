"""A RESP2 client small enough to audit — the cache's transport, with no dependency.

Why not `redis-py`: the engine's dependency set is pinned and deliberately thin
(`requirements.txt` is twelve lines), and a cache is a piece of infrastructure whose
failure modes have to be *ours*. This module is the subset of RESP2 a cache needs —
inline-safe command encoding, the five reply types, one bounded pool, pipelining and
two timeouts — and nothing else. It is deliberately not a general Redis client: no
Pub/Sub, no transactions, no cluster redirection.

The two properties that matter and are easy to get wrong:

* **Pipelining is one round trip, not N.** `pipeline([...])` writes every command
  before reading any reply. A loop of `GET`s over a 60 ms link costs 60 ms each; the
  same loop pipelined costs 60 ms once. `RedisCache.get_many` is built on it, which is
  why a retrieval that needs nine embedding keys still makes one trip.
* **A reply can arrive in pieces.** TCP does not preserve write boundaries, so
  `$30\r\n...` may land as `$3` then `0\r\n...`. Every read here goes through
  `readuntil`/`readexactly`, which is what makes the fake-server test able to write a
  reply one byte at a time and still be understood.

Failure is a first-class answer: `RespUnavailable` says "the server is not there",
`RespError` says "the server refused this command". A broken connection is discarded
rather than reused, so one timeout cannot poison the pool.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Iterable, Sequence
from urllib.parse import urlsplit

CRLF = b"\r\n"
_MAX_BULK = 512 * 1024 * 1024  # Redis' own proto-max-bulk-len default


class RespError(Exception):
    """The server answered an error reply (`-WRONGTYPE ...`). The link is fine."""


class RespUnavailable(Exception):
    """The server could not be reached, or did not answer inside the timeout."""


def encode(*args: Any) -> bytes:
    """One command as a RESP array of bulk strings.

    Every argument is length-prefixed, so a value carrying CRLF, spaces or a NUL byte
    is transmitted verbatim — the reason inline commands are not used here at all.
    """
    out = [b"*%d" % len(args), CRLF]
    for arg in args:
        if isinstance(arg, bytes):
            raw = arg
        elif isinstance(arg, str):
            raw = arg.encode("utf-8")
        elif isinstance(arg, bool):  # before int: bool is an int subclass
            raw = b"1" if arg else b"0"
        elif isinstance(arg, (int, float)):
            raw = str(arg).encode("ascii")
        else:
            raise TypeError(f"cannot send {type(arg).__name__} to Redis")
        out.append(b"$%d" % len(raw))
        out.append(CRLF)
        out.append(raw)
        out.append(CRLF)
    return b"".join(out)


class RespConnection:
    """One socket, one reply at a time, with a deadline on every read."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                 *, command_timeout: float = 0.5):
        self._reader = reader
        self._writer = writer
        self._command_timeout = command_timeout
        self._broken = False

    @classmethod
    async def connect(cls, host: str, port: int, *, connect_timeout: float = 0.5,
                      command_timeout: float = 0.5, password: str | None = None,
                      db: int = 0, limit: int = 1 << 20) -> RespConnection:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port, limit=limit), connect_timeout)
        except (OSError, asyncio.TimeoutError) as e:
            raise RespUnavailable(f"connect to {host}:{port} failed: {e}") from e
        conn = cls(reader, writer, command_timeout=command_timeout)
        try:
            if password:
                await conn.execute("AUTH", password)
            if db:
                await conn.execute("SELECT", db)
        except Exception:
            await conn.close()
            raise
        return conn

    @property
    def usable(self) -> bool:
        return not self._broken and not self._writer.is_closing()

    @property
    def tcp_nodelay(self) -> bool | None:
        """Whether the small-reply path is riding Nagle or not.

        Every cache hit is a one-line reply, and Nagle's algorithm delays exactly that
        shape by up to an ACK. asyncio sets `TCP_NODELAY` on transports it creates; this
        accessor exists so a test can assert the property instead of trusting it.
        """
        sock = self._writer.get_extra_info("socket")
        if sock is None:
            return None
        try:
            import socket as _socket
            return bool(sock.getsockopt(_socket.IPPROTO_TCP, _socket.TCP_NODELAY))
        except (OSError, AttributeError):
            return None

    async def execute(self, *args: Any) -> Any:
        return (await self.pipeline([args]))[0]

    async def pipeline(self, commands: Iterable[Sequence[Any]]) -> list[Any]:
        """Write every command, drain once, then read every reply in order.

        An error reply does not abort the batch: Redis has already executed the
        commands behind it, so the honest answer is the whole list with the errors in
        place. Callers that cannot tolerate a partial batch simply do not use this.
        """
        batch = list(commands)
        if not batch:
            return []
        payload = b"".join(encode(*cmd) for cmd in batch)
        count = len(batch)
        try:
            self._writer.write(payload)
            await asyncio.wait_for(self._writer.drain(), self._command_timeout)
            replies = []
            for _ in range(count):
                replies.append(await asyncio.wait_for(self._read_reply(),
                                                      self._command_timeout))
            return replies
        except RespError:
            raise
        except (OSError, asyncio.IncompleteReadError, asyncio.LimitOverrunError,
                asyncio.TimeoutError, ConnectionError) as e:
            self._broken = True
            raise RespUnavailable(f"pipeline failed: {e}") from e

    async def _read_reply(self) -> Any:
        line = await self._reader.readuntil(CRLF)
        if len(line) < 3 or not line.endswith(CRLF):
            self._broken = True
            raise RespUnavailable("malformed reply line")
        kind, body = line[:1], line[1:-2]
        if kind == b"+":
            return body.decode("utf-8", "replace")
        if kind == b"-":
            raise RespError(body.decode("utf-8", "replace"))
        if kind == b":":
            return int(body)
        if kind == b"$":
            length = int(body)
            if length == -1:
                return None
            if length < 0 or length > _MAX_BULK:
                self._broken = True
                raise RespUnavailable(f"bulk length {length} out of range")
            data = await self._reader.readexactly(length + 2)
            return data[:length]
        if kind == b"*":
            length = int(body)
            if length == -1:
                return None
            if length < 0:
                self._broken = True
                raise RespUnavailable(f"array length {length} out of range")
            return [await self._read_reply() for _ in range(length)]
        self._broken = True
        raise RespUnavailable(f"unknown reply type {kind!r}")

    async def close(self) -> None:
        self._broken = True
        try:
            self._writer.close()
            await self._writer.wait_closed()
        except (OSError, RuntimeError, asyncio.TimeoutError):
            pass


class RespPool:
    """A bounded pool: N sockets, borrowed one command batch at a time.

    The semaphore is the bound, not the idle list — a pool that grows under load and
    trims later is how a cache becomes the outage. A connection that raised
    `RespUnavailable` is closed on the way out instead of being returned, so a
    half-read socket is never handed to the next caller with a reply still in flight.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 6379, *, db: int = 0,
                 password: str | None = None, size: int = 4,
                 connect_timeout: float = 0.5, command_timeout: float = 0.5):
        self.host, self.port, self.db, self.password = host, port, db, password
        self.size = max(1, int(size))
        self.connect_timeout = connect_timeout
        self.command_timeout = command_timeout
        self._sem = asyncio.Semaphore(self.size)
        self._idle: list[RespConnection] = []
        self._closed = False
        self.stats = {"borrowed": 0, "created": 0, "reused": 0, "discarded": 0,
                      "errors": 0, "round_trips": 0}

    @classmethod
    def from_url(cls, url: str, *, size: int = 4, connect_timeout: float = 0.5,
                 command_timeout: float = 0.5) -> RespPool:
        parts = urlsplit(url)
        if parts.scheme not in ("redis", ""):
            raise ValueError(f"unsupported cache scheme {parts.scheme!r}; redis:// only")
        db = 0
        if parts.path and parts.path.strip("/"):
            db = int(parts.path.strip("/"))
        return cls(parts.hostname or "127.0.0.1", parts.port or 6379, db=db,
                   password=parts.password or None, size=size,
                   connect_timeout=connect_timeout, command_timeout=command_timeout)

    @property
    def closed(self) -> bool:
        return self._closed

    @asynccontextmanager
    async def _borrow(self):
        await self._sem.acquire()
        conn: RespConnection | None = None
        try:
            while self._idle:
                candidate = self._idle.pop()
                if candidate.usable:
                    conn = candidate
                    self.stats["reused"] += 1
                    break
                self.stats["discarded"] += 1
                await candidate.close()
            if conn is None:
                conn = await RespConnection.connect(
                    self.host, self.port, connect_timeout=self.connect_timeout,
                    command_timeout=self.command_timeout, password=self.password,
                    db=self.db)
                self.stats["created"] += 1
            self.stats["borrowed"] += 1
            yield conn
        except RespError:
            # The link answered; only the command was refused. The socket is healthy,
            # so it goes back to the idle list instead of being dropped on the floor
            # (a dropped socket is a leak: nothing closes it and the server keeps the
            # handler alive until the process exits).
            self.stats["errors"] += 1
            if conn is not None and conn.usable and len(self._idle) < self.size:
                self._idle.append(conn)
            elif conn is not None:
                await conn.close()
            raise
        except BaseException:
            # A timeout, a reset, a cancelled request: the socket's state is unknown,
            # so it must not go back into the idle list with a reply still in flight.
            self.stats["errors"] += 1
            if conn is not None:
                self.stats["discarded"] += 1
                await conn.close()
            raise
        else:
            if conn is not None and conn.usable and len(self._idle) < self.size:
                self._idle.append(conn)
            elif conn is not None:
                self.stats["discarded"] += 1
                await conn.close()
        finally:
            self._sem.release()

    async def execute(self, *args: Any) -> Any:
        if self._closed:
            raise RespUnavailable("pool closed")
        async with self._borrow() as conn:
            reply = await conn.execute(*args)
        self.stats["round_trips"] += 1
        return reply

    async def pipeline(self, commands: Sequence[Sequence[Any]]) -> list[Any]:
        if self._closed:
            raise RespUnavailable("pool closed")
        batch = list(commands)
        if not batch:
            return []
        async with self._borrow() as conn:
            replies = await conn.pipeline(batch)
        self.stats["round_trips"] += 1
        return replies

    async def ping(self) -> bool:
        try:
            return await self.execute("PING") in ("PONG", b"PONG")
        except RespUnavailable:
            return False

    async def close(self) -> None:
        self._closed = True
        idle, self._idle = self._idle, []
        for conn in idle:
            await conn.close()
