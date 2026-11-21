"""Epic 354 — the Career Chronicle: a grounded, chaptered epic over the reader's own search.

The same discipline as every second voice: a bounded StateGraph, a deterministic
per-chapter verifier, and silence on failure. No invented milestone, company or outcome.
"""
import pytest

from app.features import career_chronicle as cc


@pytest.mark.asyncio
async def test_chronicle_returns_a_book_shape(monkeypatch):
    """The engine answers the book envelope, in the reader's language."""
    async def fake_ask_json(req, *, user_id=None, run_id=None, agent=None, kind=None):
        if "skeptical reader" in str(req.messages):
            return {"issues": []}
        return {"chapters": [{"key": "opening", "title": "The Opening Move",
                              "prose": "The ledger shows 3 dated entries marking the start.",
                              "loreEntries": ["Anchored to 3 in the ledger."], "anchor": "3"}],
                "epilogue": "Three entries remain on record."}
    monkeypatch.setattr(cc, "ask_json", fake_ask_json)
    out = await cc.career_chronicle(
        {"events": [{"title": "Applied", "at": "2026-11-10"}], "milestones": {"total": 3}},
        locale="zh")
    assert set(out) == {"chapters", "epilogue", "locale", "issues", "struck", "empty"}
    assert out["locale"] == "zh"
    assert isinstance(out["chapters"], list)
    assert out["empty"] is False


@pytest.mark.asyncio
async def test_ungrounded_chapters_are_struck(monkeypatch):
    """A chapter whose prose cites a digit the payload does not carry is dropped."""
    async def fake_ask_json(req, *, user_id=None, run_id=None, agent=None, kind=None):
        if "skeptical reader" in str(req.messages):
            return {"issues": []}
        return {"chapters": [
            {"key": "bad", "title": "Invented", "prose": "The reader applied to 99 jobs.",
             "loreEntries": [], "anchor": "99"},
        ], "epilogue": ""}
    monkeypatch.setattr(cc, "ask_json", fake_ask_json)
    out = await cc.career_chronicle({"events": [{"title": "Applied"}], "milestones": {"total": 3}})
    assert out["chapters"] == []
    assert out["struck"] >= 1
    assert out["empty"] is True


@pytest.mark.asyncio
async def test_silent_llm_is_an_empty_book_not_a_guess(monkeypatch):
    """A relay that raises produces an empty book, never invented prose."""
    async def boom(*args, **kwargs):
        raise RuntimeError("relay down")
    monkeypatch.setattr(cc, "ask_json", boom)
    out = await cc.career_chronicle({"events": [], "milestones": {}})
    assert out["empty"] is True
    assert out["chapters"] == []
