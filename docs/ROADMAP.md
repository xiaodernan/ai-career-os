# ROADMAP — AI Career OS (长期演进计划)

This file is the standing backlog toward the **final goal**: a complete,
production-grade *personal job-search operating system* — evidence-bound AI over
the full career loop, plus growth, outreach, and offer intelligence, with data
portability, analytics, and hardened delivery. It is the single source of truth
for "what to build next" across sessions; pick the top un-done task and execute.

> The loop the product runs today (Epic 0–9, shipped): resume → knowledge base →
> job discovery → JD intelligence → evidence-matched scoring → tailored materials →
> adaptive mock interviews → application tracking → observability. Every AI claim is
> traced to the user's own material. The forward epics extend *that* loop.

## Status
- **Epic 0–9: DONE.** Foundation, auth, resume intelligence, RAG, job discovery,
  materials, interview coach, copilot/agents, tracker/dashboard, quality & delivery.
  Verified end-to-end: 24/24 Playwright golden journey, both eval harnesses, RAG
  eval 15/15 on the seeded corpus.
- **Epics 10/11/12 (ai-service halves): DONE (2026-10-11 → 13).** Twelve internal,
  evidence-bound engines shipped in ai-service, all unit-tested offline:
  gap analysis (10.1), target-role readiness (10.7), learning plan (10.5),
  skill-progress tracking (10.6), market skill demand (10.9), STAR story bank (6.5),
  outreach drafting (11.2), salary benchmark (12.1), negotiation coach (12.2),
  offer comparison (12.3), counter-offer drafting (12.4), equity annualization (12.5)
  — plus an aggregate
  `POST /internal/features/growth-report` (10.8) that composes the growth page in one
  call, the **progression planner** (10.11, stepping-stone roles toward a dream
  role), the **learning-priority** ranker (10.12, learn the most-demanded gap
  first), and the **interview-prep** checklist (10.13, study the gaps, rehearse the
  strength stories). Seventeen internal engines then; **Epic 13 (portability) and
  Epic 15 (analytics) add more** — export/serialize/render/redact + import-plan, and
  pipeline funnel / response-rate / insight-digest — all unit-tested offline and pinned by
  `tests/test_forward_features_contract.py` where they are routed.
  **The growth loop is now bridged end-to-end (2026-10-14)** — the 10.2 aggregate
  (`/api/v1/growth-report`), the 10.3 `/growth` panel, and 10.4 plan persistence all ship.
  The granular growth engines (gap, salary, readiness, learning, progress as their own
  routes) and the 12.x bridges are still unwired.
  **Every engine is bridged (2026-10-20).** The forward surface that shipped
  ahead of its bridges is empty: the 10.x granular engines, 11.2/11.3, the 12.x
  salary & offer quartet, the 13.x portability trio, the 14.x ingestion quartet,
  the 15.x analytics trio and the 16.1 health report all have a backend route
  now, and each has a frontend surface where the answer is worth a screen of
  its own — `/growth` (the report and the per-engine panel), `/networking` and
  the dashboard's follow-up tile, `/offers`, `/data`, `/ingestion`, `/analysis`
  and `/monitoring`. The ai-service's 3.2 table in `docs/API.md` is empty, and
  the gate that measures the split re-measures it rather than remembering it.
  The E2E suite grew to match: every signed-in route is walked for its heading,
  and the golden journey now answers the growth report, the gap engine, the
  salary benchmark, the digest, the funnel, the rates and the export bundle
  through the real API.

  **The bridges are tested and the product is finished (2026-10-20, later).**
  Every new route carries a controller test (24 of them, from 402 to 426), every
  new client hook a wire-shape test, and the new surfaces a normalizer test —
  549 frontend tests and 426 backend ones, all green.
  The product got the rest of what a shipped app needs: a chart component with
  no library behind it (`components/common/bar-chart.tsx` — the scale is the
  caller's, the value is always printed), the i18n table extended to the new
  pages with a gate that holds the two languages to the same key set, and the
  landing page promoted to the public front door.

  **The round closed on the gates (2026-10-20, last pass).** Six of the contract
  gates read the code rather than trust it, and the bridges moved what they
  read: the record census, the toast floor, the skipped-test roster, the
  documentation ledger's line numbers, and the rate-limit knob's reader list.
  Each is now pinned to the measured population, with a comment saying what
  moved — the gates are the product's own account of itself, so leaving them
  stale would be a lie in the one place the reader can check.

- **The portability gap is closed (2026-10-22).** The export bundle's `knowledge`
  section read the `documents` table — the files the reader uploaded — while the
  notes they *typed* lived in `user_notes` and in no section of the bundle at all.
  So a reader who kept their salary research in a note and then exported their
  data did not get that note back: "your data" meant "the data in the tables the
  export reads". Since **1.2.0** the bundle carries the notes and the contacts
  too — the reader's own words and the people they know — and the browser can
  redact them like any other section. The schema version is read as *numbers*
  now, so a 1.1.0 backup is still a valid bundle and a 1.1.5 one is held to the
  1.1.0 sections rather than to the newest.
- **And the restore stopped writing over somebody else's rows.** A bundle's ids
  are the source's, and the restore kept them so the links inside the bundle
  still pointed where they did — but an id that belongs to *another account's*
  row was written into that row. So restoring a colleague's export changed the
  colleague's data (a note they had edited since the export went back to the
  exported text) and gave the caller nothing of their own, while the answer
  said "created". The id is now kept only when it is free and minted when it is
  not: the restore still lands the rows, and it no longer lands them on top of
  somebody else's.
