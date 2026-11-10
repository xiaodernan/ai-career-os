"""The backend's blocking load balancer must keep its health check (Epic 108.21).

`AiServiceRouter` hands the discovery's configured list to Spring Cloud LoadBalancer each
call. With `spring.cloud.loadbalancer.configurations=health-check` the blocking LB stops
offering an instance of ai-service that no longer answers `/health`, instead of the circuit
breaker absorbing every slow failure. The properties are load-bearing for multi-replica
deployments; this gate keeps them in `application.yml`.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_the_blocking_loadbalancer_health_check_is_on_and_points_at_ai_service():
    text = (ROOT / "backend" / "src" / "main" / "resources" / "application.yml").read_text(
        encoding="utf-8"
    )
    assert "configurations: health-check" in text, (
        "the blocking load balancer lost its health-check supplier; ai-service replicas "
        "that stop answering /health will be handed to callers until the circuit opens"
    )
    assert "ai-service: /health" in text, (
        "the health-check path for ai-service changed; it must be the engine's own bounded "
        "/health, not the default /actuator/health which ai-service does not serve"
    )
