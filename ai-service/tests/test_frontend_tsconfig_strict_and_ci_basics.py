"""Frontend tsconfig must keep strict type checking enabled.

CI runs `npx tsc --noEmit`. Disabling `strict` (or key strict flags) silently
weakens type safety. This gate asserts `strict: true` is configured.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TSCONFIG = ROOT / "frontend" / "tsconfig.json"


def _load_tsconfig(text: str) -> dict:
    # tsconfig allows comments/trailing commas in practice, but this repo's file is JSON.
    # Try strict JSON first; fall back to a minimal strip of // comments.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        stripped = re.sub(r"(?m)//.*$", "", text)
        stripped = re.sub(r"/\*.*?\*/", "", stripped, flags=re.S)
        return json.loads(stripped)


def test_frontend_tsconfig_strict_enabled() -> None:
    data = _load_tsconfig(TSCONFIG.read_text(encoding="utf-8"))
    opts = data.get("compilerOptions") or {}
    assert opts.get("strict") is True, f"frontend tsconfig compilerOptions.strict must be true, got {opts.get('strict')!r}"
