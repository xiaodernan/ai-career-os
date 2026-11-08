"""Dockerfiles and prod compose build contexts must exist.

CI and production builds depend on service Dockerfiles. A missing Dockerfile or a
prod compose `build:` context without a Dockerfile fails only at build time. This
gate asserts the key Dockerfiles exist and that each prod compose `build:` service
has a resolvable context with a Dockerfile.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROD = ROOT / "docker-compose.prod.yml"


def test_service_dockerfiles_exist() -> None:
    for svc in ("ai-service", "backend", "frontend"):
        p = ROOT / svc / "Dockerfile"
        assert p.is_file(), f"missing {svc}/Dockerfile"


def test_prod_compose_build_contexts_have_dockerfiles() -> None:
    text = PROD.read_text(encoding="utf-8")
    # Capture simple `build: ./path` and `build:\n  context: ./path` forms.
    contexts = set(re.findall(r"(?m)^\s*build:\s*([./][^\s#]+)\s*$", text))
    contexts.update(re.findall(r"(?m)^\s*context:\s*([./][^\s#]+)\s*$", text))
    assert contexts, "prod compose has no build contexts (sanity)"
    missing = []
    for ctx in contexts:
        base = (ROOT / ctx).resolve()
        if not (base / "Dockerfile").is_file():
            missing.append(f"{ctx} -> missing Dockerfile")
    assert not missing, f"prod build contexts missing Dockerfiles: {missing}"
