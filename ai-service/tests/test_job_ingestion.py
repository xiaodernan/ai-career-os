"""Tests for the Epic 14 job-ingestion engine (offline, deterministic).

Distinct from ``test_ingestion.py`` (which covers the document pipeline's
clean/chunk/parsers); this file covers the *job* connector engine in
``app/features/ingestion.py``.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.features import ingestion as I

NOW = datetime(2026, 10, 15, tzinfo=timezone.utc)

RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item>
    <title>Senior Backend Engineer</title>
    <link>https://jobs.example.com/1</link>
    <description>Java, Kubernetes, Postgres</description>
    <pubDate>2026-10-01T09:00:00Z</pubDate>
  </item>
  <item>
    <title>Data Analyst</title>
    <link>https://jobs.example.com/2</link>
    <description>SQL and dashboards</description>
  </item>
</channel></rss>"""

ATOM = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Platform Engineer</title>
    <link href="https://jobs.example.com/atom/1"/>
    <summary>Go, Terraform</summary>
    <updated>2026-10-05T00:00:00Z</updated>
  </entry>
</feed>"""


# ---------------- 14.1 normalize ----------------


def test_normalize_maps_and_defaults():
    out = I.normalize_posting({"title": "  Backend  Engineer ", "company_name": "Acme",
                               "location": "Shanghai"}, source="rss")
    assert out["title"] == "Backend Engineer"
    assert out["company"] == "Acme"          # company_name alias honoured
    assert out["remote_type"] == "onsite"    # default
    assert out["employment_type"] == "full_time"
    assert out["salary_currency"] == "CNY"
    assert out["source"] == "rss"


def test_normalize_coerces_salary_and_skills():
    out = I.normalize_posting({"title": "X", "salary_min": "25,000", "salary_max": 40000,
                               "skills": "Java, Kubernetes、Go", "salary_currency": "usd"})
    assert out["salary_min"] == 25000
    assert out["salary_max"] == 40000
    assert out["skills"] == ["Java", "Kubernetes", "Go"]
    assert out["salary_currency"] == "USD"


def test_normalize_missing_title_is_empty_not_error():
    out = I.normalize_posting({}, source="paste")
    assert out["title"] == ""
    assert out["source"] == "paste"


# ---------------- 14.3 fingerprint / dedupe ----------------


def test_fingerprint_normalizes_case_and_punctuation():
    a = {"company": "Acme, Inc.", "title": "Backend Engineer!", "location": "Shanghai"}
    b = {"company": "acme inc", "title": "backend engineer", "location": "shanghai"}
    assert I.posting_fingerprint(a) == I.posting_fingerprint(b)


def test_fingerprint_keeps_location_distinct():
    a = {"company": "Acme", "title": "Engineer", "location": "Shanghai"}
    b = {"company": "Acme", "title": "Engineer", "location": "Beijing"}
    assert I.posting_fingerprint(a) != I.posting_fingerprint(b)


def test_dedupe_keeps_newest_survivor():
    old = {"id": "old", "company": "Acme", "title": "Backend Engineer",
           "location": "Shanghai", "posted_at": "2026-09-01"}
    new = {"id": "new", "company": "Acme", "title": "Backend Engineer",
           "location": "Shanghai", "posted_at": "2026-10-01"}
    res = I.dedupe_postings([old, new])
    assert res["uniqueCount"] == 1 and res["duplicateCount"] == 1
    assert res["unique"][0]["id"] == "new"
    assert res["duplicates"][0]["duplicateOf"] == "new"


def test_dedupe_breaks_ties_by_completeness():
    bare = {"id": "bare", "company": "Acme", "title": "Engineer", "location": "SH"}
    rich = {"id": "rich", "company": "Acme", "title": "Engineer", "location": "SH",
            "description": "lots", "salary_min": 100, "skills": ["Go"],
            "external_url": "u"}
    res = I.dedupe_postings([bare, rich])
    assert res["unique"][0]["id"] == "rich"


def test_dedupe_keeps_unkeyed_distinct():
    res = I.dedupe_postings([{}, {"title": ""}])
    assert res["uniqueCount"] == 2 and res["duplicateCount"] == 0


def test_dedupe_empty():
    res = I.dedupe_postings([])
    assert res == {"unique": [], "duplicates": [], "inputCount": 0,
                   "uniqueCount": 0, "duplicateCount": 0}


def test_dedupe_deterministic():
    items = [{"id": "a", "company": "C", "title": "T", "location": "L"},
             {"id": "b", "company": "C", "title": "T", "location": "L"}]
    first = I.dedupe_postings(items)["unique"][0]["id"]
    second = I.dedupe_postings(items)["unique"][0]["id"]
    assert first == second


# ---------------- 14.3 freshness ----------------


def test_freshness_partitions():
    apps = [
        {"id": "fresh", "posted_at": (NOW - timedelta(days=3)).isoformat()},
        {"id": "expired", "posted_at": (NOW - timedelta(days=90)).isoformat()},
        {"id": "stale", "posted_at": (NOW - timedelta(days=10)).isoformat(),
         "last_seen": (NOW - timedelta(days=45)).isoformat()},
        {"id": "undated"},
    ]
    out = I.freshness_sweep(apps, now=NOW, max_age_days=60, stale_seen_days=30)
    assert [x["id"] for x in out["fresh"]] == ["fresh"]
    assert [x["id"] for x in out["expired"]] == ["expired"]
    assert [x["id"] for x in out["stale"]] == ["stale"]
    assert [x["id"] for x in out["undated"]] == ["undated"]
    assert out["counts"] == {"fresh": 1, "stale": 1, "expired": 1, "undated": 1}


def test_freshness_no_last_seen_never_stale():
    apps = [{"id": "x", "posted_at": (NOW - timedelta(days=10)).isoformat()}]
    out = I.freshness_sweep(apps, now=NOW, stale_seen_days=1)
    assert out["counts"]["stale"] == 0 and out["counts"]["fresh"] == 1


# ---------------- 14.2 feed parsing ----------------


def test_parse_rss():
    items = I.parse_feed(RSS)
    assert len(items) == 2
    assert items[0]["title"] == "Senior Backend Engineer"
    assert items[0]["link"] == "https://jobs.example.com/1"
    assert items[0]["pubDate"] == "2026-10-01T09:00:00Z"


def test_parse_atom():
    items = I.parse_feed(ATOM, source="atom")
    assert len(items) == 1
    assert items[0]["title"] == "Platform Engineer"
    assert items[0]["link"] == "https://jobs.example.com/atom/1"  # href attribute
    assert items[0]["source"] == "atom"


def test_parse_feed_malformed_raises():
    with pytest.raises(ValueError):
        I.parse_feed("<rss><channel><item></rss>")


def test_parse_feed_size_cap():
    with pytest.raises(ValueError):
        I.parse_feed("x" * (I.MAX_FEED_BYTES + 1))


def test_parse_feed_then_normalize_roundtrip():
    items = I.parse_feed(RSS)
    norm = [I.normalize_posting(i, source="rss") for i in items]
    assert norm[0]["title"] == "Senior Backend Engineer"
    assert norm[0]["external_url"] == "https://jobs.example.com/1"


# ---------------- composition: plan_ingest ----------------


def test_plan_ingest_creates_from_feed_string():
    plan = I.plan_ingest(RSS, source="rss")
    assert plan["counts"]["create"] == 2
    assert plan["counts"]["update"] == 0 and plan["counts"]["close"] == 0
    assert plan["create"][0]["title"] == "Senior Backend Engineer"


def test_plan_ingest_updates_known_by_fingerprint():
    existing = [{"id": "job-1", "company": "Acme", "title": "Backend Engineer",
                 "location": "Shanghai", "posted_at": (NOW - timedelta(days=5)).isoformat()}]
    incoming = [{"title": "Backend Engineer", "company": "Acme", "location": "Shanghai"}]
    plan = I.plan_ingest(incoming, source="rss", existing=existing, now=NOW)
    assert plan["counts"]["create"] == 0 and plan["counts"]["update"] == 1
    assert plan["update"][0]["existingId"] == "job-1"


def test_plan_ingest_closes_expired_absent_row():
    existing = [
        {"id": "old", "company": "Acme", "title": "Old Role", "location": "SH",
         "posted_at": (NOW - timedelta(days=120)).isoformat()},
        {"id": "keep", "company": "Acme", "title": "Live Role", "location": "SH",
         "posted_at": (NOW - timedelta(days=5)).isoformat()},
    ]
    plan = I.plan_ingest([], source="rss", existing=existing, now=NOW, max_age_days=60)
    assert [c["id"] for c in plan["close"]] == ["old"]  # expired + not re-seen
    assert plan["counts"]["create"] == 0


def test_plan_ingest_expired_row_reseen_is_not_closed():
    existing = [{"id": "old", "company": "Acme", "title": "Old Role", "location": "SH",
                 "posted_at": (NOW - timedelta(days=120)).isoformat()}]
    incoming = [{"title": "Old Role", "company": "Acme", "location": "SH",
                 "posted_at": (NOW - timedelta(days=1)).isoformat()}]
    plan = I.plan_ingest(incoming, source="rss", existing=existing, now=NOW)
    assert plan["close"] == []          # re-seen this batch -> refreshed, not closed
    assert plan["counts"]["update"] == 1


def test_plan_ingest_reports_within_batch_duplicates():
    incoming = [
        {"title": "Dup", "company": "C", "location": "L", "posted_at": "2026-10-01"},
        {"title": "dup", "company": "c", "location": "l", "posted_at": "2026-09-01"},
    ]
    plan = I.plan_ingest(incoming, source="rss", now=NOW)
    assert plan["counts"]["create"] == 1 and plan["counts"]["duplicates"] == 1
    # raw postings carry no id, so duplicateOf is None but the shared fingerprint is reported
    assert plan["duplicates"][0]["fingerprint"] == "c|dup|l"


# ---------------- 14.2 board-API JSON parsing ----------------


def test_parse_json_board_array():
    items = I.parse_json_board('[{"title": "Backend", "company": "Acme"}]')
    assert len(items) == 1
    assert items[0]["title"] == "Backend"
    assert items[0]["source"] == "board"


def test_parse_json_board_wrapped_object():
    payload = '{"jobs": [{"title": "A"}, {"title": "B"}], "total": 2}'
    items = I.parse_json_board(payload, source="greenhouse")
    assert [i["title"] for i in items] == ["A", "B"]
    assert items[0]["source"] == "greenhouse"


def test_parse_json_board_accepts_data_key():
    items = I.parse_json_board('{"data": [{"title": "C"}]}')
    assert items[0]["title"] == "C"


def test_parse_json_board_invalid_json_raises():
    with pytest.raises(ValueError):
        I.parse_json_board("{not json")


def test_parse_json_board_no_array_raises():
    with pytest.raises(ValueError):
        I.parse_json_board('{"total": 0}')


def test_parse_json_board_non_array_raises():
    with pytest.raises(ValueError):
        I.parse_json_board("42")


def test_parse_json_board_size_cap():
    with pytest.raises(ValueError):
        I.parse_json_board("x" * (I.MAX_FEED_BYTES + 1))


def test_parse_json_board_scalar_items_wrapped():
    items = I.parse_json_board('["Just a title"]')
    assert items[0]["title"] == "Just a title"


def test_plan_ingest_is_idempotent_across_a_reingest():
    """The same batch ingested twice must not create twice -- the claim plan_ingest makes."""
    batch = [
        {"id": "j1", "title": "Backend", "company": "Acme", "location": "SH",
         "posted_at": (NOW - timedelta(days=2)).isoformat()},
        {"id": "j2", "title": "Data", "company": "Beta", "location": "BJ",
         "posted_at": (NOW - timedelta(days=2)).isoformat()},
    ]
    first = I.plan_ingest(batch, source="board", now=NOW)
    assert first["counts"]["create"] == 2

    # the created rows become the corpus; re-ingesting the same batch creates nothing
    corpus = [{"id": f"new-{i}", **p} for i, p in enumerate(first["create"])]
    second = I.plan_ingest(batch, source="board", existing=corpus, now=NOW)
    assert second["counts"]["create"] == 0
    assert second["counts"]["update"] == 2
    assert second["close"] == []


# ---------------- 19.8 real board payloads ----------------

# The shapes the two public board APIs answer with, as the docs show them: Greenhouse
# wraps its rows under `jobs`, escapes the HTML `content` once, sends the location as an
# object, and dates a row with `first_published` beside a later `updated_at`. Lever sends
# a bare array whose title is `text`, whose HTML `description` has a plain twin, whose
# location and commitment sit under `categories`, and whose `createdAt` is epoch
# milliseconds.

GREENHOUSE = """{
  "jobs": [
    {
      "id": 4001,
      "title": "Senior Backend Engineer",
      "updated_at": "2026-10-10T12:00:00-04:00",
      "first_published": "2026-09-01T09:30:00-04:00",
      "location": {"name": "Berlin, Germany"},
      "absolute_url": "https://boards.greenhouse.io/acme/jobs/4001",
      "content": "&lt;p&gt;Build &amp; ship the API.&lt;/p&gt;&lt;p&gt;Postgres.&lt;/p&gt;",
      "metadata": []
    }
  ],
  "meta": {"total": 1}
}"""

LEVER = """[
  {
    "id": "abc-123",
    "text": "Staff Frontend Engineer",
    "hostedUrl": "https://jobs.lever.co/acme/abc-123",
    "createdAt": 1759349400000,
    "description": "<div>React and TypeScript</div>",
    "descriptionPlain": "React and TypeScript",
    "categories": {"location": "Remote - US", "team": "Engineering", "commitment": "Full-time"},
    "workplaceType": "remote"
  },
  {
    "id": "def-456",
    "text": "Data Contractor",
    "hostedUrl": "https://jobs.lever.co/acme/def-456",
    "createdAt": 1759349400000,
    "descriptionPlain": "SQL and dashboards",
    "categories": {"location": "Shanghai", "commitment": "Contract"},
    "workplaceType": "on-site"
  },
  {
    "id": "ghi-789",
    "text": "Part-time Analyst",
    "hostedUrl": "https://jobs.lever.co/acme/ghi-789",
    "categories": {"location": "Paris", "commitment": "Part-time"},
    "workplaceType": "hybrid"
  }
]"""


def test_a_greenhouse_board_maps_onto_the_canonical_fields():
    plan = I.plan_ingest(GREENHOUSE, source="greenhouse", default_company="Acme")

    assert plan["counts"]["create"] == 1
    row = plan["create"][0]
    assert row["title"] == "Senior Backend Engineer"
    # the row never names a company; the board's own name is the only truthful source
    assert row["company"] == "Acme"
    assert row["location"] == "Berlin, Germany"           # {"name": ...} location
    assert row["external_url"] == "https://boards.greenhouse.io/acme/jobs/4001"
    assert row["posted_at"] == "2026-09-01T09:30:00-04:00"  # first_published, not updated_at
    assert "Build & ship" in row["description"]           # escaped HTML decoded once
    assert "<" not in row["description"] and "&lt;" not in row["description"]
    assert row["source"] == "greenhouse"
    assert row["remote_type"] == "onsite"                 # the payload names none
    assert row["employment_type"] == "full_time"


def test_a_row_that_names_its_own_company_wins_over_the_boards_name():
    plan = I.plan_ingest([{"title": "Backend", "company_name": "Acme Labs"}],
                         source="greenhouse", default_company="Acme")
    assert plan["create"][0]["company"] == "Acme Labs"


def test_a_lever_board_maps_its_own_names_onto_the_canonical_fields():
    plan = I.plan_ingest(LEVER, source="lever", default_company="Acme")

    assert plan["counts"]["create"] == 3
    rows = {row["title"]: row for row in plan["create"]}

    staff = rows["Staff Frontend Engineer"]
    assert staff["company"] == "Acme"
    assert staff["location"] == "Remote - US"             # categories.location
    assert staff["external_url"] == "https://jobs.lever.co/acme/abc-123"
    assert staff["posted_at"] == "2025-10-01T20:10:00+00:00"  # createdAt, epoch millis
    assert staff["description"] == "React and TypeScript"  # descriptionPlain over HTML
    assert staff["remote_type"] == "remote"               # workplaceType
    assert staff["employment_type"] == "full_time"        # categories.commitment

    contractor = rows["Data Contractor"]
    assert contractor["employment_type"] == "contract"
    assert contractor["remote_type"] == "onsite"

    analyst = rows["Part-time Analyst"]
    # the product has no word for part-time, so the row keeps the canonical default
    # rather than being given a word the payload did not use
    assert analyst["employment_type"] == "full_time"
    assert analyst["remote_type"] == "hybrid"
    assert analyst["posted_at"] is None                   # no date in the payload


def test_an_epoch_stamp_in_seconds_is_read_as_seconds_not_as_1970():
    plan = I.plan_ingest([{"title": "Backend", "createdAt": 1759349400}], source="lever")
    assert plan["create"][0]["posted_at"] == "2025-10-01T20:10:00+00:00"


def test_a_board_stamp_that_is_not_a_number_is_no_date():
    plan = I.plan_ingest([{"title": "Backend", "createdAt": "yesterday"}], source="lever")
    assert plan["create"][0]["posted_at"] is None


def test_the_parsed_and_raw_forms_of_one_payload_plan_identically():
    """`postings` and `feed` are two doors to one plan, not two mappings."""
    parsed = I.plan_ingest(I.parse_json_board(LEVER, source="lever"),
                           source="lever", default_company="Acme")
    raw = I.plan_ingest(LEVER, source="lever", default_company="Acme")
    assert parsed["create"] == raw["create"]
