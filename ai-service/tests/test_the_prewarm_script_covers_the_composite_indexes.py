"""The prewarm script covers exactly the hot composite indexes it claims to cover.

``scripts/prewarm-hot.sql`` exists so a cold deploy does not pay the first
page reads out of random disk I/O: Section A re-runs ``ANALYZE`` on the hot
relations and Section B loads the composite indexes into shared buffers with
``pg_prewarm``. The two halves drift by hand as easily as any copy -- somebody
lands ``V38__more_indexes.sql`` and the script still warms five.

This gate parses the hot-path migrations for the indexes and tables they
create and asserts both halves of the script name every one of them. A new
composite in a hot-path migration must move this gate and the script in the
same change; that is the point.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION_DIR = ROOT / "backend" / "src" / "main" / "resources" / "db" / "migration"
HOT_MIGRATIONS = (
    "V36__search_lookup_indexes.sql",
    "V37__matches_digest_indexes.sql",
)
SCRIPT = ROOT / "scripts" / "prewarm-hot.sql"

INDEX_RE = re.compile(r"CREATE INDEX IF NOT EXISTS (\w+)\s+ON \w+", re.I)
TABLE_RE = re.compile(r"CREATE INDEX IF NOT EXISTS \w+\s+ON (\w+)", re.I)


def _migration():
    text = "\n".join(
        (MIGRATION_DIR / name).read_text(encoding="utf-8") for name in HOT_MIGRATIONS)
    indexes = INDEX_RE.findall(text)
    tables = TABLE_RE.findall(text)
    assert indexes, "no indexes parsed out of the hot migrations -- the reader narrowed or they changed shape"
    return indexes, tables


def test_every_hot_index_is_prewarmed():
    indexes, _ = _migration()
    script = SCRIPT.read_text(encoding="utf-8")
    missing = [i for i in indexes if f"pg_prewarm('{i}')" not in script]
    assert missing == [], (
        f"prewarm-hot.sql does not warm {missing} -- a cold deploy pays for the "
        "hot composites out of disk exactly where Epics 123/126 promise warm buffers")


def test_every_hot_table_is_analyzed():
    _, tables = _migration()
    script = SCRIPT.read_text(encoding="utf-8")
    missing = [t for t in tables if not re.search(rf"^ANALYZE {t};", script, re.M)]
    assert missing == [], (
        f"prewarm-hot.sql does not ANALYZE {missing} -- the planner keeps the "
        "old histograms for the hottest user-scoped reads")


def test_both_files_exist():
    for name in HOT_MIGRATIONS:
        assert (MIGRATION_DIR / name).is_file(), f"missing {MIGRATION_DIR / name}"
    assert SCRIPT.is_file(), f"missing {SCRIPT}"


def test_the_script_does_not_warm_indexes_that_do_not_exist():
    indexes, _ = _migration()
    script = SCRIPT.read_text(encoding="utf-8")
    warmed = set(re.findall(r"pg_prewarm\('(\w+)'\)", script))
    assert warmed == set(indexes), (
        f"the script and the migrations disagree: {sorted(warmed - set(indexes))} warmed but not created, "
        f"{sorted(set(indexes) - warmed)} created but not warmed")
