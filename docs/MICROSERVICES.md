# Microservices & Spring Cloud Architecture

This document describes the Spring Cloud microservices elements integrated into AI Career OS.
The goal is to provide production-oriented service discovery, edge routing, centralized
configuration (opt-in), resilience, and observability while preserving backward compatibility
with existing local/dev and env-driven deployments.

## 1. Components and responsibilities

| Component | Module/Service | Responsibility | Spring Cloud elements |
|---|---|---|---|
| Service Registry | `discovery/` (`career-os-discovery`) | Eureka server; source of truth for registered instances when discovery is enabled | Netflix Eureka Server, Actuator |
| API Gateway / Edge | `gateway/` (`career-os-gateway`) | Single browser-facing edge, routes `/api/**` to backend, request governance and resilience at the edge | Spring Cloud Gateway (WebFlux), CircuitBreaker (Reactor Resilience4j), LoadBalancer, Eureka Client (opt-in), Config Client (opt-in) |
| Domain Backend | `backend/` (`career-os-backend`) | Public API, auth/ownership boundary, orchestration, persistence, bridge to ai-service | Eureka Client (opt-in), Config Client (opt-in), CircuitBreaker Resilience4j (ai-service bridge), LoadBalancer support, Actuator observability |
| Config Server (opt-in) | `config-server/` (`career-os-config-server`) | Centralized externalized configuration via native file/classpath backend | Spring Cloud Config Server (native), Actuator |
| AI Engine | `ai-service/` (FastAPI) | LLM/RAG/agent/interview/feature engines (internal service) | Participates in W3C trace propagation and correlation (request/trace context echoed and logged) |
| Frontend | `frontend/` (Next.js) | User interface; consumes backend API and displays fleet/resilience state in monitoring views | Consumes `/api/v1/system/topology` and `/api/v1/system/resilience` |

Stateful dependencies (PostgreSQL+pgvector, Redis, MinIO) remain shared infrastructure services
as defined in `docker-compose.yml` / `docker-compose.prod.yml`.

## 2. Service discovery (Eureka, opt-in)

- **Registry**: `discovery` runs a standalone Eureka server (`:8761` by default), dashboard on `/`.
  - Single-node defaults prioritize correctness over preservation: self-preservation disabled and
    faster eviction interval (configurable) so dead instances are removed promptly.
  - Holds no durable data; restart cost is re-registration only.
- **Clients**: `backend` and `gateway` include Eureka client support but are **inert by default**
  (`eureka.client.enabled` / `*_EUREKA_ENABLED` toggles). Enabling the `eureka` profile/flags
  makes registration and (for gateway) registry-backed discovery authoritative.
- **Instance identity & metadata** (for operators and topology clarity):
  - `eureka.instance.instance-id`: `${spring.application.name}:${APP_BUILD_SHA:dev}:${server.port}`
  - `eureka.instance.metadata-map`: `build-sha`, `service`
  - Lease tuning (env-overridable): renewal 10s, expiration 30s on backend/gateway for responsive
    updates in opt-in discovery setups.
- **Topology visibility**: backend exposes authenticated `GET /api/v1/system/topology` (registry mode
  and instances as seen by the backend discovery client), surfaced in the frontend monitoring UI.

## 3. API Gateway (Spring Cloud Gateway)

- Edge entrypoint (`gateway`, default `:8081`) routes browser API traffic to the backend via
  `lb://backend` (service-id based routing; compatible with simple instances or Eureka-backed discovery).
- Request governance at the edge includes:
  - CORS alignment with backend and response-header dedupe
  - Forwarded-header handling with trusted proxy boundary
  - Removal/sanitization of sensitive internal headers from browser requests
  - Request size limiting, retry policy for safe/idempotent cases, and circuit-breaker fallback
    behavior for backend unavailability
  - Request/trace correlation propagation (see §6)
- Actuator endpoints exposed per gateway configuration for operations (health/info/gateway/metrics as configured).

## 4. Centralized configuration (Spring Cloud Config, opt-in)

- **Config Server** (`config-server`, default `:8888`, compose profile `config`):
  - Spring Cloud Config Server with **native** backend (`classpath:/config-repo` and mounted `/config`),
    no git dependency.
  - Serves shared and per-service configuration (`application.yml`, `career-os-backend.yml`,
    `career-os-gateway.yml`, `career-os-discovery.yml`) with non-sensitive example knobs.
  - Actuator: `health`, `info`, `env` exposed for operational verification.
- **Clients** (`backend`, `gateway`, `discovery`):
  - Include `spring-cloud-starter-config` but default to **disabled** (`spring.cloud.config.enabled=false`)
    with `spring.config.import=optional:configserver:`.
  - Enable explicitly via environment/config (e.g. `SPRING_CLOUD_CONFIG_ENABLED=true` and Config Server URI);
    `fail-fast` defaults to `false` to preserve startup resilience and existing deployments.
  - A contract gate (`ai-service/tests/test_the_config_client_stays_opt_in.py`) asserts the opt-in
    posture and the config-server's `config` compose profile.
- **Design constraint**: configuration centralization is additive and opt-in; env-driven and offline
  workflows remain valid defaults.

## 5. Resilience (Resilience4j / Spring Cloud CircuitBreaker)

- **Backend ai-service bridge** is protected by Resilience4j circuit breakers (per-origin and aggregate
  behavior as implemented in `HttpAiServiceClient` / resilience configuration), preventing cascading
  waits when the engine is unavailable and returning fast failures per existing error semantics.
- **Gateway edge** also applies circuit-breaker/retry policies on routed traffic as configured in
  `GatewayResilienceConfig` and the route definitions.
