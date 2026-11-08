"""Frontend package.json must declare tooling required by CI.

CI runs `npx vitest run` and `npx tsc --noEmit`. This gate ensures `vitest`,
`typescript`, and `next` are present in dependencies/devDependencies so a bad
dep edit fails fast.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "frontend" / "package.json"


def test_frontend_package_json_declares_ci_tooling() -> None:
    pkg = json.loads(PKG.read_text(encoding="utf-8"))
    deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
    required = ["next", "typescript", "vitest"]
    missing = [r for r in required if r not in deps]
    assert not missing, f"frontend/package.json missing CI-required deps: {missing}"
