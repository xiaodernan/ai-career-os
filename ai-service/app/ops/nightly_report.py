"""The night's verdict, written where a person can read it later.

A failed nightly run is a red X in the Actions list, and the red X expires:
GitHub drops run logs on its own schedule, and nothing in this deployment
kept the outcome. So "did last night's full-stack pass, and what did the
evals measure" had no answer that outlived the run page.

This script is the last step of the nightly job, run with ``if: always()``.
It reads the job's own step outcomes -- which GitHub exposes only inside the
run that produced them -- and posts them to the backend's internal surface
(``POST /api/internal/nightly-reports``), which owns the row. The monitoring
page then reads the history back through ``/api/v1/monitoring/nightly-reports``.

Usage, from ``ai-service/``::

    python -m app.ops.nightly_report \
        --started-at 2026-10-28T03:17:00Z \
        --commit <sha> --run-url <url> \
        --step "backend-it=success" --step "eval=failure" \
        --eval-report-dir evals/reports \
        --url http://localhost:8080 \
        --token <internal token>

Without ``--url`` the payload is built and printed but not sent, so a local
run says exactly what it would have recorded. Exit codes: ``0`` built (and
posted, when a URL was given); ``1`` the post failed; ``2`` the arguments do
not make a sensible record (unknown step syntax, unparsable clock, a night
that finished before it started).
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# GitHub's step vocabulary mapped onto the backend's. The contract is
# total on purpose: an outcome nobody anticipated is recorded as failed --
# an unknown step outcome is not a pass, and the conservative reading is
# the one that gets somebody to look.
_STEP_STATUS = {
    "success": "passed",
    "failure": "failed",
    "cancelled": "failed",
    "skipped": "skipped",
}

MAX_METRICS = 3

# The write surface the recorder posts to. `--url` names the backend's base;
# the path lives here so the workflow passes one variable and inherits the
# route, and an unset variable means "no --url" rather than a relative path.
ENDPOINT = "/api/internal/nightly-reports"


def step_status(outcome: str) -> str:
    """One step outcome in the record's vocabulary."""
    return _STEP_STATUS.get(outcome.strip().lower(), "failed")


def build_payload(
    *,
    steps: list[tuple[str, str]],
    started_at: str,
    finished_at: str,
    commit_sha: str | None = None,
    run_url: str | None = None,
    details: dict[str, str] | None = None,
    source: str = "nightly",
) -> dict:
    """The request body the backend's ``NightlyReportRequest`` declares.

    The overall status is ``passed`` only when there is at least one step and
    every one of them either passed or was skipped. A night with no steps is
    a wiring break, not a green night, so it records as failed.
    """
    details = details or {}
    rows = []
    for name, outcome in steps:
        row = {"name": name, "status": step_status(outcome)}
        detail = details.get(name)
        if detail:
            row["detail"] = detail
        rows.append(row)

    passed = bool(rows) and all(r["status"] in ("passed", "skipped") for r in rows)
    payload = {
        "source": source,
        "status": "passed" if passed else "failed",
        "startedAt": started_at,
        "finishedAt": finished_at,
        "summary": {"steps": rows},
    }
    if commit_sha:
        payload["commitSha"] = commit_sha
    if run_url:
        payload["runUrl"] = run_url
    return payload


def _parse_stamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.strip())
    except ValueError:
        return None


def check_clocks(started_at: str, finished_at: str) -> str | None:
    """The backend's own two refusals, said here first.

    A row that the backend will reject is better refused at the source, with
    the value that was wrong -- the run page keeps the message, the backend's
    400 keeps only a sentence.
    """
    start, end = _parse_stamp(started_at), _parse_stamp(finished_at)
    if start is None:
        return f"started-at is not an ISO timestamp: {started_at!r}"
    if end is None:
        return f"finished-at is not an ISO timestamp: {finished_at!r}"
    if (start.tzinfo is None) != (end.tzinfo is None):
        # Comparing one against the other raises; a record that cannot say
        # which zone its clock is in is not a record yet.
        return "started-at and finished-at must agree on whether they carry a time zone"
    if end < start:
        return f"the night finished ({finished_at}) before it started ({started_at})"
    return None


