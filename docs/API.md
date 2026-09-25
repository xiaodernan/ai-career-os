# API

Reference for AI Career OS's HTTP surfaces (PRD §28).

Two API layers, deliberately separated:

| Layer | Owner | Reachable from | Auth |
|---|---|---|---|
| **Public** `/api/v1/*` | Spring Boot | browser, any client | JWT bearer (except `/health`, `/auth/*`) |
| **Internal** `/internal/*` | FastAPI ai-service | backend only, private network | `X-Internal-Token` shared secret |

The frontend only ever talks to the backend. The ai-service is never exposed to
browsers — that keeps a single authentication/ownership boundary and stops prompt
and token traffic from bypassing the JWT layer.

## 1. Conventions

**Envelope.** Every public response is wrapped:

```json
{ "success": true, "data": { }, "error": null }
```

```json
{ "success": false, "data": null,
  "error": { "code": "JOB_NOT_FOUND", "message": "Job not found", "details": [] } }
```

Error codes are a closed set in `ApiErrorCode`; the HTTP status carries the class
(400 validation, 401 unauthenticated, 403 forbidden, 404 not found, 409 conflict,
429 rate-limited, 502 upstream/AI failure) and `code` carries the precise reason.
`details` is a list (field-level validation messages).

**Pagination.** `?page=0&size=20` → `{ items, total, page, size }`.

**Naming.** JSON is camelCase. Request DTOs accept `@JsonAlias` snake_case too
(`resume_version_id` == `resumeVersionId`) so the AI service and scripts can post
either form.

**Auth.** `Authorization: Bearer <accessToken>`. Access tokens live 15 minutes;
refresh tokens rotate on every use and a replayed refresh token revokes the family
(reuse detection). Logout revokes the presented refresh token.

**Ownership.** Every user-scoped query is filtered by the authenticated user id.
Cross-user access returns 404/403, never data. This is asserted by the IDOR suite
in `backend/src/test/java/com/careeros/DomainApiIT.java`.

**Rate limits.** Redis sliding-window: strict on `/auth/*` (per IP + per account),
per-user budget on AI endpoints.

**SSE.** `text/event-stream` with events `status`, `token`, `trace`, `artifact`,
`done`, `error`.

## 2. Public API — `/api/v1`

### Health

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | liveness; no auth |

### Auth (`/auth`)

| Method | Path | Body / notes |
|---|---|---|
| POST | `/auth/register` | `{email, password, displayName}` → tokens + user |
| POST | `/auth/login` | `{email, password}` → tokens |
| POST | `/auth/refresh` | `{refreshToken}` → new token pair (rotates; reuse revokes) |
| POST | `/auth/logout` | `{refreshToken}` |
| POST | `/auth/password/forgot` | `{email}` → always 200 (no account enumeration) |
| POST | `/auth/password/reset` | `{token, newPassword}` |

### Current user

| Method | Path | Notes |
|---|---|---|
| GET | `/me` | account summary |
| PATCH | `/me` | `{displayName, headline, location, summary, yearsExperience, targetRoles, targetLocations, links, workAuthorization, preferences}` — every field optional, `null` means leave unchanged |
| GET | `/users/me` | alias of `/me` (binding seam) |
| PATCH | `/users/me` | same body as `PATCH /me` (`{displayName, headline, location, ...}`) |
| GET | `/users/me/profile` | career profile |
| PATCH | `/users/me/profile` | `{headline, summary, location, yearsExperience, targetRoles, targetLocations, links, workAuthorization, preferences}` |

### Resumes (`/resumes`)

| Method | Path | Notes |
|---|---|---|
| GET | `/resumes` | list |
| POST | `/resumes` | create from `{title, plaintext}` |
| POST | `/resumes/upload` | multipart file → MinIO → `documents` row (PDF/DOCX/TXT, magic-byte checked) |
| GET | `/resumes/{id}` | detail + versions |
| PATCH | `/resumes/{id}` | rename / relabel |
| DELETE | `/resumes/{id}` | |
| POST | `/resumes/{id}/parse` | run structured parse → profile + rows + score |
| POST | `/resumes/{id}/set-current` | mark current version |
| GET | `/resumes/{id}/versions` | version history (original + tailored) |
| GET | `/resume-versions` | all versions for the user |
| GET | `/resume-versions/{id}` | one version (structured JSON, diff, plaintext) |

