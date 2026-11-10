"""The Spring Cloud services publish the same build identity in `/actuator/info` (Epic 108.25).

`/actuator/info` is how every Spring Cloud service answers "which commit am I?" — the fleet,
the registry and the reverse proxy all read `build-sha` from the same env-driven value, so a
deployment that lines up one service's `APP_BUILD_SHA` and forgets the others is visible:
the fleet answers with four different SHAs instead of one. The shape is fixed: `info.app.name`
is `${spring.application.name}`, `info.app.build-sha` is `${APP_BUILD_SHA:dev}`.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ("backend", "gateway", "discovery", "config-server")


def _info_block(service: str) -> str:
    text = (ROOT / service / "src" / "main" / "resources" / "application.yml").read_text(
        encoding="utf-8"
    )
    start = text.find("info:")
    assert start >= 0, f"{service} has no `info` block in application.yml"
    # tolerate preceding motivation comments; slice to end of file
    return text[start:]


def test_every_service_publishes_the_same_info_app_shape():
    for service in SERVICES:
        block = _info_block(service)
        assert "app:" in block, f"{service} info block lacks `app:`"
        assert "name: ${spring.application.name}" in block, (
            f"{service} publishes app's name differently; every service must read it from "
            "spring.application.name so the scrape names what it serves"
        )
        assert "build-sha: ${APP_BUILD_SHA:dev}" in block, (
            f"{service} does not publish build-sha from APP_BUILD_SHA; a fleet of four "
            "services then has four different ways to answer which commit it serves"
        )