- **An unchanged row is not written (2026-10-28).** The "Your data" panel
  promises that unchanged rows are skipped, and the plan answered `update` for
  every row whose id it already knew — so a re-import of the bundle the
  workspace itself exported counted "2 to update" and the apply wrote both rows
  again. The plan now emits a fourth op, `skip`, for a known id whose content
  did not change; the apply writes nothing for it and counts it `unchanged`.
  Deciding that required the `existing` half to be the *same serialization* as
  the bundle (it now reads through `ExportService.backendSections`, and the
  profile row is spelled the way the engine reads it) and the comparison to
  cover the fields the apply writes rather than the stamps the database sets —
  otherwise the first apply bumps `updated_at` and every row is changed
  forever. The operator's `restore_plan` dry run reports the fourth count too.
  The open thread above is unchanged: the current state still does not cover
  the resumes, the knowledge base, the job descriptions, the interviews and the
  memories, so a restore still cannot promise a delete for them.

- **The bundle carries what the restore writes (2026-10-28).** The restore
  writes a `jsonb` column through a map, and the bundle carried those columns
  as the text asyncpg returns: a restored posting came back with its raw text
  and none of the analyst's reading, a session with no config, every answer
  with no evaluation. The export decodes the columns the schema calls `jsonb`
  (the backend still parses a string, so bundles written before this restore
  too), and the session's report — `interview_evaluations`, which the export
  never read — now travels on the session as `evaluation`, the three fields
  the restore writes and the anonymized export blanks. The joined company's
  name no longer shadows the session's own `company_name` column.
  The same visit found the plan preview answering counts for a different
  question than the apply: the browser's plan sends no `existing`, so every
  row was a `create`. That is fixed with the thread below, which makes the
  preview and the apply read the same current state.

