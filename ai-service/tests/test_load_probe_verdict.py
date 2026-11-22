"""The pressure probe's --strict verdict is a gate, so it must fail for the right reasons.

`scripts/load_probe.py` measures by default (always exit 0) but `--strict` turns
those measurements into a PASS/FAIL. The judgement lives in a pure function so it
can be proven here without a live stack: saturation is acceptable, but a 5xx, a
dropped connection, a wrong-password login that succeeds, or a health probe that
does not recover is a real failure the operator must see as non-zero.

Historical note: a load probe that only prints rows cannot gate a pipeline. This
is the smallest thing that makes the night's pressure run mean something.
"""

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROBE = REPO / "scripts" / "load_probe.py"


def _load():
    spec = importlib.util.spec_from_file_location("load_probe", PROBE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lp = _load()


def _ramp(status=None):
    return [{"workers": 50, "status": status or {200: 100}}]


def _authed(status=None, registered=True):
    return {"registered": registered, "http": 200 if registered else 422,
            "status": status or {200: 60}}


def _gate(status=None, health=200):
    return {"status": status or {401: 100}, "post_storm_health_http": health}


def test_a_clean_run_passes():
    assert lp._strict_failures(_ramp(), _authed(), _gate()) == []


def test_connection_errors_count_even_without_a_status_code():
    out = lp._strict_failures(_ramp({200: 90, 0: 10}), _authed(), _gate())
    assert any("connection_errors=10" in x for x in out)


def test_a_5xx_on_any_ramp_step_fails():
    out = lp._strict_failures(_ramp({200: 99, 503: 1}), _authed(), _gate())
    assert any("5xx=" in x for x in out)


def test_a_failed_registration_is_named():
    out = lp._strict_failures(_ramp(), _authed(registered=False), _gate())
    assert any("registration failed" in x for x in out)


def test_a_registration_timeout_is_named_not_a_crash():
    # A registration that misses the client timeout right after a saturation ramp
    # returns http=0 with a note; the strict verdict must name it, so a probe run
    # reports FAIL rather than dying with a traceback (which hides every other row).
    timed_out = {"registered": False, "http": 0, "note": "registration transport: ReadTimeout"}
    out = lp._strict_failures(_ramp(), timed_out, _gate())
    assert any("registration failed http=0" in x for x in out)


def test_unexpected_errors_on_the_authed_read_fail():
    out = lp._strict_failures(_ramp(), _authed({200: 58, 500: 2}), _gate())
    assert any("authed read" in x for x in out)


def test_a_wrong_password_that_succeeds_is_a_security_failure():
    out = lp._strict_failures(_ramp(), _authed(), _gate({401: 98, 200: 2}))
    assert any("SUCCEEDED" in x for x in out)


def test_a_5xx_in_the_credential_storm_fails():
    out = lp._strict_failures(_ramp(), _authed(), _gate({401: 95, 500: 5}))
    assert any("auth gate: 5xx=" in x for x in out)


def test_dropped_connections_in_the_credential_storm_fail():
    out = lp._strict_failures(_ramp(), _authed(), _gate({401: 95, 0: 5}))
    assert any("auth gate: connection_errors=5" in x for x in out)


def test_health_must_recover_after_the_storm():
    out = lp._strict_failures(_ramp(), _authed(), _gate(health=503))
    assert any("health after storm http=503" in x for x in out)


def test_multiple_violations_are_reported_together():
    out = lp._strict_failures(_ramp({500: 5}), _authed(registered=False),
                              _gate({200: 1}, health=500))
    assert len(out) == 4


def test_a_pressure_run_has_a_citable_ci_gate():
    """The strict verdict must be reachable by CI, not only by reading a chat log.

    The workflow must never start or stop the reader's containers (ci.yml's
    nightly owns that lifecycle), and a stack that is down must be named SKIPPED
    rather than quietly reported as a green pressure run.
    """
    workflow = (REPO / ".github" / "workflows" / "pressure-probe.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch" in workflow
    assert "scripts/load_probe.py" in workflow
    assert "--strict" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "shell: pwsh" not in workflow
    assert "docker compose down" not in workflow
    assert "docker compose up" not in workflow
    assert "SKIPPED" in workflow
    # The report must come from the same file the gate reads.
    assert "pressure-probe.log" in workflow
