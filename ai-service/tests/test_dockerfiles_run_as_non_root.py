"""Service Dockerfiles must run as a non-root user.

Running containers as root increases blast radius. Each service Dockerfile should
declare a non-root `USER` (e.g. `app`, `node`). This gate checks for a `USER`
directive that is not `root`.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILES = [ROOT / s / "Dockerfile" for s in ("ai-service", "backend", "frontend")]


def test_dockerfiles_declare_non_root_user() -> None:
    missing = []
    for path in DOCKERFILES:
        assert path.is_file(), f"missing {path}"
        text = path.read_text(encoding="utf-8", errors="replace")
        users = [m.group(1).strip() for m in re.finditer(r"(?im)^\s*USER\s+(\S+)", text)]
        if not users:
            missing.append(f"{path.parent.name}: no USER directive")
            continue
        # The effective/last USER matters in simple cases; require at least one non-root.
        if all(u.lower() in ("root", "0") for u in users):
            missing.append(f"{path.parent.name}: only root USER directives {users}")
        elif users[-1].lower() in ("root", "0"):
            missing.append(f"{path.parent.name}: final USER is root {users}")
    assert not missing, "Dockerfiles must run as non-root:\n" + "\n".join(missing)
