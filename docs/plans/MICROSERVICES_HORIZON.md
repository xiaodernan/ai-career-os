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
| Config Server security (114) | optional `X-Config-Token` gate gated by `CONFIG_SERVER_TOKEN`; `/actuator/health` stays open | `ConfigServerTokenGateTest` |

---

## Planned epics (not started)

### Epic 109 — Kubernetes manifests for the Spring Cloud services **DONE (measured 2026-11-10)**
`deploy/k8s/base` ships a Kustomize bundle mirroring `docker-compose.yml`: namespace, ConfigMap, Secret example with `CHANGE_ME` placeholders, PersistentVolumeClaims for postgres and minio, Postgres StatefulSet + Redis/MinIO/AI/BE/GW/Discovery/Config/Frontend Deployments with probes, PDBs for backend/gateway/frontend/ai-service, NetworkPolicy. `deploy/k8s/overlays/prod` raises replicas for ai-service/backend/frontend to 3. All manifests validated by `kubectl kustomize` (exit 0) and by the contract gate `test_the_k8s_manifests_define_a_working_fleet.py` (9/9 green), which pins the invariants the compose file represents (service names, ports, probes, PDB coverage, label hygiene, no real-looking secrets, prod overlay scaling).

### Epic 110 — Config Server opt-in demo round-trip **DONE (measured 2026-11-10)**
- The `career-os-backend.yml` example profile now carries `careeros.extras.demo-property=backend-roundtrip-ok`; a service opted into Config (`SPRING_CLOUD_CONFIG_ENABLED=true` with `spring.application.name=career-os-backend`) can read the key back from `GET http://config-server:8888/career-os-backend/default`. `ConfigServerApplicationTests.servesTheBackendRoundTripDemoProperty` pins the round-trip offline; suite 5/5 green. Scope kept to a round-trip demo; not a general config-refresh loop. `MICROSERVICES.md` §4 now lists the round-trip.

### Epic 111 — Gateway route-id histograms in Prometheus **DONE (measured 2026-11-10)**
- The gateway application.yml now enables `percentiles-histogram.spring.cloud.gateway.requests: true` alongside its `http.server.requests` bucket so Prometheus can compute per-route p50/p95. Extended `test_the_spring_cloud_services_publish_latency_histograms.py` to assert the gateway meter too (gate 2/2). Slice did not introduce a new alert — `CareerOSGatewayRateLimited` stays in this ledger as next; publishing the buckets is the smallest, verifiable step.

### Epic 112 — Backend probes split: liveness vs readiness for the db/redis/storage probes
- **Goal:** backend liveness (/actuator/health/liveness) reports only "process up" (DB down ≠ unalive), and readiness reports db/redis/storage/ai reachability.
- **Deliverables:** `@ReadinessGroup`/configuration that maps the existing `/api/v1/health` components to Spring Boot probe indicators; a contract gate asserting the wiring + the split; docs updated.
- **Acceptance:** a test that flips the DB unreachable shows `/actuator/health/readiness` false and `/actuator/health/liveness` true.

### Epic 112 — Backend probes split: liveness vs readiness **DONE (measured 2026-11-11, semantics refined from the sketch below)**
`management.endpoint.health.probes.enabled=true` plus group mapping
(`liveness → livenessState`, `readiness → readinessState`) on the backend, and the four
public probe paths (`/actuator/health`, `/actuator/health/liveness`, `/actuator/health/readiness`,
`/actuator/prometheus`) permitted in the security chain. `test_backend_security_config_permits_the_probe_groups.py`
holds the wiring; `ActuatorMetricsContractTest` pins the widened permitAll list and the
exposure surface it serves. **Refinement from the sketch:** readiness tracks
`readinessState` (the application lifecycle) and deliberately *not* db/redis/storage/ai
reachability — dependency-gated readiness evicts a healthy pod from the Service endpoints
on a database blip and cascades restarts across the fleet. Dependency truth stays where it
already lived: `/api/v1/health` aggregates db/redis/storage/ai and answers 200 either way,
so a monitor reads *which* half is degraded instead of the orchestrator guessing. The
sketch's acceptance test (flip the DB, watch readiness flip) was replaced by this
contract: the flip belongs in the dependency report, not in the pod's routing eligibility.

### Epic 113 — Eureka multi-node peer config (optional, opt-in profile) **DONE (measured 2026-11-11)**
`discovery` gained an `application-peer.yml` (`peer` profile): client ON (register + fetch),
self-preservation back ON — the base keeps a lone registry client-off and evicting, because it
cannot tell a dead service from a network hiccup. Compose ships `discovery-peer` under the
opt-in `cloud` profile with `EUREKA_MAIN_PEER_ZONE` teaching the main registry the pair's zone
(Eureka's peer setup lists every node in each node's zone); Kubernetes ships the peer as a prod
overlay resource with a zone patch on the main discovery. `DiscoveryPeerProfileTests` (3/3,
offline, property-level) and the single-node default assertions in `DiscoveryApplicationTests`
(5/5) hold the wiring; the fleet gate grew a peer-wiring case. **Found while landing this: the
prod overlay had never been buildable** — `resources: [- ../base]` was one level short and every
`kubectl kustomize overlays/prod` died at evalsymlink since Epic 109, invisible to the text-only
gate. Fixed to `../../base`, and a new gate case refuses any resource path a kustomization names
that does not exist relative to it. Two-node boot stays documented manual verification (DEPLOYMENT
"Two-node registry"), not faked in CI.

### Epic 114 — Config Server security (opaque token) **DONE (measured 2026-11-10)**
`ConfigTokenFilter`+`ConfigTokenConfig` add an optional `X-Config-Token` header check gated by
`CONFIG_SERVER_TOKEN`: set it and every request except `/actuator/health` is refused without it;
unset keeps dev behavior. `ConfigServerTokenGateTest` proves refusal, admission, wrong-token refusal
and anonymous health probe (suite 9/9 green). Honest scope: a single opaque shared token (sufficient
for a single-node native server), not mTLS; mTLS and per-service client identity remain next-horizon.

## Sequencing notes
- 109 and 112 unblock real-world operability questions; 110–111 tighten the observability loop; 113–114 are advanced and only worth doing when a second instance is needed.
- Each epic must land with a gate (or a contract assertion if port of attack is a doc/K8s manifest, gate reads the manifests as text) and offline verification.
