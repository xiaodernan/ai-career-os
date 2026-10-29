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
  - Replacing a password — the emailed reset and the authenticated
    `PATCH /me/password`, which re-checks the current password — revokes every
    refresh token the account holds; access tokens are stateless and expire within
    `JWT_ACCESS_TTL_MINUTES`.
  - A refresh-token family is one signed-in device. Its first token records the
    user-agent and client address (truncated to 255/45 chars, both optional), and
    `GET /me/sessions` folds live tokens back into families so the account can
    recognise its own doors without the family id ever appearing in a letter or a
    log. `DELETE /me/sessions/{id}` closes one family and `DELETE /me/sessions`
    closes all; another account's family id answers the same 404 as an unknown
    one, so the endpoint cannot be used to probe for sessions. Revoking a session
    is the fastest account-holder response to a borrowed laptop: refresh stops
    immediately, and the thief's access token dies at its 15-minute horizon — the
    same bound every access token has, because tokens are stateless.
  - Moving the sign-in address (`POST /me/email-change`) costs the password and
    the new mailbox: the address on the account and the address being claimed
    each receive a letter, and nothing moves until the claimed mailbox follows
    its link (`POST /auth/email-change/confirm`, public because possession of the
    token is the proof, not a session). The row keeps only a SHA-256 hash of that
    token and the link lives a two-hour window, so a leaked database cannot
    answer it. A confirmed move revokes every refresh token, like a password
    change, and mails both addresses the outcome; a link that is unknown, spent,
    expired or ownerless is one `EMAIL_CHANGE_INVALID`, so the public route is
    no existence oracle.
- Public (unauthenticated) routes: `/api/v1/auth/**`, `/api/v1/health`,
  OpenAPI/Swagger (`/api-docs/**`, `/v3/api-docs/**`, `/swagger-ui/**`,
  `/swagger-ui.html` — `application.yml` serves them at `/api-docs` and
  `/api-docs/ui`, and the filter admits both spellings), CORS preflight
  (`OPTIONS /**`), the observability pair `/actuator/health` and
  `/actuator/prometheus` (read-only Micrometer metrics; restrict the scrape at
  the reverse proxy in production if metrics must not be public), the
  signed-link mail-settings page `/api/v1/mail/**` (its path is its own
  credential — an HMAC-SHA256 of the account id under `app.mail.link-secret`,
  compared in constant time; forge one and the route is a 404, but it still
  answers without a session so a mailbox can unsubscribe in one click), and the
  internal surface `/api/internal/**` (guarded below).

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

### Erasure

`POST /api/v1/me/erase` is the reader's exit. The account must present its password
and its own email typed back; then the objects named by its `documents.file_key`
rows are removed from the private bucket and the `users` row is deleted. Every
user-scoped table has carried `REFERENCES users(id) ON DELETE CASCADE` since V1,
so the remaining rows — profile, memories, resumes, applications, interviews,
conversations, chunks, feeds, notifications, digests, usage and refresh tokens —
leave in the same transaction. A storage failure aborts before the row is removed
(the account stays whole and retryable); access tokens are stateless and expire
within `JWT_ACCESS_TTL_MINUTES`, and every request they can still make finds no
account. Backups are outside the live system: a set taken before the request keeps
the rows and objects until its retention window passes (see DEPLOYMENT.md).

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
- `docker-compose.yml` publishes the host ports in its `ports:` blocks on `127.0.0.1`,
  so a development stack answers on the machine that runs it. The production override
  `docker-compose.prod.yml` republishes `backend` as `8080:8080` and `frontend` as
  `3000:3000` with no interface prefix, which Docker binds on every interface of the
  host, so a deployed stack answers to the network and the reverse proxy is not the one
  path in — `docs/DEPLOYMENT.md` carries the per-file reach tables. Close those two with
  a host firewall or a loopback override of your own unless the exposure is intended.
  `ai-service` stays reachable over loopback and inside the compose network. Put TLS
  behind a reverse proxy in production.
