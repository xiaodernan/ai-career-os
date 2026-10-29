# Deployment

How to bring AI Career OS up locally and what each knob controls. The stack is
three application services (backend, ai-service, frontend) plus three stateful
dependencies (PostgreSQL + pgvector, Redis, MinIO).

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

`docker-compose.prod.yml` republishes the three app services, and an entry written as
`HOST:CONTAINER` with no interface prefix is bound on every interface of the host. The
override therefore opens two ports the development file keeps to the machine:

| Service    | Host port | Reach           | Notes                                          |
|------------|-----------|-----------------|------------------------------------------------|
| ai-service | 8000      | `127.0.0.1`     | Internal-only by design; the override keeps it |
| backend    | 8080      | every interface | Reachable from the network, not just the host  |
| frontend   | 3000      | every interface | Reachable from the network, not just the host  |

So in the stack the Quick Start brings up (`docker-compose.yml` together with
`docker-compose.prod.yml`), `backend` on 8080 and `frontend` on 3000 answer to the
network as well as through the reverse proxy — the proxy is not the only path in.
Ports the override does not mention, `postgres` 5432, `redis` 16380 and `minio`
19000/19001, keep the development file's binding. If the host should not answer on
8080 and 3000 directly, bind them to `127.0.0.1` in your own override or firewall the
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

### Monitoring Endpoints

| Service    | Health Check                    | Metrics                    |
|------------|---------------------------------|----------------------------|
| Backend    | `GET /api/v1/health`            | Prometheus at `/actuator/prometheus` (Micrometer); orchestrator probe at `/actuator/health`. The custom `/api/v1/health` additionally reports the Redis state (`redis: true/false`) as degraded-but-up. |
| AI Service | `GET /health`                   | None. The service is internal-only and logs to stdout; there is no `/metrics` route. |
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
`ops/prometheus/alerts.yml` carries the ten rules and each one links its page in
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
`RETENTION_EXPIRED_TOKEN_DAYS` (30 by default) in the past. A table whose delete
fails is logged and leaves no reading, so a quiet night and a broken sweep are
different shapes on the dashboard. The sweep deliberately leaves the tables whose
rows are visible history — AI usage events behind the activity totals,
notification read state, ingestion runs, weekly letters — because deleting those
rows would rewrite a screen or re-announce a story the reader already settled.
V23 adds an `expires_at` index to each of the three swept tables, so the nightly
delete stays a range read as the tables grow.

The sweep also exports `careeros_retention_last_sweep_timestamp`, moved at the
end of every completed pass, with or without deletions. The counter cannot say
whether the clock still runs — a stopped sweep leaves its last value on the
scrape — so `CareerOSRetentionSweepStale` fires (warning) when the heartbeat is
more than 36 hours old, twice the daily cadence. A pass whose tables failed
still moves it; the failures are visible as "Retention sweep failed for" in the
log and as a missing per-table series.

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
three application services (backend, ai-service, frontend) plus three stateful
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

Full application stack on top of the infra — the three app services live behind
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
| ai-service | 8000      | `127.0.0.1` | Internal-only; not exposed to browsers           |
| postgres   | 5432      | `127.0.0.1` | pgvector `pg16` image                            |
| redis      | 16380     | `127.0.0.1` | host 16380 → container 6379 (avoids local clash) |
| minio      | 19000     | `127.0.0.1` | S3 API; console on 19001                         |
| minio      | 19001     | `127.0.0.1` | S3 web console                                   |

Inside the compose network the services reach each other by name
(`postgres`, `redis`, `minio`, `ai-service:8000`, `backend:8080`) — see the
`environment:` overrides in `docker-compose.yml`.

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

Every letter carries a way out (23.1). Both mails end with a settings link and
go out with the `List-Unsubscribe` / `List-Unsubscribe-Post` headers, so a
mailbox can offer one-click stop without a password. The link is its own
credential: `/api/v1/mail/preferences/{userId}/{token}` where the token is an
HMAC-SHA256 of the account id under `APP_MAIL_LINK_SECRET`, compared in constant
time; nothing is stored per link, and rotating the secret retires every link
already mailed (readers can still unsubscribe from the next letter). Page opens
change nothing — mail scanners prefetch links — and each dial (`weekly` for the
Monday letter, `signals` for the morning inbox mail) is flipped by a POST. The
choice lives in `mail_preferences`; no row means both are on. The Monday sweep
skips an account that turned the letter off without counting a delivery attempt,
and the morning sweep never asks such an account what is waiting. Composing from
the dashboard still files the week's letter — the preference silences the mail,
not the archive. The app refuses to start when the secret is blank: an HMAC with
no key would make every account's link forgeable.

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
refusing a whole morning is a page; `docs/RUNBOOK.md#the-morning-mail-is-refused` is
what the responder reads. `careeros.signals.last.sweep.timestamp` is the sweep's own
heartbeat (22.3), moved at the end of every completed pass even when no account has a
letter, and `CareerOSSignalSweepStale` pages at 36 hours without one — that is how a
misconfigured `careeros.signals.cron` or a scheduler that never started is caught
(`docs/RUNBOOK.md#the-morning-sweep-stopped`).

The same pass rings browsers when push is configured (33.3). Every outbound wake moves
`careeros.push.delivery{outcome="sent"|"gone"|"refused"|"not_configured"}`, one
registration per attempt; the episode's `notification_states.pushed_at` is written only
when some browser accepted, and a `gone` registration is deleted on the spot. No page is
attached to this counter: an install without VAPID keys reports `not_configured` every
morning by design, a refused wake is retried tomorrow, and `sent` sitting at zero while
registrations exist is a dashboard question rather than a paging one — the mail sweep's
own clock already pages when the pass itself stops.

## Health & first data

- Backend liveness: `GET /api/v1/health` (no auth).
- Create the first user through `POST /api/v1/auth/register`, then log in and
  upload a resume from the `/resumes` screen; ingestion is queued and streamed
  over SSE.

## Tests

See the [README](../README.md) Tests section: frontend `vitest`, ai-service
`pytest` (offline mock/hash), backend `mvn test` — unit tests run offline, and
the `*IT` classes need the local `postgres` and `redis` containers up (they use
the dev infra directly rather than Testcontainers; see the README for why).
