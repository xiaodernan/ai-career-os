"""The alarms name metrics that ship, and every alarm links to a page that says what to do.

`ops/prometheus/alerts.yml` is the first artifact in this repo that is *read by a machine nobody
here runs*: a Prometheus evaluates those expressions against the backend's scrape endpoint, and
an expression that names a metric the backend never registers is not a broken rule -- it is a
rule that evaluates to the empty vector and therefore never fires, silently, forever. So the
metrics in the file are pinned twice: once as the dotted name Micrometer takes (a literal in the
Java class that registers it), and once as the underscored name the exporter renders, because
that is the spelling the expressions have to use. The counter is the interesting half of that
conversion: `careeros.ingestion.runs` arrives as `careeros_ingestion_runs_total`, with a suffix
the Java source never writes -- grep the Java for the exported name and the gate would report a
missing metric that is in fact registered.

The roster is the registry, not the rules' reading list. `declared_meters()` walks every
backend file that consults `MeterRegistry` -- the import is the population, so a class that
registers a meter cannot sit outside it -- and reads the exact `careeros.` literals those files
declare. `METRICS` has to name every one of them, and the reverse test asks the question the
forward test never did: is each meter either read by a rule or excused in `UNALARMED` with a
written reason? Both directions matter for the same reason. A rule on an unregistered name
evaluates to the empty vector forever; a registered meter no rule reads is a series an operator
can only find by already knowing it exists. `careeros.storage.objects_reclaimed` sat in that
state while the runbook told an operator to read it. An excuse is a decision, not a leftover:
an entry whose meter a rule later reads fails the gate, so the reason cannot outlive the gap it
describes.

The second half of the file is human. An alert without a page is a page at 03:00 with nothing
to read, so every rule carries `annotations.runbook`, every one of those links is checked
against the headings `docs/RUNBOOK.md` actually has (a GitHub anchor, lowercased with the
punctuation dropped, recomputed here rather than trusted), and the alert's own name has to
appear in the runbook text -- the prose is allowed to be longer than the rule, but not to be
about other alarms. The runbook is also where an operator is told which script backs the stack
up, so every `scripts/*.sh` it names must exist and start with a shebang; a runbook that sends
someone to a file that is not in the tree is worse than a runbook that says nothing.

Three numbers are quoted in both places on purpose -- the 26-hour silence (`93600` seconds),
the 5 USD budget, and the reminder clock's five missed ticks (`300` seconds, read off the
scheduler's own default here) -- because a prose threshold that drifts from its expression is
an operator tuning a number that no longer means anything.
The verdict alarms have the same problem one level up: their 36-hour window is the service's
own `STALE_AFTER_HOURS`, and their streak threshold is the nightly card's warning line. Both
are read from the sources that promise them (the Java constant, the component's literal) and
compared to the expressions here, because an alarm that fires on a different number than the
page warns at is two judgements wearing one name.

The last reading is the ledger's: the budget gauge is a SQL query over `ai_usage_events`, and
the columns it sums must be columns the migration creates. The query is pinned to the trailing
24 hours, not to a calendar day, because the alert is about spend that has not gone away.
"""

import re
from pathlib import Path

