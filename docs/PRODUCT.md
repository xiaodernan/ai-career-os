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
| Accounts, sessions, token rotation, password reset | `/login`, `/register`, `/forgot-password`, `/reset-password` | `/auth/*` |
| Resume upload, parse, versions, quality score | `/resumes`, `/resumes/[id]` | `/resumes/*`, `/resume-versions` |
| Knowledge base (resume / projects / notes / JD / company) | `/knowledge` | `/knowledge/*` |
| Job search with facets (skills, location, salary, remote) + hybrid relevance | `/jobs` | `/jobs` |
| Job detail, save/bookmark, match, tailor, cover letter | `/jobs/[id]` | `/jobs/{id}/*` |
| JD analysis + resume improvement suggestions | `/jobs` (dialog) | `/jds`, `/jds/suggestions` |
| Company research | `/companies` | `/companies` |
| Adaptive mock interviews + report | `/interviews`, `/interviews/[id]/report` | `/interview/sessions/*` |
| Application tracking (stages, notes, reminders, timeline, kanban) | `/applications`, `/dashboard` | `/applications`, `/reports/dashboard` |
| Copilot chat (agent, artifacts, suggested actions) | `/copilot` | `/copilot/chat` |
| AI activity: every run, its steps and its cost | `/activity`, `/activity/[id]` | `/activity/runs`, `/ai-usage/summary` |
| Cross-entity search | (global) | `/search` |
| Profile and preferences | `/settings` | `/users/me` |
| Growth: readiness, gaps, learning plan, and each engine on its own | `/growth` | `/growth-report`, `/growth/*` |
| Salary & offers: market band, negotiation coaching, offer comparison, counter-offer | `/offers` | `/offers/*` |
| Analytics: the pipeline funnel, the response rates, the weekly digest | `/analysis` | `/analysis/*` |
| Job ingestion: parse a feed, de-duplicate it, sweep it, plan the write | `/ingestion` | `/jobs/ingest/*` |
| Data portability: export, preview a restore, redact before sharing | `/data` | `/data-portability/*` |
| Networking: the contact registry and the follow-up drafts | `/networking` | `/contacts`, `/outreach/draft` |
| Agent health and the rate-limit status | `/monitoring`, `/rate-limit` | `/monitoring/health-report`, `/rate-limit/status` |

## How the AI is actually wired

**Retrieval (RAG).** Query → rewrite → intent → hybrid retrieve (vector ∪ full-text ∪
trigram) → RRF fusion → rerank → compress → answer with citations. Hybrid retrieval
matters because pure vector search is bad at exact tokens (a skill named "Go", a
company name) and pure keyword search is bad at paraphrase. Fusing both is what makes
"find my Kubernetes work" and "find the payments rewrite" both work.

**Agent.** A hand-written tool-calling loop, capped at 8 steps, with a Career
orchestrator that delegates to eight scoped subagents — `resume`, `job_research`,
`jd_analyst`, `rag`, `interview`, `learning`, `tracker`, `networking`. Each subagent
gets an explicit tool **whitelist**, so the interview agent physically cannot save a
job. Delegation is a visible `transfer_to` handoff, not a hidden routing decision.

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

- The **Playwright golden-journey suite passes 65/65** (`e2e/`) against
  postgres+redis+minio, ai-service, backend and a production frontend build. It
  runs the PRD §35 flow for real: register → upload a resume → search → match →
  tailor → track → interview → report → copilot, plus the account-recovery pair
  (`/forgot-password` → `/reset-password`), which needs no fixture: it drives the
  screens, the local refusals, the pasted-token path and the API's own advice
  about a token it does not know, plus the language switch — the sidebar's own
  button, driven for real, and the screen checked in the reader's language
  before and after, and the same switch on the three surfaces an anonymous
  visitor can reach, plus the forward bridges' answers arriving on the screen:
  the stage names the funnel computed are the stage names the page draws, the
  verdict the health report computed is the verdict the page shows, the
  growth report is built by the screen the way a reader builds it -- a role
  typed into a form, and the report the engines answered with is the report
  on the page -- the market band and the negotiation plan come from the
  offers form, the portability round trip is driven through the screen:
  the bundle the screen exports has the hash the API's bundle has, and
  that bundle is planned and applied from the same page, and a feed is
  parsed by the ingestion screen in either shape -- RSS 2.0 / Atom XML or a
  board-API JSON payload, which is what the page has always promised -- and
  a message to a contact is drafted by the networking screen, for the
  contact the reader picked, the corpus's own read of a company --
  what its postings actually ask for -- comes from the company page, and
  the copilot's turn is *streamed*: the end-to-end suite reads the frames
  the browser received, because a turn that is answered and a turn that
  is streamed look identical on the screen. The three surfaces that take a
  *file* or an *answer* are driven the way a reader drives them: the
  knowledge base's own uploader, the resume dropzone and the interview
  runner. Driving the real file input found that the knowledge base's
  uploader had never uploaded anything -- a `FileList` is live, so
  clearing the input before reading it handed the batch an empty list,
  and an empty list is not an error, it is a batch of nothing. The browser
  tab's title is read in the reader's language too, on the public pages
  and on the 404, because the title is rendered into the head the browser
  paints before any script runs -- and a title that says "AI Career OS" on
  a Chinese page is the one thing on the page that never changed.
