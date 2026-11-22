# Runbook

What to do when the night went wrong. This is the page the alerts point at: every
alarm in `ops/prometheus/alerts.yml` carries a `runbook:` annotation that links to a
section here, and every section starts with what the operator sees, not with what the
code does.

The surfaces this document is about:

| Surface | Where it comes from | What it answers |
|---------|--------------------|-----------------|
| `GET /actuator/prometheus` | backend, Micrometer | Is the night running, what is the AI spending, and is the install still verifying itself? |
| The ingestion runs board | `GET /api/v1/ingestion/runs` | What did each pull do, and why did it fail? |
| The monitoring page's nightly card | `GET /api/v1/monitoring/nightly-reports` | Did the install verify itself last night, and for how many nights has it not? |
| `ai_usage_events` | ai-service, one row per AI call | Who spent the money? |

## The alarms, in one table

| Alert | Severity | It means | First move |
|-------|----------|----------|------------|
| `CareerOSIngestionNightMissed` | critical | No ingestion run has completed in 26 hours | [A night that never succeeded](#a-night-that-never-succeeded) |
| `CareerOSIngestionFailing` | warning | More than half the runs in six hours failed | [A night where every feed failed](#a-night-where-every-feed-failed) |
| `CareerOSIngestionRepairStale` | warning | The stuck-ingestion repair clock has missed three of its ticks | [An upload that never stopped ingesting](#an-upload-that-never-stopped-ingesting) |
| `CareerOSNightlyVerificationStale` | critical | No nightly verification has finished in 36 hours | [The nightly verification stopped reporting](#the-nightly-verification-stopped-reporting) |
| `CareerOSNightlyVerificationFailing` | warning | Two or more of the newest nightly runs failed | [The nightly verification keeps failing](#the-nightly-verification-keeps-failing) |
| `CareerOSAiBudgetBurn` | warning | The trailing 24 hours cost more than 5 USD | [The AI budget is burning](#the-ai-budget-is-burning) |
| `CareerOSDigestDeliveryFailing` | warning | A weekly letter was refused by the relay | [A weekly letter the relay refused](#a-weekly-letter-the-relay-refused) |
| `CareerOSDigestSweepStale` | warning | No Monday digest compose finished in eight days | [The Monday letter was never written](#the-monday-letter-was-never-written) |
| `CareerOSSignalMailFailing` | warning | Three or more account letters were refused in six hours, morning and reminder alike | [The morning mail is refused](#the-morning-mail-is-refused) |
| `CareerOSSignalSweepStale` | warning | No morning mail sweep finished in 36 hours | [The morning sweep stopped](#the-morning-sweep-stopped) |
| `CareerOSReminderClockStale` | warning | The minute clock has not finished a tick in five minutes | [The minute clock a reminder rings on](#the-minute-clock-a-reminder-rings-on) |
| `CareerOSRetentionSweepStale` | warning | No credential-retention sweep finished in 36 hours | [The retention sweep stopped](#the-retention-sweep-stopped) |
| `CareerOSBucketListingRefused` | warning | The nightly sweep asked the object store for its whole listing in the last day and was refused | [The bucket was not swept](#the-bucket-was-not-swept) |
| `CareerOSPushDeliveryFailing` | warning | Three or more browser wakes were refused by a push service in a day | [The wake a push service refused](#the-wake-a-push-service-refused) |
| `CareerOSCircuitBreakerOpen` | warning | An ai-service circuit breaker has been open for ten minutes | [An ai-service circuit breaker sits open](#an-ai-service-circuit-breaker-sits-open) |
| `CareerOSGatewayRateLimited` | warning | The edge's token bucket has refused callers for five minutes straight | [The edge is refusing callers](#the-edge-is-refusing-callers) |

## A night that never succeeded

**What the alert looks like.** `time() - careeros_ingestion_last_success_timestamp`
stays above 93600 (26 hours). The gauge was last moved by a run that ended
`completed`; a night of failures leaves it exactly where it was, which is the point.

**The trap in the logs.** The backend writes `nightly ingestion swept N feed(s)` after
every sweep, and `N` is the number of feeds that were *due*, not the number that
succeeded. A night where all three feeds failed logs `swept 3 feed(s)` just like a
good one. Trust the runs board, not that line.

**What to do, in order.**

1. Confirm the sweep ran at all: `docker compose logs --since 26h backend | grep
   'nightly ingestion'`. No line means the clock never fired — check
   `careeros.ingestion.cron` (`03:20` by default) and that the backend that is up is
   the one you deployed.
2. Read the failures: `GET /api/v1/ingestion/runs` (the runs board does this for you).
   Each failed run carries the sentence that stopped it — a 503 from the feed, a
   timeout, or the planner's refusal. One dead feed is that feed's problem.
3. If every feed failed the same way, treat it as one outage: the fetcher's egress,
   DNS, or the ai-service behind `planIngest`. `GET /health` on the ai-service and the
   backend's `/api/v1/health` separate those two.
4. Once the cause is fixed, pull one feed by hand:
   `POST /api/v1/ingestion/feeds/{id}/run`. A `completed` run moves the success
   marker, and the alert clears on the next evaluation.

**A fresh process is not a broken one.** The success marker starts at the process's
boot time, so a deploy at 23:00 gives the first night until the following 03:20 and
the alert cannot fire before 26 hours after boot. If the marker is right at boot time
and the alert fires anyway, the process has been up for more than a day without a
single completed run — which is exactly what the alert is for.

## A night where every feed failed

**What the alert looks like.** More than half of the runs in a six-hour window ended
`failed`, with at least three runs in the window. The count floor keeps two dead feeds
in a quiet night from paging; the ratio keeps one failure in a busy night from paging.

**What to read.** The runs board's error column, sorted newest first. The same sentence
repeated across feeds points at shared infrastructure; one sentence on one feed points
at that feed's owner.

**Before touching anything**, check whether this is the world or the plan engine:
`GET /api/v1/health` says whether the stack is degraded, and the ai-service log has
one line per failed planning call. A feed that answers 200 with a body the planner
cannot read fails here without anything being down.

## An upload that never stopped ingesting

**What the alert looks like.** `CareerOSIngestionRepairStale` fires when
`time() - careeros_ingestion_repair_last_tick_timestamp > 1800` has held for ten minutes — three
ticks of the shipped ten-minute clock. Read it as what it is: this page says the **clock**
stopped, not that an upload is stuck. A single stuck upload has never paged, and still does not.

**Why the state exists at all.** An upload is two rows and one handover. The source and the
document commit together inside one transaction, reading `ingesting` and `pending`, and the call
that tells the engine to start runs *after* the commit, because a model call must not hold a
transaction open. That ordering is deliberate and it leaves a gap of milliseconds: a replica
drained or killed in it leaves a document nobody is working on. The second shape of the same
silence is the engine dying mid-task, where no exception ever arrives to mark anything failed.
Before Epic 418 nothing in the install looked at either row again, and the reader's page kept
drawing "ingesting" over a document that was no longer anyone's job.

**What the clock does about it.** Every `careeros.ingestion.repair.interval-ms` (600000, ten
minutes) the backend claims the documents past `careeros.ingestion.repair.window-minutes` (30)
that still read `pending` or `indexing` and offers each one back to the engine — safe, because the
pipeline re-reads the stored bytes and replaces the chunk set rather than adding to it. Each row
is claimed in the database before it is offered, so when several replicas wake at once exactly one
works on a document; that is why this clock needs neither a fleet lease nor the queue. Three
offers, then the row gets a verdict instead of a fourth spinner, and the sentence the reader's list
shows is `ingestion never landed after 3 offers`.

**Read it in this order.**

1. `docker compose logs --since 40m backend | grep -i repair`. A clock that is running but cannot
   read the table logs `the stuck-ingestion repair could not run` and does not move the gauge,
   which is the alarm's other half; a clock that logs nothing at all is not scheduled — check
   `careeros.ingestion.repair.interval-ms`, and that the backend started with scheduling on.
2. `docker compose exec -T postgres psql -U career_os -d career_os -c "select status, count(*),
   min(updated_at) from documents where status in ('pending','indexing') group by 1"`. What is
   actually waiting, and how long the oldest has waited. This is the repair's own predicate: rows
   past the window here are rows the next tick takes.
3. `curl -s localhost:8080/actuator/prometheus | grep careeros_ingestion_repairs_total`. The four
   outcomes say which side of the handover failed. `contended` is a sibling that got the row first
   and is the expected reading on a multi-replica install. `refused` is the engine saying no, which
   leaves the row for the next window rather than failing it — `refused` climbing while `requeued`
   does not is an ai-service problem, not a repair problem, and the health line's ai-service
   component says which. `exhausted` is the verdict, and it is the only outcome that writes a
   `failed` row.
4. The window itself, if a document that is legitimately still being embedded keeps getting
   offered. A 300-page PDF also reads `indexing`, and the window is the only thing that tells a
   slow ingest from a dead one: raising `careeros.ingestion.repair.window-minutes` is the answer,
   and it costs nothing but latency on the repair.

**What this does not mean.** A row the clock failed is not a lost upload. The bytes stay in the
bucket and the row keeps its key, so the recovery is the ordinary one: upload the file again, or
ask for the same internal handover the request thread asks for (`POST /internal/ingest/document/
{id}` with the internal token and the owner's `X-User-Id`). And the alarm is not an upload's own
page — on an install where the clock is healthy and one document is broken, the meter reads
zero movement and no rule fires, because that is a document, not an outage.

## The AI budget is burning

**What the alert looks like.** `careeros_ai_cost_usd_24h > 5` for fifteen minutes.
The number is the deployment-wide sum of `cost_usd` in `ai_usage_events` over the
trailing 24 hours — a rolling window, so it falls only when the calls that produced
it age out, not at midnight.

**Where the money is.** The users' own pages show their spend under
`GET /api/v1/ai-usage/summary`, but that is one caller's view and it is all-time. For
the deployment-wide split by model, ask the ledger:

```sql
select model, count(*) as calls,
       sum(input_tokens + output_tokens) as tokens,
       sum(cost_usd) as usd
  from ai_usage_events
 where created_at > now() - interval '24 hours'
 group by model
 order by usd desc;
```

An install where embeddings or re-ranking dominate is normal on a busy day; an
install where a chat model dominates usually means a retry loop or a client polling a
long-running call.

**Raising the budget** is a one-line edit in your copy of
`ops/prometheus/alerts.yml` (`5`, in the `CareerOSAiBudgetBurn` rule), followed by
`promtool check rules` and a Prometheus reload. Raise it after the split above says
the spend is the traffic, not a loop — the alert exists to make that a decision
rather than a surprise.

## The nightly verification stopped reporting

**What the alert looks like.** `CareerOSNightlyVerificationStale` fires when
`time() - careeros_nightly_last_finished_timestamp` stays above 129600 (36 hours).
The marker moves on every finished night — passed or failed — so this is not about
one bad verification: it is the report itself stopping. The monitoring card calls
the same window stale.

**What to do, in order.**

1. Open the workflow's own history: the scheduled run starts at 03:17 UTC and its
   last step posts the record. A run that is missing from the list means the
   schedule is the fault (a disabled workflow, an expired token, a fork without
   `CAREEROS_OPS_URL`).
2. A run that exists with a red final step means the POST failed: read that step's
   log for the internal surface's sentence — a rejected status, a reversed clock or
   an oversized summary, and the recorder prints the code it got.
3. If the workflow is green and the marker is still old, the scrape and the page are
   looking at different backends: check the scrape target against the deployment
   whose database the page reads.

**A fresh process is not a broken one.** The marker starts at the process's boot
time, so a deploy gets the same 36 hours a healthy install gets before this can
fire. A boot that cannot read the history keeps those defaults and logs why; the
nightly card is still the immediate answer to "has this install ever verified
itself". A deployment that has never recorded a night reads "missing" there at
once, and this alarm still waits the full window.

## The nightly verification keeps failing

**What the alert looks like.** `CareerOSNightlyVerificationFailing` fires when
`careeros_nightly_consecutive_failures >= 2` — the same line the nightly card
warns at. One failed night does not page; it is visible on its own row, and the
streak ends at the first passed night.

**What to read.** The monitoring page's nightly card, newest rows first: the eval
step's detail carries the newest eval report's aggregates and case count, every
other step carries the sentence its suite printed, and the row links to the
workflow run with the full log.

**What it means.** A single red suite is usually that suite's own dependency (a
migration, a flaky container); two nights in a row is a change that landed, or a
dependency that went away. Find the first red night's commit — the row records the
SHA the run tested — and diff from there. The nightly job tests the whole stack,
so a red night can be the ai-service, the backend, the frontend build or the eval
suite; the step names say which.

## The siege shows `http_req_failed 100%` — check a running stack first

**What it looks like.** `scripts/siege.js` (or `siege-e292.js`) runs, every iteration returns EOF, k6 reports `http_req_failed 100.00%` and `data_received 0 B`.

**What to read.** Docker Compose's health gate. The backend's `start_period` is generous (~120 s for a cold boot); if k6 starts before the health check passes it sees an EOF for every request. It is Compose, not the code. Confirm with `docker compose ps` (`careeros-backend | Up (healthy)`) and a single `curl http://127.0.0.1:8080/api/v1/health` — when that's 200, rerun the siege.

## The edge returned BACKEND_UNAVAILABLE during mid-operation maintenance

**What the alert looks like.** The gateway's `backend` circuit breaker is OPEN on the
`/actuator/circuitbreakers` readout; every route in the edge returns the static fallback body
`{"error":"BACKEND_UNAVAILABLE"}` while the backend itself routes fine via 8080.

**What it means.** The edge's Resilience4j breaker protects the user from a dying upstream —
pulling the cord so callers do not hang on a broken connection. The state machine is:

`CLOSED` → sliding-window of 10 calls, 50% failures → `OPEN` (waits 30 s, permits 3 probes) → `HALF_OPEN` → 3 successful probes → `CLOSED`.

The events feed (`/actuator/circuitbreakerevents/backend`) records every transition, so the
evidence-bearing sequence can be read: at `16:12:26Z` the probe failure rate crossed 50% — five
of ten calls against the backend failed because Docker Desktop crashed and the backend restarted
during the burst — the breaker opened at `16:12:27Z`; from the outside that looked like a total
loss of access across the edge. After the wait window closed at ~16:12:57Z, the first real traffic
re-entered as HALF_OPEN; three successes closed it at 16:13:47Z. Nothing in the backend or the gateway
required rebooting — only the operator's test harness required patience.

Note for next time: triggering the breaker yourself from a burst test creates exactly the
intervention you would correctly see as the alarm of a dying backend — except next time the alarm
will have been raised against a healthy upstream. Burst test through the gateway free-runs
(http_reqs at 10 VUs saw 96% 503s with sub-30 ms latency, which is the edge answering its own
fallback body before even attempting the backend); ATP for this edge is meters-scale.

## The Docker Desktop daemon dies and the host refuses every compose port

**What the alert looks like.** Compose says every container is `Up (healthy)` —
then `curl 127.0.0.1:8080/api/v1/health` refuses, `127.0.0.1:8000/health`
refuses, and the gateway refuses — while inside the containers Tomcat/Netty/
uvicorn are answering fine, because the probes run in-app, not through the host
forwarding. `docker compose ps` reports `health: starting` forever, and the
daemon crashes on the way down with `error reading from server: EOF` or
`dockerDesktopLinuxEngine: file has already been closed`.

**What it means.** The daemon (not the fleet) is the flaky part of the dev
machine. Measured on 2026-11-17: five daemon deaths in the long session —
three inside `docker compose build frontend`, every one within ~430 seconds of
the lint/type phase of a ~5.6-minute compile (so the image is never tagged,
but everything up to lint stays cached); two more surfaced as `socket hang up`
health-flaps mid-run elsewhere. The host port *forwarder* is the thing that
dies; the containers themselves are usually fine or fixable with one
`restart` per service.

**What to read and do, in order.**

1. Restart Docker Desktop (`Start-Process "C:\Program Files\Docker\Docker\
   Docker Desktop.exe"`), and wait until `docker info --format '{{.ServerVersion}}'`
   answers — not merely the UI saying it's alive. The daemon can answer early
   and still fail the next write; a build writes on every step, so a daemon
   that dies mid-step takes the step with it, while everything before that
   step stays cached for the next attempt.
2. `docker compose --profile app down` then up-d — re-pinning the forwarder.
   If `ports` still refuse, the daemon died again; step 1 is cheaper than
   step 2's false comfort.
3. `docker compose --profile app restart backend gateway` — after daemon
   death the Spring apps sometimes wake before their own VM is sound; a
   restart from a settled daemon boots clean ({Tomcat on 8080 at 09:17:38Z,
   gateway 8081 at 09:12:38Z, both healthy after waiting ~3 minutes}).
4. Any failing CI-like run: if every failing assertion is `Service at ...
   did not become ready within 60000ms (socket hang up)` (or an identical
   `ERR_CONNECTION_REFUSED`), it is the machine, not the product. Re-run only
   the failing specs once the stack answers 200. Do **not** lengthen the
   per-test timeouts or the health window to absorb the flap — the gates
   shrink only with measured cause recorded alongside them.
5. The frontend image trap: `docker compose build frontend` compiles in the
   container at exactly the moment the daemon keeps dying, so the tag never
   lands. Building the same production bundle locally (`next build` on the
   host) is the honest fallback — every bundle asset is identical except the
   `standalone` bit — and it is how the 77/77 golden-journey record was taken:
   against the local bundle, not the container.

**The honest limit.** The nightly CI and the local dev box disagree on
stability; this section is for the dev box. On CI the same fault shape reads
"nightly failed on X/jobs" with the X names doing the talking.

## The AI relay answers 502 from inside compose though the host reaches it fine

**What the alert looks like.** Every AI call inside the stack fails fast:
ingestion never becomes ready, the copilot answers 500/502, the trace shows
`httpx` connecting to the relay through a proxy nobody asked for, or every
internal call (ai→backend, ai→minio, ai→postgres) answering 502.

**What to read.** `docker compose exec ai-service python -c "import os; print(os.environ.get('NO_PROXY'))"`.
If it does not contain the fleet hosts (`backend,redis,postgres,minio,...`),
the shell's own `NO_PROXY` (the dev machine exports `127.0.0.1,localhost,::1`)
interpolated into `${NO_PROXY:-…}` and deleted the fleet bypass. The compose
file now pins the fleet bypass literally; an override wants both proxy knobs
and never the `NO_PROXY` one.

## The local gate sweep reds in `AsyncClient` construction, on a machine that is otherwise fine

**What the alert looks like.** `bash scripts/verify_gates.sh` answers one failure,
in whichever gate builds an HTTP client, with
`httpx.InvalidURL: Invalid port: ':1]'` from `_urlparse.normalize_port` -- not a
timeout, not a refusal, and the same gate passes when run by itself.

**What to read.** `python -c "import os; print(os.environ.get('NO_PROXY'))"`. On a
machine routing through a local proxy (Clash Verge and friends) that value ends in
`[::1],::1`, and `httpx` parses every entry as a URL: the bracketed form leaves `:1]`
where a port belongs, so constructing any client raises before a request is made. The
fleet's own bypass is a separate problem, documented above; this one is only about the
shell a developer runs gates from. Run the sweep with the variable cleared --
`env -u NO_PROXY -u no_proxy bash scripts/verify_gates.sh` -- the same way the
ai-service suites are run. Nothing in the repo works around it, because a proxy
variable that breaks the client is worth seeing rather than hiding.

## The nightly dies with 'too many clients already'

**What the alert looks like.** The IT step reds with
`FATAL: sorry, too many clients already` from Postgres, usually first at the
`entityManagerFactory`/`flywayInitializer` beans (`FleetWiringIT`,
2026-11-16). The nightly boots one application context per IT class against
the shared CI Postgres with its default `max_connections`; the harness used
to ask for the production pool size (20) per context, and the contexts sum
pasted the ceiling mid-suite.

**What to read.** The failing step's log, search `too many clients`. The
diff is never in the migration: the pool the ITs ask for is the lever.

**What it means, and the fix.** `AbstractIntegrationTest` caps every IT's
pool at 2 connections (production stays 20). That was the red on the night of
2026-11-16; the cap landed in the same tree. If the nightly goes ever red on
this line again, the cap was undone or a new IT class asks for more itself —
raise `max_connections` in the infra job and keep the cap; do not widen the
cap to dodge a load-shaped failure.

## Backups

**What a backup is.** One set, written by `scripts/backup.sh`, named after a UTC stamp:

| File | What it holds |
|------|---------------|
| `careeros-<stamp>.dump` | `pg_dump --format=custom` of the whole database, verified readable before the script exits |
| `careeros-<stamp>-files.tgz` | the MinIO data volume (`/data`), tarred from the running container |
| `careeros-<stamp>.sha256` | one checksum line per file above |

**Installing the night.** The script resolves the stack through `COMPOSE_FILE`, the
same variable the rest of the ops scripts read. A host line for cron:

```cron
# 04:10 every day, after the ingestion sweep and before the weekly letter
10 4 * * * cd /srv/career-os && COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml BACKUP_DIR=/srv/backups ./scripts/backup.sh >> /var/log/careeros-backup.log 2>&1
```

`BACKUP_KEEP` (default `7`) is how many sets stay; pruning removes a set whole —
dump, files and checksums together — so a half-deleted set can never claim to be one.

**The copy that is not on this disk.** `BACKUP_DIR` is on the same host as the
database it protects. Mirror it off the host (object storage, another machine) with
whatever the deployment already runs; a backup that only exists next to its original
is a backup of the disk, not of the data.

**Restoring on purpose.** `scripts/restore_drill.sh` is the rehearsal:

1. takes the newest set and verifies its checksums (a corrupted set stops here),
2. opens the files archive and counts its entries,
3. restores the dump into a throwaway database (`career_os_drill` by default) on the
   same server, with `--exit-on-error`,
4. compares the public table set and the applied Flyway migration count against the
   live database,
5. drops the drill database, unless `KEEP_DRILL=1`.

The files are verified readable but **not** unpacked over the live volume: doing that
is a restore, not a drill (see [Restoring by hand](#restoring-by-hand)).

**What a good drill looks like:**

```
drill: ok
  dump       careeros-20261028T041000Z.dump
  tables     <same set as career_os>
  migrations <same count as career_os>
  files      <N> entries (archive opens; not restored into a bucket)
```

The two `same` lines are the comparison itself: the drill prints the live set's count
and the migration count only after the equality check has passed.

**What a bad drill looks like.** Any `drill:` line on stderr and exit 1. A table-set
mismatch prints the diff and keeps the drill database; a checksum mismatch means the
backup is corrupt and the previous set deserves a look. Run the drill weekly, and
after any upgrade that changes the schema.

## Restoring by hand

Two restores, two commands, both destructive. Stop the writers first. Every line
names the override with `COMPOSE_FILE` and hands compose `.env.prod` with
`--env-file`: a bare `docker compose` drives the development project, and the
override cannot render its required values without the file, so a command missing
either one restores into the wrong stack or stops before running.

**Database.** With the backend and ai-service stopped:

```bash
COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml docker compose --env-file .env.prod stop backend ai-service
COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml docker compose --env-file .env.prod exec -T postgres sh -c \
  'pg_restore --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges' \
  < backups/careeros-<stamp>.dump
COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml docker compose --env-file .env.prod start backend ai-service
```

`--clean --if-exists` drops the objects the dump is about to recreate, so the result
is the backup's schema rather than a merge with whatever is left. Flyway runs on the
restarted backend and finds the schema already at the dump's version.

**Files.** With MinIO stopped, write the archive back onto the data volume:

```bash
COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml docker compose --env-file .env.prod stop minio
docker run --rm --volumes-from "$(COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml docker compose --env-file .env.prod ps -q minio)" \
  -v "$(pwd)/backups:/backups:ro" alpine \
  sh -c 'rm -rf /data/* && tar -C /data -xzf /backups/careeros-<stamp>-files.tgz'
COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml docker compose --env-file .env.prod start minio
```

The database and the files must come from the **same** set: a row that points at a
resume object holds a key, and the object lives in the archive with the same stamp.

## Where these alarms live

The rules ship in `ops/prometheus/alerts.yml`; they are not installed by the compose
file, because a deployment may already run Prometheus. Point it at the backend and
load the rules:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: career-os-backend
    metrics_path: /actuator/prometheus
    static_configs:
      - targets: ["backend:8080"]

rule_files:
  - /etc/prometheus/careeros-alerts.yml
```

Check the file before a reload (`promtool check rules ops/prometheus/alerts.yml`) and
reload Prometheus rather than restarting it. `/actuator/prometheus` is public by
default and must be restricted at the reverse proxy to the scraper's address — the
deployment checklist in `docs/DEPLOYMENT.md` already says so.

The metric families the rules read are written by
`backend/src/main/java/com/careeros/job/service/IngestionMetrics.java` (the counter
and the success marker), `backend/src/main/java/com/careeros/ai/service/AiUsageMetrics.java`
(the rolling 24-hour spend, tokens and calls, refreshed every
`careeros.ai.metrics-refresh-ms`, one minute by default),
`backend/src/main/java/com/careeros/report/service/NightlyVerdictMetrics.java`
(the newest nightly finish and the failure streak, moved by each recorded night and
once at boot), `backend/src/main/java/com/careeros/report/service/WeeklyDigestDeliveryMetrics.java`
(the letter counter, the delivered marker and the Monday heartbeat),
`backend/src/main/java/com/careeros/notification/service/NotificationDeliveryMetrics.java`
(the signal-letter counter and the morning heartbeat), and
`backend/src/main/java/com/careeros/auth/retention/RetentionMetrics.java`
(the per-table deletion counter and the nightly sweep heartbeat), and
`backend/src/main/java/com/careeros/knowledge/service/IngestionRepairMetrics.java`
(the repair clock's four outcomes and its own tick marker). A metric missing
from the scrape means the bean did not start: the backend log has the reason.

## A reader quotes one request

**What arrives.** "The export failed at 14:03" covers a minute of requests. Ask for
the `X-Request-Id` header on the failed answer — every answer carries one, including
the `401`s and `429`s that never reached a controller, and the browser exposes it to
the shell so the reader can copy it from the network panel. A proxy that mints its
own id keeps it when the value is 8–64 characters of letters, digits, dot, dash or
underscore; anything else is replaced by a fresh UUID, so a quoted value always
fits on one log line.

**What to read.** The console pattern prints the id in square brackets after the
level and thread:

```
14:03:07.412 WARN  [http-nio-8080-exec-4] [edge-7c1d4f9a] c.c.report.ExportService - ...
```

Grep the backend log for `[edge-7c1d4f9a]` and every line the request wrote is on
screen, in order. A line with an empty bracket — `[]` — was written outside any
request: boot lines and scheduled sweeps have none and cannot be tied to a report.
The id is diagnostics, not a credential: it is not stored, it changes on every
call, and quoting it exposes nothing.

Every answer also leaves one `careeros.access` line under that id:

```
14:03:08.913 INFO  [http-nio-8080-exec-4] [edge-7c1d4f9a] c.c.common.RequestIdFilter - GET /api/v1/jobs 200 37ms
```

so "what was the backend doing at 14:03" is `grep 'careeros.access'` followed by
the status and time columns — no id needed. A request whose chain threw says
`error` instead of a number, because the container's 500 is decided after this
line is written. The query string is never printed: a search term is the reader's
text and a reset flow carries a token.

**What crosses the service boundary.** Every backend call to the ai-service — the
typed `/internal/*` routes and the SSE stream — carries the same id in
`X-Request-Id`; the ai-service echoes it on its answer and writes it as
`request_id` in its JSON log lines. A turn that failed upstream is then one grep in
two files: the backend line that says the call failed and the ai-service line with
the same value that says why. The stream relay reads on a worker thread, so the id
is copied across threads explicitly. A scheduled sweep has no id and sends none:
the ai-service mints one for its own lines, and that value appears nowhere in the
backend log.

## What this runbook does not cover

- **Redis.** It backs the rate limiter and the health ping; its outage is a degraded
  `/api/v1/health`, not an alert (see `docs/SECURITY.md`).
- **The reverse proxy, DNS and TLS.** The deployment guide owns those.
- **The AI provider's own outage.** It shows up as failed planning calls and, from
  there, as the ingestion alarms above; the provider's status page is the source.

## A weekly letter the relay refused

**What the alert looks like.** `CareerOSDigestDeliveryFailing` fires when
`increase(careeros_digest_delivery_total{outcome="refused"}[6h]) > 0`: the mail relay
answered at least one weekly letter with an error. One refusal is enough — a letter is
one account's Monday, and the Monday sweep does not try it again within the same night.
The metric is written by
`backend/src/main/java/com/careeros/report/service/WeeklyDigestDeliveryMetrics.java`;
its `outcome="sent"` series is what the same relay accepted, so the refusal rate is one
division.

**What to read.** The backend log names the week and the account ("the weekly letter
for the week of ... could not be sent"). The letter's own row in `weekly_digests` holds
the relay's sentence in `delivery_error` (capped at 500 characters) and the count in
`delivery_attempts`; `delivered_at` is null for a letter that never left. Zero attempts
is the dashboard's compose route, which never sends — it is not a stuck letter.

**What to do, in order.**

1. Fix the relay. Check `APP_EMAIL_PROVIDER` is `smtp`, `APP_EMAIL_SMTP_HOST` and the
   from address, then the port and its transport: 587 with STARTTLS or 465 with SSL
   from the first byte, never both. A provider that rejects the credentials answers
   with its own code, which is the sentence on the row.
2. Let the retry clock run. At 09:05 UTC every morning it asks for the undelivered
   letters that were attempted, oldest week first, and hands them to the transport
   again; each attempt increments `delivery_attempts`. A letter is tried at most five
   times, then it stays on its row with its last error and is not mailed.
3. If the alert is still inside its six-hour window after a success, nothing else is
   wrong: the rule counts refusals in the window, and the next accepted letter — on the
   sweep or on a retry — moves the window past them.

**What a retry cannot recover.** A letter already at the attempt cap, and a week whose
row was deleted, are not re-sent by anything: the Monday sweep writes each week once,
and the dashboard's compose route files a letter without mailing it. After a relay
outage that outlasts the cap, the affected week is readable on the analysis page but
will not arrive by mail.

## The morning mail is refused

**What the alert looks like.** `CareerOSSignalMailFailing` fires when
`sum(increase(careeros_signals_delivery_total{outcome="refused"}[6h])) >= 3`: at least
three account letters were refused by the mail relay inside six hours. Since 41.1 the
counter is of letters, not of one letter kind: the 07:30 UTC morning sweep and the minute
clock's reminder letter write the same series, so three refusals can be three reminders
inside one hour, or both kinds mixed. Several accounts in one window still means the relay
or its configuration rather than one mailbox; a single address that refuses both its
morning letter and its reminder letters reaches the floor sooner than it used to. The metric
is written by
`backend/src/main/java/com/careeros/notification/service/NotificationDeliveryMetrics.java`;
its `outcome="sent"` series is what the relay accepted. The same class exports
`careeros_signals_last_delivered_timestamp` (the last acceptance, started at boot); it
is not alarmed on, because an install whose inboxes are quiet writes no letter and
that is not a fault.

**What to read.** The backend log carries one line per refusal, e.g. "the signal mail
to <account> was refused" or "the reminder letter to <account> was refused", with the
transport's exception on it — the provider's own code is the diagnosis, and the line's
wording says which letter was refused. Cases that never reached the transport ("no account
to mail", "no address") are warn lines too, but they are not counted as refusals: the relay was
never asked, so the metric and the alert stay quiet. A refusal writes nothing to
`notification_states`: `notified_at` is still null for every episode in that letter, so
the next pass asks again — the next morning's sweep for a morning letter, and the next
morning for a refused reminder's episode (the minute clock does not retry its own letter). The in-app inbox is unaffected — the items are
still there, unread.

**What to do, in order.**

1. Tell one bad address from a relay fault. If every refusal in the window names the
   same account, it is that mailbox (a bounce, a typo, a full inbox): correct the
   address and let the next sweep deliver it. If refusals name different accounts, the
   relay is refusing the deployment — check `APP_EMAIL_PROVIDER` is `smtp`,
   `APP_EMAIL_SMTP_HOST`, `APP_EMAIL_FROM`, the relay credentials, and the port with
   its transport (587 with STARTTLS or 465 with SSL from the first byte, never both),
   exactly as in the weekly-letter section above.
2. Wait for the next morning. There is no retry clock for signals: the 07:30 UTC sweep
   itself retries every unread, unmailed episode, so a fixed relay is exercised the
   following day without an operator action. Nothing needs to be re-run.
3. Do not touch `notified_at`. A refusal left it null on purpose; writing a timestamp
   there would silence the episode without ever handing it to the reader, and the
   sweep would never look at it again.

**Why one refusal does not page.** The morning letter re-asks every morning while the
episode is visible, so a single undeliverable address would refuse once a day forever;
a fleet with one dead mailbox must not page daily. The three-refusal floor keeps that
case a warn line while a relay outage — which refuses every account in one pass — pages
on the first morning. A reminder letter adds at most one refusal per account per tick,
but a day with three different reminders coming due can carry one dead address over the
floor; that is the moment the alert is for as well, because the reader has then missed
three moments the clock promised, and the log's wording still names the one address.
An install with fewer than three mail-bearing accounts is below
the floor by construction: its relay outage is read from the warn lines instead.

## The morning sweep stopped

**What the alert looks like.** `CareerOSSignalSweepStale` fires when
`time() - careeros_signals_last_sweep_timestamp > 129600`: no completed morning mail
sweep in 36 hours. The gauge is the sweep's heartbeat — moved at the end of every
completed pass, with or without letters, by
`backend/src/main/java/com/careeros/notification/service/NotificationDeliveryMetrics.java`.
It cannot be inferred from the delivered marker: an install whose inboxes are quiet
sends no letter for weeks, and that is healthy. 36 hours is twice the daily cadence,
which tolerates one late or skipped morning without paging and still catches a clock
that has actually stopped; it is the same 129600 seconds the nightly stale rule uses.
A fresh process starts the heartbeat at boot, so a deploy is not read as stale before
it has had a morning.

**What to read.** First, the scrape: `careeros_signals_last_sweep_timestamp` in
`/actuator/prometheus` tells you when the last pass finished — a missing series means the
metrics bean never started, and the backend log has the reason. Then the backend log:
every scheduled firing that reached the service logs "signal mail delivered to N
account(s)" when N > 0 and is otherwise silent, so an ordinary quiet morning looks like
nothing at all; a firing that threw before the audience was readable logs "the signal
mail sweep could not run" with the stack trace. Check that the scheduler is firing at
all: `careeros.signals.cron` (default `0 30 7 * * *`) in the deployment's environment,
and whether the scheduler thread started (`@EnableScheduling` is part of the app; a
profile that excludes it would never fire).

**What to do, in order.**

1. If the log shows failed firings, fix what the stack trace names. A database outage
   during the audience query is the common one; the next scheduled firing recovers on
   its own once the database answers.
2. If the log shows no firings at all, the clock is wrong or missing. Correct
   `careeros.signals.cron`, restart the backend so the schedule is re-read, and confirm
   the next morning's line. A backend that has been down counts: its boot time is the
   only reading until a pass completes.
3. Do not "fix" the gauge by hand or by an internal call; nothing writes it except a
   completed sweep. The inbox is unaffected either way — every signal is still in the
   app, and `notified_at` is untouched, so the next completed pass mails the waiting
   episodes once.

**What this alert does not mean.** It is not a relay fault (`CareerOSSignalMailFailing`
owns that), not a slow sweep (the pass is bounded by the transport's five-second cap per
account), and not an empty inbox (a pass with no letters still heartbeats). It means the
promise "every morning the inbox can leave" stopped being kept.

## The minute clock a reminder rings on

**What the alert looks like.** `CareerOSReminderClockStale` fires when
`time() - careeros_reminders_last_tick_timestamp > 300` for five minutes — five missed ticks
of the default `careeros.reminders.tick-ms` of `60000`. The gauge is the epoch second of the
last completed tick, and it moves only when a tick finished; a board with nothing due and a
dead clock therefore read differently. From a stale gauge onward a reminder that comes due
waits for the next morning's pass instead of ringing and mailing when the reader asked. What
lags is the moment, not the reminder: the inbox showed it, the morning letter still carries it
when the signals dial is on, and the calendar carries its own alarm.

**A fresh process is not a broken one.** The gauge starts at the process's boot time, so a
deploy gets its first five minutes before this can fire — the same shape every heartbeat in
this file has. A backend that is up but whose schedule never started moves nothing, and that
is exactly what the rule is for; a backend that is down is not scraped at all, and its
silence is the other alarms' business.

**What to read.** The backend log prints "reminder ring delivered to N account(s)" and
"reminder letter written for N account(s)" when a tick woke or mailed at least one; an ordinary
minute is silent. A tick whose audience query failed logs "the reminder clock could not read
its audience for the ring" or "... for the letter" with the stack trace, and the window is not
advanced — the next tick asks for the same span again. Then check
`careeros.reminders.tick-ms` and that `@EnableScheduling` is active.

**What to do, in order.**

1. If the log shows failed ticks, fix what the stack trace names. A database outage during the
   audience query is the common one; the next tick recovers on its own once the database answers.
2. If the gauge is stale and no tick has logged, the clock is wrong or missing. Correct
   `careeros.reminders.tick-ms`, restart the backend so the schedule is re-read, and confirm the
   gauge moves within two minutes.
3. Do not backfill by hand. A reminder whose moment fell while the process was down is not
   replayed by this clock — the next morning's pass rings what is still unread and unpushed, the
   morning letter carries the episode when the signals dial is on, and the inbox and calendar
   feed showed it all along.

**What this clock does not own.** It rings only browsers that registered for push, and it mails
only accounts whose `reminders` dial is on. An episode the morning already carried is not rung
or mailed again, and a browser that refused is not latched, so the next morning's pass asks it
again. A letter the relay refused is not latched either, so the episode remains for the morning
sweep. The calendar feed rings on its own through each event's alarm and does not depend on this
clock.

## The Monday letter was never written

**What the alert looks like.** `CareerOSDigestSweepStale` fires when
`time() - careeros_digest_last_sweep_timestamp > 691200`: no completed Monday compose in
eight days. The gauge is the weekly clock's heartbeat, moved by
`WeeklyDigestScheduler.publish()` after the compose pass returns — with or without
letters — and written by
`backend/src/main/java/com/careeros/report/service/WeeklyDigestDeliveryMetrics.java`.
Eight days is the seven between Mondays plus one day of grace, so a Monday that ran a
little late does not page, and a Monday that never ran pages the next day. The delivered
marker cannot stand in for it: a week with no applications writes no letter, and that is
healthy. The 09:05 retry clock is a different promise and does not move this gauge. A
fresh process starts the heartbeat at boot.

**What to read.** The backend log always prints a compose line when the clock fires:
"weekly digest composed N letter(s) for the week of YYYY-MM-DD", N may be zero. If the
line is missing for the last Monday, the clock did not fire. Then check
`careeros.digest.cron` (default `0 0 8 * * MON`) in the deployment's environment, whether
the backend was running at that hour, and whether scheduling is enabled at all. If the
line is there but the alert is up, the pass wrote a heartbeat and the gauge you are
reading is older than the log — re-read the scrape. The rows in `weekly_digests` are the
evidence of what was written for each week.

**What to do, in order.**

1. Fix what stopped the clock: correct `careeros.digest.cron` and restart the backend so
   the schedule is re-read, or bring the backend up for the hour. The next Monday
   composes the week that just ended; the log line is the confirmation.
2. Accept that the missed week is lost. No route composes an arbitrary past week: the
   Monday clock always composes the week that just ended, and `POST /digests/run` files
   the current week for the signed-in account without mailing it. The missed week's
   numbers are still on the analysis page; its letter will not arrive. Do not try to
   compose it by editing rows or calling internal endpoints.
3. Leave the gauge alone. Nothing writes it except a completed compose; moving it by
   hand would only hide the next missed Monday.

**Why it is not the relay alert.** `CareerOSDigestDeliveryFailing` fires when a letter
was composed and the transport refused it. This alert fires when no compose finished at
all. Fix the clock here; fix the relay there. A week that fails both is two separate
promises, and both sections apply.

## The retention sweep stopped

**What the alert looks like.** `CareerOSRetentionSweepStale` fires when
`time() - careeros_retention_last_sweep_timestamp > 129600`: no completed retention sweep in
36 hours -- one pass does both halves, the credential deletes and the purge of retired
evidence, so this is the clock for both. The gauge is the sweep's heartbeat, moved at
the end of every completed pass by
`backend/src/main/java/com/careeros/auth/retention/RetentionMetrics.java`, and it is
the only reading that can answer "did the clock run". The deletion counter cannot: a
sweep that stopped leaves `careeros_retention_deleted_rows_total` at its last value,
which a scrape cannot tell from a night that had nothing to delete. 36 hours is twice
the daily cadence, so one late or skipped run does not page and two do. A fresh
process starts the heartbeat at boot, so a deploy is not read as stale before its
first 04:47.

**What to read.** First the scrape: `careeros_retention_last_sweep_timestamp` in
`/actuator/prometheus` says when the last pass finished. Then the backend log: every
completed pass logs "Retention sweep removed N row(s) at <clock> (<per-table map>)"; a
table whose delete threw logs "Retention sweep failed for <table>" with the stack trace
and is left out of the summary, and a purge that skipped rows it would rather not delete
logs "Retention sweep left N retired document row(s)". Check `careeros.retention.cron`
(default `0 47 4 * * *`) in the deployment's environment, whether the backend was running
at that hour, and whether scheduling is enabled at all. The per-table counters
(`refresh_tokens`, `password_reset_tokens`, `email_change_tokens`, `documents`,
`document_chunks`) separate a quiet night (series present, value flat) from a table that
has never been swept (no series), because the series is registered on the first
successful sweep of that table. The evidence pair moves together or not at all: rows and
chunks go in one statement, so a `documents` reading with no `document_chunks` beside it
is a dashboard missing a series, not a night that deleted only rows.

**What to do, in order.**

1. If the log shows no firings at all, the clock is wrong or missing. Correct
   `careeros.retention.cron`, restart the backend so the schedule is re-read, and
   confirm the next night's "Retention sweep removed" line. A backend that has been
   down counts: its boot time is the only reading until a pass completes.
2. If the log shows a pass that failed one or more tables, fix what the stack trace
   names -- usually a lock timeout or a database outage. The other tables were pruned
   in their own transactions and the next night retries the failed one on its own; the
   heartbeat moved because the scheduler ran, so this alert staying quiet is correct.
3. Leave the gauge alone. Nothing writes it except a completed sweep, and a missed
   night cannot be replayed through any route: the next completed pass sweeps with its
   own clock, which is later and deletes strictly more.

**What this alert does not mean.** It is not a table-failure alarm (the heartbeat moves
on a failed pass; read the WARN line and the missing series), and it is not data loss:
only rows past a window are ever deleted -- refresh, password-reset and address-change
rows more than `RETENTION_EXPIRED_TOKEN_DAYS` (thirty days) past expiry, and documents
more than `RETENTION_RETIRED_DOCUMENT_DAYS` (180 days) past the delete that retired them,
together with the chunks indexed from them. Nothing a reader can see is in either set:
retirement is what takes a document out of evidence, and the purge only closes the window
on a record nobody quotes. The tables behind visible history -- AI usage events,
notification read state, ingestion runs, weekly letters -- are deliberately not swept.
It is also not a storage-growing alarm, which is the direction the old version of this
paragraph pointed: files are removed now, both by a delete that retires the last row
naming an object and by the purge of a row that aged out, so a bucket that keeps growing
is a reclaim failing rather than a sweep not running -- read
`careeros_storage_objects_reclaimed_total{outcome="failed"}` and the WARN line naming the
key. If the delete itself is slow after a restart, confirm the V23 and V31 migrations
applied: they add the `expires_at` indexes the credential deletes ride and the partial
index on the retired slice of `documents` that the purge reads.

## The bucket was not swept

**What the alert looks like.** `CareerOSBucketListingRefused` fires when
`increase(careeros_storage_bucket_reads_total{outcome="refused"}[24h]) > 0`: the nightly
retention sweep asked the object store for the whole listing of the bucket and the store
refused, so the pass that reclaims what no row names (roadmap 48.2) judged nothing. The
sweep's own clock almost certainly moved — a pass that could not read the bucket still
finishes its tables and its purge — so `CareerOSRetentionSweepStale` stays quiet while this
fires, and that pair of readings is the point: one says the night ran, the other says the
bucket half of it did not.

**Why it is a counter and not a timestamp.** `careeros_storage_objects_judged_total` moves
once per object the listing showed, and on a refused listing there is no listing — no size,
no objects, nothing to divide. So this family answers one question per pass: did the store
answer (`listed`) or refuse (`refused`). A night that never asked at all moves neither,
which is the reading `CareerOSRetentionSweepStale` already covers.

**What to read.** The backend log for "Retention sweep could not list the bucket, so it
reclaimed nothing" with its stack trace, and the sweep's own summary line: a failed bucket
phase adds `bucket_objects` to its list of what did not finish, beside the table names.
Then the two families together on the scrape —
`careeros_storage_bucket_reads_total{outcome="listed"}` should step once a day, and
`careeros_storage_objects_judged_total` should add up to the listing across its four
outcomes (`named`, `young`, `deleted`, `failed`). A `refused` reading with four flat
judgement series is the same night described twice, which is the check.

**What to do, in order.**

1. Check whether the object store was reachable at 04:47 UTC: `docker compose ps minio`,
   the MinIO container's log, and the backend's `MINIO_*` credentials. The refusal is a
   store problem, not a scheduler problem — the pass ran.
2. Nothing needs replaying. The next night's pass lists the bucket from the start, so a
   refused night costs one night of reclaim and no data: an object that was not judged is
   an object that was not deleted.
3. If refusals keep arriving while the store looks healthy, read the same log for the
   delete-side WARN line naming a key. That is `outcome="failed"` on the judgement family
   and a different problem: the store answers the listing but will not give a specific
   object back, usually a permission or an already-deleted key. It does not page here.

**What this alert does not mean.** It is not data loss, and it is not a warning that the
bucket is full. Nothing on this path deletes when the listing failed, and the objects it
would have reclaimed stay exactly where they are. The delete path's own reclaims
(`careeros_storage_objects_reclaimed_total`) are counted separately and alarm nowhere: an
object that outlives a row is a storage cost, and a counter with no baseline would page on
a quiet week.

## The fleet queue is enabled and its jobs are not running

**What the alert looks like.** There is no page on this path, which is why this section starts
from a reading rather than an alarm: `careeros_queue_jobs_total{outcome="dead"}` moving, or
`{outcome="failed"}` climbing while `{outcome="done"}` does not, or a pending list that only
grows. The queue is opt-in — `CAREEROS_QUEUE_ENABLED=false` is the shipped default — so in a
default deployment every one of these series reads zero and this section is about a stack where
someone turned the switch on.

**The five jobs that ride it.** `retention.sweep` (the nightly credential and evidence bucket),
`ingestion.sweep` (the subscribed boards), `digest.compose` and `digest.retry` (the Monday
letter), and `rag.cache.invalidate` (the epoch bump a delete hands over after it commits).
The stream is `careeros:v1:jobs`, the consumer group is `backend`, and a job that stopped being
retried is in `careeros:v1:jobs:dlq`. Each replica names itself `pid@host` in the group, which
is what makes "whose job is this" answerable after a crash.

**Read it in this order.** The commands below are the development stack's shape. On
production, every `docker compose` call also takes `-f docker-compose.yml
-f docker-compose.prod.yml --env-file .env.prod` (DEPLOYMENT's form), and every `redis-cli`
call also takes `-a "$REDIS_PASSWORD"`, because production Redis starts with `--requirepass`.

1. `docker compose exec -T redis redis-cli XLEN careeros:v1:jobs` and
   `docker compose exec -T redis redis-cli XPENDING careeros:v1:jobs backend`. Pending rows
   with no idle time are a queue that is busy; pending rows idle past
   `careeros.queue.claim-idle-ms` (30 s by default) are work a replica died holding, and a
   sibling claims them on its next tick.
2. `docker compose exec -T redis redis-cli XINFO GROUPS careeros:v1:jobs`. A group that is
   missing entirely means no replica ever ran a tick: check `careeros.queue.enabled` on the app,
   and that the app can reach Redis at all — a tick that cannot reach it logs
   `queue tick failed` and returns, leaving the entries in place. The next tick is the retry.
3. `docker compose exec -T redis redis-cli XRANGE careeros:v1:jobs:dlq - + COUNT 20`. Each
   dead entry carries the original job's fields plus `from` (the stream id it came from) and
   `reason`, which is either `no-handler` — an entry whose kind nothing in this process claims,
   usually a rolling deploy that wrote a kind the new replicas renamed away — or
   `max-deliveries`: a job that failed `careeros.queue.max-deliveries` times, 5 by default. The
   second is a real defect behind the job; the first is a wiring gap.
4. `docker compose logs --since 1h backend | grep -i queue` for the handler's own failure line.
   A handler that throws leaves its entry pending on purpose, so the same job names itself
   repeatedly until it succeeds or is retired.

**What a `dropped` reading means, and why the platform kept working.** `enqueue` answers false
when the queue is off or when Redis refused the write, and every producer then does the work on
its own thread exactly as it did before the queue existed: the retention leader sweeps inline,
and a delete bumps the cache inline. So `dropped` counts are a Redis outage seen from the one
place that notices, not a lost job. What is genuinely lost is fleet deduplication — if every
replica dropped, all of them ran the pass, which is the pre-queue behaviour and its cost.

**What this section does not cover.** A `dead` entry is not data loss: each of these five jobs
is idempotent by construction, so replaying it by hand is safe. To replay, copy the DLQ entry's
fields back onto the stream with `XADD careeros:v1:jobs '*' kind <kind> ...`, or simply wait for
the next scheduled tick, which enqueues the same work again.

## The wake a push service refused

**What the alert looks like.** `CareerOSPushDeliveryFailing` fires when
`sum(increase(careeros_push_delivery_total{outcome="refused"}[24h])) >= 3`: three browser wakes in a
day that the push service answered with something other than an acceptance. The family counts one
reading per registration a ring pass asked to wake, tagged `sent`, `gone`, `refused` or
`not_configured`, and only `refused` is in the expression.

**Why three, and why only that tag.** One refusal is normal churn: a browser that abandoned its
registration can refuse once on its way out. Three in a day is not churn, because the two passes
that ring -- the morning sweep and the minute clock -- walk every registration of every account with
something waiting, and a registration that keeps refusing keeps counting. `gone` is the service
saying 404 or 410, which the ring deletes from the database on the spot, so it is a cleanup rather
than a fault and an alarm on it would page on every reader who closes a laptop for good.
`not_configured` is an install that ships no VAPID keys at all: the boot line says `push=off`, and a
deployment choice is not a transport that broke.

**What to read.** The backend log for the sentence that names the host, since a refusal is written by
whichever half failed: "push service ... refused a wake with status ..." (the service answered
outside 2xx), "push service ... could not be reached" (egress, DNS or the service being down),
"push subscription ... has no usable endpoint" or "... has no https origin to address" (a stored
address this service cannot dial), and "push service ... answered a wake that could not be read".
Then the whole family on the scrape: `careeros_push_delivery_total` split by `outcome` says whether
the day was all refusals -- keys or egress, so every browser failed together -- or one registration
refusing in an otherwise accepting day, which is one broken browser.

**What to do, in order.**

1. Check the boot line's `push=` reading first. `keypair` means the install thinks it has VAPID
   keys, so a day of refusals is about those keys or the address in the JWT's `sub`; `off` means no
   rule here should be firing at all, because every wake lands on `not_configured`.
2. Read the refused host from the log and ask whether the install can reach it at all. Push services
   are third-party endpoints, so a firewall, a proxy change or a provider outage produces the same
   counter as a bad key, and the log line separates them: a status code is an answer, "could not be
   reached" is not.
3. Nothing needs replaying, and nothing is lost. A wake that was refused leaves the notification
   unread, which means it is still in the next pass's audience -- the morning sweep and the minute
   clock will ask that browser again. The in-app inbox, the morning letter and the calendar all
   carried the item whether or not the browser rang.
4. If one account is the only one refusing, have the reader turn the browser's permission off and on
   again from the settings page. The registration is an upsert on its endpoint, so a renewed
   subscription replaces the address that cannot be dialed rather than adding a second one.

**What this alert does not mean.** It is not a stopped clock; `CareerOSReminderClockStale` and
`CareerOSSignalSweepStale` say whether the passes ran, and this rule can fire on a night where both
did. It is not a lost reminder, and it is not the account's second factor or the mail relay -- the
push transport is a different outbound path with its own host in the log.

## An account is locked out of its second factor

**What the reader sees.** The password is right and the code field still refuses every
six-digit number (401 `MFA_INVALID`), or a fresh code changes nothing. `POST /auth/login`
with an enrolled account answers 401 `MFA_REQUIRED` until a code is sent, then judges it;
a wrong password is a different answer (`INVALID_CREDENTIALS`), so "the code is refused"
always means the password matched.

**What to read, in order.**

1. **The phone's clock.** TOTP is time-based: 30-second steps, one step of drift either
   side. Ask the reader to switch the phone to automatic time and try two codes from
   consecutive windows. This is the most common cause by far.
2. **The code's kind.** The field accepts six digits or one printed recovery code (case,
   hyphens and spaces forgiven). A printed code is single-use: the settings card shows how
   many remain (`recoveryCodesRemaining`), and a spent one is refused exactly like a wrong
   one.
3. **The bucket.** The MFA routes are metered at five verdicts a minute per signed-in
   account, and login is metered per client IP. A reader who tried five codes in a row is
   told 429 `RATE_LIMITED`, not another verdict -- wait out the minute before concluding
   anything.
4. **The seed.** The backend log line `the sealed TOTP seed cannot be opened with this
   app.security.mfa-secret` means the row was sealed under a different `APP_MFA_SECRET`
   (or is damaged). No code -- not even a printed one -- can pass, because the login opens
   the seed before it tries the printed set. This is the one case where nothing the reader
   holds can help.

**What to do, in order.**

1. Clock or wrong-reader trouble needs nothing on the server. The printed sheet is the way
   in when the phone is gone: sign in with one printed code, then reprint or turn the
   factor off from settings, which needs one more printed code.
2. No phone and no printed sheet: establish identity through the ordinary password-reset
   path (the mailbox link proves the mailbox), then have an operator delete the two rows
   for that account once the request is confirmed out-of-band:

   ```sql
   DELETE FROM user_mfa_recovery_codes WHERE user_id = '<user id>';
   DELETE FROM user_mfa WHERE user_id = '<user id>';
   ```

   The next login asks for the password alone. Record who asked and who deleted; the
   factor is gone until the reader enrolls again, and nothing else on the account changes.
3. A rotated `APP_MFA_SECRET`: either put the old value back (every seed opens again) or
   accept that every enrolled account is in case 2 at once and delete the rows for the
   accounts that ask. There is no bulk re-seal, and no route can prove ownership of a
   seed this deployment cannot open.

**What this does not mean.** It is not a password problem: `INVALID_CREDENTIALS` is the
wrong-password answer, and a wrong code never says whether the password was right. It is
not account loss: the deletion removes the second factor, not the account, its documents
or its open sessions -- those still expire or close on their own. And it is not a reason
to lower the factor for everyone: the door exists so a leaked password alone cannot open
the account.

## A reply never arrives

**What the operator sets up first.** Inbound mail is not a mailbox the app polls: the
provider forwards each delivery to the webhook, and the recipient's local part has to
reach the path, because the token *is* the credential. Set `APP_INBOUND_DOMAIN` to a host
whose mail the provider accepts (the bare hostname, e.g. `inbox.careeros.example`), give
that host a catch-all inbound route, and have it POST to `/api/v1/inbound/mail/{token}` —
the local part goes in the path, the provider's Postmark-shaped body passes through
unchanged. A provider that only offers one fixed webhook URL needs a worker or route in
front that expands the recipient's local part into the path. A rule that strips
plus-addressing at the first dot, or rewrites the recipient to a fixed address, produces a
token the backend cannot verify. `docs/DEPLOYMENT.md` has the provider-side paragraph;
this section is the diagnosis when a reader says "someone replied and nothing appeared".

**What a silent address means, in order.**

1. **No address at all.** `GET /api/v1/inbound/link` answers **503**
   `INBOUND_NOT_CONFIGURED` and the settings card says the deployment has no inbox:
   `APP_INBOUND_DOMAIN` is blank, or the boot predates it. Nothing is delivered and
   nothing is lost; set the variable and restart.
2. **An address, but every delivery answers 404 `INBOUND_LINK_INVALID`.** The token did
   not verify: `APP_MAIL_LINK_SECRET` was rotated (every address minted under the old
   secret is dead, along with every calendar and unsubscribe link), the account was
   erased, or the mail path mangled the local part (see above). Rotation is the
   documented revoke — the reader pastes a fresh address from settings, and there is
   nothing to repair server-side.
3. **Deliveries answer 200, the letters are on `/replies`, but intent, company and role
   are null.** The letter was stored before it was read (37.2), so this is a classifier
   outage, not mail loss: the reader can file the letter by hand, and the next delivery
   reads normally. The backend log line names the failure per letter.
4. **Deliveries answer 200 and the letters are filed nowhere.** The reading named no
   company, or named one where the account has several applications and the role did not
   narrow to one. That is the designed answer — a wrong timeline is worse than a waiting
   letter — and the page's picker is the fix, not the server.
5. **429 from the webhook.** The meter is 10 deliveries a minute per address
   (`RATELIMIT_INBOUND_PER_MINUTE`); one address's provider retry burst can hit it. The
   provider's own retry policy decides whether the delivery comes back; if it gives up on
   429, raise the limit or find the loop that is re-delivering.

**What to read.** The row is in `inbound_mails`, scoped to the account:

```sql
SELECT id, from_address, subject, intent, company, role, received_at, filed_at,
       application_id, message_key
FROM inbound_mails
WHERE user_id = '<user id>'
ORDER BY received_at DESC
LIMIT 20;
```

`filed_at` null with `application_id` null is a waiting letter; both set is a filed one.
`message_key` is the deduplication key — a provider that retries the same `MessageID`
stores one row, so two rows with the same subject are two letters, not a loop.

**What this does not mean.** It is not the morning signal mail: that letter is outbound
and has its own section above. And one silent address is not a reader-visible outage on
the other accounts: the webhook's 200 is the provider's receipt, and a forged or
erased-account token's 404 is deliberately indistinguishable from a nonexistent address.

## A stack that looks healthy and is the wrong one

**What you see.** `docker compose ps` shows every service `running` (or even `healthy`),
the landing page renders, `/api/v1/health` answers `ok` — and still nothing happens: no
nightly pull, no morning letter, an upload that ends at its first file. Nothing crashed;
the process came up with different choices than the ones you believe you made. A stale
container, an override file or an exported shell variable won the race against the
`.env` you edited.

**Read the boot line first.** `docker compose logs backend | grep 'boot:'` — one line,
written once at readiness:

```
boot: env=prod port=8080 db=db.internal/career_os redis=cache.internal storage=objects.internal bucket=career_os_files ai=ai.internal mail=smtp push=keypair schedulers=[AiOpsMetrics, AiUsageMetrics, IngestionRepairScheduler, IngestionScheduler, JobWorker, NotificationMailScheduler, ReminderScheduler, RetentionScheduler, WeeklyDigestScheduler]
```

The line is the process describing the objects it actually bound — bound properties, the
chosen mail and push beans, whether a store bean exists, and the scheduler beans the
context really registered — never a re-read of the environment. If it disagrees with
`.env`, the `.env` you edited is not the one this process loaded.

**The words to look for, and what each means.**

1. `env=dev` where you expected `prod`. The production guards (published secrets,
   console mail, default object store) all key off this one word, so a dev-labelled
   production boot has every demo convenience on.
2. `db=unset` or `db=unparseable`. The datasource never bound; requests will fail after
   readiness rather than at boot.
3. `storage=off`. No store bean was created — uploads answer 503 and the resume flow
   ends at its first file. `bucket=unset` is the other half: a store with no bucket name.
4. `mail=console`. Letters go to the log, not to a mailbox; a production install that
   says `console` was never configured. `mail=smtp` is the configured transport.
5. `push=off`. No VAPID pair: registrations are still stored, but no wake is ever signed.
6. `schedulers=` missing a name you rely on. The full set is
   `[AiOpsMetrics, AiUsageMetrics, IngestionRepairScheduler, IngestionScheduler, JobWorker,
   NotificationMailScheduler, ReminderScheduler, RetentionScheduler,
   WeeklyDigestScheduler]`; an empty list means the clock is off entirely, and one missing
   name is a bean that did not load — read earlier in the log for why. None of the alarms
   above can fire from a process with no scheduler, which is why this line comes before
   them.

**What the line never contains.** Passwords, tokens, JDBC or Redis URLs, SMTP credentials
or the private VAPID key — only hosts, names and choices. A unit test builds the line
from sentinel secrets and asserts none of them appears, so an edit that starts echoing a
URL fails the suite rather than leaking in production.

**When there is no boot line at all.** The application never reached readiness: whatever
stopped it is earlier in the log. And on a multi-replica deployment, read every replica's
line — a rolling deploy can leave one process running yesterday's environment.

## A redeploy finishes what it started

**What changed.** The backend stops like a service, not like a process: `server.shutdown`
is `graceful` and `spring.lifecycle.timeout-per-shutdown-phase` is 30 seconds
(`backend/src/main/resources/application.yml`). On `docker compose up -d --no-deps
backend` (or any SIGTERM) the connector stops accepting new connections and requests
already inside the process are allowed to finish. Both compose files set
`stop_grace_period: 40s`, so Docker's SIGKILL comes after the JVM's own bound — Docker's
10-second default would come first and cut the drain short.

**What a redeploy is allowed to cost.**

| In flight at SIGTERM | What happens |
|---|---|
| A request that finishes within 30 seconds | answered normally; the container exits when the drain ends and the new one starts |
| A request still running at 30 seconds | cut at the phase bound. The usual case is a long AI stream (copilot, tailoring and interview answers carry a 180-second budget); the client sees the stream end without its ending and retries |
| A scheduled sweep mid-run | schedulers are beans, not detached workers: they are destroyed with the context and do not fire from the old process. The half-done run is not resumed; the next scheduled run starts fresh |
| New requests during the drain | refused by the closing connector; through a reverse proxy the caller may see a brief 502 until the new container is healthy. That is the rolling update's gap, not a cut request |

**How to see it.** `docker compose logs backend | grep -i 'graceful shutdown'` — the
backend logs `Commencing graceful shutdown. Waiting for active requests to complete`
and, when the drain ends, `Graceful shutdown complete`. A redeploy that shows neither
line is running configuration older than this change.

**Do not raise the phase past the compose grace.** Docker kills at
`stop_grace_period` regardless of what Spring is still waiting for; `ShutdownContractTest`
refuses a compose file whose backend grace does not exceed the YAML phase by at least
five seconds. If a deployment needs a longer drain, raise both numbers in the same
change.

## An ai-service circuit breaker sits open

**What the alert looks like.** `CareerOSCircuitBreakerOpen` fires when
`max(careeros_circuitbreaker_open) == 1` has held for ten minutes: the gauge is 1 while any
Resilience4j circuit breaker the bridge to ai-service owns is in OPEN (or FORCED_OPEN), 0 otherwise.
The backend's door-level breaker watches each configured engine replica's calls; the whole-bridge
breaker watches the door chosen for a turn. Sustained for ten minutes, the refusal is structural —
connections refused, timeouts, TLS/handshake failures — not an error body from the engine, because
the guard ignores 400/404 answers the engine itself produced.

**What the gauge is.** `careeros.circuitbreaker.open` is one untagged gauge, registered by the
backend process that routes the calls. Prometheus scrapes it as
`careeros_circuitbreaker_open`. A breaker in HALF_OPEN does not raise it — the backend gives the
door a probe turn before declaring it gone, and the alarm is for "the backend stopped believing
every configured replica can serve", not for "a replica answered wrong once".

**What you need for the fix, in order.**

1. `/actuator/circuitbreakers` on the backend (or the authenticated `/api/v1/system/resilience`
   JSON — same breakers, same names, one per door plus the whole-bridge one). Note which door the
   open breaker watches.
2. `/api/v1/health` — the deployment's dependency report, `aiNodes` array one row per configured
   engine replica in configured order. Every row shows up/down as the backend probed it. All false
   means the whole engine is unreachable from the backend; some true/some false means a single door
   fell, and the health check eviction in the load balancer should be routing around it without a
   restart.
3. The ai-service container's own logs — the first connect error tells whether the door is crashed,
   the network path is broken, or the container is up but refusing the shared token at the network
   layer (e.g. the engine and backend were restarted with different `INTERNAL_API_TOKEN` values — a
   door that does not answer the probe is not a door, but a door that answers 401 to the bridge is
   exactly the kind that looks silent from the outside).

**What the fix is, in order.**

1. If every replica is false in `aiNodes`: restart or scale the ai-service container. The backend
   keeps serving the non-AI `/api/v1` surface; the AI routes refuse until a door answers.
2. If one replica is false: check the engine replica's container logs for a crash, an OOM, or a
   bind failure. The health check the LB uses (`/health` on the engine) can also fail for a
   replica that is answering HTTP but unhealthy in `ai` state — in which case the LB eviction
   should still route around it; if the eviction loop is fighting you, the door is in a worse state
   than its health line reports and a restart is usually the fastest honest fix.
3. If the engine answers HTTP but the breaker still reads open — look at the bridge's config, not
   the engine: the backend's `AI_SERVICE_INSTANCES` and `INTERNAL_API_TOKEN` must agree across the
   deploy; a token mismatch is a door that speaks HTTP and never lets the bridge in, which the
   breaker (rightly) reads as unreachable.

**If the alarm cleared on its own after the engine redeployed:** that is the alarm's interval
doing its job — wait ten minutes of evidence, not one, before paging. If it comes back the next
time traffic ramps after a deploy, the engine is not healthy fast enough to satisfy the probe and
should start on a longer `start_period` / `initial-delay` than the default lets it.

## The edge is refusing callers

**What the alert looks like.** `CareerOSGatewayRateLimited` fires when
`rate(careeros_gateway_ratelimit_refused_total[5m]) > 0` has held for five minutes: the gateway's
token bucket has refused at least one caller on every scrape interval for five minutes straight.
One refused request is noise — a client that misbehaved once, a script that hammered the login
route for a second; the bucket answered and the moment passed. The alarm is for continuity, which
is what a flood looks like on a counter that keeps moving.

**What the counter is.** `careeros.gateway.ratelimit.refused` is registered by the gateway's edge
filter (`GatewayRateLimitFilter`) and increments once per 429 the token bucket answers. It carries
no caller tag on purpose: the identity is a caller's token hash or address, and a metric tagged by
either grows one series per caller — the cardinality accident that makes a metrics backend fall
over precisely during the flood this counter exists to describe. The bucket's capacity is
`GATEWAY_RATE_LIMIT_PER_MINUTE` (1200/min by default) per caller identity; a refusal means one
identity outran its own bucket, not that the edge is out of capacity for everyone.

**What you need for the fix, in order.**

1. The gateway log — the refused identities are there (the filter logs every 429 with the
   identity class it refused). One identity is a misbehaving client; every identity is a
   deployment-wide event (a crawler, a retry storm after an outage, a probing script).
2. `/actuator/metrics/careeros.gateway.ratelimit.refused` — the running total, to judge scale
   against the bucket's own 1200/min.
3. If the caller is legitimate (an internal integration outrunning its own bucket), raise
   `GATEWAY_RATE_LIMIT_PER_MINUTE` for the edge or give the integration its own identity cadence —
   do not disable the bucket: it is the only thing between the backend and an unauthenticated flood
   (docs/SECURITY.md).

**If the alarm cleared on its own:** the flood ended before you looked — the counter's total
tells you whether anyone was refused since. Persistent refusal from an unknown identity is what
the edge exists for; persistent refusal from your own integrations is a configuration problem, not
an attack.