- **Operator visibility**:
  - Authenticated API: `GET /api/v1/system/resilience` reports breaker name, state and key metrics
    (sorted, deployment-wide view) for monitoring/UI and troubleshooting.
  - Authenticated actuator endpoints (backend and gateway): `/actuator/circuitbreakers`,
    `/actuator/circuitbreakerevents` (Spring Cloud/Resilience4j observability), while
    `/actuator/health` and `/actuator/prometheus` remain the public probe/scrape endpoints.
  - Authenticated `/actuator/info` publishes build identity (and backend ai-service breaker shape).
  - Gateway, discovery and config-server expose authenticated `/actuator/prometheus` (Meter registry
    pinned to the offline repository's 1.15.3); they remain behind authentication and are not permitAll.
  - Frontend monitoring page displays topology and resilience cards.

## 6. Distributed tracing and correlation

- **W3C trace context propagation** across the request chain:
  - Gateway validates/preserves or mints `traceparent` (and forwards `tracestate` as allowed),
    propagates/echoes correlation headers.
  - Backend propagates/echoes `X-Request-Id` and `traceparent`, records trace context (MDC/logging),
    and forwards to ai-service.
  - ai-service validates/preserves or mints `traceparent`, echoes headers, and emits `trace_id`
    in JSON logs; structured refusal error responses may include optional `requestId`/`traceId`
    for correlation without changing error code/message/status semantics.
- **CORS**: correlation headers are allowed/exposed as required for browser diagnostics.

## 7. Observability and build identity

- **Actuator/health/metrics**:
  - Backend: `/api/v1/health` remains the dependency report contract; `/actuator/health` and
    `/actuator/prometheus` are public probe/scrape endpoints; `/actuator/info` and Resilience4j
    actuator endpoints require authentication.
  - Gateway/Discovery/Config Server expose actuator endpoints appropriate to their role.
  - The edge carries an optional shared-secret gate for its operations surface: set `GATEWAY_ACTUATOR_TOKEN`
    and every `/actuator/**` needs the `X-Actuator-Token` header (`/actuator/health` stays open for the
    container probe); `GatewayActuatorGuard` refuses at the edge with 403 (`actuator-surface-not-exposed`)
    before the actuator is reached. When unset the surface stays open, as before (compose binds loopback;
    a production proxy must authenticate what it publishes). Runbook: `docs/EDGE_OPERATIONS_LOCKDOWN.md`.
    The edge also carries `/actuator/conditions` behind the same token (Epic 108.16) — the Spring Boot
    condition report, for an operator to see why a wiring bean did or did not match.
    The backend also exposes `/actuator/conditions` for the same Spring Cloud wiring debug (Epic 108.18) —
    behind its existing authentication, not permitAll. Use it to see why the Eureka client or
    circuit breaker did or did not match: a misrouted deployment fails fast there.
- **Build identity**:
  - `APP_BUILD_SHA` is propagated to service `info.app` metadata and Eureka instance metadata/IDs
    where applicable, enabling consistent instance identification across registry, actuator, and health views.
- **Monitoring UI**: fleet topology and circuit-breaker state are surfaced in the authenticated monitoring experience.
- **Metrics**: every Spring Cloud service pins \management.metrics.tags.application=\,
  so a shared scraper can aggregate \/actuator/prometheus\ by application
  (backend/gateway/discovery/config-server). A contract gate
  (\i-service/tests/test_the_spring_cloud_services_print_a_common_metrics_tag.py\) enforces it.

## 8. Opt-in enablement summary

| Capability | Default | How to enable |
|---|---|---|
| Eureka registration/discovery | Disabled | Set service-specific `*_EUREKA_ENABLED` / Spring profile `eureka` and configure `EUREKA_DEFAULT_ZONE` (see compose/profile wiring) |
| Config Server | Not started | `docker compose --profile config up -d config-server` (or equivalent) |
| Config Client (gateway/discovery/backend) | Disabled | `SPRING_CLOUD_CONFIG_ENABLED=true` and point to Config Server URI/import; keep `fail-fast=false` unless required |
| Resilience actuator endpoints (backend) | Exposed but authenticated | Access with valid credentials/proxy controls; `health`/`prometheus` remain permitAll |
| Trace propagation/correlation | Enabled in request path | No opt-in required; clients/proxies should forward/allow correlation headers |

### 8.1 Runnable opt-in check (no secrets, no live services)

With the `config` profile up, the Config Server serves the shared and per-service examples:

```bash
docker compose --profile config up -d config-server
curl -s http://127.0.0.1:8888/career-os-backend/default    # shared + career-os-backend.yml, must contain `careeros.config-server.service`
curl -s http://127.0.0.1:8888/actuator/health             # {"status":"UP"...}
```

Enable a client the same way (the example is inert by default, so this is opt-in only):

```bash
SPRING_CLOUD_CONFIG_ENABLED=true \
SPRING_CLOUD_CONFIG_URI=http://127.0.0.1:8888 \
< run backend|gateway|discovery as usual >
```

If Config Server is not up, the client keeps the `optional:` import and continues with env-driven
defaults (the contract gate `test_the_config_client_stays_opt_in.py` pins this posture).


## 9. Compatibility and safety notes

- Opt-in features must not break existing env-driven deployments, local development, or offline tests.
- Security boundaries remain unchanged: internal tokens/ownership checks stay enforced, actuator
  exposure beyond probe/scrape endpoints remains authenticated, and no secrets are committed in config examples.
- Verification is performed per batch with targeted offline tests/compiles and compose parse checks
  where relevant; measured results are recorded in `docs/ROADMAP.md` and related docs.