import yaml

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
ALERTS = ROOT / "ops" / "prometheus" / "alerts.yml"
RUNBOOK = ROOT / "docs" / "RUNBOOK.md"
BACKEND = ROOT / "backend"
MIGRATION = BACKEND / "src" / "main" / "resources" / "db" / "migration" / "V1__init_schema.sql"
INGESTION_METRICS = BACKEND / "src" / "main" / "java" / "com" / "careeros" / "job" / "service" / "IngestionMetrics.java"
AI_USAGE_METRICS = BACKEND / "src" / "main" / "java" / "com" / "careeros" / "ai" / "service" / "AiUsageMetrics.java"
NIGHTLY_VERDICT_METRICS = BACKEND / "src" / "main" / "java" / "com" / "careeros" / "report" / "service" / "NightlyVerdictMetrics.java"
DIGEST_METRICS = BACKEND / "src" / "main" / "java" / "com" / "careeros" / "report" / "service" / "WeeklyDigestDeliveryMetrics.java"
SIGNAL_METRICS = BACKEND / "src" / "main" / "java" / "com" / "careeros" / "notification" / "service" / "NotificationDeliveryMetrics.java"
PUSH_METRICS = BACKEND / "src" / "main" / "java" / "com" / "careeros" / "push" / "service" / "PushDeliveryMetrics.java"
REMINDER_CLOCK = BACKEND / "src" / "main" / "java" / "com" / "careeros" / "notification" / "service" / "ReminderScheduler.java"
RETENTION_METRICS = BACKEND / "src" / "main" / "java" / "com" / "careeros" / "auth" / "retention" / "RetentionMetrics.java"
UNNAMED_RECLAIMER = BACKEND / "src" / "main" / "java" / "com" / "careeros" / "auth" / "retention" / "UnnamedObjectReclaimer.java"
STORED_OBJECT_RECLAIMER = BACKEND / "src" / "main" / "java" / "com" / "careeros" / "knowledge" / "service" / "StoredObjectReclaimer.java"
RATE_LIMIT_METRICS = BACKEND / "src" / "main" / "java" / "com" / "careeros" / "ratelimit" / "RateLimitMetrics.java"
REGISTRATION_ROOT = BACKEND / "src" / "main" / "java"
NIGHTLY_REPORT_SERVICE = BACKEND / "src" / "main" / "java" / "com" / "careeros" / "report" / "service" / "NightlyReportService.java"
NIGHTLY_CARD = ROOT / "frontend" / "src" / "components" / "monitoring" / "nightly-history.tsx"

# exported Prometheus name -> (the Java file that registers it, the dotted Micrometer name in it).
# The counter's `_total` is the exporter's suffix: the Java literal stops before it. Every meter
# the backend registers appears here, read or not -- the reverse test below holds this roster
# complete against the files that consult the registry.
METRICS = {
    "careeros_ingestion_runs_total": (INGESTION_METRICS, "careeros.ingestion.runs"),
    "careeros_ingestion_last_success_timestamp": (INGESTION_METRICS, "careeros.ingestion.last.success.timestamp"),
    "careeros_ai_cost_usd_24h": (AI_USAGE_METRICS, "careeros.ai.cost.usd.24h"),
    "careeros_ai_tokens_24h": (AI_USAGE_METRICS, "careeros.ai.tokens.24h"),
    "careeros_ai_calls_24h": (AI_USAGE_METRICS, "careeros.ai.calls.24h"),
    "careeros_nightly_last_finished_timestamp": (NIGHTLY_VERDICT_METRICS, "careeros.nightly.last.finished.timestamp"),
    "careeros_nightly_consecutive_failures": (NIGHTLY_VERDICT_METRICS, "careeros.nightly.consecutive.failures"),
    "careeros_digest_delivery_total": (DIGEST_METRICS, "careeros.digest.delivery"),
    "careeros_digest_last_delivered_timestamp": (DIGEST_METRICS, "careeros.digest.last.delivered.timestamp"),
    "careeros_digest_last_sweep_timestamp": (DIGEST_METRICS, "careeros.digest.last.sweep.timestamp"),
    "careeros_signals_delivery_total": (SIGNAL_METRICS, "careeros.signals.delivery"),
    "careeros_signals_last_delivered_timestamp": (SIGNAL_METRICS, "careeros.signals.last.delivered.timestamp"),
    "careeros_signals_last_sweep_timestamp": (SIGNAL_METRICS, "careeros.signals.last.sweep.timestamp"),
    "careeros_push_delivery_total": (PUSH_METRICS, "careeros.push.delivery"),
    "careeros_reminders_last_tick_timestamp": (PUSH_METRICS, "careeros.reminders.last.tick.timestamp"),
    "careeros_retention_deleted_rows_total": (RETENTION_METRICS, "careeros.retention.deleted_rows"),
    "careeros_retention_last_sweep_timestamp": (RETENTION_METRICS, "careeros.retention.last.sweep.timestamp"),
    "careeros_ratelimit_decisions_total": (RATE_LIMIT_METRICS, "careeros.ratelimit.decisions"),
    # 48.2's per-pass verdict. The sweep's own timestamp moves through a night whose listing the
    # store refused -- the pass finishes, its tables and its purge run -- so the alarm about the
    # bucket has to read a number that says only "the store would not answer", once per pass.
    "careeros_storage_bucket_reads_total": (UNNAMED_RECLAIMER, "careeros.storage.bucket_reads"),
    "careeros_storage_objects_reclaimed_total": (STORED_OBJECT_RECLAIMER, "careeros.storage.objects_reclaimed"),
    "careeros_storage_objects_judged_total": (UNNAMED_RECLAIMER, "careeros.storage.objects_judged"),
}

