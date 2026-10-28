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
| POST | `/auth/password/forgot` | `{email}` → always 200 (no account enumeration); the mail carries `<app.web.base-url>/reset-password?token=…` (the dev stack logs it while APP_EMAIL_CONSOLE_LOGBODY is on), good for 30 minutes |
| POST | `/auth/password/reset` | `{token, newPassword}` → single-use token; revokes every session the user had |

### Current user

| Method | Path | Notes |
|---|---|---|
| GET | `/me` | account summary |
| PATCH | `/me` | `{displayName, headline, location, summary, yearsExperience, targetRoles, targetLocations, links, workAuthorization, preferences}` — every field optional, `null` means leave unchanged |
| GET | `/users/me` | alias of `/me` (binding seam) |
| PATCH | `/users/me` | same body as `PATCH /me` (`{displayName, headline, location, ...}`) |
| GET | `/users/me/profile` | career profile |
| PATCH | `/users/me/profile` | `{headline, summary, location, yearsExperience, targetRoles, targetLocations, links, workAuthorization, preferences}` |

### Long-term memory

What the agents remember about the caller (AGENTS.md §6). The write path runs at the end of
every chat turn and at interview finalize; these three routes are how a user reads it back
and corrects what the extractor got wrong. Ownership is enforced by the AI service, so a
record the caller does not own answers 404 rather than 403.

| Method | Path | Notes |
|---|---|---|
| GET | `/memories` | every memory for the caller, newest update first; optional `kinds` filter (comma-separated, repeatable) |
| PATCH | `/memories/{id}` | `{content, importance}` — either or both; `content` ≤ 4000 chars, `importance` 0.0–1.0. A blank `content` is a 400, because "delete it" is what `DELETE` is for |
| DELETE | `/memories/{id}` | forgets one memory; 204 |

### Growth report

The roadmap 10.2 bridge: one call composes readiness (10.7), gap analysis (10.1), salary
benchmark (12.1), the learning plan (10.5) and progress-vs-previous (10.6) into the growth
page's single answer. The report's schema is the AI service's — this route forwards the
request and answers the engine's shape, and rate-limits as an AI-costing path.

