# Deployment

How to bring AI Career OS up locally and what each knob controls. The stack is
five application services (discovery, gateway, backend, ai-service, frontend), an opt-in
Spring Cloud Config Server (`config-server`, Epic 103), plus three stateful
dependencies (PostgreSQL + pgvector, Redis, MinIO). For the Spring Cloud microservices
architecture (Eureka/Gateway/Config, resilience, tracing/observability) see
[MICROSERVICES.md](MICROSERVICES.md).

Redis is small but not optional: it backs only the rate limiter and the backend's
health ping. The client timeout is pinned to 500ms (`REDIS_TIMEOUT` /
`REDIS_CONNECT_TIMEOUT`) so an outage *degrades* the service — `/api/v1/health`
returns `{"status":"degraded","redis":false}` in about half a second — rather than
stalling every request on a client timeout. Raising those values trades that
degradation back for an outage that looks like a hang. See `docs/SECURITY.md` §3.

## Production Deployment

For production, use the dedicated production compose file with a `.env.prod` file
containing all secrets, passed to every command as `--env-file .env.prod`. The
production compose uses the `app` profile and adds resource limits, health checks,
and proper restart policies.

### Prerequisites

- Docker + Docker Compose v2
- A `.env.prod` file with all production secrets (copy `.env.prod.example` and fill in)
- A reverse proxy (nginx/Traefik/Caddy) for TLS termination in front of the stack
- DNS records pointing to the host

### Quick Start (Production)

```bash
# 1. Copy and edit the production environment file
cp .env.prod.example .env.prod
# Edit .env.prod with all required secrets

# 2. Start the production stack
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod --profile app up -d

# 3. Verify health
curl -f http://localhost:8080/api/v1/health
curl -f http://localhost:8000/health
curl -f http://localhost:3000
```

`--env-file` is the flag that matters here, and it is not the same thing as the
services' `env_file:` entries. Compose expands every `${...}` in the files before a
container exists, from the process environment and the file `--env-file` names —
`env_file:` only fills a container afterwards, and an `environment:` entry that
carries an interpolation overrides it. The override spells each required value
`${VAR:?...}`, so a command without the flag stops before anything is pulled and
names the variable, its message saying where to fill it; starting on empty
passwords is no longer a reachable state.

### Production Checklist

- [ ] All secrets in `.env.prod` are strong, unique, and not from `.env.example`
- [ ] `JWT_SECRET` is >= 64 random characters
- [ ] `APP_ENV=prod` (blocks the mock providers; with it the backend also refuses to
  start on any published secret, see the next item)