- **The errors a reader sees were the server's own English (measured 2026-10-22;
  the codes that mean one thing are bilingual now, the ones that mean several
  are the queue).** A failed
  write answers with a toast, and the toast says what the server said — in
  English. The obvious fix is to translate by the **code**, because the code is
  the contract ("never rename an emitted code") and the code is what crosses the
  wire. Measured: the codes are **coarser than the messages**. `TOKEN_INVALID`
  answers with five different sentences, `INTERNAL_ERROR` with five,
  `NOT_FOUND` with four, `VALIDATION_FAILED` with three,
  `VERSION_NOT_FOUND` with three. One sentence per code would tell a reader
  whose interview has not started that the interview is already under way
  — so the fix is not a translation, it is a *finer vocabulary*: roughly
  eight more codes (one per distinct wording), about seventy sentences in
  each language, and the throw sites changed to name them.

  **The first split is done.** The resume's not-found code answered with six
  sentences -- no resume at all, no parsed version, nothing to tailor, the
  original file gone, the file never ingested, and the resume not found --
  and one sentence for it would have been wrong about five of the six. They
  are six codes now (`RESUME_NOT_AVAILABLE`, `RESUME_NOT_PARSED`,
  `RESUME_NOT_TAILABLE`, `RESUME_FILE_MISSING`, `RESUME_NOT_INGESTED`,
  `RESUME_NOT_FOUND`), each with its own sentence in both languages, and the
  statuses did not move: the *code* is the contract and the *status* is what
  the client's error path reads, so the split is free where it is needed.

  **And the request bucket is gone.** `BAD_REQUEST` answered with twelve
  different sentences -- the interview's four situations, the upload that
  could not be read, the empty file, the file key's two, the bundle's two,
  the resume's text, the method the reader called, and the assistant's own
  refusal -- and one sentence for it would have been wrong about most of
  them. They are thirteen codes now (`INTERVIEW_ALREADY_STARTED`,
  `INTERVIEW_NOT_STARTED`, `INTERVIEW_NOTHING_TO_FINALIZE`,
  `INTERVIEW_NO_QUESTION`, `UPLOAD_UNREADABLE`, `FILE_EMPTY`,
  `FILE_KEY_MALFORMED`, `FILE_KEY_INVALID`, `BUNDLE_NO_SECTION`,
  `BUNDLE_NOT_PLANNABLE`, `RESUME_TEXT_NOT_READY`, `METHOD_NOT_ALLOWED`,
  `AI_SERVICE_BAD_REQUEST`), each with its own sentence in both languages --
  and the bucket itself is gone, because a name that means nothing is not a
  contract. Twelve of the thirteen are translated; the assistant's own
  refusal keeps the assistant's words, because its reason varies with the
  request and a sentence that covered half of them would be wrong about the
  rest.

  **And the session codes are one meaning each.** `TOKEN_INVALID` answered
  with five sentences -- the access token is bad, the token is not the kind
  we minted, the token's subject is broken, the refresh token is unknown,
  the account behind the token is gone -- and `RESET_TOKEN_INVALID` with two.
  The reader cannot act on most of that difference: a token that is unknown
  and a token that was spent both say the same thing (the link is no good,
  ask for another), and a token that is not one of ours is one thing too
  (the session cannot be read). So the two codes are five: `TOKEN_INVALID`
  keeps the two the reader can act on, `TOKEN_MALFORMED` takes the two that
  mean the token is not ours, `TOKEN_OWNER_NOT_FOUND` says the account is
  gone, `RESET_TOKEN_INVALID` keeps the link that is unknown, spent or
  expired, and `RESET_TOKEN_OWNER_NOT_FOUND` says the account behind the
  link is gone. Five sentences, in both languages -- and the two that are one
  thing to the reader are held there by the same-meaning list, which is a
  person's judgement the gate keeps honest.

  **And the not-found code is five.** `NOT_FOUND` answered with four
  sentences -- the route is not mapped, the assistant's own record is gone,
  the account is gone, the profile is gone, the contact is gone -- and the
  reader could not tell them apart: every one of them arrives as a 404, and
  the browser answers a 404 with "your frontend and the backend are
  different versions", which is false whenever the route is served and the
  record is not. They are five codes now (`NOT_FOUND` for the route that is
  not served, `AI_SERVICE_NOT_FOUND`, `USER_NOT_FOUND`, `PROFILE_NOT_FOUND`,
  `CONTACT_NOT_FOUND`), and `DOCUMENT_NOT_FOUND` is two as well -- a
  document that is gone, and a file key no document owns. The code is what
  tells the reader which of them happened, and the browser's rule is next:
  only the route that is not served may be reported as a version mismatch.

  **And the storage errors are split.** `INTERNAL_ERROR` answered with five
  sentences -- the generic fallback, and the four MinIO operations (write,
  presign, delete, read) -- and one sentence for it would have been wrong
  about four of them. They are five codes now (`INTERNAL_ERROR` for the
  fallback, `STORAGE_WRITE_FAILED`, `STORAGE_PRESIGN_FAILED`,
  `STORAGE_DELETE_FAILED`, `STORAGE_READ_FAILED`), each with its own
  sentence in both languages. The statuses did not move: all five are still
  the 500 they were.

  **And the validation bucket is four.** `VALIDATION_FAILED` answered with
  three different sentences -- the request failed its own validation, a job
  needs a company (by id or by name), and a tailored version needs the
  structured body it was generated with -- plus a fourth that varies with the
  request (the knowledge kind that was not recognized). One sentence for it
  would have been wrong about two of the three, and the varying one cannot be
  measured at all, so it can never be held to a sentence. They are four codes
  now: `VALIDATION_FAILED` for the three validation channels that share one
  sentence, `VALIDATION_FIELD_REQUIRED` for the missing company,
  `VALIDATION_STRUCTURE_INVALID` for the tailored body, and
  `VALIDATION_KIND_UNKNOWN` for the kind -- each with its own sentence in both
  languages.

  **And the version code is three.** `VERSION_NOT_FOUND` answered with three
  different sentences -- the resume has no version to parse yet, the version
  id does not exist, and the version belongs to another resume -- and one
  sentence for it would have been wrong about two of the three: a reader whose
  version was never there and a reader whose version belongs to somebody else
  need different answers. They are three codes now (`VERSION_NOT_FOUND` for
  the version that is not there, `VERSION_NOT_OWNED` for the one that belongs
  to another resume, `RESUME_VERSION_MISSING` for the resume that has no
  version yet), each with its own sentence in both languages. The statuses
  did not move: all three are still the 404 they were.

  **And the assistant's own errors are two.** `AI_SERVICE_ERROR` answered
  with two different sentences -- the upstream did not answer (a refused
  connection, a timeout, or a status this service does not read) and the
  upstream answered with nothing -- and one sentence for it would have been
  wrong about one of the two. They are two codes now
  (`AI_SERVICE_UNAVAILABLE`, `AI_SERVICE_EMPTY_RESPONSE`), each with its own
  sentence in both languages, and the statuses did not move: both are still
  the 502 they were.

  **And the upstream's own answers are this service's own codes.** The
  assistant's service answers 404, 400, 409 and 5xx, and the boundary
  flattened every status that was not 404 or 400 into one 502. So a document
  that was still being read was reported as the assistant failing -- and the
  code this service already had for it ("that resume's text is not available
  yet") was *unreachable*, because the upstream's answer short-circuited the
  line that raises it. A 409 is a code of its own now
  (`AI_SERVICE_CONFLICT`), and the resume path turns it into the resume's
  own code, which is the sentence the reader should read.

  **And the browser's 404 rule reads the code.** The backend answers a 404 in
  two different ways -- the route is not served, or the route is served and the
  record it reads is gone -- and both arrive as a 404, so a rule that reads the
  status alone tells a reader whose job was deleted that their frontend and
  their backend are different versions, and offers a "Check again" button that
  cannot help. The code is what tells the two apart, so the boundary's rule
  reads the code now, and the failure describer shows the code's own sentence
  *before* it falls back to the version sentence. A deleted record reads as
  "that job is no longer here", in the reader's language, and not as a version
  mismatch.

  **And the second shell reads it too.** `module-view.tsx` -- the list shell
  five screens spend -- decided the same thing from the status, so a 404
  landed on the screen's own "nothing here yet" hint: a list that is not
  empty, and a route that is not served, both reported as an empty list,
  with an action that sends the reader to the assistant to look for work
  that is there. It reads the code now. A route that is not served gets the
  not-live state (the version sentence and a "check again" button), and a
  record that is gone gets the error surface, which shows the code's own
  sentence.

  **And a code travels by three roads.** A throw (`new ApiException`), the
  envelope builder (`ApiError.of`), and the framework's own edges — the 401,
  the 403, the 404, the 429. A measurement that read only the throws called
  `RATE_LIMITED` and `FORBIDDEN` silent, and "silent" is not the same as "one
  meaning". The gate reads all three now, so the split it measures is the
  split the reader meets. The exception handler's own helper is a fourth road:
  it names the code and the sentence at the call site and hands them to the
  builder as variables, so a measurement that read only the builder's call
  called the three validation channels silent — and the validation channels
  are exactly the codes that answer for a reader's own request.

  **Done so far.** The browser's language is now readable *outside* a render
  (`lib/i18n/locale-context.tsx`'s `translate`), which is what a toast needs — it
  is raised from an event handler, long after the render that knew the language.
  The failure helper shows the table's sentence rather than the English literal
  the code was raised with.

  **And the services' codes are classified now.** Every code the services can
  send is either **translated** (the browser's table answers it, in both
  languages) or **named as a gap** — and the gap list is the queue for the finer
  vocabulary.
  The gate
  *measures* the split rather than remembering it: a code that is translated
  must carry one meaning (read off the throw sites), a code that is named as a
  gap must be one for a stated reason, and a code nobody classified fails the
  gate. So the sixty-seven codes that mean one thing are bilingual today, and
  the one that is left keeps the server's own words for a reason that is now
  written down rather than implied.

  **And there are two reasons a code can be a gap.** A code that means
  several things is waiting to be split into codes — that is a queue of work,
  and it is empty. A code whose wording cannot be read at all is waiting for
  a vocabulary that does not exist yet: `AI_SERVICE_BAD_REQUEST` carries the
  upstream's own sentence, and that sentence varies with the request, so a
  sentence of its own would be wrong about most of the requests it answers.
  The gate reads the reason out of the source and the list has to agree, so a
  gap cannot rot into an excuse — and so the last one is a decision, not a
  leftover.
- **And the ai-service learned to answer with codes (2026-10-23).** Its engines
  refused with bare `ValueError`s, so the only thing that crossed the wire was a
  sentence and the boundary had nothing stable to map. The refusals are typed
  now (`ai-service/app/core/errors.py`): a stable code, the one sentence that
  code means, and the status the route always answered with — the sweep plan's
  both-or-neither, the unreadable feed, the invalid bundle, the unknown section,
  the blank memory content and the missing ingest text. They answer as
  `{"detail": {"code", "message"}}`, the boundary reads the sentence out of the
  object (and the legacy string shape still crosses), and the backend keeps its
  own vocabulary for now — the code is what travels, so the mapping can grow one
  later without another visit to every throw site.
  `tests/test_refusals.py` drives the real routes and pins each code, status and
  extra. A committed red came with it: the SSE gate's reader expected `sse()`'s
  return on the line after its `def`, and the frame hardening had put two guards
  above it — the gate reads the function's body now, which is the claim it
  always meant to make.
- **The export's readable half had one language (closed 2026-10-22).** 13.1's
  *human-readable* export — the print-ready document — was written in Chinese
  and had no other language, so an English reader's printable document was a
  Chinese document. Measured: about 35 sentences across `export.py`'s
  `to_markdown` and `export_render.py`, so the work was the sentences plus a
  way to say which language a bundle should be rendered in. The bundle already
  carries the reader's id and the `anonymized` marker, so the locale could
  travel the same way; nothing carried it yet. An English reader's "printable
  document" was a Chinese document, which is the same class of defect as the
  rest of the i18n holes: a word the reader cannot change.
  **Both halves are done** — the words live in one table (`export_words.py`), in
  every language the readable half ships in, and the caller says which one it
  wants. The Markdown view was the second half, and it had a second defect:
  it left out four sections the bundle carries (the pipeline, the growth runs,
  the notes and the people the reader knows), so the quick look at a bundle
  stopped at the reading list.
  **And the Markdown has a surface (2026-10-28).** It was a library function
  nothing called — the render route served the HTML and the PDF, the bridge
  had no field for it, and the export page had no Markdown affordance — so
  the *operator's quick look* existed only for someone already inside Python.
  `format: "markdown"` is a format of the route now, the bridge hands it
  through unchanged, and the page downloads `career-os-export.md`. The
  route-level test calls the route the way the bridge calls it, in both
  languages, and the wire test pins the format the browser sends.
- **The restore can retire what it can name (closed 2026-10-28).** The plan
  tells a delete from a create by comparing the bundle with the caller's
  current state, and the current state covered five of the ten sections — so a
  restore could not remove a row the bundle no longer carried in the rest, and
  the plan could never promise a delete it could keep.
  **The current state grew to cover them, in the half that owns each.** The
  backend defaults `existing` to its own workspace when the browser sends
  none, and the engine's route reads the six sections it owns and overlays
  only the caller's gaps (the caller's profile wins) — so a preview and an
  apply compare the same two documents, which is the only way the preview's
  counts can be true.
  **And the remapping question is answered by splitting the sections in
  two.** The sections the restore keeps ids for — the profile, the
  applications, the growth runs, the notes, the contacts, the postings, the
  interviews — are matched by id, so a row the bundle omits is a row the
  reader took out of the document they asked to restore: it is retired, and
  an interview whole (the transcript and the report cascade with the
  session). The sections the restore re-mints — the resumes, the documents,
  the memories — have no id at the target to match, so they are matched by
  content (a resume by title and text, a document by title and excerpt, a
  memory by its kind and key) **and never delete**: the absence of a row
  whose id is not shared is not a statement the restore can keep, and a
  redacted bundle must not destroy the target's own rows on the strength of
  a section the sharer withheld. A row the apply could not write is not
  planned, and its existing counterpart is not retired on its absence.
  The comparison now covers exactly what the apply writes — ids, ownership
  and the database's stamps stripped at every level, the interview's child
  bookkeeping, the posting's job link and a memory's `last_used_at` with
  them, JSON text parsed, numbers normalized — so a row that is already the
  same is a `skip` rather than a write that would recur forever.
  Pinned by `tests/test_import_plan.py` (the two kinds, the multiset
  matching, the hash stability), `tests/test_export_redact.py` (a withheld
  section deletes nothing; a genuinely empty one still does), the
  controller's apply tests, and the route-level preview test.
## Epic 10 — Growth Intelligence
- [x] **10.1** Gap & growth analysis engine (evidence-bound coverage verdict).
  (Backend bridge: `POST /api/v1/growth/gap-analysis`; the `/growth` page's
  engine panel runs it on its own.)
- [x] **10.2** Backend bridge: `HttpAiServiceClient.growthReport` + `GrowthController`
  (`/api/v1/growth-report`, the 10.8 aggregate; granular endpoints after). `docs/API.md`
  extended, the route rate-limited as AI-cost, controller pinned by `GrowthControllerTest`.
- [x] **10.3** Frontend page/panel: target-role input, readiness verdict, coverage
  bars (covered / partial / gap), learning plan, salary band, progress delta.
  (`/growth`, rendered from the 10.2 aggregate; the panel hands its own gap block
  back as `previous` until 10.4 persists the plan server-side).
- [x] **10.4** Persist a `growth_plan` per (user, target_role) so repeat runs diff.
  (`V9__growth_plans` + `GrowthService`: every run stored, the stored gap block fed
  back as the next run's `previous` unless the caller brought one; a failed store
  degrades the next diff, never the answer.)
- [x] **10.5** Learning plan: gaps → phased study items (foundation → core → applied)
  with category-aware resource hints. (`features/learning.py`)
- [x] **10.6** Skill-progress tracking: diff two gap reports → closed / improved /
  regressed / opened + coverage delta. (`features/progress.py`)
- [x] **10.7** Target-role readiness synthesis: skills (10.1) + market (12.1) → one
  verdict, a must-gap capping a "ready". (`features/readiness.py`)
- [x] **10.8** Aggregate `growth-report` endpoint (readiness + gap + salary + learning
  plan + progress in one call) — the intended bridge target.
- [x] **10.9** Market skill demand: which skills a role family's postings ask for, and
  how often — the market-centric half of the gap view. (`features/demand.py`)
- [x] **10.11** Career progression planner: given an aspirational role, rank
  stepping-stone role families that are *reachable today* (current coverage) **and**
  build the dream role's missing skills. Composes gap-analysis + role-suggestions +
  demand; deterministic bridge score. (`features/progression.py`)
- [x] **10.12** Learning priority: enrich each gap with its market demand (10.9) over
  the role family and rank by importance × market pull, so the candidate learns the
  most-asked-for missing skill first. Composes gap-analysis + demand. (`features/prioritize.py`)
- [x] **10.13** Interview prep plan: the pre-interview checklist -- weak areas to study
  (gaps, by importance), strength stories to rehearse (covered skills mapped to the
  candidate's own STAR stories), and likely topics (responsibilities + gap-address
  lines). Complements the adaptive coach (interview.py). Composes gap-analysis + stories.

## Epic 11 — Outreach & Networking
- [x] **11.1** Contacts registry (name, role, company, relation, last touch).
  (`/api/v1/contacts` CRUD, `V10__contacts`, user-scoped; the outreach generator's
  `{name, role, company}` consumer shape came first and this registry feeds it.)
- [x] **11.2** Referral / networking message generator (evidence-bound; validator
  strips any skill the profile does not support). (`features/outreach.py`)
- [x] **11.3** Follow-up reminders + cadence; surface stale contacts on dashboard.
  The engine and its agent-facing half shipped first: `features/reminders.py` ranks a
  contact against its own relation's cadence (bucket before days, so a contact past due
  outranks a merely-old one) and the `get_follow_ups` tool hands that list to the agent.
  Both now read through one pair of definers -- `domain.list_contacts_for_follow_ups`
  (the capped, oldest-touch-first read) and `reminders.follow_ups_for` (rank, then draft)
  -- and that pair is routed as `POST /internal/features/follow-ups`, so the tile cannot
  disagree with the copilot. The dashboard tile now reads the same rows.
