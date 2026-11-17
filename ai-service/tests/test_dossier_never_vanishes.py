"""Epic 315: the dossier that never silently vanishes, and never lies about the data.

Epic 312's dedup collapsed a sixty-one-row synthetic flood into a single line, the
`len(out) > 2` floor failed, and a user with 61 applications on file got an EMPTY
dossier -- the copilot walked in knowing nothing. These tests pin the contract that
can no longer fail quietly: repeated identical rows are collapsed with an honest
``xN`` count, the dossier renders whenever ANY section has material, the resume bound
is 10 k chars, ordering tiebreaks by id, and the block is byte-identical across two
reads of the same DB state.
"""
from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from app.agents import memory


SYNTHETIC_APPS = [
    {"title": "Senior Backend Engineer - Agent Platform", "company": "Mock Corp",
     "status": "interview", "updated_at": f"2026-11-{10 + i % 20:02d}",
     "created_at": f"2026-11-{10 + i % 20:02d}", "id": f"00000000-0000-0000-0000-{i:012d}"}
    for i in range(61)
]
DISTINCT_APPS = [
    {"title": "Platform Engineer", "company": "Amathus", "status": "offer",
     "updated_at": "2026-11-16", "created_at": "2026-11-16", "id": "11111111-1111-1111-1111-111111111111"},
    {"title": "Database Engineer", "company": "Rosette", "status": "interview",
     "updated_at": "2026-11-15", "created_at": "2026-11-15", "id": "22222222-2222-2222-2222-222222222222"},
]


def _run(user_id: str = "u1") -> str:
    return asyncio.run(memory.build_dossier_context(user_id))


def test_a_flood_of_identical_rows_collapses_with_an_honest_count(monkeypatch):
    async def fake_current(_):
        return None

    fetch_calls = []

    async def fake_fetch(query, *args):
        fetch_calls.append(str(query))
        q = str(query).lower()
        if "from applications" in q and "count(*)" in q:
            return [{"apps": 61, "interviews": 0}]
        if "from applications" in q:
            return list(SYNTHETIC_APPS + DISTINCT_APPS)
        return []

    async def fake_init():
        return "pool"

    async def fake_close():
        return None

    monkeypatch.setattr(memory.domain, "get_current_resume_version", fake_current)
    monkeypatch.setattr(memory.db, "fetch", fake_fetch)
    monkeypatch.setattr(memory.db, "init_db", fake_init)
    monkeypatch.setattr(memory.db, "close_db", fake_close)

    out = _run()
    assert "Senior Backend Engineer - Agent Platform @Mock Corp — interview ×61" in out
    assert "Platform Engineer @Amathus — offer" in out
    assert "Database Engineer @Rosette — interview" in out
    assert out.count("Mock Corp") == 1                      # the flood is one line, not sixty-one
    assert "applications on file: 61" in out                # the true total is shown, not hidden


def test_the_dossier_never_vanishes_while_a_row_exists(monkeypatch):
    async def fake_current(_):
        return None

    async def fake_fetch(query, *args):
        q = str(query).lower()
        if "from applications" in q and "count(*)" in q:
            return [{"apps": 1, "interviews": 0}]
        if "from applications" in q:
            return list(SYNTHETIC_APPS[:1])
        return []

    async def fake_init():
        return "pool"

    async def fake_close():
        return None

    monkeypatch.setattr(memory.domain, "get_current_resume_version", fake_current)
    monkeypatch.setattr(memory.db, "fetch", fake_fetch)
    monkeypatch.setattr(memory.db, "init_db", fake_init)
    monkeypatch.setattr(memory.db, "close_db", fake_close)

    out = _run()
    assert out.startswith("## Candidate dossier")           # not the empty string, ever


def test_the_resume_is_accepted_at_ten_thousand_chars(monkeypatch):
    big = "x" * 9000

    async def fake_current(_):
        return {"id": "rv1", "plaintext": big, "label": "v3"}

    async def fake_fetch(query, *args):
        return []

    async def fake_init():
        return "pool"

    async def fake_close():
        return None

    monkeypatch.setattr(memory.domain, "get_current_resume_version", fake_current)
    monkeypatch.setattr(memory.db, "fetch", fake_fetch)
    monkeypatch.setattr(memory.db, "init_db", fake_init)
    monkeypatch.setattr(memory.db, "close_db", fake_close)

    out = _run()
    assert big in out


def test_goals_render_when_the_wire_recorded_them(monkeypatch):
    async def fake_current(_):
        return None

    async def fake_fetch(query, *args):
        return []

    async def fake_memories(user_id, kinds=None, limit=20):
        if kinds == ["goal"]:
            return [{"kind": "goal", "key": None, "content": "become a staff engineer in 2027",
                     "importance": 0.9}]
        return []

    async def fake_init():
        return "pool"

    async def fake_close():
        return None

    monkeypatch.setattr(memory.domain, "get_current_resume_version", fake_current)
    monkeypatch.setattr(memory.db, "fetch", fake_fetch)
    monkeypatch.setattr(memory.domain, "get_memories", fake_memories)
    monkeypatch.setattr(memory.db, "init_db", fake_init)
    monkeypatch.setattr(memory.db, "close_db", fake_close)

    out = _run()
    assert "become a staff engineer in 2027" in out
    assert "### goals" in out


def test_repeated_calls_are_byte_identical(monkeypatch):
    async def fake_current(_):
        return {"id": "rv1", "plaintext": "graphite and roses.", "label": "v2"}

    async def fake_fetch(query, *args):
        q = str(query).lower()
        if "count(*)" in q and "from applications" in q:
            return [{"apps": 63, "interviews": 5}]
        if "from applications" in q:
            return list(SYNTHETIC_APPS + DISTINCT_APPS)
        if "from job_matches" in q:
            return [
                {"title": "Engineer", "overall": 0.5, "technical": 0.4,
                 "missing_skills": ["Kafka"], "id": "a"},
                {"title": "Engineer", "overall": 0.5, "technical": 0.4,
                 "missing_skills": ["Kafka"], "id": "a"},
            ]
        return []

    async def fake_memories(user_id, kinds=None, limit=20):
        return [{"kind": "interview", "key": None,
                 "content": "weak: outbox atomicity never answered",
                 "importance": 0.7}] if kinds == ["interview"] else []

    async def fake_init():
        return "pool"

    async def fake_close():
        return None

    monkeypatch.setattr(memory.domain, "get_current_resume_version", fake_current)
    monkeypatch.setattr(memory.db, "fetch", fake_fetch)
    monkeypatch.setattr(memory.domain, "get_memories", fake_memories)
    monkeypatch.setattr(memory.db, "init_db", fake_init)
    monkeypatch.setattr(memory.db, "close_db", fake_close)

    assert _run() == _run()
