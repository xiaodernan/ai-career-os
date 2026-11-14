"""Epic 4: no text the reader cannot read — the contrast gate for both themes.

Every `text-*` / `text-muted-foreground` token pair in globals.css is measured
by WCAG relative luminance, on both themes, every time this suite runs. The
pair list is the pairs the product actually paints; a new pair is added here
and not shipped unmeasured. The gate fails loud with the computed ratio so the
person fixing it sees the number, not a guess.

Scope honesty (the reason this file exists): FRONTEND_HORIZON.md Epic 4 said
"the contrast gate (test_accessibility_contrast_tokens.py, exists)" — it did not
exist. It does now. The gate is a contract: only pairs in this list are held,
and adding a pair here is the gate learning a new thing the product paints.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

GLOBALS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "app" / "globals.css"

# (foreground_token, background_token, what it is in the UI)
TEXT_PAIRS = [
    ("foreground", "background", "body text"),
    ("foreground", "card", "text on a card"),
    ("foreground", "secondary", "text on secondary surface"),
    ("foreground", "muted", "text on muted surface"),
    ("foreground", "accent", "text on accent surface"),
    ("card-foreground", "card", "card foreground"),
    ("popover-foreground", "popover", "popover foreground"),
    ("secondary-foreground", "secondary", "secondary chip"),
    ("accent-foreground", "accent", "accent chip"),
    ("muted-foreground", "background", "muted body text"),
    ("muted-foreground", "card", "muted text on a card"),
    ("muted-foreground", "muted", "muted text on muted surface"),
    ("muted-foreground", "accent", "muted text on accent surface"),
    ("primary-foreground", "primary", "button label on the accent"),
    ("destructive-foreground", "destructive", "button label on destructive"),
    ("destructive", "background", "destructive as text on the page"),
    ("destructive", "card", "destructive as text on a card"),
    ("success", "background", "success as text"),
    ("success", "card", "success as text on a card"),
    ("warning", "background", "warning as text"),
    ("warning", "card", "warning as text on a card"),
    ("sidebar-foreground", "sidebar", "sidebar text"),
    ("sidebar-accent-foreground", "sidebar-accent", "sidebar accent item"),
    ("sidebar-primary-foreground", "sidebar-primary", "sidebar primary item"),
    ("sidebar-accent-foreground", "sidebar", "sidebar accent item on sidebar"),
]

FLOOR = 4.5

# ------------------------------------------------------------------ oklch -> luminance

def _parse_tokens(block: str) -> dict[str, str]:
    tokens: dict[str, str] = {}
    for name, value in re.findall(r"--([a-z][a-z0-9-]*)\s*:\s*([^;]+);", block):
        tokens[name] = value.strip()
    return tokens

def _block(text: str, opener: str) -> str:
    at = text.index(opener) + len(opener)
    end = text.index("}", at)
    return text[at:end]

def _oklch(value: str) -> tuple[float, float, float]:
    m = re.match(r"oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)", value)
    assert m, f"expected an oklch() value, got {value!r}"
    l, c, h = (float(g) for g in m.groups())
    hr = math.radians(h)
    a = c * math.cos(hr)
    b = c * math.sin(hr)
    return l, a, b

def _linear_srgb(l: float, a: float, b: float) -> tuple[float, float, float]:
    # Björn Ottosson's oklab in reverse (matrices as published).
    ll = l + 0.3963377774 * a + 0.2158037573 * b
    m = l - 0.1055613458 * a - 0.0638541728 * b
    s = l - 0.0894841775 * a - 1.2914855378 * b
    l3, m3, s3 = ll ** 3, m ** 3, s ** 3
    r = +4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3
    g = -1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3
    bl = -0.0041960863 * l3 - 0.7034186147 * m3 + 1.7076147010 * s3
    def clamp(x: float) -> float:
        return min(1.0, max(0.0, x))
    return clamp(r), clamp(g), clamp(bl)

def _luminance(value: str) -> float:
    """Relative luminance (WCAG 2.x) of an oklch() token value."""
    lin = _linear_srgb(*_oklch(value))
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

def _ratio(fg: str, bg: str) -> float:
    l1, l2 = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)

# ------------------------------------------------------------------ the gate

def _load_themes() -> dict[str, dict[str, str]]:
    text = GLOBALS.read_text(encoding="utf-8")
    return {
        "light": _parse_tokens(_block(text, ":root {")),
        "dark": _parse_tokens(_block(text, ".dark {")),
    }

def test_the_block_parse_points_at_real_token_tables():
    themes = _load_themes()
    for name, tokens in themes.items():
        assert len(tokens) >= 20, f"{name}: only {len(tokens)} tokens parsed from globals.css"
        for required in ("background", "foreground", "muted-foreground", "card"):
            assert required in tokens, f"{name}: missing --{required}"

def test_every_text_pair_meets_the_wcag_floor_on_both_themes():
    themes = _load_themes()
    failures: list[str] = []
    for theme, tokens in themes.items():
        for fg, bg, what in TEXT_PAIRS:
            if fg not in tokens or bg not in tokens:
                failures.append(f"{theme}: --{fg} or --{bg} is absent; the pair for {what} cannot be measured")
                continue
            ratio = _ratio(tokens[fg], tokens[bg])
            if ratio < FLOOR:
                failures.append(f"{theme}: --{fg} on --{bg} ({what}) measures {ratio:.2f}:1, floor {FLOOR}:1")
    assert not failures, (
        "contrast below the WCAG floor — every failure names its own ratio:\n  "
        + "\n  ".join(failures)
    )

def test_the_audit_reports_both_themes_so_a_new_theme_cannot_slip_in_unmeasured():
    text = GLOBALS.read_text(encoding="utf-8")
    assert ":root {" in text and ".dark {" in text, (
        "globals.css no longer carries the two audited theme blocks"
    )
