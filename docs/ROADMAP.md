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
  The thread this note called open closed later in Epic 13: the current state now
  covers the six sections the engine owns, so the restore can retire what it can
  name -- see "The restore can retire what it can name" below.

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
  languages. That tail code went the way of `BAD_REQUEST` once the proactive
  layer arrived: it had picked up a feed address, a saved search with no
  criteria, an inverted salary range and the per-user feed cap, so the split
  left it naming nothing. It is five codes now (`TAILORED_BODY_MISSING`,
  `FEED_URL_INVALID`, `SAVED_SEARCH_EMPTY`, `SALARY_RANGE_INVALID`,
  `FEED_LIMIT_REACHED`), `VALIDATION_STRUCTURE_INVALID` is removed from the
  enum and from both tables, and every status is still the 400 it was.

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
  A sentence split around a value — `{replied} of {applied} submitted
  applications got a reply.` — was the last shape: its tail begins
  lower-case because the value before it is the sentence's subject, and
  the scan's capital rule skipped it, so whole English sentences rendered
  on a Chinese page behind a green gate. A lower-case fragment with a
  space and a closing mark is the tail of a sentence, not an identifier,
  and it is read now.
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

- [x] **19.1** Saved searches: a named criterion set (role, location, remote,
  salary floor, skills) the user can keep, list and delete — the thing an alert
  is about. Backend CRUD + `V__saved_searches` + the `/jobs` surface's "save
  this search" affordance.
  (`V11__saved_searches.sql` + `SavedSearchController`: GET/POST/DELETE under
  `/api/v1/saved-searches`, scoped to the caller. Criteria are stored as
  canonical JSONB under the board's own filter names, so the alert engine can
  hand them to `JobSearchRepository` unchanged; an exactly repeated skill folds
  to one but its case is kept — the board's SQL matches skills exactly — and
  `remote=false` is not stored, because the switch means "remote only". An
  empty board is not a saved search on either side of the wire. The panel
  beside the filters saves the live search under a suggested name, applies one
  back in a click through the URL's `replaceAll`, and forgets one behind a
  confirmation. 702 vitest, 29 backend tests green.)
- [x] **19.2** Scheduled ingestion: a nightly per-source pull that reuses
  `plan-ingest` (14.3) and writes the create/update/close plan, so a feed is
  swept without the user pasting it. The scheduler is the backend's, the plan
  is the engine's, and a failed pull is a recorded run rather than a silent
  night.
  (`V12__ingestion_feeds.sql` + `IngestionFeedController`: feeds and runs under
  `/api/v1/ingestion`, seven routes scoped to the caller, at most 20 feeds each.
  `IngestionScheduler` runs at 03:20 (`careeros.ingestion.cron`), and
  `ScheduledIngestionService` hands every enabled feed to the same
  deterministic engine 14.3 uses, storing the plan as a run — recorded, never
  applied, so a night can never rewrite the board. `FeedUrls` refuses
  non-http(s) shapes and private/loopback/link-local literals, and
  `HttpFeedFetcher` re-checks every redirect hop and caps the body. A failed
  pull is a `200` run with `status:"failed"` and the reason the server wrote
  down. The ingestion page now opens with the feeds panel: add/toggle/delete a
  feed, pull one now, read the night's runs, open a run's plan. 56 backend
  tests for the slice and its two gates, 712 vitest, census 133 files.)
- [x] **19.3** Notification center: an in-app inbox for the events the product
  already computes — a reminder that came due, an application that went quiet,
  a nightly pull that failed or brought postings. Read/unread, dismiss, and a
  deep link to the row that owns the signal.
  (`V13__notification_states.sql` + `NotificationController`: GET
  `/notifications` plus `/read`, `/read-all` and `/dismiss`, scoped to the
  caller. There is no notifications table — every item is synthesized at read
  time from the source that already knows it, the dashboard's own 14-day
  attention query and the last seven days of runs, so an item can never
  disagree with the screen that shows the same thing and a source that ends
  takes its item with it. The only stored state is the reader's,
  `notification_states`, keyed by the episode (`reminder:<app>:<epoch>`,
  `stale:<app>:<epoch>`, `ingestion:<run>`) so a new episode arrives unread
  rather than inheriting a dismissal; a write for a key the inbox is not
  showing is ignored, and every write answers the fresh inbox. A failed pull is
  always an item, a completed one only when it proposed postings. The
  `/notifications` page composes each sentence from the item's kind and holes in
  the reader's language, with mark-read, dismiss, mark-all-read and a link back
  to the board, the run history or the application. 15 backend tests for the
  slice, the doc/self-invocation/DTO/paging gates green, 604 backend tests, 718
  vitest, census 134 files.)
- [x] **19.4** Weekly digest delivery: the 15.3 digest delivered on a cadence
  (in-app, with an email-ready payload), so the week's signals do not require
  opening the app.
  (`V14__weekly_digests.sql` + `WeeklyDigestController`: GET `/digests` and
  POST `/digests/run`, and a Monday 08:00 `WeeklyDigestScheduler` writes the
  week that just ended for every user who has applications. Each row freezes
  the engine's answer — the payload is a snapshot, so re-reading a letter never
  re-renders it from data that has since moved; recomposing the same week
  replaces it in place under the `(user_id, week_start)` unique key.
  `week_start` is a date with a Monday check, never a timestamp, so no reader
  can convert it and land on the Sunday before. The letter asks the engine for
  its own 7-day window through a new 4-arg `insightDigest` (the dashboard keeps
  the engine's 14), and one user's failure is logged and skipped rather than
  costing the other letters. The analysis page opens with the letter card: the
  week's four numbers, the quietest stalled rows, earlier letters as history,
  and a compose-this-week action for the morning before the schedule runs;
  `formatDateOnly` pins a date-only value to UTC so the label is the Monday it
  names. 13 backend tests for the slice, the doc/wire/DTO/paging gates green,
  617 backend tests, 724 vitest, census 134 files.)
- [x] **19.5** Tailored-resume print view: a single version rendered through
  the export renderer's print layout and locale words, reachable from the
  tailoring surface — "tailor → print/PDF" without exporting the whole bundle.
  The ai-service's `POST /internal/features/render-resume` renders one
  version: its structured body section by section through the export's own
  print chrome and section words, or its stored text when it was never
  parsed, with the request's `locale` choosing the words. The backend's
  `printHtml` forwards (a blank document is `AI_SERVICE_EMPTY_RESPONSE`,
  "The renderer answered no document"), and `POST /resume-versions/{id}/print`
  answers `{html}` scoped to the caller — a version that is not the caller's
  is a 404. The browser opens the window inside the click gesture and fills
  it when the answer arrives, so the popup blocker sees a click rather than
  an await; the tailor panel prints a just-saved version and every version
  row on the resume detail page prints. 10 ai-service render tests, 3 service
  tests, 11 controller tests, the doc-parameter and error-vocabulary gates
  green, 625 backend tests, 724 vitest.)
- [x] **19.6** Voice mock interview: an STT/TTS provider seam plus record/play
  on the interview page. The scoring, difficulty ladder and depth trajectory
  stay the text interview's; only the input and output become voice.
  (`VOICE_PROVIDER=none|openai_compat|mock`, with `mock` refused under
  `APP_ENV=prod`; the provider's four refusals are typed --
  `VOICE_AUDIO_INVALID`, `VOICE_AUDIO_TOO_LARGE`, `VOICE_NOT_CONFIGURED` and
  `VOICE_UPSTREAM_FAILED`. Audio crosses the backend's JSON bridge as base64.
  `GET /interview/voice` answers `{provider, stt, tts}` best-effort -- an
  engine that cannot answer reads as no provider, which is what the page
  offers the browser's own speech for -- and
  `POST /interview/sessions/{id}/voice/transcribe|speak` checks the session is
  the caller's before any spend; a provider that answers no text or no clip is
  `AI_SERVICE_EMPTY_RESPONSE`. The runner's mic records through MediaRecorder
  (a two-minute cap) and sends base64, or falls back to the browser's
  SpeechRecognition; the question's listen toggle plays the provider's clip or
  `speechSynthesis`. A denied microphone is one sentence and the text box is
  untouched. 13 ai-service voice tests, 9 controller tests, 3 bridge tests,
  10 vitest helpers, the doc/wire gates green, 637 backend tests, 739 vitest.)
- [x] **19.7** Mobile/PWA: an installable shell, an offline shell page, and a
  responsive audit of the sidebar, the kanban drag and the wide tables.
  (`app/manifest.ts` + `public/sw.js` + `public/offline.html` + four PNGs under
  `public/icons/`. The manifest names the brand, starts an install on
  `/dashboard` with `scope:"/"`, and reads its description from the same locale
  cookie the document's metadata does, so the install dialog speaks the
  reader's language; iOS reads the document's `icons`/`appleWebApp` tags, and
  both roads name the same files. The worker precaches only the offline page
  and the install icons -- never a page or an API answer, because a cached
  board would show yesterday's postings as today's -- answers a navigation with
  the network or, with none, the offline page, and serves the build's
  content-hashed `_next/static` chunks cache-first with a background refresh.
  `lib/pwa.ts` registers it from `Providers`, only in a production build (a
  worker beside the dev server serves HMR's own stale chunks and hides the
  edit), and swallows a refused install because the app opens without one.
  The audit found the sidebar already a drawer under `lg` and the table
  primitive already wrapped in `overflow-x-auto`; the board's one real gap was
  the drag handle, where `touch-none` is what lets dnd-kit's pointer sensor see
  the gesture instead of the browser scrolling the column. `pwa.test.ts` holds
  the three files and the four PNGs to their promises; 739 vitest.)
- [x] **19.8** Real board connectors: Greenhouse / Lever public board APIs
  behind the existing `Connector` protocol, with the RSS/JSON paste path kept
  as the offline fallback.
  (The backend owns the network, the engine owns the meaning: a
  `BoardConnector` seam (`source()` + `apiUrl()`) turns what the reader knows —
  the board token, the public board page, or the API URL — into the one URL
  the fetcher opens, and `BoardConnectors` picks it by the feed's `source`.
  Greenhouse boards become `boards-api.greenhouse.io/v1/boards/{token}/jobs`,
  with `content=true` added when the reader's own URL omitted it; Lever boards
  become `api.lever.co/v0/postings/{token}?mode=json`, and an EU page maps to
  `api.eu.lever.co`. A foreign host or a path that names no board is refused
  with `FEED_BOARD_INVALID` — one sentence for every board, because the
  reader's next step is the same — and the panel's source is a three-way
  select whose URL placeholder and name note follow the choice. A board
  payload names no company, so the run passes the feed's name as `company`;
  the engine's normalizer learned both payload shapes (Greenhouse's wrapped
  `jobs`, escaped HTML `content`, `first_published`, dict locations; Lever's
  bare array, `text`, `hostedUrl`, epoch-millisecond `createdAt`,
  `categories`, `workplaceType`), reads epoch seconds as seconds, and leaves a
  commitment word outside the canonical four at the default rather than
  inventing a value. The paste path takes the same road: a parsed payload and
  its raw text plan to the same answer. 7 ai-service tests, 12 connector
  tests, 3 service tests, 1 frontend helper test, the error-code and wire
  gates green, 658 backend tests, 740 vitest.)
- [x] **19.9** Delivery hardening: nightly backups plus a restore drill,
  metrics/alerts for the scheduler and the AI budget, and a runbook that says
  what a failed night looks like.
  (The night now leaves readings, not just rows. `IngestionMetrics` is a
  Micrometer bean wired into `ScheduledIngestionService.runFeed` after the run
  is filed: one counter tagged by outcome, and a gauge holding the epoch second
  of the last *completed* run — a night of failures moves the counter and leaves
  the gauge where it was. The gauge starts at the process's own boot time rather
  than zero, because zero reads as a 1970 success and would page on every fresh
  deploy. `AiUsageMetrics` reads the trailing 24 hours of `ai_usage_events` once
  a minute and publishes cost, tokens and calls; a failed read logs and keeps
  the last reading instead of publishing zero. `ops/prometheus/alerts.yml` turns
  three questions into rules — no successful sweep for 26 hours, more than half
  of the last six hours' runs failed (with at least three runs), and more than
  5 USD spent in the last day — and each annotation links the
  `docs/RUNBOOK.md` section that says what to do. The runbook also records the
  reading the log line hides: `nightly ingestion swept N feed(s)` counts feeds
  that were *due*, not feeds that succeeded.
  Backups are two scripts, not a paragraph. `scripts/backup.sh` takes one
  custom-format `pg_dump`, one tar of the MinIO data directory, and a sha256
  file over both, verifies the archive lists before calling it a backup, and
  prunes complete sets beyond `BACKUP_KEEP`. `scripts/restore_drill.sh`
  verifies the checksums, restores the newest dump into a scratch database on
  the same server, compares the public table set and the applied Flyway count
  with the live database's, and drops the scratch database only when every
  check passed. Both find their containers through `docker compose ps -q`, so
  the `-prod` overlay is a `COMPOSE_FILE` away rather than a second script.
  Measured, not asserted: the pair was run against the live dev stack — the
  backup wrote its three files, and the drill restored 35 tables, 10
  migrations and a 942-entry files archive and then dropped `career_os_drill`.
  8 backend tests (6 metrics, 2 wiring), 15 ai-service gates (alerts + backup),
  660 backend tests.)

## Epic 20 — The Deployment Watches Itself

Epic 19 made the pass of a night visible while it ran: metrics, alarms, a runbook.
But the nightly *verification* run — the one that proves the whole stack still works
together — answered with a red X in a list that GitHub eventually forgets, and the
answer to "did the install verify itself last week" expired with the log. This epic
keeps the answers, and then starts asking the OS to act on them.

- [x] **20.1** The night's verdict, kept: the scheduled workflow records its own
  step outcomes in the database, and the monitoring page reads the history back.
  (A failing nightly run was a red X whose log expired; nothing else remembered.
  Now the job's last step runs under `if: always()` and posts
  `{startedAt, finishedAt, status, commitSha, runUrl, summary}` through the internal
  token to `POST /api/internal/nightly-reports`. The backend keeps it in
  `nightly_reports` (Flyway V15): written once and never updated, with a status
  check (passed or failed), a finish-before-start check, and a 40-entry cap on the
  summary's top-level keys — the row is a record, and a record that can be edited
  is not one. `GET /api/v1/monitoring/nightly-reports` pages the deployment-wide
  history newest first; it is deliberately not per account, because it records the
  install, not a user. The recorder (`app.ops.nightly_report`) maps GitHub's step
  outcomes onto passed / failed / skipped, records an outcome it does not recognise
  as failed, refuses a night with no steps, and turns the newest eval report's
  aggregates and case count into the eval step's detail. Without `CAREEROS_OPS_URL`
  it builds and prints the record without posting, so forks and dry runs stay green;
  with it, a failed post is a red step, because the record is the step's purpose.
  The workflow test reads `ci.yml` and holds the wiring: `if: always()`, a tracked
  step id per suite, and every tracked id read back into the payload. The monitoring
  page grows a nightly-history card whose own states survive a failed health report.
  8 ai-service tests (7 recorder + the workflow gate), 13 backend tests (7 service,
  6 controller), 5 frontend component tests, the copy census at 135 sources, the
  shape gates at 283 component names and 156 declared records.)

- [x] **20.2** The install's verdict, acted on: the history answers one question —
  is this deployment verifying itself — and the card says the answer out loud.
  (A list of nights still makes a reader page it to learn whether the cadence
  stopped. `GET /api/v1/monitoring/nightly-reports/verdict` reads the newest 30
  rows, in the same newest-first order the list uses, and answers the newest night
  as a verdict: `passed`, `failed`, or `missing` when no night has ever recorded,
  with its finish, commit and run link, the count of consecutive failed nights
  from the top (the walk ends at the first non-failure), and whether the newest
  record is older than 36 hours — a day and a half, more than twice the scheduled
  gap, so a stale verdict is an alarm even when that night passed: a record that
  stopped arriving is the failure nothing wrote down. The walk is bounded, so a
  long outage cannot turn one read into a scan of the whole table. The nightly
  card asks for the verdict through its own query and draws a warning strip only
  when the verdict earns one: no record at all, a cadence that stopped reporting,
  or two or more failed nights in a row — a single failure is already visible on
  its own row, and an unread verdict draws nothing rather than an alarm. 6 backend
  tests (5 service, 1 controller), 6 frontend tests (2 normalizer, 4 card), the
  shape gates at 283 component names and 157 declared records, the field contract
  at 46 bound readers and 80 producers, the copy census still at 135 sources.)

- [x] **20.3** The verdict reaches the pager: the install's answer becomes two gauges
  and two alarms, and the operator is told which night to open.
  (20.2 gave the page one answer, but its only reader was a person who happened to
  open the page: a deployment whose verification stopped reporting sat quietly until
  somebody looked. The backend publishes the verdict as Micrometer gauges —
  `careeros.nightly.last.finished.timestamp`, the newest record's finish whether it
  passed or failed, because the cadence stopping and the verification failing are
  different faults, and `careeros.nightly.consecutive.failures`, the same streak the
  card warns at. Both move when a night is recorded; a boot reads the stored history
  once so a restart cannot silence a streak, and a boot whose read fails keeps the
  boot defaults and logs why — a scrape endpoint is not worth a process that will not
  start. A missing verdict publishes no finish: silence on the wire is exactly what
  the stale rule exists to catch, and a fabricated "now" would mute it for 36 hours.
  `ops/prometheus/alerts.yml` gains `CareerOSNightlyVerificationStale` (36 hours of
  silence, critical) and `CareerOSNightlyVerificationFailing` (two failed nights in a
  row, warning), each linking its new RUNBOOK section. The alarm gate now reads the
  36-hour window from `STALE_AFTER_HOURS` and the streak threshold from the card's own
  warning line, so rule, service, page and prose cannot drift apart. 7 backend tests
  (3 service, 4 gauges), the alarm gate at 5 rules and 7 metrics, the runbook at 5
  alarm sections, the copy census still at 135 sources.)

- [x] **20.4** One night is one row: a retried post is answered with the record it
  already wrote, and the streak cannot count a timeout twice.
  (20.3's failure alarm counts nightly rows in a row, which made the writer's
  weakest point matter: the recorder runs under `if: always()` and posts over the
  network, and a post that times out after the row was saved is answered by a retry
  with a second row for the same night. The night's identity is its span, not its
  commit: a re-run starts and finishes at new times and is a distinct attempt, while
  a retry carries the same source and the same start and finish. `record()` looks
  that up before it inserts and, when it finds the row, answers it unchanged — same
  id, no second write — and republishes the verdict so the gauges still reflect what
  is stored. The dedupe lives in the service rather than behind a unique index on
  purpose: adding a constraint to a table that may already hold a duplicate would
  either fail the migration or tempt a delete of history, and the table's only
  writer is the one job, whose retries are sequential. 2 backend tests (the retry
  answered with the stored id and no save; a later end from the same start is
  another night and moves the gauge), the nightly service at 17 tests, the backend
  unit suite at 632, `API.md` and the deployment guide stating the retry answer, no
  frontend or census movement.)

## Epic 21 — The Letters Leave the Building

Epic 20 taught the install to keep its own verdict and hand it to a pager. The
user-facing half of "proactive" still ended at a screen: the weekly letter was
composed and stored with an email-ready payload, and the password-reset mail was
printed by the only transport that shipped. This epic gives the mail port a relay
that can leave the machine, and then lets the letter ride it.

- [x] **21.1** The mail port gains a transport that can leave the machine, and the
  configuration that proves which one is armed.
  (The `EmailSender` port shipped with a console implementation and a javadoc asking
  production to write an SMTP one; every reset mail in a real deployment went to a
  log line. `app.email.provider` now chooses the transport in one `EmailConfig`
  bean: `console` stays the default and keeps the reset link out of the logs unless
  the dev toggle is on, and `smtp` hands the plain-text letter to the relay named by
  `app.email.smtp.*` — host, port (587), an optional username/password pair that
  also arms `mail.smtp.auth`, STARTTLS on 587 or SSL from the first byte on 465,
  and `app.email.from` as the sender. The relay is built with 5-second connect,
  read and write ceilings, so a dead relay fails the request that needed the mail
  instead of holding it open; `smtp` refuses to boot without a host or a from
  address, and refuses STARTTLS and SSL together rather than guessing. A refused
  letter is thrown, not logged away, because the reset flow believes a send that
  returns. An unknown provider names itself instead of leaving the context with no
  mail bean. The eight new leaves join the `app:` block's census, re-pinned at 24
  leaves and 21 interpolated, with both env examples declaring the variables and
  the deployment guide explaining the console/SMTP split. The knob gate's
  client-cap reader follows the upload refusal into the English catalogue, where
  the i18n sweep moved it, so the gate is green on main again. 10 backend tests (2
  sender, 8 configuration), the backend unit suite at 642 (unit classes only; the
  ITs need Docker and are not counted here), no frontend or copy-census
  movement.)

- [x] **21.2** The weekly letter leaves on the night it is written, and the row says
  whether it did.
  (The Monday sweep composed each letter and stopped at the row: the week was written
  and nobody was told. `WeeklyDigestMailer` lays the stored payload out as the
  plain-text mail — the totals, the stage mix, the rates, the stalled rows and the
  engine's signals, with a key the payload does not carry dropping its line rather
  than printing a zero, and a stalled list capped at ten rows — and hands it to
  whichever transport `app.email.provider` armed. The sweep composes, writes, then
  mails: `delivered_at` is the latch as much as the receipt, so recomposing the week
  cannot put a second copy in a mailbox; a refused letter keeps the transport's error
  (`delivery_error`, capped at 500 characters) and the attempt count on the row while
  the night moves on to the next account, and an account row that is gone is a warn
  line with no attempt counted, so "never tried" stays zero. Composing from the
  dashboard still mails nothing — the sweep is the only sender, and `API.md` says so.
  V17 adds the three columns. 8 backend tests (4 service, 4 mailer), the backend unit
  suite at 650, the deployment guide and `API.md` stating the sweep's ownership of
  the send, no frontend or census movement.)

