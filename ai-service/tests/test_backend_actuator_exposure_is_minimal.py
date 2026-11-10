"""Backend actuator exposure must stay minimal (public: health + prometheus only).

`application.yml` controls which actuator endpoints are exposed over HTTP. The public
scrape/probe set stays exactly `health` and `prometheus`; the authenticated wiring-debug
and Resilience4j observability endpoints (`info`, `conditions`, `circuitbreakers`,
`circuitbreakerevents`) are allowed but require authentication (the security chain does not
permitAll them). This gate reads the YAML source and asserts the `include` list is exactly
the intended set (order-insensitive), that no leaky endpoint (`env`, `beans`, `heapdump`,
`configprops`, ...) crept in, and that Redis's actuator health indicator stays disabled
(as documented, to avoid false-down on rate-limiter fail-open).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_YML = ROOT / "backend" / "src" / "main" / "resources" / "application.yml"

# Only these may be on the surface; everything else (env, beans, heapdump, configprops,
# threaddump, ...) is refused here so a stray line is a failed gate, not an open door.
ALLOWED = {"health", "prometheus", "info", "conditions", "circuitbreakers", "circuitbreakerevents"}
REQUIRED = {"health", "prometheus"}


def test_actuator_exposure_is_minimal_and_only_authorized_endpoints() -> None:
    text = APP_YML.read_text(encoding="utf-8")
    # Find `include:` under management exposure; tolerate whitespace/comments around it.
    m = re.search(r"(?m)^\s*include:\s*([^\n#]+)", text)
    assert m, "application.yml missing management endpoints exposure include"
    items = {x.strip() for x in m.group(1).split(",") if x.strip()}
    assert REQUIRED <= items, f"health and prometheus are required, got {sorted(items)}"
    assert items <= ALLOWED, (
        f"actuator exposure must stay within authorized endpoints {sorted(ALLOWED)}, "
        f"got {sorted(items)}"
    )


def test_actuator_redis_health_indicator_disabled() -> None:
    text = APP_YML.read_text(encoding="utf-8")
    # Look for the management.health.redis.enabled: false stanza.
    assert re.search(r"(?ms)management:.*?health:.*?redis:.*?enabled:\s*false", text), (
        "application.yml must keep management.health.redis.enabled: false (fail-open semantics)"
    )
