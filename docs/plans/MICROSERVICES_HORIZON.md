# Microservices horizon — next epics (planned)

> **Status:** planning doc (2026-11-10). Everything in this file is **not implemented**.
> Verified-current Spring Cloud state is recorded in `docs/ROADMAP.md` (Epics 108.x) and
> `docs/MICROSERVICES.md`. Do not claim any of these are shipped until a real gate/test exists.
>
> Pick the top un-done item; implement; move into ROADMAP when the gate is green locally.

## What is already in place (measured 2026-11-10)

| Element | State | Verification |
|---|---|---|
| Service discovery (Eureka) | opt-in; `instance-id`/`metadata-map`/lease tuning; compose `app` profile | `DiscoveryApplicationTests` 4/4 (mvn), `test_the_compose_files_parse.py` |
| Spring Cloud Gateway | routing `lb://`, CORS dedupe, rate limiter, request size, circuit breaker + fallback, optional ops lockdown `GATEWAY_ACTUATOR_TOKEN` | `GatewayOperationsTest`/`GatewayRoutingTest`/`GatewayActuatorSurfaceTest` green; `ci.yml` springcloud job |
| Spring Cloud Config (opt-in) | native backend; `spring.cloud.config.enabled=false` default + `optional:configserver:`; per-service example configs | `ConfigServerApplicationTests` 4/4; `test_the_config_client_stays_opt_in.py` 2/2 |
| Resilience4j | backend bridge circuit breaker (per-door + whole-bridge); gateway `CircuitBreaker` route filter | `ResilienceStatusServiceTest`, `AiServiceCircuitBreakerMetricsTest` |
| LoadBalancer | blocking LB evicts dead engine replicas via `/health`; configured `health-check.path.ai-service=/health` | `test_the_load_balancer_health_check_stays_on.py`, `AiServiceRouterTest` green |
| Trace propagation | W3C `traceparent` gateway → backend → ai-service; `trace_id` in ai-service JSON logs; optional `requestId`/`traceId` in refusal bodies | `test_the_id_the_backend_sends_is_the_id_the_service_logs.py`, refusal suite 15/15 |
| Observability | `info.app`/build-sha; `metrics.tags.application`; `http.server.requests` histograms; `circuitbreakers[events]` + `conditions` auth-only; `/api/v1/system/resilience` + `ServiceResilience` card; `careeros.circuitbreaker.open` gauge + `CareerOSCircuitBreakerOpen` alarm | `test_the_spring_cloud_*` 8 gates; `GatewayActuatorSurfaceTest` 5/5 |
| Kubernetes probes | `probes.enabled=true` on all four services (`/actuator/health/liveness` + `/readiness`) | `test_the_spring_cloud_services_expose_liveness_and_readiness_probes.py` |
| Config round-trip (110) | native repo `career-os-backend.yml` carries `careeros.extras.demo-property=backend-roundtrip-ok` | `ConfigServerApplicationTests.servesTheBackendRoundTripDemoProperty` |

---

## Planned epics (not started)

### Epic 109 — Kubernetes manifests for the Spring Cloud services
- **Goal:** deployment is no longer compose-only; a Kubernetes manifest set (Kustomize overlay) ships for discovery/gateway/backend/config-server/ai-service.
- **Deliverables:** `deploy/k8s/{base,overlays}` with Deployments, Services, liveness/readiness probes pointing at `/actuator/health/liveness` and `/actuator/health/readiness`, PodDisruptionBudget for multi-instance gateway/backend/ai-service, `config` profile for config-server, ServiceAccount + NetworkPolicy (gateway egress only to backend; backend egress only to ai-service/db/minio/redis).
- **Acceptance:** `kubectl apply --dry-run=client` validates; a smoke test checks the manifests reference the same images/tags as dev compose; documented in `docs/DEPLOYMENT.md` profile.

### Epic 110 — Config Server opt-in demo round-trip **DONE (measured 2026-11-10)**
- The `career-os-backend.yml` example profile now carries `careeros.extras.demo-property=backend-roundtrip-ok`; a service opted into Config (`SPRING_CLOUD_CONFIG_ENABLED=true` with `spring.application.name=career-os-backend`) can read the key back from `GET http://config-server:8888/career-os-backend/default`. `ConfigServerApplicationTests.servesTheBackendRoundTripDemoProperty` pins the round-trip offline; suite 5/5 green. Scope kept to a round-trip demo; not a general config-refresh loop. `MICROSERVICES.md` §4 now lists the round-trip.

### Epic 111 — Spring Cloud Gateway route metrics + one alert
- **Goal:** gateway latency and refusal counts are exported to Prometheus under `spring.cloud.gateway.*` and a `CareerOSGatewayRateLimited` alert exists.
- **Deliverables:** `spring.cloud.gateway.metrics.enabled=true` (default) verified in `/actuator/metrics`; rule for `gateway.ratelimit.refused` increase > N per minute (probe with `Outcome` refusal tag); docs added to `ops/prometheus/alerts.yml` + RUNBOOK entry; gate asserts the rule exists and the metric name is the one Micrometer registers.
- **Acceptance:** a route fires the metric through a synthetic refused request in a test; the alert references the same metric.

### Epic 112 — Backend probes split: liveness vs readiness for the db/redis/storage probes
- **Goal:** backend liveness (/actuator/health/liveness) reports only "process up" (DB down ≠ unalive), and readiness reports db/redis/storage/ai reachability.
- **Deliverables:** `@ReadinessGroup`/configuration that maps the existing `/api/v1/health` components to Spring Boot probe indicators; a contract gate asserting the wiring + the split; docs updated.
- **Acceptance:** a test that flips the DB unreachable shows `/actuator/health/readiness` false and `/actuator/health/liveness` true.

### Epic 113 — Eureka multi-node peer config (optional, opt-in profile)
- **Goal:** demonstrate peer-awareness: two discovery instances that gossip, `peer-eureka-server` profile in prod overlay.
- **Deliverables:** `discovery` profile-driven `eureka.client.register-with-eureka=true/fetch-registry=true`; `EUREKA_PEER_ZONES` wiring; docs explain split-horizon; no default behavior change.
- **Acceptance:** two-node overlay boots (documented as manual verification; not in CI); `DiscoveryApplicationTests` covers the profile properties.

### Epic 114 — Config Server security (opaque token or mTLS)
- **Goal:** the config endpoint refuses anonymous reads; native backend serves only behind a shared token.
- **Deliverables:** `spring.cloud.config.server.native....` + a filter (`X-Config-Token`) or mTLS in front; config examples sanitized; a test asserts 401 without the token; docs updated; `.env.prod.example` handles it via an env placeholder (same pattern as `GATEWAY_ACTUATOR_TOKEN`).
- **Acceptance:** gate refuses anonymous config fetch; docs show how to enable.

## Sequencing notes
- 109 and 112 unblock real-world operability questions; 110–111 tighten the observability loop; 113–114 are advanced and only worth doing when a second instance is needed.
- Each epic must land with a gate (or a contract assertion if port of attack is a doc/K8s manifest, gate reads the manifests as text) and offline verification.