- [x] **21.3** The receipt is on the wire, a refused letter is tried again, and the
  install pages when the relay says no.
  (21.2 recorded the outcome on the row and stopped there: the browser could not see
  the receipt, and a refused letter sat until the next Monday. `WeeklyDigestDto` now
  carries `deliveredAt`, `deliveryError` and `deliveryAttempts` with every letter, so
  the page can say whether a week left, when, and what the relay said if it did not;
  zero attempts stays distinct from a refusal. A second scheduler clock runs at 09:05
  UTC daily: `WeeklyDigestService.retryUndelivered` asks the repository for undelivered
  letters that were actually attempted, oldest week first, at most a hundred a pass,
  and hands each to the same `deliver` latch -- so the dashboard's compose, at zero
  attempts, is never mailed by the clock, and a letter at the five-attempt cap is left
  on its row with its last error instead of retried forever. `deliver` now reports
  whether a letter left, which is what the retry counts. `WeeklyDigestDeliveryMetrics`
  publishes `careeros.digest.delivery{outcome=sent|refused}` and
  `careeros.digest.last.delivered.timestamp` (boot time at start, moved only by an
  acceptance). `ops/prometheus/alerts.yml` gains `CareerOSDigestDeliveryFailing`
  (any refusal in a six-hour window, warning), the alarms gate pins the new metric and
  rule, and `RUNBOOK.md` gains "A weekly letter the relay refused" with what to read
  on the row and what the retry can and cannot recover; the deployment guide lists the
  two families and the retry. 9 backend tests (3 retry, 3 metrics, 1 controller
  receipt, 2 scheduler), the backend unit suite at 659, the alarms/docs gates passing,
  no frontend or copy-census movement -- the digest card's delivery line waits for the
  frontend's i18n lane to land before the page can print the receipt.)

- [x] **21.4** The account's language reaches the letter.
  (21.2's mailer wrote English because the sweep composes without a browser, and the only
  copy of "the reader's language" was the browser's cookie. V18 gives the account one:
  `users.locale` (en or zh, default en) is answered by `/me` and accepted by PATCH `/me`
  as an eleventh optional field -- anything but en/zh is a 400 with a field-level detail
  before the service runs -- and `weekly_digests.locale` freezes the language with the
  payload. The sweep reads the account's language, passes it to the digest engine's
  `locale` so the signals are written in it, and stores it on the row; `WeeklyDigestMailer`
  lays the same readings out in Chinese words (subject, week line, stage mix, rates,
  stalled rows and signals), keyed off the letter's own locale, and the English output is
  byte-identical to before. A retry re-sends the stored letter, so a week keeps the language
  it was written in even if the account switches later. In the browser the cookie still
  paints the first render, and a new `AccountLocale` inside the signed-in shell reconciles
  the two copies: an explicit switch in this browser (the `localStorage` marker) is pushed
  to the account through the same PATCH, skipped without a session, while a browser that
  never chose adopts the account's language via `adoptLocale` -- cookie and screen, never
  `localStorage` -- so it keeps following a change made elsewhere. 5 backend tests (1 sweep,
  2 mailer, 2 controller), the backend unit suite at 664; 10 frontend tests over the
  decision table and the no-session guard; the user request census now pins eleven fields
  (with a mutation arm run) and the two failure-toast assertions the i18n commit moved are
  current again; `API.md` and the deployment guide state the account-language rule. The
  lifetime census was also charging a RUNBOOK metrics-refresh interval as a refresh-token
  lifetime, reworded. No copy-census movement: the reconciler prints nothing.)

## Epic 22 — The Inbox Leaves the App

Epic 21 taught the weekly letter to leave the building. The inbox itself still only
reached whoever opened the app: a reminder that came due, an application that went
quiet, a pull that failed -- all of it waited on a screen behind a sign-in. This epic
carries those waiting signals out by mail, once per episode and never twice, without
making the notification a second source of truth: the app remains where a signal is
settled, and the letter is only a pointer to it.

- [x] **22.1** The morning sweep mails what the inbox is still waiting on, once per
  episode.
  (The inbox is synthesized on every read and its only stored state was the reader's --
  read and dismissed -- so nothing could carry a signal out of the app without either
  mailing it every morning or inventing a notifications table. V19 adds
  `notification_states.notified_at`: the moment a mail carrying the episode was accepted
  by the transport, the third thing the reader's state remembers and the one a later
  sweep reads. `NotificationService` grows the walk the screen already used: `shown` is
  the dismissed filter, the newest-first sort and the forty-item cap moved out of
  `inbox`, `awaitingDelivery` answers the visible items that are unread and unnotified,
  and `markNotified` latches the delivered keys. A read that lands between composing and
  latching keeps its own column and does not stop the latch; a dismissal or an in-app
  read before the sweep keeps the item out of the letter entirely. `NotificationMailer`
  lays the items out as plain text in the account's language -- the same EN/ZH
  word-table shape as the weekly letter, ten named rows with the rest counted (and all
  of them latched, because the letter announced them), one line per signal with its
  reason and an absolute link under it built from `app.web.base-url` --
  and `NotificationMailService` asks the union of application owners and feed owners
  what is waiting, never writes an empty letter, sends with no transaction open, and
  latches only after the transport accepts: a refusal is a warn line and tomorrow's
  sweep retries, and one account's bad state never costs the others their morning.
  `NotificationMailScheduler` runs the pass at 07:30 UTC, configurable through
  `careeros.signals.cron`. 16 backend tests (3 service, 6 mailer, 5 sweep, 2
  scheduler), the backend unit suite at 680, the architecture doc naming the new
  column, `API.md` and the deployment guide stating the once-per-episode rule and the
  absolute-link requirement. No frontend or copy-census movement: the inbox screen is
  unchanged, and the letter is read in the mailbox.)

- [x] **22.2** The morning mail is metered, and a relay that refuses a whole morning
  pages.
  (22.1 could refuse every account's letter and leave only warn lines: no counter, no
  alarm, and the one reading an operator needed -- was the relay down, or is the install
  quiet? -- did not exist. `NotificationDeliveryMetrics` publishes
  `careeros.signals.delivery{outcome=sent|refused}`, counted per account letter that
  reached the transport, and `careeros.signals.last.delivered.timestamp`, the last
  acceptance (boot time at start, moved only by an acceptance, never by a refusal). An
  account with no row or no address is a warn line rather than a refusal: the transport
  was never asked, so counting it would blame the relay for a missing mailbox.
  `NotificationMailService` records the refusal in the transport's catch and the
  acceptance before the latch, so the counter and `notified_at` describe the same event
  and the latch still waits for the transport. The marker is deliberately not alarmed:
  an install whose inboxes are quiet writes no letter and that is not a fault.
  `ops/prometheus/alerts.yml` gains `CareerOSSignalMailFailing` at three refusals in six
  hours (warning) -- not the digest's any-refusal rule, because the signal sweep re-asks
  every morning while an episode stays visible, so one undeliverable address would
  refuse once a day forever and page daily, while three refusals inside one sweep window
  are several accounts failing in the same morning, which is the relay or its
  configuration. The alarms gate pins the counter's exported and dotted names and the
  rule; `RUNBOOK.md` gains "The morning mail is refused" (one address versus the relay,
  why nothing should be latched by hand, why one refusal stays below the floor) and the
  deployment guide lists the two families and the alert. 3 backend metrics tests plus
  the sweep's metric assertions, the backend unit suite at 683 and the integration suite
  at 69, the alarms/docs gates passing, no frontend or copy-census movement.)

- [x] **22.3** The morning has a heartbeat, so a clock that stopped is not mistaken for a
  quiet inbox.
  (22.2 metered letters, but its delivered marker moves only when a letter leaves: an
  install with nothing waiting never moves it, so a scheduler that stopped -- a bad
  `careeros.signals.cron`, a bean that never started -- was invisible. The same metrics
  class now publishes `careeros.signals.last.sweep.timestamp`, moved by
  `NotificationMailService.mailPending()` at the end of every completed pass, with or
  without letters; a pass that could not even read its audience never reaches it, so a
  database outage that blocks the sweep still goes stale. The marker starts at boot, so a
  fresh deploy is not read as stale before it has had a morning. `ops/prometheus/alerts.yml`
  gains `CareerOSSignalSweepStale` at 36 hours (twice the daily cadence and the same
  129600 seconds the nightly stale rule uses, warning); the alarms gate pins the gauge and
  the rule, and `RUNBOOK.md` gains "The morning sweep stopped", separating a failed firing
  from a silent clock and warning against writing the gauge by hand. 2 backend tests (1
  metrics, 1 sweep) plus the quiet-pass heartbeat assertion, the backend unit suite at
  685 and the integration suite at 69, the alarms/docs gates passing, no frontend or
  copy-census movement.)

- [x] **22.4** The Monday letter has a heartbeat, so a compose clock that stopped is not
  mistaken for a week where nobody applied.
  (22.3 gives the morning signal sweep a heartbeat, but the weekly letter's own clock --
  Monday 08:00 UTC, `careeros.digest.cron` -- had none. Its two meters answer what the
  transport did with a letter; a compose that never ran writes no letter, so the
  delivered marker sits still and every dashboard reads "no mail" rather than "no
  Monday". `WeeklyDigestDeliveryMetrics` now publishes
  `careeros.digest.last.sweep.timestamp`, moved by `WeeklyDigestScheduler.publish()`
  only after `composeWeek` returns -- a sweep that threw never advances it, and a quiet
  Monday with nothing to write still does. The 09:05 retry deliberately does not move it:
  the heartbeat answers whether the week was written, and a retry that delivered an old
  letter must not mask two missed Mondays. The marker starts at boot. `alerts.yml` gains
  `CareerOSDigestSweepStale` at 691200 seconds (eight days: one weekly period plus a day
  of grace, so a missed Monday pages the following Tuesday and a merely late run does
  not), warning; the alarms gate pins the gauge and the rule, and `RUNBOOK.md` gains "The
  Monday letter was never written", which separates a stopped cron from a delivery
  failure and records that a missed week cannot be recomposed through any route -- the
  sweep always writes the week before last. 2 backend tests (1 metrics, 1 scheduler) plus
  heartbeat assertions, the backend unit suite at 686 and the integration suite at 69,
  the alarms/docs gates passing, no frontend or copy-census movement.)

## Epic 23 — The Letters Can Be Stopped

Epic 22 finished the outbound loop: the inbox and the week both leave the app on a
cadence, and both are metered while they do. What neither letter could do was stop. An
account that no longer wanted the Monday digest or the morning signals had no switch
anywhere -- not in the mail, not in the app -- so the only way out a mailbox offers is
the spam button, and a spam report costs every letter the install sends after it. This
epic gives both lists a stored preference, a signed page a mailbox can open without a
password, and the RFC 8058 headers mail clients read; the sweeps obey the preference
and the dashboard archive does not: a reader can stop the mail without losing the
record.

- [x] **23.1** Every letter carries a way out, and the clocks obey it.
  (Two lists, two dials -- `weekly` for the Monday letter and `signals` for the morning
  inbox mail -- stored in V20's `mail_preferences`, one row per account, absence meaning
  both on: the shipped default is what an account that never visited the page gets, and a
  row that turns a dial back on is written rather than deleted, so "on" is a value the
  reader chose and not a missing row. `MailList` names the two and owns the mapping to
  their columns; `MailPreferenceService` answers `receives(userId, list)` with the absent
  default and `optedOut(list)` with the set of accounts that said no, read once per
  sweep, so the morning pass can skip a reader before asking what is waiting and the
  Monday `deliver` can return before the attempt counter moves -- turning the mail off is
  not a refusal, so it must not spend one of the five retries or page the relay.

  The link is its own credential. `MailLinks` signs `careeros-mail-preference:<userId>`
  with HMAC-SHA256 under `app.mail.link-secret`, URL-safe and unpadded, and compares the
  presented token in constant time: no per-link row, no expiry to sweep, and rotating the
  secret retires every link ever mailed -- the answer to a forwarded letter or a leaked
  mailbox. A blank secret stops the boot instead of signing with an empty key, which would
  make every account's URL forgeable. `app.web.base-url` prefixes the page because the
  reader's origin is the app that proxies the backend, and a trailing slash in that knob
  does not double the separator.

  The page is server-rendered and bilingual, in the account's own language like the
  letters: `MailPreferenceController` serves `/api/v1/mail/preferences/{userId}/{token}`
  as HTML (`no-store`, `X-Robots-Tag: noindex`, because it states private settings) with
  one section per list and a POST button each. The GET changes nothing -- mail scanners
  prefetch every URL in a letter, so a read that flipped a switch would unsubscribe
  readers who never clicked -- and a GET on either POST URL is a 405. A forged token, an
  unknown account and an unknown list are one 404 and touch no state. The prefix is
  admitted by `SecurityConfig` without a bearer because a mailbox cannot send one, and
  `SECURITY.md`'s public-routes list names it beside auth and health.

  Both letters carry the footer and the headers: `EmailSender` grew a header map so the
  RFC 8058 pair (`List-Unsubscribe: <.../stop/{list}>`,
  `List-Unsubscribe-Post: List-Unsubscribe=One-Click`) reaches the relay, and
  `SmtpEmailSender` builds a UTF-8 `MimeMessage` because a Chinese subject cannot ride a
  `SimpleMailMessage`; the console transport logs header names only, so a token URL never
  leaks by default. The Monday letter's one-click names `weekly` and the signal letter's
  names `signals`, so a one-click from one letter can never silence the other.

  26 backend tests (7 for the signed links, 5 for the stored preference, 8 for the
  page, and the mailers, sweeps and transport updated for the new signatures and
  headers), the backend unit suite at 712 and the integration suite at 69, the
  API/knob/security/env doc gates passing, no frontend or copy-census movement.)

## Epic 24 — The Reader Can Leave

The workspace can leave in a file (Epic 13) and the letters can stop (Epic 23), but the
account itself had neither exit. The only way to replace a password was to sign out,
claim to have forgotten it and wait for a mail; the only way to leave was to walk away
from the rows. Everything a reader owns has cascaded from `users` since V1 — 36 foreign
keys when this epic landed, 37 after the address move — yet no route ever deleted a row.
This epic gives the account the two verbs its owner holds: change the lock, and close
the door.

- [x] **24.1** The password can be changed from the session that already knows it.

  (A signed-in reader had no way to replace a password except the forgot-password
  detour: sign out, say you forgot, open a mail, pick a new one. `PATCH /me/password`
  — and its `/users/me/password` alias — takes `{currentPassword, newPassword}`. The
  current value is the re-authentication: an open tab or a borrowed laptop is not
  enough to take the account away from its owner, so a wrong current password is a
  **401** `CURRENT_PASSWORD_INCORRECT` and changes nothing. A new value equal to the current
  one is refused with its own **400** `PASSWORD_UNCHANGED`, because re-storing the same
  hash would buy the reader nothing while still signing every other device out. On
  success the hash is re-encoded (BCrypt, never stored raw) and
  `TokenService.revokeAllForUser` retires every refresh token — the same response the
  reset path gives — so the caller's open tab keeps working only for the access
  token's short life, like every access token. The account id is the principal's; the
  request body has no field that could name another account. The answer is
  `{changed: true}` and carries neither password.

  11 backend tests (4 for the service rules — the right current password re-hashes and
  revokes, a wrong one touches nothing, the same value is refused by name, a vanished
  account is a 404 — and 7 for the two routes' envelope, validation, refusal codes,
  unauthenticated answer and body hygiene). The epic's suite and doc gates are recorded
  with 24.2, whose routes share the same two controllers. The screen landed in 38.4:
  `components/settings/password-card.tsx` posts the route and puts each refusal under
  the field that caused it.)

- [x] **24.2** The account can be erased for good, files and rows together.

  (`POST /me/erase` — and its `/users/me/erase` alias — takes `{password, confirmEmail}`.
  The password is the re-authentication; the typed address, compared without case or
  surrounding spaces, makes the request a second, explicit act — the address is on the
  screen, so it is a speed bump against a mis-click, not a secret. Both wrong answers
  have their own code — **401** `CURRENT_PASSWORD_INCORRECT` and **400**
  `CONFIRMATION_MISMATCH` — and touch nothing.
  Then `AccountErasureService` deletes the object-store file named by every
  `documents.file_key` the account owns and only after that deletes the `users` row: every
  foreign key into `users` — 36 when this epic landed, 37 since the address move — carries
  `ON DELETE CASCADE`, so the workspace — profile, memories, resumes, jobs, applications,
  interviews, conversations,
  documents and their chunks, knowledge sources, feeds, notifications, digests, growth
  plans, jobs, usage, tokens and mail preferences — leaves in one statement. Knowledge
  sources elsewhere in the product are retired with their files kept as an audit record;
  erasure is the one operation where the reader's right to be forgotten outranks the
  record, which is why nothing before this service ever called `StorageService.delete`.
  A storage failure aborts the transaction before the row is removed, so the account is
  whole and the request retryable, never half-erased; object deletion is idempotent, so a
  retry after a database failure finishes the job. The answer is `{erased: true}` and
  carries no password. The access token used to make the request still parses — access
  tokens are stateless — and its next request is a **404** `USER_NOT_FOUND`, while every
  refresh token is gone with its row. Backups are outside the live system and keep what
  they captured until their retention window passes; DEPLOYMENT.md says so beside the
  restore drill.

  12 backend tests (5 for the service — every file deleted before the row, a wrong
  password or a neighbour's address touching nothing, a storage failure leaving the
  account whole, a vanished account a 404 — 6 for the two routes' envelope, both refusal
  codes, validation, the unauthenticated answer and body hygiene, and 1 integration test
  that gives two accounts the same rows and files, erases one through the API and proves
  every user-scoped table and the bucket empty for it while the neighbour is whole), the
  backend unit suite at 734 and the integration suite at 70, the API/knob/security/env
  doc gates passing, no frontend or copy-census movement. The screen landed in 38.5:
  `components/settings/erase-account-card.tsx` draws the card, and the public
  `app/(auth)/account-erased/page.tsx` is the sentence the erased reader lands on.)

## Epic 25 — The Reader Can See the Open Doors

Epic 24 gave the account a lock and a door, but a reader who suspected a borrowed
laptop had no way to see what was still signed in, let alone close one of them: a
refresh-token family was an opaque id, and the only lever was the password change,
which signs every device out at once. This epic names each session when it starts and
gives the account the verbs the list implies.

- [x] **25.1** A session is named when it starts, and listed by family.

  (V21 adds `user_agent` and `client_ip` to `refresh_tokens`. `ClientInfo` reads them
  from the request that registers or logs in — the agent truncated to 255 chars, the
  address to 45, both optional because a client may omit the header — and rotation
  carries the family's name forward rather than re-reading the header, so a stolen
  refresh token cannot relabel the device it was stolen from. The reverse-proxy
  address parse now lives in `ClientInfo` and the rate limiter delegates to it, so the
  two readers of "who is calling" cannot drift apart.

  `GET /me/sessions` folds live tokens back into families: one row per device with the
  family id, the name, the start, the last rotation and the furthest expiry, newest
  activity first. The token that opened a family is retired by the first rotation, so
  the start is computed from every row of the family, not from the live ones alone —
  otherwise every refresh would make the session look newly opened. Revoked and
  expired families are left out: a session that can no longer refresh is not something
  the reader can still close. No token hash, raw token or family secret beyond the id
  is in the answer.

  8 backend tests (7 for the service — the name recorded at issuance, rotation staying
  in the family with its name, listing folding a rotation into one session ordered by
  last visit, closed and expired families left out, one family closed at a time, a
  stranger's family a 404 that touches nothing, closing twice answering the same 404 —
  and 1 for the list route's envelope across both spellings). The screen landed in
  38.3: `components/settings/sessions-card.tsx`.)

- [x] **25.2** The reader can close one door, or all of them.

  (`DELETE /me/sessions/{familyId}` revokes every live token of that family; the
  refresh token stops buying pairs at once and the answer is `{revoked: true}`. A
  family id that is not live for the caller — someone else's, or already closed — is
  one **404** `LOGIN_SESSION_NOT_FOUND` (the catch-all `NOT_FOUND` until 30.5 split
  it), deliberately indistinguishable so the endpoint cannot be used to probe for
  sessions, and it touches nothing. Closing the session that is
  asking is allowed and behaves like logout: the access token dies at its short
  expiry, because access tokens are stateless and a revocation list for them would be
  a second session store. `DELETE /me/sessions` closes everything and is the lever a
  reader reaches for after a password change has already done the same thing.
  `/users/me/sessions` mirrors all three verbs for the browser-facing alias, as the
  rest of the surface does.

  4 backend tests for the close verbs' two spellings, the 404 and the
  unauthenticated answer, plus 1 integration test that
  registers and logs in from two agents, proves the list names both and never leaks a
  token, rotates one without growing the list, closes the other and watches only its
  refresh die, sees a neighbour's family id answer 404 while the neighbour keeps
  refreshing, then closes all and watches the remaining refresh die and the list
  empty. The backend unit suite at 746 and the integration suite at 71, the
  API/knob/security/env doc gates passing, no frontend or copy-census movement — the
  settings screen that draws this list waited for the shared copy file, then landed in
  38.3 as `components/settings/sessions-card.tsx`.)

## Epic 26 — The Reader Can Move the Address

Epic 24 gave the account a lock and Epic 25 let it see its own doors, but the
address on the account was still the one typed at registration. A reader whose
mailbox closes, or who stops trusting an employer's domain, had no way to move it
short of opening a new account and losing the workspace. This epic moves the
address only once the new mailbox answers, because a sign-in address is also where
reset letters land: a move that skipped the confirmation would let anyone holding
a borrowed tab send the account's recovery mail to an inbox they own.

- [x] **26.1** The account can ask its address to move.

  (V22 adds `email_change_tokens`: the owner, the requested address in `citext`, a
  unique SHA-256 hash of the token, an expiry, a spend mark, a creation stamp and
  an index on the owner, with the same `ON DELETE CASCADE` every table pointing at
  `users` carries. `POST /me/email-change` — and the `/users/me/email-change`
  alias — costs the password, so a borrowed tab cannot start the move; it refuses
  the address the account already has (**400** `EMAIL_UNCHANGED`, compared after
  trimming and case-insensitively because the column is `citext`) and an address
  another account owns (**409** `EMAIL_ALREADY_REGISTERED`), and asking again
  replaces the pending link instead of leaving two live. Two letters leave: the
  confirmation link to the mailbox being claimed, and a warning naming the
  requested address to the mailbox on the account, so a reader who did not ask
  learns that someone holds their password. The raw token exists only in the
  first letter — the row keeps its hash, so a leaked table cannot answer it — and
  nothing on the user row changes yet.)

- [x] **26.2** The new mailbox answers, and only then does anything move.

  (`POST /auth/email-change/confirm` is public on purpose: possession of the
  token is the proof, exactly as on the reset route, so the new mailbox answers
  without a session. It is the only place that writes `users.email`. The token is
  spent before the address is checked, so a link that lost a race to a
  registration answers **409** `EMAIL_ALREADY_REGISTERED` and cannot be retried;
  unknown, spent, expired and ownerless links are one **400**
  `EMAIL_CHANGE_INVALID`, so the route is no oracle for which links were real. A
  confirmed move revokes every refresh token — the reset path's answer to a
  credential change — and mails the outcome to both addresses; the old address no
  longer signs in, the new one signs in with the unchanged password, and a
  neighbour account keeps its address and its sessions. The vocabulary grows to
  86 codes with `EMAIL_UNCHANGED` and `EMAIL_CHANGE_INVALID`, so the census
  test's frozen list and its prose counts move with it.)

  20 backend tests — 10 for the service (the two letters and the stored hash, a
  wrong password mailing nothing, the same address refused however it is cased, a
  neighbour's address refused, asking again replacing the earlier link, the
  confirmed move with its revocation and both letters, a link nobody issued, a
  spent or expired one, a link whose account was erased, and an address
  registered meanwhile burning the link), 9 for the three routes (both signed-in
  spellings' envelope and principal, body hygiene, the 401/400/409 answers,
  validation before the service, the public confirmation answering without a
  session and carrying only the flag, and the unauthenticated refusal) and 1
  integration test that registers two accounts, refuses a wrong password and a
  neighbour's address with no letter sent, reads the link out of the captured
  mail, confirms it against the real schema and watches `users.email` move, the
  old refresh die, the old address fail to sign in, the new one sign in with the
  same password, the link refuse a second answer, and the neighbour keep its
  address and its refresh. The backend unit suite at 765 and the integration suite
  at 72, the API/knob/security/env doc gates passing, no frontend or copy-census
  movement — the screen that starts the move waited for the shared copy and endpoint
  files, as the session list did; the card landed in 38.2
  (`components/settings/email-change-card.tsx`) and the public confirmation in 38.1
  (`app/(auth)/confirm-email/page.tsx`).

## Epic 27 — The Letter Relay Has a Meter

Epic 26 put a route on the account that writes to a mailbox it names — twice per
call. The limiter knew two kinds of spend, model calls and credential attempts,
and this route was neither, so a signed-in account could make the product write
to any unregistered address as fast as it could type. This epic gives the relay
its own ceiling and, in doing so, removes the filter's second copy of the
admission rule that had made a third bucket unsafe to add.

- [x] **27.1** The address move is metered, and one predicate decides every bucket.

  (`app.ratelimit.mail-per-minute` — default five a minute, `RATELIMIT_MAIL_PER_MINUTE`
  in both env examples — is a third ceiling, keyed by account id. `RateLimitFilter.ruleFor`
  is now the only author of "which bucket a path lands in": `doFilterInternal`
  asks it once and reads the ceiling, the identity and the
  `ratelimit:<bucket>:<identity>` key off that answer, where it used to test the
  auth prefix a second time — two authors of one predicate, and a path admitted
  by one rule could be counted against another. The bucket covers
  `POST /me/email-change` and its `/users/me/email-change` alias, both spellings
  and a trailing slash, because every call mails a confirmation and a warning;
  every other account route stays unthrottled. The over-limit answer, the
  `Retry-After` promise and the fail-open branch are unchanged; a sixth move in
  a minute is refused before the service mails anything.)

  The gate grew with the ceiling: the census now reads three knobs from
  `application.yml`, reconciles `AppProperties`' shadow initialisers, both env
  examples, the filter's javadoc, SECURITY.md's three identity lines and
  `RateLimitIT`'s three warm-up bounds, and its bucket test now asserts the one
  predicate and the three readings taken from its answer rather than the old
  two-author shape. 2 new classification tests and 1 integration test carry the
  behavior (five moves allowed, the sixth refused with the standard envelope);
  the backend unit suite at 767 and the integration suite at 73 are green, the
  knob census reads twenty-six `app.*` leaves with the mail ceiling among the
  fourteen accessor-read ones, and no frontend or copy-census movement.

- [x] **27.2** Every refusal is a reading an operator can scrape.

  (`RateLimitMetrics` registers `careeros.ratelimit.decisions`, tagged `bucket`
  — `auth`, `ai`, `mail` — and `outcome` — `allowed`, `denied` — and the filter
  moves it on either answer, so the 429s that used to leave only a response to
  the client now leave a counter the scrape endpoint renders as
  `careeros_ratelimit_decisions_total`. The fail-open branch counts as
  `allowed`, because that is the decision the server made; dropping it would
  make a Redis outage read as a quiet period on the one dashboard that should
  show it. A series exists from the bucket's first decision, so an install that
  never sees a mail call exports no mail series rather than a flat zero.
  DEPLOYMENT.md names the family and states that no alarm reads it yet — a
  refusal rate has no known-good baseline, and a guessed one would page on a
  busy minute. 3 decision tests drive the filter itself, which the suite had
  only classified but never executed: a refusal answers 429 with
  `Retry-After: 60` and the RATE_LIMITED envelope without reaching the chain,
  an admitted AI request runs the chain keyed by the account id and counted
  against 30, and a mail refusal is counted against the mail ceiling and
  neither of the other two; 3 more pin the counter's tags, the allowed/denied
  split and the lazy series. The backend unit suite at 773 and the integration
  suite at 73 are green, the metrics, alarms, limiter and knob gates pass, and
  no frontend or copy-census movement.)

## Epic 28 — The Tables Forget

Every account act writes a row that outlives the act: a sign-in writes a refresh
token, a forgotten password a reset row, an address move a confirmation row. Each
is read exactly once, by hash, while it is fresh, and every reader checks expiry —
but nothing ever deleted one. The tables therefore carry the install's entire
history of credentials, and an install that has been up for a year pays for every
token it has ever issued on each nightly scan. This epic is about tables that
forget: rows nothing can still act on, removed on a schedule, with the deletions
visible to an operator. It stops deliberately where visible history begins.

- [x] **28.1** Expired credential rows do not live forever.

  (`RetentionSweeper` runs nightly at 04:47 and deletes `refresh_tokens`,
  `password_reset_tokens` and `email_change_tokens` rows whose expiry is more
  than `app.retention.expired-token-days` in the past — thirty days by default,
  `RETENTION_EXPIRED_TOKEN_DAYS` in both env examples, and a negative value
  clamps to zero rather than deleting rows that expire in the future. The cutoff
  is the sweep's clock minus the grace window, not "expired now": a late request,
  a clock-skewed client or a support investigation still finds its row. Each
  table is deleted in its own repository transaction, so a lock timeout on one
  leaves the other two pruned; the failed table is logged and exports no counter,
  which is how a quiet night and a broken sweep stay different shapes. The
  deletions move `careeros.retention.deleted_rows`, tagged `table`, registered
  per table on its first successful sweep so an unused table advertises nothing.
  V23 adds an `expires_at` index to each of the three tables — the delete is a
  range read, not a full scan, which is the difference between a sweep that
  stays cheap as the tables grow and one that gets slower every night. The
  tables behind visible history are deliberately absent: `ai_usage_events` feeds
  the activity page's all-time totals, `notification_states` is the reader's
  read/dismiss memory, and ingestion runs and weekly letters are records, not
  residue; deleting any of them would rewrite a screen or re-announce a story the
  reader already settled. 4 unit tests pin the grace cutoff, the per-table
  counters, the failure isolation that leaves no series, and the negative clamp;
  the knob census now reads twenty-seven `app.*` leaves, twenty-four
  interpolated, eighteen bound fields and fifteen accessor readers; DEPLOYMENT.md
  names the metric family and the tables that are not pruned. The backend unit
  suite at 777 and the integration suite at 73 are green, the knob, env, alarms
  and deployment gates pass, and no frontend or copy-census movement.)

- [x] **28.2** The sweep proves it ran, not just how much it deleted.

  (A counter cannot answer whether a clock still runs: a stopped sweep leaves
  `careeros_retention.deleted_rows` at its last value, which a scrape reads the
  same as a night with nothing to delete, and the log line that would say so
  scrolls away. `RetentionMetrics` now also exports
  `careeros.retention.last.sweep.timestamp`, moved at the end of every completed
  pass — with or without deletions, and even when every table failed, because a
  pass that ran and failed is a different fault from a clock that stopped; the
  failed table is already a WARN line and an absent per-table series. The gauge
  starts at the process's boot time rather than zero, so a fresh deploy is not
  read as stale before its first 04:47. `CareerOSRetentionSweepStale` fires at 36
  hours — twice the daily cadence, the same window the other staleness rules
  use — and links a new RUNBOOK section that reads the gauge, the counters and
  the two log lines in order and names the one thing an operator must not do
  (hand-write the gauge; a missed night cannot be replayed). The RUNBOOK's
  "alarms, in one table" was five rows behind the rules it claimed to list, so
  it now carries all ten, and DEPLOYMENT.md names the gauge beside the delete
  counter. 2 unit tests cover the all-tables-failed pass moving the heartbeat and
  the boot-time start; the class is at 6. The backend unit suite at 779 and the
  integration suite at 73 are green, the alarms and deployment gates pass, and no
  frontend or copy-census movement.)

- [x] **28.3** The sweep's delete is proven against the schema Flyway builds.

  (The unit tests mock the repositories, so the JPQL delete and the V23 indexes
  were arguments, not evidence. `RetentionSweepIT` registers a real account,
  writes two rows into each credential table through the schema Flyway built --
  one expired sixty days ago, one expired yesterday -- runs the sweep, and
  asserts the far row is gone while the near one survives in all three tables,
  then reads `pg_indexes` for the three expiry indexes. A renamed column, a
  dropped index or a grace window that collapsed to "expired now" would each
  pass the mocks and fail here. The backend unit suite at 779 and the
  integration suite at 74 are green.)

## Epic 29 — The Search Speaks

A saved search is a question the reader asked once and kept. The rest of the
proactive layer has a voice — an application's reminder, a pull's failure, the
morning letter — but the criterion set itself was silent: the board answered it
only on the click that reopened it, so a posting that matched overnight waited
for the reader to come back and ask again. This epic gives the saved search its
own signal, on the inbox's own terms: synthesized at read time, keyed by the
episode, settled by reading or acting, and mailed at most once.

- [x] **29.1** A saved search speaks when new postings match it.

  (`SavedSearchMatcher` asks the board's own predicate:
  `JobSearchRepository.matchStats` reuses the WHERE fragment `search` and
  `count` build, so an alert cannot name a posting the board would not answer,
  and answers how many matching postings appeared since a moment and when the
  newest one did. The window starts at the later of the search's own creation
  and a seven-day floor (`NEW_WINDOW_DAYS`) — the same lookback the inbox gives
  a pull — so a search kept for months does not announce the catalogue it was
  saved against while a ten-day-old arrival is history, not news. Only
  `status='open'` postings count, and an empty criterion set is skipped rather
  than answered. The item is keyed
  `saved_search:<searchId>:<newestPostingAt epoch second>`, so a dismissal
  silences that arrival and the next matching posting re-arms the search with
  nothing stored but the reader's own state; its link is the board on the same
  question in the page's own spellings (`/jobs?q=…&skills=a,b&remote=1&…`), every
  value encoded. The morning letter names it in both languages ("a new posting
  matches this saved search" / "有 1 个新职位符合这个保存的搜索") and counts it like
  any other kind.

  Two facts came from evidence rather than reading. `matchStats` binds the WHERE
  values without `:userId`, because its statement carries no match-score join to
  reference it; the blind reuse of `bind` made every inbox read a 500 until
  `SavedSearchAlertIT` said so, and `JobSearchRepositoryTest` now pins the
  binding symmetry of this third statement. The integration test also pins the
  window against the schema Flyway builds: two matching postings, one inside
  seven days and one pushed twenty days back, and only the recent one is
  counted, with a dismissal round trip proving the episode re-arms on the next
  arrival. 5 matcher unit tests, 2 service tests, 1 mailer test, 1 repository
  binding test and 2 integration tests cover it. The backend unit suite at
  788 and the integration suite at 76 are green.)

- [x] **29.2** The morning sweep knows the reader who only keeps searches.

  (29.1 gave a saved search a voice inside the app, but the letter's audience was
  still applications ∪ feeds — the two sources that predate saved searches. A
  reader who browses with saved questions and never applies or subscribes a feed
  was in neither half, so their search's news waited in the inbox while every
  other account's morning left the building. `SavedSearchRepository` now answers
  its distinct owners and `NotificationMailService` unions it in as the third
  half; one account is still one letter, an opt-out is still read before the
  account is asked anything, and one account's bad row still costs nobody else
  their morning. 1 unit test pins an account reachable only through a saved
  search getting its mail, and the existing union test now puts one account in all
  three halves. The backend unit suite at 789 and the integration suite at
  76 are green.)

- [x] **29.3** The bell the inbox's own hook promised.

  (`useNotifications` said it was "read on demand by the bell and the page", but
  there was no bell: the synthesized inbox existed only on its own page, so a
  reminder that came due while the reader was on the board waited to be
  discovered. The notifications row now carries the unread count — a pill after
  the label, a badge on the icon in the collapsed rail — and the link's
  accessible name carries the count too; in the rail that name is the only one,
  since the label is hidden and the icon is aria-hidden (before this the
  collapsed rail's links had no name at all, so every row announced as "link").
  The query asks again on a 60-second beat (`INBOX_REFRESH_MS`), and React Query
  pauses the beat in a hidden tab, so a signal that arrives while the reader is
  elsewhere reaches the count without a reload and without a request per page
  view. A read inbox paints nothing rather than a zero. The copy is the
  existing `notifications.unreadBadge` key in every language — no new strings.
  3 layout tests pin the count, the empty state and the rail's name, and the
  badge was read in a real browser against a live backend: one unread
  saved-search signal, the count `1` on the notifications row. The full suite
  ran 785 of 786 — the one red is the route-parity census in
  `frontend/src/lib/api/endpoints.test.ts`, where the backend's
  account-security routes have no browser caller yet; pre-existing, and
  untouched here.

- [x] **29.4** A saved-search list is bounded like the feed list.

  (29.1 gave the search a voice, and 29.3 made the bell ask on a minute's beat —
  which turned the stored list into a multiplier on the read path that feeds
  never had: a feed is asked once a night, while every saved search is re-asked
  by every inbox read, by the bell's beat, and again by the morning sweep. The
  list had no bound, so an account could store as many questions as it liked and
  every one of them would run the board's predicate before the sweep had asked
  anything. `SavedSearchService` now refuses a create past
  `MAX_SAVED_SEARCHES_PER_USER` — the feed list's own 20, so the two lists a
  reader keeps are bounded alike — with a new `SAVED_SEARCH_LIMIT_REACHED`
  code, added to the frozen name census (87 codes) and to `API.md`. Validation
  still comes first: an empty search is refused as empty, not as full. 2 unit
  tests pin the boundary in both directions — the search that fills the last
  place is stored, and the one past it is refused without a write. The backend
  unit suite at 791 and the integration suite at 76 are green. The refusal's
  sentence reaches the reader in English through the server's own wording
  until the browser's copy table carries the code; the table is another
  session's in-flight file, so the localized sentence is left for the change
  that next opens it.)

- [x] **29.5** The phone's menu trigger carries the count.

  (29.3 put the count on the notifications row, but below `lg` the rows live in
  a drawer behind the topbar's hamburger: a reader on a phone saw nothing until
  they opened the menu, so the bell still waited to be discovered on exactly the
  form factor where the app is hardest to check. `MobileSidebar` now reads the
  same inbox the rows read — one query key, so the beats do not double — and the
  trigger carries the count twice: the badge on the icon, and the count inside
  the trigger's accessible name, because the badge is decorative. A read inbox
  leaves the trigger plain. The copy is the existing `notifications.unreadBadge`
  key; no new strings. 2 server-render tests pin the named trigger and the
  plain one, and the file now holds 5; the live inbox-to-row path was already
  read in a real browser under 29.3, and this change only adds a second reader
  of the same query. The full suite ran 787 of 788 — the one red is the
  route-parity census in `frontend/src/lib/api/endpoints.test.ts`, the same
  pre-existing, other-session-owned item 29.3 recorded.)

## Epic 30 — The Censuses the Backend's Epics Outran

The repository's cross-language censuses grade the tree from both sides: the
architecture document against the migrations and the backend's packages, the
credential lifetimes against every duration written in the repo, the browser's
copy table against the error codes the services throw. Those gates were written
before the last ten epics and read the repository as it had been. The ai-service
suite has been red for several epics, and every red had been read as "the other
session's mess" without anyone separating the two. This epic brings the censuses
up to the tree both sides actually ship, and writes down which red is whose.

- [x] **30.1** The structural censuses read the tree the backend ships.

  (Three gates were red for reasons of their own. `docs/architecture.md` §3 did
  not name `mail/` — the letters' reader-facing half landed in 21.1 and
  `test_the_repository_layout_names_what_exists.py` refused the undocumented
  package — and §4 counted 40 of the migrations' 42 tables, missing
  `email_change_tokens` (26: the hash, never the link; one use; two hours) and
  `mail_preferences` (23.1: the two switches; an absent row means both on).
  `SavedSearchAlertIT` backdated its search by `interval '30 days'`, the refresh
  token's shipped lifetime, and the lifetime census charges every shipped
  duration written without a credential word beside it, so a fixture
  about a news window failed a gate about credentials; ten days stays outside
  the seven-day floor the test needs and outside the credential vocabulary.
  The three files pass (12 tests), `SavedSearchAlertIT` passes alone against
  Postgres (2 tests), and the backend stands at 791 unit + 76 integration, 0
  failures. The epic also measured the suite honestly for the first time: a
  clean worktree at `f25f6db` answers 27 failed / 1889 passed / 1 skipped,
  while the shared tree answered 37 — the ten extra reds read the concurrent
  session's in-flight `normalize.ts`, `types.ts`, `endpoints.ts`,
  `translations.ts` and `test_response_shape_contract.py`, and are that
  session's to land. Of the 27 at HEAD, these three were the structural ones;
  the other 24 are the next items of this epic.)

- [x] **30.2** The mutation censuses read the key the toast resolves.

  (Between Epics 23 and 29 the browser moved every failed write from an English
  literal at the hook to a copy key -- `onError: fail("failures.applicationCreate")`
  -- because the toast is raised long after the render that knew the reader's
  language, and the sentence has to be resolved then. Ten ai-service censuses
  still searched for the retired sentences, and each red said "the failure toast
  message changed" about a message that had been deliberately replaced. They now
  pin the key each mutation spends: the six action-hook contracts (application
  create/update/move, conversation start/rename, copilot, interview
  start/evaluate, JD analysis/suggestions, the resume version switch), the two
  route rosters the account-security epics grew (`/email-change/confirm` is the
  auth controller's seventh POST and sixth record; `/me` keeps the profile pair
  bare and lists its six security paths), and the central fail() census, whose
  roster now reads 73 uses across eight files and names its one shared key
  (`notifications.actionFailed`, the inbox's three writes, which are one
  sentence about one screen). The helper's own shape moved with it
  (`fail(fallbackKey: string)`), and every key a call names is answered in both
  languages by the browser's own `fail-keys` gate, so the two suites meet at
  the table. Ten reds closed; the nine files run 76 tests green at `f25f6db`.)

- [x] **30.3** The drift censuses read the keys and the tree both lanes ship.

  (Six census files still pinned sentences the copy-key refactor had retired --
  the reminder toast, the 404 page's offline and missing-route sentences, the
  two profile toasts, the validation detail line, and the knowledge mutations'
  four failure keys -- and every red said "the message changed" about a message
  that had been deliberately replaced by a key. They now pin the key each site
  spends and read the sentence from the one locale table: the 404 sentence's
  English copy is answered exactly twice there, the two profile toasts resolve
  through keys in both languages and their sentences appear in no other source,
  and the knowledge contract's mutation arm breaks `failures.ingest` instead of
  an English literal. The records mapper's component census became a floor at
  349 -- 63 names joined since it was written at 286 and none left, because the
  walk grows with the backend -- and its dead-name tiers split when `versionNo`
  turned out to be carried by the copy census's fixture and scanner as well as
  the three readers.

  `test_response_shape_contract.py` carried three drifts of its own. The
  backend declares 170 records, not 157: thirteen joined with the
  account-security, session, retention, saved-search, notification and mail
  epics, and the comment names each one. The interval ledger's doc census is
  now per-file counts (26 rows: ROADMAP 7, RUNBOOK 13, DEPLOYMENT 4, AGENTS 1,
  SECURITY 1) because a line ledger red on every roadmap paragraph written
  above it, and its shipped-code vocabulary lists all ten spans -- the run
  stream's two and the eight the other three clocks contribute (22.3's signal
  mail, 22.4's Monday letter, 28.2's retention sweep). The media-type census
  grew a third bucket, `declared-constant`, for 23.1's mail-settings page
  naming its own answer as HTML from a literal, and 25.1's `ClientInfo` reads
  `User-Agent`, joining the request-header floor -- still no media type among
  them. The 30.1 entry above was charged by the lifetime census itself: its
  sentence put the old interval on one line and the refresh token on the next,
  and that scan is line-scoped; the wrap moved, the claim did not.

  At `f25f6db` these eight files run 107 of 109 green. In the shared tree the
  suite reads 14 failed / 1902 passed / 1 skipped: two reds are the cache-writes
  pair reading this session's in-flight `ingestion.ts` and `source-actions.tsx`
  (7 -> 10 invalidation calls, 62 -> 65 borrowed promises), six read the same
  session's uncommitted `normalize.ts` / `types.ts` (`normalizeApplyResult` and
  the accessor counts), and three read its `ingestion.ts` mutation roster (8 ->
  9). The two that remain after that attribution are the error-code gate's, and
  they are not excused: 24.2's `CONFIRMATION_MISMATCH` has no browser sentence,
  and `INVALID_CREDENTIALS` answers four throw sites with three different
  sentences (login, a password change, an erased account's wrong password, an
  address move) while the table resolves one sentence per code. The fix is
  finer codes plus their sentences in `translations.ts`, which the concurrent
  session is rewriting; **30.4** below lands them, staging only its own hunks
  beside that rewrite, so the gate is green at 30.4's commit.)

- [x] **30.4** The sign-in refusal and the signed-in reader's wrong password
  are two codes.

  (`INVALID_CREDENTIALS` answered four throw sites with three sentences: a
  failed sign-in, a wrong current password at the password change, at the
  address move and at erasure. The enum gains `CURRENT_PASSWORD_INCORRECT`
  (401) -- the three re-authentication sites name it with one sentence,
  "Current password is incorrect", and sign-in keeps `INVALID_CREDENTIALS`
  with "Invalid email or password" -- so the gate's one-sentence-per-code rule
  holds with no same-meaning exception. The census's frozen name list grows to
  88 codes deliberately, the split's reason beside the new name; seven
  backend test files move their pins to the new code and sentence, the
  address-move IT moves its request-path pin, and the three `API.md` rows say
  it.

  The gate had five more unclassified codes behind its first red: epics 26-29
  added `EMAIL_CHANGE_INVALID`, `EMAIL_UNCHANGED`, `PASSWORD_UNCHANGED` and
  `SAVED_SEARCH_LIMIT_REACHED` and 24.2 added `CONFIRMATION_MISMATCH`, none
  with a sentence in either language, because the epics' own tests pinned the
  server's words and the table was never asked. Six sentences now sit in both
  `errorCodes` blocks, each read off its throw sites;
  `EMAIL_CHANGE_INVALID` has two wordings and joins the same-meaning list,
  because the public route refuses unknown, spent and expired links in one
  voice on purpose, so the reader is not told which half of a guess was right.

  `NOT_FOUND` is named as a gap instead: it answers the route catch-all
  ("Resource not found"), a login-session row a reader asked to close
  ("Session not found"), and the mail-settings page's three refusals through
  a constant the scan cannot read. One sentence would be wrong about two of
  the three, so the reader keeps the server's own words -- the queue item this
  entry leaves behind is a session-row code and a mail-link code. The gate
  runs 7 of 7 green, and the browser's table gained its six sentences with
  only this session's hunks staged beside the concurrent rewrite.)

- [x] **30.5** The catch-all is the address, and the session and the letter
  have their own refusals.

  (`NOT_FOUND` answered three things: the route catch-all ("Resource not
  found"), a login-session row a reader asked to close ("Session not found"),
  and the mail-settings page's three refusals, which share one constant. The
  gate could not read the constant at all, so the code was named a gap with
  three meanings. `LOGIN_SESSION_NOT_FOUND` (404, "That session is already
  closed.") and `MAIL_LINK_INVALID` (404, "That mail-settings link is not
  valid or has been retired.") are the split; `NOT_FOUND` keeps the
  catch-all's one sentence, and the gaps list is empty again.

  The gate learned to read a same-file `static final String`, so the mail
  page's one sentence is measured rather than guessed -- the three throw sites
  still share the constant, and the scan now follows it. The frozen name
  census reads 90 codes; `TokenServiceSessionsTest`'s two refusals and
  `SessionControllerTest`'s envelope move to the session code, `API.md`'s
  three rows name them, and both tables answer the two sentences. The gate
  reddened on the measured three meanings before the split and runs 7 of 7
  after it.)

- [x] **30.6** The split's two readers: a session IT still expected the
  catch-all, and the docs census read an error code as a field.

  (30.5 ran its own gate and a targeted backend run, not the full suite, and
  two readers it had not taught were left red. `SessionsIT` closed a
  neighbour's session family and still expected `NOT_FOUND` — the route the
  split had just re-coded; it now expects `LOGIN_SESSION_NOT_FOUND`.
  `ApiDocParamContractTest` reads a snake_case name quoted in a GET row as a
  field the backend writes, and the mail row legitimately names
  `MAIL_LINK_INVALID`, an error code rather than a field. The census now
  grades a quoted name against the field literals *or* the `ApiErrorCode`
  members, so a code the enum does not declare is still a red — a typo in a
  promised code is as invisible to an integrator as a field that never
  arrives. The positive control asserts the vocabulary is actually read.

  Seen by a full-suite run — 872 tests, exactly these 2 failures — fixed, and
  green since. The lesson is the 30.5 entry's own: a split's gate is not the
  suite.)

## Epic 31 — The Shell's Own Hardening

Every hardening epic so far guarded the services behind the browser: limits,
retention, metrics, mail. The browser's half was left to "the reverse proxy",
yet the same shell is served by `next start` in local runs and the E2E suite,
where no proxy exists.

- [x] **31.1** Every answer tells the browser what it may frame, sniff and use.

  (`frontend/next.config.ts` returns four headers for `/:path*`:
  frame-denial, no-sniff, a referrer policy that strips the path from
  cross-site referrers — record ids live in the path — and a permissions
  policy that denies the camera and geolocation while leaving the microphone
  to this origin, because the interview page records with it. The list is
  exported once and `src/app/security-headers.test.ts` pins the rule Next
  reads, so a header added to the list cannot skip the rule and a rule that
  stops carrying the list is a red. Verified against a running dev server:
  all four headers appear on a `200` from `/`, and `tsc` and ESLint stay
  clean.)

- [x] **31.2** Every answer names the sources it may load and run.

  (`frontend/src/middleware.ts` mints a nonce per answer, hands it to Next in
  the request's `Content-Security-Policy` header — the channel Next reads to
  stamp the scripts it emits — and returns the same policy on the response.
  The rules live once in `src/lib/security/csp.ts`: this origin, the API's
  origin (read off `NEXT_PUBLIC_API_BASE_URL`, path dropped) and nothing else
  may be connected to; the nonce plus `'strict-dynamic'` is what may run;
  `style-src` keeps `'unsafe-inline'` because Next writes the fonts'
  variables and the first paint as inline style; `img-src` adds the local
  `data:`/`blob:` images and `media-src` the interview page's recorded voice;
  `worker-src 'self'` admits the installable shell; objects, framing, a
  foreign `base` and foreign form posts are refused; and
  `upgrade-insecure-requests` appears only when the answer itself arrived
  over https, because a plain-http local run has no TLS to upgrade to and the
  API's own http address would be rewritten into an https one the server does
  not answer. The development build alone gets `'unsafe-eval'` and the
  `ws:`/`wss:` connect sources its hot reload needs.

  next-themes writes its own inline theme bootstrap, and a nonce on the
  framework's scripts is not a nonce on that one: the layout reads the
  middleware's `x-nonce` and the nonce travels `RootDocument` → `Providers` →
  `ThemeProvider`. The gate (`csp.test.ts`, 7 cases, and
  `middleware.test.ts`, 3) pins each directive, the development-only
  exemptions, the https-only upgrade, that every answer's nonce differs, and
  that the build's hashed chunks are left out. Verified against `next start`:
  the header rides every answer; the raw answer's 28 script tags all carried
  its nonce (before the theme hand-off, 27 of 28 did — the bare one was
  next-themes); the policy names the configured API origin; the worker
  registers at this origin; a client-side language switch changed
  `<html lang>` and the heading, so the page hydrates under the policy;
  static chunks carry no policy while `sw.js` and `offline.html` do; and the
  console shows no CSP or hydration error in either the production or the
  development build. `tsc`, ESLint and `next build` stay clean.)

- [x] **31.3** The API's cross-origin door names the shell and nothing else.

  (The services behind the browser were gated; the door between the browser
  and the API was not. `docs/SECURITY.md` described the CORS allow-list, but
  nothing had ever driven it: a chain that forgot `.cors(...)`, a method
  dropped from the list, or a header the shell sends but the door no longer
  names would have surfaced only as a request that never leaves the browser.
  `backend/src/test/java/com/careeros/CorsContractIT.java` now speaks through
  the real filter chain as `http://localhost:3000` — the shipped
  `APP_CORS_ORIGINS` default — and as `https://evil.example`. It pins the
  shell's preflight (`200`; the origin echoed back; `POST` among the allowed
  methods; `authorization` and `content-type` among the allowed headers;
  `max-age 3600`), that the shell's actual request carries the origin back,
  and that a foreign origin gets neither door: its preflight is a `403` with
  no `Access-Control-Allow-Origin`, and its request to the public
  `/api/v1/health` is refused before the route is reached — only the origin
  check can refuse a public route, so the `403` names the door as the
  refuser. A `TRACE` preflight from the shell is refused too.

  Mutation arm: deleting `.cors(...)` from `SecurityConfig` turned the
  shell's preflight into a `403` and stripped the origin from the actual
  request; the chain was restored byte-identical and the class runs 5/5
  green. Full backend suite green.)

- [x] **31.4** The client's address is the socket's unless a proxy is
  declared.

  (`docs/SECURITY.md` finding #2 had measured this bypass: `clientIp` read the
  leftmost `X-Forwarded-For` entry unconditionally, so six logins carrying six
  spoofed values bought six fresh buckets. The trust is now a deployment
  declaration — `APP_HTTP_TRUST_FORWARDED_FOR` (`app.http.trust-forwarded-for`),
  **off by default**. Off, the socket's address is the identity and the header
  is hearsay; on, the **rightmost** hop is read — the one the trusted proxy
  wrote — because the nginx form the docs used to show,
  `$proxy_add_x_forwarded_for`, appends to whatever the client sent, which made
  even the leftmost read spoofable behind a compliant proxy. Overwrite and
  append shapes both now name the address the proxy saw. The same declaration
  governs the address a session records, since `AuthController` and the limiter
  read through `ClientInfo`.

  `ClientInfoTest` (6 cases) pins both modes, the rightmost hop, the
  empty-header fallback, and the column-width truncation the session row
  relies on. `ForwardedAddressIT` speaks as a direct client with the auth
  limit at 2: two logins from one socket fill its bucket and the third is
  `429` although each carried a different `X-Forwarded-For`; a second socket
  still has its own window. The IT harness declares the trust (it stands where
  the shipped proxy stands), and `RateLimitIT` keeps exercising that topology,
  so the declaration is tested from both sides. Mutation arm: deleting the
  flag check turned the chain IT's third login into `401` — the measured
  bypass — and two unit cases red; restored byte-identical, both green.

  `DEPLOYMENT.md` now writes the header as `$remote_addr` (overwrite) and
  carries `APP_HTTP_TRUST_FORWARDED_FOR=true` as a checklist item;
  `application.yml` binds it with an off default; SECURITY.md's finding #2 and
  PRODUCT.md's summary are rewritten as fixed.)

- [x] **31.5** A production boot cannot open on the repository's published
  secrets.

  (`application.yml` interpolated `JWT_SECRET`, `APP_MAIL_LINK_SECRET` and
  `INTERNAL_API_TOKEN` from the environment but shipped working defaults, and
  `APP_ENV` — already passed by both compose files — reached no backend code, so
  the switch that should have refused a forgotten secret was a no-op. A deploy
  that missed one booted fine on a value printed in this repository: access
  tokens anyone can sign, unsubscribe and mail-settings links anyone can forge,
  and `/internal/*` callable with the shared default. The ai-service had a
  preflight for this class; the backend had nothing before its context existed.

  `app.deployment.env` (`APP_ENV`, `dev` unless set) now arms
  `ProductionGuard`: `env=prod` refuses the refresh when any of the three still
  holds a literal the repository publishes (application.yml's default or
  `.env.example`'s `generate-a-64+char-random-string`), a `CHANGE_ME` value from
  `.env.prod.example`, or nothing at all — every offender named in one message,
  so one restart fixes all three instead of three restarts finding them one by
  one. Non-prod boots are untouched; the examples are what a dev checkout runs
  on.

  `ProductionGuardTest` runs 11 cases: the decision table (dev, ` PROD `, a lone
  override, blank, `CHANGE_ME`), a drift check that reads `application.yml` and
  both env examples so the guard's copies cannot go stale, an
  `ApplicationContextRunner` proving a prod context fails while dev and
  prod-with-real-secrets start, and the `@Component` wiring. Mutation arm:
  replacing the published-set clause with `isEmpty()` turned 5 of the 11 red,
  including the prod context; restored byte-identical, 11/11 green.
  `DEPLOYMENT.md`'s checklist and preflight section and SECURITY.md's finding
  #4 carry the refusal; both compose files already set `APP_ENV: prod`.

  The knob census this unit had to extend was **red at HEAD, and the red was
  31.4's**: `app.http.trust-forwarded-for` had no census entry, and the IT
  harness's array-shaped `@TestPropertySource` — with a comment between its two
  strings — stopped matching the switch scan. The census now reads 29 leaves /
  20 fields / 17 accessor readers, follows the multi-line annotation, and pins
  `APP_HTTP_TRUST_FORWARDED_FOR` out of both env examples by name
  (`DOC_NAMED_VARS`): it is a deployment decision that `DEPLOYMENT.md` carries,
  and the gate reads that document rather than waving the var through. The
  census runs 7/7.)

- [x] **31.6** rep: the censuses the session and security units outran.

  (31.5 closed with one census repaired and the ai-service suite still red in
  four more populations, across five gates. None was a product defect: each was
  a pin that had stopped describing the app while the unit that moved the
  population ran its own green. 30.5's split of `NOT_FOUND` into a session row
  and a mail link added two enum constants and the 404 gate still read
  twenty-nine. 31.4 turned `userOrIp` from a static helper into an instance
  method that reads the declared-proxy switch, and two gates anchored on
  `private static String userOrIp`. 31.2's middleware puts a nonce and a policy
  on the request Next hands its own renderer, and the browser-header census read
  them as headers a browser sends. And 31.4 re-wrapped SECURITY.md's measurement
  so its `RATELIMIT_AUTH_PER_MINUTE=3` row no longer shared a line with the
  sentence that excuses it, stated 429 twice in a file pinned at once, and added
  `app.http.trust-forwarded-for` to a yml whose gate reconciles every read
  against the env examples — which are a checkout's knobs, not a deployment's
  topology.

  The 404 table reads thirty-one constants (one route, thirty record names) and
  the docstring's "thirty places" became thirty-two. Both limiter gates read the
  helper as it is written now. SECURITY.md's second measurement is a site the
  429 census should count, so its pin is two and the floor is the measured nine —
  the setter excluded, five prose sentences and the fixture's four detection
  strings; the measurement sentence and its `=3` figure share a line again, and
  the ledger's dead-entry check still proves it excuses exactly one row. The
  header census refuses `frontend/src/middleware.ts` by name through
  `SERVER_MODULES`, and a control pins the refusal to the file's role: it
  exports Next's middleware, decorates via `NextResponse.next`, sets exactly the
  CSP/nonce pair, sends no fetch/XHR/setRequestHeader, and the pair is absent
  from the fifteen browser sites the census reads; a mutant with a `fetch(...)`
  inserted flips the detector. The env gate gains `DOC_DECLARED`:
  `APP_HTTP_TRUST_FORWARDED_FOR` is reconciled three ways — the yml reads it,
  DEPLOYMENT.md names it, neither example declares it — and a row that loses any
  of the three goes red; DEPLOYMENT.md's "single source of truth" sentence now
  names the exception instead of overclaiming.

  The five gates run 40/40. The full suite at this measurement answers 11
  failed / 1907 passed / 1 skipped, and all eleven are the three
  frontend-reading censuses whose populations moved with the concurrent
  session's in-flight `ingestion.ts`, `source-actions.tsx`, `normalize.ts` and
  `types.ts` — cache writes, failure announcements, response-field contract —
  and are that session's to land. The backend is untouched.)

- [x] **31.7** the production command feeds compose the file it tells you to fill.

  (DEPLOYMENT.md's production Quick Start says to copy `.env.prod.example` to
  `.env.prod`, fill it, and start the stack; the command it printed never passed
  `--env-file`, so compose interpolated the override's values from the process
  environment and the project-directory `.env` — a file the production procedure
  never creates. The `env_file: .env.prod` entries look like they cover this and do
  not: they fill a container after the project renders, while `${...}` is resolved
  before it, and the `environment:` entries carrying those interpolations override
  what `env_file:` supplied. A fresh host therefore started postgres on an empty
  password, redis on `--requirepass ""`, minio on an empty root pair, a backend
  with blank MinIO keys and an empty CORS allow-list, and a frontend bundle
  inlined with an empty API base. The stack came up — open and broken in the ways
  SECURITY.md says it is not.

  All eight values are now `${VAR:?message}`, the message naming both the file and
  the flag, so an unset or empty value stops the render with the fix. `docker
  compose config` proved both arms by hand: green with the eight in the
  environment, and on an empty env file every interpolation stopped the command and
  named its variable. `--env-file .env.prod` is now on the five commands
  DEPLOYMENT.md prints, on the override's own usage header, and on the RUNBOOK's
  six restore lines — two of which (the `exec` and the `ps -q minio` substitution)
  had been driving the development project, because they named neither the
  override nor its file. The nightly backup and the weekly drill build their
  compose argv through a `COMPOSE` array that adds the flag whenever `COMPOSE_FILE`
  names the override; its fragment was executed for the dev, prod and
  absolute-path spellings. The new gate reads the scanner against all three
  compose spellings (comment lines excluded, because the file explains `:?` in
  prose), reconciles the required set with the eight and with `.env.prod.example`'s
  uncommented values, walks the documented commands fence by fence, and pins the
  scripts' one-call rule. Mutation arms: dropping the flag from the Quick Start,
  dropping `COMPOSE_FILE` from the RUNBOOK exec, and respelling one `${VAR:?}` as
  `${VAR}` each turned their case red. The CORS gate's interpolation reader learned
  `:?` — a requirement, not a default — with its own fixture, and the knob census's
  compose-arm reader now accepts the required spelling. The limiter ledger gained
  the one row 31.6's ROADMAP prose had left classified, which the suite found at
  the start of this unit. The affected seven gates run 55/55; the full suite answers
  11 failed / 1913 passed / 1 skipped, and the eleven are the same three
  frontend-reading censuses (cache writes, failure announcements, response-field
  contract) that the concurrent session's in-flight files keep red and that are
  that session's to land. The backend is untouched.)

- [x] **31.8** a production boot refuses the console mail transport.

  (`app.email.provider` defaults to `console`, and both `application.yml` and
  `.env.example` ship that default. `.env.prod.example` sets `smtp` and the
  production checklist names the knob, but nothing refused a boot that kept the
  default: the stack came up healthy, answered "check your email" to a password
  reset, and wrote the letter into the log — with the console transport's body
  withheld by default, not even the link was there. Every reset of such a
  deployment was a silent loss, discovered only by the user who could not get
  back into the account.

  `ProductionGuard` now refuses `APP_EMAIL_PROVIDER` alongside the three
  published secrets when `APP_ENV=prod`; a blank value is refused too, because
  the interpolation's own default is console. The refusal joins the same
  offender list, so one restart names the knob with the secrets. `smtp` keeps
  its own requirement — a host and a from address, `EmailConfig` — and there is
  no opt-out: a production deployment that cannot send mail cannot run the
  password-reset flow, and console is exactly the state the checklist warns
  about. Non-prod boots are untouched; console is what a dev checkout runs on.

  `ProductionGuardTest` grew from 11 to 15 cases: console, `" CONSOLE "`,
  blank and null in the decision table, dev untouched on console, a drift check
  that reads `APP_EMAIL_PROVIDER` out of `application.yml`, `.env.example` and
  `.env.prod.example` (the first two must be refused, the third must not), and
  an `ApplicationContextRunner` arm where real secrets plus console fail naming
  only `APP_EMAIL_PROVIDER`, while real secrets plus `smtp` start. Mutation arm:
  forcing the console predicate to `false` turned 4 of the 15 red; restored
  byte-identical (sha1), 15/15 green. The context arms assert the exact
  offender list through `NestedExceptionUtils.getMostSpecificCause` — a
  `hasStackTraceContaining("APP_EMAIL_PROVIDER")` passed even with the check
  disabled, because the guard's own message ends "…and APP_EMAIL_PROVIDER=smtp
  with a relay".

  `application.yml`'s comment, the production checklist item, DEPLOYMENT.md's
  preflight paragraph and Email section, and SECURITY.md's finding #4 carry the
  refusal. The backend suite answers 894 tests, 0 failed (ITs included); the
  ai-service suite answers 11 failed / 1913 passed / 1 skipped, and the eleven
  are the same three frontend-reading censuses the concurrent session's
  in-flight files keep red.)

- [x] **31.9** a production boot refuses the database and object-store defaults.

  (`application.yml` ships `POSTGRES_PASSWORD: dev_pg_pass_9f3k` and
  `MINIO_SECRET_KEY: careeros_minio_dev_password`, and both env examples ship
  `change-me` trio values; a prod boot that forgot either credential reached
  production's Postgres and bucket on a password this repository prints. The
  MinIO user name is different in kind: an access key is a user name, so the
  shipped `careeros-minio-admin` stays allowed and only a placeholder
  (`change-me`/`CHANGE_ME`) or an empty name is refused.)

  `ProductionGuard` now builds one ordered map — JWT, mail-link, internal token,
  `spring.datasource.password` (through `@Value`, since it is not an `app.*`
  key) and the MinIO pair from `AppProperties` — and hands it to the same pure
  `offenders(env, transport, map)`. The pair is asked for unconditionally: the
  census forbids the property object as a second reader of the storage switch
  (the bean condition decides it), and a prod boot with the store switched off
  has no `StorageService` bean to inject anyway — four services require one — so
  turning the switch off cannot dodge the check. Values added to `PUBLISHED`:
  `dev_pg_pass_9f3k` and `change-me` for the database, `change-me` and
  `careeros_minio_dev_password` for the store. The refusal message now names up
  to seven offenders in one sentence.

  `ProductionGuardTest` grew from 15 to 18 cases: the decision table covers the
  shipped database and store defaults, a published user name over a real secret
  (allowed), and the `CHANGE_ME`/blank arms extended to six credentials; the
  drift arm reads `POSTGRES_PASSWORD`, `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY`
  out of `application.yml` (two offenders — the user name is allowed),
  `.env.example`'s trio (three) and `.env.prod.example` through the
  `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD` mapping compose applies (two); the
  context arms assert the exact seven-name prefix, keep console-alone isolated,
  and add a storage-off boot that still fails naming only the pair. Mutation
  arms: dropping the two MinIO puts from the constructor turned 2 of 18 red
  (the context arms); dropping the published-literal lookup turned 7 of 18 red;
  restored byte-identical (sha1 934baf5c…), 18/18 green.

  The knob census learned the pair's second reader (`config/ProductionGuard.java`
  beside `storage/MinioStorageService.java`) and judged a fourth flat
  the storage switch's row — the new test spells the switch to prove a store-off
  boot is still refused. `application.yml`'s datasource and storage blocks,
  the DEPLOYMENT checklist item and preflight paragraph, and SECURITY finding #4
  (six values, the unconditional pair, 18 cases) carry the refusal. The backend
  suite answers 897 tests, 0 failed (ITs included); the ai-service suite answers
  11 failed / 1913 passed / 1 skipped, and the eleven are the same three
  frontend-reading censuses the concurrent session's in-flight files keep red;
  the 32 doc-reading gate files answer 238/238.)

- [x] **31.10** a production boot mails links the reader can open.

  (`app.web.base-url` defaults to `http://localhost:3000`, and
  `.env.prod.example` ships `https://your-domain.com`; every password-reset,
  email-change and unsubscribe link is built from that one value (`AuthService`,
  `EmailChangeService`, `MailLinks`). A prod boot that forgot the knob mailed its
  readers a link to their own machine, and a boot that kept the example's value
  mailed every reset and confirmation token to whoever owns `your-domain.com`.)

  `ProductionGuard` now asks for the link base too: `WEB_BASE_URL` joins the
  ordered map through `@Value("${app.web.base-url:http://localhost:3000}")`, and
  its check is the one with a shape rule beside the literal lookup. The shipped
  loopback default and the example's literal sit in `PUBLISHED`;
  `isUnreachableBaseUrl` additionally refuses a value that is not an http(s) URL,
  whose host is loopback (`localhost`, `*.localhost`, `127.*`, `[::1]`,
  `0.0.0.0`), or whose host is `your-domain.com` under any scheme, trailing slash
  or `www.` prefix — a copying operator is as likely to keep the domain as the
  literal. The refusal names the base in the same offender list, so one restart
  still fixes everything.

  `ProductionGuardTest` grew from 18 to 23 cases: three decision-table arms — the
  loopback spellings (seven), broken spellings (empty, spaces, a bare host, ftp,
  `not a url`, `http://`), and the example domain's four spellings — and a drift
  arm that reads `APP_WEB_BASE_URL` out of `application.yml`, `.env.example` and
  `.env.prod.example` (all three refused). The context arms: a prod boot with
  real secrets on loopback names only `APP_WEB_BASE_URL`, the all-offenders arm's
  exact prefix now carries eight names, and every other prod arm pins a real
  public base. Mutation arm: forcing `isUnreachableBaseUrl` to `false` turned 3
  of 23 red — the three decision-table arms; the loopback context arm stayed
  green because its `http://localhost:3000` is in `PUBLISHED` too, which is the
  point of the two layers. Restored byte-identical (sha1 b9e0fe10…), 23/23 green.

  `application.yml`'s `web` block carries a comment; the DEPLOYMENT checklist,
  preflight paragraph and Email section, and SECURITY finding #4 (the base URL,
  23 cases) state the refusal. The deployment-doc gate caught the first drafts'
  quantifiers ("only the server or nobody can open", "console-alone"): beside a
  loopback mention they claim the whole stack, so both sentences were reworded.
  No census file changed — `app.web.base-url` was already bound through `@Value`
  outside AppProperties, and the knob census is keyed by the key's name. The
  backend suite answers 902 tests, 0 failed (ITs included); the ai-service suite
  answers 11 failed / 1913 passed / 1 skipped, and the eleven are the same three
  frontend-reading censuses the concurrent session's in-flight files keep red;
  the 32 doc-reading gate files answer 238/238.)

- [x] **31.11** a production boot admits the shell the browser loads.

  (`app.cors.allowed-origins` defaults to `http://localhost:3000`, and the browser
  compares its `Origin` header to the allow-list literally. A prod boot that kept
  the default served the shell and refused the API call behind each page — healthy
  in the logs, unusable in the browser. The prod example's
  `https://your-domain.com,https://www.your-domain.com` had the same ending until
  replaced, and an origin pasted from the address bar (`https://app.example.com/`,
  a path, a query) never equals an Origin, so it sat in the list and matched
  nothing.)

  `ProductionGuard` now reads the allow-list (`AppProperties.Cors`) and names it in
  the same offender list, after the link base. Its rule is stricter than the link
  base's: every comma-separated entry must be a bare public http(s) origin — no
  blank entry, `CHANGE_ME`, loopback or example-domain host, no path, trailing
  slash, query or userinfo, because Spring compares the header to the string and a
  spelling the header cannot carry matches nothing. A well-formed list also has to
  name the shell's own origin, built from `APP_WEB_BASE_URL` (lowercased scheme and
  host, port only when the value carries one), because that is where the mailed
  links open. When the base is itself an offender the shell rule is skipped — the
  operator is about to change it, so judging the list against the old value would
  only add noise. The refusal message now sends the operator to the shell's origin.

  `ProductionGuardTest` grew from 23 to 27 cases: the dev and example lists in
  fourteen spellings (loopback, example domain, blank, `CHANGE_ME`, bare host, ftp,
  trailing slash, path, query, one bad entry beside a good one), the public-list
  arm including an uppercase host, which is the same origin; a public list that
  does not name the shell (a sibling subdomain, a different port, a different
  scheme); a drift arm reading `APP_CORS_ORIGINS` out of `application.yml`,
  `.env.example` and `.env.prod.example` (all three refused); a context arm where
  real secrets plus the dev list fail naming only `APP_CORS_ORIGINS`, and the
  all-offenders arm's exact prefix now carries nine names. Mutation arm: disabling
  the CORS branch turned 5 of 27 red — the four CORS arms and the nine-name prefix;
  restored byte-identical (sha1 5951aa57…), 27/27 green.

  The knob census learned the allow-list's second reader
  (`config/ProductionGuard.java` beside `config/SecurityConfig.java`).
  `application.yml`'s `cors` block, the DEPLOYMENT checklist item and preflight
  paragraph, and SECURITY's transport bullet and finding #4 state the refusal. The
  backend suite answers 906 tests, 0 failed (ITs included); the ai-service suite
  answers 11 failed / 1913 passed / 1 skipped, and the eleven are the same three
  frontend-reading censuses the concurrent session's in-flight files keep red; the
  doc-reading gate selection answers 238/238.)

- [x] **31.12** a browser is told the shell speaks https only.

  (The shell's answers said what a page may frame, sniff, load and run, and the
  API's door named the shell; the transport the first answer arrived on was still
  whatever the visitor typed. A reader who reached the http spelling once — a typed
  address, a link in a letter, a bookmark saved before TLS — kept being served over
  http until they noticed, and a network in between could rewrite pages and API
  calls wholesale. Browsers offer one defense: a host that answers over https with
  `Strict-Transport-Security` is pinned, and every later spelling of it is upgraded
  before a byte leaves the browser. The shell sent none of it.)

  The header rides the same one exported list in `frontend/next.config.ts` as the
  other four, so every `/:path*` answer carries it. Its value is exactly one
  directive, `max-age=31536000`: a year of pinning and nothing else on purpose.
  `includeSubDomains` would extend the promise to hosts under the shell's own name
  that this repository does not know the operator runs, `preload` is a commitment
  only the operator can make for a hostname they own, and a reverse proxy may add
  both around the app. STS delivered over http is ignored by browsers, so the
  plain-http dev runs and the E2E stack are untouched — the header costs them
  nothing and protects every https deployment, including the ones served by
  `next start` with no proxy to add it.

  The gate grew a second case: the exact five-header array for `/:path*` (a sixth
  header added to the list cannot skip the rule; a rule that stops carrying the list
  is a red), and a transport case that parses the value as `max-age=\d+` only — an
  accidental `includeSubDomains`, `preload` or `max-age=0` cannot arrive unnoticed —
  and floors the year at 31536000 seconds. Mutation arm: deleting the entry turned
  both cases red; restored byte-identical (sha1 82954f1e…), 2/2 green. Verified live
  against a dev server on a fresh port: a `200` from `/` carried all five headers,
  HSTS last, under the existing policy and nonce; `tsc` and ESLint stayed clean, and
  the full frontend suite answers 800 tests, 799 passed, the one red the concurrent
  session's in-flight `endpoints.test.ts` parity case. The doc-reading gate
  selection answers 238/238 after SECURITY's new prose.

  `docs/SECURITY.md`'s shell-headers bullet names the value, the one-year pin and
  why the two stronger directives are the operator's to add; `csp.ts`'s comment now
  counts five headers.)

- [x] **31.13** the shell stops naming its framework and keeps no handles.

  (Two things were still volunteered on every answer. `X-Powered-By: Next.js`
  named the framework and gave a version fingerprint no reader uses. And a page on
  another origin that opened the shell in a new window kept a handle on that
  window — enough to steer it later or time what it loaded. Neither is a page
  behavior; both are facts the answer gave away.)

  `next.config.ts` sets `poweredByHeader: false`, so the banner is gone from every
  route, and the one exported header list gained the isolation pair:
  `Cross-Origin-Opener-Policy: same-origin` severs a cross-origin opener's link to
  a shell window, and `Cross-Origin-Resource-Policy: same-origin` refuses another
  origin the shell's answers as subresources of its own. Same-origin windows and
  fetches are untouched — the app's print window, its chunks, the manifest, the
  worker's own cache writes — and a reverse proxy may add its own around the app.

  The gate now has three cases: the exact seven-header array for `/:path*`, a
  `poweredByHeader: false` case, and the transport rule's shape. Mutation arm:
  deleting the `poweredByHeader` line turned 1 of 3 red — the banner case, since the
  array and the transport rule know nothing about it; restored byte-identical
  (sha1 8ae616b2…), 3/3 green. Verified live against a dev server on a fresh port:
  a `200` from `/` carried all seven headers and no `X-Powered-By`; `tsc` and
  ESLint stayed clean, and the full frontend suite answers 801 tests, 800 passed,
  the one red the concurrent session's in-flight `endpoints.test.ts` parity case.
  The doc-reading gate selection answers 238/238.

  `docs/SECURITY.md`'s shell-headers bullet names the pair and the banner switch;
  `csp.ts`'s comment counts seven headers.)

## Epic 32 — The Answer Leaves a Trail

Epic 20 taught the deployment to page itself, but every alarm it added points at a
window of time, not at one request. A report that arrives as "the export failed at
14:03" still had to be matched against a minute's worth of log lines, and the
refusals that arrive without a session — a `401`, a `429` — carried nothing a
reader could quote back. This epic gives every answer an id, writes the same id on
the lines it logs, and carries it to the services and screens the answer touches,
so one grep reconstructs one request.

- [x] **32.1** An answer and its log lines share one id.

  (`backend/src/main/java/com/careeros/common/RequestIdFilter.java` runs at
  `Ordered.HIGHEST_PRECEDENCE`, ahead of the security chain, so the `401`s and
  `429`s that never reach a controller carry the id too. The value is the caller's
  own `X-Request-Id` when it is 8–64 characters of `[A-Za-z0-9._-]` and starts
  with a letter or digit; anything else — an empty string, a space, a line break,
  `%0d%0a`, 65 characters — is replaced by a fresh UUID rather than refused,
  because the id is diagnostics, not a credential. The response header is set
  before the chain runs, so an error handler and the log agree on one value, and
  the MDC entry is removed in a `finally` so a pooled thread never carries one
  request's id into the next. `application.yml`'s console pattern gained
  `[%X{requestId:-}]` — boot lines and scheduled sweeps print an empty bracket —
  and `SecurityConfig` exposes `X-Request-Id` through CORS so the browser can
  quote it from a failed call.

  `RequestIdFilterTest` holds three cases: a minted id is already on the response
  and in the MDC while the chain runs and gone afterwards; four well-formed
  caller ids are echoed (including a 32-hex trace id and the 64-character
  ceiling); eight malformed ones are replaced. `RequestIdIT` pins the same
  promise through the real security chain: an unauthenticated `401` carries a
  UUID, a caller id is echoed and listed in `Access-Control-Expose-Headers` for
  the shell's origin, and a malformed id still answers `401` with a replaced id.
  Mutation arm: deleting the `response.setHeader` line turned all six red (3
  unit + 3 IT); restored byte-identical (sha1 2a3c1381…), 6/6 green. The full
  backend suite answers 912 tests, 0 failures, 0 errors, 0 skipped. The
  doc-reading gate selection answers 238/238 after the two doc edits.

  `docs/RUNBOOK.md` gained "A reader quotes one request" — asking for the header,
  what the bracket looks like, and why an empty bracket is a scheduled line — and
  `docs/API.md` its correlation convention.)

- [x] **32.2** The id crosses into the ai-service.

  (Every backend call to the ai-service — the typed `/internal/*` routes through
  `HttpAiServiceClient` and the SSE relay — now sends the request's id as
  `X-Request-Id`. The ai-service's new `app/core/request_id.py` middleware echoes
  it on the answer, keeps it in a `ContextVar` while the request runs, and the
  JSON formatter writes it as `request_id` on every line logged in that scope; the
  variable is reset in a `finally` so a reused task does not inherit it. The
  middleware accepts the same 8–64-character alphabet the backend accepts and
  replaces anything else with a fresh UUID, so a value quoted across two logs is
  always one line long and the id never changes the status a route answers.

  The SSE relay hands the upstream read to a task executor, and MDC is a
  thread-local: the id would have been lost on exactly the long calls that need
  it. `relay` captures it on the request thread and puts it back on the worker for
  the duration of the pump, removing it in a `finally`. Calls made outside a
  request (the nightly report, the embedding pass) send no header; the ai-service
  mints one for its own lines.

  Gates: `HttpAiServiceClientTest` gained two cases over its real socket — a
  request-thread id arrives at the upstream, and a call outside a request carries
  none — and the new `SseRelayServiceTest` proves the id survives the hop onto a
  real second thread and that the worker keeps none afterwards. On the ai-service
  side, `test_the_id_the_backend_sends_is_the_id_the_service_logs.py` holds five
  cases: the answer echoes a well-formed id, a malformed one is replaced without
  changing the status, the id is in scope only while the request runs, a line
  logged inside the request carries it, and a line outside any request has none.
  Mutation arms: deleting the RestClient interceptor turned 1 of 16 red (the
  forwarding case only); dropping the relay's cross-thread copy turned 1 of 2 red;
  removing the middleware's `ContextVar.set` turned 4 of 5 red. All restored
  byte-identical (sha1 b968efac…, 2eba47e9…, 603f4670…), all green. The full
  backend suite answers 916 tests, 0 failures, 0 errors, 0 skipped. The full
  ai-service suite answers 14 failed, 1915 passed, 1 skipped — every red the
  concurrent session's in-flight frontend files; one census this unit moved was
  updated: `test_file_key_composers.py` now names `RequestIdFilter.java` among the
  UUID mints (a fifth, composing no key). The doc-reading gate selection answers
  235 of 238, the three reds the concurrent session's in-flight
  `test_response_shape_contract.py`.

  `docs/RUNBOOK.md`'s correlation section gained the boundary paragraph: the same
  id crosses to the ai-service, appears as `request_id` in its JSON lines, and a
  scheduler-minted id appears only there.)

- [x] **32.3** Every answer leaves one access line.

  (The id joined the lines a request chose to write, but a slow request that logged
  nothing still had to be found by hand. `RequestIdFilter` now writes one line per
  answer to the `careeros.access` logger — `GET /api/v1/jobs 200 37ms` — under the
  id the console pattern already prints. A chain that throws logs `error` in the
  status slot rather than a number, because the container's 500 is decided after the
  filter unwinds and a number there would be one the answer never ends up carrying.
  The query string is deliberately omitted: a search term is the reader's text and a
  reset flow carries a token, and neither belongs in every log file.

  `RequestIdFilterAccessLogTest` pins the sentence shape through a Logback appender
  — method, path, status and a millisecond figure — asserts the event's MDC carries
  the id the answer carries (the line is written before the MDC is cleared), proves
  `?q=my-private-search&token=secret` never reaches the line, and that a throwing
  chain still leaves its `error` line and clears the id. Mutation arm: deleting the
  `writeAccessLine` call turned 3 of 4 red (the throwing case still logged); restored
  byte-identical (sha1 762b7ca5…), 4/4 green. The full backend suite answers 920
  tests, 0 failures, 0 errors, 0 skipped, and the suite's own run wrote 401 access
  lines in the shape the case pins.

  The doc-reading gate selection answers 235 of 238, the three reds the concurrent
  session's in-flight `test_response_shape_contract.py`. `docs/RUNBOOK.md`'s
  correlation section now shows the line and says what the status column means and
  what is never printed.)

## Epic 33 — The Bell Rings Without the Tab

The bell already carries a count on every page (29.3), and the morning letter
carries the inbox out of the app (22.1) — but both assume something is looking: a
tab holding a session, or a mailbox being read. A reader who closes the laptop
learns nothing until they come back, and the saved search that found three
postings overnight has no way to say so. This epic gives the account a Web Push
address: the browser hands the service its subscription, a VAPID-signed push
wakes the installed worker, and the worker shows one sentence and opens the
inbox; the tab it opens asks the app what is new. The push itself carries no
payload, and the worker holds no account token — one browser can have tabs open
under different accounts, and a token replayed from a worker would revoke the
family the page is still using — so no signal text, saved-search name, count or
name transits a push service and a wake can never show one account's inbox on
another account's tab.

- [x] **33.1** A browser can hand the account its push address.

  (`V24__push_subscriptions.sql` keeps one row per browser registration — the
  endpoint, the two keys a push service needs, an optional label, and the account
  it currently rings. The endpoint carries the table's unique constraint, not the
  caller: a browser is one registration, so a second reader signing in there
  re-points the row rather than adding a second one, which would ring that browser
  twice for one morning. Four routes under `/push/subscriptions`: list the
  caller's registrations, register (an upsert on the endpoint that refreshes the
  keys and re-points the owner), forget one, and forget every device.

  Validation lives in the service, not only in bean validation, because the
  service is the boundary that stores the text: an endpoint must parse, be
  `https`, name a host, carry no userinfo or fragment and stay within 2048
  characters; a key must be unpadded base64url of the size a P-256 point and a
  16-byte secret have. Anything else is `PUSH_SUBSCRIPTION_INVALID` — refused
  here rather than stored and discovered by a failing send at 08:00. An account
  keeps at most ten browsers, the same bound the feed and saved-search lists
  carry, and the cap cannot refuse a registration the account already keeps
  because the upsert is checked first.

  Gates: `PushSubscriptionServiceTest` holds eight cases (stored under the
  caller with padding trimmed; re-registration moves and refreshes the row without
  asking the cap; the eleventh browser is refused; the cap does not refuse an
  endpoint already kept; six unwakeable endpoints refused; five malformed keys
  refused; another account's row is a 404; forgetting all stays inside the
  caller), and `PushSubscriptionControllerTest` eight more over the routes,
  including ownership on list/delete-all and both own refusal codes.
  `ApiErrorCodeCensusTest`'s frozen name list gained the three new codes on
  purpose. Mutation arm: deleting the upsert branch turned 2 of 16 red (the
  re-registration and the cap-does-not-refuse-a-kept-registration cases);
  restored byte-identical (sha1 0f053f72…), 16/16 green. The full backend suite
  answers 936 tests, 0 failures, 0 errors, 0 skipped, Flyway applying V24 in the
  IT harness. `docs/API.md` gained the route table and the no-payload rule, and
  `docs/architecture.md`'s section 4.7 the table's row.

  The doc-reading gate selection answers 234 of 238. Three reds are the concurrent
  session's in-flight frame-parser cases; the fourth is that same file's record
  census, pinned at 170 and now reading 172 — this unit's two DTO records. The pin
  lives in the concurrent session's uncommitted file, so it is recorded here as
  debt and moves when that file lands rather than being folded into this commit.
  One gate did change this unit's code: `test_a_configured_knob_that_no_code_reads`
  resolves a lone `getEndpoint()` call to the storage knob, so the entity's accessor
  is `getEndpointUrl()` and the column is still `endpoint`.)

- [x] **33.2** A signed push leaves the building.

  `push/service/PushSender` is the port: one registration in, one
  `SENT`/`GONE`/`REFUSED`/`NOT_CONFIGURED` out. `VapidWebPushSender` is the RFC
  8030/8292 transport -- an empty `POST`, an ES256 JWT whose `aud` is the
  endpoint's *origin* (scheme, host and port; the path is the registration), the
  deployment's public key as `k`, and a `TTL` header of half a day by default. The
  push says only "there is news"; no payload and no encryption, so the content is
  fetched by the worker from the authenticated inbox and the push service learns
  nothing but that the browser exists. A `404`/`410` answers `GONE` and the caller
  prunes the row; every other status, a timeout and an unreachable service answer
  `REFUSED` -- counted, never retried inside the pass, and never thrown out of the
  port, because the sweep walks many browsers and one dead one must not stop the
  rest. With no VAPID key pair configured the bean is a `NoopPushSender` that
  reports "not configured" (registrations stay, so keys arriving later still
  reach browsers that opted in early) and the boot logs the reason.

  `VapidKeys` reads the two halves in the formats the ecosystem hands them over
  in -- an uncompressed P-256 point and a 32-byte scalar, with PKCS#8 accepted for
  the private half -- and refuses a mismatched pair with a probe signature, the
  only check that can see two well-formed halves from different key pairs. A boot
  with one half of the pair is refused (`PushConfig`), and so is a TTL outside
  RFC 8030's four-week ceiling. `app.push.contact` is RFC 8292's `sub`; empty
  falls back to the deployment's public web origin.

  Gates: `VapidKeysTest` 8 (raw and PKCS#8 halves, padding, a mismatched pair, a
  wrong-length point, non-base64url, a half pair, a private key that is neither
  scalar nor PKCS#8), `VapidWebPushSenderTest` 7 (the signed empty POST with
  method/TTL/headers/body and the token's header, `aud`, `sub` and lifetime
  verified with the public key; a non-default port in `aud`; 404 and 410 as
  `GONE`; 400/401/403/429/503 as `REFUSED`; a non-https endpoint refused without
  a request; the boot refusals; the origin derivation) and `PushConfigTest` 6
  (no keys, half a pair either way, a real pair, the contact fallback, the TTL
  bounds, a malformed and a mismatched pair) -- 21 new tests. The knob gate moved
  with the configuration: 33 `app:*` leaves, 21 accessor readers, 24 leaf fields,
  and the four push keys pinned to `PushConfig` as their only reader. No DTO
  records were added, so the 172-record census is unchanged. `docs/API.md`,
  `docs/architecture.md` 4.7, `docs/DEPLOYMENT.md`'s checklist and both env
  examples carry the new knobs. The backend's non-IT suite answers 872 tests, 0 failures.

- [x] **33.3** The morning sweep rings as well as writes.

  `V25` gives `notification_states` a `pushed_at`: the ring is the second door out
  of the app, so it gets the episode's second latch rather than sharing the
  letter's. `NotificationService.awaitingPush` answers what the inbox is showing
  that is unread, undismissed and not yet pushed -- the mail latch is deliberately
  not consulted, because a reader who turned the letter off still asked to be
  woken, and a mailed episode nobody has opened the app for is exactly what a ring
  is for -- and `markPushed` writes the latch per episode, so a new signal arrives
  under a new key with none.

  `NotificationPushService` rides the 07:30 clock after the letters. Its audience
  is every account with a registration (`distinctUserIds` on the push table); the
  browser is this door's consent, so the mail stop list is never read. One
  waiting morning is one coalesced wake fanned to each of the account's browsers,
  not one per item, and the latch is written only when at least one browser
  accepted -- a morning where every registration refused is tried again rather
  than remembered as rung, and a deployment whose sender is the no-op reports
  `not_configured` and latches nothing, so keys arriving later still reach the
  episodes nobody saw. A `GONE` registration is deleted on the spot, because a
  push service that retired it will say so every morning. `PushDeliveryMetrics`
  carries one counter, `careeros.push.delivery`, tagged `sent` / `gone` /
  `refused` / `not_configured`; there is no second pass marker, because the ring
  shares the letters' pass and that pass's own gauge already answers whether the
  clock ran. The scheduler catches the two halves separately: a relay that refuses
  every letter does not silence the ring, and a hanging push service does not cost
  the morning its letters.

  Gates: `NotificationPushServiceTest` 8 (one wake per browser and one latch per
  episode; nothing waiting costs no call; a `GONE` row deleted and a refusing
  morning not latched; one acceptance enough to latch; a refused morning asked
  again; no keys latches nothing; a vanished registration skipped; one bad account
  does not stop the others), `PushDeliveryMetricsTest` 2, `NotificationServiceTest`
  +3 (a mailed but unread episode still rings; only unread/undismissed/unpushed
  travels; a rung episode is not rung twice and is still unread in the app) and
  `NotificationMailSchedulerTest` 3 (both halves in order, a failed letter sweep
  still rings, a failed ring is swallowed). The full non-IT backend suite answers
  886 tests, 0 failures. The full run also caught a flake outside this unit: a
  Micrometer gauge keeps its object weakly, and two tests discarded the metrics
  instance they had just built, so a collection under load answered `NaN`;
  `RetentionSweeperTest` and `AiUsageMetricsTest` now hold the instance for the
  read. `test_response_shape_contract`'s run-stream interval census grew by one row
  (the ring's class comment says why there is no second marker; nine Java rows), and
  the knob census is unchanged -- no new settings. `docs/API.md` and
  `docs/architecture.md` 4.7 carry the sweep and the migration.

- [x] **33.4** The worker wakes, asks and opens.

  (`public/sw.js` answers `push` with one notification — one sentence in the
  browser's language, one bubble tagged `careeros-inbox`, the install icon and
  badge, deep-linked to `/notifications` — and `notificationclick` focuses a tab
  already on that path or opens one. The worker holds no token by design: a
  refresh token replayed from a worker would revoke the family the page is still
  using, and one browser can have tabs open under different accounts, so the
  notification carries no count, title or name and the tab it opens reads the
  authenticated inbox itself. `pushsubscriptionchange` re-subscribes with the old
  key and messages the new registration to any open tab, which upserts it; with
  no tab open the message is lost and the switch's next visit re-registers what
  the browser holds.

  `lib/push.ts` is the browser's half as pure functions — the public key trimmed
  out of the build, base64url to bytes, the three-field record, the five states a
  switch can read, permission before subscribe, opt-out — and `lib/hooks/push.ts`
  is the account's half: the upsert, the one-row forget (never the whole list,
  because another browser's row is another browser's consent), and the
  read-then-write repair. `components/settings/push-card.tsx` is the switch: it
  re-reads the browser on mount, asks permission on the reader's gesture,
  subscribes with `NEXT_PUBLIC_VAPID_PUBLIC_KEY`, rolls the local subscribe back
  when the registration fails, and on opt-out unsubscribes and deletes this
  browser's row. Compose passes `APP_PUSH_VAPID_PUBLIC_KEY` into the frontend
  build arg in both compose files, so one variable fills both halves; empty
  leaves the switch off with a sentence that says so.

  Gates: `push.test.ts` 27 (the key's alphabet and trimming, the record's three
  fields, every state the switch can read, permission before subscribe, an
  existing subscription kept rather than doubled, a refused prompt / failed
  subscribe / failed unsubscribe as sentences, opt-out twice, a renewal's type
  and shape, the handler's filters and clean-up), `pwa.test.ts` +1 (the worker's
  three handlers, the deep link, both languages, no token and no `fetch` in the
  wake path), `endpoints.test.ts` drops the two `NEVER_REFERENCED` entries whose
  caller now exists. The copy census moves to 136 browser sources. `npx tsc
  --noEmit` is clean and the frontend suite answers 829 tests in 77 files, 0
  failures. `docs/API.md`, `docs/architecture.md` §4.7, `docs/DEPLOYMENT.md` and
  the root env examples carry the build-time key.)

## Epic 34 — The Reminder Leaves the App

Every time on this board lives only inside the product: `reminder_at` turns a row
red on the dashboard at its hour, and nothing else on the reader's phone knows.
The calendar is the one app already open, already synced, already shared with a
partner — and it cannot be told about an account, because it cannot sign in. This
epic gives the reminders an address: a read-only signed URL a calendar client
subscribes to, and a settings card that shows it once and says plainly that the
URL is the credential. The signature is the same HMAC secret the letters'
unsubscribe links use, under a purpose of its own, so one leaked link cannot
stand in for the other; rotating the secret retires both families at once.

- [x] **34.1** The account's reminders leave as a calendar feed.

  `common/SignedLink` is the signature both link families now share —
  HMAC-SHA256 over `purpose + account id`, URL-safe and unpadded, verified in
  constant time and answering false rather than throwing on anything the open
  internet can send; `MailLinks` delegates to it unchanged in behavior, and
  `CalendarLinks` signs `careeros-calendar:` so a mail token cannot open a feed
  and a feed token cannot flip a mail switch. A blank `app.mail.link-secret`
  stops the boot. `CalendarLinks.token` is `<account id>.<signature>`, so the id
  is readable but worthless without the MAC; `account` answers null for a
  missing, truncated, re-signed or retired URL.

  `CalendarService.feed(account, locale)` reads the rows carrying a
  `reminder_at` through `findByUserIdAndReminderAtIsNotNullOrderByReminderAtAscIdAsc`
  and hands them to `CalendarFeed.render`: one `VEVENT` per row, `UID`
  `<application id>@careeros` so a re-subscription updates rather than
  duplicates, `DTSTART` the reminder in UTC, a fixed 30-minute `DTEND`,
  `DTSTAMP` from the row's own `updated_at` (its creation, then the reminder,
  when a row is unstamped) so an unchanged board renders byte-identically,
  `SUMMARY` company and title joined by a middle dot (the role alone when no
  company was recorded), `DESCRIPTION` and `URL` pointing at the apps list, and
  `TRANSP:TRANSPARENT` so a reminder does not mark the reader busy. TEXT values
  escape backslash, newline, semicolon and comma; every content line folds at 75
  UTF-8 octets without splitting a code point, which is where a Chinese company
  name and a parser meet. Past reminders stay: the feed mirrors the board, so an
  event leaves when the reader clears the reminder, not when the date slips by.
  The calendar's name and note follow the account's locale.

  Two routes. `GET /calendar/link` is the signed-in half the settings card
  reads; `GET /calendar.ics` is the anonymous half — permitAll for that one path
  only — answering the document itself as `text/calendar;charset=UTF-8` with
  `Cache-Control: no-store` and `X-Robots-Tag: noindex`, because the body names
  the reader's applications. The envelope's `byte[]` passthrough is what keeps a
  calendar client from rejecting a wrapped feed. An unreadable token, a token
  signed for another account, a retired secret and a token naming an erased
  account are one 404 `CALENDAR_LINK_INVALID` with one sentence, so the internet
  cannot grade its guesses; the code joined the frozen enum census, the 404
  ledger and the browser's copy table.

  Gates: `CalendarFeedTest` 9 (one event per reminder with UID, UTC start,
  half-hour end, summary, way back and transparency; a past reminder still
  listed; a company-less row named by its role; the four escaped characters;
  both languages' name and note; an empty feed still a valid calendar; the stamp
  from `updated_at` with both fallbacks; a folded Chinese title under 75 octets
  per physical line and unfolding back to itself), `CalendarLinksTest` 7 (one
  account one address, another another; forged, truncated, empty, null,
  non-base64 and rotated-secret tokens all null; a well-shaped token with an
  unknown MAC null; mail and calendar tokens refused by each other's reader;
  absolute address and trailing slash; blank secret refuses the boot),
  `CalendarControllerTest` 6 (the document raw with no-store and noindex; the
  account's locale reaching the service; forged, foreign, unreadable and missing
  tokens all the same 404 with no service call; an erased account the same 404;
  the signed-in account handed the address that signs back to it; no session, no
  address). Twenty-two tests. Mutation arm: `account` returning the parsed id
  without checking the MAC turned 3 of 13 red — two `CalendarLinksTest` cases
  and the controller's forged-token case, answered 200 — and the restored file
  is byte-identical (sha1 607bd77b…).

  Measured on the committed tree: the backend answers 993 tests including the
  real-stack ITs with 0 failures, 0 errors and 0 skipped (`mvn -o -q test`; the
  non-IT selection alone is 908), the frontend answers 831 tests in 78 files,
  `npx tsc --noEmit` is clean and `eslint` reports 0 errors (one pre-existing
  unused-import warning in `memory-card.tsx`). The first full run's single red
  was `RateLimitIT`'s AI-window case — its 31-request loop straddling a
  wall-clock minute boundary under load; the class answers 4/4 alone and the
  re-run is 993/0/0.

  The doc-gate selection answered 74 tests with one red: `types.ts`'s union pin,
  which the concurrent lane's `CalendarLinkRow` had moved eleven lines; re-aimed
  with the reason. The same selection exposed drift the push units outran, and
  this unit repaired it in passing: the message-token census's twenty rows (the
  worker's DOM `message` event classified as `dom-event-name`), the lifetimes
  census's fourth TTL field (`presignedUrlTtlSeconds`) and the VAPID comment's
  bare "24 hours" reworded off the ledger, the prod command's optional
  `NEXT_PUBLIC_VAPID_PUBLIC_KEY` build arg declared as the one defaulted
  interpolation, and `PUSH_SUBSCRIPTION_NOT_FOUND` missing from the 404 ledger.
  `docs/API.md`, `docs/SECURITY.md`, `docs/DEPLOYMENT.md` and
  `docs/architecture.md` §4.7 carry the route, its semantics and the rotation
  meaning. The browser's copy line for `CALENDAR_LINK_INVALID` landed with 34.2's
  card in the same commit: one file carries both the error table and the card's
  sentences, so splitting it would have been two commits over one writer's hand.

- [x] **34.2** The settings page hands out the calendar address.

  Settings gained a card that asks `GET /calendar/link` and nothing else: a
  read-only input with a copy button, a loading sentence, and a refused read
  shown as a sentence rather than a blank box — a blank address reads as "no
  address exists" when the truth is "try again". The hint names where the address
  goes (Google Calendar, Apple Calendar, Outlook, "subscribe from a URL") and
  repeats that the address is the credential. The browser never fetches the feed
  itself: `endpoints.test`'s `NEVER_REFERENCED` entry says so, and the parity
  ledger grew by the anonymous half's one `token` (44 parameters in 20 names,
  seven spelled inside the annotation).

  Gates: `calendar.test.ts` 2 (the one route asked, and the signed URL handed
  back verbatim — no trimming, no re-encoding of the base64url alphabet), the
  copy census at 137 browser sources, the endpoint ledger at 44/20,
  `npx tsc --noEmit` clean and the frontend suite at 831 tests in 78 files, 0
  failures.

## Epic 35 — The Reminder Rings on Time

Thirty-four gave the reminders two ways out of the app: the morning letter and
a calendar the phone already reads. Both wait. A callback set for 09:00 is
carried at 07:30 the next morning — by which time the board has already gone
red — and an event on a subscribed calendar only reminds a client that renders
alarms at all. This epic closes the gap at both ends: a minute clock that wakes
the browsers at the reminder's own hour, and an alarm inside every event, so a
subscriber who never registered for push still hears the reminder.

- [x] **35.1** The minute clock rings a reminder when it comes due.

  `ReminderScheduler` is a fixed-delay clock (`careeros.reminders.tick-ms`,
  default `60000`), not a cron: every pass asks
  `ApplicationRepository.findUserIdsWithReminderBetween(since, until)` which
  accounts have a reminder inside the span, and
  `NotificationPushService.pushDue` rings each of them through `ring(userId)` —
  the same doorway, and the same `notification_states.pushed_at` latch, the
  morning sweep uses. One episode is rung once: an application the morning
  already carried is not rung by the tick, and a browser that refused writes no
  latch, so the next tick asks it again. A reminder on an `offer`/`rejected`
  row is not due at all — the status filter is the dashboard's attention
  query's own.

  The first window after boot looks back one minute rather than at the whole
  board: a deploy does not ring last week's reminders, and a reminder that came
  due while the backend was down is not rung retroactively — it is still red on
  the board, and the next morning's sweep still carries it. The window advances
  only on a completed pass; a tick that throws logs "the reminder clock could
  not read its audience; the window is retried" and re-asks the same span, so a
  database blink costs a minute, not a reminder. One account that cannot be
  prepared does not stop the rest of the pass.

  The pass has its own heartbeat, `careeros.reminders.last.tick.timestamp`,
  started at boot and moved only at the end of a completed tick, with or
  without a reminder to ring (`PushDeliveryMetrics.recordDueTick`). It is not
  the morning sweep's gauge: a stopped minute clock and a stopped 07:30 sweep
  are different faults whose first readings differ, and the runbook section
  "The minute clock a reminder rings on" says which is which.

  Gates: `ReminderSchedulerTest` 5 (the first window looks back exactly a
  minute; a completed pass advances the window; a failed pass repeats the same
  span; the heartbeat moves on completion; a throw writes none),
  `NotificationPushServiceTest` 13 (the tick rings only the accounts the board
  named for its window; an empty window asks no browser list; a reminder the
  morning already rang is not rung again; one account that cannot be prepared
  does not stop the next; a browser that refused is not latched),
  `PushDeliveryMetricsTest` 3 (the gauge starts at boot, moves only when a tick
  finishes). The ai-service heartbeat census learned the fifth clock in
  `test_response_shape_contract` — one vocabulary row, the push meter's second
  line, and the deprecation of "nine Java rows" — because the word now names
  one more pass.

- [x] **35.2** Every calendar event carries its own alarm.

  `CalendarFeed.event` appends, after `TRANSP`, a display alarm:
  `BEGIN:VALARM`, `ACTION:DISPLAY`, `DESCRIPTION` the event's own summary,
  `TRIGGER:PT0M`, `END:VALARM`. `PT0M` is the reminder moment itself — the
  event's `DTSTART` is the hour the reader picked — so the phone rings when the
  board would go red. A subscriber who never installed the app, never granted a
  browser notification and never registered for push still hears it. Clients
  that ignore alarms inside subscribed feeds (Google Calendar applies its own
  notification setting to subscribed calendars) are not made worse: the event
  renders as before, and the app stays the exact surface.

  Gate: `CalendarFeedTest` 10 — the new case asserts the exact five-line block,
  `DESCRIPTION:Acme · Backend Engineer` included, so an alarm without its text
  or a trigger other than zero fails as the block it is. `docs/API.md` and
  `docs/architecture.md` §4.7 state the alarm and the client caveat.

  Gates, measured on the committed tree: the full backend suite,
  `cd backend && mvn -o -q test`, answers 1005 tests in 153 reports with 0
  failures, 0 errors and 0 skipped (`EXIT=0`; the non-IT selection alone is
  920) — the 993 Epic 34 measured grew by the twelve cases above. The first
  full run after this epic was written answered 85 context errors, every one
  `No default constructor found` for `ReminderScheduler`: the clock has two
  constructors and Spring could not choose between them, which the five tests
  that construct it directly could not see. The public constructor now carries
  `@Autowired`; the second run is the 1005 above. The ai-service's census gates
  answer 53/53 after the heartbeat ledger learned the fifth clock (its line
  pins moved again with the import, which is why the class's three rows name
  lines 13, 14 and 74). The frontend is untouched by this epic and still
  answers 831 tests in 78 files, 0 failures, with `npx tsc --noEmit` clean and
  `npx eslint` at 0 errors over the one pre-existing warning
  (`MEMORY_WEIGHTS` unused in `memory-card.tsx`).

## Epic 36 — The Account's Second Door

An account holds a resume, a mailbox address and every application the reader has
made; a password is the only thing between that and the open internet. The
password can be changed (24.1), the sessions listed and closed (25.x), the address
moved (26) and the rows erased (24.2) — but every one of those starts with the same
single factor, and a password reused on another site hands the whole board over.
This epic adds a second: a six-digit code from an authenticator app, asked only
after the password, replay-proof, with single-use recovery codes for the day the
phone is gone. A reader who never enrolls loses nothing but the offer; a reader who
does gets a login a leaked password alone cannot open. The seed is sealed at rest
under its own secret, so a second factor does not become a second copy of the
password in the database.

- [x] **36.1** An account can enroll an authenticator and prove it answers.

  Migration `V26__user_mfa.sql` adds `user_mfa` (one row per account: the TOTP seed
  sealed with AES-GCM under `app.security.mfa-secret`, the step it was last used
  at, the moment it was proven) and `user_mfa_recovery_codes` (ten rows, each a
  BCrypt hash of a single-use code, with `used_at`). `Totp` is the RFC 6238 core:
  HMAC-SHA1, 30-second steps, six digits, one step of drift either side, Base32
  without padding both ways, constant-time compare. `MfaService.enroll` mints a
  fresh 160-bit seed and answers the `otpauth://` URI and the seed in spaced groups
  for manual entry; `activate` accepts the account's current password and a code,
  refuses an unproven seed, stores the step it was proved at, and issues the ten
  recovery codes once. Enrolling is authenticated; activation asks for the password
  again, so a stolen session cannot bolt a phone onto the account and outlive a
  password change, and 36.2's MFA bucket is where these routes also become
  rate-limited. A second enrollment replaces an unproven seed but never an enabled
  one. A blank `app.security.mfa-secret` refuses a prod boot (the same guard as the
  mail-link secret), and the dev default is the published one the guard names.

- [x] **36.2** A login cannot pass with the password alone.

  `LoginRequest` gains an optional `code`. When the account is enrolled,
  `AuthService.login` checks the password first and then the code — or a recovery
  code, which is burned on use — refusing with `MFA_REQUIRED` when no code was
  sent and `MFA_INVALID` when the one sent is wrong, wasted or already spent. A
  step at or below the stored one is refused even when its digits are correct, so
  a code watched over a shoulder does not open a second session. The refusal
  names the factor, never the password: a wrong password on an enrolled account
  is still `INVALID_CREDENTIALS`, and a wrong code never says whether the password
  was right. The limiter gains an MFA bucket so guessing six digits is as
  expensive as guessing a password.

  Landed as specified, with three decisions the outline left open. Login became a
  writing transaction (`@Transactional`, not `readOnly`), because a verified code
  moves `last_used_step` or burns a recovery row and those writes must commit with
  the session they paid for; a login that fails afterwards spends nothing. The
  MFA bucket covers exactly the route that judges a code —
  `POST /api/v1/me/mfa/activate`, whose every miss can cost eleven BCrypt
  comparisons — and is keyed by the signed-in account, the one identity a stolen
  session cannot rotate; the status read and seed minting stay outside it on
  purpose. And `SECURITY.md` spells the identity `per signed-in user`, which the
  limiter census reads as a fourth identity distinct from the AI bucket's `per
  user`: the reader is told which knob counts an account's guesses and which
  counts a person's model calls.

  Measured: the new `AuthServiceLoginTest` (6), six new `MfaServiceTest` cases
  (16 total), `ApiErrorCodeCensusTest` (4, the two new names frozen),
  `RateLimitFilterTest` (12) and `RateLimitFilterDecisionTest` (4, the `mfa` key
  and its own ceiling) all green; `AuthFlowIT` (9) drives enroll → activate →
  `MFA_REQUIRED` → `MFA_INVALID` → right code → replayed code refused → recovery
  code accepted once → reuse refused against the real stack, and `RateLimitIT` (5)
  sends five verdicts then reads a 429. The limiter census is 10/10 green over
  four ceilings and 29 carriers, and the browser's error table carries both new
  codes in both languages.

- [x] **36.3** Recovery codes can be reissued, and the account can turn the door off.

  `POST /api/v1/me/mfa/recovery-codes` replaces the set after password and code,
  answers the new ten once and revokes every old code; `POST /api/v1/me/mfa/disable`
  turns the factor off after password and code (or a recovery code), deletes the
  seed and every recovery row, and the next login asks for the password alone. The
  status answer carries how many recovery codes remain, so the settings card can
  say "3 left" without a second request. Erasing the account deletes both tables.

  Landed with three decisions the outline left open. The two routes live under
  `/api/v1/me/mfa` beside the status read, and both are POSTs on their own paths
  rather than a `DELETE /me/mfa`: the limiter meters a route's whole URI, so a
  DELETE beside the settings GET would put every status read in the same
  five-a-minute bucket as the code guesses -- the card would throttle itself.
  The `me` payload does **not** grow the two fields the outline named: the card
  already calls `GET /me/mfa` for the enabled/pending flags, that answer now
  carries `recoveryCodesRemaining`, and an MFA query behind every profile read
  would charge the header for a screen it never shows. And the retention sweep
  gains no fourth table: the rows are bounded at ten per account, and every path
  that ends a set -- activation, reprint, disable, erasure -- deletes it
  wholesale, so this table cannot grow with the install's history the way the
  token tables could. A used code is a credential with nowhere left to go; the
  sweep's subject is rows no other code path removes.

  Measured: `MfaServiceTest` (22, six new: the reprint's delete-then-mint order,
  a printed code as proof, the wrong password, the pending enrollment, the
  disable's two deletes, and a wrong or blank code leaving the door standing);
  `MfaControllerTest` (11, three new: the reprint's answer, the two fields'
  validation on both routes, and the disable's `{disabled: true}`, with both new
  routes added to the unauthenticated sweep); `RateLimitFilterTest` (12, the
  classification now naming the three code-judging routes); `RateLimitIT` (5, the
  activate arm extended: once the account's bucket is spent, both new routes
  answer 429 while `GET /me/mfa` still answers 200); `AuthFlowIT` (10, the new case
  walking enroll → activate → reprint using a printed code → the replaced sheet's
  code refused → disable using a fresh code → password-only sign-in → status
  reports no door and no codes); `AccountErasureIT` now seeds
  both MFA tables and reads both empty for the erased account and whole for the
  neighbour. The shape contract is 182 with `MfaProofRequest`, and the limiter
  census still reads seven `RATE_LIMITED` sites over four ceilings. The browser's
  endpoint ledger grew the two rows 36.3 added -- `/me/mfa/recovery-codes` and
  `/me/mfa/disable`, each saying the 36.4 security card is the caller -- because
  `endpoints.test.ts` measures Spring's table, not a hand-copied list.

- [x] **36.4** The reader can see and turn the door from settings, and answer it at login.

  A security card: status, enroll (the seed in spaced groups plus the `otpauth://`
  URI to copy, a code field, and a sentence that says to keep the recovery codes
  somewhere else), recovery codes shown once with a copy-all, replace, and turn
  off. The login page grows one step: a refused login answered `MFA_REQUIRED`
  shows the code field and resubmits email, password and code together. Copy in
  both languages, the browser's error table, `API.md` and `SECURITY.md` (what the
  seed sees, what a lost phone costs, what rotation of the secret does), and the
  runbook's "an account is locked out of its second factor" section.

  Landed with three decisions the outline left open. The card is a section of the
  settings page, not a route of its own, and it keeps one cached status (`["mfa"]`,
  a minute of staleness) that every write invalidates: the answer to activation is
  a fresh recovery sheet, not a new status, so nothing is patched locally and the
  card cannot show a factor it just turned off. The login's second step is driven
  by the refusal itself -- the form draws the code field only when the server
  answers `MFA_REQUIRED`, which happens after the password matched -- so no status
  preflight runs on a page strangers can visit, and a reader without a factor never
  sees a field they cannot answer; changing the email clears the challenge and the
  field, because a step left open would strand someone signing into a different
  account. And `MFA_REQUIRED` gained its own sentence ahead of the generic 401 rule
  in the recovery module: the generic rule would have replaced "enter the code from
  your authenticator" with advice about an expired session, which is the one thing
  that answer is saying it is not.

  The card's states are the server's answer. Off offers Start; pending offers Start
  over (a fresh seed replaces the unproven one) and says no code has proven the seed
  yet; on offers Replace and Turn off and says how many printed codes remain.
  Activation, reprint and disable each take the password and a code -- six digits,
  or a printed code where the route accepts one -- and a recovery sheet, when an
  answer carries one, is shown once with a copy-all and a Done button that drops it
  from the page. The verbs speak from the keys `failures.mfa*` while a known code
  (`MFA_INVALID`, `RATE_LIMITED`, `MFA_NOT_ENROLLED`) keeps its own sentence, so a
  reader who mistyped a digit is told that, not "the write failed".

  Measured: the new helper suite `mfa.test.ts` (8: the spaced seed, the printable
  sheet, and the three field checks), `auth-recovery.test.ts` (35, three new: the
  empty/whitespace code issue, six digits and a printed code both accepted, and
  `MFA_REQUIRED` winning before the 401 rule); `copy-census` pins 138 files with
  `security-card.tsx` named; the endpoint ledger lost its five MFA rows because they
  now have a caller, and re-measures 65 request call sites; `translations` and
  `used-keys` carry every new key in both languages; the full browser suite is 79
  files / 842 tests and `tsc --noEmit` is clean. The census gates follow the new
  population: `test_failed_mutation_is_announced` reads 86 mutation sites in twelve
  files (80 announcing at the hook, the same six quiet, 77 `fail` uses),
  `test_cache_writes_ship_what_the_key_owner_produces` files the four writes in an
  eighth file, `test_invalidated_keys_are_queries_screens_mount` reads 50 promises,
  every one naming a declared key and matching a query a screen mounts, and
  `test_auth_controller_request_contract` reads the optional `code` through the
  payload's `?` and pins login's keys as `[email, password, code]`. No Java changed
  in this unit, so the backend counts are 36.3's.

