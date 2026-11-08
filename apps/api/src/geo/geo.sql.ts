/* SQL for the Geo module. Kept as plain constants so scripts/check-sql.py can
   prepare and execute every statement against the seeded database in CI. */

export const AREA_SUMMARY_COLS = `a.id::int, a.level::text, a.parent_id::int, a.name_bn, a.name_en, a.slug, a.path, a.verified`;

export const AREA_DETAIL_SQL = `
SELECT ${AREA_SUMMARY_COLS}, a.bbs_code, a.website, a.lat::float8, a.lon::float8, a.area_km2::float8,
       a.area_basis, a.population_2022, a.population_basis, a.wards_count, a.established,
       a.production_eligible, a.notes,
       CASE WHEN s.id IS NULL THEN NULL ELSE json_build_object('key', s.key, 'name', s.name, 'url', s.url) END AS source
FROM admin_areas a
LEFT JOIN data_sources s ON s.id = COALESCE(a.population_source_id, a.data_source_id)
WHERE a.path = $1`;

export const AREA_BY_ID_PATH_SQL = `SELECT path FROM admin_areas WHERE id = $1`;

export const BREADCRUMB_SQL = `
WITH RECURSIVE up AS (
  SELECT a.*, 0 AS depth FROM admin_areas a WHERE a.id = $1
  UNION ALL
  SELECT p.*, up.depth + 1 FROM admin_areas p JOIN up ON p.id = up.parent_id
)
SELECT ${AREA_SUMMARY_COLS} FROM up a ORDER BY a.depth DESC`;

export const CHILDREN_SQL = `
SELECT ${AREA_SUMMARY_COLS} FROM admin_areas a
WHERE a.parent_id = $1 AND ($2::text IS NULL OR a.level::text = $2)
ORDER BY a.level, a.name_en`;

export const DESCENDANT_COUNTS_SQL = `
WITH RECURSIVE d AS (
  SELECT id, level FROM admin_areas WHERE parent_id = $1
  UNION ALL
  SELECT a.id, a.level FROM admin_areas a JOIN d ON a.parent_id = d.id
)
SELECT level::text, count(*)::int AS n FROM d GROUP BY level`;

export const PLACE_COUNTS_SQL = `
SELECT c.key, count(*)::int AS n
FROM places p JOIN categories c ON c.id = p.category_id
WHERE p.status = 'active'
  AND $1::bigint IN (p.division_id, p.district_id, p.upazila_id, p.union_id, p.city_corporation_id)
GROUP BY c.key`;

export const NATIONAL_PLACE_COUNTS_SQL = `
SELECT c.key, count(*)::int AS n FROM places p JOIN categories c ON c.id = p.category_id
WHERE p.status = 'active' GROUP BY c.key`;

export const LIST_SQL = `
SELECT ${AREA_SUMMARY_COLS} FROM admin_areas a
WHERE a.level::text = $1 AND ($2::bigint IS NULL OR a.parent_id = $2)
ORDER BY a.name_en
LIMIT $3 OFFSET $4`;

export const NATIONAL_STATS_SQL = `
SELECT
  count(*) FILTER (WHERE level = 'division')::int AS division,
  count(*) FILTER (WHERE level = 'district')::int AS district,
  count(*) FILTER (WHERE level = 'upazila')::int AS upazila,
  count(*) FILTER (WHERE level = 'union')::int AS "union",
  count(*) FILTER (WHERE level = 'city_corporation')::int AS city_corporation,
  count(*) FILTER (WHERE level = 'pourashava')::int AS pourashava,
  (SELECT count(*)::int FROM places WHERE status = 'active') AS places,
  (SELECT count(*)::int FROM places WHERE status = 'active' AND verification_status = 'verified') AS verified_places
FROM admin_areas`;
