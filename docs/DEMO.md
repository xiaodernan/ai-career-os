# Demo — the eight-minute golden journey

A script for showing AI Career OS to someone who has never seen it. It walks the loop the
product actually runs — **resume → knowledge → job discovery → JD intelligence →
evidence-matched scoring → tailored materials → mock interview → tracking → growth** — and
ends with the user leaving with their own data.

Two rules for the person driving:

1. **Every AI claim must trace to the user's own material.** When the match or the cover
   letter cites a skill, open the evidence chip; if the resume does not support it, the
   product is not supposed to claim it. Do not narrate a capability the screen does not show.
2. **Numbers are computed, not narrated.** Coverage %, salary percentiles and match scores
   are arithmetic over the user's data and the corpus; say "computed from these postings",
   not "the AI thinks".

## Before you start

- Bring the stack up (see `docs/DEPLOYMENT.md`) and seed the demo corpus:
  `docker compose up -d postgres redis minio minio-init seed-jobs`
  (12 companies / 41 roles).
- Have one real resume file (PDF/DOCX) ready — the demo is only convincing with real text.
- Use a fresh account so the knowledge base, applications and growth history start empty.

## The journey

| # | Page | What to show | Why it lands |
|---|------|--------------|--------------|
| 1 | `/register` → `/login` | Create the demo account, sign in. | The rest of the app is authenticated; job search and every personal surface need the session. |
| 2 | `/resumes` | Upload the resume; watch the pipeline move through extracting → cleaning → chunking → embedding → indexing. Open the parsed profile. | Shows the resume became *structured evidence*, not just a stored file. |
| 3 | `/jobs` | Search a role ("backend", "AI agent", a city). Open a posting. | The corpus is real and searchable; this is the discovery half. |
| 4 | `/jobs/[id]` | Run **match**. Expand the evidence for two skills — one covered, one a gap. | This is the core claim: a score backed by the user's own resume sections, with the gap named. |
| 5 | same page | **Tailor** the resume, then draft the **cover letter**. Show the diff/notes. | Materials are generated *from* the evidence, and the diff shows exactly what changed. |
| 6 | `/interviews` | Start a mock interview for the job, answer two questions, open the report. | The coach is adaptive and scores answers; the report is the takeaway. |
| 7 | `/applications` | Move the job through saved → applied → OA → interview. | The tracker is the operating spine; stages feed the analytics. |
| 8 | `/growth` | Enter a target role; show readiness, the covered/partial/gap split, the salary band, the learning plan, and the progress delta on a second run. | The growth loop: what to learn next, what it pays, and whether the last run moved. |
| 9 | `/networking` | Add a contact; show the stale/follow-up ranking and draft a referral message. | Outreach is evidence-bound — it uses only the contact's own fields, never a invented shared history. |
| 10 | `/copilot` | Ask one question that needs several tools ("find backend roles that fit me and tailor for the best one"). | One conversation orchestrates search → match → tailor, with the same evidence rules. |
| 11 | (terminal) | Export and preview a restore: `python -m app.ops.restore_plan backup.json` | The user can leave with their data, and an operator can dry-run a restore before any write. |

## API equivalents (technical audience)

The UI above is a thin client over the backend's public API; shapes are in `docs/API.md`.

| Step | Method + path |
|------|---------------|
| Register / log in | `POST /api/v1/auth/register`, `POST /api/v1/auth/login` |
| Upload / parse a resume | `POST /api/v1/resumes/upload`, `POST /api/v1/resumes/{id}/parse`, `POST /api/v1/resumes/{id}/set-current` |
| Ingest pasted text into the knowledge base | `POST /api/v1/knowledge/text` |
| Search jobs | `GET /api/v1/jobs` (authenticated) |
| Match / tailor / cover letter | `POST /api/v1/jobs/{id}/match`, `/tailor`, `/cover-letter` |
| Mock interview | `POST /api/v1/interview/sessions`, `/{id}/opening`, `/{id}/answer`, `/{id}/finalize` |
| Track an application | `GET/POST /api/v1/applications`, `PATCH /api/v1/applications/{id}` |
| Growth report | `POST /api/v1/growth-report` |
| Contacts | `GET/POST /api/v1/contacts` |
| Copilot | `POST /api/v1/copilot/chat` (or `/chat/stream` over SSE) |

## Ops dry-runs worth showing

```bash
# is this configuration safe to run in prod? (no DB, no network)
cd ai-service && python -m app.ops.preflight

# what would a restore create / update / delete? (no DB)
python -m app.ops.restore_plan backup.json [--existing current.json]

# what would ingesting this feed write? (no DB)
python -m app.ops.ingest_plan feed.xml [--existing corpus.json] [--now 2026-10-17T00:00:00Z]
```

All three are pure: they read a file (or the settings) and print a plan. Use them to show
that the write is previewable *before* it happens.

There is a fourth that is not pure, and it earns its place for exactly that
reason:

```bash
# does the portable export still build against the schema this database has? (DB, no app)
cd ai-service && python -m app.ops.check_export [user-id]
```

The export's fetch functions are monkeypatched in the unit tests, so a query
that names a column the schema does not have is invisible there — and it
happened: the export read `interview_sessions.created_at`, a column that
table has never had. `check_export` builds the bundle against the real
schema and exits 1 with the reason when it cannot. The nightly CI job runs
it, because the app images are deliberately not built there.

## If someone asks "is this just an LLM?"

No. The scores, coverage, percentiles, funnel and freshness are deterministic functions
over the user's data and the corpus; the model is used for wording, and generation passes a
no-fabrication verifier. The offline providers (`LLM_PROVIDER=mock`, `EMBEDDING_PROVIDER=hash`)
exist only for tests and first-run dev — a production deploy refuses them, and the preflight
above is the gate that catches it.
