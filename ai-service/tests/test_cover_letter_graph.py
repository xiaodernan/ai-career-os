"""Epic 287: the cover letter rides the bounded StateGraph.

The resume tailor got retrieve -> draft -> verify -> render in Epic 269; the
cover letter kept its single ask() until now — the most fabrication-prone
surface in the app went unaudited. This file pins the graph spine, the
deterministic veto, and the exhausted-draft fallback: a letter that still
fails verification renders with its rejection recorded, never silently.
"""

import re

import pytest

from app.features import cover_letter
from app.providers.base import LLMResponse, Usage


def _source() -> str:
    return (
        "CANDIDATE SKILLS: Python, Rust, Kubernetes\n"
        "resume: Led migration of 12 services to Kubernetes; cut deploy time by 55%; "
        "team of 3 engineers; revenue impact $2.4M.\n"
        "JD title: Staff Engineer — platform\n"
        "goal: The role owns developer experience for 200 engineers.\n"
    )


def test_numbers_in_reads_every_number_including_percents():
    got = cover_letter._numbers_in("12 services, 55% faster, $2.4M raised")
    assert got == {"12", "55%", "2.4"}


def test_numbers_in_empty_string():
    assert cover_letter._numbers_in("") == set()


def test_verifier_accepts_a_grounded_letter():
    letter = (
        "Hello; I led migration of 12 services to Kubernetes and cut deploy time by 55%, "
        "working with a team of 3 engineers. The platform charter speaks directly to the "
        "200 engineers this role serves."
    )
    assert cover_letter.verify_no_fabrication(_source(), letter) is None


def test_verifier_flags_an_invented_skill():
    reason = cover_letter.verify_no_fabrication(
        _source(), "I love Kubernetes and I also know Redis at depth."
    )
    assert reason is not None
    assert "redis" in reason.lower()


def test_verifier_flags_an_invented_number():
    reason = cover_letter.verify_no_fabrication(
        _source(), "I personally shipped 900 features last quarter."
    )
    assert reason is not None
    assert "900" in reason


def test_verifier_accepts_numbers_present_in_sources():
    letter = "I migrated 12 services to Kubernetes with 3 engineers and saved 55%."
    assert cover_letter.verify_no_fabrication(_source(), letter) is None


def test_source_text_collects_everything_the_letter_may_ground_itself_in():
    s = cover_letter._source_text(
        {"profile": {"name": "Ann"}}, "resume text", {"title": "Staff"},
        {"name": "Acme"}, "goal statement",
    )
    for needle in ("Ann", "resume text", "Staff", "Acme", "goal statement"):
        assert needle in s


async def test_the_graph_retries_once_then_renders_with_the_rejection_recorded(monkeypatch):
    """First draft invents a number; the retry is clean; the render records zero rejections."""
    letter_bad = "I shipped 900 features last quarter."
    letter_good = "I migrated 12 services to Kubernetes with 3 engineers."
    calls: list[str] = []

    class FakeResp:
        def __init__(self, text):
            self.text = text
            self.model = "mock-model"

    async def fake_retrieve(*args, **kwargs):
        return {"context_block": "context", "evidence": [{"text": "Kubernetes", "source": "cv"}]}

    async def fake_ask(req, **kwargs):
        prompt = req.messages[-1].content
        if "VERIFIER REJECTION" in prompt:
            calls.append("retry")
            return FakeResp(letter_good)
        calls.append("draft")
        return FakeResp(letter_bad)

    monkeypatch.setattr(cover_letter, "retrieve", fake_retrieve)
    monkeypatch.setattr(cover_letter, "ask", fake_ask)

    out = await cover_letter.generate(
        {"profile": {"name": "Ann"}}, _source(), {"title": "Staff Engineer",
        "requiredSkills": [{"name": "Kubernetes"}]},
        {"name": "Acme"}, "grow the platform", user_id="u1", run_id=None)

    assert out["letter"] == letter_good
    assert out["sources"] == [{"text": "Kubernetes", "source": "cv"}]
    assert calls == ["draft", "retry"]


async def test_the_graph_renders_anyway_when_the_retry_still_fails(monkeypatch):
    """A letter that fails twice renders with its rejection list, never silently."""
    letter_bad = "I shipped 900 features last quarter."

    class FakeResp:
        def __init__(self, text):
            self.text = text
            self.model = "mock-model"

    async def fake_retrieve(*args, **kwargs):
        return {"context_block": "context", "evidence": []}

    calls2: list[str] = []

    async def fake_ask(req, **kwargs):
        calls2.append("retry" if "VERIFIER REJECTION" in req.messages[-1].content else "draft")
        return FakeResp(letter_bad)

    monkeypatch.setattr(cover_letter, "retrieve", fake_retrieve)
    monkeypatch.setattr(cover_letter, "ask", fake_ask)

    out = await cover_letter.generate(
        {"profile": {"name": "Ann"}}, "short source", {"title": "Staff Engineer",
        "requiredSkills": [{"name": "Kubernetes"}]},
        {"name": "Acme"}, "grow the platform", user_id="u1", run_id=None)

    assert out["letter"] == letter_bad
    assert calls2 == ["draft", "retry"]
    assert set(out) == {"letter", "sources", "mode", "model"}


async def test_sources_and_shape_are_unchanged_for_callers(monkeypatch):
    """The frontend reads letter/sources/mode/model; the graph adds only `verification`."""
    letter = "I migrated 12 services to Kubernetes with 3 engineers."

    class FakeResp:
        def __init__(self):
            self.text = letter
            self.model = "mock-model"

    async def fake_retrieve(*args, **kwargs):
        return {"context_block": "context", "evidence": [{"text": "K8s"}]}

    async def fake_ask(req, **kwargs):
        return FakeResp()

    monkeypatch.setattr(cover_letter, "retrieve", fake_retrieve)
    monkeypatch.setattr(cover_letter, "ask", fake_ask)

    out = await cover_letter.generate(
        {"profile": {"name": "Ann"}}, _source(), {"title": "Staff Engineer",
        "requiredSkills": [{"name": "Kubernetes"}]},
        {"name": "Acme"}, "grow", user_id="u1", run_id=None)

    assert set(out) == {"letter", "sources", "mode", "model"}
    assert out["sources"] == [{"text": "K8s"}]
    assert out["mode"] == "generate"
