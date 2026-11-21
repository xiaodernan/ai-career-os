"""The admin surface has one honest owner; no fake-data stub rides alongside it.

The consolidated WIP batch once shipped `app/features/admin.py`: a router that was
never mounted, endpoints returning `{"total_runs": 0}` and a fabricated
`2026-01-01` timestamp, and a docstring promising "aggregate statistics" it never
computed. It was imported but unmounted, unreachable and untrue — a quiet failure
in the exact place the reader trusts for the install's own numbers.

The real admin feature is the Java `/api/v1/admin/*` controllers (real DB rows,
password "123" at the browser) plus `counsel.py` (the LLM analyst, Epic 320/342).
This gate keeps a fake-data stub from reappearing in the ai-service feature set.
"""

from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
FEATURES = APP / "features"


def test_no_fake_data_admin_stub_in_features():
    stub = FEATURES / "admin.py"
    assert not stub.exists(), (
        "app/features/admin.py is a fake-data stub (never-mounted router, "
        "'2026-01-01' timestamp, hardcoded zeroes). The admin surface is owned by "
        "the Java /api/v1/admin controllers + counsel.py; do not reintroduce a stub."
    )


def test_no_hardcoded_placeholder_timestamp_in_shipped_features():
    """A fabricated fixed timestamp is the fingerprint of demo data. No feature
    that ships to the API may carry one as a value it returns to a caller."""
    offenders: list[str] = []
    for path in FEATURES.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if '"2026-01-01T00:00:00Z"' in text or "'2026-01-01T00:00:00Z'" in text:
            offenders.append(path.name)
    assert offenders == [], f"fake fixed timestamps in shipped features: {offenders}"


def test_features_imports_do_not_reference_a_dead_admin_module():
    api = (APP / "api" / "features.py").read_text(encoding="utf-8")
    assert "import admin" not in api and "admin_mod" not in api, (
        "features.py still imports the removed fake-data admin stub"
    )
