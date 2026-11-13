"""The engine shares exactly one byte-identical prefix; nothing forks it.

The origin of the fix (Epic 182): every one-shot feature call opened with a
~200-token agent contract — structurally identical across calls, yet far too short
to cross the provider's prefix-cache threshold. The copilot could share a ~6.2k-token
prefix across turns; the features could not, and every aggregate cache read showed
it. The fix was structural (one shared PLATFORM_PREAMBLE) not configuration.

This file is the gate the helper references: it holds the claim that every LLM
request the engine sends opens with PLATFORM_PREAMBLE. A drift here is the
difference between "the whole engine warms one cache" and "every one-shot is
still a cold miss".
"""

from __future__ import annotations

import re
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "app"

# Calls in app/ that open a conversation. Every call site in the engine MUST go
# through stable_messages() so the preamble leads; a raw LLMMessage("system", ...)
# anywhere else is the fork that reintroduces per-call cold prefixes.
# The only file that may spell a system message literally is the helper itself.

# ------------------------------------------------------------- the constant


def _find_literal_system_sites() -> list[str]:
    found: list[str] = []
    pattern = re.compile(r"\bLLMMessage\(\s*[\"']system[\"']")
    for path in sorted(APP.rglob("*.py")):
        if path.name == "ai.py":
            # stable_messages builds the two system messages itself; everything else
            # in this module is the helper's own construction.
            continue
        for m in pattern.finditer(path.read_text(encoding="utf-8")):
            found.append(f"{path.relative_to(APP)}:{path.read_text(encoding='utf-8')[:m.start()].count(chr(10)) + 1}")
    return found


def test_no_bare_system_prompt_outside_the_helper():
    sites = _find_literal_system_sites()
    assert sites == [], (
        "bare system prompts found outside stable_messages: "
        f"{sites} — open a conversation through `stable_messages(agent, ...)` instead"
    )


def test_the_preamble_is_static_and_non_trivial():
    from app.core.preamble import PLATFORM_PREAMBLE
    assert isinstance(PLATFORM_PREAMBLE, str)
    assert len(PLATFORM_PREAMBLE) > 2000, (
        f"the preamble is {len(PLATFORM_PREAMBLE)} chars — "
        "shorter than the prefix-cache minimum for any provider we aim at"
    )
    assert not re.search(r"\{\w+\}|%(\(|\w)|\$\{", PLATFORM_PREAMBLE, re.M), (
        "PLATFORM_PREAMBLE contains an interpolation placeholder; the cache key would split"
    )


def test_every_feature_caller_uses_the_helper():
    """Every file that builds an LLMRequest must call stable_messages — the one exception
    is `{...LLMRequest(messages=stable_messages(...)...}` fragments everywhere already."""
    from app.core.ai import stable_messages  # noqa: F401 — exists, importable

    source_files = [p for p in APP.rglob("*.py")
                    if "test" not in p.parts
                    and "core" not in p.parts]
    offenders: list[str] = []
    for path in source_files:
        text = path.read_text(encoding="utf-8")
        # An `LLMRequest` in this file that doesn't mention stable_messages is a fork.
        if "LLMRequest(" in text and "stable_messages(" not in text:
            # Adapters/tests live elsewhere; helper module is skipped above.
            offenders.append(str(path.relative_to(APP)))
    assert offenders == [], (
        f"files building LLMRequest without stable_messages: {offenders}"
    )


def test_the_helper_returns_the_preamble_first():
    """The first message is always the platform block — byte-identical across every agent."""
    from app.core.ai import stable_messages
    from app.core.preamble import PLATFORM_PREAMBLE
    from app.providers.base import LLMMessage

    out = stable_messages("You are the narrator.", LLMMessage("user", "hi"))
    assert out[0].role == "system"
    assert out[0].content == PLATFORM_PREAMBLE
    assert out[1].role == "system"
    assert out[1].content == "You are the narrator."
    assert out[2].role == "user"
    assert out[2].content == "hi"
