"""ai-service requirements should be version-pinned for reproducibility.

Unpinned deps make CI/local builds non-deterministic and can pull breaking
changes. This gate requires each non-comment, non-option requirement line to
include a version specifier (`==`, `>=`, `~=`, `<=`, etc.).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = [ROOT / "ai-service" / "requirements.txt", ROOT / "ai-service" / "requirements-dev.txt"]
VERSION_SPEC = re.compile(r"(==|>=|<=|~=|!=|<|>)")


def test_ai_service_requirements_lines_have_version_specifiers() -> None:
    bad = []
    for path in FILES:
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            s = line.strip()
            if not s or s.startswith("#") or s.startswith("-"):
                continue
            if not VERSION_SPEC.search(s):
                bad.append(f"{path.name}:{i}: {s}")
    assert not bad, "requirements must be version-pinned:\n" + "\n".join(bad)
