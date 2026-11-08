#!/usr/bin/env bash
# Drop + recreate the schema, apply migrations in order, then load the seed.
# Usage: DATABASE_URL=postgres://... bash scripts/db-reset.sh
set -euo pipefail
cd "$(dirname "$0")/.."
: "${DATABASE_URL:=postgres://elaka360:elaka360@localhost:5432/elaka360}"
PSQL=(psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -q)
echo "→ resetting schema"
"${PSQL[@]}" -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"
for f in db/migrations/*.sql; do echo "→ $f"; "${PSQL[@]}" -f "$f"; done
echo "→ db/seed/seed.sql"
"${PSQL[@]}" -f db/seed/seed.sql >/dev/null
"${PSQL[@]}" -At -c "SELECT level, count(*) FROM admin_areas GROUP BY 1 ORDER BY 1;"
