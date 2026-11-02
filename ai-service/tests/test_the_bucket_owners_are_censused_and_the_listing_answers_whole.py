"""The bucket's owners are a census, and the port that lists it answers whole or not at all.

A reclaim that deletes bytes no row names is the most permanent operation in this project: nothing
later can undo it, because the record that would have described the file is the file. So the sweep
that will do it (48.2) has to subtract, from every key the store shows, every key any row could hold
-- and an unlisted key owner is a deletion bug waiting for the day a table gains a column. Today the
owners are exactly two writers (`FileIngestService`'s two upload paths and `ResumeService`'s parse),
two removers (24.2's `AccountErasureService` and 44.2's `StoredObjectReclaimer`), two readers, and two
columns (`documents.file_key`, `resumes.source_file_key`). Each axis here is walked from what a call
site or a declaration looks like rather than from a file name, so a third writer, a renamed remover or
a new key column reddens a case instead of becoming invisible to a sweep.

The other half is the listing itself (48.1). `StorageService.list()` promises the whole bucket, and a
store that cannot deliver every page throws rather than returning what it reached -- because a short
list is not a smaller answer, it is an accusation against every object it left out. So the port's
surface, both implementations of `list()`, and the fact that nothing in production may call it until
48.2 adds the sweep, are pinned here too.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAIN_JAVA = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros"
TEST_JAVA = ROOT / "backend" / "src" / "test" / "java" / "com" / "careeros"
MIGRATIONS = ROOT / "backend" / "src" / "main" / "resources" / "db" / "migration"

PORT = MAIN_JAVA / "storage" / "StorageService.java"
MINIO = MAIN_JAVA / "storage" / "MinioStorageService.java"
DOUBLE = TEST_JAVA / "support" / "InMemoryStorageConfig.java"

# The port's whole surface. A seventh operation means the call-site censuses below describe less than
# the port offers, and an operation nothing calls is the configured-knob defect in a new costume.
PORT_OPERATIONS = {"put", "getPresignedUrl", "delete", "getBytes", "list", "available"}

# Every class that can put bytes into the bucket, and how many call sites it owns. Two composers mint
# the keys (`test_file_key_composers.py` holds that census); these are the places a key reaches store.
WRITERS = {"FileIngestService.java": 2, "ResumeService.java": 1}

# Every class that can take bytes out. Erasure deletes directly because the account's rows are going
# anyway; the reclaimer deletes once no live row names the key. A third way to remove an object is a
# third thing a sweep has to be reasoned against before it trusts its own listing.
REMOVERS = {"AccountErasureService.java": 1, "StoredObjectReclaimer.java": 1}

# Who may read bytes back out: a reader is a route that proves a key still resolves.
READERS = {"InternalFileController.java": 1, "ResumeService.java": 1}

# Columns that can hold a key, and the entities that map them. A column no entity maps is a column no
# repository can be censused against, so both halves are pinned -- the SQL declaration and the field.
KEY_COLUMNS = {("documents", "file_key"), ("resumes", "source_file_key")}
KEY_ENTITIES = {"Document.java", "Resume.java"}

# Production classes that read the whole bucket. Empty is the honest current state: `list()` shipped
# with 48.1 and its first caller is 48.2's sweep, which has to land in this set in its own commit --
# a sweep that appears in the code but not in a census is the unlisted owner this file exists to catch.
LISTERS: set[str] = set()

LISTING = "List<StoredObject> list()"


def read(path: Path) -> str:
    """Shipped text with LF endings; this host checks the tree out with CRLF."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def call_sites(operation: str, root: Path) -> dict[str, int]:
    """How many times each class under `root` calls `storage.<operation>(...)`.

    Matched on the receiver the services use, so a class that renames its field to `store` shows up as
    an absence -- which the control case below refutes instead of passing on.
    """
    pattern = re.compile(r"storage\." + re.escape(operation) + r"\(")
    out: dict[str, int] = {}
    for path in sorted(root.rglob("*.java")):
        hits = len(pattern.findall(read(path)))
        if hits:
            out[path.name] = hits
    return out


def balanced_body(source: str, open_brace: int) -> str:
    """The text between a `{` and its matching `}`, with braces in strings and comments skipped."""
    depth, index, length = 0, open_brace, len(source)
    while index < length:
        char = source[index]
        if source.startswith("//", index):
            index = source.index("\n", index)
            continue
        if source.startswith("/*", index):
            index = source.index("*/", index) + 2
            continue
        if char in "\"'":
            quote, index = char, index + 1
            while index < length and source[index] != quote:
                index += 2 if source[index] == "\\" else 1
            index += 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[open_brace + 1:index]
        index += 1
    raise AssertionError(f"the brace at {open_brace} never closes in {source[:80]!r}")