def eval_detail(report_dir: Path) -> str | None:
    """The newest eval report as one line: a few aggregates and the count.

    The reports are named ``YYYYmmdd-HHMMSS_<experiment>.json``, so sorting
    the file names sorts them by time. A malformed newest file must not cost
    the night its record, so the walk falls through to the next one, and no
    readable report is simply no detail.

    The counts key differs by harness (``n_cases`` for the RAG report,
    ``n_scenarios`` for the agent one); either is a count of what was asked,
    which is the number a reader checks first.
    """
    if not report_dir.is_dir():
        return None
    for path in sorted(report_dir.glob("*.json"), reverse=True):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(report, dict):
            continue
        parts = []
        aggregate = report.get("aggregate")
        if isinstance(aggregate, dict):
            for key in sorted(aggregate):
                value = aggregate[key]
                if isinstance(value, (int, float)):
                    parts.append(f"{key} {value}")
                if len(parts) == MAX_METRICS:
                    break
        count = report.get("n_cases", report.get("n_scenarios"))
        if isinstance(count, int):
            parts.append(f"{count} cases" if "n_cases" in report else f"{count} scenarios")
        return " · ".join(parts) if parts else None
    return None


def post(payload: dict, url: str, token: str) -> None:
    """POST the payload with the shared token. Raises on any non-2xx."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Internal-Token": token,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()


def parse_steps(values: list[str]) -> list[tuple[str, str]]:
    steps = []
    for value in values:
        name, sep, outcome = value.partition("=")
        if not sep or not name.strip() or not outcome.strip():
            raise ValueError(f"a step is name=outcome, not {value!r}")
        steps.append((name.strip(), outcome.strip()))
    return steps


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Record the nightly run in the backend's history.")
    parser.add_argument("--step", action="append", default=[],
                        help="name=outcome, repeated once per job step")
    parser.add_argument("--started-at", required=True,
                        help="when the night started (ISO 8601)")
    parser.add_argument("--finished-at", default=None,
                        help="when it finished; defaults to now")
    parser.add_argument("--commit", default=None, help="the commit the night ran against")
    parser.add_argument("--run-url", default=None, help="the run page a reader can open")
    parser.add_argument("--source", default="nightly",
                        help="the record's source label (default: nightly)")
    parser.add_argument("--eval-report-dir", default=None,
                        help="where the eval harness wrote its reports; the newest "
                             "one's numbers become the `eval` step's detail")
    parser.add_argument("--url", default=None,
                        help="the backend's base URL; without it the payload is "
                             "printed but not recorded")
    parser.add_argument("--token", default=None,
                        help="the internal token sent as X-Internal-Token")
    parser.add_argument("--out", default=None, help="also write the payload here")
    args = parser.parse_args(argv)

    finished_at = args.finished_at or datetime.now().astimezone().isoformat(timespec="seconds")
    problem = check_clocks(args.started_at, finished_at)
    if problem:
        print(problem, file=sys.stderr)
        return 2
    try:
        steps = parse_steps(args.step)
    except ValueError as err:
        print(err, file=sys.stderr)
        return 2
    if not steps:
        # A record with no steps reads as a night in which nothing ran and
        # nothing failed. That is never true, so it is never recorded.
        print("no --step was given; a night with no steps is a wiring break, "
              "and it is not recorded as a green one", file=sys.stderr)
        return 2

    details = {}
    if args.eval_report_dir:
        detail = eval_detail(Path(args.eval_report_dir))
        if detail:
            details["eval"] = detail

    payload = build_payload(
        steps=steps,
        started_at=args.started_at,
        finished_at=finished_at,
        commit_sha=args.commit,
        run_url=args.run_url,
        details=details,
        source=args.source,
    )
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")

    if not args.url:
        print(text)
        print("no --url was given; the payload was built but not recorded", file=sys.stderr)
        return 0
    if not args.token:
        print("--url needs --token: the internal surface refuses an untokened call",
              file=sys.stderr)
        return 2
    try:
        post(payload, args.url.rstrip("/") + ENDPOINT, args.token)
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", "replace")[:500]
        print(f"the backend refused the record: {err.code} {body}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"the record was not posted: {err}", file=sys.stderr)
        return 1
    print(f"recorded {payload['status']} for {args.commit or 'an unnamed commit'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