# Meters no rule reads, each with the reason the absence is a decision rather than a hole.
#
# The reverse direction needs somewhere to put a deliberate silence. Without this table the
# gate would either fail on the healthy meters no rule reads or be relaxed into a list of names; with it,
# an exemption is a written judgement and the next meter to ship has to be one of three
# things: watched, excused here, or caught. The substitute reading named in each reason is the
# point -- a meter is unalarmed because another one answers the operator's question, or
# because there is no threshold a quiet week could not cross.
UNALARMED = {
    "careeros_ai_tokens_24h":
        "The budget rule reads the dollar figure this gauge decomposes; a raw token count has no "
        "threshold of its own -- a busy day within budget is not a fault -- and the usage panel "
        "reads the same ledger for its shape.",
    "careeros_ai_calls_24h":
        "Call count prices nothing by itself -- one expensive call and a thousand cheap ones read "
        "the same -- so the money rule is the one with a number; the figure is a dashboard "
        "reading of the same rolling window.",
    "careeros_digest_last_delivered_timestamp":
        "A week with no applications writes no letter, so a flat marker is healthy; the sweep "
        "heartbeat covers the clock and CareerOSDigestDeliveryFailing covers the relay.",
    "careeros_signals_last_delivered_timestamp":
        "A quiet morning with nothing to say moves no marker; CareerOSSignalSweepStale covers the "
        "clock and CareerOSSignalMailFailing covers the relay, which leaves this as the "
        "dashboard's last-acceptance reading.",
    "careeros_push_delivery_total":
        "The outcomes are not one judgement: gone is a retired browser and not_configured is an "
        "install without VAPID keys, so no single threshold covers the family; the minute clock "
        "has its own alarm, and a refused wake leaves the in-app inbox.",
    "careeros_retention_deleted_rows_total":
        "A stopped sweep leaves this counter at its last value, indistinguishable from a quiet "
        "night, and the first purge of a backlog would cross any rate threshold; the sweep's own "
        "timestamp (CareerOSRetentionSweepStale) is the alarm.",
    "careeros_ratelimit_decisions_total":
        "No known-good refusal rate exists yet, so any threshold would page on a busy minute; the "
        "family is exported for dashboards, and DEPLOYMENT.md records the decision until a "
        "baseline is measured.",
    "careeros_storage_objects_reclaimed_total":
        "An object that outlives its row is a storage cost, not an outage, and a counter with no "
        "baseline would page on a quiet week; a failed reclaim is logged with its key and retried "
        "by the next delete or purge.",
    "careeros_storage_objects_judged_total":
        "One object the store would not release is retried by the next night and named in the WARN "
        "line meanwhile; the four verdicts are the dashboard companion to the listing-refusal "
        "rule, not a second judgement.",
}

