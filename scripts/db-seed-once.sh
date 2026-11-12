#!/usr/bin/env bash
# First load of reference data into an EMPTY production database (after db-migrate.sh). Safe to re-run: it refuses
# when admin_areas already has rows, so it can never duplicate or overwrite data. Never use db-reset.sh outside dev.
# Usage: DATABASE_URL=postgres://... bash scripts/db-seed-once.sh
set -euo pipefail
cd "$(dirname "$0")/.."
: "${DATABASE_URL:?DATABASE_URL must be set}"
PSQL=(psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -qAt)
n=$("${PSQL[@]}" -c "SELECT count(*) FROM admin_areas")
if [[ "$n" != "0" ]]; then
  echo "db-seed-once: admin_areas already has $n rows; nothing to do" >&2
  exit 0
fi
echo "→ loading db/seed/seed.sql (one transaction)"
"${PSQL[@]}" -f db/seed/seed.sql >/dev/null
"${PSQL[@]}" -c "SELECT level, count(*) FROM admin_areas GROUP BY 1 ORDER BY 1"
echo "db-seed-once: done"
