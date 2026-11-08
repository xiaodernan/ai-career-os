"""Dev compose data services must bind to loopback, not all interfaces.

postgres, redis, and minio in `docker-compose.yml` are for local development and
carry data/credentials. Publishing their ports on `0.0.0.0` (bare `HOST:CONTAINER`)
exposes them to the local network. The dev stack should bind to `127.0.0.1`.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "docker-compose.yml"

DATA_SERVICES = ("postgres", "redis", "minio")


def _service_block(text: str, name: str) -> str:
    m = re.search(rf"(?m)^  {re.escape(name)}:\s*$", text)
    assert m, f"service {name!r} not found in dev compose"
    rest = text[m.start() :]
    nxt = re.search(r"(?m)^  [a-z][\w-]*:\s*$", rest[m.end() - m.start() :])
    return rest if not nxt else rest[: m.end() - m.start() + nxt.start()]


def test_dev_data_services_bind_to_loopback() -> None:
    text = DEV.read_text(encoding="utf-8")
    bad = []
    for name in DATA_SERVICES:
        block = _service_block(text, name)
        mappings = re.findall(r'-\s*"([^"]+)"', block)
        for mapping in mappings:
            # Expect 127.0.0.1:HOST:CONTAINER (or ::1). A bare HOST:CONTAINER binds all interfaces.
            if mapping.startswith("127.0.0.1:") or mapping.startswith("[::1]:") or mapping.startswith("localhost:"):
                continue
            if re.match(r"\d+:\d+$", mapping):
                bad.append((name, mapping, "binds all interfaces; use 127.0.0.1:HOST:CONTAINER"))
            elif ":" in mapping and not mapping.split(":")[0].replace(".", "").isdigit() and mapping.split(":")[0] not in ("127", "localhost", "[::1]"):
                bad.append((name, mapping, "unexpected host binding"))
    assert not bad, f"dev data services must bind to loopback: {bad}"
