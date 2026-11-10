"""The Spring Cloud services must all expose the probe groups (Epic 108.27).

Spring Boot's `probes` feature wires `/actuator/health/liveness` and `/actuator/health/readiness`
— the Kubernetes-shaped split an orchestrator reads to distinguish "is the process up" from "is
the process ready to serve". A service registered with Eureka that answers `liveness` but not
`readiness` (or vice versa) misleads the fleet; the four Spring Cloud services publish the same
probe groups, and this gate keeps it so.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ("backend", "gateway", "discovery", "config-server")


def test_every_spring_cloud_service_exposes_probes():
    for service in SERVICES:
        text = (ROOT / service / "src" / "main" / "resources" / "application.yml").read_text(
            encoding="utf-8"
        )
        assert "probes:" in text, f"{service} does not enable the liveness/readiness probe groups"
        assert "enabled: true" in text, f"{service} does not enable the probe groups"
        assert "health" in text, f"{service} dropped health from its actuator exposure"
