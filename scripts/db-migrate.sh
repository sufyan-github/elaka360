#!/usr/bin/env bash
# Apply pending migrations in order. Safe for staging/production: never drops data.
# Applied files are recorded in schema_migrations with their SHA-256; a changed applied file aborts.
# Usage: DATABASE_URL=postgres://... bash scripts/db-migrate.sh
set -euo pipefail
cd "$(dirname "$0")/.."
: "${DATABASE_URL:?DATABASE_URL must be set}"
PSQL=(psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -qAt)

"${PSQL[@]}" -c "CREATE TABLE IF NOT EXISTS schema_migrations (file text PRIMARY KEY, sha256 text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now());"
for f in db/migrations/*.sql; do
  name=$(basename "$f")
  sum=$(sha256sum "$f" | cut -d' ' -f1)
  applied=$("${PSQL[@]}" -c "SELECT sha256 FROM schema_migrations WHERE file = '$name'")
  if [[ -n "$applied" ]]; then
    [[ "$applied" == "$sum" ]] || { echo "db-migrate: $name changed after it was applied — add a new migration instead" >&2; exit 3; }
    continue
  fi
  echo "→ applying $name"
  "${PSQL[@]}" -f "$f"
  "${PSQL[@]}" -c "INSERT INTO schema_migrations(file, sha256) VALUES ('$name', '$sum')"
done
echo "db-migrate: up to date"
