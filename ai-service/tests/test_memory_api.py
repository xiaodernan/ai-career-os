"""The memory surface: the row maths and the ownership rule (PRD §17).

No DB: `domain.list_memories` / `update_memory` / `delete_memory` are exercised through
a fake pool, so what is asserted is the SQL they build and the scoping they apply.
"""

import asyncio

import app.core.db as db
from app.db import domain


class Row(dict):
    """Stand-in for asyncpg.Record."""
    __getattr__ = dict.get


class _Conn:
    def __init__(self, row, rows, capture):
        self.row = row
        self.rows = rows
        self.capture = capture

    async def fetch(self, query, *args):
        self.capture.append(("fetch", query, args))
        return [Row(r) for r in self.rows]

    async def fetchrow(self, query, *args):
        self.capture.append(("fetchrow", query, args))
        return Row(self.row) if self.row else None


class FakePool:
    """`db.*` does `async with get_pool().acquire() as conn`, so the fake has to speak
    that protocol rather than answering the high-level helper."""

    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows if rows is not None else ([row] if row else [])
        self.capture: list = []

    def acquire(self):
        outer = self

        class _Ctx:
            async def __aenter__(self):
                return _Conn(outer.row, outer.rows, outer.capture)

            async def __aexit__(self, *exc):
                return False

        return _Ctx()


def _install(monkeypatch, pool):
    monkeypatch.setattr(db, "get_pool", lambda: pool)


# ------------------------------- list ---------------------------------------


def test_list_memories_returns_the_id_and_the_freshness_order(monkeypatch):
    pool = FakePool(rows=[
        {"id": "m2", "kind": "skill", "key": "kafka", "content": "Kafka at scale",
         "importance": 0.8, "source": "conversation",
         "created_at": None, "updated_at": None},
        {"id": "m1", "kind": "profile", "key": "h", "content": "Backend engineer",
         "importance": 0.9, "source": "manual",
         "created_at": None, "updated_at": None},
    ])
    _install(monkeypatch, pool)

    rows = asyncio.run(domain.list_memories("u"))
    assert [r["id"] for r in rows] == ["m2", "m1"]
    # A list a user reads to find the wrong sentence must order by what changed last.
    _kind, sql, args = pool.capture[0]
    assert "updated_at DESC" in sql
    assert "id, kind, key, content" in sql, "the id is what a correction targets"
    # It is not the prompt reader: that one caps at 20, this one at 100 by default.
    assert "LIMIT $3" in sql, "the limit is bound, not interpolated"
    assert args == ("u", None, 100)


def test_list_memories_filters_by_kind_without_interpolation(monkeypatch):
    pool = FakePool(rows=[])
    _install(monkeypatch, pool)
    asyncio.run(domain.list_memories("u", ["skill", "goal"]))
    _kind, sql, args = pool.capture[0]
    assert "kind = ANY($2)" in sql, "kinds must be bound, never interpolated"
    assert args == ("u", ["skill", "goal"], 100)


# ------------------------------- update -------------------------------------


def test_a_patch_rebinds_parameters_in_order(monkeypatch):
    """Both values are optional, so the placeholder has to follow whichever set is
    being written -- a fixed $3/$4 would bind nothing when only one field is sent."""
    pool = FakePool(row={"id": "m1", "kind": "skill", "key": "k", "content": "new",
                         "importance": 0.4, "source": "conversation",
                         "created_at": None, "updated_at": None})
    _install(monkeypatch, pool)

    row = asyncio.run(domain.update_memory("u", "m1", content="new", importance=0.4))
    assert row["content"] == "new" and row["importance"] == 0.4
    _kind, sql, args = pool.capture[0]
    assert sql.startswith("UPDATE user_memories")
    assert "content=$3" in sql and "importance=$4" in sql
    assert args == ("m1", "u", "new", 0.4)


def test_a_one_field_patch_does_not_leave_a_hole_for_the_other(monkeypatch):
    pool = FakePool(row={"id": "m1", "kind": "skill", "key": "k", "content": "x",
                         "importance": 0.4, "source": "conversation",
                         "created_at": None, "updated_at": None})
    _install(monkeypatch, pool)
    asyncio.run(domain.update_memory("u", "m1", importance=0.4))
    _kind, sql, args = pool.capture[0]
    assert "content=$3" not in sql, "an unset field must not bind a placeholder"
    assert "importance=$3" in sql
    assert args == ("m1", "u", 0.4)


def test_an_empty_patch_reads_the_row_instead_of_writing_it(monkeypatch):
    """Lowering importance and fixing the content are two different corrections; a caller
    that wants one must not have to send the other, and a no-op update is not a write."""
    pool = FakePool(row={"id": "m1", "kind": "skill", "key": "k", "content": "x",
                         "importance": 0.4, "source": "conversation",
                         "created_at": None, "updated_at": None})
    _install(monkeypatch, pool)
    row = asyncio.run(domain.update_memory("u", "m1"))
    assert row["content"] == "x"
    _kind, sql, _args = pool.capture[0]
    assert sql.startswith("SELECT"), "an empty patch must answer from a read, not a write"


def test_update_is_scoped_to_the_owner(monkeypatch):
    """The WHERE is the whole ownership rule: an id belonging to somebody else updates
    nothing and reports that as a miss."""
    pool = FakePool(row=None)
    _install(monkeypatch, pool)
    assert asyncio.run(domain.update_memory("someone-else", "m1", content="x")) is None
    _kind, sql, args = pool.capture[0]
    assert "user_id=$2::uuid" in sql
    assert args[1] == "someone-else", "the caller's id is what is bound, not the row's"


# ------------------------------- delete -------------------------------------


def test_delete_answers_from_a_returned_row_not_a_status_string(monkeypatch):
    """asyncpg's `execute` answers "DELETE 0" for a row that was not there -- a non-empty
    string, therefore truthy. An existence question cannot be answered by a truthiness
    check on prose."""
    pool = FakePool(row=None)
    _install(monkeypatch, pool)
    assert asyncio.run(domain.delete_memory("u", "m1")) is False
    _kind, sql, args = pool.capture[0]
    assert "RETURNING id" in sql
    assert args == ("m1", "u")

    pool2 = FakePool(row={"id": "m1"})
    _install(monkeypatch, pool2)
    assert asyncio.run(domain.delete_memory("u", "m1")) is True


def test_delete_is_scoped_to_the_owner(monkeypatch):
    pool = FakePool(row=None)
    _install(monkeypatch, pool)
    asyncio.run(domain.delete_memory("not-me", "m1"))
    _kind, sql, args = pool.capture[0]
    assert "user_id=$2::uuid" in sql
    assert args == ("m1", "not-me")