ALERT_NAMES = frozenset({
    "CareerOSIngestionNightMissed",
    "CareerOSIngestionFailing",
    "CareerOSNightlyVerificationStale",
    "CareerOSNightlyVerificationFailing",
    "CareerOSAiBudgetBurn",
    "CareerOSDigestDeliveryFailing",
    "CareerOSDigestSweepStale",
    "CareerOSSignalMailFailing",
    "CareerOSSignalSweepStale",
    "CareerOSReminderClockStale",
    "CareerOSRetentionSweepStale",
    "CareerOSBucketListingRefused",
})

# The columns the budget query sums, each one a column of the ledger migration.
USAGE_COLUMNS = ("cost_usd", "input_tokens", "output_tokens", "created_at")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def declared_meters() -> dict:
    """Dotted Micrometer name -> the file that declares it, read off the registry's users.

    The population is structural: a class that registers a meter consults MeterRegistry -- a
    fully-qualified reference still contains the word -- so the walk takes the files that name
    it rather than a list somebody has to remember to extend. A file inside that population
    that declares no careeros meter fails loudly: either it registers under a prefix no rule
    here can watch, or the census has stopped seeing a name it used to.
    """
    out = {}
    for source in sorted(REGISTRATION_ROOT.rglob("*.java")):
        text = read(source)
        if "MeterRegistry" not in text:
            continue
        names = set(re.findall(r'"(careeros\.[a-z0-9._]+)"', text))
        assert names, (
            f"{source.relative_to(ROOT)} consults MeterRegistry and declares no careeros meter; "
            "a meter registered under another prefix is a reading no rule here can watch"
        )
        for name in names:
            assert name not in out, f"{name} is declared in both {out[name]} and {source}"
            out[name] = source
    assert out, "the registration walk found no meter at all"
    return out


def rules():
    document = yaml.safe_load(read(ALERTS))
    out = {}
    for group in document["groups"]:
        for rule in group["rules"]:
            out[rule["alert"]] = rule
    return out


def slug(heading: str) -> str:
    """GitHub's anchor for a heading: lowercase, punctuation dropped, spaces to hyphens."""
    kept = "".join(ch for ch in heading.strip().lower() if ch.isalnum() or ch in " -_")
    return "-".join(kept.split())


def headings() -> set:
    return {
        slug(match.group(1))
        for match in re.finditer(r"(?m)^#{1,6}\s+(.+?)\s*$", read(RUNBOOK))
    }


def test_every_alarm_is_pinned_and_each_carries_an_audience_and_a_page():
    pinned = rules()

    assert set(pinned) == ALERT_NAMES, (
        "a new alarm needs a name in this gate, a section in docs/RUNBOOK.md, and a reader "
        "who knows what it pages for"
    )
    for name, rule in pinned.items():
        assert rule["expr"].strip(), f"{name} has no expression"
        assert rule["for"].strip(), f"{name} has no `for`: it would flap on a single scrape"
        assert rule["labels"]["service"] == "career-os-backend", (
            "every alert says which stack raised it; the label is what a shared Alertmanager routes on"
        )
        assert rule["labels"]["severity"] in {"critical", "warning"}, f"{name} has no severity anyone acts on"
        assert rule["annotations"]["summary"].strip(), f"{name} has no summary"
        assert rule["annotations"]["description"].strip(), f"{name} has no description"
        assert rule["annotations"]["runbook"].startswith("docs/RUNBOOK.md#"), (
            f"{name} must link to a section of the runbook, not to the file's top"
        )


def test_every_metric_an_alarm_reads_is_a_name_java_registers():
    # Scan each rule's expression, not the whole file: a name that appears only in prose is not
    # read by Prometheus, and -- the reason this test exists -- a misspelled name is read by it
    # forever and never matches. The token pattern deliberately starts at `career`, so a typo
    # like `careers_ai_cost_usd_24h` (one letter off) is still caught rather than skipped by a
    # scan that only looked for `careeros_`: the first version of this gate pinned no rule's
    # spelling at all, and both shipped expressions were one `s` short of their gauges.
    used = set()
    for name, rule in rules().items():
        tokens = set(re.findall(r"\bcareer\w*", rule["expr"]))
        assert tokens, (
            f"{name} reads no metric from this project's namespace: an alert whose numbers come "
            f"from nowhere either fires on nothing or fires on another stack's metric"
        )
        used |= tokens

    assert used, "no metric is read by any rule; the alerts cannot ever fire"
    unknown = used - set(METRICS)
    assert not unknown, (
        f"these names are read by a rule and registered nowhere: {sorted(unknown)}. A rule on a "
        "missing metric evaluates to the empty vector and never fires"
    )
    for exported, (source, dotted) in METRICS.items():
        assert dotted in read(source), (
            f"{exported} is rendered from {dotted}, which {source.relative_to(ROOT)} does not register"
        )


