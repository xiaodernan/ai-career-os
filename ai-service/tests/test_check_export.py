"""Tests for the portable-export check.

The check exists because the export's queries are monkeypatched everywhere
offline; these tests hold the check's own contract the same way -- the export
half is stubbed, the database boundary is stubbed (the check runs on CI with
no postgres at all, and a real init_db there answers OSError before the check
says anything -- that exact red shipped once in the corpus tests).
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import pytest

from app.ops import check_export as mod

_UID = "3403c9e0-b866-4be0-87b6-c2b499bda715"


def _bundle(data: dict) -> dict:
    from app.features import export as ex

    return {
        "schema_version": "1.2.0",
        "generator": "careeros-export/test",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "user": {"id": _UID},
        "manifest": {
            "schema_version": "1.2.0",
            "generator": "careeros-export/test",
            "counts": {},
            "content_hash": ex.content_hash(data),
            "anonymized": False,
        },
        "data": data,
    }


@pytest.fixture()
def offline_db(monkeypatch):
    async def no_pool():
        return None
    async def no_close():
        return None
    monkeypatch.setattr(mod.db, "init_db", no_pool)
    monkeypatch.setattr(mod.db, "close_db", no_close)


def _with_export(monkeypatch, bundle):
    async def fake_export(user_id):
        return bundle
    monkeypatch.setattr(mod.ex, "export_bundle", fake_export)


def test_a_bundle_carrying_timestamps_survives_its_own_canonical_form(
        offline_db, monkeypatch, capsys):
    # The exact shape the nightly first ran this check on: rows with created_at /
    # updated_at. The canonical form spells datetimes with ISO's T; the old proxy
    # compared against json.dumps(default=str), which spells them with a space --
    # every healthy bundle with a timestamp in it failed, and the check had only
    # ever passed on bundles with no rows.
    _with_export(monkeypatch, _bundle({
        "profile": {"id": _UID, "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc)},
    }))
    rc = asyncio.run(mod.main(["check-export", _UID]))
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert len(out["content_hash"]) == 64
    assert out["schema_version"] == "1.2.0"


def test_a_shipper_that_disagrees_with_the_hasher_is_reported(
        offline_db, monkeypatch, capsys):
    # What ships must be the canonical form. A serialize_bundle that re-encodes
    # with a different encoder (here: the old proxy's default=str) ships bytes
    # whose data no longer matches what the manifest hash is over.
    async def fake_export(user_id):
        return _bundle({"profile": {"created_at": datetime(2026, 1, 1, tzinfo=timezone.utc)}})
    monkeypatch.setattr(mod.ex, "export_bundle", fake_export)
    monkeypatch.setattr(
        mod.ex, "serialize_bundle",
        lambda bundle: json.dumps(bundle, default=str))
    rc = asyncio.run(mod.main(["check-export", _UID]))
    assert rc == 1
    assert "does not survive" in capsys.readouterr().err


def test_an_export_that_raises_is_reported_where_it_happened(
        offline_db, monkeypatch, capsys):
    async def broken_export(user_id):
        raise RuntimeError("no such column: jobs.owner_id")
    monkeypatch.setattr(mod.ex, "export_bundle", broken_export)
    rc = asyncio.run(mod.main(["check-export", _UID]))
    assert rc == 1
    err = capsys.readouterr().err
    assert "did not build" in err
    assert "no such column" in err


def test_a_content_hash_that_is_not_a_sha256_is_reported(
        offline_db, monkeypatch, capsys):
    bundle = _bundle({"notes": []})
    bundle["manifest"]["content_hash"] = "abc"
    _with_export(monkeypatch, bundle)
    rc = asyncio.run(mod.main(["check-export", _UID]))
    assert rc == 1
    assert "not a sha256" in capsys.readouterr().err
