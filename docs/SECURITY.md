# Security model

Two trust boundaries: **user → backend** (public API) and **backend → ai-service**
(internal). The frontend only ever talks to the backend; ai-service is never
reachable from a browser.

## User authentication (backend)

- Stateless bearer tokens; `SessionCreationPolicy.STATELESS` and Spring CSRF is
  disabled because there are no cookie-based credentials — a cross-site request
  cannot carry the `Authorization` header. See `config/SecurityConfig.java`.
- `auth/security/JwtAuthFilter` validates the access JWT on every protected
  route and populates the `@CurrentUser` principal used by controllers.
- Passwords hashed with **BCrypt `$2B`, strength 12** (`SecurityConfig.passwordEncoder`).
- Tokens (from `.env` / `AppProperties`):
  - `JWT_SECRET` — HS256 signing key, generate a 64+ char random string.
  - `JWT_ACCESS_TTL_MINUTES=15`, `JWT_REFRESH_TTL_DAYS=30`.
  - Refresh tokens are **hashed at rest** (`resume`/`auth` `TokenHasher`) so a DB
    leak does not expose usable tokens; reuse of a rotated refresh token is
    rejected and rotates the whole family (see `TokenRotationReuseTest`).
- Public (unauthenticated) routes: `/api/v1/auth/**`, `/api/v1/health`,
  OpenAPI/Swagger (`/v3/api-docs/**`, `/swagger-ui/**`), CORS preflight
  (`OPTIONS /**`), and the internal surface `/api/internal/**` (guarded below).

## Service-to-service authentication (ai-service)

ai-service is internal-only and gated by `core/deps.require_internal`:

- Every `/internal/*` request must carry `X-Internal-Token` equal to
  `INTERNAL_API_TOKEN` (shared secret between backend and ai-service), else `401`.
- It must also carry `X-User-Id` — the backend forwards the authenticated user,
  and ai-service **scopes every retrieval and write to that `user_id`**. Missing
  `X-User-Id` is a `400`. `X-Run-Id` links traces to an observability run.
- `backend → ai-service` calls add these headers in `ai/HttpAiServiceClient`; the
  reverse (`ai-service → backend`, e.g. `/api/internal/*` callbacks) is guarded by
  `auth/security/InternalApiFilter` on the backend side.

## Data isolation

Retrieval, matching, resume tools and every RAG query filter by the caller's
`user_id` — see [RAG.md](RAG.md). One user's evidence chunks are never returned
into another user's prompt.

## Prompt-injection defense (ai-service)

Untrusted, user-/web-sourced content (uploaded resumes, company text pulled from
the web, JD bodies) is wrapped by `core/ai.wrap_untrusted(label, content)` before
it is placed in a model prompt, so the model is told the text is data, not
instructions. Generation features additionally run a **no-fabrication verifier**
(`features/tailor.verify_no_fabrication`, covered in `tests/test_core_modules.py`)
that rejects invented skills/numbers not present in the source evidence.

## Transport & headers

- CORS is allow-listed from `APP_CORS_ORIGINS` (default
  `http://localhost:3000`); methods `GET/POST/PUT/PATCH/DELETE/OPTIONS`; headers
  `Authorization`, `Content-Type`, `X-Internal-Token` only.
- All Docker service ports bind `127.0.0.1` (see `docker-compose.yml`) so nothing
  is exposed on the host network by default. Put TLS behind a reverse proxy in
  production.
- `ratelimit/RateLimitFilter` applies a Redis-backed sliding-window limit; it
  runs after JWT so AI-heavy endpoints can key limits off the user id.

## Error envelope

Auth failures and API errors share one shape so clients never parse stack
traces: `{ success: false, error: { code, message, details[] } }` (written by
`common/EnvelopeJson` / `EnvelopeAdvice`). Codes include `UNAUTHORIZED`,
`FORBIDDEN`, `NOT_FOUND`, etc.

## Production checklist

- Set a unique, long `JWT_SECRET` and `INTERNAL_API_TOKEN`; never reuse the
  `.env.example` values.
- `APP_ENV=prod` (this also hard-blocks the `mock` LLM provider at boot).
- Use a real embedding provider, not `hash`.
- Terminate TLS at a proxy and restrict `APP_CORS_ORIGINS` to your real domain(s).
- Rotate the MinIO and Postgres passwords; keep the buckets private (the
  `minio-init` step sets the app bucket to `private`).