- [x] **11.4** Networking subagent wired into the orchestrator's whitelist.
  (`SUBAGENT_TOOLS["networking"]` = `search_contacts`, `get_follow_ups`, `draft_outreach`,
  `log_contact_touch`, `get_user_profile` -- the contact reads plus one touch write, and
  no job or application tool, which is the boundary AGENTS.md §2 documents and
  `tests/test_networking_tools.py` enforces.)

## Epic 12 — Salary & Offer Intelligence
- [x] **12.1** Salary benchmarking against the seeded corpus (percentiles by role /
  seniority band / location) — deterministic, no external data required.
  (`features/salary.py`. Backend bridge: `POST /api/v1/offers/salary-benchmark`;
  frontend: the `/offers` page.)
- [x] **12.2** Negotiation coaching: offer vs benchmark → leverage + talking points.
  (`features/negotiation.py`. Backend bridge: `POST /api/v1/offers/negotiate`.)
- [x] **12.3** Offer comparison (multiple offers, cash-only ranking). (`features/offers.py`.
  Backend bridge: `POST /api/v1/offers/compare`.)
- [x] **12.4** Counter-offer drafting (deterministic anchor + reasons, model phrases).
  (`features/counter_offer.py`. Backend bridge: `POST /api/v1/offers/counter-offer`.)
