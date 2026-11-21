"""A single, config-driven character budget for volatile model INPUT (Epic 340).

The old engine scattered magic numbers across features — a JD was cut at 20 000
chars, a resume at 24 000, an interview context at 7 500. On a relay whose prompt
cache is keyed by the byte prefix and whose model carries a Codex-class context
(5万-9万 tokens), those caps threw away most of the window the reader paid for: a
long resume or a detailed posting arrived as a truncated stub.

This module owns ONE ceiling (``settings.llm_input_char_budget``) and the helpers
that divide it. Every feature that sends variable-length source material to the
model goes through here, so:

* there is one number to raise when a larger model is configured, not a dozen;
* the byte-identical prefix (``app.core.preamble``) is never touched — only the
  volatile tail after it is fitted, so the provider's prefix cache still fires;
* the cut is honest: ``fit_input`` reports how much it kept, and features attach
  that figure to the run's trace so an operator can see whether the budget was
  actually used rather than guessing.

Nothing here raises ``max_tokens`` — that is the OUTPUT budget and stays a
per-feature decision. This is input only.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings


@dataclass(frozen=True)
class Fit:
    """The fitted text plus an honest account of what was kept and dropped."""

    text: str
    kept: int
    dropped: int
    cap: int

    @property
    def truncated(self) -> bool:
        return self.dropped > 0

    def as_trace(self) -> dict:
        return {"input_kept": self.kept, "input_dropped": self.dropped,
                "input_cap": self.cap, "input_truncated": self.truncated}


def input_budget() -> int:
    """The configured whole-input ceiling, floored so a bad env value cannot zero it."""
    return max(2000, int(get_settings().llm_input_char_budget or 200_000))


def fit_input(text: str | None, *, share: float = 1.0, ceiling: int | None = None) -> Fit:
    """Fit one volatile input to ``share`` of the configured budget (or ``ceiling``).

    ``share`` lets a feature that packs several sources cap each one; ``ceiling``
    lets a caller that already owns a hard floor keep it. The larger of the two
    constraints is never exceeded — the effective cap is the smaller.
    """
    raw = text if isinstance(text, str) else ""
    share = max(0.01, min(1.0, float(share)))
    cap = int(input_budget() * share)
    if ceiling is not None:
        cap = min(cap, max(1, int(ceiling)))
    kept = raw[:cap]
    return Fit(text=kept, kept=len(kept), dropped=max(0, len(raw) - len(kept)), cap=cap)
