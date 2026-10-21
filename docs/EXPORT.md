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

## The bridge (2026-10-20)

The engines were internal-only until now; the routes that reach them are:

| Route | Body | Answers |
|---|---|---|
| `POST /api/v1/data-portability/export` | `{anonymized?}` | the bundle, with its content hash |
| `POST /api/v1/data-portability/import-plan` | `{bundle, existing?}` | the per-item create/update/delete plan, with the counts |
| `POST /api/v1/data-portability/import-apply` | `{bundle}` | what each section wrote, and which ones were left alone |
| `POST /api/v1/data-portability/redact` | `{bundle, drop?}` | the bundle with the named sections removed and the hash recomputed |
| `POST /api/v1/data-portability/render` | `{bundle, format?}` | the print-ready document — HTML, or PDF bytes |

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
- **A section is applied whole or not at all.** A section the backend cannot
  write yet — the resumes, the knowledge base, the job descriptions, the
  interviews — is reported as skipped rather than claimed.

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
    "interviews": [ { ...interview_sessions joined jobs/companies..., "turns": [...] } ],
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

## Import contract (13.2)

- `validate_bundle(bundle)` returns `[]` for a well-formed bundle and lists every
  violation otherwise: missing top-level / manifest keys, missing data sections,
  or a `content_hash` that no longer matches `data` (tamper detection).
- `diff_bundles(old, new)` returns, per section, `added` / `removed` / `changed`
  lists of stable item keys (prefers `id`, else hashes the item). The bridge
  upserts `added` + `changed` and deletes `removed`. Because `content_hash` is
  stable, a no-op re-import produces empty diffs.

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