## Epic 37 — The Reply Comes Back

Every letter this product has sent left the building and never wrote back. The
unsubscribe and calendar links are read-only, the inbox files only signals the
app computed itself, and a recruiter's answer lives in a mailbox the app cannot
see. This epic opens the returning road: an account gets an address of its own,
a provider forwards the reply to it, and the reply is read, matched to the
application it answers, and filed where the tracker already tells the story.
Nothing is applied silently -- the intent is a suggestion with a one-click
accept -- and a letter the engine cannot read is still a letter that arrived.

- [x] **37.1** A mailbox of one's own: `GET /api/v1/inbound/link` hands the
  signed-in reader the address, and `POST /api/v1/inbound/mail/{token}` is the
  provider's anonymous webhook. The token is the credential -- `SignedLink`
  with a purpose of its own over the account id, cut to a 16-byte MAC so the
  local part (45 octets) fits RFC 5321's mailbox cap and otherwise the calendar
  feed's construction, so rotating `app.mail.link-secret` retires every address
  at once and a calendar token reads nothing here. The canonical payload is
  Postmark's inbound JSON (`MessageID`, `From`, `Subject`, `TextBody`, `Date`);
  a letter without a message id is keyed by SHA-256 of those fields,
  `(user_id, message_key)` is unique, and a provider retry answers the same
  200 without a second row. Text only, capped per field and body, behind a
  limiter bucket keyed by the token and not the address. Forged, rotated,
  missing and erased accounts answer one 404 `INBOUND_LINK_INVALID`; a
  deployment without `app.inbound.domain` answers `INBOUND_NOT_CONFIGURED` on
  the link route and 404 on the webhook. `V27` holds the letters, and account
  erasure takes them with it.