- **The keyboard path is driven, not asserted.** The suite tabs through the
  shell and checks three things a reader who cannot use a mouse depends on:
  the skip link is the *first* thing the keyboard reaches and it moves the
  focus to the content (a viewport jump without a focus move buys nothing),
  every element the keyboard reaches has a visible focus indicator, and
  every control in the shell has an accessible name. The suite also drives
  the language switch and the command palette with the keyboard alone, and
  reads the top bar's own heading to prove the page followed.
- **The run's trace is read on the screen.** The activity page is the debug
  view behind the answers (PRD §31, §47 Demo 6), and the suite drives a
  copilot turn, opens the list, and checks that the run the list carries is
  the run the API recorded and that its steps -- the same number, and the
  same kinds -- are the ones the page draws. It also closed a race in the
  streaming case: the question is on the screen the moment it is sent, so a
  transcript read straight after it was reading the page mid-answer, and
  that case failed about one run in four.
- **Job vectors are backfilled and indexed.** `python -m app.ops.embed_jobs`
  embedded all 41 roles, `jobs.embedding` is `vector(1536)` and `idx_jobs_hnsw`
  is built, so `search_jobs` now runs keyword and vector retrieval and fuses them
  by reciprocal rank. Keyword-only behaviour is preserved whenever embeddings are
  unavailable, which is what a provider outage or an un-backfilled database looks
  like. The service runs that same backfill as a background sweep, so a role
  created mid-session becomes vector-searchable within a minute without re-running
  the script.
- **The board's own search is hybrid as well.** `GET /api/v1/jobs?q=…` ranks by
  keyword/tsvector and pgvector cosine distance over one filtered row set, fused
  the same way (the query vector comes from `POST /internal/rag/embeddings`), so a
  paraphrase with no shared keyword is recallable. An explicit `sort=` still only
  orders, no vector is fetched, and an outage or a noise query degrades to
  keyword-only or zero rows. The ⌘K palette's channel (`GET /api/v1/search`) fuses the
  same way — `JobSearchHybridIT` and `GlobalSearchHybridIT` pin both against a real
  database, including the two degradations that matter (no vector at all, and a row whose
  embedding carries another provider's dimensionality).

Remaining gaps, stated plainly rather than hidden:

- Semantic search quality is only as good as the embedding provider. The offline
  default (`EMBEDDING_PROVIDER=hash`) exercises the whole path deterministically
  but carries no meaning, so retrieval quality must be judged against a real
  provider.
- A mocked database hides a whole class of bug, and the portable export was
  full of it: it read a column the schema does not have, and its canonical
  serializer refused the `uuid.UUID` the rows actually arrive as. Every unit
  test passed, because the export's fetch functions are monkeypatched and a
  fixture row is a plain dict. It took the e2e suite, against a real database,
  to find them. The gate that now holds the class is
  `ai-service/tests/test_the_ai_service_sql_names_real_columns.py`: it reads the
  schema of record -- the backend's migrations -- and checks that every column
  the ai-service's SQL names is one the schema declares.

A pass over the PRD §30 checklist is recorded in `docs/SECURITY.md`. It closed one
real gap — the AI rate limit did not cover any of the blocking AI endpoints,
including `/copilot/chat`, the most expensive call in the product — and it
documented a second one that has since been closed: `X-Forwarded-For` used to be
trusted for IP throttling unconditionally, so a directly exposed backend let a
client rotate the header and spoof login throttling away. The header is now read
only behind a declared proxy (`APP_HTTP_TRUST_FORWARDED_FOR`, off by default)
and only its last hop, the one the proxy wrote. The remaining operational note
is that a Redis outage degrades the service rather than killing it — the
fail-open path was always correct, but it was only reachable after a Redis
timeout, so the client timeout is now pinned to 500ms and a stopped Redis yields
`/health` `degraded` in 0.51s instead of no response at all.

See `docs/product-plan.md` for the epic/task breakdown and
`docs/architecture.md` for the system design.