| Method | Path | Notes |
|---|---|---|
| POST | `/growth-report` | `{targetRole, seniority, resumeVersionId, location, currency, targetSalary, previous}` → the composed report. `targetRole` is required and floored at 10 characters (the engine's own floor); everything else is optional, `currency` a 3-letter code. `previous` is a prior report's own shape, for the progress diff; a report is computed, not stored, so there is nothing to GET |

### Analysis & monitoring

The 15.x and 16.1 bridges. Both answers are computed by the AI service's own
engines — the funnel, response rates and digest are deterministic reads over the
caller's application history, and the health report is a deterministic read over
the caller's agent runs. No model runs here.

| Method | Path | Notes |
|---|---|---|
| GET | `/analysis/insight-digest` | the weekly insight digest — the generated-at stamp, the staleness window, the total and active application counts, the live stage mix, the response and offer rates, the stalled count with its rows, and the engine's own signals. A stalled row is aged from the latest of its timestamps that has already passed, because a stamp from next month — which an `applied_at` imported from the caller's own bundle can carry — is not evidence of silence; a row whose timestamps all lie later than the generated-at stamp is left out rather than aged. The stage mix is a distribution: each application is counted once, under the status it holds now, so the counts add up to the total — the page draws them as shares of it. Cumulative reached-stage counts belong to `/analysis/pipeline-funnel` and are not in this answer. `locale` (en or zh) picks the language of the engine's signals — the digest's only words — and anything else answers in the product default, English; no other query parameter is read, because the digest is computed for the caller |
| GET | `/analysis/pipeline-funnel` | the pipeline funnel — one row per stage with the count that reached it and the conversion at each step, plus the applied / saved / rejected / total counts. Reached-stage semantics are cumulative: reaching the interview means the application also reached the applied stage, so these counts deliberately do not add up to the number of applications. The counts read each row's current status, so a rejection is credited with the applied stage only — the stages an application actually passed are timed by `/analysis/response-rate`, which reads the status-change log |
| GET | `/analysis/response-rate` | the response rates — of everything submitted, what fraction got any reply (a rejection included), what fraction reached an interview, what fraction reached an offer, and the average and median days per stage. Applications missing a timestamp are skipped for that stage's duration rather than counted as zero, and so are pairs that cannot be a duration: a stage stamped before the submission, or either moment later than the generated-at stamp the answer is measured from |
| GET | `/monitoring/health-report` | agent health — the verdict (healthy / warn / regressed), the error rate, the run count, the cost and token totals, the latency percentiles, the alert list and the regression list. No query parameters: the window is the account's own |
| GET | `/monitoring/nightly-reports` | the install's nightly verification history, newest first — one row per night the scheduled job recorded: the status, the commit and the run's link, when it started and finished, and each step's own status with the numbers it measured. Deployment-wide rather than per account: the history is the same for every reader, which is what makes it a record of the install. `page` (floored at 0) and `size` (default 10, clamped to 100) paginate; the list is append-only, so page 0 always holds the newest nights |
| GET | `/monitoring/nightly-reports/verdict` | the install's own verdict as one answer rather than a page: the newest night's status — passed, failed, or missing when no night has ever recorded — with its finish, commit and run link, how many newest nights in a row ended failed (the walk stops at 30), and whether the newest record is older than the cadence (a stale flag with the 36-hour window). A stale verdict is a warning even when that night passed: a record that stopped arriving is the failure nothing wrote down. No query parameters; deployment-wide like the history |
| GET | `/rate-limit/status` | the configured limits — whether limiting is on, the per-minute AI cap and the per-minute auth cap — plus the caller's remaining AI-bucket quota. Only the AI bucket is reported: it is keyed by the authenticated user id, so the number the page shows is the number the limiter enforces. The auth bucket is keyed by client IP, which the server cannot know from the principal alone — reporting a number for it would be a guess |

### Weekly digest (`/digests`)

The 19.4 letter: the 15.3 digest composed on the backend's clock and kept, so a week's
signals outlive the week. One letter per account per week, refreshed in place; the payload
is the engine's own answer, stored as it came back, and is the material an email would be
assembled from.

| Method | Path | Notes |
|---|---|---|
| GET | `/digests` | the caller's letters, newest week first, at most twelve — each one the Monday its week starts on, the window it was composed with, when it was written, and the frozen digest payload the engine answered. No query parameters: the list is the caller's own and the cap is the server's |
| POST | `/digests/run` | composes the current week's letter now and files it, refreshing it if it already exists; answers the filed letter as the list answers one row. No request body and no query parameters — the week is now and the window is the letter's own. The Monday schedule writes the week that just ended, when it can no longer change |

### Resumes (`/resumes`)

| Method | Path | Notes |
|---|---|---|
| GET | `/resumes` | list |
| POST | `/resumes` | create from `{title, plaintext}` |
| POST | `/resumes/upload` | multipart file → MinIO → `documents` row (PDF/DOCX/TXT, magic-byte checked); the document pair and the resume's own rows are filed in one transaction, so an upload that cannot file its resume files neither |
| GET | `/resumes/{id}` | detail + versions; **sourceFileKey** says whether an original file exists |
| GET | `/resumes/{id}/file` | the original upload's bytes, `Content-Disposition: attachment`, named from the document row — user-scoped, 404 when the resume has no file |
| PATCH | `/resumes/{id}` | rename / relabel |
| DELETE | `/resumes/{id}` | |
| POST | `/resumes/{id}/parse` | run structured parse → profile + rows + score |
| POST | `/resumes/{id}/set-current` | mark current version |
| GET | `/resumes/{id}/versions` | version history (original + tailored) |
| GET | `/resume-versions` | all versions for the user |
| GET | `/resume-versions/{id}` | one version's metadata — label, kind, job, score, diff; the body is not in this shape, and the print route below is the read that renders it |
| POST | `/resume-versions/{id}/print` | `{locale}` → `{html}` — one version as a self-contained, print-ready document in the reader's language: its structured body section by section, or its stored text when it was never parsed. The browser's own print dialog is the PDF. Scoped to the caller: a version that is not the caller's is a 404, not someone's resume |

### Jobs & companies

| Method | Path | Notes |
|---|---|---|
| GET | `/jobs` | search: `q, skills, location, remote, company, minSalary, maxSalary, status, sort=posted\|salary\|title\|match\|relevance, page, size` — blank `sort` = relevance for a query, recency for a browse; every ordering ends in the job id, so a page is a partition of the board rather than of a plan's mood |
| GET | `/jobs/saved` | bookmarked jobs |
| GET | `/saved-searches` | this caller's saved searches, newest first |
| POST | `/saved-searches` | `{name, criteria}` → the saved search (201). `criteria` uses the board's own names (`q`, `skills`, `location`, `remote`, `company`, `minSalary`, `maxSalary`) and at least one is required; a repeated skill folds to one, a blank one is dropped, and `remote=false` is not stored because the switch means "remote only" |
| DELETE | `/saved-searches/{id}` | forgets one saved search; 204 |
| POST | `/jobs` | create a job (with inline `company`) |
| POST | `/jobs/import` | pasted/imported posting |
| GET | `/jobs/{id}` | detail + match breakdown |
| POST | `/jobs/{id}/save` | `{note}` → bookmark + `saved` application |
| DELETE | `/jobs/{id}/save` | |
| POST | `/jobs/{id}/match` | `{resumeVersionId?}` → `{jd, match, matchId}` — evidence-bound match, persisted; the stored row also answers `whyMatch` (bullets only for dimensions that clear their bar), `preparation` items with `title`, `reason`, `priority`, ordered by the overall-score points closing each gap, and `skillGaps` items with `skill`, `importance` (the JD's own priority word) and `reason` (the phrase the JD used to ask) — all three are columns, so the job detail replays the same cards after a refresh |
| POST | `/jobs/{id}/tailor` | `{resumeVersionId?}` → tailored version + diff |
| POST | `/jobs/{id}/tailored-version` | `{resumeVersionId, tailored, diff, plaintext}` → keeps a reviewed draft as a new version of that resume (201) |
| POST | `/jobs/{id}/cover-letter` | `{resumeVersionId?, mode, tone, length, previous, goal}` |
| GET | `/companies` | list (`?q=&page=&size=`), name ascending — the order the pages partition by; each row is a CompanyItem — profile fields plus openRoleCount |
| GET | `/companies/{id}` | `{company, openRoles}` — the profile including culture, interviewProcess and sources (the three POST accepts and no read path used to carry), and the company's status='open' roles in the board's own row shape, best match first, capped at Paging.MAX_PAGE_SIZE while company.openRoleCount stays the real total. Scoped by id, not by the board's ?company= name facet. Company rows are maintained by the application (the inline company field on job create/import); there are no client-facing write endpoints |
| POST | `/companies/brief` | `{company, top?}` → what the corpus says about one company: its roles, the skills its postings ask for, and the interview topics they name. A deterministic read — a company the corpus does not carry answers with no rows rather than a plausible summary |

### Job ingestion (`/jobs/ingest`)

The 14.2-14.3 bridge. Every route is a deterministic read of the payload the
caller brings: the parse is stdlib-only, the de-duplication is an exact
fingerprint match, and the freshness sweep partitions by age. Nothing is fetched
from the network here, and no model runs.

| Method | Path | Notes |
|---|---|---|
| POST | `/jobs/ingest/parse` | `{feed, source}` → `{postings[], count}`. `feed` is RSS 2.0 / Atom XML or a board-API JSON payload; `source` names the connector. A broken or oversized feed raises rather than answering an empty success |
| POST | `/jobs/ingest/dedupe` | `{postings[]}` → `{unique[], duplicates[], inputCount, uniqueCount, duplicateCount}`. Exact-fingerprint duplicates collapse to the newest / most complete survivor; the fingerprint is company + title + location, so the same title in two cities stays distinct |
| POST | `/jobs/ingest/freshness-sweep` | `{postings, maxAgeDays?, staleSeenDays?}` → `{fresh[], stale[], expired[], undated[], counts}`. A posting with no usable date is reported under `undated` rather than silently bucketed as fresh |
| POST | `/jobs/ingest/plan` | `{feed, source?, existing?, maxAgeDays?, staleSeenDays?}` → `{create[], update[], close[], duplicates[], counts}`. One plan for a sweep: `close` is proposed only for a posting that is expired *and* absent from this batch, so a still-live posting is never closed for not reappearing today |

### Scheduled ingestion (`/ingestion`)

The 19.2 layer. A feed is a URL the caller subscribes to; the backend's clock
fetches it, hands the body to the same plan engine 14.3 uses, and files the plan
as a run. A plan is the record; nothing is applied when it is filed. Applying
is the reader's own step (`POST /ingestion/runs/{id}/apply`, below), so no sweep
ever rewrites the corpus as a side effect of reading a feed. A failed
pull is a run with `status: "failed"` and the reason, not a 5xx: the feed being
down is the outcome the caller asked to see. The URL is checked at fetch time
against private, loopback, link-local and carrier-grade addresses, and again on
every redirect hop, so a feed cannot make the server read its own network.
Board sources (19.8) are the one exception to the absolute-URL rule: with
`source=greenhouse` or `source=lever`, `url` may also be the board's bare token
or its human page address, and the connector turns it into the API URL it
stores; a name the connector cannot read is refused with the sentence that
says what would work.

| Method | Path | Notes |
|---|---|---|
| GET | `/ingestion/feeds` | this caller's feeds, newest first, each with its last run (or null) |
| POST | `/ingestion/feeds` | `{name, url, source}` → the feed (201). `source` defaults to `feed`, a generic RSS/Atom or board-JSON address re-checked at fetch time; `greenhouse` / `lever` name a board whose `url` may be a token, page address or API URL, stored as the API URL the connector derives. For a board, `name` is also the company its postings belong to. At most 20 feeds per user |
| PATCH | `/ingestion/feeds/{id}` | `{enabled}` — the one switch: whether the night's sweep includes this feed |
| DELETE | `/ingestion/feeds/{id}` | forgets the feed and the runs it filed; 204 |
| POST | `/ingestion/feeds/{id}/run` | pulls one feed now and answers the run plus the engine's plan — create / update / close / duplicates and their counts. A failed pull answers 200 with `status: "failed"` and `error` |
| GET | `/ingestion/runs` | the caller's runs, newest first, one page at a time — `page` (default 0) and `size` (default 20, clamped to 100) → {items, total, page, size} |
| GET | `/ingestion/runs/{id}` | one run plus its stored plan |
| POST | `/ingestion/runs/{id}/apply` | writes the run's stored plan to the board in one transaction — creates the postings the plan calls new, refreshes the ones it names (re-opening a closed one), closes exactly the open rows it lists as closed; companies are reused by name, and a blank company takes the feed's. Answers `{created, updated, closed, appliedAt}`; the counts are what the write produced, so a plan row the board already has is not a create. Applying twice is 409 `INGESTION_RUN_ALREADY_APPLIED`; a failed run, or one whose plan is missing, is 409 `INGESTION_RUN_NOT_APPLICABLE` |

### Notification center (`/notifications`)

The 19.3 inbox. Nothing is stored as a notification: every item is synthesized
from a signal the platform already wrote down — an open application whose
reminder has come due or that has gone quiet for the dashboard's own 14-day
window, and the last week's pulls that failed or proposed new postings. What
persists is what the reader did with each item, keyed by the signal's own
episode (`reminder:<applicationId>:<reminderAt>`, `stale:<applicationId>:<updatedAt>`,
`ingestion:<runId>`), so a dismissal silences that episode and a new reminder or
a new update arrives unread. A read or dismissed key the inbox is not currently
showing is ignored, and every write answers with the fresh inbox.

| Method | Path | Notes |
|---|---|---|
| GET | `/notifications` | the synthesized inbox, newest first, with the unread count → {items[], unread, generatedAt} |
| POST | `/notifications/read` | `{keys}` → marks the named items read and answers the fresh inbox: {items[], unread, generatedAt}. Keys not in the inbox are ignored |
| POST | `/notifications/read-all` | marks every item the inbox is showing read; answers the fresh inbox, the same shape GET /notifications answers |
| POST | `/notifications/dismiss` | `{key}` → files one item away and answers the fresh inbox: {items[], unread, generatedAt} |

### Growth engines (`/growth`)

The granular 10.x engines, each asked on its own. The 10.2 aggregate
(`POST /growth-report`) composes the same engines for the growth page in one
call; these routes are the same engines one at a time, so a caller that wants
only the gap analysis does not have to run the whole report to get it.

Every answer is the engine's own shape — the bridge forwards the request and
owns none of it. All nine take the same request record, because they share a
shape: a target role, optionally a resume version, and the specializations
that narrow the question.

| Method | Path | Notes |
|---|---|---|
| POST | `/growth/gap-analysis` | `{targetRole, seniority?, resumeVersionId?, location?, currency?, targetSalary?, top?}` → the coverage and the gaps. `targetRole` is required and floored at 10 characters (the engine's own floor) |
| POST | `/growth/readiness` | the same request → one verdict (`ready` / `borderline` / `not_ready`), the coverage, the covered/partial/open counts, and the blockers. A must-gap caps a `ready` |
| POST | `/growth/learning-plan` | the same request → the phased study items (foundation → core → applied) with category-aware resource hints |
| POST | `/growth/skill-demand` | the same request → which skills a role family's postings ask for, and how often — the market-centric half of the gap view |
| POST | `/growth/learning-priority` | the same request → the gaps enriched with their market demand and ranked by importance × market pull, so the candidate learns the most-asked-for missing skill first |
| POST | `/growth/progression` | the same request → the stepping-stone role families that build the dream role's missing skills, each with the skills it builds, its current coverage and the bridge score that ranks it. `targetRole` is the role being aimed at |
| POST | `/growth/interview-prep` | the same request → the pre-interview checklist: the weak areas to study, the strength stories to rehearse, and the likely topics |
| POST | `/growth/story-bank` | `{resumeVersionId?, top?}` → the STAR stories drawn from the profile's own evidence |
| POST | `/growth/role-suggestions` | `{resumeVersionId?, top?}` → the target roles this profile could plausibly aim at |
| POST | `/growth/progress` | `{targetRole?, seniority?, resumeVersionId?, previous?}` → the skill progress: closed / improved / regressed / still open, and the coverage delta. `previous` is a prior gap report's own shape, for the diff; without it the answer is a baseline |

### Outreach (`/outreach`)

| Method | Path | Notes |
|---|---|---|
| POST | `/outreach/draft` | `{name, role?, company?, purpose?, context?, resumeVersionId?}` → the drafted message and the evidence it cited. `name` is required; `purpose` is the kind of message (referral / intro / coffee-chat / thank-you) and defaults to `referral`. The draft is **evidence-bound**: the validator strips any skill the profile does not support, so a message can only cite what the candidate can back up |

### Offers (`/offers`)

The 12.x bridges. Every answer is a deterministic read of the seeded corpus
against the caller's own offer — no model invents a number here.

| Method | Path | Notes |
|---|---|---|
| POST | `/offers/salary-benchmark` | `{role, location?, seniority?, targetSalary?, currency?}` → the percentiles (p25/p50/p75), the sample size and the currency. `role` is required and floored at two characters |
| POST | `/offers/negotiate` | `{role, location?, seniority?, currency?, offerBase, matchScore?}` → the verdict, the benchmark it was measured against, the leverage and the talking points. `matchScore` is 0..1 and changes the leverage named |
| POST | `/offers/compare` | `{role, location?, seniority?, currency?, matchScore?, offers}` → one row per offer (`label`, `base`, `bonus`, `firstYearCash`, `annualEquity`, `totalComp`, `assessment`), the `best` row, and the engine's notes. The ranking is by **total compensation** — first-year cash plus the grant annualized over its vest — while the market verdict compares **base** to the benchmark, because the benchmark is base salary. An offer with no grant ranks exactly as a cash-only one |
| POST | `/offers/counter-offer` | `{role, location?, seniority?, currency?, offerBase, matchScore?}` → the deterministic anchor, the reasons behind it, and a script that phrases them. The anchor is computed, never guessed: no model writes a number here |

### Data portability (`/data-portability`)

The 13.1-13.3 bridge. The bundle's schema and its content hash are the AI
service's — this route forwards the request and answers the engine's shape.

| Method | Path | Notes |
|---|---|---|
| POST | `/data-portability/export` | `{anonymized?}` → the export bundle: `schema_version` (`1.1.0`), `generator`, `generated_at`, `user`, `manifest` (`counts`, `content_hash`, `anonymized`) and `data`. The hash covers only the data payload, so re-exporting unchanged data yields the same hash. `anonymized` strips the profile's PII fields before the bundle is built. Since 1.1.0 the bundle also carries the two sections the **backend** owns — `applications` and `growth_plans` — so an export is the candidate's pipeline and not only their reading list |
| POST | `/data-portability/import-plan` | `{bundle, existing?}` → `{schema_version, source_content_hash, sections, op_counts}`. The plan is idempotent by construction: every op is `create`, `update`, `delete` or `skip`, and a row whose content did not change is a `skip` (the comparison covers exactly the fields a restore writes, not the ids, the ownership or the stamps the database sets). `existing` is the caller's current state; when the caller sends none the backend reads its own workspace, and the engine's route reads the six sections it owns itself, overlaying only the caller's gaps — a preview is a comparison, never a guess. The sections split two ways: the ones the restore keeps ids for (profile, applications, growth runs, notes, contacts, job descriptions, interviews) are matched by id, so a row the bundle omits is a `delete`; the ones the restore re-mints (resumes, knowledge, memories) are matched by content and never delete. A bundle written before 1.1.0 is still accepted — the required set is read off the bundle's own schema version. A bundle that is not a bundle is a **400** carrying `IMPORT_BUNDLE_INVALID` and the sentence that says what is wrong with the file (`errors` lists it): the reader's file is the input, so the file is what the answer must name |
| POST | `/data-portability/import-apply` | `{bundle}` → `{applied, skipped, op_counts}`. The plan is computed and then executed: the `applied` map says what each section wrote — `created`, `updated`, `deleted` and `unchanged` — and `skipped` names every section the bundle carried no rows for **with the reason**. A `skip` op writes nothing, so re-importing a bundle the workspace exported reports `unchanged` rows and no writes. A `delete` retires the caller's own row (an interview whole — its transcript and report cascade), and an updated interview's transcript is replaced rather than merged, because the bundle carries it whole. A partial restore is visible rather than reported as a success. Only the caller's own rows are touched — a bundle naming another user's id finds nothing to change |
| POST | `/data-portability/redact` | `{bundle, drop?}` → the bundle with the named sections removed, its content hash recomputed over what is left and `manifest.redacted_sections` recording what went. The manifest's counts are recomputed too, and the bundle stays valid — a withheld section is not a missing one, so the redacted file can still be restored. An unknown section name is rejected rather than silently dropping the wrong (or no) section — a **400** (`EXPORT_SECTIONS_UNKNOWN`) naming the sections that are real, with the rejected ones in `invalid` |
| POST | `/data-portability/render` | `{bundle, format?, locale?}` → `{format, html}`, `{format, markdown}` or `{format, bytes_base64}`. The human-readable half of 13.1: a self-contained, print-ready document (A4, monochrome, page-break-friendly) with every field HTML-escaped — the bundle is user data and is treated as untrusted on render. `format` is `html` (the default, and already print-ready in a browser), `markdown` (the same sections and words as a diffable text document) or `pdf`; the PDF converter is an optional dependency, so a build without it answers the HTML and says why the PDF is not there. `locale` is the reader's language: the bundle carries the data and the view carries the words |

A query parameter binds by name, so one the endpoint does not declare is **ignored, not
rejected**: `/jobs?remoteType=hybrid` answers 200 with the unfiltered board. `remote` takes a
`remote_type` value (`onsite` / `hybrid` / `remote`), never `true`, and an unknown `sort` falls
back to `posted` for the same reason. `sort=relevance` fuses keyword/tsvector rank with the
query vector's cosine distance (the agent's `search_jobs` fusion) and answers keyword-only when
no vector is available. `GET /search`'s jobs channel runs the same fusion over the whole
catalogue, so the palette and the board rank one query the same way.

### JD intelligence (`/jds`)

| Method | Path | Notes |
|---|---|---|
| POST | `/jds` | `{jobId?, rawText}` → structured JD (required/preferred/hidden/priorities/topics) |
| GET | `/jds/{id}` | stored analysis |
| POST | `/jds/suggestions` | resume-improvement suggestions for a JD |

### Knowledge base (`/knowledge`)

| Method | Path | Notes |
|---|---|---|
| GET | `/knowledge/sources` | registered sources + status (`?page=&size=&documentId=` — the last narrows to the document a citation points at) |
| GET | `/knowledge/sources/{id}/status` | ingestion progress |
| DELETE | `/knowledge/sources/{id}` | |
| POST | `/knowledge/text` | ingest inline text (`{kind, title, refId?, text}`) |
| POST | `/knowledge/documents` | ingest an uploaded document: multipart `file`, optional `kind` and `title`; the source row and its document row are filed in one transaction, so an upload that cannot store its document stores neither |
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
| POST | `/interview/sessions/{id}/answer` | `{answer}` → evaluation + follow-up + difficulty step; the candidate's turn, the follow-up and the difficulty step are filed in one transaction, so an answer that cannot file its follow-up files no turn at all |
| POST | `/interview/sessions/{id}/finalize` | 8-dimension report + trajectory; the report row and the session's completion are filed in one transaction, so a finalize that cannot close the session files neither |
| GET | `/interview/voice` | whether this deployment has a speech provider, and which halves of the seam it can do — the runner's fallback gate: no provider means the browser's own speech APIs, or the text box |
| POST | `/interview/sessions/{id}/voice/transcribe` | `{audio, mime?, locale?}` — base64 of one recorded answer → `{text, provider}`; a blank transcript is `AI_SERVICE_EMPTY_RESPONSE`, never a silent success |
| POST | `/interview/sessions/{id}/voice/speak` | `{text, locale?}` → `{audio, mime, provider}` — base64 of the spoken question for the runner's play button |

There is no `maxQuestions` field: the body binds by name, so one sent at the top level is
dropped without a word. The question budget is a key inside `config`, in the snake_case the
interview engine reads it under — `{"config": {"max_questions": 12}}`, default 8. `config` is
stored verbatim on the session, so the same place takes the rest of the run's tuning.

### Contacts (`/contacts`)

The networking registry (roadmap 11.1): the people a search actually touches. Every row is
the caller's own; the optional fields a request omits are absent on the wire, not empty
strings, and `lastTouchAt` is the user's claim about when contact last happened.

| Method | Path | Notes |
|---|---|---|
| GET | `/contacts` | this caller's people, most recently updated first |
| POST | `/contacts` | `{name, role, company, relation, email, notes, lastTouchAt}` → the row (201). `name` is the only required field |
| PATCH | `/contacts/{id}` | same shape, full replace (the form's current values); 404 when the row is not the caller's |
| DELETE | `/contacts/{id}` | forgets one contact; 204 |

### Applications (`/applications`)

| Method | Path | Notes |
|---|---|---|
| GET | `/applications` | board (`?status=&page=&size=`) |
| POST | `/applications` | create |
| GET | `/applications/{id}` | detail |
| PATCH | `/applications/{id}` | `{status, position, note, reminderAt, clearReminderAt, offerCompensation, rejectionReason}` — kanban drag & drop; `reminder_at` / `clear_reminder_at` are the accepted aliases, `note` (singular) is the writable one, a null component means "leave it alone" (so removing a reminder travels as `clearReminderAt: true`), and the outcome pair records the compensation on an offer or the reason on a rejection |
| PUT | `/applications/{id}/reorder` | `{position, status?}` within column |
| GET | `/applications/{id}/timeline` | status-transition audit events |
| DELETE | `/applications/{id}` | |

### Copilot & conversations

| Method | Path | Notes |
|---|---|---|
| POST | `/copilot/chat` | `{message, conversationId?, context?}` → `{conversationId, userMessageId, assistantMessageId, answer, artifacts[], sources[], actions[], runId}` (synchronous; the question and the answer are filed in one transaction, so a turn that cannot store its answer stores no question) |
| POST | `/copilot/chat/stream` | `{message, conversationId?, context?}` → SSE: `status` / `token` frames as the agent works, then `done` carrying the same reply as `/copilot/chat` (both messages are stored before it closes), or `error`. This is the route the copilot page calls |
| GET | `/conversations` | list |
| POST | `/conversations` | create |
| GET / PATCH / DELETE | `/conversations/{id}` | |
| GET | `/conversations/{id}/messages` | transcript with artifacts/sources/actions |

### Dashboard, activity, search, AI usage

| Method | Path | Notes |
|---|---|---|
| GET | `/reports/dashboard` | pipeline health, counts, recommended jobs, skill gaps, resume score, recent insights |
| GET | `/activity/runs` | agent runs (`?page=&size=&agent=`) |
| GET | `/activity/runs/{id}` | run + ordered traces (AI Activity detail) |
| GET | `/ai-usage/summary` | tokens, requests, cached tokens, estimated cost |
| GET | `/search` | global ⌘K search (`?q=`, required) across jobs/companies/resumes/notes/conversations/applications — the jobs channel is hybrid-ranked, like `/jobs?sort=relevance` |
| GET | `/ai/stream/{taskId}` | SSE relay of an ai-service task |

## 3. Internal API — ai-service

Requires `X-Internal-Token`. `X-User-Id` (and optionally `X-Run-Id`) supply the
tenant context via `core.deps.Ctx`.

**Refusals.** A request the engines refuse answers with the upstream's own
vocabulary: a stable code plus the one sentence that code means --
`{"detail": {"code": "INGEST_FEED_INVALID", "message": "invalid feed xml"}}`.
The status is the one the route always answered with (400, except
`TEXT_REQUIRED`, still the 422 it was); a refusal that names the offender
carries it alongside (`"invalid": [...]`, `"errors": [...]`). The codes are
defined in `ai-service/app/core/errors.py` and pinned end to end by
`ai-service/tests/test_refusals.py`. The backend reads the sentence out of
that object and still maps every 400 to `AI_SERVICE_BAD_REQUEST` -- the code
crosses the wire now so the mapping can grow a vocabulary later.

| Method | Path | Purpose |
|---|---|---|
| POST | `/internal/agents/chat` | run a copilot turn as a background task → `{task_id, run_id}` (started by the backend's `/copilot/chat/stream`, whose reader takes its frames off `/internal/stream/{task_id}`) |
| POST | `/internal/agents/chat/sync` | blocking turn → `Outcome` (relay + E2E + eval harness) |
| GET | `/internal/agents/runs` | runs list (no backend caller: the Activity panel reads agent_runs over the shared database instead) |
| GET | `/internal/agents/runs/{run_id}` | run + traces (no backend caller: same, for one run's detail) |
| POST | `/internal/features/resume/parse` | structured resume parse + score |
| POST | `/internal/features/jd/analyze` | JD intelligence |
| POST | `/internal/features/match` | deterministic match |
| POST | `/internal/features/tailor` | tailoring + diff (no fabrication) |
| POST | `/internal/features/cover-letter` | cover letter |
| POST | `/internal/features/jd/suggestions` | improvement suggestions |
| POST | `/internal/features/growth-report` | one call for the whole growth page: readiness + gap + salary + the learning plan + the progress diff, composed by `features/growth.py` (backend `growthReport`) |
| POST | `/internal/features/insight-digest` | Epic 15.3 -- a weekly snapshot: stalled applications, live stage mix, headlines (backend `insightDigest`) |
| POST | `/internal/features/health-report` | Epic 16.1 -- agent health, cost and regression verdict over a window (backend `healthReport`) |
| POST | `/internal/features/follow-ups` | Epic 11.3 -- the contacts that have gone cold, ranked, each with a draft (backend `followUps`) |
| POST | `/internal/features/parse-feed` | Epic 14.2 -- a feed parsed into raw postings: RSS 2.0 / Atom XML or a board-API JSON payload, the shape detected from the text (backend `parseFeed`) |
| POST | `/internal/features/dedupe-jobs` | Epic 14.3 -- the same posting seen from several sources, collapsed to one survivor (backend `dedupeJobs`) |
| POST | `/internal/features/freshness-sweep` | Epic 14.3 -- the corpus split into fresh, stale (re-check) and expired (close) (backend `freshnessSweep`) |
| POST | `/internal/features/plan-ingest` | Epic 14.3 -- one plan for a sweep: create / update / close, with the diff (backend `planIngest`). 19.8: optional `company` names the board every row without a company of its own belongs to |
| POST | `/internal/features/export-bundle` | Epic 13.1 -- the export bundle: every section, with a content hash over the data (backend `exportBundle`) |
| POST | `/internal/features/import-plan` | Epic 13.2 -- the idempotent write plan for a bundle, per-item content hashes and all (backend `importPlan`); the reader's own six sections are read here when the request carries none |
| POST | `/internal/features/redact-bundle` | Epic 13.3 -- the bundle with sections dropped and the hash recomputed over what is left (backend `redactBundle`) |
| POST | `/internal/features/render-bundle` | Epic 13.1 -- the human-readable half: a print-ready document of the bundle, HTML or PDF (backend `renderBundle`) |
| POST | `/internal/features/render-resume` | Epic 19.5 -- one resume version as a print-ready document: the structured body in the export's print chrome and section words, or the version's plaintext when it was never parsed (backend `renderResume`) |
| POST | `/internal/memories/import` | Epic 13.2 -- restore a bundle's long-term memories, upserted on the same (kind, key) the extraction path uses, so the restore is idempotent (backend `importMemories`) |
| POST | `/internal/features/salary-benchmark` | Epic 12.1 -- percentiles by role, seniority band and location (backend `salaryBenchmark`) |
| POST | `/internal/features/negotiate` | Epic 12.2 -- an offer against the benchmark, with leverage and talking points (backend `negotiate`) |
| POST | `/internal/features/compare-offers` | Epic 12.3 (with 12.5) -- several offers ranked by total comp, equity annualised (backend `compareOffers`) |
| POST | `/internal/features/counter-offer` | Epic 12.4 -- the deterministic anchor and reasons a counter-offer is built from (backend `counterOffer`) |
| POST | `/internal/features/gap-analysis` | Epic 10.1 -- the distance between the profile and the target role (backend `gapAnalysis`) |
| POST | `/internal/features/readiness` | Epic 10.7 -- target-role readiness, as one verdict (backend `readiness`) |
| POST | `/internal/features/learning-plan` | Epic 10.5 -- the plan that closes the gaps readiness named (backend `learningPlan`) |
| POST | `/internal/features/skill-demand` | Epic 10.9 -- which skills the market asks for, counted from the corpus (backend `skillDemand`) |
| POST | `/internal/features/learning-priority` | Epic 10.12 -- gaps ranked by importance and by market pull (backend `learningPriority`) |
| POST | `/internal/features/progression` | Epic 10.11 -- stepping-stone roles toward a dream role, each with the bridge score that ranks it (backend `progression`) |
| POST | `/internal/features/interview-prep` | Epic 10.13 -- the pre-interview checklist: study the gaps, rehearse the strengths (backend `interviewPrep`) |
| POST | `/internal/features/story-bank` | Epic 6.5 -- STAR stories drawn from the profile's own evidence (backend `storyBank`) |
| POST | `/internal/features/role-suggestions` | Epic 10.10 -- the target roles this profile could plausibly aim at (backend `roleSuggestions`) |
| POST | `/internal/features/progress` | Epic 10.6 -- skill progress tracked between two snapshots (backend `progress`) |
| POST | `/internal/features/outreach` | Epic 11.2 -- a referral or networking message, built only from saved evidence (backend `outreach`) |
| POST | `/internal/features/pipeline-funnel` | Epic 15.1 -- how many applications reached each stage, and where they stall (backend `pipelineFunnel`) |
| POST | `/internal/features/response-rate` | Epic 15.2 -- reply / interview / offer rates and per-stage durations (backend `responseRate`) |
| POST | `/internal/features/company-brief` | Epic 4.8 -- what the corpus says about one company (backend `companyBrief`) |
| GET | `/internal/memories` | the copilot's own memories, `?kinds` filtered, for the settings panel (backend `listMemories`) |
| PATCH | `/internal/memories/{memory_id}` | correct one memory's text, or lower the weight it is quoted at (backend `patchMemory`) |
| DELETE | `/internal/memories/{memory_id}` | forget one memory; the row is gone, not hidden (backend `deleteMemory`) |
| POST | `/internal/ingest/document/{doc_id}` | ingest a stored document |
| GET | `/internal/ingest/documents/{doc_id}/text` | extracted document text (used by backend resume parsing) |
| POST | `/internal/ingest/text` | ingest inline text |
| POST | `/internal/rag/embeddings` | `{text}` → `{embedding}`: one query vector for the backend's hybrid `/jobs` ranking; an empty list means no provider could answer, so the caller ranks keyword-only |
| POST | `/internal/rag/retrieve` | hybrid retrieval + citations (no backend caller: retrieval happens in-process, agent tools -> pipeline.retrieve) |
| POST | `/internal/rag/answer` | retrieval + grounded answer (no backend caller: same, for the grounded-answer variant) |
| POST | `/internal/rag/chunks` | chunk listing / inspection (no backend caller: kept for operators) |
| POST | `/internal/interview/opening` | first question |
| POST | `/internal/interview/answer` | evaluate + follow up |
| POST | `/internal/interview/finalize` | final report |
| GET | `/internal/voice/status` | the deployment's speech provider and its two capabilities; no provider answers an empty name and false flags rather than failing |
| POST | `/internal/voice/transcribe` | `{audio, mime, locale?}` — base64 audio → `{text, provider}`; refusals: `VOICE_AUDIO_INVALID`, `VOICE_AUDIO_TOO_LARGE`, `VOICE_NOT_CONFIGURED` (503), `VOICE_UPSTREAM_FAILED` (502) |
| POST | `/internal/voice/speak` | `{text, locale?}` → `{audio, mime, provider}` — base64 of one spoken line; the runner plays it, and falls back to the browser's own voice when this deployment has no provider |
| GET | `/internal/tasks/{task_id}` | task state (no backend caller: the app follows /internal/stream/{taskId} instead) |
| GET | `/internal/tasks/{task_id}/stream` | task SSE (canonical) (no backend caller: a second stream spelling, unused by the relay) |
| GET | `/internal/stream/{task_id}` | SSE alias the backend relay proxies as `/api/v1/ai/stream/{taskId}` |
| GET | `/health` | liveness + provider probe (no auth) |

### 3.1 Backend internal surface — consumed by ai-service

The same `X-Internal-Token` guards the backend's own service-to-service routes
(`InternalApiFilter` watches the `/api/internal` prefix and compares the token in constant
time). They are not reachable with a user JWT: no `Authorization` header is consulted on
them, so the token *is* the credential.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/internal/files/{fileKey}` | a stored upload's bytes, for ai-service ingestion — the key must match `{userId}/(resumes\|knowledge)/{id}.{pdf\|docx\|txt}` and belong to a `documents` row, otherwise 400 (malformed key) or 404 (no document owns it) |
| POST | `/api/internal/nightly-reports` | the scheduled workflow's own record of the night — `{startedAt, finishedAt, status, source, commitSha, runUrl, summary}` — written once per run and never updated; status is passed or failed (`NIGHTLY_REPORT_STATUS_INVALID` otherwise), a finish before the start is `NIGHTLY_REPORT_CLOCK_REVERSED`, and an oversized summary is `NIGHTLY_REPORT_SUMMARY_TOO_LARGE`. The job posts its step outcomes under `summary.steps`; the history answers them back as a typed `steps` list, because the map is the storage shape and the list is the wire shape. The caller is the nightly job (`app.ops.nightly_report`), not the ai-service; the history is read back over `GET /api/v1/monitoring/nightly-reports` |


### 3.2 Forward internal surface -- registered, and not called by the backend

Every route here answers under the same `X-Internal-Token` and the same `Ctx`, and every one
has an engine in `app/features/` and a contract row in
`ai-service/tests/test_forward_features_contract.py`. What none of them has yet is a caller in
`HttpAiServiceClient`: the product reaches the same computation through the backend's own
`/api/v1` routes, or has not built the screen yet. The split is measured, not remembered --
`tests/test_api_doc_contract.py` derives this table from the live route table minus the
requests the backend is seen building, so an engine that gains a backend caller has to move up
into section 3, and a new route with no row anywhere reddens the completeness gate.
Seven routes that no backend caller builds do sit in section 3, and each says so in its own
Purpose cell; the gate that partitions the unreached surface charges those seven with
carrying the marker and every other row with not carrying it.

Every engine now has a backend caller, so this table is empty — a new engine that ships
ahead of its bridge joins it again, and the split is re-measured.

| Method | Path | Purpose |
|---|---|---|

## 4. Worked examples

```bash
B=http://127.0.0.1:8080/api/v1

# register and capture the access token
TOKEN=$(curl -s -X POST $B/auth/register -H 'Content-Type: application/json' \
  -d '{"email":"a@example.com","password":"Str0ngPassphrase!23","displayName":"A"}' \
  | python -c 'import sys,json;print(json.load(sys.stdin)["data"]["tokens"]["accessToken"])')

# upload and parse a resume -- the upload answers the ids the next two calls need, and it
# binds one part: `file`. Anything else you send alongside it is ignored, not rejected.
RID=$(curl -s -X POST $B/resumes/upload -H "Authorization: Bearer $TOKEN" \
  -F file=@resume.pdf \
  | python -c 'import sys,json;print(json.load(sys.stdin)["data"]["resumeId"])')
curl -s -X POST $B/resumes/$RID/parse -H "Authorization: Bearer $TOKEN"

# search jobs, then score one against the resume
JID=$(curl -s "$B/jobs?q=Agent&remote=hybrid&sort=match" -H "Authorization: Bearer $TOKEN" \
  | python -c 'import sys,json;print(json.load(sys.stdin)["data"]["items"][0]["id"])')
curl -s -X POST $B/jobs/$JID/match -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{}'

# ask the copilot, then inspect what the agent actually did
curl -s -X POST $B/copilot/chat -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"message":"帮我找适合我的 AI Agent 岗位"}'
curl -s "$B/activity/runs?page=0&size=5" -H "Authorization: Bearer $TOKEN"
```

## 5. OpenAPI

Spring Boot exposes generated OpenAPI through springdoc (`/v3/api-docs`,
`/swagger-ui.html`) and FastAPI serves its own at `/docs`. This document is the
hand-written overview that explains the *why*; the generated specs are the
mechanical field-level reference.
