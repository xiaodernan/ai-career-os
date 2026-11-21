"""Epic 362: no feature hand-writes a cap on what it sends the model.

The relay carries a Codex-class context and the reader pays for the window, so a
guess about how much of it to use is a guess about how much of the reader's own
material reaches the model. Epic 340 put one ceiling in
`app/core/context_budget.py` and fitted the main paths through it, but seventeen
features still hand-wrote a slice -- `[:8000]` for a chronicle, `[:2400]` for a
letter, `[:16000]` for the tailor's resume. Every one of them threw away most of
the window on a payload the budget would have taken whole.

The gate is a walk, not a measurement: the serialise-then-slice idiom
(`json.dumps(..., ensure_ascii=False, default=str)[:N]`) and the bare string slice
on a variable passed to `wrap_untrusted` are both forbidden outside
`context_budget.py` itself, which owns the fitting. A new feature that reaches for
a magic number reddens here rather than in production, where the symptom is a
model that was never shown the reader's resume.

What this does NOT forbid: output fields, preview strings, trace snippets and
anything the model did not read. Those caps are about what a *human* sees, and a
200 kB trace row is not a bigger gift.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"

# The idiom this gate forbids: serialise the payload, then cut it at a literal.
SERIALISE_SLICE = re.compile(r"json\.dumps\([^)]*ensure_ascii=False[^)]*\)\s*\[:\d+\]")
# A bare slice on a name handed to the model. Narrow on purpose: only the first
# argument of `wrap_untrusted` is read, so an output field elsewhere is untouched.
WRAP_SLICE = re.compile(r"wrap_untrusted\(\s*[\"'][A-Z_]+[\"']\s*,\s*([A-Za-z_][\w\.]*)\[:\d+\]")

# The one module that owns fitting, and therefore may name the idiom.
OWNERS = {"app/core/context_budget.py"}


def shipped_python() -> list[Path]:
    return sorted(p for p in APP.rglob("*.py") if p.is_file())


def test_no_feature_serialises_then_slices_its_input() -> None:
    offenders: list[str] = []
    for path in shipped_python():
        rel = path.relative_to(ROOT).as_posix()
        if rel in OWNERS:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in SERIALISE_SLICE.finditer(text):
            offenders.append(f"{rel}: {match.group(0)[:80]}")
    assert offenders == [], (
        "these payloads are still cut at a hand-written number before the model "
        "sees them; route them through app.core.context_budget.fit_json instead: "
        + "; ".join(offenders)
    )


def test_no_feature_slices_what_it_hands_the_model_unwrapped() -> None:
    offenders: list[str] = []
    for path in shipped_python():
        rel = path.relative_to(ROOT).as_posix()
        if rel in OWNERS:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in WRAP_SLICE.finditer(text):
            offenders.append(f"{rel}: {match.group(1)}[:N]")
    assert offenders == [], (
        "these are handed to the model behind a literal slice; fit them through "
        "fit_input first so the budget decides: " + "; ".join(offenders)
    )


def test_the_budget_is_one_number_and_every_feature_can_reach_it() -> None:
    """The point of the whole module: one ceiling, not one per feature."""
    settings = (ROOT / "app" / "core" / "config.py").read_text(encoding="utf-8")
    assert "llm_input_char_budget" in settings, (
        "the single input ceiling left the settings; a feature would have to invent "
        "its own number again"
    )
    value = re.search(r"llm_input_char_budget:\s*int\s*=\s*([\d_]+)", settings)
    assert value, "the ceiling is no longer a plain integer default"
    assert int(value.group(1).replace("_", "")) >= 50_000, (
        "the input ceiling fell below the Codex-class window this product runs on"
    )
    budget = (ROOT / "app" / "core" / "context_budget.py").read_text(encoding="utf-8")
    assert "def fit_json(" in budget, "the JSON fitter left; the callers would break"
