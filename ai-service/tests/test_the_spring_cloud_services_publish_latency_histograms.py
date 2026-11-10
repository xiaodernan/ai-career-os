"""The Spring Cloud services must publish latency histograms (Epic 108.22).

`http.server.requests` comes with a default bucket set that resolves nothing at the
sub-second regime this platform lives in, so a scrape tells you a mean but not a p95.
Setting `management.metrics.distribution.percentiles-histogram.http.server.requests=true`
gives Prometheus the bucket series (`http_server_requests_seconds_bucket{le=...}`) it needs
to compute p50/p95 per application. This gate reads the four application.yml files together,
along with the shared `metrics.tags.application`, so the distribution cannot be dropped without
the gate noticing — the metrics view of the fleet is only useful if every service reports it.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ("backend", "gateway", "discovery", "config-server")


def test_every_spring_cloud_service_publishes_request_latency_histograms():
    for service in SERVICES:
        text = (ROOT / service / "src" / "main" / "resources" / "application.yml").read_text(
            encoding="utf-8"
        )
        match = re.search(
            r"percentiles-histogram:\s*\n\s*http\.server\.requests:\s*true", text
        )
        assert match, (
            f"{service} dropped its latency histogram; Prometheus gets a count, not a p95"
        )
