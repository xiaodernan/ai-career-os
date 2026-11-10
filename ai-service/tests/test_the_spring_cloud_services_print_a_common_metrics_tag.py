"""The Spring Cloud services must publish one common Micrometer tag.

Every Java service here (`backend`, `gateway`, `discovery`, `config-server`) publishes
Micrometer metrics. A path like `/actuator/prometheus` is only useful to a shared
scraper if the metrics say which application they came from — otherwise a
`http_server_requests_seconds_count` from the gateway and one from the backend are the
same series with different pod IPs, and no relabel rule fixes that after the fact.

This gate reads the four application.yml files and asserts each one sets
`management.metrics.tags.application` to `${spring.application.name}`, in the same shape
as `test_the_config_client_stays_opt_in.py`. It reads the four files rather than one,
so the tag cannot silently drift in only one service.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ("backend", "gateway", "discovery", "config-server")
TAG = "application: ${spring.application.name}"


def test_every_spring_cloud_service_sets_the_application_metrics_tag():
    for service in SERVICES:
        text = (ROOT / service / "src" / "main" / "resources" / "application.yml").read_text(
            encoding="utf-8"
        )
        assert TAG in text, (
            f"{service} lost its management.metrics.tags.application = "
            "${spring.application.name}; the shared scraper can no longer aggregate "
            "series by application"
        )
