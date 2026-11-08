"""ai-service requirements files must declare core runtime and dev dependencies.

CI and local dev rely on these files (`pip install -r requirements.txt -r requirements-dev.txt`).
This gate asserts key packages are present (name match, version-agnostic) so an
accidental removal fails fast.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQ = ROOT / "ai-service" / "requirements.txt"
REQ_DEV = ROOT / "ai-service" / "requirements-dev.txt"


def _names(text: str) -> set[str]:
    out = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Strip extras/versions/markers.
        name = re.split(r"[<>=!~;\[\s]", line, maxsplit=1)[0].strip().lower().replace("_", "-")
        if name:
            out.add(name)
    return out


def test_ai_service_runtime_requirements_include_core_packages() -> None:
    names = _names(REQ.read_text(encoding="utf-8"))
    required = {"fastapi", "uvicorn", "pydantic", "asyncpg", "httpx"}
    missing = sorted(required - names)
    assert not missing, f"ai-service/requirements.txt missing core runtime deps: {missing}"


def test_ai_service_dev_requirements_include_test_tooling() -> None:
    names = _names(REQ_DEV.read_text(encoding="utf-8"))
    required = {"pytest", "pytest-asyncio"}
    missing = sorted(required - names)
    assert not missing, f"ai-service/requirements-dev.txt missing test tooling: {missing}"
