"""Tests for the Epic 14 ingest-plan CLI (offline, no database)."""

import json

import pytest

from app.ops import ingest_plan as P

RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item><title>Senior Backend Engineer</title><link>https://x/1</link>
    <description>Java</description><pubDate>2026-10-01T09:00:00Z</pubDate></item>
  <item><title>Data Analyst</title><link>https://x/2</link></item>
</channel></rss>"""

BOARD = json.dumps({"jobs": [
    {"title": "Platform Engineer", "company": "Acme", "location": "SH",
     "posted_at": "2026-10-01"},
]})

NOW = "2026-10-17T00:00:00+00:00"


# ---------------- format detection / parsing ----------------


def test_detect_format():
    assert P.detect_format(RSS) == "rss"
    assert P.detect_format(BOARD) == "board"
    assert P.detect_format("  [{\"title\": \"x\"}]") == "board"


def test_build_plan_rss_creates():
    plan = P.build_plan(RSS)
    assert plan["counts"]["create"] == 2
    assert plan["source"] == "rss"


def test_build_plan_board_creates():
    plan = P.build_plan(BOARD)
    assert plan["counts"]["create"] == 1
    assert plan["create"][0]["title"] == "Platform Engineer"
    assert plan["source"] == "board"


def test_build_plan_forced_format():
    plan = P.build_plan(BOARD, fmt="board")
    assert plan["counts"]["create"] == 1


# ---------------- planning against a corpus ----------------


def test_build_plan_updates_known():
    existing = [{"id": "j1", "title": "Platform Engineer", "company": "Acme",
                 "location": "SH", "posted_at": "2026-10-01"}]
    plan = P.build_plan(BOARD, existing=existing, now=P._parse_now(NOW))
    assert plan["counts"]["create"] == 0 and plan["counts"]["update"] == 1


def test_build_plan_closes_expired_absent():
    existing = [{"id": "old", "title": "Old Role", "company": "Zeta",
                 "location": "BJ", "posted_at": "2020-01-01"}]
    plan = P.build_plan(BOARD, existing=existing, now=P._parse_now(NOW),
                        max_age_days=60)
    assert [c["id"] for c in plan["close"]] == ["old"]


def test_build_plan_pins_the_clock():
    # with a pinned now, an old posting is expired; without it the result depends on today
    plan = P.build_plan(BOARD, existing=[
        {"id": "old", "title": "Old", "company": "Z", "location": "L",
         "posted_at": "2020-01-01"}], now=P._parse_now(NOW))
    assert plan["counts"]["close"] == 1


def test_parse_now_rejects_garbage():
    with pytest.raises(ValueError):
        P._parse_now("not-a-date")


# ---------------- CLI ----------------


def test_main_rss(tmp_path, capsys):
    feed = tmp_path / "feed.xml"
    feed.write_text(RSS, encoding="utf-8")
    assert P.main([str(feed), "--now", NOW]) == 0
    out = capsys.readouterr().out
    assert "2 create" in out
    plan = json.loads(out.split("ingest-plan:")[0])
    assert plan["counts"]["create"] == 2


def test_main_board_with_existing(tmp_path, capsys):
    feed = tmp_path / "feed.json"
    feed.write_text(BOARD, encoding="utf-8")
    corpus = tmp_path / "corpus.json"
    corpus.write_text(json.dumps([
        {"id": "j1", "title": "Platform Engineer", "company": "Acme", "location": "SH",
         "posted_at": "2026-10-01"}]), encoding="utf-8")
    assert P.main([str(feed), "--existing", str(corpus), "--now", NOW]) == 0
    assert "1 update" in capsys.readouterr().out


def test_main_missing_file_exits_2(tmp_path, capsys):
    assert P.main([str(tmp_path / "nope.xml")]) == 2
    assert "ingest-plan:" in capsys.readouterr().err


def test_main_bad_feed_exits_2(tmp_path, capsys):
    feed = tmp_path / "bad.xml"
    feed.write_text("<rss><channel><item></rss>", encoding="utf-8")
    assert P.main([str(feed)]) == 2
    assert "ingest-plan:" in capsys.readouterr().err


def test_main_bad_now_exits_2(tmp_path, capsys):
    feed = tmp_path / "feed.xml"
    feed.write_text(RSS, encoding="utf-8")
    assert P.main([str(feed), "--now", "yesterday"]) == 2
    assert "ISO datetime" in capsys.readouterr().err
