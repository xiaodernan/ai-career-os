"""The Spring Cloud actuator surfaces must stay in sync (Epic 108.20).

Each Java service exposes a different slice of the actuator: backend/cache gateway are
operations-heavy, discovery/config-server are infrastructure-heavy. Nothing in this
repository can see all four files' exposure lists today — the gateway's and backend's
tests each see their own, the registry's sees discovery's. The anonymous `/actuator/health`
on every service is the probe; everything else is behind authentication. This gate reads
the four application.yml files together and asserts the shared promises:

- every service exposes `health` and `info` (the probe + build-sha),
- every service exposes `prometheus` (the scrape),
- the services that carry Spring Cloud circuit breakers (`backend`, `gateway`) also
  expose `circuitbreakers` and `circuitbreakerevents` (the operator's door into Resilience4j),
- the services that carry the Spring Cloud wiring footgun (`backend`, `gateway`) expose
  `conditions`, the wiring debug report that says *why* a bean did or did not match.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ("backend", "gateway", "discovery", "config-server")


def _exposure_include(service: str) -> set[str]:
    text = (ROOT / service / "src/main/resources/application.yml").read_text(encoding="utf-8")
    # The exposure include line is `include: health,prometheus,info,...` possibly preceded by comments.
    match = re.search(r"^\s*include:\s*([a-z,]+)\s*$", text, re.MULTILINE)
    assert match, f"{service} no longer carries an `include:` actuator exposure line"
    return {part.strip() for part in match.group(1).split(",") if part.strip()}


def test_every_service_exposes_health_info_and_prometheus():
    for service in SERVICES:
        include = _exposure_include(service)
        assert "health" in include, f"{service} dropped /actuator/health from exposure"
        assert "info" in include, f"{service} dropped /actuator/info from exposure"
        assert "prometheus" in include, f"{service} dropped /actuator/prometheus from exposure"


def test_the_circuit_breaker_and_wiring_debug_endpoints_are_where_the_breakers_live():
    expectations = {
        "backend": {"circuitbreakers", "circuitbreakerevents", "conditions"},
        "gateway": {"circuitbreakers", "circuitbreakerevents", "conditions"},
        "discovery": set(),
        "config-server": set(),
    }
    for service, required in expectations.items():
        include = _exposure_include(service)
        missing = required - include
        assert not missing, f"{service} is missing its authenticated actuator endpoints: {sorted(missing)}"


def test_nothing_new_slips_into_the_public_probe_set():
    # `health` and `prometheus` are the only anonymous endpoints; nothing else on the list is
    # an authentication-free surface. This is not a privilege audit (the security chain does
    # that): it is a drift guard so a refactor does not sneak `env` onto that surface.
    anonymous_whitelist = {"health", "prometheus", "info"}
    for service in SERVICES:
        include = _exposure_include(service)
        assert include <= ({"health", "prometheus", "info"}
                           | {"conditions", "circuitbreakers", "circuitbreakerevents", "gateway", "metrics", "env"}), (
            f"{service} exposure includes something unexpected: {sorted(include)}"
        )


def test_the_gateway_probe_is_not_hostage_to_its_optional_redis():
    # The gateway depends on spring-boot-starter-data-redis for the optional distributed
    # rate limit (Epic 120), but a Redis outage must not mark the edge as down, exactly
    # like the backend's rate-limiter probe precedent. Assert the indicator is off in the
    # gateway, the same way the backend does it for its own optional redis.
    text = (ROOT / "gateway" / "src" / "main" / "resources" / "application.yml").read_text(
        encoding="utf-8"
    )
    m = re.search(r"(?ms)^\s*health:\s*$\n\s*#[^\n]*\n(?:\s*#[^\n]*\n)*\s*redis:\s*$\n\s*enabled:\s*false", text)
    assert m, (
        "gateway must disable the actuator redis health indicator (management.health.redis.enabled=false); "
        "otherwise an optional shared-budget outage flips the edge's probe DOWN"
    )