### Jobs & companies

| Method | Path | Notes |
|---|---|---|
| GET | `/jobs` | search: `q, skills, location, remote, company, minSalary, maxSalary, status, sort=posted\|salary\|title\|match, page, size` |
| GET | `/jobs/saved` | bookmarked jobs |
| POST | `/jobs` | create a job (with inline `company`) |
| POST | `/jobs/import` | pasted/imported posting |
| GET | `/jobs/{id}` | detail + match breakdown |
| POST | `/jobs/{id}/save` | `{note}` → bookmark + `saved` application |
| DELETE | `/jobs/{id}/save` | |
| POST | `/jobs/{id}/match` | `{resumeVersionId?}` → evidence-bound match, persisted |
| POST | `/jobs/{id}/tailor` | `{resumeVersionId?}` → tailored version + diff |
| POST | `/jobs/{id}/cover-letter` | `{resumeVersionId?, mode, tone, length, previous, goal}` |
| GET | `/companies` | list (`?q=&page=&size=`) |
| GET | `/companies/{id}` | company intelligence + open roles |
| POST / PUT / DELETE | `/companies`, `/companies/{id}` | maintained by the application |

A query parameter binds by name, so one the endpoint does not declare is **ignored, not
rejected**: `/jobs?remoteType=hybrid` answers 200 with the unfiltered board. `remote` takes a
`remote_type` value (`onsite` / `hybrid` / `remote`), never `true`, and an unknown `sort` falls
back to `posted` for the same reason.

### JD intelligence (`/jds`)

| Method | Path | Notes |
|---|---|---|
| POST | `/jds` | `{jobId?, rawText}` → structured JD (required/preferred/hidden/priorities/topics) |
| GET | `/jds/{id}` | stored analysis |
| POST | `/jds/suggestions` | resume-improvement suggestions for a JD |

### Knowledge base (`/knowledge`)

| Method | Path | Notes |
|---|---|---|
| GET | `/knowledge/sources` | registered sources + status |
| GET | `/knowledge/sources/{id}/status` | ingestion progress |
| DELETE | `/knowledge/sources/{id}` | |
| POST | `/knowledge/text` | ingest inline text (`{kind, title, refId?, text}`) |
| POST | `/knowledge/documents` | ingest an uploaded document |
| GET / POST / PATCH / DELETE | `/knowledge/notes`, `/knowledge/notes/{id}` | user notes |

### Interviews (`/interview/sessions`)

| Method | Path | Notes |
|---|---|---|
| GET | `/interview/sessions` | list |
| POST | `/interview/sessions` | `{jobId, jdId?, resumeVersionId?, companyName?, positionTitle?, mode, config}` |
| GET | `/interview/sessions/{id}` | session + turns + evaluation |
| PATCH | `/interview/sessions/{id}` | `{status, mode, difficulty, config}` — pause / resume / abandon |
| DELETE | `/interview/sessions/{id}` | |
| POST | `/interview/sessions/{id}/opening` | first question |
| POST | `/interview/sessions/{id}/answer` | `{answer}` → evaluation + follow-up + difficulty step |
| POST | `/interview/sessions/{id}/finalize` | 8-dimension report + trajectory |

There is no `maxQuestions` field: the body binds by name, so one sent at the top level is
dropped without a word. The question budget is a key inside `config`, in the snake_case the
interview engine reads it under — `{"config": {"max_questions": 12}}`, default 8. `config` is
stored verbatim on the session, so the same place takes the rest of the run's tuning.

### Applications (`/applications`)

| Method | Path | Notes |
|---|---|---|
| GET | `/applications` | board (`?status=&page=&size=`) |
| POST | `/applications` | create |
| GET | `/applications/{id}` | detail |
| PATCH | `/applications/{id}` | `{status, position, note, reminderAt}` — kanban drag & drop; `reminder_at` is accepted as an alias, `note` (singular) is the writable one |
| PUT | `/applications/{id}/reorder` | `{position, status?}` within column |
| GET | `/applications/{id}/timeline` | status-transition audit events |
| DELETE | `/applications/{id}` | |

### Copilot & conversations

| Method | Path | Notes |
|---|---|---|
| POST | `/copilot/chat` | `{message, conversationId?, context?}` → `{conversationId, userMessageId, assistantMessageId, answer, artifacts[], sources[], actions[], runId}` (synchronous; both messages persisted) |
| GET | `/conversations` | list |
| POST | `/conversations` | create |
| GET / PATCH / DELETE | `/conversations/{id}` | |
| GET | `/conversations/{id}/messages` | transcript with artifacts/sources/actions |