- [x] **12.5** Equity annualization (intrinsic value over the vest), folded into offer
  comparison so ranking is by total comp. (`features/equity.py`, `features/offers.py`)

## Epic 13 — Data Portability & Export
- [x] **13.1** Export bundle (resumes, knowledge, applications, interviews, growth
  plans) as JSON + a human-readable PDF. (ai-service half: `features/export.py`
  gather/serialize/validate/diff + content-hash idempotency; `features/export_render.py`
  print-ready HTML + lazy weasyprint PDF. Backend bridge: `POST /api/v1/data-portability/export`.)
- [x] **13.2** Import / re-import with idempotent upsert; local backup snapshot.
  (ai-service half: `features/import_plan.py` validates a bundle, then emits per-item
  create/update/delete ops with per-item content hashes so the backend can skip
  unchanged rows; `python -m app.ops.restore_plan backup.json [--existing current.json]`
  dry-runs that plan from a backup file with no database, so an operator can preview a
  restore or diff a backup before any write. Backend bridge: `POST /api/v1/data-portability/import-plan`
  and `POST /api/v1/data-portability/import-apply` — the second one executes the plan
  and reports what it wrote **and which sections it left alone, with the reason**. Every
  section applies: the profile, the applications, the stored growth runs, the job
  descriptions and the interviews are row writes (so the analyst does not run again and
  the interviewer does not question the user a second time), the resumes and the
  knowledge base are re-ingested (their ids belong to the ingestion pipeline, not to
  the row), and the long-term memories are upserted on the same (kind, key) the
  extraction path uses, which makes the restore idempotent.)
