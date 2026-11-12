-- D1 schema for the Cloudflare edge API (apps/edge-api). Idempotent: applied before every data sync.
-- Reference tables hold snapshots of the NestJS API's own responses (apps/api/src/cli/export-edge.ts), refreshed
-- row by row by scripts/d1-sync.mjs using the content hash `h`. Keep indexes few: every index costs one extra
-- row written per insert, and the free plan allows 100,000 rows written per day.

CREATE TABLE IF NOT EXISTS areas (
  id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, parent_id INTEGER, level TEXT NOT NULL, depth INTEGER NOT NULL,
  name_en TEXT, summary TEXT NOT NULL, detail TEXT NOT NULL, stats TEXT NOT NULL, h TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS areas_level_parent ON areas(level, parent_id);

CREATE TABLE IF NOT EXISTS places (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, summary TEXT NOT NULL, detail TEXT NOT NULL, h TEXT NOT NULL);

-- places with coordinates (nearby, map pins)
CREATE TABLE IF NOT EXISTS place_points (
  id INTEGER PRIMARY KEY, lat REAL NOT NULL, lon REAL NOT NULL, division_id INTEGER, district_id INTEGER, upazila_id INTEGER,
  union_id INTEGER, city_corporation_id INTEGER, category_key TEXT, subcategory_key TEXT, summary TEXT NOT NULL, h TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS place_points_lat ON place_points(lat);

-- ordered place ids per (area, category); area 0 = all places, cat '' = all categories; chunks of 2,000 ids
CREATE TABLE IF NOT EXISTS area_lists (
  area_id INTEGER NOT NULL, cat TEXT NOT NULL, chunk INTEGER NOT NULL, total INTEGER NOT NULL, ids TEXT NOT NULL, h TEXT NOT NULL,
  PRIMARY KEY (area_id, cat, chunk)) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS boundaries (
  id INTEGER PRIMARY KEY, level TEXT NOT NULL, path TEXT NOT NULL, minx REAL NOT NULL, miny REAL NOT NULL, maxx REAL NOT NULL,
  maxy REAL NOT NULL, summary TEXT NOT NULL, geometry TEXT NOT NULL, h TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS boundaries_minx ON boundaries(minx);

-- small documents: national stats, categories, hotlines, boundary levels, data version
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL, h TEXT NOT NULL) WITHOUT ROWID;

-- user data (never touched by the sync)
CREATE TABLE IF NOT EXISTS contact_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, subject TEXT NOT NULL, message TEXT NOT NULL, ip_hash TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')));
CREATE INDEX IF NOT EXISTS contact_messages_ip ON contact_messages(ip_hash, created_at);