- Every answer from the Next shell carries `X-Frame-Options: DENY`,
  `X-Content-Type-Options: nosniff`, `Referrer-Policy:
  strict-origin-when-cross-origin` and a `Permissions-Policy` that denies the
  camera and geolocation but leaves the microphone to this origin — the
  interview page records with it. `frontend/next.config.ts` exports the list
  and `src/app/security-headers.test.ts` pins the rule Next reads, so the
  headers exist under `next start` and the E2E stack too, not only in a
  deployment's reverse proxy.
- `ratelimit/RateLimitFilter` applies a Redis-backed sliding-window limit; it
  runs after JWT so AI-heavy and mail-sending endpoints can key limits off the user id.
  `ruleFor` is the one author of a path's bucket: the ceiling, the identity and
  the Redis key prefix are all read off its answer.
  - `/api/v1/auth/**` — 10/min per client IP.
  - Mail-sending account routes — 5/min per account. `POST /me/email-change`
    (and its `/users/me/email-change` alias) asks the relay for two letters on
    every call, so an unthrottled route is a mailbox any signed-in account can
    point at an address it names. Both spellings are listed in
    `RateLimitFilter.sendsMail`; the bucket is keyed by the account id.
  - AI-costing paths — 30/min per user. This is an explicit list
    (`RateLimitFilter.isAiCost`), not a prefix sweep: it covers the `/ai` SSE
    routes **plus** `/copilot` (the agent turn, the single most expensive call),
    `/interview`, `/jds`, `/growth` (the 10.2 bridge — the aggregate report and the
    granular engines that will join under the prefix), `/knowledge/text`,
    `/resumes/{id}/parse` and
    `/jobs/{id}/(match|tailor|cover-letter)`. It also covers the three that spend
    money without living under an "AI-looking" path: `/jobs/import` (importing a JD
    runs the analyst) and `/knowledge/documents` and `/resumes/upload` (both embed
    every chunk of the document into pgvector). Left out, a scripted client could
    call those three without limit — the exact hole this list exists to close.
    Cheap reads (search, listings, dashboards) are deliberately excluded so browsing
    is not throttled. Covered by `RateLimitFilterTest`.
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
| SQL injection | **Clear.** Five native-query classes exist (`JobSearchRepository`, `SearchRepository`, `DashboardRepository`, and the two digest repositories that replaced the copilot sidebar's and the interview list's per-row reads — `ConversationDigestRepository`, `InterviewDigestRepository`); every value is bound as a parameter and only placeholder *indices* (`${len(args)}`) and an `int` limit are interpolated, both in `JobSearchRepository` and both derived from the server's own paging window. `ORDER BY` cannot be parameterised, so it resolves through a whitelist map, not the request string. The census is held by `test_the_native_query_census_matches_the_security_doc.py`, which fails when a sixth class appears or when this row stops naming the five. |
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

2. **`X-Forwarded-For` is only believed when a proxy is declared — fixed.**
   `clientIp` used to read the leftmost `X-Forwarded-For` entry unconditionally, so
   a service reached directly let a client rotate a spoofed header to get a fresh
   auth bucket per request and defeat login throttling. Measured against the running stack with `RATELIMIT_AUTH_PER_MINUTE=3`:
   with no header the fourth and fifth requests returned **429**; six requests sent with
   `X-Forwarded-For: 203.0.113.{1..6}` returned **401 six times**, and Redis then
   held seven `ratelimit:auth:*` keys — one per spoofed address plus the real
   client. The bypass needed no tooling beyond `curl`.

   The trust is now a deployment declaration: `APP_HTTP_TRUST_FORWARDED_FOR`
   (`app.http.trust-forwarded-for`, **off by default**). Only when it is on is the
   header read at all; off, the socket's address is the identity and the header is
   hearsay. When it is on, the **rightmost** hop is read — the one the trusted proxy
   itself wrote — rather than the leftmost, because a proxy configured with
   `$proxy_add_x_forwarded_for` appends to whatever the client sent, and the
   leftmost entry is then the client's fiction. Both shapes (overwrite and append)
   therefore name the address the proxy saw.

   `ForwardedAddressIT` speaks as a direct client: with the auth limit set to 2,
   two logins fill the socket's bucket and the third is **429** even though each
   carried a different `X-Forwarded-For`; a second socket address still has its own
   window. `ClientInfoTest` pins both modes, the rightmost hop, and the empty-header
   fallback; `RateLimitIT` and the rest of the suite exercise the declared-proxy
   topology. **Deployment requirement: behind the reverse proxy, set
   `APP_HTTP_TRUST_FORWARDED_FOR=true`** (see `DEPLOYMENT.md`); a service exposed
   directly must leave it off.

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