def method_body(path: Path, signature: str) -> str:
    """One method's own body, found by its declaration and closed by brace counting.

    Reading to the next blank line, or to the next `;`, would report an accumulator declaration as the
    whole of a `list()` -- and a partial read of the listing is exactly the failure this gate refuses.
    """
    source = read(path)
    start = source.find(signature)
    if start < 0:
        raise AssertionError(f"{path.name} no longer declares {signature!r}; this case reads that "
                             "method's own body, so a rename or a move belongs in this file too")
    return balanced_body(source, source.index("{", source.index(")", start)))


def declared_operations() -> set[str]:
    """Every operation the port interface declares: the name of each `(...);` in its body."""
    source = read(PORT)
    interface = balanced_body(source, source.index("{", source.index("interface StorageService")))
    return set(re.findall(r"\b(\w+)\s*\([^)]*\)\s*;", interface))


def key_columns(sql: str) -> set[tuple[str, str]]:
    """The (table, column) pairs in this SQL that can hold a stored object's key.

    Both ways a column arrives are read: a `CREATE TABLE` line and an `ALTER TABLE ... ADD COLUMN`.
    The second is what a later migration would use, so a census that only parsed the first would age
    out of usefulness without ever going red.
    """
    out: set[tuple[str, str]] = set()
    for block in re.finditer(r"CREATE TABLE\s+(\w+)[^;]*?\((.*?)\n\s*\);", sql, re.S | re.I):
        for line in block.group(2).splitlines():
            column = re.match(r"\s*(\w*file_key\w*)\s+\w", line)
            if column:
                out.add((block.group(1), column.group(1)))
    for added in re.finditer(
            r"ALTER TABLE\s+(\w+)\s+ADD\s+(?:COLUMN\s+)?(?:IF\s+NOT\s+EXISTS\s+)?(\w*file_key\w*)",
            sql, re.I):
        out.add((added.group(1), added.group(2)))
    return out


# ------------------------------------------------------------------------ the port's surface


def test_the_port_offers_six_operations_and_one_of_them_lists_the_whole_bucket():
    operations = declared_operations()
    assert operations == PORT_OPERATIONS, (
        f"the storage port declares {sorted(operations)}, not the six operations every call-site "
        f"census below was written against")
    assert re.search(r"\bList<StoredObject> list\(\);", read(PORT)), (
        "the port no longer answers a listing as a list of StoredObject, so a sweep would be trusting "
        "a different contract than the one pinned here")


def test_the_listing_promises_the_whole_bucket_and_refuses_to_answer_less():
    """The contract sentence and the code shape behind it: one try, one return, no empty fallback.

    A listing that swallowed a page failure and returned the earlier pages would pass every test that
    counts what came back, because the number it compares against is the one the listing supplied.
    """
    port = read(PORT)
    assert "whole-or-nothing" in port, (
        "the port stopped stating its own contract: the implementations below are checked against a "
        "promise this file can still read")
    assert "short would let a sweep" in port, (
        "the reason a partial listing is a defect rather than a smaller answer is gone from the "
        "javadoc, and the next reader of the adapter has nothing to keep the shape honest")

    body = method_body(MINIO, LISTING)
    assert body.lstrip().startswith("try"), (
        "the MinIO listing no longer wraps its whole walk in one try, so a page that fails after the "
        "first can return the pages it reached")
    assert body.count("client.listObjects(") == 1, (
        f"the adapter asks the store for pages {body.count('client.listObjects(')} times; this case "
        "proves one walk is covered by the refusal, and two walks is a different shape")
    assert body.index("client.listObjects(") < body.index("return"), (
        "the adapter returns before it ever reaches the store, which is a listing that cannot fail")
    assert "catch (Exception e)" in body and "ApiErrorCode.STORAGE_READ_FAILED" in body, (
        "a failed listing no longer throws the typed storage refusal, so a sweep that catches "
        "ApiException would be catching nothing")
    assert "List.of()" not in body and "emptyList" not in body, (
        "the listing grew an empty-answer fallback, which turns a store that refused into a bucket "
        "that looks empty -- the one reading a reclaim must never take")


def test_both_implementations_date_every_object_and_neither_answers_a_null_stamp():
    """`lastModified` is the number a window is measured against, so an undated object reads as young.

    A stamp that defaults to zero makes every object older than every window; a null makes the sweep
    either crash or skip, and a skip that is not counted is a bucket that never drains.
    """
    for path in (MINIO, DOUBLE):
        body = method_body(path, LISTING)
        assert "OffsetDateTime.now()" in body, (
            f"{path.name}'s listing no longer falls back to the moment it read the object, so an "
            "undated object can be dated by nothing -- or by the epoch")
    assert "storedAt" in method_body(DOUBLE, LISTING), (
        "the double's listing stopped reading the map a window test sets, so 48.2 would be testing "
        "a timestamp its own listing ignores")


