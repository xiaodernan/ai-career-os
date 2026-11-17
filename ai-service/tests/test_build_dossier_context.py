"""Epic 310: the dossier is byte-stable across calls.

The provider-side prefix cache keys on byte-identical bytes. If `build_dossier_context`
returns different strings for the same user between two calls, the prefix cache misses
on every turn — and the user's experience is that the cache never fires. This test
proves the dossier is deterministic for the same DB state.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import patch

import pytest

from app.agents import memory


def test_dossier_is_deterministic(monkeypatch):
    class Row(dict):
        pass

    current_rv = {"id": "rv1", "plaintext": "rose petals and graphite.", "label": "v2", "score": None, "kind": "tailored"}
    apps = [
        {"title": "Senior Backend Engineer", "company": "Rosette", "status": "interview", "updated_at": "2026-11-15", "created_at": "2026-11-15"},
        {"title": "Platform Engineer", "company": "Amathus", "status": "offer", "updated_at": "2026-11-16", "created_at": "2026-11-16"},
    ]
    matches = [
        {"title": "Engineer, Data", "overall": 0.82, "technical": 0.7, "missing_skills": ["Kafka", "Reliability"]},
    ]

    async def fake_current(_):
        return current_rv

    async def fake_fetch(query, *args):
        q = str(query).lower()
        if "from applications" in q:
            return apps
        if "from job_matches" in q:
            return matches
        return []

    async def fake_init():
        return "pool"

    async def fake_close():
        return None

    monkeypatch.setattr(memory.domain, "get_current_resume_version", fake_current)
    monkeypatch.setattr(memory.db, "fetch", fake_fetch)
    monkeypatch.setattr(memory.db, "init_db", fake_init)
    monkeypatch.setattr(memory.db, "close_db", fake_close)

    async def run():
        return await memory.build_dossier_context("u1")

    first = asyncio.run(run())
    second = asyncio.run(run())
    assert first == second, "same DB state produced two different dossier strings"
    assert "rose petals and graphite." in first
    assert "Rosette" in first
    assert "Reliability" in first
    print("dossier bytes:", len(first), "— deterministic")


def test_dossier_empty_when_no_user_data(monkeypatch):
    async def fake_current(_):
        return None

    async def fake_fetch(*_):
        return []

    monkeypatch.setattr(memory.domain, "get_current_resume_version", fake_current)
    monkeypatch.setattr(memory.db, "fetch", fake_fetch)

    async def run():
        return await memory.build_dossier_context("u1")

    assert asyncio.run(run()) == ""


def test_dossier_does_not_invent_entries(monkeypatch):
    async def fake_current(_):
        return {"id": "rv1", "plaintext": "see bio.", "label": "v1"}

    async def fake_fetch(query, *args):
        if "FROM job_matches" in query:
            return [{"title": "Engineer", "overall": 0.42, "technical": 0.4, "missing_skills": []}]
        return []

    monkeypatch.setattr(memory.domain, "get_current_resume_version", fake_current)
    monkeypatch.setattr(memory.db, "fetch", fake_fetch)

    async def run():
        return await memory.build_dossier_context("u1")

    out = asyncio.run(run())
    assert "see bio." in out
    assert "Engineer" in out
    assert "Reliability" not in out  # nothing invented, nothing silently filled in
