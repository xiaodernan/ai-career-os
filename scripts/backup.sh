#!/usr/bin/env bash
# Nightly backup: the database and the files, sealed with checksums (roadmap 19.9).
#
# What it writes, one set per run, all named after the same UTC stamp:
#   careeros-<stamp>.dump        pg_dump custom-format archive of POSTGRES_DB
#   careeros-<stamp>-files.tgz   the MinIO data volume, tarred
#   careeros-<stamp>.sha256      one checksum line per file above
#
# What it does not do: copy the set off the host. The dump lives on the same disk as
# the database it protects, so an operator must mirror BACKUP_DIR somewhere else --
# docs/RUNBOOK.md has the sentence and the reason.
#
# Which stack is backed up is decided by COMPOSE_FILE, the same variable the rest of
# the ops scripts read:
#   development   docker compose up (the default; docker-compose.yml)
#   production    COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml
# Host paths and the compose project follow from that, so the script never names a
# container: the service key `postgres` is the same in both files.
#
# Usage:
#   scripts/backup.sh
#   BACKUP_DIR=/srv/backups BACKUP_KEEP=14 scripts/backup.sh
#
# Exit codes: 0 a complete set was written and verified; anything else means a partial
# set is on disk under a stamp that must not be trusted (see RUNBOOK, "Backups").
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-backups}"
BACKUP_KEEP="${BACKUP_KEEP:-7}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

die() {
    echo "backup: $*" >&2
    exit 1
}

case "$BACKUP_KEEP" in
    ''|*[!0-9]*) die "BACKUP_KEEP must be a positive integer, got '$BACKUP_KEEP'" ;;
esac
[ "$BACKUP_KEEP" -ge 1 ] || die "BACKUP_KEEP must be at least 1, got $BACKUP_KEEP"

mkdir -p "$BACKUP_DIR"
BACKUP_DIR="$(cd "$BACKUP_DIR" && pwd)"

DUMP="$BACKUP_DIR/careeros-$STAMP.dump"
FILES="$BACKUP_DIR/careeros-$STAMP-files.tgz"
SUMS="$BACKUP_DIR/careeros-$STAMP.sha256"

STAGE="$(mktemp -d)"
cleanup() {
    rm -rf "$STAGE"
}
trap cleanup EXIT

# The compose project is whatever COMPOSE_FILE says; an empty id means the service is
# not running, and a dump of a container that is not up is a guess, not a backup.
POSTGRES_ID="$(docker compose ps -q postgres)"
[ -n "$POSTGRES_ID" ] || die "the postgres service is not running (COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.yml})"
MINIO_ID="$(docker compose ps -q minio)"
[ -n "$MINIO_ID" ] || die "the minio service is not running (COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.yml})"

echo "backup: dumping postgres"
# The credentials come from the container's own environment, the same variables the
# service was started with -- the script names no database, so a renamed POSTGRES_DB
# is backed up as itself rather than as the default.
docker exec "$POSTGRES_ID" sh -c \
    'pg_dump --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --format=custom --no-owner --no-privileges' \
    > "$DUMP"
[ -s "$DUMP" ] || die "pg_dump wrote nothing to $DUMP"

# Verified before it is called a backup: pg_restore reads the archive's table of
# contents, which is the cheapest proof that the bytes are a restorable dump and not
# a truncated file.
docker exec -i "$POSTGRES_ID" pg_restore --list < "$DUMP" > /dev/null \
    || die "$DUMP is not a readable custom-format archive"

echo "backup: copying the minio data volume"
docker cp "$MINIO_ID:/data/." "$STAGE/minio"
tar -C "$STAGE/minio" -czf "$FILES" .

if command -v sha256sum > /dev/null 2>&1; then
    sha256sum "$DUMP" "$FILES" > "$SUMS"
else
    shasum -a 256 "$DUMP" "$FILES" > "$SUMS"
fi
[ -s "$SUMS" ] || die "no checksums were written to $SUMS"

# Retention: newest $BACKUP_KEEP sets by stamp, and a set is only ever removed whole.
# Name order is stamp order (UTC, fixed width), so the keep decision never depends on
# file mtimes, which a restore or a copy can rewrite.
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'careeros-*.dump' -print \
    | sort -r \
    | tail -n "+$((BACKUP_KEEP + 1))" \
    | while IFS= read -r stale; do
        base="${stale%.dump}"
        rm -f "$stale" "${base}-files.tgz" "${base}.sha256"
        echo "backup: pruned $(basename "$stale")"
    done

echo "backup: ok"
echo "  database  $DUMP"
echo "  files     $FILES"
echo "  checksums $SUMS"
