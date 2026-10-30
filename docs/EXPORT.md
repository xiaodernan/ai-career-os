# Export & Portability — Epic 13

A personal job-search OS is only as trustworthy as the user's ability to leave
with their data. This document locks the export/import contract implemented in
`ai-service/app/features/export.py` and bridged through
`POST /api/v1/data-portability/*` (the backend owns the `applications` and
`growth_plans` sections).

## Scope

| Item | Status | Owner |
|---|---|---|
| 13.1 JSON + readable export of ai-service-readable data | **done** | ai-service + backend bridge |
| 13.1 PDF rendering of the readable export | pending | downstream generator |
| 13.2 Idempotent re-import (upsert/delete plan) | **done** (plan emitted; the apply step is the backend's) | backend (writes) |
| 13.3 Right-to-be-forgotten / anonymized export | **done** (anonymize + validate + section redaction) | ai-service + backend bridge |
| `applications` + `growth_plans` sections | **done** (shipped in the bundle since 1.1.0) | backend bridge |
| `notes` + `contacts` sections | **done** (shipped in the bundle since 1.2.0) | backend bridge |
| `conversations` + `saved_jobs` + `saved_searches` + `ingestion_feeds` + `inbound_mails` sections | **open** (measured 2026-10-30; Epic 40) | ai-service + backend bridge |

## The bundle is not everything yet (measured 2026-10-30)

The page says "Export everything", and the bundle still has five gaps. They were
measured by reading the ten sections against every table the migrations create,
and each is the reader's own content or standing choice:

| Table | What it holds | Why it belongs |
|---|---|---|
| `conversations` + `messages` | the copilot chats: the reader's questions, the answers, the artifacts built from their material | the reader's own words |
| `saved_jobs` | a bookmark and the note beside it | the reader's shortlist |
| `saved_searches` | the standing queries the morning sweep speaks for | the reader's standing question |
| `ingestion_feeds` | the sources the ingester is pointed at | the reader's configuration |
| `inbound_mails` | the letters a provider forwarded, their reading and the application each was filed on | the reader's correspondence |

What stays out is bookkeeping rather than content: tokens and sessions, MFA
secrets, push subscriptions, notification read state, mail preferences, usage
events and agent runs, digests and nightly reports — they describe what the
account did, not what it holds. Epic 40 carries the five sections end-to-end
(export, anonymize, readable half, plan, apply) under schema 1.3.0, and its last
unit makes the distinction a census so a future table cannot land on the wrong
side of it.

## The bridge (2026-10-20)

The engines were internal-only until now; the routes that reach them are:

| Route | Body | Answers |
|---|---|---|
| `POST /api/v1/data-portability/export` | `{anonymized?}` | the bundle, with its content hash |
| `POST /api/v1/data-portability/import-plan` | `{bundle, existing?}` | the per-item create/update/delete/skip plan, with the counts |
| `POST /api/v1/data-portability/import-apply` | `{bundle}` | what each section wrote, and which ones were left alone |
| `POST /api/v1/data-portability/redact` | `{bundle, drop?}` | the bundle with the named sections removed and the hash recomputed |
| `POST /api/v1/data-portability/render` | `{bundle, format?}` | the readable document — HTML, Markdown, or PDF bytes |

The frontend's `/data` page drives all five: export (plain or anonymized),
download the JSON, drop sections before sharing, paste a bundle back to
preview what a re-import would write — then to run it — and open the
print-ready view of the whole thing.

### The readable half (13.1, the PDF)

`render` answers a self-contained, print-ready document: A4, monochrome,
page-break-friendly, and every field HTML-escaped — the bundle is user data
and is treated as untrusted on render, exactly like generated text is on
display elsewhere in the product. The browser's own "save as PDF" is the PDF,
so the optional `weasyprint` converter is a convenience rather than a
requirement; a build without it answers the HTML and says why the PDF is not
there.

### The apply is real (2026-10-20)

The plan was always only a plan. `import-apply` now executes it: the backend
computes the plan, then runs the ops against the tables it owns, and the answer
says what was written **and names every section it left alone with the
reason**. A partial restore is visible rather than reported as a success.

Two rules make it safe:

- **Only the caller's own rows are touched.** Every read and every write is
  scoped by the user id, so a bundle naming another user's rows finds nothing
  to change rather than writing into someone else's account.
- **Every section is applied.** The resumes and the documents re-enter the
  ingestion pipeline, the memories upsert on their key, and the rest are row
  writes — every section of the bundle has a writer, so the answer's
  `skipped` list only ever names a section the bundle carried no rows for,
  and the reason says so. An omission is visible rather than silent.

What applies today: every section.

- The profile, the applications, the stored growth runs, the job
  descriptions and the interviews are row writes. The analyst does not run
  again over a posting and the interviewer does not question the user a
  second time: the bundle carries the parsed result and the whole
  transcript, so the user's own reading of a posting and the answers they
  gave come back as they were.
- The resumes and the knowledge base are re-ingested. A restored resume is
  a *new* resume with the same content, because its id is the key its
  knowledge chunks and its versions hang off and the ingestion pipeline
  mints those — reusing an old id would leave two documents' chunks
  pointing at one row. A restored document is re-ingested as a note: the
  bundle carries a document's metadata and its excerpt, not its whole
  body (the body is in the object store).
- The long-term memories come back too, upserted on the same (kind, key)
  the extraction path uses — so the restore is idempotent, and a memory
  the user has since corrected is overwritten with the correction rather
  than duplicated. They are the user's own statements about their skills,
  their goals and their preferences, the export carries them
  deliberately, and the settings page lets the user correct or delete any
  of them.

A section the plan names but the bundle does not carry the rows for is
reported as skipped, with the reason. So is a section whose rows are
malformed. A restore that quietly dropped something is the failure this
exists to catch.

### An unchanged row is not written (2026-10-28)

The page's copy promises that "unchanged rows are skipped", and the plan used
to answer `update` for every row it already knew — so the promise was kept by
the `content_hash` and not by the plan, and the preview's own counts said
"2 to update" about a restore with nothing to do. The plan now compares each
bundle row with the caller's current row and emits a `skip` when they are the
same; `import-apply` takes that at its word, writes nothing for it, and counts
it as `unchanged`.

The comparison needed two things to be true:

- **The same serializer on both sides.** The `existing` half is now read
  through `ExportService.backendSections`, the method that builds the bundle's
  backend sections, instead of a hand-written summary of three columns. A row
  serialized two different ways always looks changed — and the profile used to
  travel as the JPA entity, whose fields are camelCase, while the bundle's
  profile is the engine's snake_case `SELECT *`. Both are pinned by tests.
- **The stamps are not content.** `created_at` and `updated_at` are set by the
  database, so the first apply bumps them; a comparison over whole rows would
  find every row it had just written changed, write it again, and never once
  answer "skip". The comparison covers the fields the apply writes, which is
  what "unchanged" means.

The operator's CLI (`python -m app.ops.restore_plan`) reports the fourth
count too, so a dry run of a backup against the same backup says
`skip 2` rather than `update 2`.

### The restore can retire what it can name (2026-10-28)

The plan is a comparison, so both halves have to read the same state. The
browser's preview sends no state, and the backend used to default to
"nothing" — every row a create, counts about a workspace nobody has, which
the apply then contradicted. `import-plan` reads the caller's workspace when
the caller sends no `existing` now, and the engine's route fills the six
sections it owns itself, overlaying only the caller's gaps (the caller's
profile wins). A preview and an apply compare the same two documents.

