#!/bin/sh
# Placement: infrastructure/postgres/restore_inside.sh
# Runs INSIDE the mahara-postgres container (called by restore_supabase_backup.ps1).
# Loads a Supabase cluster dump into a throwaway database, then copies only the
# application schemas (public, eval_graphrag) into a clean target database.
# Usage: sh restore_inside.sh /tmp/cluster.sql <target_database>
set -eu

DUMP="$1"
TARGET="$2"
RAW="supabase_raw_restore"
PSQL="psql -U postgres -v ON_ERROR_STOP=1 -q"

if [ -n "$($PSQL -d template1 -tAc "SELECT 1 FROM pg_database WHERE datname = '$TARGET'")" ]; then
    echo "Database $TARGET already exists; refusing to overwrite it." >&2
    exit 1
fi

# The section of the cluster dump that holds the Supabase "postgres" database.
START=$(grep -n '^-- Database "postgres" dump' "$DUMP" | cut -d: -f1)
[ -n "$START" ] || { echo "No postgres database section in $DUMP" >&2; exit 1; }
tail -n +"$START" "$DUMP" | sed "s/^\\\\connect postgres\$/\\\\connect $RAW/" > /tmp/postgres_db.sql

# Supabase roles must exist for GRANT/OWNER statements. Never touch "postgres":
# the dump would demote it to NOSUPERUSER.
for role in $(grep -o '^CREATE ROLE [a-z_]*' "$DUMP" | awk '{print $3}' | grep -v '^postgres$'); do
    $PSQL -d template1 -c "DO \$\$BEGIN CREATE ROLE $role NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END\$\$;"
done

$PSQL -d template1 -c "DROP DATABASE IF EXISTS $RAW;" -c "CREATE DATABASE $RAW;"
# Supabase-only objects (vault, event triggers) fail here by design; they are not copied.
psql -U postgres -q -d "$RAW" -f /tmp/postgres_db.sql > /tmp/raw_restore.log 2>&1 || true
echo "Supabase-only statements skipped: $(grep -c ERROR /tmp/raw_restore.log || true)"

pg_dump -U postgres -d "$RAW" -n public -n eval_graphrag --no-owner --no-privileges -f /tmp/app_schemas.sql
sed -i '/^CREATE SCHEMA public;/d' /tmp/app_schemas.sql

$PSQL -d template1 -c "CREATE DATABASE $TARGET TEMPLATE template0;"
$PSQL -d "$TARGET" -c "CREATE EXTENSION vector;"
$PSQL -d "$TARGET" -f /tmp/app_schemas.sql
$PSQL -d template1 -c "DROP DATABASE $RAW;"
rm -f /tmp/postgres_db.sql /tmp/app_schemas.sql /tmp/raw_restore.log

echo "Restored into $TARGET: $($PSQL -d "$TARGET" -tAc 'SELECT count(*) FROM public.job_offers') job offers, $($PSQL -d "$TARGET" -tAc 'SELECT count(*) FROM public.users') users."
