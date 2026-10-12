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
containing all secrets. The production compose uses the `app` profile and adds
resource limits, health checks, and proper restart policies.

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
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile app up -d

# 3. Verify health
curl -f http://localhost:8080/api/v1/health
curl -f http://localhost:8000/health
curl -f http://localhost:3000
```

### Production Checklist

- [ ] All secrets in `.env.prod` are strong, unique, and not from `.env.example`
- [ ] `JWT_SECRET` is >= 64 random characters
- [ ] `APP_ENV=prod` (blocks mock LLM provider)
- [ ] Real LLM/embedding provider keys configured (not `mock`/`hash`)
- [ ] Reverse proxy (nginx/Traefik/Caddy) terminates TLS and forwards to:
  - Frontend: `http://frontend:3000`
  - Backend API: `http://backend:8080`
  - AI service: **not exposed** (internal only)
- [ ] Reverse proxy sets `X-Forwarded-For` and `X-Forwarded-Proto` headers
- [ ] `/actuator/prometheus` restricted at the proxy to the scraper's address (public by default)
- [ ] DNS records point to the reverse proxy
- [ ] TLS certificates configured and auto-renewing (Let's Encrypt recommended)
- [ ] Database backups configured (pg_dump on schedule)
- [ ] MinIO bucket versioning enabled for object recovery
- [ ] Log aggregation configured (Loki/ELK/Datadog)
- [ ] Metrics/monitoring configured (Prometheus/Grafana)

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
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api/v1/ {
        proxy_pass http://backend:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
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

```bash
# Backup Postgres
docker exec careeros-postgres-prod pg_dump -U career_os career_os > backup_$(date +%F).sql

# Restore
docker exec -i careeros-postgres-prod psql -U career_os career_os < backup_2026-01-15.sql

# Backup MinIO (using mc mirror)
mc mirror local/careeros-files remote/careeros-backup/
```

### Rolling Updates

```bash
# Build new images
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# Rolling restart (one service at a time)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps backend
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps ai-service
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps frontend
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
variable list.

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

Two offline-only escape hatches for tests and first-run dev: `mock` LLM and
`hash` embeddings. The app **refuses to boot with `LLM_PROVIDER=mock` when
`APP_ENV=prod`** (see `app/main.py`), and `hash` embeddings give limited
retrieval quality — use a real embedding provider for anything beyond a smoke
test.

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