That made the sections outside the old current state reachable — and with
them the question this feature opened with: what does a restore do with a
row the bundle no longer carries? The answer differs by section, because the
restore does:

- **The sections matched by id can retire a row.** The profile, the
  applications, the growth runs, the notes, the people the reader knows, the
  postings and the interviews keep the bundle's ids through the restore (or
  find the row the id already names), so a row the bundle omits is a row the
  reader took out of the document they asked to restore. It is deleted —
  scoped to the caller, and an interview is retired whole, its transcript and
  its report with it.
- **The sections the restore re-mints cannot.** A restored resume is a new
  resume; a restored document re-enters the ingestion pipeline; a memory
  upserts on its (kind, key). Their ids mean nothing at the target, so "the
  bundle omits this id" says nothing about what the target holds. They are
  matched by content instead — a resume by its title and its text, a
  document by its title and its excerpt, a memory by its (kind, key) — and
  they never delete: the absence of a row whose id is not shared is not a
  statement the restore can keep.
- **A row the apply could not write is not planned, and not deleted.** A
  resume with no title or no text, a document with no excerpt, a memory with
  no content, a posting with no text, a person with no name: the apply skips
  these (a row it cannot restore is not a row it may claim), so the plan does
  not name them — and their existing counterparts are not retired on their
  absence either.