def test_the_double_lists_everything_it_holds_including_what_a_test_seeded_behind_it():
    """Integration tests write `store` directly, so the listing has to cover keys it never saw put().

    A double that listed only what its own `put` recorded would show a sweep an empty bucket and let
    the test conclude that the sweep correctly reclaimed nothing -- the cleanest proof of nothing.
    """
    body = method_body(DOUBLE, LISTING)
    assert "store.entrySet()" in body, (
        "the double now builds its listing from something other than the byte map it stores")
    assert ".filter(" not in body, (
        "the double filters its listing, so it no longer answers the whole store it models")


# ------------------------------------------------------------------------ the owners, censused


def test_exactly_the_two_known_classes_can_write_the_bucket():
    found = call_sites("put", MAIN_JAVA)
    assert found == WRITERS, (
        f"the classes that put bytes into the bucket moved: {found}. A new writer stores bytes under a "
        "key no sweep was told to expect, and the reclaim's subtraction is only as good as the census "
        "of who can point a row at an object")


def test_exactly_the_two_known_classes_can_delete_from_the_bucket():
    found = call_sites("delete", MAIN_JAVA)
    assert found == REMOVERS, (
        f"the classes that take bytes out of the bucket moved: {found}. Each is a way an object can go "
        "without a row being retired -- the half of the story 44.2 tells -- and a third has to be "
        "reasoned about before 48.2's sweep trusts what the store shows it")


def test_exactly_the_two_known_classes_can_read_bytes_back_out():
    found = call_sites("getBytes", MAIN_JAVA)
    assert found == READERS, (
        f"the classes that read a stored object moved: {found}. A reader is a route that proves a key "
        "still resolves, so the sweep's claim that no row names an object has to survive it")


def test_the_call_site_scanner_is_proved_on_operations_that_exist_and_one_that_does_not():
    """Without a control, the three censuses above would pass on a receiver rename.

    That is the drift they are watching for, so the scanner's reach is pinned against the same tree.
    """
    assert sum(call_sites("put", MAIN_JAVA).values()) == 3, (
        "the scanner lost a write site, so an empty census below could mean an empty scan")
    assert sum(call_sites("delete", MAIN_JAVA).values()) == 2, "same, for the removers"
    assert call_sites("touch", MAIN_JAVA) == {}, (
        "the scanner matched an operation the port does not declare, so its emptiness proves nothing")


def test_no_production_class_lists_the_bucket_until_the_sweep_that_would_is_named_here():
    found = set(call_sites("list", MAIN_JAVA))
    assert found == LISTERS, (
        f"these classes now read the whole bucket: {sorted(found)}. 48.2 lands the sweep that does, "
        "and its class belongs in LISTERS in the same change -- a sweep no census names is the "
        "unlisted owner this file was written to catch")


def test_two_and_only_two_columns_can_name_a_stored_object_and_two_entities_hold_them():
    sql = "".join(read(path) for path in sorted(MIGRATIONS.glob("*.sql")))
    columns = key_columns(sql)
    assert columns == KEY_COLUMNS, (
        f"{sorted(columns)} can hold a file key. A third column is a third set of bytes a row can "
        "point at, and a sweep that subtracts only the columns it knows reclaims what the new one "
        "names")

    holders = {path.name for path in MAIN_JAVA.rglob("*.java")
               if re.search(r"private String \w*[fF]ileKey;", read(path))}
    assert holders == KEY_ENTITIES, (
        f"these entities map a key field: {sorted(holders)}. The Java side has to move with the SQL "
        "side, or this census calls a column unreadable while a repository asks its rows by name")


def test_the_column_reader_fires_on_declarations_it_has_to_see_and_stops_at_the_ones_it_must():
    """A scan over migrations is worth nothing until it has fired on a real statement.

    Both shapes a key column can arrive in are fed to the reader, plus the near-miss it must not
    invent: a column whose name merely mentions a file, and a table whose key line has no type.
    """
    created = key_columns("CREATE TABLE letters (\n  id uuid,\n  reply_file_key text,\n);")
    assert created == {("letters", "reply_file_key")}, (
        f"the reader cannot see a key column in a CREATE TABLE: {sorted(created)}")
    altered = key_columns("ALTER TABLE letters ADD COLUMN IF NOT EXISTS archive_file_key text;")
    assert altered == {("letters", "archive_file_key")}, (
        f"the reader cannot see a column a later migration adds: {sorted(altered)}")
    assert key_columns("CREATE TABLE letters (\n  file_count int,\n  body text,\n);") == set(), (
        "the reader matched a column that holds no key, so its set overstates the bucket's owners")