- [x] **37.2** The engine reads the reply: ai-service's internal
  `POST /internal/features/classify-reply` answers `{intent, company, role}`
  with intents `rejection | interview | offer | info | other` -- deterministic
  keyword passes in the letter's language first, the model only filling what
  the rules abstain on, and the offline mock stays deterministic. The route is
  pinned in `test_forward_features_contract.py`. The backend's bridge runs on
  arrival, and its failure leaves the letter with no intent rather than losing
  it: a classifier outage is not a lost reply. `V28` adds the three reading
  columns, `intent` CHECK-constrained to those five values; the row is stored
  before it is read (two transactions, so a stalled classifier holds no
  connection), and a duplicate delivery is not classified again. The shape
  census counts `InboundMailService` among the classes that read an AI answer.
- [x] **37.3** The reply meets the application: a company-name match
  (case-insensitive, narrowed by role containment when the name repeats) files
  the mail on one application, and a guess that narrows to nothing files
  nothing rather than the wrong row. Filing writes an `application_events`
  row of kind `reply` (mail id, sender, subject, intent) and the notification
  center gains a `reply:<id>` episode, so the bell counts the reply, the
  morning sweep may ring it, and the stamp stays the reader's. An unmatched
  letter waits on the replies page with a "file this reply" route; the intent
  maps to a suggested stage (`rejected` / `interview` / `offer`, the board's
  own vocabulary) that the reader applies in one click, never automatically,
  and only on the application the mail is actually filed on. The letters are
  readable through `GET /api/v1/inbound/mails` (paged, scoped) and fileable
  through `POST /api/v1/inbound/mails/{id}/file`.
  `V29` adds `application_id` (`ON DELETE SET NULL`, so deleting a card
  returns its letters to unmatched rather than deleting them) and `filed_at`
  (null exactly when unfiled). `InboundReplyService` owns the match, the two
  writes of a filing (the letter names the card; the card's timeline gains the
  event) and the list; `InboundMailService` calls `autoFile` after the reading,
  in its own transaction and its own failure, so a matcher that throws costs
  the filing and never the letter. Filing on the same card twice is a no-op;
  a different card is `409 INBOUND_MAIL_ALREADY_FILED` rather than a silent
  move, because the first card's timeline already says the letter answers it.
  A letter that is not the caller's is `404 INBOUND_MAIL_NOT_FOUND`, the same
  answer as one that never existed. The notification item is synthesized, not
  stored: filed letters inside the seven-day lookback, keyed `reply:<mailId>`,
  titled by the employer (the sender when the reading named none) and linked
  to `/replies?mail=<id>`; the morning letter names it in both languages and
  prints the reply's own subject under the line. The suggested stage is advice
  on the wire only — no route here moves an application.
