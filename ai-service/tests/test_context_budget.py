"""Epic 340 — one config-driven budget for all volatile model input.

The engine used to scatter magic caps (20k JD, 24k resume, 7.5k interview ctx,
1.8k per evidence chunk) that left most of a Codex-class context window unused.
The budget is now owned by one setting and divided by helpers; these tests hold
that the helper is honest (kept/dropped/cap), that a configured floor cannot be
zeroed by a bad env value, and that the preamble — the cache's byte-stable prefix —
is never touched by the fitting.
"""

from __future__ import annotations

import pytest

from app.core import context_budget as cb
from app.core.config import get_settings


def test_budget_reads_the_setting_with_a_safe_floor(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "llm_input_char_budget", 50_000)
    assert cb.input_budget() == 50_000
    monkeypatch.setattr(s, "llm_input_char_budget", 0)
    assert cb.input_budget() >= 2000  # a bad env cannot zero the window


def test_fit_input_reports_exactly_what_it_kept(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "llm_input_char_budget", 10_000)
    fitted = cb.fit_input("x" * 25_000)
    assert fitted.text == "x" * 10_000
    assert fitted.kept == 10_000 and fitted.dropped == 15_000 and fitted.cap == 10_000
    assert fitted.truncated is True
    assert fitted.as_trace() == {"input_kept": 10_000, "input_dropped": 15_000,
                                 "input_cap": 10_000, "input_truncated": True}


def test_fit_input_share_and_ceiling(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "llm_input_char_budget", 10_000)
    assert cb.fit_input("y" * 10_000, share=0.25).cap == 2500
    # ceiling wins when it is the tighter of the two constraints
    assert cb.fit_input("z" * 10_000, ceiling=80).cap == 80
    assert cb.fit_input("z" * 10_000, share=0.25, ceiling=3000).cap == 2500


def test_fit_input_tolerates_none():
    fitted = cb.fit_input(None)
    assert fitted.text == "" and fitted.kept == 0 and fitted.dropped == 0


def test_default_budget_uses_the_full_codex_class_window():
    # The shipped default must actually be generous — the whole complaint was that
    # inputs were too small. 200k chars is ~50k mixed tokens, inside a 6.2-sol window.
    assert get_settings().llm_input_char_budget >= 120_000


def test_the_main_input_sites_no_longer_hardcode_a_magic_cap():
    """The four sources that used to cut at a fixed small number must now use the
    budget helper, so raising the one setting really does reach the model everywhere.
    """
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app"
    sites = {
        "features/jd_analyze.py": "raw_text[:20000]",
        "features/resume_parse.py": "text[:24000]",
        "features/interview.py": "ctx[:7500]",
        "agents/orchestrator.py": "str(evidence)[:8000]",
    }
    for rel, old in sites.items():
        body = (root / rel).read_text(encoding="utf-8")
        assert old not in body, f"{rel} still carries the old cap {old!r}"
        assert "fit_input" in body, f"{rel} does not route its input through the budget"
