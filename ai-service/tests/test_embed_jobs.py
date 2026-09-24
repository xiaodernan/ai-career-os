"""Tests for the job-embedding ops script (PRD §4.1).

Covers `job_embedding_text`, the one pure part of the script — it decides what the
model actually sees, so a regression there silently degrades every job vector
without failing anything. The DB and provider halves are exercised by running the
script against the stack.
"""

from __future__ import annotations

from app.ops.embed_jobs import job_embedding_text


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