- [x] **37.4** The replies have a page: `/replies` lists the letters newest
  first -- sender, subject, time, the intent as a badge, the application the
  letter is filed on or the picker that files it, and the suggested-stage
  action behind the existing confirmation; settings grows the address card
  (copy, the rotation warning beside the address, the not-configured
  sentence). Both languages, the copy census, the endpoint ledger and the
  three hook gates follow the new population; API.md records the four routes
  and the two new error codes, SECURITY.md says the address is a capability
  and the letters are user data that leaves with the account, RUNBOOK says how
  to forward a domain to the webhook and what a silent address means.
  `app/(app)/replies/page.tsx` draws the row, the picker and the
  confirmation, `components/settings/inbound-card.tsx` tells
  `INBOUND_NOT_CONFIGURED` from a retryable failure, and `lib/hooks/replies.ts`
  is the three routes' one reader (`mapInboundMail` keeps "not read yet" null
  rather than borrowing an intent). The page highlights `?mail=` -- the bell's
  link -- and corrects a past-the-end page through `lastPageOf`; the nav gains
  `nav.replies` and `navDescriptions.replies`. The endpoint ledger drops the
  three reader routes it had listed for this unit (`/inbound/mail/{}` stays:
  only the provider calls it), and the browser population the copy census
  walks grows 138 -> 140 with the page and the card.

