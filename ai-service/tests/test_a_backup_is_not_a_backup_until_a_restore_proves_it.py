"""A backup is a file until a restore proves it, and the drill is the proof.

The roadmap's last delivery item asks for nightly backups *plus a restore drill*, which is two
different promises wearing one sentence. The first is easy to satisfy badly: `pg_dump > file`
on a timer produces a directory of files that look exactly like backups, are pruned by nothing,
verified by nobody, and -- the classic -- are stored on the disk they exist to replace. The
second is the one that catches that: a nightly timer that has never been replayed is a cron job
with a hopeful name.

So this gate reads the two scripts rather than running them (no Docker, no database, no
network in this suite) and pins what makes each one honest. `scripts/backup.sh` must dump the
database in a format that can be restored selectively (`--format=custom`), prove the archive is
readable before the run is called a success (`pg_restore --list`), take the files with it (the
MinIO volume, not just Postgres), and seal the set with checksums that cover *both* files.
Retention is by stamp, not mtime, and it removes a set whole -- dump, files, checksums -- so a
half-deleted set can never sit in the directory claiming to be one.

`scripts/restore_drill.sh` must do the opposite of a backup and nothing less: verify the
checksums it was handed, restore into a database that is not the live one (`_drill`, created
for the occasion, dropped afterwards), compare the restored set with the live one -- the public
table set and the number of applied migrations -- and only then print its `ok`. The order is
the claim: a script that prints `ok` before it compares has printed a greeting. A set that is
missing its files archive or its checksums is refused before any of that, because a partial set
is not a smaller backup, it is a set somebody has to notice.

Neither script may name a container. Both stacks (development and production) share the same
compose service keys, and the file that decides which pair is up is `COMPOSE_FILE`; a script
that hard-codes `careeros-postgres-prod` works on exactly one host and fails closed on the
other -- at 04:10, in cron, with no one watching. `docker compose ps -q` follows the file, so
the check here is that the literal container names appear nowhere in either script.
"""

from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
SCRIPTS = ROOT / "scripts"
BACKUP = SCRIPTS / "backup.sh"
DRILL = SCRIPTS / "restore_drill.sh"

CONTAINER_NAMES = ("careeros-postgres", "careeros-minio")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_both_scripts_exist_and_stop_at_the_first_failure():
    for script in (BACKUP, DRILL):
        source = read(script)

        assert source.startswith("#!/usr/bin/env bash\n"), f"{script.name} does not name its interpreter"
        assert "\nset -euo pipefail\n" in source, (
            f"{script.name} must fail loudly: `-e` exits on the first broken step, `-u` refuses "
            "an unset variable instead of backing up an empty database, `-o pipefail` keeps a "
            "tail of a pipeline from swallowing the failure"
        )


def test_the_backup_takes_both_stores_and_seals_both():
    source = read(BACKUP)

    assert "pg_dump" in source and "--format=custom" in source, (
        "custom format is what pg_restore can read selectively; a plain SQL file is all-or-nothing"
    )
    assert "docker cp" in source and "/data" in source, (
        "the files are half the state; a database dump alone restores a stack whose resumes are gone"
    )
    assert "sha256sum" in source and "shasum -a 256" in source, (
        "one checksum tool with a fallback keeps the script portable without dropping the seal"
    )
    assert 'sha256sum "$DUMP" "$FILES"' in source, "the checksum file must cover the dump *and* the files"
    assert "date -u +%Y%m%dT%H%M%SZ" in source, (
        "a fixed-width UTC stamp is what makes name order stamp order in the retention step"
    )


def test_the_backup_proves_the_archive_before_it_calls_the_run_a_success():
    source = read(BACKUP)

    verify = source.index("pg_restore --list")
    ok = source.index('echo "backup: ok"')
    assert verify < ok, "the archive is read before the run announces itself"


def test_the_backup_keeps_whole_sets_and_prunes_by_stamp():
    source = read(BACKUP)

    assert "BACKUP_KEEP" in source
    assert "sort -r" in source, "newest first, by stamp"
    assert 'tail -n "+$((BACKUP_KEEP + 1))"' in source, (
        "the keep count is one number: BACKUP_KEEP sets stay, the rest go"
    )
    assert '"${base}-files.tgz"' in source and '"${base}.sha256"' in source, (
        "pruning removes the whole set, never a stray dump that outlives its checksums"
    )


def test_neither_script_names_a_container_that_the_compose_file_should_name():
    for script in (BACKUP, DRILL):
        source = read(script)

        assert "docker compose ps -q postgres" in source, (
            f"{script.name} must ask the compose project which container is postgres"
        )
        for name in CONTAINER_NAMES:
            assert name not in source, (
                f"{script.name} names {name}; the dev and prod containers differ and COMPOSE_FILE "
                "is the file that knows which one is up"
            )


def test_the_drill_restores_elsewhere_and_compares_before_it_trusts():
    source = read(DRILL)

    assert "career_os_drill" in source, "the default target is a database that is not the live one"
    assert "DROP DATABASE IF EXISTS" in source and "CREATE DATABASE" in source, (
        "the drill target is built for the occasion, so a previous drill cannot lend it a table"
    )
    assert "--exit-on-error" in source, "a restore that continues past an error restores an unknown subset"
    assert "pg_restore --list" not in source, "that is the backup's verification, not the drill's"

    restore = source.index("pg_restore --username")
    tables = source.index("information_schema.tables")
    migrations = source.index("flyway_schema_history")
    ok = source.index('echo "drill: ok"')
    assert restore < tables < migrations < ok, "the drill prints ok only after both comparisons"


def test_the_drill_refuses_a_set_that_is_not_whole():
    source = read(DRILL)

    assert "$FILES is missing" in source, "a set without its files archive is partial"
    assert "$SUMS is missing" in source, "a set without its checksums cannot be verified"
    assert "--check" in source, "the drill verifies the checksums it was handed"
    assert "diff -u" in source, "a table-set mismatch prints the difference, not a count"
    assert "exit 1" in source, "a drill that cannot fail is a drill that proves nothing"


def test_the_live_database_is_read_from_the_container_not_guessed_on_the_host():
    source = read(DRILL)

    assert 'docker exec "$POSTGRES_ID" sh -c \'printf %s "$POSTGRES_DB"\'' in source, (
        "the comparison must be against the database the stack is serving"
    )
    assert 'docker exec "$POSTGRES_ID" sh -c \'printf %s "$POSTGRES_USER"\'' in source