- [x] **13.3** Per-user data deletion (right-to-be-forgotten). (ai-service half:
  `features/export_redact.py` deep-copy section redaction + `anonymize`; recomputes the
  content hash and records `redacted_sections`. Backend bridge: `POST /api/v1/data-portability/redact`.)
  The redaction also has to leave a bundle the product can still use, which took three
  rules of its own: the counts are recomputed over what is left (they are the badges the
  reader sees and the last line of the printable document, and a stale count says their
  data is still in the file); a section the manifest records as withheld is *not* a
  missing section, so the redacted file still validates and still restores; and a
  withheld section gets no import ops at all, so "I did not share this" never reads as
  "delete yours".)

## Epic 14 — Job Ingestion Connectors
- [x] **14.1** Pluggable connector interface (RSS / board API / paste) feeding `jobs`.
  (ai-service half: `features/ingestion.py::Connector` protocol + `normalize_posting`
  mapping a raw payload onto the canonical jobs fields. The HTTP fetch + `jobs` write
  stay in the backend.)
- [x] **14.2** First real connector (e.g. RSS/Atom board) with the same hybrid index path
  as the seed import. (ai-service half: `features/ingestion.py::parse_feed` parses RSS
  2.0 / Atom XML, and `parse_json_board` parses a board-API JSON payload (top-level array
  or jobs/data/results/items/postings) -- both stdlib-only, offline, size-capped, and
  raising on bad input. `parse_any` picks between them from the text, so a reader is
  not asked to say which shape they pasted. Routed as
  `POST /internal/features/parse-feed`. Backend bridge:
  `POST /api/v1/jobs/ingest/parse`.)
- [x] **14.3** De-duplication + freshness sweep against existing `jobs`.
  (`features/ingestion.py::dedupe_postings` collapses exact-fingerprint duplicates to
  the newest / most complete survivor; `freshness_sweep` partitions into fresh / stale /
  expired / undated; `plan_ingest` composes parse/normalize/dedupe/freshness into one
  create / update / close plan. Routed as `POST /internal/features/dedupe-jobs`,
  `/freshness-sweep`, `/plan-ingest`; `python -m app.ops.ingest_plan feed.xml|feed.json`
  dry-runs that plan from a file with no database (`--existing`, `--now` for a
  reproducible diff). Backend bridge: `POST /api/v1/jobs/ingest/dedupe|freshness-sweep|plan`.)

