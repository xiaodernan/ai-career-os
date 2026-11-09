"""The registry and its citizens must name the same address (Epic 98).

Three files declare where the registry lives: its own `server.port`, the gateway's
`defaultZone`, and the backend's `defaultZone`. None imports the others, so a port
change on one side leaves the other two polling an address that no longer answers --
and every module's own tests stay green, because each is internally consistent.

The same test also pins the switch's shape: Eureka is off in the base document and on
in the `eureka` profile. A base document that defaulted to on would make every laptop
and every unit test wait on a registry that is not running, which is the failure mode
the profile exists to prevent.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parents[2]
DISCOVERY_YML = ROOT / "discovery/src/main/resources/application.yml"
DISCOVERY_APP = ROOT / "discovery/src/main/java/com/careeros/discovery/DiscoveryApplication.java"
GATEWAY_YML = ROOT / "gateway/src/main/resources/application.yml"
BACKEND_YML = ROOT / "backend/src/main/resources/application.yml"
COMPOSE = ROOT / "docker-compose.yml"
COMPOSE_PROD = ROOT / "docker-compose.prod.yml"


def _documents(path: Path) -> list[dict]:
    loaded = yaml.safe_load_all(path.read_text(encoding="utf-8"))
    return [document for document in loaded if document]


def _profile_document(path: Path, profile: str) -> dict:
    for document in _documents(path):
        activate = document.get("spring", {}).get("config", {}).get("activate", {})
        if activate.get("on-profile") == profile:
            return document
    raise AssertionError(f"{path} declares no '{profile}' profile document")


def _placeholder_default(value: str) -> str:
    """The value a `${NAME:default}` spelling uses when the variable is unset."""
    found = re.search(r"\$\{[A-Z_]+:(.+)\}", value)
    assert found, f"{value!r} is not a placeholder with a default"
    return found.group(1)


def _registry_port() -> int:
    port = _documents(DISCOVERY_YML)[0]["server"]["port"]
    return int(_placeholder_default(str(port)))


def test_the_registry_is_a_server() -> None:
    assert "@EnableEurekaServer" in DISCOVERY_APP.read_text(encoding="utf-8"), (
        "a registry that only carries the client starter never accepts a registration"
    )


def test_every_default_zone_points_at_the_registrys_port() -> None:
    expected = _registry_port()

    for path in (GATEWAY_YML, BACKEND_YML):
        zone = _placeholder_default(
            _documents(path)[0]["eureka"]["client"]["service-url"]["defaultZone"]
        )
        assert urlparse(zone).port == expected, (
            f"{path.name} polls {zone!r} while the registry listens on {expected}: "
            "the citizen is looking for a process that is not there"
        )


def test_the_edge_empties_its_static_list_when_the_registry_is_on() -> None:
    profile = _profile_document(GATEWAY_YML, "eureka")

    assert profile["eureka"]["client"]["enabled"] is True
    instances = profile["spring"]["cloud"]["discovery"]["client"]["simple"]["instances"]
    assert instances["backend"] == [], (
        "a configured instance left beside the registry is a second answer: roughly "
        "half the edge's decisions would ignore every service that registered"
    )


def test_the_registry_is_off_outside_its_profile() -> None:
    for path in (GATEWAY_YML, BACKEND_YML):
        base = _documents(path)[0]
        enabled = str(base["eureka"]["client"]["enabled"])
        assert re.fullmatch(r"\$\{[A-Z_]+:false\}", enabled), (
            f"{path.name} enables Eureka by default; every test and laptop would then "
            "wait on a registry that is not running"
        )
        assert _profile_document(path, "eureka")["eureka"]["client"]["enabled"] is True, (
            f"{path.name}'s profile turns nothing on"
        )


def test_compose_puts_every_citizen_on_the_same_registry() -> None:
    for compose in (COMPOSE, COMPOSE_PROD):
        services = yaml.safe_load(compose.read_text(encoding="utf-8"))["services"]
        assert "discovery" in services, f"{compose.name} lost the registry service"

        for citizen in ("gateway", "backend"):
            environment = services[citizen]["environment"]
            assert environment["SPRING_PROFILES_ACTIVE"] == "eureka", (
                f"{compose.name}: {citizen} does not activate the profile that enables "
                "registration"
            )
            assert environment["EUREKA_DEFAULT_ZONE"] == "http://discovery:8761/eureka/", (
                f"{compose.name}: {citizen} polls a registry address the compose network "
                "does not serve"
            )

        assert services["discovery"]["healthcheck"]["test"], (
            "a registry without a healthcheck lets dependants start against a socket "
            "that is open but not answering"
        )
