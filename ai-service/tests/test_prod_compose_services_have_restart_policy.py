"""Production compose services should define a restart policy.

Without `restart`, a crashed container stays down after host reboot or failure.
This gate asserts every top-level service in `docker-compose.prod.yml` declares
`restart:` (e.g. `unless-stopped`).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROD = ROOT / "docker-compose.prod.yml"


def _service_blocks(text: str) -> dict[str, str]:
    # Top-level services under `services:` at column 2, stopping at the next
    # top-level key (e.g. `volumes:`, `networks:`).
    blocks: dict[str, str] = {}
    m = re.search(r"(?m)^services:\s*$", text)
    if not m:
        return blocks
    rest = text[m.end() :]
    # Stop at next column-0 key that isn't a comment/blank (volumes/networks/etc).
    end = re.search(r"(?m)^[a-z]", rest)
    section = rest if not end else rest[: end.start()]
    parts = re.split(r"(?m)^  ([a-z][\w-]*):\s*$", section)
    for i in range(1, len(parts) - 1, 2):
        blocks[parts[i]] = parts[i + 1]
    return blocks


def test_prod_compose_all_services_define_restart_policy() -> None:
    text = PROD.read_text(encoding="utf-8")
    blocks = _service_blocks(text)
    assert blocks, "no services found in prod compose (sanity)"
    missing = [name for name, body in blocks.items() if not re.search(r"(?m)^\s+restart:", body)]
    assert not missing, f"prod compose services missing restart policy: {sorted(missing)}"
