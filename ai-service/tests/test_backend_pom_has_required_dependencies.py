"""Backend pom.xml must declare key runtime/security/schema dependencies.

Source-level contract gate: removing security, Flyway, actuator, JPA, Postgres,
or Prometheus registry breaks core runtime guarantees. This asserts the expected
artifact coordinates/IDs appear in the POM.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POM = ROOT / "backend" / "pom.xml"

REQUIRED = [
    "spring-boot-starter-web",
    "spring-boot-starter-security",
    "spring-boot-starter-data-jpa",
    "spring-boot-starter-actuator",
    "micrometer-registry-prometheus",
    "flyway-core",
    "postgresql",
]


def test_backend_pom_declares_required_dependencies() -> None:
    text = POM.read_text(encoding="utf-8")
    missing = [a for a in REQUIRED if a not in text]
    assert not missing, f"backend/pom.xml missing required dependencies: {missing}"