- [ ] Real LLM/embedding provider keys configured (not `mock`/`hash`)
- [ ] `APP_EMAIL_PROVIDER=smtp` with a reachable relay and a from address it
  accepts — with `APP_ENV=prod` the backend refuses to start on the console
  transport, which logs resets instead of mailing them (`ProductionGuard`; see
  [Email](#email))
- [ ] `APP_MAIL_LINK_SECRET` set to 32+ random bytes (`openssl rand -base64 48`).
  It signs the unsubscribe links in every letter; the dev default is published in
  this repository, so leaving it in prod lets anyone forge a stop-link
- [ ] `APP_MFA_SECRET` set to 32+ random bytes (`openssl rand -base64 48`). It
  seals every enrolled authenticator seed at rest (roadmap 36.1); the dev default
  is published here, so leaving it in prod is every account's second factor in a
  database dump. Rotating it makes every existing seed unreadable — those accounts
  sign in on their password until they enroll again
- [ ] `JWT_SECRET`, `APP_MAIL_LINK_SECRET`, `INTERNAL_API_TOKEN`, `POSTGRES_PASSWORD`
  and the object-store secret behind `MINIO_ROOT_PASSWORD` are not the repository's
  published defaults and do not begin with `CHANGE_ME` — booted with `APP_ENV=prod`,
  the backend refuses to start on any of them (it names the store's pair
  `MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY`), names every offender in one message, and
  exits instead of serving forgeable credentials (`ProductionGuard`; see
  [SECURITY.md](SECURITY.md#findings) finding #4). The store's user name may keep
  the shipped `careeros-minio-admin`; the refusal there is on `change-me` names.
- [ ] Web Push (optional): `APP_PUSH_VAPID_PUBLIC_KEY` and `APP_PUSH_VAPID_PRIVATE_KEY`
  are both set or both empty. With neither, browsers can register but no push leaves
  the backend and the boot logs "push is not configured"; one half refuses the boot
  (`PushConfig`). Set `APP_PUSH_CONTACT` to a `mailto:` or `https:` contact (empty
  falls back to `APP_WEB_BASE_URL`). Generate the pair with
  `npx web-push generate-vapid-keys`; the public key is also what the browser
  subscribes with, so it must be the one the frontend is built against — both
  compose files pass `APP_PUSH_VAPID_PUBLIC_KEY` into the frontend image as
  `NEXT_PUBLIC_VAPID_PUBLIC_KEY`, which Next inlines at build time, so changing the
  key needs a frontend rebuild (`docker compose build frontend`). An empty value
  ships a switch that reads "not configured" rather than a browser subscribed under
  a key nothing signs with
- [ ] `APP_WEB_BASE_URL` is the deployment's public origin (an `https://` URL), not
  the shipped `http://localhost:3000` and not `.env.prod.example`'s
  `your-domain.com` placeholder — every password-reset, email-change and
  unsubscribe link is built from it, and a prod boot refuses a loopback host, a
  non-http(s) value, the example domain, or an empty value (`ProductionGuard`;
  see [Email](#email))
- [ ] `APP_CORS_ORIGINS` names the shell's public origin — the origin of
  `APP_WEB_BASE_URL`, comma-separated, with no path or trailing slash. With
  `APP_ENV=prod` the backend refuses the dev `http://localhost:3000`, the example's
  `your-domain.com` entries, a spelling a browser's `Origin` header cannot equal,
  and a list that does not include the shell's origin (`ProductionGuard`; see
  [SECURITY.md](SECURITY.md#transport--headers))
- [ ] Reverse proxy (nginx/Traefik/Caddy) terminates TLS and forwards to:
  - Frontend: `http://frontend:3000`
  - Backend API: `http://backend:8080`
  - AI service: **not exposed** (internal only)
- [ ] Reverse proxy sets `X-Forwarded-Proto` and writes `X-Forwarded-For` with
  `$remote_addr` (overwrite, not `$proxy_add_x_forwarded_for`: the limiter reads the
  last hop, and an overwrite keeps the client's own text out of the header entirely)
- [ ] Backend runs with `APP_HTTP_TRUST_FORWARDED_FOR=true` — without it the limiter
  counts the proxy's socket address and every client shares one bucket; with the
  backend exposed directly, leave it off (see [SECURITY.md](SECURITY.md#findings))
- [ ] `/actuator/prometheus` restricted at the proxy to the scraper's address (public by default)
- [ ] edge operations surface locked in prod: `GATEWAY_ACTUATOR_TOKEN` set in the prod env file (`docs/EDGE_OPERATIONS_LOCKDOWN.md`) — unset keeps the edge surface open (dev semantics); prod plans to set it. Edge `/actuator/**` (except `/actuator/health`) refuses without `X-Actuator-Token` (Epic 108.15)
- [ ] DNS records point to the reverse proxy
- [ ] TLS certificates configured and auto-renewing (Let's Encrypt recommended)
- [ ] Nightly backups on a cron/timer (`scripts/backup.sh`: one `pg_dump`, one
  MinIO archive, checksums, `BACKUP_KEEP` full sets) and a restore drill run
  against the newest set (`scripts/restore_drill.sh`) — see
  [RUNBOOK.md](RUNBOOK.md#backups)
- [ ] MinIO bucket versioning enabled for object recovery
- [ ] Log aggregation configured (Loki/ELK/Datadog)
- [ ] Prometheus scraping `/actuator/prometheus` with `ops/prometheus/alerts.yml`
  loaded; each rule's page is a section of [RUNBOOK.md](RUNBOOK.md)

### Preflight gate (ai-service)

Before starting the stack, run the ai-service preflight against the production
environment. It catches configurations that boot fine and then fail badly — offline
providers in prod, the repo's published default `INTERNAL_API_TOKEN` (which would leave
`/internal/*` effectively unauthenticated), the development database password, a missing
API key, or an inverted DB pool. It is pure: no database or network is touched.

The backend carries the same gate inline: with `APP_ENV=prod`, `ProductionGuard`
refuses the Spring context on a published JWT secret, mail-link secret, internal
token, database password or object-store credential (or a `CHANGE_ME`/empty value),
on a link base the reader's browser cannot open (a loopback host, a non-http(s)
value, or the examples' `localhost`/`your-domain.com` placeholders), on a
cross-origin list no deployed shell can use (the dev origin, the example domain, a
spelling a browser's `Origin` header cannot equal, or a list missing the shell's own
origin), or on the console mail transport that would keep every reset link in the
log, and names every offender — a boot that would have served forgeable
credentials, reached production's database and bucket with a published password,
mailed every reset link to a machine the reader does not have, or blocked the real
page's API calls exits non-zero instead.

```bash
cd ai-service
APP_ENV=prod \
LLM_PROVIDER=openai_compat EMBEDDING_PROVIDER=openai \
INTERNAL_API_TOKEN="$INTERNAL_API_TOKEN" DATABASE_URL="$DATABASE_URL" \
LLM_API_KEY="$LLM_API_KEY" \
.venv/Scripts/python -m app.ops.preflight        # exit 1 on any blocking failure
.venv/Scripts/python -m app.ops.vector_index  # after the first ingestion: dimension-aware HNSW indexes
```

It prints `{ok, checks, failures, warnings}` as JSON. A `fail` (severity `fail`) blocks
and exits 1; a `warn` (e.g. `APP_ENV` is not `prod`, or the backend URL still points at
`localhost`) is reported but does not block. Make it the first step of the deploy script.
The same logic is unit-tested offline (`tests/test_preflight.py`), including a guard that
fails if `app/core/config.py`'s published defaults drift from the preflight's copy.

### Ports published by the production override

`docker-compose.prod.yml` republishes the five app services, and an entry written as
`HOST:CONTAINER` with no interface prefix is bound on every interface of the host. The
override therefore opens three ports the development file keeps to the machine:

| Service    | Host port | Reach           | Notes                                          |
|------------|-----------|-----------------|------------------------------------------------|
| ai-service | 8000      | `127.0.0.1`     | Internal-only by design; the override keeps it |
| backend    | 8080      | every interface | Reachable from the network, not just the host  |
| gateway    | 8081      | every interface | Optional edge; the browser may use it instead   |
| frontend   | 3000      | every interface | Reachable from the network, not just the host  |
| discovery  | —         | compose network | Registry; the override publishes no port for it |

So in the stack the Quick Start brings up (`docker-compose.yml` together with
`docker-compose.prod.yml`), `backend` on 8080, `gateway` on 8081 and `frontend` on
3000 answer to the network as well as through the reverse proxy — the proxy is not
the only path in.
Ports the override does not mention, `postgres` 5432, `redis` 16380 and `minio`
19000/19001, keep the development file's binding. If the host should not answer on
8080, 8081 and 3000 directly, bind them to `127.0.0.1` in your own override or firewall the
ports; `ai-service` stays reachable for local debugging over loopback and from inside
the compose network.

### Outbound network (egress)

The backend fetches whatever the reader subscribed to, so the host needs outbound
HTTPS to those feeds. Feeds whose source is a board (19.8) call the boards' public
APIs: allow `boards-api.greenhouse.io` and `api.lever.co` — EU Lever boards use
`api.eu.lever.co`. Every fetch, and every redirect hop, is checked against private,
loopback, link-local and carrier-grade addresses, so a feed cannot make the server
read its own network.

### Reverse Proxy Example (nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Frontend
    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        # Overwrite, do not append: the backend reads the hop this proxy wrote.
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api/v1/ {
        proxy_pass http://backend:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # AI Service (internal only - no external access)
    # location /internal/ { deny all; }
}
```

### Database Migrations

Flyway runs automatically on backend startup. Ensure the database user has
DDL permissions for the initial run. For zero-downtime deployments, run
migrations separately before deploying the new backend version.

### Backup & Recovery

Two scripts own this, so a restore is rehearsed rather than retyped at 3 a.m.:

```bash
# One set: a custom-format pg_dump, the MinIO data directory as a tar, and a
# sha256 file over both. The oldest set beyond BACKUP_KEEP is removed.
scripts/backup.sh

# The drill: verify the newest set's checksums, restore the dump into a scratch
# database on the same server, compare the table set and the applied Flyway
# count with the live database's, then drop the scratch database.
scripts/restore_drill.sh
```

Both read the running containers through `docker compose ps -q`, so they follow
the project's own names — `careeros-postgres-prod` and `careeros-minio-prod`
under the `-prod` overlay, or the dev stack's names — instead of a name typed
into the script; production is one
`COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml` away, not a second
copy. `KEEP_DRILL=1` keeps the scratch database for inspection; any mismatch
already exits 1 and keeps it.

[RUNBOOK.md](RUNBOOK.md#backups) has the cron example, what a failed night looks
like, and the by-hand restore for both the database and the objects.

Erasure (`POST /api/v1/me/erase`, roadmap 24.2) removes the account's rows and its
MinIO objects from the live system, but a backup set taken before the request still
contains them until `BACKUP_KEEP` rotations pass. Restoring an individual account
from an old set undoes an erasure the reader asked for: treat such a restore as a
data-protection decision, not a routine recovery, and prefer restoring the database
whole only into the scratch drill.

### Rolling Updates

```bash
# Build new images
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod build

# Rolling restart (one service at a time)
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d --no-deps backend
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d --no-deps ai-service
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d --no-deps frontend
```

The backend drains instead of cutting: `server.shutdown` is `graceful` with a
30-second `spring.lifecycle.timeout-per-shutdown-phase`, and both compose files give
Docker a 40-second `stop_grace_period` so the SIGKILL never pre-empts that bound. A
request still running at 30 seconds — typically a long AI stream — is cut and the
client retries; anything that finishes sooner is answered. A scheduled sweep stops with
the context and is not resumed. See RUNBOOK's "A redeploy finishes what it started".

### Monitoring Endpoints

| Service    | Health Check                    | Metrics                    |
|------------|---------------------------------|----------------------------|
| Backend    | `GET /api/v1/health`            | Prometheus at `/actuator/prometheus` (Micrometer); orchestrator probe at `/actuator/health`. The custom `/api/v1/health` is the deployment's dependency report: `db`, `redis`, `storage` and `ai` booleans, with `status: ok` only when all four answer. It answers **200 either way** so a monitor reads which half is down instead of guessing from a refusal; the four probes run together under one 2-second bound. Resilience4j circuit breaker actuator endpoints (`/actuator/circuitbreakers`, `/actuator/circuitbreakerevents`) and `/actuator/info` are exposed for Spring Cloud observability but require authentication (not permitAll). |
| AI Service | `GET /health`                   | None. The service is internal-only and logs to stdout; there is no `/metrics` route. The dependency report asks this route with a 2-second bound (`ai: true/false`). The body also names the provider halves and whether each can actually serve: `llm_ready` / `embedding_ready` are measured by building the configured provider through the same factories the AI calls use, so a stack that named `openai_compat` without a key reports `status: ok` (the process is alive) alongside `llm_ready: false` (it cannot serve) — the answer a monitor reads instead of a green probe over calls that all 500. |
| Gateway    | `GET /actuator/health`          | Spring Cloud Gateway's own actuator; `/actuator/metrics/gateway.ratelimit.refused` counts token-bucket refusals without a caller tag. Authenticated Spring Cloud observability endpoints also expose `/actuator/gateway`, `/actuator/metrics`, `/actuator/circuitbreakers`, `/actuator/circuitbreakerevents` and `/actuator/prometheus`. The custom `backend` indicator asks the backend's `/api/v1/health` under a 2-second bound and copies its `status` into `components.backend`; the line answers 503 while the backend is unreachable, which is also what the container probe reads. |
| Discovery  | `GET /actuator/health`          | Eureka's own actuator. The dashboard at `/` is the operator's view of the same lease table the edge consumes; the production override publishes no port, so it is reachable only inside the compose network. |
| Frontend   | `GET /` (200 OK)                | —                          |
| Postgres   | `pg_isready`                    | `pg_stat_statements` (needs `shared_preload_libraries`, which the compose image does not enable) |
| Redis      | `redis-cli`                     | `INFO`                     |
| MinIO      | `mc ready local`                | Prometheus exporter at `/minio/v2/metrics/cluster` (MinIO serves it by default) |

The families the nightly rules read are the scheduler's —
`careeros_ingestion_runs_total{status}` and
`careeros_ingestion_last_success_timestamp` — the AI budget's —
`careeros_ai_cost_usd_24h`, `careeros_ai_tokens_24h` and `careeros_ai_calls_24h`,
recomputed from `ai_usage_events` every minute — the install's own verdict —
`careeros_nightly_last_finished_timestamp` and
`careeros_nightly_consecutive_failures`, moved by each recorded night and once at
boot — and the weekly letter's —
`careeros_digest_delivery_total{outcome}`, `sent` or `refused` per attempt, and
`careeros_digest_last_delivered_timestamp`, moved only by an accepted letter.
`ops/prometheus/alerts.yml` carries the fourteen rules and each one links its page in
[RUNBOOK.md](RUNBOOK.md).

The limiter exports one more family for dashboards rather than alarms:
`careeros_ratelimit_decisions_total{bucket,outcome}` — `auth`, `ai` or `mail` by
`allowed` or `denied`, moved by every request the filter classifies, with the
fail-open branch counted as `allowed` because that is the decision the server
made. No nightly rule reads it: a refusal rate has no known-good baseline yet,
and an alarm that guessed one would page on a busy minute.

The retention sweep exports `careeros_retention_deleted_rows_total{table}` for
`refresh_tokens`, `password_reset_tokens` and `email_change_tokens`, moved by the
nightly 04:47 UTC delete of rows whose expiry is more than
`RETENTION_EXPIRED_TOKEN_DAYS` (30 by default) in the past, and for `documents` and
`document_chunks`, moved by the same pass deleting rows whose retirement is more than
`RETENTION_RETIRED_DOCUMENT_DAYS` (180 by default) in the past. The evidence tables get
separate readings because they are one statement's work — the chunks leave through the
schema's cascade, not a delete anyone calls — and an operator watching either table grow
back can only act on a count that names it. A table whose delete fails is logged and
leaves no reading, so a quiet night and a broken sweep are different shapes on the
dashboard. The sweep deliberately leaves the tables whose rows are visible history — AI
usage events behind the activity totals, notification read state, ingestion runs, weekly
letters — because deleting those rows would rewrite a screen or re-announce a story the
reader already settled. V23 adds an `expires_at` index to each of the three swept
credential tables and V31 a partial index on the retired slice of `documents`, so both
halves of the nightly work stay range reads as the tables grow.

A retired row that a source still points at is left in place — the delete path drops the
source in the transaction that retires the copy, so this is an anomaly, not a category —
and it is logged as "Retention sweep left N retired document row(s)" rather than counted
as a failure. Read that line as a thing to look at, not to fix tonight: the rows are
still retired, so nothing is quotable, and they will be purged the day the source row
goes.

The sweep also exports `careeros_retention_last_sweep_timestamp`, moved at the
end of every completed pass, with or without deletions. The counter cannot say
whether the clock still runs — a stopped sweep leaves its last value on the
scrape — so `CareerOSRetentionSweepStale` fires (warning) when the heartbeat is
more than 36 hours old, twice the daily cadence. A pass whose tables failed
still moves it; the failures are visible as "Retention sweep failed for" in the
log and as a missing per-table series.

A delete that retires an ingested copy asks the object store for the bytes behind it, and
`careeros_storage_objects_reclaimed_total{outcome}` moves once per key it handed back:
`deleted` when no row still names the key, `referenced` when another row does, and `failed`
when the store refused. Resume uploads put one object behind two rows — the resume serves it
as the original file and the document row is the copy the AI quotes — so the first of the two
to go records `referenced` and keeps the bytes. The nightly purge moves the same family for
the rows it retires out of the audit window, which is where a `failed` reading changes
meaning: an item delete leaves the retired row naming its key, so account erasure can finish
a reclaim the store refused, while a purged row has no trail and the object is an orphan.
The WARN line the same failure logs names the key, and that is the list to work from.
No nightly rule reads the family: an object that outlives a row is not an outage, and a
counter with no baseline would alarm on a quiet week. An orphan is now a category with a
remover rather than a permanent loss — the sweep below walks the bucket itself.

The nightly sweep also asks the object store what the bucket holds, and
`careeros_storage_objects_judged_total{outcome}` moves once per object that listing showed:
`named` when any row still points at the key in any status — a retired row is the trail 44.2
leaves a refused reclaim on, not garbage — `young` when no row names it but it is inside
`RETENTION_UNNAMED_OBJECT_DAYS` (7 by default), which is what keeps an upload that has stored
its bytes and not yet committed its row from losing them, `deleted` when the sweep reclaimed
it, and `failed` when the store would not give it back. The four outcomes add up to the
listing, so a pass that ended early shows as a sum that does not close rather than as a quiet
night. A second family counts the pass instead of the objects:
`careeros_storage_bucket_reads_total{outcome}` moves once per night with `listed` or `refused`,
and `CareerOSBucketListingRefused` pages on a `refused`. That rule exists because the retention
sweep's clock moves through a night that could not read the bucket — the pass finishes, its
tables and its purge run — so a store that refuses the listing would otherwise look exactly
like a bucket that holds nothing, and nothing on that path deletes. `objects_judged` carries no
rule of its own for the same reason the family above does not: one object the store would not
release is retried by the next night and named in the log meanwhile.

### Every Meter and What Watches It

The table is the roster, not a summary: every meter the backend registers is one row, and
`ai-service/tests/test_the_alarms_name_metrics_that_ship_and_a_page_that_says_what_to_do.py`
walks the Java files that consult `MeterRegistry`, renders each dotted Micrometer name the way the
exporter will (`careeros.ingestion.runs` arrives as `careeros_ingestion_runs_total`, and the
`_total` is the exporter's suffix rather than a string the Java ever writes), and requires this
table to hold exactly one row per meter. `Rule that reads it` is checked against the expressions
themselves, in both directions: the rules named for a row are exactly the rules whose `expr` reads
that series, so a row cannot claim a watch that was deleted and a new rule cannot read a meter this
page leaves naming another one. A `—` is a decision with a reason attached, and the reason is what
the row exists to carry -- the prose above explains each family at length, and this column says
which reading answers the operator's question instead of an alarm.

| Meter as the scrape renders it | Rule that reads it | What the reading is for |
|--------------------------------|--------------------|-------------------------|
| `careeros_ai_calls_24h` | — | Call count prices nothing by itself -- one expensive call and a thousand cheap ones read the same -- so `CareerOSAiBudgetBurn` holds the only number, and this is the dashboard's shape of the same rolling 24 hours. |
| `careeros_ai_cost_usd_24h` | `CareerOSAiBudgetBurn` | The trailing 24 hours of the AI ledger, recomputed every minute from `ai_usage_events`; above 5 USD for 15 minutes the budget rule fires (warning). |
| `careeros_ai_tokens_24h` | — | The dollar figure this gauge decomposes is the alarmed half. A raw token count has no threshold of its own, because a busy day inside the budget is not a fault. |
| `careeros_digest_delivery_total` | `CareerOSDigestDeliveryFailing` | One reading per weekly-letter attempt, tagged `sent` or `refused`; the first refusal inside six hours fires, because the relay is the fault an operator has to fix rather than one the retry clock can outlast. |
| `careeros_circuitbreaker_open` | `CareerOSCircuitBreakerOpen` | One untagged gauge: 1 while any Resilience4j breaker in the ai-service bridge is open, 0 otherwise. The exhausted queue is the only shape of an engine-door refusal that does not look like a bad request; alarming on it is the bridge telling the operator the door is gone, not the client. |
| `careeros_digest_last_delivered_timestamp` | — | Moved only by an accepted letter, so a week with no applications leaves it flat and that is healthy. `CareerOSDigestSweepStale` watches the compose clock; the delivery rule watches the relay. |
| `careeros_digest_last_sweep_timestamp` | `CareerOSDigestSweepStale` | The Monday compose's own pass marker, moved by every completed pass. Eight days of silence fires, because a week that never ran cannot be recomposed through any route. |
| `careeros_ingestion_last_success_timestamp` | `CareerOSIngestionNightMissed` | The last run that ended `completed`; 26 hours (93600 seconds) without one fires critical, whether the night never started or every feed in it failed. |
| `careeros_ingestion_runs_total` | `CareerOSIngestionFailing` | One reading per run, tagged by status. More than half failed across at least three runs in six hours fires warning -- a majority is the fetcher's problem, one dead feed is that feed's own. |
| `careeros_nightly_consecutive_failures` | `CareerOSNightlyVerificationFailing` | The install's own streak of failed nights, moved as each night is recorded. Two or more fires, which is the same line the nightly card warns at. |
| `careeros_nightly_last_finished_timestamp` | `CareerOSNightlyVerificationStale` | The last recorded verification night. 36 hours (129600 seconds) of silence fires critical, the service's own `STALE_AFTER_HOURS` rendered as seconds. |
| `careeros_push_delivery_total` | `CareerOSPushDeliveryFailing` | One reading per browser wake, tagged `sent`, `gone`, `refused` or `not_configured`. Three refusals in a day fires warning; the other outcomes are not faults, which is why the rule reads only this tag. |
| `careeros_ratelimit_decisions_total` | — | `auth`, `ai` or `mail` by `allowed` or `denied`, moved by every request the filter classifies. No known-good refusal rate exists yet, so any threshold would page on a busy minute; the family is exported for dashboards until a baseline is measured. |
| `careeros_reminders_last_tick_timestamp` | `CareerOSReminderClockStale` | The minute clock's own marker, moved at the end of every tick whether or not anything was due. Five missed ticks (300 seconds) fires, which tells a stopped scheduler from an empty board. |
| `careeros_retention_deleted_rows_total` | — | Rows per table the 04:47 sweep deleted. A stopped sweep leaves the counter at its last value, indistinguishable from a quiet night, and the first purge of a backlog would cross any rate threshold; the sweep's timestamp is the alarm. |
| `careeros_retention_last_sweep_timestamp` | `CareerOSRetentionSweepStale` | Moved at the end of every completed pass, with or without deletions; 36 hours of silence fires. A pass whose tables failed still moves it, and those failures are a log line plus a missing per-table series. |
| `careeros_signals_delivery_total` | `CareerOSSignalMailFailing` | Account letters accepted and refused, the morning letter and a reminder's own letter alike, because the counter is of letters and not of one kind. Three refusals in six hours fires. |
| `careeros_signals_last_delivered_timestamp` | — | The last morning the relay accepted a letter, which a quiet morning never moves. The sweep gauge covers the clock and the refusal counter covers the relay, leaving this as the dashboard's acceptance reading. |
| `careeros_signals_last_sweep_timestamp` | `CareerOSSignalSweepStale` | The morning sweep's own pass marker; 36 hours (129600 seconds) without a completed pass fires, which is the failure the delivery rules cannot see. |
| `careeros_storage_bucket_reads_total` | `CareerOSBucketListingRefused` | One reading per nightly pass, `listed` or `refused`. The retention clock moves through a night whose listing the store refused, so this is the only series that says the bucket half of the night did not run. |
| `careeros_storage_objects_judged_total` | — | One reading per object the listing showed, across `named`, `young`, `deleted` and `failed`, and the four sum to the listing. A store that would not release one object is retried the next night and named in the WARN line meanwhile, so this is the dashboard companion to the listing rule rather than a second judgement. |
| `careeros_storage_objects_reclaimed_total` | — | One reading per key the delete path or the purge handed back (`deleted`, `referenced`, `failed`). An object that outlives its row is a storage cost, not an outage, and a counter with no baseline would page on a quiet week. |

### Startup gating (healthchecks)

The five application services are probed, not assumed. Each healthcheck fetches the
service's own route on the container's loopback and accepts its 200; `depends_on` then
waits for `service_healthy`, so `--profile app up -d` no longer returns while a
dependency is still booting. A degraded dependency does not fail the backend's probe —
`/api/v1/health` answers 200 with `status: degraded` — so a transient database or Redis
outage is reported in `docker compose ps` rather than restarted by Docker.

| Service    | Probe (inside the container)                         | Starts after                                   |
|------------|------------------------------------------------------|------------------------------------------------|
| ai-service | `python -c` GET `http://127.0.0.1:8000/health`       | postgres healthy                               |
| backend    | `wget` GET `http://127.0.0.1:8080/api/v1/health`     | postgres, redis, minio, ai-service, discovery healthy |
| gateway    | `wget` GET `http://127.0.0.1:8081/actuator/health`   | backend and discovery healthy                  |
| frontend   | `node -e` fetch `http://localhost:3000/`             | backend healthy                                |
| discovery  | `wget` GET `http://127.0.0.1:8761/actuator/health`   | nothing; its state is the leases it receives   |

The production override carries the same probes; `ai-service` there also waits for Redis.
A probe's port is a container port the service publishes, and its path is the route in
the table above — `ai-service/tests/test_the_stack_waits_for_an_app_that_answers.py`
refuses, by name, an application service with no probe, a dependency without a health
condition, and a probe pointed at a port the service does not publish.

### Recording the nightly run

The scheduled workflow (`.github/workflows/ci.yml`, 03:17 UTC) ends with a step that
runs even when the night failed. It posts the job's own step outcomes to
`POST /api/internal/nightly-reports`, and the monitoring page reads the history back
over `GET /api/v1/monitoring/nightly-reports`. Two repository settings arm it:

| Kind | Name | Value |
|---|---|---|
| Variable | `CAREEROS_OPS_URL` | the backend's base URL as the runner sees it, e.g. `https://careeros.example.com` — the recorder appends `/api/internal/nightly-reports` |
| Secret | `CAREEROS_INTERNAL_TOKEN` | the same value as `INTERNAL_API_TOKEN` |

Left unset (forks, dry runs), the recorder builds the record and prints it but posts
nothing, so the job stays green and says the night was not recorded. A set URL whose
post fails is a red step: keeping the record is the step's whole purpose.

Posting is idempotent on the night, not on the attempt: a retry carries the same
source and the same start/finish span, and the backend answers it with the row the
first attempt wrote instead of inserting a second. A night retried after a timeout is
still one night, so the history does not grow a duplicate that the failure-streak
alarm would count twice.

---

How to bring AI Career OS up locally and what each knob controls. The stack is
five application services (discovery, gateway, backend, ai-service, frontend) plus three stateful
dependencies (PostgreSQL + pgvector, Redis, MinIO).

## Prerequisites

- Docker + Docker Compose v2 (for the infra and the `app` profile).
- Java 21+ and Maven (only if you run `backend/` outside Docker).
- Python 3.11 with a venv (only if you run `ai-service/` outside Docker).
- Node 20+ (only if you run `frontend/` outside Docker).

## Configure the environment

```bash
cp .env.example .env
# then edit .env — at minimum set:
#   POSTGRES_PASSWORD, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
#   JWT_SECRET            (>= 64 random chars)
#   INTERNAL_API_TOKEN    (same value in backend and ai-service)
#   LLM_API_KEY / EMBEDDING_API_KEY  (for a real provider, see below)
```

Never commit `.env`. `.env.example` is the single source of truth for the full
variable list a checkout sets; the one it does not carry,
`APP_HTTP_TRUST_FORWARDED_FOR`, describes the network a deployment sits behind
and is set from the production checklist above.

## Run with Docker (recommended)

Infra only (Postgres, Redis, MinIO + one-shot bucket init + the demo job seed):

```bash
docker compose up -d postgres redis minio minio-init seed-jobs
```

`seed-jobs` is a one-shot job-market loader: it waits for Flyway to have created `jobs`,
then loads `scripts/seed/01_jobs.sql`. It is idempotent and safe on every `up`, and it
skips itself (after ~120s) rather than failing when the schema is not there yet — run
`docker compose run --rm seed-jobs` to retry it on its own.

Full application stack on top of the infra — the five app services live behind
the `app` profile:

```bash
docker compose --profile app up -d
```

### Ports published by `docker-compose.yml` (development)

`docker-compose.yml` publishes these host ports, and the Reach column is the interface
each one is bound to, so the development stack answers on the machine that runs it:

| Service    | Host port | Reach       | Notes                                            |
|------------|-----------|-------------|--------------------------------------------------|
| frontend   | 3000      | `127.0.0.1` | Next.js; `NEXT_PUBLIC_API_BASE_URL` → backend    |
| backend    | 8080      | `127.0.0.1` | Public REST API under `/api/v1`                  |
| gateway    | 8081      | `127.0.0.1` | Optional edge; forwards `/api/**` to `backend:8080` |
| discovery  | 8761      | `127.0.0.1` | Registry; lease dashboard at `/`                  |
| ai-service | 8000      | `127.0.0.1` | Internal-only; not exposed to browsers           |
| postgres   | 5432      | `127.0.0.1` | pgvector `pg16` image                            |
| redis      | 16380     | `127.0.0.1` | host 16380 → container 6379 (avoids local clash) |
| minio      | 19000     | `127.0.0.1` | S3 API; console on 19001                         |
| minio      | 19001     | `127.0.0.1` | S3 web console                                   |

Inside the compose network the services reach each other by name
(`postgres`, `redis`, `minio`, `ai-service:8000`, `backend:8080`, `discovery:8761`) — see the
`environment:` overrides in `docker-compose.yml`.

The gateway is optional: the default `NEXT_PUBLIC_API_BASE_URL` still points the
browser at `backend:8080` directly. To route every API call through the edge, build
the frontend with `NEXT_PUBLIC_API_BASE_URL=http://localhost:8081/api/v1` (or the
production host's `/api/v1` behind the reverse proxy) and set `GATEWAY_CORS_ORIGINS`
to the browser's origin. The gateway answers `GET /actuator/health` with the backend's
own status in `components.backend`, and a backend that is down is a 503 with
`{"error":"backend-unavailable"}` rather than a connection error.

The route addresses `lb://backend` through Spring Cloud's discovery abstraction. In the
development default (and any laptop without the registry) the simple client holds the
list: `GATEWAY_BACKEND_URI` is instance zero and the address the health indicator asks,
and a second backend is a configuration change -- give
`spring.cloud.discovery.client.simple.instances.backend[1].uri` (or a `[1].host` /
`[1].port` pair) and the load-balancer spreads reads across both. In the compose stack
the `eureka` profile hands the same route to the registry instead; see
[Service registry (Eureka)](#service-registry-eureka).

The edge also answers once. Both it and the backend write
`Access-Control-Allow-Origin`, and a browser rejects a response carrying it twice, so
the duplicate is removed before the answer leaves this process. A request body above
30 MB is refused with `413` before it reaches a backend parser;
`GATEWAY_MAX_REQUEST_SIZE` moves that line, and it should stay above the backend's own
25 MB multipart cap so the backend remains the authority on files it would accept.

The edge also knows which door is not the browser's. `/api/internal/**` is answered
`403` here and the backend is never called; a browser-supplied `X-Internal-Token`,
`Forwarded`, or `X-Forwarded-*` chain is removed before the edge writes its own
observed values, so an internal credential or a claimed address cannot be smuggled
through the front door.

The edge writes `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Forwarded-Host` and
`X-Forwarded-Port` from the connection it sees, after removing any that arrived, so the
backend's logs name the caller rather than a value the caller chose. 4.3 only writes
those headers when `trusted-proxies` admits the caller; `GATEWAY_TRUSTED_PROXIES`
defaults to `.*` because the edge itself is the trust boundary, and the strip above is
what keeps that default from becoming "trust the browser". If a reverse proxy sits in
front, the address the edge records is the proxy's -- that is the cost of not trusting
a chain the browser can write. A deployment that must preserve the proxied address can
replace this pair of behaviours explicitly rather than loosening the default.

## Service registry (Eureka)

The edge and the backend can learn addresses from a registry instead of their own
configuration lists. The registry is its own process (`discovery/`, Spring Cloud
Netflix Eureka on 8761); the compose stack runs it under the `app` profile and both
citizens register with it.

The switch is one profile: `SPRING_PROFILES_ACTIVE=eureka`. Outside it,
`eureka.client.enabled` is false and nothing contacts a registry -- the gateway keeps
its simple instance list and the backend its `AI_SERVICE_BASE_URL` list, which is what
every laptop and every unit test use. Inside it:

- the gateway empties its simple list, so the registry is the only answer for
  `backend`; a configured address left beside it is an address the operator cannot
  see, and roughly half the edge's decisions would ignore the registry;
- the backend registers itself (`BACKEND`), and the gateway appears as
  `CAREER-OS-GATEWAY`;
- `EUREKA_DEFAULT_ZONE` names the registry (`http://discovery:8761/eureka/` in
  compose).

Open `http://localhost:8761/` in the development stack to see the leases. The
production override publishes no port for it, so the dashboard is reachable only from
the compose network (port-forward, or `docker compose exec`).

A single-node registry disables self-preservation (`EUREKA_SELF_PRESERVATION=false`):
with no peers it cannot tell a dead service from a network partition, and keeping dead
leases would route traffic to a process that is gone. Eviction runs every five seconds
rather than the default minute, so a redeploy is a short gap instead of a minute of
refusals.

The registry holds no durable data -- its state is the set of live leases -- so a
restart costs one registration round. Losing it does not stop the stack: the edge
keeps its last answer and the backend keeps serving; new instances are simply not
discovered until it returns.

## Spring Cloud Config Server (opt-in, Epic 103)

An opt-in Config Server centralizes externalized configuration for the Java services
without requiring a git backend. It is not started by default.

- **Profiles**: `docker compose --profile config up -d config-server` (dev) or add
  the `config-server` service in an override. The dev compose publishes
  `127.0.0.1:8888` and mounts `./config-server/src/main/resources/config-repo` to
  `/config` for local overrides.
- **Backend/naming**: native file/classpath backend (`spring.profiles.active=native`),
  default port `8888`. The config repo can hold shared `application.yml` and
  per-service files (`career-os-backend.yml`, `career-os-gateway.yml`, `career-os-discovery.yml`).
- **Client opt-in**: `gateway`, `discovery` and `backend` ship `spring-cloud-starter-config`
  with `spring.cloud.config.enabled=false` by default and
  `spring.config.import=optional:configserver:`. Enable with
  `SPRING_CLOUD_CONFIG_ENABLED=true` and set `spring.cloud.config.uri` (e.g.
  `http://config-server:8888`) or `spring.config.import=configserver:http://config-server:8888`;
  `fail-fast` defaults to `false`. Existing env-driven deployments remain unchanged.
- **Health/actuator**: `GET /actuator/health` (and `info`, `env`) are exposed by the
  config server. For the runnable opt-in check and the full microservices architecture, see
  [MICROSERVICES.md](MICROSERVICES.md) §9.1.

## Kubernetes (opt-in, Epic 109)

A Kustomize bundle mirroring the `docker-compose.yml` fleet lives under `deploy/k8s/`.
It is operator-driven: it is **not** started by default, and you must create your own
Secret before applying (the example manifest deliberately holds `CHANGE_ME` placeholders).

- **Base** (`deploy/k8s/base`): namespace, ConfigMap, non-secret example Secret, StatefulSet for
  Postgres with PVC, Deployments for Redis/MinIO/ai-service/Discovery/Backend/Gateway/Config-Server/Frontend with
  liveness+readiness probes (Spring Cloud services use the actuator liveness/readiness groups,
  the ai-service `/health`, the frontend `/`), PersistentVolumeClaims for postgres and minio,
  PDBs for backend/gateway/frontend/ai-service, and a NetworkPolicy allowing only inter-service + DNS traffic.
- **Prod overlay** (`deploy/k8s/overlays/prod`): namespace `careeros-prod`, `ai-service`/`backend`/`frontend`
  scaled to 3 replicas.
- **Apply**: create a cluster, put a real secret in place (`kubectl -n careeros create secret generic careeros-secrets`
  with the keys shown in `deploy/k8s/base/secret.example.yaml`), then `kubectl apply -k deploy/k8s/base` or
  `kubectl apply -k deploy/k8s/overlays/prod`.
- **Images**: the manifest references the same image repositories the Dockerfile build used in compose. In a
  registry-enabled cluster, replace `:latest` in each image field with a pinned digest.
- **Validation**: `kubectl kustomize deploy/k8s/base` (and the prod overlay) succeeds offline; the contract gate
  `ai-service/tests/test_the_k8s_manifests_define_a_working_fleet.py` pins the topology invariant.

## Run services locally against Docker infra

Useful when iterating on one service. Start the infra (above), then:

```bash
# backend
cd backend && mvn spring-boot:run

# ai-service
cd ai-service && python -m venv .venv && .venv/Scripts/activate  # or source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt && uvicorn app.main:app --port 8000

# frontend
cd frontend && npm install && npm run dev
```

Point each service at `localhost` via `.env` (the `.env.example` defaults assume
local execution; Docker overrides them through `environment:`).

## AI providers

ai-service reads the provider selection from env:

- `LLM_PROVIDER` — `openai_compat` | `anthropic` | `ollama` | `mock`.
- `EMBEDDING_PROVIDER` — `openai` | `ollama` | `hash`.
- `VOICE_PROVIDER` — `none` (default) | `openai_compat` | `mock`. `none` leaves the
  interview text-only and the runner uses the browser's own speech APIs. The real
  provider serves `/audio/transcriptions` and `/audio/speech` at `VOICE_BASE_URL`
  (defaults to the LLM base) with `VOICE_API_KEY` (defaults to the LLM key). `mock`
  is refused when `APP_ENV=prod`, exactly like the LLM mock.

Two offline-only escape hatches for tests and first-run dev: `mock` LLM and
`hash` embeddings. The app **refuses to boot with `LLM_PROVIDER=mock` when
`APP_ENV=prod`** (see `app/main.py`), and `hash` embeddings give limited
retrieval quality — use a real embedding provider for anything beyond a smoke
test.

### Several engine nodes, and the rest state (Epics 85.1-85.2)

The backend reaches ai-service as a service, not an address. By default `AI_SERVICE_BASE_URL`
is the only instance. Set `AI_SERVICE_INSTANCES` to a comma-separated list of absolute
http(s) origins (`http://ai-node-1:8000,http://ai-node-2:8000`) and every outbound AI call
is handed to the next instance by Spring Cloud LoadBalancer, cycling in the configured
order. Entries are validated at boot: a missing scheme, a path or a query stops the start
with the offending entry named, rather than surfacing later as a 502.

`GET /api/v1/health` asks every instance and reports `ai: true` when any of them answers;
one dead replica does not take the line down while the bridge still serves from the others.
`aiNodes` lists each configured origin with its own `up` flag (86.2), so a quiet replica is
visible rather than only implied.

Failure is counted per node (87.1): the circuit guard keeps one breaker per origin, all in
the same shape — after five recorded calls in a ten-call window, half of them failing, that
node rests for thirty seconds. Calls the balancer addresses to other nodes keep leaving, and
`/health` shows that node down while the others stay up. The whole-bridge breaker still
exists, used only by a caller that cannot name a door. Refusals from the engine (4xx) are not
failures — the engine answered. The thresholds live in `AiServiceResilienceConfig`; raise the
thirty-second rest if the engine takes longer to come back.

Failover is one hop at a time (87.2): a door whose breaker is resting, or whose connection
was refused before the request left, hands the same call to the next configured origin.
A read timeout is never retried — the engine may have started the work, and repeating it on
a second node would repeat the work.

## Email

Outbound mail (password resets, the Monday letter and the morning signal mail)
leaves through the transport `APP_EMAIL_PROVIDER` names:

- `console` (the default) logs each letter instead of sending it. The body — a
  reset link carrying a usable token — is withheld unless
  `APP_EMAIL_CONSOLE_LOGBODY=true`; the development compose sets it so the flow
  can be walked by hand.
- `smtp` hands the letter to the relay at `APP_EMAIL_SMTP_HOST` /
  `APP_EMAIL_SMTP_PORT` (587 by default), authenticating with
  `APP_EMAIL_SMTP_USERNAME` / `APP_EMAIL_SMTP_PASSWORD` when a username is set.
  On 587 set `APP_EMAIL_SMTP_STARTTLS=true` (the default); on 465 set
  `APP_EMAIL_SMTP_SSL=true` instead — exactly one of the two, and the boot
  refuses both. `APP_EMAIL_FROM` is the address the relay sends as.

`smtp` refuses to boot without a host and a from address, and every SMTP call is
capped at 5 seconds, so a relay that is down fails the request that needed the
mail instead of holding it open. A refused letter is an error the caller sees: a
reset mail silently dropped is worse than a retry. With `APP_ENV=prod` the boot
refuses `console` — and a blank value, whose default is `console` — naming
`APP_EMAIL_PROVIDER` in `ProductionGuard`'s message, because a production reset
link that goes into the log never reaches the mailbox.

The weekly letter rides the same transport. The Monday sweep writes the week that
just ended, mails each letter, and keeps the outcome on the letter's row
(`delivered_at`, `delivery_error`, `delivery_attempts`). A letter that already left
is not mailed again when that week is recomposed, so re-running the sweep cannot put
a second copy in a mailbox; a refused letter keeps the relay's error on the row while
the sweep moves on to the next account. A daily retry clock (09:05 UTC) picks the
refused letters up again, oldest week first, until a letter has been tried five times;
a letter at the cap stays on its row and is not mailed. Composing from the dashboard
(`POST /digests/run`) files the letter without mailing it, and its zero attempts keep
it out of the retry queue — the scheduler is the only sender. On `console` each
week's letter is a log line instead of mail, which is the right default for a
development machine. A letter is written in the account's own language
(`users.locale`, switched from the app's language control): the sweep has no
browser, so the cookie cannot speak for the reader, and a letter freezes its
language with its payload — a retry re-sends the stored week as it was written
rather than re-composing it in whatever the account speaks today. Nothing has to
be configured for this; both languages ship in the image. The Monday clock has its own
heartbeat (22.4): `careeros.digest.last.sweep.timestamp` moves after every completed
compose, with or without letters, and `CareerOSDigestSweepStale` pages at eight days — so
a wrong `careeros.digest.cron` cannot pass for a quiet week
(`docs/RUNBOOK.md#the-monday-letter-was-never-written`).

Every letter carries a way out (23.1). Each one ends with a settings link and
goes out with the `List-Unsubscribe` / `List-Unsubscribe-Post` headers, so a
mailbox can offer one-click stop without a password. The link is its own
credential: `/api/v1/mail/preferences/{userId}/{token}` where the token is an
HMAC-SHA256 of the account id under `APP_MAIL_LINK_SECRET`, compared in constant
time; nothing is stored per link, and rotating the secret retires every link
already mailed (readers can still unsubscribe from the next letter). Page opens
change nothing — mail scanners prefetch links — and each dial (`weekly` for the
Monday letter, `signals` for the morning inbox mail, `reminders` for the letter
mailed the moment a reminder comes due) is flipped by a POST. A signed-in reader does
not need a letter to reach these dials (42.1): `GET /api/v1/me/mail/settings` answers
the three states plus the page's signed address, and Settings → Mail shows the states
and opens the page. Since 42.2 the card's switches write the same three states
(`PUT /api/v1/me/mail/settings/{list}` with `{enabled}`), so a press and the sweep that
reads it meet on one column. The choice lives in `mail_preferences`; no row means all three are on. The Monday sweep
skips an account that turned the letter off without counting a delivery attempt,
and the morning sweep never asks such an account what is waiting. Composing from
the dashboard still files the week's letter — the preference silences the mail,
not the archive. The app refuses to start when the secret is blank: an HMAC with
no key would make every account's link forgeable.

Rotating `APP_MAIL_LINK_SECRET` also retires every calendar feed (34.1). The
feed is `/api/v1/calendar.ics` with the address's `token` query parameter, and
its token is the same HMAC of the
account id under the same secret, signed with a separate prefix so the two
surfaces cannot be exchanged. A reader whose calendar app stops updating after a
rotation pastes a fresh address from Settings → Calendar; nothing else carries
over, because nothing about a link is stored. If a feed URL leaked, rotate the
secret: that is the only revocation this surface has, short of deleting the
account, and it costs every mailed unsubscribe link too — so rotate for a real
disclosure, not for a hunch.

The inbound address (37.1) points the other way: it is how a recruiter's reply
reaches the reader. Set `APP_INBOUND_DOMAIN` to a host whose mail the deployment
can route (the bare hostname, e.g. `inbox.careeros.example`), give the provider
an inbound route for that host, and have it POST the delivery to
`/api/v1/inbound/mail/{token}` with the recipient's local part in the path and
the provider's inbound JSON as the body. A provider that only offers one fixed
webhook URL needs an email worker or route in front that expands the recipient's
local part into the path and passes the body through: the token is in the path
precisely so the app never trusts an unsigned `To` header. The address shares
`APP_MAIL_LINK_SECRET`, so rotating that secret retires every address along with
the unsubscribe and calendar links; a reader pastes a fresh one from the replies
settings. Leaving `APP_INBOUND_DOMAIN` blank is valid — the deployment has no
inbox, and the settings card says so (**503** `INBOUND_NOT_CONFIGURED`) instead
of handing out an address nothing delivers to.

The inbox's signals ride the same transport (22.1). Every morning at 07:30 UTC a
sweep asks each account what is waiting — unread in the app and never mailed — and
sends one plain-text letter naming up to ten items, counting the rest, with links
back to the app. The latch is `notification_states.notified_at`, written only after
the transport accepts: a refused morning is a warn line and tomorrow's sweep tries
again, while an accepted letter is never repeated, and an item read or dismissed in
the app is not mailed at all. `careeros.signals.cron` moves the clock, and on
`console` each morning's letter is a log line. The letter's links are absolute and
built from `APP_WEB_BASE_URL`; a prod boot refuses the knob's shipped loopback
default and the example's `your-domain.com`, because otherwise every link in a
real mailbox points at localhost or at a domain the operator does not own.

The sweep is metered (22.2): `careeros.signals.delivery{outcome="sent"|"refused"}`
counts account letters that actually reached the transport, and
`careeros.signals.last.delivered.timestamp` is the moment the last letter was accepted
(started at boot, moved only by an acceptance — a quiet inbox is not a fault and is not
alarmed). The shipped rules raise `CareerOSSignalMailFailing` at three refusals inside
six hours, so one undeliverable address — which refuses once a morning while its
episode stays visible — is a log line rather than a daily page, while a relay outage
refusing a whole morning is a page; since 41.1 the same counter carries the minute clock's
reminder letters, so a day with three due reminders can lift one dead address over the
floor. `docs/RUNBOOK.md#the-morning-mail-is-refused` is
what the responder reads. `careeros.signals.last.sweep.timestamp` is the sweep's own
heartbeat (22.3), moved at the end of every completed pass even when no account has a
letter, and `CareerOSSignalSweepStale` pages at 36 hours without one — that is how a
misconfigured `careeros.signals.cron` or a scheduler that never started is caught
(`docs/RUNBOOK.md#the-morning-sweep-stopped`).

The same pass rings browsers when push is configured (33.3). Every outbound wake moves
`careeros.push.delivery{outcome="sent"|"gone"|"refused"|"not_configured"}`, one
registration per attempt; the episode's `notification_states.pushed_at` is written only
when some browser accepted, and a `gone` registration is deleted on the spot.
Three `refused` wakes in a day page — `CareerOSPushDeliveryFailing`, whose page is
`docs/RUNBOOK.md#the-wake-a-push-service-refused`. The other outcomes stay
unpaged on purpose: a refusal that clears costs one silent morning and the next pass asks the
same browser again, an install without VAPID keys reports `not_configured` every morning by
design, and `sent` sitting at zero while registrations exist is a dashboard question rather
than a paging one — the mail sweep's own clock already pages when the pass itself stops.

A reminder that comes due is rung when it comes due (35.1), and its letter is written then
(41.1). `careeros.reminders.tick-ms`
(default `60000`) is a fixed-delay clock: every tick asks the board which accounts' reminders
fell inside the window since the last completed tick, rings their browsers through the same
latch the morning uses, and mails the reminder's own letter to the accounts whose `reminders`
dial is on. The letter and the ring latch the same episode (`notified_at` / `pushed_at`), so
whichever door carried it, the morning letter does not repeat it, and a browser that
refused is not remembered as rung. The two halves are caught separately — a relay that refuses
letters does not silence a browser, and a push transport that hangs does not cost the tick its
letter — but a tick that failed in either half does not advance its window: the next tick asks
for the same span again. The heartbeat is `careeros.reminders.last.tick.timestamp`, moved
at the end of every completed tick with or without a reminder to ring;
`CareerOSReminderClockStale` pages when it has not moved for 300 seconds (five missed
ticks) and
`docs/RUNBOOK.md#the-minute-clock-a-reminder-rings-on` is what the responder reads. The
calendar feed does not depend on this clock: each event carries its own alarm (35.2), so a
subscriber's phone rings even with push turned off.

## Health & first data

- Backend liveness: `GET /api/v1/health` (no auth).
- Create the first user through `POST /api/v1/auth/register`, then log in and
  upload a resume from the `/resumes` screen; ingestion is queued and streamed
  over SSE.

## Running the stack without Docker (host) — the escape hatch

The canonical bring-up is `docker compose --profile app build` on the committed images. This
section exists for the case where that path is blocked *for this machine* — network to docker.io
or PyPI unreachable, or the daemon wedge — and someone must still reproduce verification. The
[timeline e2e run](../e2e/tests/timeline.spec.ts) was verified this way.

What the running containers may not be is patched in place — rebuild an image or run the service
directly from source; do not edit a running container to paper over drift.

Procedure used here (verified 2026-11-09):

1. **Postgres / Redis / MinIO live in the dev compose services** (`careeros-postgres`,
   `careeros-redis` at `127.0.0.1:5432` / `127.0.0.1:16380`, MinIO at `19000/19001`; the
   dev database is `career_os`, the same one `*IT` classes use with `IMAGE_IT` rules — never
   touched in production shape).
2. **ai-service** runs from the checkout with the existing venv:
   `env DATABASE_URL=postgresql://<user>:<pass>@127.0.0.1:5432/career_os \
     BACKEND_BASE_URL=http://127.0.0.1:8081 LLM_PROVIDER=mock EMBEDDING_PROVIDER=hash \
     APP_ENV=dev APP_BUILD_SHA=$(git rev-parse HEAD) \
     .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001`.
3. **backend** runs as the packaged jar:
   `SERVER_PORT=8081 AI_SERVICE_BASE_URL=http://127.0.0.1:8001 REDIS_URL=redis://127.0.0.1:16380/0 \
    MINIO_ENDPOINT=http://127.0.0.1:19000 APP_BUILD_SHA=$(git rev-parse HEAD) \
    RATELIMIT_AUTH_PER_MINUTE=100 \
    java -jar backend/target/career-os-backend-*.jar`,
   keeping the committed `.env` values. `APP_BUILD_SHA` is the commit hash — the `/health` answer names it.
4. **frontend standalone** built with
   `NEXT_STANDALONE=1 NEXT_PUBLIC_API_BASE_URL=http://localhost:8081/api/v1 npm run build`,
   then `node .next/standalone/server.js` with `PORT=3001`.
5. **e2e** runs against the host services via `E2E_BASE_URL=http://localhost:3001
   E2E_API_URL=http://127.0.0.1:8081/api/v1 E2E_AI_URL=http://127.0.0.1:8001
   npx playwright test tests/timeline.spec.ts` — this exact procedure proved the fold
   end-to-end (1 passed).

Known limits of this escape hatch, stated honestly:

- `*IT` classes still require the Docker dev infra; they do NOT use this procedure.
- The host-run frontend and backend do NOT share the compose file's env wiring; drift between
  the two configs is a risk the escape hatch does not cover.
- A wedged daemon or a corrupted compose file is a defect to file (and this repository had
  one — the literal-`\n` build args that broke every `docker compose` invocation until
  `feat(build): make the stack buildable again` landed), not a permanent state to route around.

## Tests

See the [README](../README.md) Tests section: frontend `vitest`, ai-service
`pytest` (offline mock/hash), backend `mvn test` — unit tests run offline, and
the `*IT` classes need the local `postgres` and `redis` containers up (they use
the dev infra directly rather than Testcontainers; see the README for why).
