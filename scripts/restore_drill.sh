#!/usr/bin/env bash
# Restore drill: prove the newest backup still restores, without touching the live
# database (roadmap 19.9).
#
# The drill takes the newest careeros-*.dump, verifies its checksums, restores it into
# a throwaway database (<live db>_drill by default) on the same server, and compares
# that database with the live one:
#   - the set of public tables must be identical,
#   - the number of applied Flyway migrations must be identical,
#   - the files archive must open and hold at least one entry.
# It then drops the drill database, unless KEEP_DRILL=1.
#
# On any mismatch the drill database is kept for inspection and the script exits 1 --
# a drill that cannot fail is a drill that proves nothing.
#
# The files archive is verified readable, not restored into a bucket: unpacking it
# over the live MinIO data would overwrite the objects it was taken from, which is a
# restore, not a drill. docs/RUNBOOK.md has the by-hand restore for that path.
#
# Which stack is drilled is decided by COMPOSE_FILE, like scripts/backup.sh:
#   development   docker compose up (the default; docker-compose.yml)
#   production    COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml
#
# Usage:
#   scripts/restore_drill.sh
#   BACKUP_DIR=/srv/backups KEEP_DRILL=1 scripts/restore_drill.sh
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-backups}"
DRILL_DB="${DRILL_DB:-career_os_drill}"
KEEP_DRILL="${KEEP_DRILL:-0}"

die() {
    echo "drill: $*" >&2
    exit 1
}

# Compose resolves every `${...}` while it renders the project, from the shell and the file
# `--env-file` names -- never from the services' `env_file:`. The prod override marks its
# values required and cannot render without that file, so the script hands it over whenever
# COMPOSE_FILE names the override; the development stack keeps its own defaults.
COMPOSE=(docker compose)
case "${COMPOSE_FILE:-}" in
    *docker-compose.prod.yml*) COMPOSE+=(--env-file .env.prod) ;;
esac

STAGE="$(mktemp -d)"
cleanup() {
    rm -rf "$STAGE"
}
trap cleanup EXIT

POSTGRES_ID="$("${COMPOSE[@]}" ps -q postgres)"
[ -n "$POSTGRES_ID" ] || die "the postgres service is not running (COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.yml})"

# Live names are read from the container, never guessed on the host: the drill must
# compare against the database the stack is actually serving.
LIVE_DB="$(docker exec "$POSTGRES_ID" sh -c 'printf %s "$POSTGRES_DB"')"
DB_USER="$(docker exec "$POSTGRES_ID" sh -c 'printf %s "$POSTGRES_USER"')"
[ -n "$LIVE_DB" ] || die "the postgres container does not name a database (POSTGRES_DB is empty)"

LATEST="$(find "$BACKUP_DIR" -maxdepth 1 -type f -name 'careeros-*.dump' -print | sort -r | head -n 1)"
[ -n "$LATEST" ] || die "no careeros-*.dump in $BACKUP_DIR"
FILES="${LATEST%.dump}-files.tgz"
SUMS="${LATEST%.dump}.sha256"

echo "drill: newest set is $(basename "$LATEST")"
[ -f "$FILES" ] || die "$FILES is missing; the set is partial and cannot be trusted"
[ -f "$SUMS" ] || die "$SUMS is missing; the set is partial and cannot be trusted"

echo "drill: verifying checksums"
if command -v sha256sum > /dev/null 2>&1; then
    sha256sum --check "$SUMS" || die "the checksums do not match the files; the set is corrupt"
else
    shasum -a 256 --check "$SUMS" || die "the checksums do not match the files; the set is corrupt"
fi

echo "drill: opening the files archive"
tar -tzf "$FILES" > "$STAGE/files.list" || die "$FILES is not a readable tar archive"
FILE_COUNT="$(wc -l < "$STAGE/files.list" | tr -d ' ')"
[ "$FILE_COUNT" -ge 1 ] || die "$FILES is empty"

echo "drill: restoring into $DRILL_DB"
docker exec "$POSTGRES_ID" psql --username="$DB_USER" --dbname=postgres -v ON_ERROR_STOP=1 \
    -c "DROP DATABASE IF EXISTS \"$DRILL_DB\" WITH (FORCE)" \
    -c "CREATE DATABASE \"$DRILL_DB\"" > /dev/null
docker exec -i "$POSTGRES_ID" pg_restore --username="$DB_USER" --dbname="$DRILL_DB" \
    --no-owner --no-privileges --exit-on-error < "$LATEST" || die "pg_restore could not replay $LATEST"

tables() {
    docker exec "$POSTGRES_ID" psql --username="$DB_USER" --dbname="$1" --no-psqlrc \
        --tuples-only --no-align \
        -c "select table_name from information_schema.tables where table_schema = 'public' and table_type = 'BASE TABLE' order by 1"
}

migrations() {
    docker exec "$POSTGRES_ID" psql --username="$DB_USER" --dbname="$1" --no-psqlrc \
        --tuples-only --no-align \
        -c "select count(*) from flyway_schema_history"
}

echo "drill: comparing $DRILL_DB with $LIVE_DB"
LIVE_TABLES="$(tables "$LIVE_DB")"
DRILL_TABLES="$(tables "$DRILL_DB")"
if [ "$LIVE_TABLES" != "$DRILL_TABLES" ]; then
    diff -u <(printf '%s\n' "$LIVE_TABLES") <(printf '%s\n' "$DRILL_TABLES") > "$STAGE/tables.diff" || true
    echo "drill: the restored table set differs from the live one:" >&2
    cat "$STAGE/tables.diff" >&2
    die "the drill database is kept; inspect it, then drop it by hand"
fi
TABLE_COUNT="$(printf '%s\n' "$LIVE_TABLES" | grep -c . || true)"

LIVE_MIGRATIONS="$(migrations "$LIVE_DB")"
DRILL_MIGRATIONS="$(migrations "$DRILL_DB")"
if [ "$LIVE_MIGRATIONS" != "$DRILL_MIGRATIONS" ]; then
    die "the restored database has $DRILL_MIGRATIONS migration(s), the live one $LIVE_MIGRATIONS"
fi

if [ "$KEEP_DRILL" != "1" ]; then
    docker exec "$POSTGRES_ID" psql --username="$DB_USER" --dbname=postgres -v ON_ERROR_STOP=1 \
        -c "DROP DATABASE IF EXISTS \"$DRILL_DB\" WITH (FORCE)" > /dev/null
    echo "drill: dropped $DRILL_DB"
else
    echo "drill: KEEP_DRILL=1, $DRILL_DB is still there"
fi

echo "drill: ok"
echo "  dump       $(basename "$LATEST")"
echo "  tables     $TABLE_COUNT (same set as $LIVE_DB)"
echo "  migrations $DRILL_MIGRATIONS (same count as $LIVE_DB)"
echo "  files      $FILE_COUNT entries (archive opens; not restored into a bucket)"
