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

## The bridge (2026-10-20)

The engines were internal-only until now; the routes that reach them are:

| Route | Body | Answers |
|---|---|---|
| `POST /api/v1/data-portability/export` | `{anonymized?}` | the bundle, with its content hash |
| `POST /api/v1/data-portability/import-plan` | `{bundle, existing?}` | the per-item create/update/delete plan, with the counts |
| `POST /api/v1/data-portability/import-apply` | `{bundle}` | what each section wrote, and which ones were left alone |
| `POST /api/v1/data-portability/redact` | `{bundle, drop?}` | the bundle with the named sections removed and the hash recomputed |

The frontend's `/data` page drives all four: export (plain or anonymized),
download the JSON, drop sections before sharing, and paste a bundle back to
preview what a re-import would write — then to run it.

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

What applies today: the profile, the applications and the stored growth runs.
What does not: the resumes and the knowledge base, because restoring a resume
means re-ingesting a document into storage and the vector store — a pipeline of
its own, not a row write.

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

## Bundle schema

```jsonc
{
  "schema_version": "1.1.0",
  "generator": "ai-career-os",
  "generated_at": "2026-10-20T00:00:00+00:00",
  "user": { "id": "<uuid>", "anonymized": false },
  "manifest": {
    "schema_version": "1.1.0",
    "generator": "ai-career-os",
    "counts": { "profile": 1, "resumes": 1, "knowledge": 1,
                "job_descriptions": 1, "interviews": 1, "memories": 1,
                "applications": 12, "growth_plans": 3 },
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
    // The two the BACKEND owns — the bridge hands them over, and the hash
    // covers them like every other section.
    "applications": [ { ...applications row... } ],
    "growth_plans": [ { ...growth_plans row... } ]
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

`anonymize(bundle, drop=("email","display_name","phone","address"))` returns a
copy with those profile fields set to `null`, flips `anonymized` on `user` and
`manifest`, and re-stamps the content hash. Useful both for a privacy-first
export and as the right-to-be-forgotten surface.

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
