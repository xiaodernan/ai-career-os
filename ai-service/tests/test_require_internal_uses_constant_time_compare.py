"""Internal token auth must use constant-time comparison.

`require_internal` guards every `/internal/*` route. Plain `!=` on secrets leaks
timing information. This gate asserts the implementation uses
`secrets.compare_digest` (or hmac.compare_digest).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEPS = ROOT / "ai-service" / "app" / "core" / "deps.py"


def test_require_internal_compares_internal_token_in_constant_time() -> None:
    text = DEPS.read_text(encoding="utf-8")
    assert "compare_digest" in text, "require_internal must use secrets.compare_digest for token comparison"
    # Ensure we didn't keep a plain string != comparison on the token path.
    assert "x_internal_token != s.internal_api_token" not in text, (
        "require_internal must not use plain != for internal token comparison"
    )
