# Edge operations lockdown (Epic 108.15)

Production checklist for locking the gateway's operations surface so an operator
can reach it and nobody else can.

## Why

The edge (`gateway`, default `:8081`) carries
`health,info,gateway,metrics,circuitbreakers,circuitbreakerevents,prometheus` at `/actuator/**`.
With no token set the surface is open on the edge as deployed — fine in a laptop/test
stack that binds loopback behind an authenticating reverse proxy, and fine for a dev host,
but unsafe the moment the edge is published directly.

## Set it

Add this line to `.env.prod` (create or extend the prod env file; the variable is **not**
tracked in git and the pre-commit hook treats `.env.prod.example` as untrusted):

```bash
GATEWAY_ACTUATOR_TOKEN=<random-strong-token>
```

`docker-compose.prod.yml` reads the variable with `${GATEWAY_ACTUATOR_TOKEN}` (no default) — when the env
file sets it, the edge refuses the operations surface without the header; when it does not, the
edge serves as before (dev semantics). Leaving it unset is the choice a laptop or a loopback-only
deploy makes; the production plan is to set it.

## Wiring debug (Spring Cloud)

The edge also exposes `/actuator/conditions` behind the same gate, so an operator can see
why a Eureka/Config bean did or did not bind without opening the network -- e.g. the Eureka
client, the circuit breaker, or the config client. Same token as the rest of `/actuator/**`.

```bash
curl -s -H "X-Actuator-Token: <token>" http://127.0.0.1:8081/actuator/conditions | jq .
```

## Verify it

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8081/actuator/health           # 200 (probe stays open)
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8081/actuator/info             # 403
curl -s -o /dev/null -w "%{http_code}\n" -H "X-Actuator-Token: <token>" http://127.0.0.1:8081/actuator/info  # 200
```

## Unset

Nothing changes; the surface stays open as before (development uses that on loopback).

## Notes

- The token is a bearer token, not a full auth system — rotate it through `.env.prod`
  and the compose env the way any other secret.
- `X-Actuator-Token` on the request — not `Authorization` — so it never collides with
  the user JWT or the internal service token semantics.
