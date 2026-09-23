# AI Career OS — Product Plan & Implementation Roadmap

Derived from the master prompt (AI Career OS). Ordered by dependency: infra → backend
core → ai core → features → frontend → quality → delivery.

## Epic 0 — Foundation
- T0.1 docker-compose (pgvector postgres, redis, minio) + healthchecks + volumes
- T0.2 repo skeleton, .env.example, Makefile/scripts, git init, README stub
- T0.3 Spring Boot scaffold (security, envelope, error handling, flyway baseline)
- T0.4 FastAPI scaffold (settings, providers, internal auth, structured logging)
- T0.5 Next.js scaffold (Tailwind tokens, theme, font, layout shell, api client)

## Epic 1 — Auth & User
- F1.1 Register/Login/Logout (JWT + refresh rotation), password reset flow, OAuth-ready
- F1.2 Profile CRUD (headline, targets, links), preferences
- F1.3 User data isolation tests (IDOR suite)

## Epic 2 — Resume Intelligence
- F2.1 Upload (PDF/DOCX/TXT) → MinIO → document record
- F2.2 Ingestion pipeline (clean/chunk/embed/store) with progress events
- F2.3 LLM structured resume parse → ResumeProfile JSON + normalized rows
  (skills/experience/projects/education/achievements/goals)
- F2.4 Career profile creation + editing UI; Resume Score (rule-based rubric)
- F2.5 Multi-version model (original + tailored)

## Epic 3 — Career Knowledge Base / RAG
- F3.1 Knowledge sources registry (resume, project, note, jd, company, interview
  feedback, certificates, courses, goals) + ingestion for each
- F3.2 Hybrid retrieval (vector + FTS + metadata filter) + RRF + rerank + compression
- F3.3 Query understanding/rewriting/intent; citation objects end-to-end
- F3.4 Evidence traceability API (chunk → document → section path → quote)

## Epic 4 — Job Discovery & Intelligence
- F4.1 Seed dataset: ~40 realistic jobs + companies (AI/backend/agent roles), FTS+vector
- F4.2 Search API (filters: location/company/type/skills/salary/exp/remote) + match sort
- F4.3 Job cards with AI match %, matched/missing skills (PRD §7 card design)
- F4.4 Job detail page (match breakdown, strengths, gaps, evidence, topics, actions)
- F4.5 JD Intelligence: paste JD → parse → required/preferred/hidden/priorities/topics
- F4.6 Matching engine: computable scores + evidence binding + caching per resume version
- F4.7 Save job / company intelligence page with sources

## Epic 5 — Materials Generation
- F5.1 Resume tailoring (KB retrieval → reorder/reword → no-fabrication verifier →
  before/after diff → new ResumeVersion)
- F5.2 Cover letter generation + regenerate/shorten/formal/concise/customize

## Epic 6 — Interview Coach
- F6.1 Session setup (company/position/JD/resume/mode)
- F6.2 Dynamic interviewer agent: question → answer → eval → follow-up chain →
  adaptive difficulty → depth trajectory
- F6.3 Per-answer feedback + final evaluation (8 dimensions, better answers,
  study materials) + replay UI

## Epic 7 — Copilot & Agents
- F7.1 Tool system (15 tools with schemas) + tool-calling loop
- F7.2 Career Orchestrator + subagents + handoff with trace events
- F7.3 Memory: short-term (conversation) + long-term (user_memories read/write)
- F7.4 Chat UI with sources / artifacts / action buttons; streaming
- F7.5 AI Activity / Debug view (agent run → tools → retrieval → llm → answer)

## Epic 8 — Application Tracker & Dashboard
- F8.1 Kanban (saved→applied→oa→interview→final→offer→rejected) drag&drop, notes,
  reminders, linked resume version/jd/match
- F8.2 Dashboard: greeting, attention counts, progress, pipeline, recommended jobs,
  skill gaps, recent AI insights, resume score, AI usage/cost
- F8.3 ⌘K global search across jobs/companies/resumes/interviews/notes/KB/conversations

## Epic 9 — Quality & Delivery
- F9.1 Unit + integration tests all services; API tests with envelope/auth assertions
- F9.2 RAG evaluation framework + dataset + first experiment report
- F9.3 Agent evaluation (tool-selection accuracy, task completion on scripted scenarios)
- F9.4 Playwright E2E: full flow PRD §35 (mock provider for CI; real provider manual)
- F9.5 ✅ Security review pass vs PRD §30 checklist — [findings in SECURITY.md](SECURITY.md#prd-30-review)
- F9.6 Nine delivery docs + production docker build + final demo verification

## Definition of Ready for each task
implementation + tests + wired into real UI/API (no placeholder endpoints) +
lint/build green.

## Execution order (waves)
1. E0 → 2. E1 → 3. E2(ingest core)+E3.1 → 4. E4 → 5. E3.2-4+E5 → 6. E6 → 7. E7 →
8. E8 → 9. E9 (continuous: tests run at every wave close).
