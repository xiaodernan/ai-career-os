# Agents

How AI Career OS turns "call an LLM" into an inspectable agent system (PRD §16,
§17, §18, §31). Implementation: `ai-service/app/agents/`. Home-grown loop, no
orchestration framework — every stage is explicit code that emits trace events.

## 1. The orchestrator loop

`orchestrator.career_turn()` handles one user turn:

```
system prompt (+ long-term memory + pinned context)
  └─ conversation window (last 12 turns)
       └─ loop, max 8 steps:
            LLM decides: answer directly │ call a tool │ transfer_to(subagent)
            tool result → appended as a `tool` message → next step
       └─ budget exhausted → forced summarise call over collected tool output
```

Key properties:

- **Grounded by construction.** A tool result is always replayed back to the model
  as a `tool` message, so the final answer is written over real output rather than
  recalled knowledge. The system prompt forbids inventing experience, skills,
  companies or results.
- **Bounded.** `MAX_STEPS = 8` (subagents `MAX_SUB_STEPS = 5`) and a per-result
  character cap (`RESULT_CHARS = 6000`) keep a looping or over-eager model from
  burning the budget; exhausting the budget still yields a grounded summary.
- **Fault-tolerant.** A tool that raises or receives bad arguments becomes
  `{"error": ...}` in the transcript — the run continues and the model is expected
  to recover. Bad arguments from the model never crash the turn.
- **Side-effect aware.** `Outcome` collects `artifacts` (structured payloads the UI
  renders) and derives `actions` (suggested next steps: tailor / interview / cover
  letter / open job), so a chat turn produces a usable product surface, not just
  text.

Returned `Outcome`: `answer`, `artifacts[]`, `sources[]`, `actions[]`, `steps`,
`tools_used[]`, `run_id`.

## 2. Subagents and handoff

Seven subagents, each with its own system prompt, its **own whitelisted tool
surface**, and no ability to delegate further (no recursive handoff):

| Subagent | Tools |
|---|---|
| `resume` | `parse_resume`, `search_resume`, `generate_resume`, `generate_cover_letter`, `search_knowledge_base`, `get_user_profile` |
| `job_research` | `search_jobs`, `get_job`, `get_company`, `search_knowledge_base`, `get_user_profile` |
| `jd_analyst` | `analyze_jd`, `calculate_match`, `get_job`, `search_resume` |
| `rag` | `search_knowledge_base`, `search_resume` |
| `interview` | `create_interview`, `evaluate_answer`, `get_job`, `search_resume` |
| `learning` | `search_knowledge_base`, `get_user_profile`, `get_job` |
| `tracker` | `save_job`, `update_application_status`, `search_jobs`, `get_job` |

Handoff is an explicit tool, `transfer_to(agent, task)`, not a prompt trick. It is
recorded as a `handoff` trace event and streamed as a `status` step, so the UI can
show *"Delegating to job_research agent"*. The subagent returns a compact factual
report (ids, numbers, evidence refs); **the orchestrator stays responsible for the
final user-facing answer**, which keeps one voice and one citation discipline.

```mermaid
flowchart TD
    U[user turn] --> CO[Career Orchestrator]
    CO -->|transfer_to| JR[job_research]
    CO -->|transfer_to| JD[jd_analyst]
    CO -->|transfer_to| RS[resume]
    CO -->|transfer_to| IV[interview]
    JR -->|report| CO
    JD -->|report| CO
    RS -->|report| CO
    IV -->|report| CO
    CO --> A[final answer + artifacts + sources + actions]
```

## 3. Memory (PRD §17)

- **Short-term** — the conversation window (last 12 turns, 4 000 chars each) passed
  in by the backend, plus `context` pins (a specific job/resume/conversation scope).
- **Long-term** — `user_memories` rows, grouped by kind (`profile`, `skill`,
  `preference`, `interview`, `goal`, `fact`). `memory.build_memory_context()` reads
  up to 40 and renders them as a `## Long-term memory about this user` section
  appended to the system prompt.
- **Write path** — after a successful turn, `memory.extract_and_store()` makes one
  cheap extraction call, keeps at most 4 durable facts with `len(content) >= 8` and
  a clamped importance score, and upserts them. It is best-effort: a failure logs a
  warning and never fails the user's turn. Credentials and secrets are explicitly
  out of scope.

## 4. Tool system (PRD §18)

15 tools in `agents/tools.py`, each a `Tool(name, description, JSON-Schema
parameters, async handler, artifact_type?, agent?)`. The schema is converted to the
provider's tool format via `Tool.spec()`, so one definition serves OpenAI-compatible
APIs, Anthropic and Ollama.

| Tool | Purpose | Artifact |
|---|---|---|
| `search_jobs` | keyword/skills/location/company/remote/salary search | `job_list` |
| `get_job` | job detail + cached match | |
| `get_company` | company intelligence + open roles | |
| `parse_resume` | raw text → structured profile + score | |
| `search_resume` | semantic search over resume/project chunks | |
| `search_knowledge_base` | hybrid RAG retrieval + context block | |
| `analyze_jd` | pasted JD → structured requirements | |
| `calculate_match` | deterministic, evidence-bound match score | `match` |
| `generate_resume` | no-fabrication tailoring + diff | `tailored_resume` |
| `generate_cover_letter` | personalized cover letter | `cover_letter` |
| `create_interview` | start a mock interview session | `interview_session` |
| `evaluate_answer` | grade one interview answer | |
| `save_job` | bookmark + create a `saved` application | |
| `update_application_status` | move an application through the pipeline | |
| `get_user_profile` | profile, goals, memories, resume headline | |

Tools read domain data directly from Postgres, always user-scoped (`user_id` on
every query) — the ownership exception documented in
[architecture.md](architecture.md) §9. Writes are deliberately minimal: `save_job`,
`update_application_status`, `create_interview` and the derived `job_matches` row.

## 5. Observability (PRD §31)

Every run is a row in `agent_runs` (agent, trigger, model, tokens, cached tokens,
cost, latency, status, error) with ordered `agent_traces` steps:

```
step_start → llm_call → tool_call → tool_result → … → handoff → final
             (retrieval / rerank are emitted by the RAG pipeline inside a tool)
```

Trace payloads carry the interesting detail — tool args, an ok/err flag and a
result preview, model + token counts + cost per LLM call, the handoff target and
brief, and the final step/tool/artifact summary. `ai_usage_events` records token
and cost per call for the dashboard's AI-usage panel.

**AI Activity UI**: `GET /api/v1/activity/runs` (list) and
`/api/v1/activity/runs/{id}` (run + traces) are proxied from the ai-service
endpoints above; the frontend renders them as a timeline
(`components/ai/agent-timeline.tsx`, `/activity` and `/activity/[id]`). This is
PRD §47 Demo 6 — you can open any run and see agent → tools → retrieval → sources
→ LLM → final answer.

**Streaming**: a turn *can* run as a background task (`POST /internal/agents/chat`)
publishing `status` / `message` events plus the task bus's own `done` / `error` and its `ping`
keep-alive, on the task bus — but nothing in the product calls it today: the copilot goes through
`POST /internal/agents/chat/sync`, the blocking variant, and the SSE relay only carries ingest
tasks. `token` deltas are produced only by `core/ai.py`'s per-call `emit` callback, which no
caller wires to the stream, so the client's `token` branch waits for a publisher.