4. **A production boot used to accept the repository's published secrets — fixed.**
   `application.yml` interpolates `JWT_SECRET`, `APP_MAIL_LINK_SECRET` and
   `INTERNAL_API_TOKEN` from the environment but ships working defaults, and a deploy
   that forgot one booted fine on a value printed in this repository: access tokens
   anyone can sign, unsubscribe and mail-settings links anyone can forge, and an
   `/internal/*` surface anyone can call with the shared default. The ai-service had a
   preflight for the same class; the backend had nothing before its context existed.

   `APP_ENV` (bound as `app.deployment.env`, **`dev` unless set**) now arms
   `ProductionGuard`: with `env=prod` the bean refuses the context refresh when any of
   the three still holds a published literal (the `application.yml` default or
   `.env.example`'s), a `CHANGE_ME` value from `.env.prod.example`, or nothing at all.
   It names **every** offender in one `IllegalStateException`, so one restart fixes all
   three instead of three restarts finding them one by one. Non-prod boots are
   untouched — the example values are exactly what a dev checkout runs on. Both compose
   files already passed `APP_ENV`; for the backend it was a no-op until now.

   `ProductionGuardTest` has 11 cases: the pure decision table (dev, case/space, a lone
   override, blank, `CHANGE_ME`), a *drift* check that reads `application.yml` and both
   env examples so the guard's copies cannot go stale, an `ApplicationContextRunner`
   that proves a prod context fails and names all three (and that dev, or prod with real
   secrets, starts), and the `@Component` wiring. `DEPLOYMENT.md`'s checklist and the
   `APP_ENV` row now state the refusal.

### Dependency audits (2026-10-24)

`npm audit --omit=dev` carried a critical and a high through PostCSS — both fixed
(`f72eec5`): next to the 15.5.28 patch, plus an npm override pinning **every**
transitive copy at `^8.5.31` (the deepest one ships inside next's own bundle, so
no direct bump could reach it). Audit is now 0.

`pip-audit` flags six starlette advisories (PYSEC-2026-161/248/249/1942/2280/2281,
fixed across 0.49.1–1.3.1). **Assessed, not patched — deliberately.** Every one of
those advisories rides a surface this service does not mount: no `FileResponse` /
`StaticFiles` / `HTTPEndpoint`, no `request.form()` (multipart uploads land on the
Spring backend, which caps file counts in `FileValidator`), no `request.url.path`
trust. The pins exist because `fastapi==0.116.1` locks `starlette<0.42`, and the
fix train crosses two major versions on both packages — an attempted upgrade
(fastapi 0.161.1 / starlette 1.9) breaks the route-introspection the contract
gates read (`app.routes` no longer flattens included routers), which was verified
before reverting. The tracked path: land the fastapi migration on its own wave
(route-scanner support for `_IncludedRouter` first), then take the starlette fix
train. Until then, the exposure is theoretical for this deployment shape.

## Error envelope

Auth failures and API errors share one shape so clients never parse stack
traces: `{ success: false, error: { code, message, details[] } }` (written by
`common/EnvelopeJson` / `EnvelopeAdvice`). Codes include `UNAUTHORIZED`,
`FORBIDDEN`, `NOT_FOUND`, etc.

## Production checklist

- Set a unique, long `JWT_SECRET`, `APP_MAIL_LINK_SECRET` and `INTERNAL_API_TOKEN`;
  never reuse the `.env.example` values.
- `APP_ENV=prod` (this also hard-blocks the `mock` LLM provider at boot, and makes the
  backend refuse to start on any published, `CHANGE_ME` or empty signing secret —
  finding #4).
- Use a real embedding provider, not `hash`.
- Terminate TLS at a proxy and restrict `APP_CORS_ORIGINS` to your real domain(s).
- Rotate the MinIO and Postgres passwords; keep the buckets private (the
  `minio-init` step sets the app bucket to `private`).