def test_every_meter_that_ships_is_alarmed_or_excused_by_name():
    # The forward test asks whether a rule reads a registered name. This is the reverse: does
    # every registered name reach an operator, by a rule or by a reason? The census makes the
    # population checkable, so a new meter cannot slip in unread and an old excuse cannot
    # outlive the rule that starts reading its meter.
    census = declared_meters()
    roster = {dotted for _, dotted in METRICS.values()}
    assert set(census) == roster, (
        "the registry and the roster disagree -- meters registered and not in METRICS: "
        f"{sorted(set(census) - roster)}; METRICS rows with no registration in the walked files: "
        f"{sorted(roster - set(census))}. A new meter has to be named in METRICS before it can "
        "be alarmed or excused"
    )

    used = set()
    for rule in rules().values():
        used |= set(re.findall(r"\bcareer\w*", rule["expr"]))
    unalarmed = {exported for exported in METRICS if exported not in used}

    unknown = set(UNALARMED) - set(METRICS)
    assert not unknown, (
        f"these excuses name a meter this project does not ship: {sorted(unknown)}. A typo here "
        "excuses nothing, because nothing registers under it"
    )
    missing = unalarmed - set(UNALARMED)
    assert not missing, (
        f"these meters ship and no rule reads them: {sorted(missing)}. Add a rule that watches "
        "one, or a line in UNALARMED that says why the reading has no threshold"
    )
    stale = set(UNALARMED) - unalarmed
    assert not stale, (
        f"these meters are excused and a rule reads them: {sorted(stale)}. The reason has to go "
        "when the rule arrives -- an excuse for a watched meter is a comment a future reader "
        "will trust instead of the rule"
    )

    for exported, reason in UNALARMED.items():
        assert len(reason) >= 60, (
            f"{exported}'s excuse is a label, not a reason: {reason!r}. The gate holds an "
            "exemption to a written decision, because 'not alarmed' is the state every missing "
            "alarm starts in"
        )


def test_the_counter_is_rendered_with_a_total_the_java_never_writes():
    exported = "careeros_ingestion_runs_total"
    source, dotted = METRICS[exported]

    assert dotted.replace(".", "_") + "_total" == exported, (
        "the exporter renders the dotted name with underscores and suffixes a counter with `_total`"
    )
    assert "careeros_ingestion_runs_total" not in read(source), (
        "the Java registers the dotted name; the `_total` is the exporter's suffix"
    )
    assert 'tag("status"' in read(source), (
        "the outcome is a tag, so a failure rate is one division and a new outcome is a tag value"
    )


def test_every_runbook_link_is_a_heading_the_runbook_has():
    available = headings()

    for name, rule in rules().items():
        anchor = rule["annotations"]["runbook"].split("#", 1)[1]
        assert anchor in available, (
            f"{name} links to #{anchor}, but docs/RUNBOOK.md has no heading that renders as it: "
            f"{sorted(available)}"
        )


