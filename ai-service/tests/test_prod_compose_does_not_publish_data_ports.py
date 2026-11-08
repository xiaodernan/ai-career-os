"""Production compose must not publish data-service ports to the host.

postgres, redis, and minio hold user data/credentials. In
`docker-compose.prod.yml` they must be reachable only on the internal compose
network (no `ports:` publishing). Application services may publish ports per
their documented binding intent (ai-service loopback, backend/frontend public or
as the operator configures) — this gate only constrains the data tier.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROD = ROOT / "docker-compose.prod.yml"

DATA_SERVICES = ("postgres", "redis", "minio")


def _service_block(text: str, name: str) -> str:
    m = re.search(rf"(?m)^  {re.escape(name)}:\s*$", text)
    assert m, f"service {name!r} not found in prod compose"
    rest = text[m.start() :]
    nxt = re.search(r"(?m)^  [a-z][\w-]*:\s*$", rest[m.end() - m.start() :])
    return rest if not nxt else rest[: m.end() - m.start() + nxt.start()]


def _publishes_host_ports(block: str) -> bool:
    m = re.search(r"(?m)^    ports:\s*$", block)
    if not m:
        return False
    # Look for a list item mapping "HOST:CONTAINER" under ports.
    tail = block[m.end() :]
    return bool(re.search(r'(?m)^\s+-\s*"?[\d.]+:\d+', tail))


def test_prod_data_services_do_not_publish_host_ports() -> None:
    text = PROD.read_text(encoding="utf-8")
    exposed = [name for name in DATA_SERVICES if _publishes_host_ports(_service_block(text, name))]
    assert not exposed, (
        f"prod compose must not publish host ports for data services: {exposed}. "
        "Keep them on the internal network only."
    )
