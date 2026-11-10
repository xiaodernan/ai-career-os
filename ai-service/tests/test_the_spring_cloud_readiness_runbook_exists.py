"""The Spring Cloud readiness runbook must name the real fleet.

`docs/SPRING_CLOUD_READINESS.md` is the operator's shorter check list for a deployment:
it walks build identity, the edge routes, the registry, the backend bridge, and the gates.
It references services and ports from `docker-compose.yml`; those must stay in sync, or
the runbook sends an operator to a dead door or past a gate. This test reads both files
and asserts the same four services by name, so a rename in either place fails here.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNBOOK = ROOT / "docs" / "SPRING_CLOUD_READINESS.md"
COMPOSE = ROOT / "docker-compose.yml"

SERVICES = ("backend", "gateway", "discovery", "config-server")
APP_NAMES = ("career-os-backend", "career-os-gateway", "career-os-discovery", "career-os-config-server")


def test_the_readiness_runbook_names_the_real_compose_services():
    runbook = RUNBOOK.read_text(encoding="utf-8")
    compose = COMPOSE.read_text(encoding="utf-8")
    for service in SERVICES:
        assert service in runbook, f"the readiness runbook no longer names {service}"
        assert service in compose, f"{service} is not a service in docker-compose.yml"
    for app_name in APP_NAMES:
        assert app_name in runbook, f"the readiness runbook no longer names {app_name}"


def test_the_readiness_runbook_walks_the_four_checks():
    runbook = RUNBOOK.read_text(encoding="utf-8")
    # Each numbered section maps to a Spring Cloud surface this deployment serves.
    for section in ("## 1.", "## 2.", "## 3.", "## 4."):
        assert section in runbook, f"the readiness runbook is missing its {section} check"
    for surface in ("/actuator/health", "/actuator/info", "instance", "registry"):
        assert surface in runbook, f"the readiness runbook no longer checks {surface}"
