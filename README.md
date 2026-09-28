# AI Career OS

A personal job-search operating system: your resume, the job market, and a fleet
of AI agents working together — from **resume → knowledge base → job discovery →
JD intelligence → evidence-backed matching → tailored materials → mock interviews
→ application pipeline**.

Not "a recruiting site with an AI button". Every AI conclusion is traceable to
your own material; every agent step is recorded and inspectable.

## What you get

| Module | What it does |
|---|---|
| Career Command Center | pipeline health, resume score, skill gaps, recommended jobs, recent AI activity |
| Resume Intelligence | upload PDF/DOCX/TXT → parse → structured profile + versioned resumes with live score |
| Career Knowledge Base | everything you are (experience, projects, notes, JDs, interview feedback) chunked, embedded, hybrid-searchable |
| RAG Copilot | query rewriting → vector + keyword + trigram retrieval → RRF fusion → rerank → compression → cited answers |
| JD Analysis & Matching | requirements/skills/interview topics extracted; deterministic match scores (tech/exp/proj/edu) bound to resume evidence |
| Tailoring & Cover Letters | job-targeted resume versions with a hard **no-fabrication verifier** and accept/reject diff |
| Adaptive Mock Interviews | interviewer agent that drills, follows up and scales difficulty (mechanism → alternative → failure → scale); 8-dimension report + depth trajectory |
| Career Orchestrator | tool-calling agent over 15 domain tools with subagent handoff (resume / job research / JD analyst / RAG / interview / learning / tracker) |
| Application Tracker | Linear-style kanban with transition audit events |
| Observability | every agent run: traces, tool calls, retrieval, tokens, cost — plus a built-in AI Activity view |
| RAG evaluation | golden-set harness: recall@k, precision@k, MRR, nDCG, faithfulness; A/B experiment reports |

## Architecture (summary)

```
Next.js 15 (design-system UI, SSE)  ──►  Spring Boot 3 (auth, domain ownership, REST /api/v1)
                                              │ X-Internal-Token
                                              ▼
                                     FastAPI ai-service (providers, ingestion,
                                     RAG, features, agent orchestrator)
                                              │
             PostgreSQL 16 + pgvector  ◄──────┴──────►  Redis · MinIO (private S3)
```

Full design: [docs/architecture.md](docs/architecture.md) · product plan:
[docs/product-plan.md](docs/product-plan.md) · ops: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) ·
security model: [docs/SECURITY.md](docs/SECURITY.md) · RAG design: [docs/RAG.md](docs/RAG.md)

## Quickstart (dev)

```bash
cp .env.example .env                # then set LLM_API_KEY / EMBEDDING_API_KEY (see docs/DEPLOYMENT.md)
docker compose up -d postgres redis minio
docker compose run --rm seed-jobs    # 12 companies / 41 roles, so search and matching have data

# ai-service (Python 3.11+)
cd ai-service && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt -r requirements-dev.txt
LLM_PROVIDER=mock EMBEDDING_PROVIDER=hash .venv/Scripts/python -m uvicorn app.main:app --port 8000   # offline dev

# backfill job vectors so vector search works, then type the column + build the index
python -m app.ops.embed_jobs
psql "$DATABASE_URL" -v dim=1536 -f ops/vector_index.sql

# backend (Java 21+, Maven)
cd backend && mvn spring-boot:run

# frontend (Node 20+)
cd frontend && npm install && npm run dev           # http://localhost:3000
```

`LLM_PROVIDER=mock` / `EMBEDDING_PROVIDER=hash` are **dev/test conveniences only**
(the mock provider is refused when `APP_ENV=prod`). For the real product,
configure any OpenAI-compatible / Anthropic / Ollama endpoint in `.env`.

The backend's `*IT` classes do not use Testcontainers: docker-java's npipe
strategy returns HTTP 400 from the Docker Desktop pipe on Windows, so they
bootstrap against the local containers instead — the `careeros-postgres`
container on `5432` (database `career_os_it`, dropped and re-migrated per run)
and a `careeros-it-redis` container on `16399` that the suite starts itself. So
`docker compose up -d postgres redis` is enough to run `mvn test`; the dev
database is never touched.

## Tests

```bash
cd frontend    && npm test                     # vitest: normalizers, formatters, SSE, nav, pipeline taxonomy
cd ai-service  && .venv/Scripts/python -m pytest # unit + orchestrator + contract gates (offline: mock/hash)
cd backend     && mvn test                     # unit tests offline; *IT also need the infra below
# RAG eval (needs the DB/infra running): cd ai-service && python -m app.eval.run_eval --user-id <uuid> [--answer]
cd e2e && npm install && npx playwright test   # PRD §35 golden journey; needs all three services up (see e2e/README.md)
```

## Repo map

```
backend/       Spring Boot — the only public API, owns all domain writes
ai-service/    FastAPI — providers, ingestion, RAG, features, agents (internal only)
frontend/      Next.js — app UI + AI activity views
docs/          architecture, product plan, RAG, security, deployment
docker-compose.yml   infra + `--profile app` full-stack containers
```

## License / status

Personal project, active development. See docs for the honest list of what is
verified end-to-end vs. pending hardening.