## Epic 38 — The Account Can Reach Its Own Verbs

Epics 24–26 put four verbs on the account — change the lock, erase the account, list
and close its doors, move its sign-in address — and each closed by saying the routes
were live for a client that had not come. The endpoint ledger still carries ten lines
that begin "the client has not wired". Worse, 26.1's confirmation letter points at
`<app.web.base-url>/confirm-email`, and no such page has ever existed: a reader who
asks the address to move receives a letter whose link is a 404. This epic builds the
client for all four verbs, starting with the link that is already in the mail.

- [x] **38.1** The confirmation letter's link lands on a page that can answer it.

  (`/confirm-email` is the public landing for 26.1's letter: it reads `?token=` in an
  effect — the URL is unreadable to the server render — and posts it to the public
  `POST /auth/email-change/confirm`, the one route that writes `users.email`. The
  page has honest states rather than one spinner: answering (the call is in flight),
  moved (`users.email` moved and every refresh token was revoked, so the page sends
  the reader to sign in with the new address instead of pretending the tab is still
  signed in), refused (unknown, spent and expired links are one
  `EMAIL_CHANGE_INVALID`, answered with advice to ask again from settings) and
  already-registered (`EMAIL_ALREADY_REGISTERED`, where the address won a race with a
  registration; re-sending the same link cannot succeed because the token was spent).
  A link with no token says so before calling, and a token can be pasted into a field
  for the same reason the reset screen offers one. The page is a `PUBLIC_PAGE_TITLES`
  entry outside the `(app)` group, so a signed-out browser can spend it; the endpoint
  ledger drops `/auth/email-change/confirm`, and the auth flow's gates follow the new
  population.

  `app/(auth)/confirm-email/page.tsx` takes its title from `PUBLIC_PAGE_TITLES`, and
  `components/auth/confirm-email-form.tsx` is its one client component; the two
  decisions that are not markup — where the token comes from and which refusal earns
  which sentence — live in `lib/email-change.ts` and are pinned by 7 unit tests, the
  way `auth-recovery.ts` holds the reset screen's arithmetic. `useConfirmEmailChange`
  posts through `authApi.confirmEmailChange` (`auth: false`) and drops the local token
  pair on success, because a confirmed move revokes every refresh token. The endpoint
  ledger loses its "the auth flow has no screen" line, `nav.test.ts` and
  `metadata.test.ts` name the new public route, and the copy census grows 140 -> 142
  with the page and the form. The frontend suite is 857 tests over 82 files, tsc and
  eslint clean, and the page was walked in a browser — paste form, answering, moved
  and invalid states — against a stubbed API.)

