# Deployment

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

Infra only (Postgres, Redis, MinIO + one-shot bucket init):

```bash
docker compose up -d postgres redis minio minio-init
```

Full application stack on top of the infra — the three app services live behind
the `app` profile:

```bash
docker compose --profile app up -d
```

Service endpoints (all bound to `127.0.0.1` only):

| Service    | Host port | Notes                                             |
|------------|-----------|---------------------------------------------------|
| frontend   | 3000      | Next.js; `NEXT_PUBLIC_API_BASE_URL` → backend     |
| backend    | 8080      | Public REST API under `/api/v1`                   |
| ai-service | 8000      | Internal-only; not exposed to browsers            |
| postgres   | 5432      | pgvector `pg16` image                             |
| redis      | 16380     | host 16380 → container 6379 (avoids local clash)  |
| minio      | 19000     | S3 API; console on 19001                          |

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
`pytest` (offline mock/hash), backend `mvn test` (unit tests run offline;
`*IT` integration tests need Docker/Testcontainers).
