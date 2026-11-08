"""The deployment doc must name the same host ports the compose files actually publish.

A port number written in DEPLOYMENT.md is an operator instruction (what to curl,
what to firewall, what stays on loopback). When it drifts from docker-compose.yml
or docker-compose.prod.yml, the doc becomes a wrong runbook. This gate reads the
published host-port mappings from both compose files and asserts the key facts
DEPLOYMENT.md states about them.

It checks concrete, load-bearing facts (not prose): dev host ports, redis's
non-default host port, minio API+console, and the prod override's binding
intent for the internal/public services.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "docker-compose.yml"
PROD = ROOT / "docker-compose.prod.yml"
DOC = ROOT / "docs" / "DEPLOYMENT.md"


def _host_ports(text: str) -> set[str]:
    # Matches quoted "127.0.0.1:HOST:CONTAINER" and "HOST:CONTAINER" mappings.
    return set(re.findall(r'"(?:[0-9.]+:)?(\d+):\d+"', text))


def _service_block(text: str, name: str) -> str:
    # Crude but deterministic: slice from "  <name>:" to the next top-level service-ish
    # header at column 2, or end of file. Good enough for our small compose files.
    m = re.search(rf"(?m)^  {re.escape(name)}:\s*$", text)
    assert m, f"service {name!r} not found"
    rest = text[m.start() :]
    nxt = re.search(r"(?m)^  [a-z][\w-]*:\s*$", rest[m.end() - m.start() :])
    return rest if not nxt else rest[: m.end() - m.start() + nxt.start()]


def test_dev_compose_host_ports_match_deployment_doc() -> None:
    dev = DEV.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")
    ports = _host_ports(dev)
    # The concrete host ports dev compose publishes (postgres, redis->16380, minio, ai, backend, frontend).
    for port in ("5432", "16380", "19000", "19001", "8000", "8080", "3000"):
        assert port in ports, f"dev compose no longer publishes host port {port}: {sorted(ports)}"
        assert port in doc, f"DEPLOYMENT.md must mention host port {port}"

    # Redis is intentionally remapped on the host (16380) to avoid local clashes; the doc
    # must state that mapping, and the redis service block must publish it.
    redis = _service_block(dev, "redis")
    assert '"127.0.0.1:16380:6379"' in redis or "16380:6379" in redis
    assert "16380" in doc and "6379" in doc, "DEPLOYMENT.md must document redis host 16380 -> container 6379"


def test_prod_compose_binding_intent_matches_deployment_doc() -> None:
    prod = PROD.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")
    # ai-service stays loopback-only in prod (internal surface).
    ai = _service_block(prod, "ai-service")
    assert "127.0.0.1:8000:8000" in ai, "prod ai-service must bind 8000 to loopback only"
    # backend/frontend are published (reverse-proxied in front in real prod).
    backend = _service_block(prod, "backend")
    frontend = _service_block(prod, "frontend")
    assert "8080:8080" in backend
    assert "3000:3000" in frontend
    # DEPLOYMENT.md must state the prod port/binding facts (table rows) and the dev ports
    # the prod override leaves alone.
    assert re.search(r"\|\s*ai-service\s*\|\s*8000\s*\|", doc), "doc missing prod ai-service 8000 row"
    assert re.search(r"\|\s*backend\s*\|\s*8080\s*\|", doc), "doc missing prod backend 8080 row"
    assert re.search(r"\|\s*frontend\s*\|\s*3000\s*\|", doc), "doc missing prod frontend 3000 row"
    assert "postgres" in doc and "5432" in doc and "redis" in doc and "16380" in doc and "19000/19001" in doc, (
        "DEPLOYMENT.md must document dev ports prod override leaves unchanged (postgres/redis/minio)"
    )
