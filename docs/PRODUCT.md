# PRODUCT.md — AI Career OS

## What this is

A personal job-search operating system built around an AI agent and retrieval over
your own career material — not a job board with AI buttons bolted on.

The distinction is the whole point. In a job board, "AI" means a generate button:
you get text out, and you have no idea where it came from. Here, the user's resume,
projects, notes and pasted job descriptions become a **searchable evidence layer**,
and every AI output is computed against that layer and **cited back to it**. A match
score is never a bare number; it arrives with the quotes it was derived from.

> A match score you can't audit is a guess with a decimal point.

## Who it's for

Someone running a real search, not browsing. Typically a mid-to-senior engineer or
product person applying to many roles at once, who has to repeatedly answer the same
questions: *Is this role actually a fit? What am I missing? How do I re-frame my
experience for it? What will they ask me? Where does this application stand?*

Doing that well by hand across 30 applications is a full-time job. That is the job
this product takes over.

## The loop it runs

The product is organised around one continuous loop rather than a set of pages:

```
Resume / projects / notes
        ↓  ingested into a knowledge base (chunks + embeddings)
Career profile  ←──────────────────────────────┐
        ↓                                       │
Discover roles (search + agent research)        │
        ↓                                       │
Understand the JD (required / preferred /       │
  hidden requirements, interview topics)        │
        ↓                                       │
Match against evidence → score + citations      │
        ↓                                       │
Produce materials (tailored resume,             │
  cover letter — reordered, never invented)     │
        ↓                                       │
Prepare & rehearse (adaptive mock interview     │
  that scores dimensions and follows up)        │
        ↓                                       │
Track the pipeline (stages, timeline, kanban) ──┘
```

The loop closes: interview feedback and skill gaps feed back into what to learn and
what to target next.

## Feature inventory

Each row is a shipped capability, the route that exposes it, and the API behind it.

| Capability | Route | API |
| --- | --- | --- |
| Accounts, sessions, token rotation | `/login`, `/register` | `/auth/*` |
| Resume upload, parse, versions, quality score | `/resumes`, `/resumes/[id]` | `/resumes/*`, `/resume-versions` |
| Knowledge base (resume / projects / notes / JD / company) | `/knowledge` | `/knowledge/*` |
| Job search with facets (skills, location, salary, remote) | `/jobs` | `/jobs` |
| Job detail, save/bookmark, match, tailor, cover letter | `/jobs/[id]` | `/jobs/{id}/*` |
| JD analysis + resume improvement suggestions | `/jobs` (dialog) | `/jds`, `/jds/suggestions` |
| Company research | `/companies` | `/companies` |
| Adaptive mock interviews + report | `/interviews`, `/interviews/[id]/report` | `/interview/sessions/*` |
| Application tracking (stages, timeline, kanban) | `/applications`, `/dashboard` | `/applications`, `/reports/dashboard` |
| Copilot chat (agent, artifacts, suggested actions) | `/copilot` | `/copilot/chat` |
| AI activity: every run, its steps and its cost | `/activity`, `/activity/[id]` | `/activity/runs`, `/ai-usage/summary` |
| Cross-entity search | (global) | `/search` |
| Profile and preferences | `/settings` | `/users/me` |

## How the AI is actually wired

**Retrieval (RAG).** Query → rewrite → intent → hybrid retrieve (vector ∪ full-text ∪
trigram) → RRF fusion → rerank → compress → answer with citations. Hybrid retrieval
matters because pure vector search is bad at exact tokens (a skill named "Go", a
company name) and pure keyword search is bad at paraphrase. Fusing both is what makes
"find my Kubernetes work" and "find the payments rewrite" both work.

**Agent.** A hand-written tool-calling loop, capped at 8 steps, with a Career
orchestrator that delegates to seven scoped subagents — `resume`, `job_research`,
`jd_analyst`, `rag`, `interview`, `learning`, `tracker`. Each subagent gets an
explicit tool **whitelist**, so the interview agent physically cannot save a job.
Delegation is a visible `transfer_to` handoff, not a hidden routing decision.

**Evidence binding.** Tailoring reorders and re-words; a verifier rejects claims the
resume does not support. "Never fabricate experience — every claim maps to evidence"
is enforced, not aspirational.

**Observability.** Every AI turn writes an `agent_run` plus ordered `agent_traces`
(`step_start` → `llm_call` → `tool_call` → `tool_result` → handoff → answer) with
tokens, latency and cost. `/activity` renders that. This is deliberately
user-facing: when the agent gives a bad answer you can see which tool returned
what, instead of guessing.

## What we deliberately did not do

- **No fabricated evidence.** The model is not allowed to invent a metric, employer
  or skill. Every generated claim traces to a stored chunk.
- **No hidden routing.** Handoffs are explicit and traced.
- **No mock UI in the product.** The offline providers (`LLM_PROVIDER=mock`,
  `EMBEDDING_PROVIDER=hash`) exist for deterministic tests and are **refused when
  `APP_ENV=prod`**.
- **No silent wrong numbers.** Where a score can be computed without an LLM
  (skill coverage, years, education), it is computed deterministically; the model
  narrates, it does not decide the arithmetic.

## Honest status

Working end to end: the three services, the full loop above, agent tracing, both
evaluation harnesses, and a seeded 12-company / 41-role corpus.

Verified against the live stack, not just in unit tests:

- The **Playwright golden-journey suite passes 9/9** (`e2e/`) against
  postgres+redis+minio, ai-service, backend and a production frontend build. It
  runs the PRD §35 flow for real: register → upload a resume → search → match →
  tailor → track → interview → report → copilot.
- **Job vectors are backfilled and indexed.** `python -m app.ops.embed_jobs`
  embedded all 46 roles, `jobs.embedding` is `vector(1536)` and `idx_jobs_hnsw`
  is built, so `search_jobs` now runs keyword and vector retrieval and fuses them
  by reciprocal rank. Keyword-only behaviour is preserved whenever embeddings are
  unavailable, which is what a provider outage or an un-backfilled database looks
  like.

Remaining gaps, stated plainly rather than hidden:

- Semantic search quality is only as good as the embedding provider. The offline
  default (`EMBEDDING_PROVIDER=hash`) exercises the whole path deterministically
  but carries no meaning, so retrieval quality must be judged against a real
  provider.
- The backend's own `/jobs` search is still keyword/facet-based; only the agent's
  `search_jobs` tool is hybrid today.

A pass over the PRD §30 checklist is recorded in `docs/SECURITY.md`. It closed one
real gap — the AI rate limit did not cover any of the blocking AI endpoints,
including `/copilot/chat`, the most expensive call in the product — and documents
two residual risks rather than papering over them: `X-Forwarded-For` is trusted
for IP throttling (so the backend must sit behind a proxy that *sets* it, or
login throttling can be spoofed away), and the limiter fails open when Redis is
down.

See `docs/product-plan.md` for the epic/task breakdown and
`docs/architecture.md` for the system design.
