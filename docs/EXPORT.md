# Export & Portability — Epic 13

A personal job-search OS is only as trustworthy as the user's ability to leave
with their data. This document locks the export/import contract implemented in
`ai-service/app/features/export.py` (internal-only; the backend bridge fills the
two reserved sections).

## Scope

| Item | Status | Owner |
|---|---|---|
| 13.1 JSON + readable export of ai-service-readable data | **done (ai-service half)** | ai-service |
| 13.1 PDF rendering of the readable export | pending | downstream generator |
| 13.2 Idempotent re-import (upsert/delete plan) | **contract done** (pure diff + validate) | backend (writes) |
| 13.3 Right-to-be-forgotten / anonymized export | **done (anonymize + validate)** | ai-service |
| `applications` + `growth_plans` sections | reserved (absent) | backend bridge |

## Bundle schema

```jsonc
{
  "schema_version": "1.0.0",
  "generator": "ai-career-os",
  "generated_at": "2026-10-14T00:00:00+00:00",
  "user": { "id": "<uuid>", "anonymized": false },
  "manifest": {
    "schema_version": "1.0.0",
    "generator": "ai-career-os",
    "counts": { "profile": 1, "resumes": 1, "knowledge": 1,
                "job_descriptions": 1, "interviews": 1, "memories": 1 },
    "content_hash": "<sha256 over data>",
    "anonymized": false
  },
  "data": {
    "profile": { ...user_profiles row... },
    "resumes": [ { ...resume_versions joined resumes... } ],
    "knowledge": [ { ...documents metadata + excerpt... } ],
    "job_descriptions": [ { ...job_jds row... } ],
    "interviews": [ { ...interview_sessions joined jobs/companies..., "turns": [...] } ],
    "memories": [ { ...user_memories row... } ]
    // "applications" and "growth_plans" are RESERVED — absent until the bridge.
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
contract is held offline (20 tests in `tests/test_export.py`). **No route is
registered** — this module stays internal-only until the backend bridge exposes
the export endpoint and supplies `applications` / `growth_plans`.