## Epic 15 — Analytics & Insights
- [x] **15.1** Pipeline funnel: applied → OA → interview → offer, with conversion %.
  (`features/analytics.py::pipeline_funnel`, `POST /internal/features/pipeline-funnel`.
  Reached-stage semantics are cumulative; `rejected` counts as reached `applied` only,
  the honest bound of a schema that stores just the current status.)
- [x] **15.2** Response-rate and time-in-stage analytics from `applications`.
  (`features/analytics.py::response_rate`, `POST /internal/features/response-rate`.
  A rejection is a response; per-stage avg/median durations skip apps missing timestamps
  rather than inventing them.)
- [x] **15.3** Personal insight digest (weekly): strongest gaps closing, top matches,
  stalled applications. (`features/analytics.py::insight_digest`,
  `POST /internal/features/insight-digest`. Surfaces stalled apps past a window and the
  live stage mix; `growthDeltas` / `topMatches` are echoed through so the digest composes
  the growth engines instead of inventing data. Backend bridge: `GET /api/v1/analysis/insight-digest`.)

## Epic 16 — Production Hardening
- [x] **16.1** Monitoring/alerting on agent error rate, LLM cost, eval regressions.
  (ai-service half: `features/monitoring.py` -- `summarize_runs` (error rate, latency
  percentiles, cost/token totals), `cost_by`, and a generic `detect_regressions` that
  compares a metric set to a baseline with direction + severity; `health_report`
  composes them into a healthy/warn/regressed verdict and also folds an eval harness's
  current/baseline pair. Routed as `POST /internal/features/health-report`; backend
  bridge: `GET /api/v1/monitoring/health-report`.)
- [x] **16.2** Rate-limit dashboard + the residual SECURITY.md risks closed.
  (Backend: `GET /api/v1/rate-limit/status` + `RedisSlidingWindowRateLimiter.remaining`.
  Frontend: `/rate-limit` page showing the configured limits and the caller's
  remaining quota per bucket.)
- [x] **16.3** CI that runs all three suites + both eval harnesses on a schedule.
  (`.github/workflows/ci.yml`: an offline gate for all three suites plus nightly
  Docker-backed `*IT` and both eval harnesses.)

## Epic 17 — Internationalization & Accessibility
- [x] **17.1** CN/EN content parity (the product is CN-context but English content).
  (Frontend: `lib/i18n/translations.ts` + `LocaleProvider` context; the root layout
  wraps the app, the sidebar reads every label through a key, and the new
  surfaces — offers, analysis, monitoring, rate limit, data, ingestion and the
  growth engine panel — answer in the caller's language. A gate
  (`translations.test.ts`) holds the two halves of the table to the same key set
  and keeps Chinese out of the English table.)
- [x] **17.1b** The browser's copy census (the long tail of 17.1, measured).
  (Frontend: `lib/i18n/copy-scan.ts` walks the `.tsx` files under `app/`
  and `components/` (the gate pins the population, so a walk that skips a
  directory is red) and finds the copy that is still a literal — a
  copy-bearing attribute (`title`, `label`, `placeholder`, `aria-label`,
  `eyebrow`, `heading`, …), the text between two tags at any length, the
  same copy-bearing names inside an object literal (`{ label: "Technical" }`)
  or inside a JSX expression (`{cond ? "Interview-ready" : "Needs work"}`),
  and a plain quoted literal (`toast.success("Export ready.")`). A string in
  any of those is a word the reader cannot change, and it is the shape the
  fix took every time. The four shapes the scan did not read before were
  the blind spots: half the product's copy is written as an object literal,
  most of the rest is prose longer than the scan's old length bound, the
  words a card shows when one thing is true and another when it is not are
  inside an expression, and a toast message is neither of those — it is a
  string that is simply a *value*. A bar labelled "Technical" on a Chinese
  page was exactly as invisible to the gate as an attribute was.
  The census now reads **zero**: every string the scan can see is a key in
  both languages, so the gate asserts an empty offender list instead of
  pinning a list of tolerated holes, and the generator that used to
  regenerate that list is gone with it. An empty list can also mean a scan
  that stopped seeing anything, so the gate keeps its own eyes: the
  population of `.tsx` files is pinned, and a synthetic probe — a sentence
  longer than any in the product, fed through the same reader — proves the
  text-node scan still finds a long sentence after the old length bound
  that used to hide them was raised.)
  The pipeline's seven stage names live in one table (`stages.*`) read
  through `lib/pipeline.ts`'s three readers, the score dimensions live in
  one table (`dimensions.*`) read through `lib/dimensions.ts`, the
  document kinds and the ingestion stages in tables of their own
  (`lib/source-kinds.ts`, `lib/ingest-steps.ts`), the section overlines in
  one (`eyebrows.*`), and `t()` fills a `{hole}` so a sentence can be
  written in one language's word order and not another's.)
