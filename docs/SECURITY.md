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
  - `/api/v1/auth/**` — 10/min per client IP.
  - AI-costing paths — 30/min per user. This is an explicit list
    (`RateLimitFilter.isAiCost`), not a prefix sweep: it covers the `/ai` SSE
    routes **plus** `/copilot` (the agent turn, the single most expensive call),
    `/interview`, `/jds`, `/knowledge/text`, `/resumes/{id}/parse` and
    `/jobs/{id}/(match|tailor|cover-letter)`. Cheap reads (search, listings,
    dashboards) are deliberately excluded so browsing is not throttled. Covered by
    `RateLimitFilterTest`.
  - **Fails open** when Redis is unavailable, logged at WARN — the limiter never
    locks anyone out. The client timeout is pinned to 500ms so that branch is
    actually reached promptly: with the defaults in effect a Redis outage left
    every endpoint unable to answer within 40s, which locked out exactly the users
    fail-open exists to serve. Measured now: `/health` `200 degraded` in 0.51s and
    `/auth/login` `401` in 1.20s while Redis is stopped.

## PRD §30 review

Audited against the eleven areas the PRD calls out. Findings are stated with their
residual risk rather than as a clean bill of health.

| Area | Result |
| --- | --- |
| SQL injection | **Clear.** Only four native queries exist (`JobSearchRepository`, `DashboardRepository`, `SearchRepository`); every value is bound as a parameter and only placeholder *indices* (`${len(args)}`) and an `int` limit are interpolated. `ORDER BY` cannot be parameterised, so it resolves through a whitelist map, not the request string. |
| XSS | **Clear.** No `dangerouslySetInnerHTML` / `innerHTML` anywhere in the frontend; React escapes all model- and user-derived text. |
| CSRF | **Not applicable by design.** No cookie credentials — the access token travels in `Authorization`, which a cross-site form cannot set. Spring CSRF is disabled for that reason, not by omission. |
| SSRF | **Clear.** `externalUrl` on a job is stored and displayed but never fetched. The only outbound HTTP is to the configured LLM/embedding provider, whose endpoint comes from env, not from user input. |
| Prompt injection | **Mitigated.** Untrusted resume/JD/web text is fenced by `wrap_untrusted` before entering a prompt, the system prompts state that fenced blocks are data, and generation passes a no-fabrication verifier. A safety scenario is pinned in the agent eval set (`tags=["safety","injection"]`). Residual risk: prompt injection is mitigated, never eliminated — treat generated text as untrusted on display. |
| File upload | **Clear.** `storage/FileValidator` sniffs magic bytes (PDF `%PDF`, DOCX `PK\x03\x04`, UTF-8 text), caps size at 20 MB, and rejects anything else. Objects land in a private MinIO bucket under a random key; the original filename never becomes a path. |
| Authorization bypass | **Clear.** Protected routes require a validated JWT; `/api/internal/**` is guarded by `InternalApiFilter` and ai-service by `X-Internal-Token`. |
| Sensitive data leakage | **Clear.** No token/password/secret is logged (the only auth log line records a user id). Password hashes and refresh-token hashes are never serialised into a response DTO. Residual risk: `agent_traces` intentionally stores prompt/answer previews for the user-facing activity view — it is PII by nature and inherits whatever retention the DB has. |
| IDOR | **Clear.** User-owned lookups go through `findByIdAndUserId` (`requireResume`, `requireVersion`, `ApplicationService.require`, `ConversationService.requireReadOnly`). Bare `findById` calls are either shared entities (jobs, companies) or ids obtained from an already user-scoped parent. |
| API abuse | **Improved, see below.** |
| Rate limiting | **Gap found and fixed, see below.** |

### Findings

1. **Rate limiting did not cover the expensive endpoints (fixed).**
   `ruleFor` only matched `/api/v1/ai/**`, so `/copilot/chat` — an agent turn that
   can run eight model calls plus tool work — and every other blocking AI endpoint
   (`/interview`, `/jds`, `/jobs/{id}/match|tailor|cover-letter`,
   `/resumes/{id}/parse`, `/knowledge/text`) were unthrottled. Coverage now
   includes them, with `RateLimitFilterTest` pinning the classification.

2. **`X-Forwarded-For` is trusted unconditionally (residual, deployment-dependent) — verified.**
   `clientIp` reads the leftmost `X-Forwarded-For` entry. Behind a proxy that
   *overwrites* the header this is correct and is what `RateLimitIT` exercises. If
   the backend is ever exposed directly, a client can rotate a spoofed
   `X-Forwarded-For` to get a fresh auth bucket per request and defeat login
   throttling entirely.

   Measured against the running stack with `RATELIMIT_AUTH_PER_MINUTE=3`: with no
   header the fourth and fifth requests returned **429**; six requests sent with
   `X-Forwarded-For: 203.0.113.{1..6}` returned **401 six times**, and Redis then held
   seven `ratelimit:auth:*` keys — one per spoofed address plus the real client. The
   bypass is not theoretical, and it needs no tooling beyond `curl`.

   **Requirement: the backend must sit behind a reverse proxy that sets (not appends)
   `X-Forwarded-For`.** Not changed in code because removing the header trust would break
   the documented proxy deployment; flagged here so the deployment posture is explicit.
   If the service is ever run without that proxy, this becomes the first thing to fix.

3. **A Redis outage used to be an availability outage — fixed by client timeouts.**
   The limiter fails open by design, but a request still has to *reach* that branch.
   With Redis stopped and the client unconfigured (Lettuce's defaults in effect),
   `/api/v1/health` and `/api/v1/auth/login` both failed to answer within 40s, against
   0.06s and 0.23s with Redis up. An outage therefore locked out exactly the users the
   fail-open policy exists to keep served.

   `spring.data.redis.timeout` and `connect-timeout` are now **500ms** (overridable via
   `REDIS_TIMEOUT` / `REDIS_CONNECT_TIMEOUT`). Redis backs only the rate limiter and the
   health ping, so failing fast costs nothing else. Re-measured with Redis stopped:
   `/api/v1/health` answers `200 {"status":"degraded","redis":false}` in **0.51s** and
   `/api/v1/auth/login` answers `401` in **1.20s** — which is what "fails open" was
   always meant to mean. Restoring Redis returns `ok`/`redis:true` with no restart.

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