- **The comparison covers exactly what the apply writes.** Ids, ownership
  and the database's stamps are stripped at every level, the interview's
  child bookkeeping with them, and so are the links the restore does not
  reproduce (the posting's job, the interview's job) and a memory's
  `last_used_at`. A JSON text column on either side parses before it
  compares — a bundle written before the boundary decoded `jsonb` carries
  text — and a number compares as a number, so `3` and `3.0` are one value.
  Each of these was a way for a row that was already the same to be
  announced as changed, and to be written again forever.

An interview that did change is replaced, not merged: the bundle carries the
transcript whole, so the restore is the document a second time — a turn the
bundle no longer names is a turn the restore was asked to take back, and the
report is about the answers, so it is rewritten with them.

### The bundle is complete (1.1.0)

Six of the eight sections are the ai-service's own. The other two —
`applications` and `growth_plans` — are the **backend's**: it writes those rows,
so the ai-service cannot read them. The bridge reads them and hands them over
in the export request, and the ai-service hashes the whole document in one
place. A bundle without them was a reading list and not a record of the search.

The required set for validation is read off the bundle's **own** schema
version: a 1.0.0 backup predates the two sections and is still a valid bundle,
while a 1.1.0 one missing them was truncated. Rejecting the old backups would
have cost every user their archive the day the format grew.

### The reader's own words (1.2.0)

The bundle carried every table the *engines* read and neither table the reader
typed in. Their notes — the salary band they wrote down, the company fact they
wanted to remember — lived in `user_notes`, and the people they know lived in
`contacts`; no section of the bundle carried either. So a reader who kept
their research in a note and then exported their data did not get that note
back.

Since **1.2.0** the bundle carries `notes` and `contacts` as well, and the
browser offers to redact them like any other section. The required set is
still read off the bundle's own version, and the version is compared as
*numbers* now: `"1.10.0"` is after `"1.9.0"`, and a string comparison says
otherwise. A 1.1.0 backup still validates with its eight sections; a 1.1.5
one is held to the 1.1.0 sections rather than to the newest.

### The restore does not write over somebody else's rows

A bundle's ids are the source's, and the restore keeps them — so the links
inside the bundle still point where they did, and a same-account restore
updates its own rows in place.

But an id that belongs to *another account's* row must not be written into.
It was: restoring a colleague's export changed the colleague's data (a note
they had edited since the export went back to the exported text) and gave the
caller nothing of their own, while the answer said **created**. The id is now
kept only when it is free and minted when it is not: the restore still lands
the rows, and it no longer lands them on top of somebody else's.

## Bundle schema

```jsonc
{
  "schema_version": "1.2.0",
  "generator": "ai-career-os",
  "generated_at": "2026-10-20T00:00:00+00:00",
  "user": { "id": "<uuid>", "anonymized": false },
  "manifest": {
    "schema_version": "1.2.0",
    "generator": "ai-career-os",
    "counts": { "profile": 1, "resumes": 1, "knowledge": 1,
                "job_descriptions": 1, "interviews": 1, "memories": 1,
                "applications": 12, "growth_plans": 3, "notes": 4,
                "contacts": 9 },
    "content_hash": "<sha256 over data>",
    "anonymized": false
  },
  "data": {
    "profile": { ...user_profiles row... },
    "resumes": [ { ...resume_versions joined resumes... } ],
    "knowledge": [ { ...documents metadata + excerpt... } ],
    "job_descriptions": [ { ...job_jds row... } ],
    "interviews": [ { ...interview_sessions joined jobs..., "turns": [...],
                      "evaluation": { dims, summary, trajectory } } ],
    "memories": [ { ...user_memories row... } ],
    // The four the BACKEND owns — the bridge hands them over, and the hash
    // covers them like every other section.
    "applications": [ { ...applications row... } ],
    "growth_plans": [ { ...growth_plans row... } ],
    // And the two the reader typed into: their own words, and the people
    // they know. They are the first things a reader loses when they leave.
    "notes": [ { ...user_notes row... } ],
    "contacts": [ { ...contacts row... } ]
  }
}
```

## Determinism (the load-bearing property)