- [x] **38.2** The address moves from settings, and the screen says it takes two letters.

  (A settings card names the address on the account, takes the new address and the
  password, and posts `POST /users/me/email-change`. Each refusal has its own
  sentence, not the server's English: `CURRENT_PASSWORD_INCORRECT` is
  re-authentication failing, `EMAIL_UNCHANGED` is the same address after trimming and
  case-folding, `EMAIL_ALREADY_REGISTERED` means the target mailbox already owns an
  account, and `RATE_LIMITED` is 27.1's mail meter with its `Retry-After`. The success
  state explains what happened instead of saying "sent": two letters left, the claimed
  mailbox holds the link that moves the address, the current mailbox holds the warning,
  and nothing changes until the link is answered. The card and the landing page share
  one hook family, so the two sides of the move cannot drift.)

  (Shipped: `components/settings/email-change-card.tsx` sits beside the account card it
  belongs to, and `lib/hooks/account.ts` holds `useRequestEmailChange` — the only
  reference to the route, so the ledger line for `/users/me/email-change` left. The card
  names the address on the account, checks the new one with the sign-in form's own
  `emailIssue` and the password by presence, and puts each refusal under the field that
  caused it (`lib/email-change.ts:addressMoveRefusal`, four unit tests):
  `CURRENT_PASSWORD_INCORRECT` under the password, `EMAIL_UNCHANGED` and
  `EMAIL_ALREADY_REGISTERED` under the address, and the meter's `RATE_LIMITED` on the
  form, because no field caused it. `describe` supplies the sentence from the code, so
  the wrong-password answer is in the reader's language — which exposed a real leak:
  `currentLocale()` read only `localStorage`, so a browser that had adopted the account's
  language (21.4) raised every sentence composed this way in English on a Chinese page;
  it now falls back to the cookie the provider writes, with two unit tests. Success
  replaces the form with the two letters and their two-hour window. Frontend 863 tests
  across 82 files; tsc and eslint clean; the card was walked in a browser — the form, the
  success panel, a wrong password, the limiter and an address already taken — against a
  stubbed API.)

- [x] **38.3** The open doors are drawn, and each one can be closed.

  (`GET /users/me/sessions` fills a settings card: one row per refresh-token family
  with the device name, the address it last came from, when it started, when it was
  last seen and when its furthest token expires. The family that is asking is marked,
  and the row says that closing it behaves like logout. Closing one door is
  `DELETE /users/me/sessions/{familyId}` behind the existing confirmation; closing all
  is the same verb without an id, states that every device signs out and that the
  current tab keeps working only until its access token expires. A neighbour's family
  or one already closed answers one `404 LOGIN_SESSION_NOT_FOUND`; the screen reads
  that as "this door is already closed" and refreshes instead of apologising for an
  error the reader cannot act on. An empty list is an honest state: no family can
  refresh, so the next expired access token sends the reader to sign in.)

  (Shipped: the list needed one fact it never carried — which row is the tab that is
  asking. The access token now carries `fid`, the refresh-token family it was minted
  for (`AuthUser.familyId`, nullable so tokens and principals minted before the claim
  still parse); `TokenService.listSessions(userId, currentFamilyId)` marks the matching
  row and `SessionResponse` gained `current`, so the screen never guesses from a
  user-agent string. Both spellings of the list route pass the family to it.
  `JwtServiceTest` round-trips the claim (and its absence), `TokenServiceSessionsTest`
  pins both the marked row and a token with no family marking no row, and `SessionsIT`
  reads the laptop row as current and the phone as not.

  `components/settings/sessions-card.tsx` draws one row per family: `lib/sessions.ts:
  deviceLabel` folds the seven browser tokens and six systems into "Chrome · Windows"
  and keeps anything it does not recognise as written, so a deployment's own client
  and an unnamed device still have a row. The current row is badged and told that
  closing it is logout. Closing one door and closing all share the existing
  `ConfirmDialog`, and each says its true consequence; one already shut answers
  `LOGIN_SESSION_NOT_FOUND`, which `sessionCloseRefusal` reads as "this door was
  already closed" and the list refetches; the empty list says the tab lives only until
  its access token expires. `useSessions`, `useRevokeSession` and
  `useRevokeAllSessions` in `lib/hooks/account.ts` are the routes' only references, so
  the ledger drops its two `/users/me/sessions` lines while the `/me` aliases stay
  listed. Copy census 143 -> 144; `lib/sessions.test.ts` adds 6 tests. Frontend 869
  tests over 83 files, tsc and eslint clean. Walked in a browser against a stubbed API:
  three rows with the current badge and note, both dialog sentences, the 404 notice
  with its refetch, and the close-all confirmation ending in the empty state.

  The full suite this shipped against also caught two latent Epic 37 breaks, fixed
  here: `AccountErasureIT`'s raw `inbound_mails` inserts omitted the id Hibernate
  generates in Java, and the self-invocation census charged `InboundMailService.
  receive`, whose two writes must stay split around the classifier call — the site is
  now named in the census list with that reason instead of being forced into one
  transaction. Backend 1116 tests, unit and ITs, green.)

- [x] **38.4** The lock changes from the page that shows it.

  (A settings card takes the current password and the new one twice, mirrors the
  record's `(min = 8, max = 72)` before sending, and posts
  `PATCH /users/me/password`. A wrong current password is
  `CURRENT_PASSWORD_INCORRECT` — the same re-authentication failure the address and
  erasure cards show — and `PASSWORD_UNCHANGED` is refused by name, because re-storing
  the same hash would still sign every other device out for nothing. Success says the
  true consequence: every refresh token is revoked, other devices sign out at their
  next refresh, and this tab keeps working until its access token expires. The form is
  replaced by that sentence rather than cleared into a toast.)

  (Shipped: `components/settings/password-card.tsx` sits between the sessions card and
  the second factor and asks for the current password, the new one twice. The bounds are
  the record's: `lib/password-change.ts:currentPasswordIssue` mirrors
  `PasswordChangeRequest.currentPassword` (`@NotBlank @Size(max = 72)`; the current
  value has no floor), the new one uses the existing `passwordIssue` `(8, 72)`, and the
  two values meet in `confirmationIssue` — all three decided before a request leaves the
  browser. `passwordChangeRefusal` puts `CURRENT_PASSWORD_INCORRECT` under the current
  field and `PASSWORD_UNCHANGED` under the new one (the server declines before writing,
  so nothing was revoked); everything else, the limiter included, is the form's.

  The client spells the route `/users/me/password` once and posts each field once;
  `useChangePassword` refetches the open-door list on success, so the sessions card
  truthfully empties the moment the change lands. The endpoint ledger drops its
  `/users/me/password` line and keeps the `/me/password` alias listed. Copy census
  144 -> 145; `lib/password-change.test.ts` adds 5 tests; frontend 874 tests over 84
  files, tsc and eslint clean. Walked in a browser against a stubbed API: the empty
  form's three sentences, a wrong current password under its field (the client answers
  the server's 401 by refreshing once and retrying, so the code reaches the card), an
  unchanged new value under the new field, a seven-character new value refused locally
  before any request was sent, and success replacing the form with the full consequence
  while the sessions list emptied. Backend unchanged and green at 1116 tests.)

- [x] **38.5** The door out is drawn like the doors in, and the ledger stops calling
  these routes unwired.

  (The bottom of settings gains the erasure card: it names what leaves (the objects
  behind `documents.file_key`, every row cascading from `users`) and what does not
  (backups, until their retention window passes), takes the password and the address
  typed back, and posts `POST /users/me/erase` only behind a confirmation restating
  both. A wrong password and a mistyped address are `CURRENT_PASSWORD_INCORRECT` and
  `CONFIRMATION_MISMATCH`, and neither touches anything; success drops the local token
  pair — the account whose rows just left cannot refresh — and lands on a sentence
  that says the account is gone, not a silent redirect into a 401. With the four
  screens wired the endpoint ledger's ten "the client has not wired" lines become what
  they are — aliases of the spelling the client uses, or, for `/mail/preferences/*`,
  backend-rendered public pages the browser navigates to and never fetches — and the
  copy census, used-key and translation gates follow the new cards and the landing
  page. Epics 24–26's paragraphs gain a pointer to where their verbs' screens finally
  landed, and 24.1's stale `INVALID_CREDENTIALS` (superseded by 30.4's split) is
  corrected in the same pass.)

  (Shipped: `components/settings/erase-account-card.tsx` closes the settings page, after
  every card whose rows the request would take with it. It names the address on the
  account, what leaves (the object-store files behind `documents.file_key` and every row
  cascading from `users`) and what does not (backups until their retention window
  passes; letters already delivered stay in their mailboxes). The password must be
  present and the typed address passes the sign-in form's own `emailIssue` before any
  request leaves; the values then open a confirmation that restates the typed address,
  and only its button posts `POST /users/me/erase` through `authApi.eraseAccount`. The
  card posts the trimmed address, and `lib/erase-account.ts:eraseRefusal` puts
  `CURRENT_PASSWORD_INCORRECT` under the password field and `CONFIRMATION_MISMATCH`
  under the address, everything else on the form — a refusal closes nothing and loses
  nothing; three unit tests pin that mapping and its silence on other codes.
  `useEraseAccount` drops the token pair, clears the query cache and hands the browser a
  full-document navigation to `/account-erased`, so the workspace tree unmounts instead
  of firing the next request into a 401 that no refresh can answer.

  The landing is `app/(auth)/account-erased/page.tsx`, a public server component: it
  reads the locale cookie, paints the sentence in the reader's language on the first
  response, repeats what survived (backups, delivered letters), and offers only the two
  doors out — register again or sign in as someone else. It makes no API call and needs
  no session, which is the point: the account it would ask about no longer exists. The
  endpoint ledger's remaining lines stop pretending a screen is pending: the `/me/*`
  entries name the `MeController` alias and the settings card that calls its
  `/users/me/*` twin (38.2–38.5), and `/mail/preferences/*` is described as
  backend-rendered public pages the browser navigates to from a mailbox and never
  fetches. The `/users/me/erase` line left with the card. Copy census 145 -> 147 with
  the card and the page; `metadata.test.ts` names the public landing title and the
  used-key and translation-parity gates follow the added keys. Frontend 877 tests over
  85 files, tsc and eslint clean.

  Walked in a browser against a stubbed API: the empty form asked for the password and
  a matching address and sent no request; a wrong password landed under its field after
  one refresh and retry, and a mistyped address under the address field, with nothing
  posted before the confirmation was accepted; the confirmation restated the typed
  address, a value typed with spaces around it was posted trimmed, the pair was gone
  after success, and the browser landed on `/account-erased` — "账号已经删除", title
  "账号已删除 · AI Career OS" — which renders without a session and makes no request.)

