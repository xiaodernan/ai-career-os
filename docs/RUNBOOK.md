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
| `CareerOSNightlyVerificationStale` | critical | No nightly verification has finished in 36 hours | [The nightly verification stopped reporting](#the-nightly-verification-stopped-reporting) |
| `CareerOSNightlyVerificationFailing` | warning | Two or more of the newest nightly runs failed | [The nightly verification keeps failing](#the-nightly-verification-keeps-failing) |
| `CareerOSAiBudgetBurn` | warning | The trailing 24 hours cost more than 5 USD | [The AI budget is burning](#the-ai-budget-is-burning) |

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

Two restores, two commands, both destructive. Stop the writers first.

**Database.** With the backend and ai-service stopped:

```bash
COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml docker compose stop backend ai-service
docker compose exec -T postgres sh -c \
  'pg_restore --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges' \
  < backups/careeros-<stamp>.dump
COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml docker compose start backend ai-service
```

`--clean --if-exists` drops the objects the dump is about to recreate, so the result
is the backup's schema rather than a merge with whatever is left. Flyway runs on the
restarted backend and finds the schema already at the dump's version.

**Files.** With MinIO stopped, write the archive back onto the data volume:

```bash
COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml docker compose stop minio
docker run --rm --volumes-from "$(docker compose ps -q minio)" \
  -v "$(pwd)/backups:/backups:ro" alpine \
  sh -c 'rm -rf /data/* && tar -C /data -xzf /backups/careeros-<stamp>-files.tgz'
COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml docker compose start minio
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
`careeros.ai.metrics-refresh-ms`, one minute by default), and
`backend/src/main/java/com/careeros/report/service/NightlyVerdictMetrics.java`
(the newest nightly finish and the failure streak, moved by each recorded night and
once at boot). A metric missing from the scrape means the bean did not start: the
backend log has the reason.

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
