"""The prewarm script covers exactly the V36 indexes it claims to cover.

``scripts/prewarm-hot.sql`` exists so a cold deploy does not pay the first
page reads out of random disk I/O: Section A re-run ``ANALYZE`` on the five
hot relations and Section B loads the five V36 composite indexes into shared
buffers with ``pg_prewarm``. The two halves drift by hand as easily as any
copy -- somebody adds ``V37__more_indexes.sql`` and the script still warms
five.

This gate parses the V36 migration for the indexes and tables it creates and
asserts both halves of the script name every one of them. A V37 that adds a
sixth composite is expected to move this gate and the script in the same
change; that is the point.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "backend" / "src" / "main" / "resources" / "db" / "migration" / "V36__search_lookup_indexes.sql"
SCRIPT = ROOT / "scripts" / "prewarm-hot.sql"

INDEX_RE = re.compile(r"CREATE INDEX IF NOT EXISTS (\w+)\s+ON \w+", re.I)
TABLE_RE = re.compile(r"CREATE INDEX IF NOT EXISTS \w+\s+ON (\w+)", re.I)


def _migration():
    text = MIGRATION.read_text(encoding="utf-8")
    indexes = INDEX_RE.findall(text)
    tables = TABLE_RE.findall(text)
    assert indexes, f"no indexes parsed out of {MIGRATION.name} -- the reader narrowed or the migration changed shape"
    assert len(indexes) == len(tables) == len(set(tables))
    return indexes, tables


def test_the_v36_indexes_are_all_prewarmed():
    indexes, _ = _migration()
    script = SCRIPT.read_text(encoding="utf-8")
    missing = [i for i in indexes if f"pg_prewarm('{i}')" not in script]
    assert missing == [], (
        f"prewarm-hot.sql does not warm {missing} -- a cold deploy pays for the "
        "V36 indexes out of disk exactly where Epic 123 promises warm buffers")


def test_the_v36_tables_are_all_analyzed():
    _, tables = _migration()
    script = SCRIPT.read_text(encoding="utf-8")
    missing = [t for t in tables if not re.search(rf"^ANALYZE {t};", script, re.M)]
    assert missing == [], (
        f"prewarm-hot.sql does not ANALYZE {missing} -- the planner keeps the "
        "old histograms for the hottest user-scoped reads")


def test_both_files_exist():
    assert MIGRATION.is_file(), f"missing {MIGRATION}"
    assert SCRIPT.is_file(), f"missing {SCRIPT}"
