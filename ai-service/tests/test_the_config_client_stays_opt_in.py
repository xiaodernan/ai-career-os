"""The Spring Cloud Config clients must stay opt-in (Epic 101/108).

`gateway`, `discovery` and `backend` all carry `spring-cloud-starter-config` with
`spring.cloud.config.enabled=false` by default and an `optional:configserver:` import.
This is deliberate: env-driven deployments and offline tests keep their behavior, and
nothing about validation of a Config Server is required for a process to boot. A
default that flipped to fail-fast or un-optional would make every laptop boot depend
on a Config Server being up, which is exactly the outage-shaped coupling this platform's
default-off posture exists to avoid.

This gate reads the three application.yml files as text and asserts the opt-in posture,
in the same shape as `test_the_compose_files_parse.py`: two nearly identical documents
nobody may edit without noticing.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ("gateway", "discovery", "backend")


def test_config_client_is_disabled_by_default_and_import_is_optional():
    for service in SERVICES:
        text = (ROOT / service / "src" / "main" / "resources" / "application.yml").read_text(
            encoding="utf-8"
        )
        assert "optional:configserver:" in text, (
            f"{service} no longer imports Config Server with `optional:`; a process that "
            "cannot boot without a Config Server would fail as soon as one is absent"
        )
        assert "enabled: ${SPRING_CLOUD_CONFIG_ENABLED:false}" in text, (
            f"{service} lost its disabled-by-default Config client; setting the env var "
            "would not be what any laptop currently rides"
        )
        assert "fail-fast: ${SPRING_CLOUD_CONFIG_FAIL_FAST:false}" in text, (
            f"{service} lost its disabled-by-default fail-fast; a missing Config Server "
            "would stop the process instead of being ignored"
        )


def test_config_server_runs_only_from_the_config_profile():
    # The dev compose only starts the Config Server under the `config` profile; nothing
    # about a plain `compose up` (or the offline tests) should depend on it.
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    block = compose.split("config-server:", 1)[1]
    assert "profiles: [config]" in block, (
        "the Config Server left its opt-in profile; a plain compose up would start it "
        "and add a hard dependency for every fresh checkout"
    )
