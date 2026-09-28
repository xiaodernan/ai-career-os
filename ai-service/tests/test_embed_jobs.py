"""Tests for the job-embedding ops script (PRD §4.1).

Covers `job_embedding_text`, the one pure part of the script — it decides what the
model actually sees, so a regression there silently degrades every job vector
without failing anything — and the service loop that now runs the same backfill
periodically, which is what keeps a job created mid-session from staying invisible
to vector recall. The DB and provider halves of a pass are exercised by running the
script against the stack.
"""

from __future__ import annotations

import asyncio
import logging

import pytest

from app.ops import embed_jobs as embed_jobs_module
from app.ops.embed_jobs import embed_loop, job_embedding_text


def test_labels_every_section_it_includes():
    text = job_embedding_text({
        "title": "AI Agent 平台工程师",
        "location": "上海",
        "remote_type": "hybrid",
        "employment_type": "full_time",
        "skills": ["Python", "PostgreSQL", "RAG"],
        "description": "Build the agent platform.",
        "requirements": ["5y backend", "LLM experience"],
        "nice_to_have": ["pgvector"],
        "responsibilities": ["Own retrieval quality"],
    })
    for label in ("Title:", "Location:", "Work type:", "Skills:", "Description:",
                  "Requirements:", "Nice to have:", "Responsibilities:"):
        assert label in text, f"{label} missing from embedding text"
    # The values must survive, not just the labels.
    assert "AI Agent 平台工程师" in text
    assert "Python, PostgreSQL, RAG" in text
    assert "5y backend, LLM experience" in text
    assert "hybrid full_time" in text


def test_omits_absent_sections_rather_than_emitting_empty_labels():
    text = job_embedding_text({"title": "Backend Engineer"})
    assert text == "Title: Backend Engineer"
    # An empty label would still consume prompt/embedding budget and skew the vector.
    assert "Requirements:" not in text
    assert "Location:" not in text


def test_handles_a_job_with_nothing_usable():
    # The caller skips these (and counts them) rather than embedding noise.
    assert job_embedding_text({}) == ""
    assert job_embedding_text({"title": None, "skills": [], "description": "   "}) == ""


def test_blank_entries_inside_arrays_are_dropped():
    text = job_embedding_text({"title": "SRE", "skills": ["Go", "", "  ", "Kubernetes"]})
    assert "Skills: Go, Kubernetes" in text


def test_company_salary_and_age_are_excluded():
    # Deliberate: they are filters, not semantics — including them makes similar
    # roles at different employers look unrelated.
    text = job_embedding_text({
        "title": "Backend Engineer",
        "company": "TechCorp",
        "salary_min": 300000,
        "salary_max": 450000,
        "posted_at": "2026-09-01",
    })
    assert text == "Title: Backend Engineer"


# ------------------------------------------------- the loop the service runs


async def test_the_loop_passes_repeatedly_and_ends_when_asked(monkeypatch):
    """First pass immediately (it doubles as the startup backfill), then on the tick."""
    calls = 0
    stop = asyncio.Event()

    async def fake_embed_jobs():
        nonlocal calls
        calls += 1
        if calls >= 3:
            stop.set()

    monkeypatch.setattr(embed_jobs_module, "embed_jobs", fake_embed_jobs)
    await embed_loop(interval=0.001, stop=stop)
    assert calls == 3


async def test_a_broken_pass_is_logged_and_the_next_tick_still_runs(monkeypatch, caplog):
    """Provider down costs recall for a minute, never the service."""
    calls = 0
    stop = asyncio.Event()

    async def flaky():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("no embedding provider configured")
        stop.set()

    monkeypatch.setattr(embed_jobs_module, "embed_jobs", flaky)
    with caplog.at_level(logging.WARNING, logger="ops.embed_jobs"):
        await embed_loop(interval=0.001, stop=stop)
    assert calls == 2
    assert "job embedding pass failed" in caplog.text


async def test_cancelling_the_task_ends_the_loop_mid_sleep(monkeypatch):
    """Shutdown cancels the task; a loop that ignored it would hold the app open."""
    calls = 0

    async def instant():
        nonlocal calls
        calls += 1
        return {"embedded": 0}

    monkeypatch.setattr(embed_jobs_module, "embed_jobs", instant)
    task = asyncio.create_task(embed_loop(interval=60))
    await asyncio.sleep(0)  # let the immediate first pass finish and the loop park
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert calls == 1
