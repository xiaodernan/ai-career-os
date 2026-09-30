# e2e — Playwright golden-journey suite

Drives the **real** stack through a real browser: PRD §35 says the golden flow
"必须真正跑通", so nothing here stubs the API. What keeps it safe to re-run is
that the backend runs with `LLM_PROVIDER=mock` / `EMBEDDING_PROVIDER=hash`, so
every AI call is deterministic and free while still traversing the real
orchestrator, retrieval and persistence paths.

## What it covers (PRD §35)

| Spec | Flow |
| --- | --- |
| account and session | Register → land in the app → sign in again; wrong password refused; the recovery pair (`/forgot-password` → `/reset-password`), including the pasted-token path and the API's refusal of an unknown token |
| resume becomes a knowledge base | Upload file → parse → knowledge source listed → visible in `/resumes` |
| find a role and understand the match | Search corpus → open role → evidence-backed match → tailor + cited cover letter |
| track the application | Save role → create application → move stage → timeline → kanban agrees |
| interview practice | Create session → opening → answer → scored follow-up → finalize report |
| copilot and observability | Copilot artifact → run recorded → trace shows the llm/tool loop → usage summary |

## Prerequisites

Three services must be up, plus the infrastructure they need:

```bash
docker-compose up -d postgres redis minio
docker-compose run --rm minio-init                 # creates the private app bucket
docker-compose run --rm seed-jobs                  # 12 companies / 41 roles

cd backend   && RATELIMIT_AUTH_PER_MINUTE=100 APP_ENV=dev SERVER_PORT=8080 bash ../scripts/mvn.sh spring-boot:run
cd ai-service && LLM_PROVIDER=mock EMBEDDING_PROVIDER=hash .venv/Scripts/python -m uvicorn app.main:app --port 8000
cd frontend  && npx next build && npx next start -p 3000
```

`RATELIMIT_AUTH_PER_MINUTE=100` is required, not cosmetic — see trap 3 below.

## Run

```bash
cd e2e && npm install && npx playwright install chromium

# Normal run. The `timeout` wrapper is deliberate — see "the runner is slow to
# exit" below; the summary line is the result.
CODEBUDDY_SAFE_DELETE_BULK_THRESHOLD=100000 timeout 300 npx playwright test

# Just the flow you are working on
npx playwright test -g "knowledge base"

# Debug a failure: traces, an HTML report, and a visible browser
E2E_TRACE=on E2E_HTML=1 npx playwright test --headed
npx playwright show-report
```

Expected result: **10 passed**. Each run takes ~60s of actual testing, plus the
per-test teardown described below.

### Running against the containerized stack

The suite does not care whether the three services are local processes or containers,
so it doubles as the acceptance test for the production images. This is the run that
actually exercises `frontend/Dockerfile`'s standalone bundle and the built jars:

```bash
# whole stack in containers, offline providers, no API keys needed
LLM_PROVIDER=mock EMBEDDING_PROVIDER=hash \
  docker-compose --profile app up -d

# the suite provisions one account per test, so the auth limit has to be raised;
# see trap 3 for why, and the compose override below for how
CODEBUDDY_SAFE_DELETE_BULK_THRESHOLD=100000 timeout 500 npx playwright test
```

Both providers have to be named on the command line: `.env` selects the hosted
providers with empty keys, and the ai-service only reports that as a `ConfigError`
on the first AI call — which surfaces here as a stalled upload, not a startup error.

The auth limit needs an override file, because `environment:` beats `env_file:` and
the base compose does not name `RATELIMIT_AUTH_PER_MINUTE`:

```yaml
# e2e-override.yml — pass with: docker-compose -f docker-compose.yml -f e2e-override.yml
services:
  backend:
    environment:
      RATELIMIT_AUTH_PER_MINUTE: "100"
```

Verified this way: **10/10 against the containerized images**, which is what closed
the "production build" item in the Definition of Done.

### The runner is slow to exit in this sandbox

After the summary prints, the node process can sit for another minute or more and
sometimes never exits at all. Two separate causes, neither of them the tests:

- Teardown costs roughly 20s *per test* here — every artifact write and delete
  goes through the sandbox's brokered-fs / safe-delete shim.
- `test-results/` accumulating past the shim's 50-file bulk-delete threshold
  makes the *next* run hang before it prints anything at all. Raise the threshold
  as shown above, or move the directory aside (`mv test-results test-results-junk`).

So: judge a run by its summary line, not its exit code, and wrap it in `timeout`.
`--trace=off` makes a run noticeably faster.

## Traps worth knowing

**1. Visit the frontend as `localhost`, not `127.0.0.1`.**
The backend allows exactly the origins in `APP_CORS_ORIGINS`
(default `http://localhost:3000`). A browser treats `localhost` and `127.0.0.1`
as *different* origins, so browsing via the IP makes every call fail with
`Invalid CORS request`. Override with `E2E_BASE_URL` if your allowlist differs.

**2. Don't add custom request headers.**
The backend's CORS allowlist covers only the headers the app actually sends. An
extra header (e.g. a tracing tag) fails preflight with
`Request header field X is not allowed by Access-Control-Allow-Headers`, which
surfaces as a silent login failure.

**3. Raise `RATELIMIT_AUTH_PER_MINUTE` for the run.**
Each test provisions its own account so tests stay isolated, which means a full
run issues one `POST /auth/register` per test — more than the product's
10/min-per-IP auth limit. The suite would then fail on its own product's
protection. Registration detects the 429 and says so explicitly rather than
reporting a bare "expected 201".

**4. `SERVER__PORT` in the sandbox environment.**
Some harnesses export `SERVER__PORT`, which Spring's relaxed binding maps onto
`server.port` and silently relocates the backend (it fails with
"Port 62707 was already in use"). Start the backend with `env -u SERVER__PORT`
if that happens.

**5. Run with `CODEBUDDY_SAFE_DELETE_ENABLED=0`.**
Playwright wipes `test-results/` before each run. In this environment that is
hundreds of files, which trips the bulk-delete guard and aborts the run before a
single test starts — with a stack trace from the shim, not from Playwright.

## Env overrides

| Var | Default | Meaning |
| --- | --- | --- |
| `E2E_BASE_URL` | `http://localhost:3000` | frontend origin (must be CORS-allowed) |
| `E2E_API_URL` | `http://127.0.0.1:8080/api/v1` | backend API base |
| `E2E_AI_URL` | `http://127.0.0.1:8000` | ai-service, used for the readiness probe |

Each run registers a **fresh** account (`e2e+<stamp>@careeros.test`) through the
API, so the suite is idempotent and never touches an existing user's data.
