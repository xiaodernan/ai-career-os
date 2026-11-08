"""Backend actuator exposure must stay minimal (health + prometheus only).

`application.yml` controls which actuator endpoints are exposed over HTTP.
Exposing `env`, `beans`, `heapdump`, etc. leaks sensitive internals. The security
model allows only the read-only health and Prometheus scrape endpoints. This gate
reads the YAML source and asserts the `include` list is exactly the expected
minimal set (order-insensitive) and that Redis's actuator health indicator stays
disabled (as documented, to avoid false-down on rate-limiter fail-open).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_YML = ROOT / "backend" / "src" / "main" / "resources" / "application.yml"


def test_actuator_exposure_is_health_and_prometheus_only() -> None:
    text = APP_YML.read_text(encoding="utf-8")
    # Find `include:` under management exposure; tolerate whitespace/comments around it.
    m = re.search(r"(?m)^\s*include:\s*([^\n#]+)", text)
    assert m, "application.yml missing management endpoints exposure include"
    items = {x.strip() for x in m.group(1).split(",") if x.strip()}
    assert items == {"health", "prometheus"}, (
        f"actuator exposure must be exactly {{health,prometheus}}, got {sorted(items)}"
    )


def test_actuator_redis_health_indicator_disabled() -> None:
    text = APP_YML.read_text(encoding="utf-8")
    # Look for the management.health.redis.enabled: false stanza.
    assert re.search(r"(?ms)management:.*?health:.*?redis:.*?enabled:\s*false", text), (
        "application.yml must keep management.health.redis.enabled: false (fail-open semantics)"
    )