### Dashboard, activity, search, AI usage

| Method | Path | Notes |
|---|---|---|
| GET | `/reports/dashboard` | pipeline health, counts, recommended jobs, skill gaps, resume score, recent insights |
| GET | `/activity/runs` | agent runs (`?limit=&agent=`) |
| GET | `/activity/runs/{id}` | run + ordered traces (AI Activity detail) |
| GET | `/ai-usage/summary` | tokens, requests, cached tokens, estimated cost |
| GET | `/search` | global ⌘K search (`?q=`, required) across jobs/companies/resumes/interviews/notes/KB/conversations |
| GET | `/ai/stream/{taskId}` | SSE relay of an ai-service task |

## 3. Internal API — ai-service

Requires `X-Internal-Token`. `X-User-Id` (and optionally `X-Run-Id`) supply the
tenant context via `core.deps.Ctx`.

| Method | Path | Purpose |
|---|---|---|
| POST | `/internal/agents/chat` | run a copilot turn as a background task → `{task_id, run_id}` |
| POST | `/internal/agents/chat/sync` | blocking turn → `Outcome` (relay + E2E + eval harness) |
| GET | `/internal/agents/runs` | runs list |
| GET | `/internal/agents/runs/{run_id}` | run + traces |
| POST | `/internal/features/resume/parse` | structured resume parse + score |
| POST | `/internal/features/jd/analyze` | JD intelligence |
| POST | `/internal/features/match` | deterministic match |
| POST | `/internal/features/tailor` | tailoring + diff (no fabrication) |
| POST | `/internal/features/cover-letter` | cover letter |
| POST | `/internal/features/jd/suggestions` | improvement suggestions |
| POST | `/internal/ingest/document/{doc_id}` | ingest a stored document |
| GET | `/internal/ingest/documents/{doc_id}/text` | extracted document text (used by backend resume parsing) |
| POST | `/internal/ingest/text` | ingest inline text |
| POST | `/internal/rag/retrieve` | hybrid retrieval + citations |
| POST | `/internal/rag/answer` | retrieval + grounded answer |
| POST | `/internal/rag/chunks` | chunk listing / inspection |
| POST | `/internal/interview/opening` | first question |
| POST | `/internal/interview/answer` | evaluate + follow up |
| POST | `/internal/interview/finalize` | final report |
| GET | `/internal/tasks/{task_id}` | task state |
| GET | `/internal/tasks/{task_id}/stream` | task SSE (canonical) |
| GET | `/internal/stream/{task_id}` | SSE alias the backend relay proxies as `/api/v1/ai/stream/{taskId}` |
| GET | `/health` | liveness + provider probe (no auth) |

## 4. Worked examples

```bash
B=http://127.0.0.1:8080/api/v1

# register and capture the access token
TOKEN=$(curl -s -X POST $B/auth/register -H 'Content-Type: application/json' \
  -d '{"email":"a@example.com","password":"Str0ngPassphrase!23","displayName":"A"}' \
  | python -c 'import sys,json;print(json.load(sys.stdin)["data"]["tokens"]["accessToken"])')

# upload and parse a resume
curl -s -X POST $B/resumes/upload -H "Authorization: Bearer $TOKEN" \
  -F file=@resume.pdf -F title='Main resume'
curl -s -X POST $B/resumes/$RID/parse -H "Authorization: Bearer $TOKEN"

# search jobs, then score one against the resume
curl -s "$B/jobs?q=Agent&remote=hybrid&sort=match" -H "Authorization: Bearer $TOKEN"
curl -s -X POST $B/jobs/$JID/match -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{}'

# ask the copilot, then inspect what the agent actually did
curl -s -X POST $B/copilot/chat -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"message":"帮我找适合我的 AI Agent 岗位"}'
curl -s "$B/activity/runs?limit=5" -H "Authorization: Bearer $TOKEN"
```

## 5. OpenAPI

Spring Boot exposes generated OpenAPI through springdoc (`/v3/api-docs`,
`/swagger-ui.html`) and FastAPI serves its own at `/docs`. This document is the
hand-written overview that explains the *why*; the generated specs are the
mechanical field-level reference.
