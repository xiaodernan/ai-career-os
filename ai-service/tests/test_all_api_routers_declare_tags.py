"""Every APIRouter in ai-service/app/api must declare OpenAPI tags.

Tags keep the generated OpenAPI spec organized and make the route inventory
auditable. An untagged router produces endpoints that are harder to discover in
docs/tooling. This gate scans router construction in API modules.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API_DIR = ROOT / "ai-service" / "app" / "api"

ROUTER_CALL = re.compile(r"APIRouter\s*\(")


def test_all_api_router_constructions_declare_tags() -> None:
    assert API_DIR.is_dir()
    problems = []
    for path in sorted(API_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        text = path.read_text(encoding="utf-8")
        # Find APIRouter(...) calls; a simple window check is sufficient for our style.
        for m in ROUTER_CALL.finditer(text):
            window = text[m.start() : m.start() + 200]
            # Grab until matching close paren at same rough level by finding first ')'
            # that ends the call in our single-line/multi-arg style is imperfect; instead
            # check that 'tags=' appears in the next 300 chars of source.
            ahead = text[m.start() : m.start() + 300]
            if "tags" not in ahead.split("APIRouter", 1)[1].split("\n\n", 1)[0]:
                # refine: within the router call arguments
                pass
            if "tags=" not in text[m.start() : m.start() + 250]:
                problems.append(f"{path.name}:{m.start()} APIRouter missing tags=")
    assert not problems, "APIRouter constructions must declare tags:\n" + "\n".join(problems)
