"""Tests for the nightly recorder.

The recorder is the only writer of the night's history, and its reader is a
page a person trusts to say whether the install verified itself. So the tests
hold three contracts: the step vocabulary maps onto the backend's (an outcome
nobody anticipated is not a pass), the payload speaks the backend's request
spelling exactly (a renamed key is a 400 the night never sees), and the
workflow really invokes it with ``if: always()`` and a step per suite -- a
recorder that runs only on success can never record the failure it exists for.
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

import yaml

from app.ops import nightly_report as mod

ROOT = Path(__file__).resolve().parents[2]


def _payload(**overrides):
    base = dict(
        steps=[("backend-it", "success"), ("eval", "success")],
        started_at="2026-10-28T03:17:00Z",
        finished_at="2026-10-28T04:02:11Z",
    )
    base.update(overrides)
    return mod.build_payload(**base)


def test_an_outcome_nobody_anticipated_is_not_a_pass():
    assert mod.step_status("success") == "passed"
    assert mod.step_status("skipped") == "skipped"
    assert mod.step_status("failure") == "failed"
    assert mod.step_status("cancelled") == "failed"
    # GitHub's own list is short, and anything outside it -- a renamed
    # outcome, a paste error, an empty string -- records as failed: the
    # reader is deciding whether to trust the night, and an unknown word
    # has not earned "passed".
    assert mod.step_status("timed_out") == "failed"
    assert mod.step_status("") == "failed"
    assert mod.step_status("SUCCESS") == "passed"


def test_a_night_is_green_only_when_every_step_passed_or_was_skipped():
    assert _payload()["status"] == "passed"

    skipped = _payload(steps=[("backend-it", "success"), ("eval", "skipped")])
    assert skipped["status"] == "passed", "a skipped step is not a failure"

    failed = _payload(steps=[("backend-it", "success"), ("eval", "failure")])
    assert failed["status"] == "failed"

    # No steps is a wiring break -- the recorder ran, the job was not
    # described -- and it must never read as a green night.
    assert _payload(steps=[])["status"] == "failed"


def test_the_payload_speaks_the_backend_request_spelling():
    payload = _payload(commit_sha="a" * 40, run_url="https://ci.example/run/1")
    assert set(payload) == {
        "source", "status", "startedAt", "finishedAt", "summary", "commitSha", "runUrl",
    }
    assert payload["source"] == "nightly"
    rows = payload["summary"]["steps"]
    assert [set(r) for r in rows] == [{"name", "status"}, {"name", "status"}]

    # Absent optional facts are left out rather than sent as null: the
    # request record's @Size limits do not reject null, but an explicit
    # null read back as "the job had no commit" is a claim, and
    # "unreported" is the truth.
    bare = _payload()
    assert "commitSha" not in bare and "runUrl" not in bare

    with_detail = _payload(details={"eval": "recall_at_k 0.812 · 26 cases"})
    assert with_detail["summary"]["steps"][1]["detail"] == "recall_at_k 0.812 · 26 cases"
    # A detail for a step that is not in the night is dropped, not invented.
    assert "detail" not in with_detail["summary"]["steps"][0]


def test_the_clock_check_mirrors_the_backend_refusals():
    ok = "2026-10-28T03:17:00Z"
    assert mod.check_clocks(ok, "2026-10-28T04:02:11Z") is None
    assert "not an ISO timestamp" in mod.check_clocks("yesterday", "2026-10-28T04:02:11Z")
    assert "not an ISO timestamp" in mod.check_clocks(ok, "26:00")
    assert "before it started" in mod.check_clocks(
        "2026-10-28T04:02:11Z", "2026-10-28T03:17:00Z")
    # Naive against zoned raises in Python and would be a 500-free crash in
    # CI; the check names it instead.
    assert "time zone" in mod.check_clocks("2026-10-28T03:17:00", ok)


def test_the_newest_eval_report_becomes_the_eval_detail(tmp_path):
    older = tmp_path / "20261027-031700_exp-aaaa.json"
    older.write_text(json.dumps({"n_cases": 20, "aggregate": {"recall_at_k": 0.5}}),
                     encoding="utf-8")
    newest = tmp_path / "20261028-031700_exp-bbbb.json"
    newest.write_text(
        json.dumps({"n_cases": 26,
                    "aggregate": {"recall_at_k": 0.812, "faithfulness": 0.9,
                                  "precision_at_k": 0.667, "mrr": 0.7}}),
        encoding="utf-8")
    assert mod.eval_detail(tmp_path) == \
        "faithfulness 0.9 · mrr 0.7 · precision_at_k 0.667 · 26 cases"

    # A malformed newest file must not cost the night its record: the walk
    # falls through to the newest readable one.
    newest.write_text("{not json", encoding="utf-8")
    assert mod.eval_detail(tmp_path) == "recall_at_k 0.5 · 20 cases"

    # The agent harness counts scenarios, not cases.
    only = tmp_path / "20261029-031700_agent-cccc.json"
    only.write_text(json.dumps({"n_scenarios": 27, "aggregate": {"tool_recall": 1.0}}),
                    encoding="utf-8")
    assert mod.eval_detail(tmp_path) == "tool_recall 1.0 · 27 scenarios"

    assert mod.eval_detail(tmp_path / "missing") is None


def test_the_post_carries_the_internal_token(monkeypatch):
    seen = {}

    class _Response:
        def read(self):
            return b"{}"

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(request, timeout=None):
        seen["request"] = request
        seen["timeout"] = timeout
        return _Response()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    payload = _payload()
    mod.post(payload, "http://backend:8080/api/internal/nightly-reports", "secret-token")

    request = seen["request"]
    assert request.full_url == "http://backend:8080/api/internal/nightly-reports"
    assert request.get_method() == "POST"
    assert request.get_header("X-internal-token") == "secret-token"
    assert json.loads(request.data.decode("utf-8")) == payload


def test_the_cli_refuses_what_would_be_a_bad_row(capsys):
    # No steps: a wiring break, refused loudly.
    assert mod.main(["--started-at", "2026-10-28T03:17:00Z"]) == 2
    assert "wiring break" in capsys.readouterr().err

    # A step without an outcome, and a night that ended before it began.
    assert mod.main(["--started-at", "2026-10-28T03:17:00Z", "--step", "eval"]) == 2
    assert mod.main(["--started-at", "2026-10-28T04:00:00Z",
                     "--finished-at", "2026-10-28T03:00:00Z",
                     "--step", "eval=success"]) == 2

    # Without a URL the payload is built and printed, and nothing is claimed
    # to have been recorded.
    code = mod.main(["--started-at", "2026-10-28T03:17:00Z",
                     "--finished-at", "2026-10-28T04:02:11Z",
                     "--step", "eval=success"])
    captured = capsys.readouterr()
    assert code == 0
    assert json.loads(captured.out)["status"] == "passed"
    assert "not recorded" in captured.err

    # A URL without a token would be a 401 at the far end; refused here.
    assert mod.main(["--started-at", "2026-10-28T03:17:00Z",
                     "--step", "eval=success",
                     "--url", "http://backend:8080"]) == 2


def test_the_nightly_job_records_itself_even_when_it_fails():
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml")
                              .read_text(encoding="utf-8"))
    steps = workflow["jobs"]["nightly"]["steps"]

    recorder = [s for s in steps if "app.ops.nightly_report" in (s.get("run") or "")]
    assert len(recorder) == 1, "the nightly job records itself exactly once"
    step = recorder[0]
    assert step.get("if") == "always()", \
        ("the recorder must run on failure too -- a recorder that only runs on success "
         "can never record the failure it exists for")
    assert step.get("working-directory") == "ai-service"

    run = step["run"]
    ids = {s["id"] for s in steps if "id" in s}
    referenced = set(re.findall(r"steps\.([\w-]+)\.outcome", run))
    assert referenced, "the recorder must read the job's own step outcomes"
    assert referenced <= ids, f"reads undefined step ids: {sorted(referenced - ids)}"
    # An id exists only so the recorder can read it; a tracked step that
    # dropped out of the payload is a suite that silently stops reporting.
    assert ids <= referenced, f"tracked steps missing from the record: {sorted(ids - referenced)}"

    pairs = re.findall(r'--step "([\w-]+)=\$\{\{ steps\.([\w-]+)\.outcome \}\}"', run)
    assert {sid for _, sid in pairs} == referenced, \
        "every outcome the recorder reads must become a named step in the payload"
    assert ("eval", "eval") in pairs, "the eval harness's numbers belong to the eval step"

    assert "--started-at" in run and "night-start" in run, \
        "the row needs the job's own start, not the recorder's clock"
    assert '--url "$OPS_URL' in run, "the endpoint comes from the configured variable"
    assert '--token "$OPS_TOKEN' in run, "the internal token comes from a secret"
