#!/usr/bin/env bash
# DEVELOPMENT ONLY. Drops and recreates the public schema, applies migrations in order, then loads the seed.
# Usage: DATABASE_URL=postgres://... bash scripts/db-reset.sh
# Refuses to run when NODE_ENV=production or the database host is not local, unless ALLOW_DB_RESET=yes.
# For real environments use scripts/db-migrate.sh, which never drops anything.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${DATABASE_URL:=postgres://elaka360:elaka360@localhost:5432/elaka360}"

host=$(printf '%s' "$DATABASE_URL" | sed -E 's#^[a-z]+://([^@]*@)?([^:/?]+).*#\2#')
if [[ "${NODE_ENV:-}" == "production" ]]; then
  echo "db-reset: refusing to run with NODE_ENV=production" >&2; exit 2
fi
if [[ ! "$host" =~ ^(localhost|127\.0\.0\.1|::1|postgres|db)$ && "${ALLOW_DB_RESET:-}" != "yes" ]]; then
  echo "db-reset: host '$host' is not local; set ALLOW_DB_RESET=yes if you really mean to wipe it" >&2; exit 2
fi

PSQL=(psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -q)
echo "→ resetting schema on $host"
"${PSQL[@]}" -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"
for f in db/migrations/*.sql; do echo "→ $f"; "${PSQL[@]}" -f "$f"; done
echo "→ db/seed/seed.sql"
"${PSQL[@]}" -f db/seed/seed.sql >/dev/null
"${PSQL[@]}" -At -c "SELECT level, count(*), count(*) FILTER (WHERE production_eligible) AS public FROM admin_areas GROUP BY 1 ORDER BY 1;"
