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

The second half of the file is human. An alert without a page is a page at 03:00 with nothing
to read, so every rule carries `annotations.runbook`, every one of those links is checked
against the headings `docs/RUNBOOK.md` actually has (a GitHub anchor, lowercased with the
punctuation dropped, recomputed here rather than trusted), and the alert's own name has to
appear in the runbook text -- the prose is allowed to be longer than the rule, but not to be
about other alarms. The runbook is also where an operator is told which script backs the stack
up, so every `scripts/*.sh` it names must exist and start with a shebang; a runbook that sends
someone to a file that is not in the tree is worse than a runbook that says nothing.

Two numbers are quoted in both places on purpose -- the 26-hour silence (`93600` seconds) and
the 5 USD budget -- and both are read off the rule file here, because a prose threshold that
drifts from its expression is an operator tuning a number that no longer means anything.

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
NIGHTLY_REPORT_SERVICE = BACKEND / "src" / "main" / "java" / "com" / "careeros" / "report" / "service" / "NightlyReportService.java"
NIGHTLY_CARD = ROOT / "frontend" / "src" / "components" / "monitoring" / "nightly-history.tsx"

# exported Prometheus name -> (the Java file that registers it, the dotted Micrometer name in it).
# The counter's `_total` is the exporter's suffix: the Java literal stops before it.
METRICS = {
    "careeros_ingestion_runs_total": (INGESTION_METRICS, "careeros.ingestion.runs"),
    "careeros_ingestion_last_success_timestamp": (INGESTION_METRICS, "careeros.ingestion.last.success.timestamp"),
    "careeros_ai_cost_usd_24h": (AI_USAGE_METRICS, "careeros.ai.cost.usd.24h"),
    "careeros_ai_tokens_24h": (AI_USAGE_METRICS, "careeros.ai.tokens.24h"),
    "careeros_ai_calls_24h": (AI_USAGE_METRICS, "careeros.ai.calls.24h"),
    "careeros_nightly_last_finished_timestamp": (NIGHTLY_VERDICT_METRICS, "careeros.nightly.last.finished.timestamp"),
    "careeros_nightly_consecutive_failures": (NIGHTLY_VERDICT_METRICS, "careeros.nightly.consecutive.failures"),
    "careeros_digest_delivery_total": (DIGEST_METRICS, "careeros.digest.delivery"),
    "careeros_digest_last_sweep_timestamp": (DIGEST_METRICS, "careeros.digest.last.sweep.timestamp"),
    "careeros_signals_delivery_total": (SIGNAL_METRICS, "careeros.signals.delivery"),
    "careeros_signals_last_sweep_timestamp": (SIGNAL_METRICS, "careeros.signals.last.sweep.timestamp"),
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
})

# The columns the budget query sums, each one a column of the ledger migration.
USAGE_COLUMNS = ("cost_usd", "input_tokens", "output_tokens", "created_at")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


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