`content_hash` is computed over `data` **only** — never over `generated_at` or
the hash itself — so re-exporting unchanged data yields the same hash. That is
what makes the re-import idempotent and the backup snapshot detectable as
"nothing changed". `canonical_json` sorts keys and serializes datetimes to ISO,
so equal data hashes equally across runs and machines.

## A JSON column is an object in the bundle (2026-10-28)

The export read its rows with `asyncpg`, which hands a `jsonb` column back as
the text it holds. The bundle passed that text straight through, so the file
carried the parsed posting, a session's config, every answer's evaluation and
the interview report as escaped strings. The printable documents did not
notice — they read the columns that are text anyway — but the **restore**
did: it writes those columns back through a map, and a map is not a string.
A restored job description came back with its raw text and none of the
analyst's reading; a restored interview came back as turns with the config
and the per-answer evaluations dropped.

The fix is at the boundary: the export decodes the columns the schema calls
`jsonb` (`app/features/export.py`'s `_json_value`) and the backend parses a
JSON string as a fallback, so a bundle written by an older build restores
with its objects intact. Passing the string through was never a format
decision — it was a driver's return shape leaking into a document.

The session's report was missing for a second reason: it lives in
`interview_evaluations`, which the export never read. Each session now
carries `evaluation` (`dims`, `summary`, `trajectory`) — the same three
fields the restore writes — and the anonymized export blanks it, because the
summary quotes the reader's answers back the way the growth report quotes
their material. The session's own `company_name` column is no longer
shadowed by the joined company's name: the join was a decoration for the
document, and a restore that read it wrote the decoration into the column.

## Import contract (13.2)

- `validate_bundle(bundle)` returns `[]` for a well-formed bundle and lists every
  violation otherwise: missing top-level / manifest keys, missing data sections,
  or a `content_hash` that no longer matches `data` (tamper detection).
- `diff_bundles(old, new)` returns, per section, `added` / `removed` / `changed`
  lists of stable item keys (prefers `id`, else hashes the item). The bridge
  upserts `added` + `changed` and deletes `removed`. Because `content_hash` is
  stable, a no-op re-import produces empty diffs.

## The readable half (13.1)

The export has two faces: the JSON a machine reads and the document a person
reads — the Markdown view and the print-ready HTML.

The document was Chinese-only, so an English reader's printable document was a
Chinese document; and the words live in a server-side module, in a document,
so the copy census could not see them either — they are not on a screen. The
words now live in one table (`app/features/export_words.py`), in every language
the readable half ships in, and the request says which one the reader wants:
the bundle carries the data and the view carries the words. An unknown
language is English rather than a guess — the table is the product's account
of itself, and a language it does not have is one it must not pretend to.

The document also left out two sections: the notes the reader typed and the
people they know. A section the bundle carries and the document does not is a
section the reader cannot read, and the counts still said it was there. The
gate holds the table against **every section the bundle carries**, so a
section added later cannot be left out of the document.

The Markdown view was the second half of the same defect, twice over: it was
Chinese-only, and it left out four sections the bundle carries — the pipeline
the candidate worked, the growth runs they built, the notes they typed and
the people they know. It reads the same table now, in every language, and it
carries every section. The gate for it is a census rather than a list: **the
English document has no Chinese in it at all**, so a sentence nobody thought
of cannot slip through.

The Markdown has a surface now (2026-10-28). It was a library function
nothing called: the render route served the HTML and the PDF, the bridge had
no field for it and the export page had no Markdown affordance, so the
operator's quick look existed only for someone already inside Python.
`format: "markdown"` is a format of the route, the bridge hands it through
unchanged, and the page's "Download Markdown" saves `career-os-export.md` —
in the reader's language, because the words come from the same table.

And the route that serves it never worked: the render module was never
imported by the module that serves the route, so every call raised a
`NameError` and the "Print view" button had never done anything but show an
error toast. The unit tests called the *function*; nothing called the *route*.
The gate now calls the route the way the bridge calls it.

## Anonymize (13.3)

There are two ways to leave with your data. The **redaction** drops whole
sections; the **anonymized export** keeps the shape and takes the people out
of it.

It used to take nobody out. It blanked four field names on the profile —
`email`, `display_name`, `phone`, `address` — and the profile has carried
none of them for as long as the export has existed, so the button called
"Export anonymized" exported the reader's own uuid, the links to their
profiles, their resume's plaintext, every answer they gave an interviewer,
and (since 1.2.0) the notes they typed and the people they know, with their
email. Worse, the printable document *believed* the file was anonymized: it
prints "（已匿名）" beside the reader's id whenever the manifest says so.

So there is now one policy, per section, in `ANONYMIZED_FIELDS`: the fields
that name a person — the reader, or somebody the reader knows — or that are
the reader's own words. The strip happens where the bundle is **built**, so
the flag and the file cannot disagree, and the hash is re-stamped over what
is left. The shape stays: the counts still say what the file holds, and the
substance of a job search — the posting, the headline, the years — is still
in it, because an export that leaves nothing behind is not an export.

### The policy is a classification, not a list (2026-10-22)

A list of field names is a list of the names somebody thought of, and
everything else was the reader's by default. Proven against the running
system: the note's full text travelled out inside the knowledge row's
`meta` — a JSON bag whose *name* says nothing about what is in it — along
with the note's title and its tags; the reader's own uuid sat in every
job-description row and again inside the storage key of every uploaded
document (the key is a path into their own bucket, and begins with their
id); and every interview turn carried their uuid and the evaluation, which
quotes their answer back.

So the policy is a **classification** now, and it covers every column the
export really carries:

- **the reader's** — their identity, their own words, or a pointer into
  their own storage (`ANONYMIZED_FIELDS`);
- **the substance** — the posting, the title, the company, the status, the
  counts, the timestamps, the ids;
- **a bag** — a column whose *inside* holds the reader (`meta` on a
  document, the turns inside an interview session). The bag keeps its
  shape — the document still says it was a *note* — and loses its text.

The gate holds that classification against the **real sources**: the real
tables, the real queries the export runs, the real rows the backend writes.
A fixture shaped like the old thing is what let the first version pass, so
the fixture is now built out of the sources rather than written by hand. The
last check is a census rather than a list: a marker goes into every column
the classification calls the reader's, the anonymized file is searched for
it, and **nothing survives** — not in a named field, not in a bag, not in a
row inside a row. Half of an anonymization is worse than none: it looks like
the file was cleaned.

## Redaction (13.3)

`redact_bundle(bundle, drop=[...])` removes whole sections from a bundle the
reader is about to hand to somebody else. Four rules, and each one exists
because the version without it broke the feature in a way nobody would have
noticed until the file was already sent:

- **The dropped section is absent, and the manifest says so.**
  `manifest.redacted_sections` names it. A withheld section and a section that
  was always empty are different facts, and only the manifest tells them apart.
- **The counts are recomputed over what is left.** They are the badges under
  the hash on the export screen and the last line of the printable document. A
  count that still claims the dropped rows tells the reader their pipeline is
  in the file they are about to share — the opposite of what they asked for.
- **The bundle stays valid.** `validate_bundle` treats a section the manifest
  records as withheld as *not missing*: it was removed on purpose, so it is not
  a truncated bundle. Without this rule the redaction produced a file the
  product's own restore path rejected — the reader redacted the bundle so
  that somebody else could import it, and the import said the file was broken.
- **A withheld section gets no plan.** The import plan reads "the bundle
  carries no rows of this section" as "delete every row of this section at the
  target". For a section the sharer *withheld* that reading destroys the
  target's own data on the strength of a section the sharer chose not to
  share. So the redacted sections get no ops at all — a section that was
  genuinely empty still plans its deletes, and the difference is the
  manifest's record rather than the emptiness.

`docs/API.md` names the route; the browser drives it from `/data`.

## API surface (all pure, no I/O at import time)

| Function | Purpose |
|---|---|
| `gather_raw(user_id)` / `export_bundle(user_id, *, anonymized=)` | fetch + assemble |
| `build_bundle(user_id, raw, *, anonymized=)` | pure assembly |
| `canonical_json` / `content_hash` | deterministic serialization + hash |
| `anonymize` / `diff_bundles` / `to_markdown` | 13.3 / 13.2 / readable |
| `serialize_bundle` / `parse_bundle` / `validate_bundle` | JSON + validation |
| `write_bundle` / `read_bundle` | file I/O |

The fetch functions are module-level and monkeypatched in tests, so the whole
contract is held offline (20 tests in `tests/test_export.py`). The routes are
registered in `app/api/features.py` behind `require_internal`, and the backend
bridges them at `POST /api/v1/data-portability/*` — so the module is no longer
internal-only, but the *engines* still are: nothing reaches them without the
shared secret, and the browser only ever sees the backend's own routes.
