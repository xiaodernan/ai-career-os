"""Tests for the Epic 13.2 restore-plan CLI (offline, no database)."""

import json

import pytest

from app.features.export import build_bundle, write_bundle
from app.ops import restore_plan as R


def _bundle(user="u1", resumes=1):
    raw = {
        "profile": {"id": "p1", "headline": "Backend Engineer"},
        # The restore writes a resume from its title and its text; a fixture
        # without a title is a row the apply would leave alone, and the plan
        # does not promise writes the apply does not make.
        "resumes": [{"id": f"r{i}", "resume_title": f"Resume {i}",
                     "plaintext": "resume body"} for i in range(resumes)],
        "knowledge": [],
        "job_descriptions": [],
        "interviews": [],
        "memories": [],
    }
    return build_bundle(user, raw)


# ---------------- pure planning ----------------


def test_plan_for_bundle_all_creates_against_nothing():
    plan = R.plan_for_bundle(_bundle())
    assert plan["op_counts"]["create"] == 2      # profile + one resume
    assert plan["op_counts"]["update"] == 0
    assert plan["op_counts"]["delete"] == 0


def test_plan_for_bundle_reimport_is_all_skips():
    b = _bundle()
    plan = R.plan_for_bundle(b, existing=b)
    assert plan["op_counts"]["create"] == 0
    assert plan["op_counts"]["update"] == 0
    assert plan["op_counts"]["delete"] == 0
    assert plan["op_counts"]["skip"] == 2
    assert all(op["op"] == "skip" for ops in plan["sections"].values() for op in ops)


def test_plan_for_bundle_rejects_invalid():
    with pytest.raises(ValueError):
        R.plan_for_bundle({"schema_version": "1"})


def test_plan_carries_the_source_hash():
    b = _bundle()
    plan = R.plan_for_bundle(b)
    assert plan["source_content_hash"] == b["manifest"]["content_hash"]


# ---------------- CLI ----------------


def test_main_writes_a_plan(tmp_path, capsys):
    path = tmp_path / "backup.json"
    write_bundle(_bundle(resumes=2), str(path))
    assert R.main([str(path)]) == 0
    out = capsys.readouterr().out
    assert "restore-plan:" in out
    # the JSON body is printed before the summary line
    body = out.split("restore-plan:")[0]
    plan = json.loads(body)
    assert plan["op_counts"]["create"] == 3      # profile + two resumes


def test_main_diffs_against_existing(tmp_path, capsys):
    path = tmp_path / "backup.json"
    write_bundle(_bundle(), str(path))
    assert R.main([str(path), "--existing", str(path)]) == 0
    # A file diffed against itself has nothing to write, and the summary has
    # to say so: "update 2" was the old plan's answer for a no-op restore.
    assert "skip 2" in capsys.readouterr().out


def test_main_missing_file_exits_2(tmp_path, capsys):
    assert R.main([str(tmp_path / "nope.json")]) == 2
    assert "restore-plan:" in capsys.readouterr().err


def test_main_bad_json_exits_2(tmp_path, capsys):
    path = tmp_path / "bad.json"
    path.write_text("not json", encoding="utf-8")
    assert R.main([str(path)]) == 2
    assert "restore-plan:" in capsys.readouterr().err


def test_main_invalid_bundle_exits_2(tmp_path, capsys):
    path = tmp_path / "thin.json"
    path.write_text(json.dumps({"schema_version": "1"}), encoding="utf-8")
    assert R.main([str(path)]) == 2
    assert "invalid bundle" in capsys.readouterr().err


def test_plan_for_bundle_rejects_none():
    # `null` is valid JSON, so a backup file can decode to None; it must be a clean
    # ValueError (the CLI maps it to exit 2), never a TypeError from `key not in None`.
    with pytest.raises(ValueError):
        R.plan_for_bundle(None)


def test_main_null_bundle_exits_2(tmp_path, capsys):
    path = tmp_path / "null.json"
    path.write_text("null", encoding="utf-8")
    assert R.main([str(path)]) == 2
    assert "not a JSON object" in capsys.readouterr().err