def test_the_reminder_clock_alarm_is_five_ticks_and_the_page_quotes_it():
    # The clock's cadence is the scheduler's own default and the alarm's window is five of
    # those ticks. Neither number is recalled: a rule that fired after one slow tick would
    # page on every deploy's drain, and a rule that waited twenty ticks would let a due
    # reminder miss its moment for twenty minutes before anyone heard.
    tick = int(re.search(r"tick-ms:(\d+)", read(REMINDER_CLOCK)).group(1))
    window = 5 * tick // 1000
    expr = rules()["CareerOSReminderClockStale"]["expr"]
    assert f"> {window}" in expr, (
        f"the alarm's window is not five ticks of the scheduler's {tick} ms default: {expr!r}"
    )
    prose = read(RUNBOOK)
    assert f"time() - careeros_reminders_last_tick_timestamp > {window}" in prose, (
        "the runbook has to quote the window the rule uses; a prose threshold that drifts "
        "from its expression is an operator tuning a number that no longer means anything"
    )
    assert "five missed ticks" in prose


def test_the_runbook_says_what_each_alarm_means_by_its_name():
    prose = read(RUNBOOK)

    for name in ALERT_NAMES:
        assert name in prose, f"{name} fires and the runbook never says its name"
    assert "93600" in prose, "the prose must quote the same 26 hours the rule uses"
    assert "129600" in prose, "the prose must quote the same 36 hours the stale rule uses"
    assert "5 USD" in prose, "the prose must quote the same budget the rule uses"


def test_the_verdict_alarms_read_the_numbers_the_page_and_the_service_promise():
    # The window is the service's constant, rendered as seconds in the expression; the streak
    # threshold is the nightly card's own warning line. An alarm that fires on a different
    # number than the page warns at is two judgements wearing one name.
    pinned = rules()

    hours = int(re.search(r"STALE_AFTER_HOURS\s*=\s*(\d+)", read(NIGHTLY_REPORT_SERVICE)).group(1))
    assert hours == 36, f"the stale window moved to {hours} hours; re-aim the rule and the runbook"
    stale = pinned["CareerOSNightlyVerificationStale"]["expr"]
    assert f"> {hours * 3600}" in stale, (
        f"the rule's silence window is not the service's {hours} hours ({hours * 3600} seconds): "
        f"{stale!r}"
    )

    card = read(NIGHTLY_CARD)
    page_line = re.search(r"consecutiveFailures\s*>=\s*(\d+)", card)
    assert page_line, "the nightly card warns on the streak with a literal threshold"
    failing = pinned["CareerOSNightlyVerificationFailing"]["expr"]
    assert f">= {page_line.group(1)}" in failing, (
        f"the alarm fires at {failing!r} and the card warns at >={page_line.group(1)}: "
        "one judgement with two numbers is two judgements"
    )


def test_the_runbook_names_only_scripts_that_ship_and_announce_themselves():
    prose = read(RUNBOOK)
    named = set(re.findall(r"scripts/[A-Za-z0-9_.-]+\.sh", prose))

    assert named, "the runbook has to tell an operator which script backs the stack up"
    for relative in sorted(named):
        script = ROOT / relative
        assert script.is_file(), f"docs/RUNBOOK.md sends the operator to {relative}, which is not in the tree"
        first_line = read(script).splitlines()[0]
        assert first_line.startswith("#!"), f"{relative} does not announce its interpreter"
    assert "ops/prometheus/alerts.yml" in prose


def test_the_budget_gauge_reads_columns_the_migration_creates():
    sql = read(AI_USAGE_METRICS)
    assert "interval '24 hours'" in sql, (
        "the budget is a rolling window; a calendar day would jump to zero at midnight"
    )
    assert "from ai_usage_events" in sql

    block = re.search(
        r"CREATE TABLE ai_usage_events \((?P<body>.*?)\n\);",
        read(MIGRATION),
        re.DOTALL,
    )
    assert block, "the ledger table is created in V1__init_schema.sql"
    declared = {
        match.group(1)
        for match in re.finditer(r"(?m)^\s{2}([a-z_]+)\s+", block.group("body"))
    }
    for column in USAGE_COLUMNS:
        assert column in declared, f"the budget query sums {column}, which the ledger does not have"
        assert column in sql, f"{column} is in the ledger but the gauge's query never reads it"