## Epic 39 — The Deployment Answers for Itself

Epic 38 let the product tell a reader what it did with their account. The process
running it cannot be asked the same questions. `/api/v1/health` names the database and
Redis and calls everything else "ok" — an object store that stopped answering and an
ai-service that died are invisible on that line, though they own every uploaded file
and every AI feature. Compose prints `running` for a container that started and never
answered, because only postgres, redis and minio carry healthchecks. A boot says
nothing about which mail transport, storage endpoint or provider it selected, and a
redeploy cuts in-flight requests because Spring's default shutdown is immediate. This
epic makes the deployment answer three questions in its own words: is anything down,
what did I become, and did I finish what I took before I left.

- [x] **39.1** The health line names the object store and the AI service.

  (`/api/v1/health` answers `{status, db, redis}`. The object store holds every uploaded
  file and the ai-service performs every analysis, so a line that says `ok` while either
  is unreachable is a report that lies by omission. The route gains `storage` and `ai`,
  each probed under a short bound of its own — a hung dependency must not hang the
  probe, which is why the bound is smaller than any client's call budget. `status` is
  `ok` only when all four are true and `degraded` otherwise, and the answer stays 200:
  the API can serve most routes without either dependency, so the line reports, it does
  not gate. `StorageService` gains an availability probe implemented by the MinIO
  adapter as a bucket-exists check; the AI client gains a health call against the
  ai-service's own `/health` with its own short timeouts, never the 180-second feature
  budget. Unit tests pin each answer — all up, storage down, AI down, and a probe that
  hangs coming back within its bound; API.md and DEPLOYMENT.md's probe table gain the
  two names.)

  (Shipped: `StorageService` gains `available()`, the MinIO adapter answering with the one
  bucket-exists round trip boot already makes and the in-memory test store answering true
  by construction. `AiServiceClient` gains `healthy()`, the HTTP bridge asking the
  ai-service's own public `/health` through a client of the probe's own — 2-second connect
  and 2-second request, never the 180-second feature budget — with no internal token,
  because that route does not ask for one; the fake exposes `aiHealthy` so an integration
  test can turn the AI half off. The four probes left the controller for
  `com.careeros.health.HealthService`: each runs on its own virtual thread, all four share
  one 2-second deadline, a timeout cancels its probe and counts as false, an exception
  counts as false, and a deployment with no storage bean says `storage: false` rather than
  skipping a half it never had. The body keeps the report's order — `status, db, redis,
  storage, ai` — `status` is `ok` only when all four answered true, and the controller
  always answers 200. Tests: `HealthServiceTest`'s eight cases (all up; storage false; AI
  false; AI throwing; absent store; db false; Redis throwing; a storage probe that never
  answers returning inside a 100 ms budget, measured under two seconds);
  `HttpAiServiceClientTest`'s two socket cases (the public route is asked with no token; a
  503 is not health); `HealthIT`'s two against the real database and Redis (all four true →
  `ok`; the fake AI turned off → `ai: false`, `status: degraded`, still 200).
  `RateLimitIT`'s and `CorsContractIT`'s existing health assertions still pass. API.md's
  health row and DEPLOYMENT.md's probe table now name all four dependencies. Backend 1128
  tests, unit and ITs, green.)

- [x] **39.2** The stack waits for an app that answers, not one that started.

  (The three application services in `docker-compose.yml` have no healthcheck, and
  `docker compose ps` reports them `running` whether or not they can answer; only
  postgres, redis and minio are probed. Each app service gains one that checks the
  process answers — the backend and ai-service by fetching their own health route and
  accepting its 200 whether the body says `ok` or `degraded` (a degraded dependency
  must not restart-loop the container), the frontend by fetching its landing page. The
  stack's `depends_on` gates become `condition: service_healthy` where a service
  genuinely needs another up (frontend on backend, backend on ai-service and its three
  data stores), so a first boot cannot serve requests against a half-started stack.
  A deployment test reads both compose files and refuses, by name, an app service with
  no healthcheck, a dependency without a health condition, or a probe that names a
  different port than the service publishes. DEPLOYMENT.md's per-dependency table gains
  the three rows.)

  (Shipped: each application service now probes its own route from inside the container.
  The ai-service uses `python -c` and urllib against `/health` — the image carries python,
  not curl or wget — and a 500 (its database half is gone) exits non-zero, because this
  probe gates the backend's start. The backend uses busybox `wget` against `/api/v1/health`,
  which answers 200 whether the body says `ok` or `degraded`, so an outage is reported in
  `docker compose ps`, not restart-looped; Docker's 5-second timeout sits above the route's
  own 2-second bound. The frontend uses `node -e` and `fetch` against `/`, spelled
  `localhost` rather than `127.0.0.1` because the shell's admitted origin is that host and
  the origin census reads every shipped file. `start_period` is 30s for the two light
  services and 90s for Spring; `depends_on` becomes the long form with
  `condition: service_healthy` in both files — the development backend now waits for
  ai-service too, both frontends wait for the backend, and the production backend's
  ai-service gate moves from `service_started` to `service_healthy`. `docker compose config`
  parses the development file and the merged production override.
  `ai-service/tests/test_the_stack_waits_for_an_app_that_answers.py` reads only the
  `services:` section (a volume's child sits at a service header's indent), requires exactly
  one loopback HTTP probe per application service, checks that probe's port against the
  container ports the service publishes and its path against DEPLOYMENT.md's Monitoring
  table, and refuses any app-service dependency without `service_healthy`; a clean fixture
  passes while a broken one is refused by name for each rule, and the data stores'
  `pg_isready` and `mc ready local` probes are decoys it leaves alone. DEPLOYMENT.md gains a
  "Startup gating" section with the three rows. The four deployment gates pass together (21
  cases). The full ai-service suite is 1903 passed, 48 failed, 1 skipped — every one of the
  48 fails identically on a clean checkout of this commit's parent, in cross-language
  censuses the 37/38 epics outgrew (new replies hooks and page, account hooks, inbound
  config leaves, new error codes and records); none is touched by this unit, and the repair
  is the next one. Backend 1128 and frontend 877 unchanged.)

- [x] **39.2b** rep: the censuses the 37/38 epics outran.

  (39.1 and 39.2 each ran their own gates green while the ai-service suite stayed red in
  forty-eight cases across five cross-language censuses. The replies inbox (37.4) added a
  thirteenth window hook, a second `useApplications` call site and a pager; the account
  cards (38.1–38.5) and the inbound address (37.1–37.3) added routes, error codes,
  records, toasts and config leaves; a health-test comment (39.1) spelled the object
  store's switch a fifth time. None was a product defect — each was a pin that had
  stopped describing the app — and this unit moved no product code.

  Window sizes: thirteen list hooks, twelve of them asking for a size and every literal
  the route's own (the replies inbox's 50 joined the nightly letter's 10/10), the replies
  screen shadowing it with its own 20 while its application picker asks for the 100-row
  ceiling. Envelope readers: twelve page-typed hooks, two over routes that answer bare
  lists (`/jobs/saved`, `/contacts`), `size` read in eleven places — the ten
  past-the-end corrections plus the replies page's — and twelve pagers still fed the
  caller's number. Response shape: 188 backend record declarations (37.3's `FileRequest`
  and 37.4's `InboundMailItem` joining), 56 `toast.success` lines, and eight rejecting
  files, the four settings cards (38.2–38.5) joining the auth forms because their
  `onError:` belongs to react-query. 404: thirty-six answering places — thirty-five
  `ApiErrorCode` constants, thirty-four of them naming a record, plus the
  `NoResourceFoundException` handler — and twenty-six `(app)` screens, five through the
  boundary and sixteen deciding the async state on their own flags, the replies page
  among them. Knobs: thirty-seven leaves, eleven holders, twenty-six fields,
  thirty-four env-only keys; `inbound.domain` is a fourth `@Value`-only key (after web,
  mail and security), `ratelimit.inbound-per-minute` is read by the limiter's INBOUND
  arm, and the object store's switch now has five flat rows, the fifth 39.1's comment.

  The five gates run 8/8, 8/8, 32/32, 9/9 and 7/7; the full ai-service suite is 1951
  passed, 1 skipped, 0 failed in 161.54s.)

- [x] **39.3** A boot says what it became, and no secret is in the sentence.

  (A boot currently logs what Spring logs and nothing about the choices this deployment
  made. One line at readiness states them: the environment, the port, the database host
  and name (never the URL, which carries a password), the Redis host (never the URL),
  the storage endpoint host and bucket or that storage is off, the AI service host,
  which mail transport bean was selected (`Console` or `Smtp`, never a host's
  credentials), whether push has a key pair, and which schedulers are on. It is built
  from the bound beans and properties rather than re-reading the environment, so it
  cannot disagree with what the process uses; a unit test builds it from values that
  include sentinel secrets and asserts none appears, and RUNBOOK names the line as the
  first thing to read when a stack looks healthy but is not.)

  (Shipped: `com.careeros.boot.BootReport` listens for `ApplicationReadyEvent` and logs
  one line — `boot: env=... port=... db=host/path redis=host storage=host bucket=name
  ai=host mail=console|smtp push=off|keypair schedulers=[...]`. Every fact comes from
  the object the process is actually using: the bound `AppProperties` and Boot's
  datasource and Redis properties, the chosen mail and push beans, the store bean's
  presence, and the context's own bean-definition scan for methods declaring
  `@Scheduled` — never a re-read of the environment. URLs are parsed for their host and
  never echoed, a value the line cannot read is named `unset`/`unparseable` rather than
  quoted, push says on or off without the VAPID pair, and a store bean that does not
  exist says `storage=off` rather than skipping the half. `BootReportTest`'s three cases
  pin the exact sentence over sentinel secrets (asserting the sentinel, `jdbc:`,
  `postgresql`, `redis://` and `@` all absent), the dev sentence where storage, push and
  the database are off, and the unparseable sentence that must not echo the malformed
  URL. Spring 6.2's `Task.getRunnable()` hands back an `OutcomeTrackingRunnable`, so the
  `ScheduledTaskHolder` cannot name a scheduler bean; the context scan can, and the test
  exercises it against a real `AnnotationConfigApplicationContext`. RUNBOOK gains "A
  stack that looks healthy and is the wrong one", naming the line as the first read,
  the six words to look for, and what the line never contains; architecture.md's
  backend tree gains `boot/`. The config-knob census counts the report as a reader of
  `storage.endpoint`, `storage.bucket`, `ai-service.base-url` and `deployment.env` —
  reading them to describe, never to decide. Backend unit suite 1040 green (1037 plus
  the three here); ai-service 1951 passed, 1 skipped, 0 failed in 212.73s, with the
  knob census 7/7 among them.)

- [x] **39.4** A shutdown finishes the request it already took.

  (`server.shutdown` is Spring's default `immediate`: a redeploy cuts requests that were
  already being answered. It becomes `graceful`, with a bounded
  `spring.lifecycle.timeout-per-shutdown-phase` so a stuck request cannot hold a process
  forever; the schedulers stop with the context and the RUNBOOK says what a redeploy is
  allowed to cost. A config contract test pins both settings, so a future edit cannot
  quietly put the deployment back on immediate shutdown.)

  (Shipped: `application.yml` sets `server.shutdown: graceful` and
  `spring.lifecycle.timeout-per-shutdown-phase: 30s`. On SIGTERM the connector stops
  accepting, requests already inside the process finish, and a request still running at
  the bound is cut — a stuck request cannot hold a redeploy forever. Both compose files
  set the backend's `stop_grace_period: 40s`, because Docker's 10-second default would
  SIGKILL the JVM while its own 30-second phase was still draining; the schedulers are
  beans and stop with the context rather than firing from the old process.
  `ShutdownContractTest`'s two cases read the real files: the first parses
  `server.shutdown` out of `application.yml` (not any other `shutdown:` line) and
  requires the phase to be a bounded duration; the second reads both compose files,
  finds the `backend` service block, and refuses a `stop_grace_period` below the YAML
  phase plus five seconds — so neither a quiet return to `immediate` nor a compose grace
  that undercuts the drain can land. RUNBOOK gains "A redeploy finishes what it
  started": a four-row table of what an in-flight request, an over-budget request, a
  mid-run sweep and a new connection each cost, and the two log lines
  (`Commencing graceful shutdown…` / `Graceful shutdown complete`) that show the drain
  happened; DEPLOYMENT.md's Rolling Updates section says the same in one paragraph.
  Backend unit suite 1042 green (1040 plus these two); ai-service 1951 passed,
  1 skipped, 0 failed.)

## Epic 40 — The Bundle Means Everything

The `/data` page promises "Export everything", and the 1.2.0 growth carried the
notes and the contacts because "your data" that leaves out the tables the reader
typed into is not their data. Measured on 2026-10-30 against the schema
(V1–V29), ten sections is not everything the reader owns: five user-scoped
tables carry content or standing choices the reader made and travel in no
section at all — `conversations` and their `messages` (the copilot chats: the
reader's questions, the coaching, the artifacts the assistant built from their
own material), `saved_jobs` (a bookmark and the note attached to it),
`saved_searches` (the standing queries the morning sweep speaks for),
`ingestion_feeds` (the sources the reader configured) and `inbound_mails` (the
letters a provider forwarded to the reader's own address, with the classifier's
reading and the application each was filed on). A restore cannot bring any of
them back, and an anonymized bundle cannot withhold them — they were never
there.

What is deliberately *not* in the bundle is bookkeeping rather than content:
tokens and sessions, MFA secrets, push subscriptions, notification read state,
mail preferences, usage events and agent runs, digests and nightly reports.
Those describe what the account did, not what it holds. The last unit writes
that distinction down as a census, so the next table the product adds cannot
quietly land on the wrong side of it.

- [x] **40.0** Inventory the bundle's omissions and open the epic.

  (Measured, not remembered: the bundle's ten sections were read against every
  `CREATE TABLE` in `db/migration`, and the five above are the ones that carry
  the reader's own words or choices. The 1.2.0 note's open thread — "the current
  state still does not cover the resumes, the knowledge base, the job
  descriptions, the interviews and the memories" — was stale: the restore's
  current state grew to cover all ten sections later in Epic 13, and the note
  now points at that paragraph instead of repeating a closed thread. EXPORT.md
  records the measured gap as open so the document stops implying the bundle is
  complete. All five live in the backend (the conversation service writes the
  chats; the schedulers and stores write the choices, the bookmarks and the
  letters), so each unit grows the bundle where the rows are written, end-to-end
  — export, anonymize, readable half, plan with the fourth op, apply, and the
  page's counts — then one census that holds the whole promise.)

- [x] **40.1** The chats travel: a `conversations` section and its messages.

  (The copilot is where the reader thinks out loud: the question they asked, the
  answer they were given, the artifacts built from their own resume and the
  sources those artifacts cite. None of it is in the bundle. The section carries
  each conversation with its messages nested — role, content, artifacts,
  sources, suggested actions and the created time — and the six fields an
  anonymized bundle must blank are named rather than guessed. The chat is the
  reader's own words, so the readable half gets its words in both languages, the
  plan keeps its ids (a conversation the bundle omits is retired, its messages
  cascade), and the apply writes messages with their conversation. A 1.2.0
  bundle stays valid: the new sections arrive under schema 1.3.0.)

  (Shipped: the bundle's eleventh section, under schema **1.3.0** — and the
  ladder in `SECTIONS_BY_VERSION` holds a 1.2.0 backup to its ten sections, so
  the older file still validates. The bridge reads the caller's chats a page at
  a time and their transcripts in one statement, and each conversation travels
  with its messages nested — role, content, artifacts, sources, suggested
  actions and the created time — while the run id, which is bookkeeping, stays
  out. The anonymized policy walks the transcript: the chat's title and each
  message's content, artifacts and sources are the reader's, every message
  column is classified by the gate, and a marker in any of them does not
  survive. The readable half carries the chats and their transcript lengths in
  both languages. The plan compares a chat by what the restore writes — the
  message ids, the ownership, the conversation link and the stamps are not
  content — so an unchanged chat is `skip`, a changed answer is an `update`,
  and a chat the bundle no longer carries is a `delete`. The apply replaces
  the transcript whole on update, mints message ids at the target, and retires
  a dropped chat through the same cascade the chat screen relies on. The data
  page lists the section with its label in both languages, and the restore
  counts it like the others. Backend unit suite 1070 green; ai-service 1967
  passed, 1 skipped, 0 failed on a clean HEAD snapshot; the frontend's
  translation and copy censuses 19 green.)

- [ ] **40.2** The standing choices travel: saved searches and ingestion feeds.

  (A saved search is the reader's standing question and the reason the morning
  sweep has an audience; a feed is the source they pointed the ingester at. Both
  are backend-owned, both are matched by id at the target — an omitted row is a
  choice the reader cancelled — and both are compared field-for-field so an
  unchanged row is `skip` rather than a write. The feeds' URLs are the reader's
  configuration, not a secret, and the anonymized bundle keeps them: redacting a
  source hides nothing about a person, while dropping the row would break the
  restore's counts.)

- [ ] **40.3** The bookmarks and the letters travel: saved jobs and inbound mail.

  (A bookmark carries the reader's note beside the posting; the posting itself
  belongs to the shared catalogue, so the restore keeps a bookmark only when the
  target has that job and reports the ones it could not keep rather than
  inventing a posting. The letters are what a provider forwarded to the reader's
  address — the recruiter's words, the classifier's reading and the application
  it filed on — and the filed link resolves against the applications the same
  restore wrote, because the restore keeps application ids. `message_key` stays
  the provider's idempotency key, so restoring a bundle twice answers one row
  per letter. The anonymized bundle blanks the address, the subject and the
  body: those are the other person's words.)

- [ ] **40.4** The sections are all of it, and the gate says so.

  (A new gate reads every table in `db/migration` whose rows name a reader and
  requires each to be either carried by a section — itself or nested, like
  `messages` under `conversations` — or listed in EXPORT.md's exclusion table
  with a reason that says "bookkeeping, not content". The page's list of what
  an export carries is derived from the bundle's own manifest rather than typed
  by hand, so "Export everything" is a sentence the product can keep; the
  readable half's section order and the drop list both follow the one section
  tuple. The census fails by name on a new table, which is the only way the
  promise survives the next migration.)

## Epic 41 — The Reminder Reaches the Mailbox at Its Moment

The inbox has carried a due reminder since 19.3, and the minute clock has rung its
browsers since 35.1 — but a reader with no push registration heard about it only in
the next morning's letter, and a reminder's whole point is its moment. The clock now
writes the letter itself, and the mail page grows a third dial so the moment is a
choice rather than a side effect of the morning sweep.

- [x] **41.1** The reminder's own letter, written when it comes due.

  (`V30` adds `mail_preferences.reminder_mail`; absence of a row still means every
  letter is on. `MailList.REMINDERS` is the third slug — the page, the header and the
  query read one spelling — and `MailPage` grows the section that says what the dial
  chooses: the moment, not the silence, because turning it off leaves the reminder in
  the morning letter. `ReminderMailer` writes a short bilingual letter naming the
  roles that came due with a link per card (five, then counted), and
  `ReminderMailService` mails only the reminder items that fell inside the tick's
  window, so the morning's stale and reply items wait for the morning. The latch is
  the episode's own `notified_at` rather than a column on `applications`: one episode
  is one letter whichever pass carries it, so the morning sweep cannot mail it again,
  and a refused letter latches nothing — the morning sweep is the fallback.
  `ReminderScheduler` runs the two halves separately and holds its window when either
  fails, so a relay that refuses letters cannot silence a browser and a failed tick
  still asks the same minute. 19 backend tests (7 service, 6 mailer, 4 scheduler, 1
  preference, 1 page); the touched subset 44 green. API.md, architecture.md,
  DEPLOYMENT.md and RUNBOOK.md follow the third dial and the second half of the
  clock.)

- [x] **41.2** The clock that can stop is an alarm, and the refusal count says both
  letters.

  (The runbook had said "No Prometheus rule ships for this clock yet" since 35.1: the
  heartbeat `careeros.reminders.last.tick.timestamp` existed and nothing watched it. The
  shipped rules are eleven now — `CareerOSReminderClockStale` fires when the gauge has
  not moved for `300` seconds, five missed ticks of the scheduler's `60000` ms default,
  held for five minutes so a deploy's drain is not a fault, and its description says what
  lags is the moment rather than the reminder. `CareerOSSignalMailFailing` now counts
  letters rather than one letter kind, because 41.1's reminder letter writes the same
  `careeros.signals.delivery{outcome="refused"}` series; its summary, description and
  runbook section name both log lines ("the signal mail to ..." and "the reminder letter
  to ...") and say a refused reminder is retried by the next morning's sweep, not by the
  minute clock. The gate
  `test_the_alarms_name_metrics_that_ship_and_a_page_that_says_what_to_do.py` pins the
  new metric to `PushDeliveryMetrics`, the name to the set of alarms, and the window to
  five ticks of the scheduler's own default, and requires the runbook to quote the same
  expression — nine tests green. DEPLOYMENT.md's rule count and both mail paragraphs
  follow.)

## Epic 42 — The Settings That Do Not Need a Letter

Every dial in the product is reachable from the screen except the three mail dials:
their only entrance has been the signed page in a letter's footer. A reader who
deleted the letters -- or who never waited for a Monday -- had no way back, even
though the state was sitting in their own account.

- [x] **42.1** The signed-in reader answers for the mail settings.

  (`GET /api/v1/me/mail/settings` answers `{url, weekly, signals, reminders}`: the three
  booleans come from the same columns the sweeps read, and `url` is the very page
  `MailLinks` signs for the letters. The route sits under `/me` rather than `/mail`
  because that prefix is `permitAll` for the anonymous page -- a route added there
  would be public until it was moved -- so the session is the credential, and the
  answer is `no-store` and `noindex` because the address it carries is one too. The
  settings page grows a mail card beside the calendar card: each dial's state with
  On/Off, the signed address with a copy button, and a link that opens the page the
  letters open, so the buttons a mailbox would press are one click away. A failed read
  is a sentence, not blank switches. 4 backend tests and 2 frontend hook tests; API.md
  and DEPLOYMENT.md follow.)

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