- [x] **17.1c** The page's title, in the reader's language.
  (The title is rendered into the document's head, and the head is the
  browser's first paint and the crawler's whole view — so it has to be
  right in the HTML the *server* sends. The locale therefore travels in a
  cookie as well as in `localStorage`, and the server reads it
  (`lib/i18n/metadata.ts`): twenty-four routes name themselves through
  `sectionMetadata` or `absoluteMetadata`, and the root's title template
  still gives the suffix, so a section reads "Jobs · AI Career OS" in
  English and "职位 · AI Career OS" in Chinese. A `useEffect` that writes
  `document.title` does *not* work: React's own metadata reconciliation
  resets it a moment later, because the `<title>` element is part of the
  tree it just hydrated. The end-to-end suite holds the result — the
  titles are read in both languages, and the 404 names itself in the
  reader's language too.)
- [x] **17.2** Full a11y pass (keyboard, motion-reduce, screen-reader labels).
  (Global CSS: skip link, `:focus-visible` ring, `.sr-only`, 44px touch targets,
  `prefers-contrast` and `forced-colors` media queries.)

## Epic 18 — Delivery
- [x] **18.1** Production docker build + deployment runbook (existing DEPLOYMENT.md).
  (`docker-compose.prod.yml` + `docs/DEPLOYMENT.md`; the runbook now opens with an
  ai-service **preflight gate** (`app/ops/preflight.py`, `python -m app.ops.preflight`)
  that blocks offline providers in prod, the published default `INTERNAL_API_TOKEN`, the
  dev DB password, a missing API key, and an inverted pool — pure and offline-tested,
  with a census pinning its default constants to `config.py`.)
- [x] **18.2** Public demo script + a short marketing/landing page.
  (demo script: `docs/DEMO.md` — the eight-minute golden journey, UI-first, with the API
  equivalents per step and the three offline dry-run CLIs. Frontend: `app/(marketing)/page.tsx`
  — hero, features, trust, CTA sections.)

## Epic 19 — Proactive Career OS (the next horizon)

The product today answers when asked. The OS that the README promises works
while the user sleeps: it watches the market, remembers what the user is
looking for, and says so before they ask. These tasks are the first layer of
that; each ships wired to the real API and UI, like every epic before it.

- [ ] **19.1** Saved searches: a named criterion set (role, location, remote,
  salary floor, skills) the user can keep, list and delete — the thing an alert
  is about. Backend CRUD + `V__saved_searches` + the `/jobs` surface's "save
  this search" affordance.
- [ ] **19.2** Scheduled ingestion: a nightly per-source pull that reuses
  `plan-ingest` (14.3) and writes the create/update/close plan, so a feed is
  swept without the user pasting it. The scheduler is the backend's, the plan
  is the engine's, and a failed pull is a recorded run rather than a silent
  night.
- [ ] **19.3** Notification center: an in-app inbox for the events the product
  already computes — a saved search's new high-match jobs, follow-ups due
  (11.3), stalled applications (15.3), a finished nightly, an eval regression
  (16.1). Read/unread, dismiss, deep link to the row.
- [ ] **19.4** Weekly digest delivery: the 15.3 digest delivered on a cadence
  (in-app, with an email-ready payload), so the week's signals do not require
  opening the app.
- [ ] **19.5** Tailored-resume print view: a single version rendered through
  the export renderer's print layout and locale words, reachable from the
  tailoring surface — "tailor → print/PDF" without exporting the whole bundle.
- [ ] **19.6** Voice mock interview: an STT/TTS provider seam plus record/play
  on the interview page. The scoring, difficulty ladder and depth trajectory
  stay the text interview's; only the input and output become voice.
- [ ] **19.7** Mobile/PWA: an installable shell, an offline shell page, and a
  responsive audit of the sidebar, the kanban drag and the wide tables.
- [ ] **19.8** Real board connectors: Greenhouse / Lever public board APIs
  behind the existing `Connector` protocol, with the RSS/JSON paste path kept
  as the offline fallback.
- [ ] **19.9** Delivery hardening: nightly backups plus a restore drill,
  metrics/alerts for the scheduler and the AI budget, and a runbook that says
  what a failed night looks like.

## Definition of Done (per task)
Implementation + tests + wired into the real API/UI (no placeholder endpoints) +
lint/build green + a census/contract gate updated where the population moved.

## Execution discipline
- This repo is developed **concurrently**: read the file you are about to edit
  *immediately* before editing; `git add` only the files you created/changed so you
  never commit another session's in-flight work.
- Verify by running, not by reading. Offline harness: `LLM_PROVIDER=mock
  EMBEDDING_PROVIDER=hash`. Docker-dependent suites (backend `*IT`, RAG eval, E2E)
  are run by the user — don't fake them green.
- Every new AI claim must trace to evidence; never fabricate. Offline providers are
  refused when `APP_ENV=prod`.
- Keep `docs/PRODUCT.md`, `API.md`, `AGENTS.md` and their gates true to the code; a
  new endpoint/field updates the census in the same change.
- **ai-service features shipped ahead of their bridge are internal-only** and pinned
  by `tests/test_forward_features_contract.py` — add every new forward route there.
