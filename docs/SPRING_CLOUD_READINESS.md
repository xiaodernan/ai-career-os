# Spring Cloud readiness checklist

A short curl-driven check that the Spring Cloud wiring (Eureka, gateway, Config Server,
actuator, build identity and observability) a deploy claims is actually in place.

The services the checklist touches:

| Service | compose service | app name (Spring Cloud) | Port | Role |
|---|---|---|---|---|
| `backend` | `backend` | `career-os-backend` | :8080 | public API; registers (when its Eureka profile is on) |
| `gateway` | `gateway` | `career-os-gateway` | :8081 | browser edge; routes `/api/**`, LB |
| `discovery` | `discovery` | `career-os-discovery` | :8761 | Eureka dashboard; holds lease table |
| `config-server` | `config-server` | `career-os-config-server` | :8888 (opt-in profile `config`) | central outbound config (opt-in) |

## 1. Every service names its build

```bash
# backend (authenticated)
curl -s -H "Authorization: Bearer $AT"   http://127.0.0.1:8080/actuator/info
# gateway / discovery / config-server (unauthenticated dev, edge-locked in prod)
curl -s http://127.0.0.1:8081/actuator/info
curl -s http://127.0.0.1:8761/actuator/info
curl -s http://127.0.0.1:8888/actuator/info
```

Each answer must contain `app.build-sha` — a stale container answering an old commit
is the bug these markers exist to prevent (Epic 78 encodes it for the app build).

## 2. The edge routes, and only through Spring Cloud

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8081/actuator/health
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8081/api/v1/health
# with the ops gate set (Epic 108.15), the routes endpoint needs the header:
curl -s -H "X-Actuator-Token: $GWT" http://127.0.0.1:8081/actuator/gateway/routes | jq '.[].id'
```

A Spring Cloud wiring that is half-up still answers the first two probes — step 4 exists
because the first three cannot tell whether the edge routes through Spring Cloud's
load balancer or a hard-coded URL.

## 3. The registry answers

```bash
# a contract the compose stack satisfies (profile `app`)
curl -s http://127.0.0.1:8761/actuator/health        # {"status":"UP"...}
curl -s http://127.0.0.1:8081/actuator/info | jq '.app'
```

## 4. Backend talks to the engine — Spring Cloud LB

```bash
# the backend's `ai-service` selector is an address the load balancer chose,
# not a fixed hostname baked into the image
curl -s -H "Authorization: Bearer $AT" http://127.0.0.1:8080/api/v1/system/topology
curl -s -H "Authorization: Bearer $AT" http://127.0.0.1:8080/api/v1/system/resilience
```

`topology` lists every registered service with its instances and build metadata
(`registry` mode, `instances[].metadata.build-sha`); `resilience` shows the circuit
breakers guarding the ai-service bridge — including whether any of them is open.

## 5. The gates still pass

```bash
mvn -f backend/pom.xml -Dtest='ServiceTopologyServiceTest,ResilienceStatusServiceTest' -o test
cd ai-service && .venv/Scripts/python -m pytest tests/test_the_config_client_stays_opt_in.py \
  tests/test_the_spring_cloud_services_print_a_common_metrics_tag.py \
  tests/test_the_topology_page_reads_the_fleet_the_backend_writes.py -q
```

## Glossary

- **build-sha** — commit the image was built from; never secrets.
- **Eureka lease** — a service registered with the discovery server;
  its absence means the edge cannot see it.
- **native backend** (Config Server) — config from file/classpath, not git,
  because the runbook must work offline.

## Ownership

- The microservices posture is documented in `docs/MICROSERVICES.md` and
  `docs/EDGE_OPERATIONS_LOCKDOWN.md`; this file is the short operator version.
- The compose stack is `--profile app`; Config Server is `--profile config`.
