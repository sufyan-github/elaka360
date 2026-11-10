/* SQL for the Geo module. Public reads use the public_* views (db/migrations/0005), which enforce
   production eligibility. Kept as constants so scripts/check_sql.py executes each one in CI. */

export const AREA_SUMMARY_COLS = `a.id::int, a.level::text, a.parent_id::int, a.name_bn, a.name_en, a.slug, a.path, a.verified,
  a.evidence_level::text, a.production_eligible`;

export const SOURCE_JSON_S = `CASE WHEN s.id IS NULL THEN NULL ELSE json_build_object('key', s.key, 'name', s.name, 'url', NULLIF(s.url, '')) END`;
export const SOURCE_JSON_ES = `CASE WHEN es.id IS NULL THEN NULL ELSE json_build_object('key', es.key, 'name', es.name, 'url', NULLIF(es.url, '')) END`;

export const AREA_DETAIL_SQL = `
SELECT ${AREA_SUMMARY_COLS}, a.bbs_code, a.website, a.lat::float8, a.lon::float8, a.area_km2::float8,
       a.area_basis, a.population_2022, a.population_basis, a.wards_count, a.established, a.notes,
       a.verification_notes, to_char(a.last_reviewed_at, 'YYYY-MM-DD') AS last_reviewed_at,
       ${SOURCE_JSON_S} AS source, ${SOURCE_JSON_ES} AS evidence_source
FROM public_admin_areas a
LEFT JOIN data_sources s ON s.id = COALESCE(a.population_source_id, a.data_source_id)
LEFT JOIN data_sources es ON es.id = a.evidence_source_id
WHERE a.path = $1`;

export const AREA_BY_ID_PATH_SQL = `SELECT path FROM public_admin_areas WHERE id = $1`;

export const BREADCRUMB_SQL = `
WITH RECURSIVE up AS (
  SELECT a.*, 0 AS depth FROM public_admin_areas a WHERE a.id = $1
  UNION ALL
  SELECT p.*, up.depth + 1 FROM public_admin_areas p JOIN up ON p.id = up.parent_id
)
SELECT ${AREA_SUMMARY_COLS} FROM up a ORDER BY a.depth DESC`;

export const CHILDREN_SQL = `
SELECT ${AREA_SUMMARY_COLS} FROM public_admin_areas a
WHERE a.parent_id = $1 AND ($2::text IS NULL OR a.level::text = $2)
ORDER BY a.level, a.name_en`;

/** Descendants per level: public ones, and ones that exist but await verification. */
export const DESCENDANT_COUNTS_SQL = `
WITH RECURSIVE d AS (
  SELECT id, level, production_eligible, status FROM admin_areas WHERE parent_id = $1
  UNION ALL
  SELECT a.id, a.level, a.production_eligible, a.status FROM admin_areas a JOIN d ON a.parent_id = d.id
)
SELECT level::text,
       count(*) FILTER (WHERE status = 'active' AND (production_eligible OR elaka_include_unverified()))::int AS n,
       count(*) FILTER (WHERE status = 'active' AND NOT (production_eligible OR elaka_include_unverified()))::int AS pending
FROM d GROUP BY level`;

export const PLACE_COUNTS_SQL = `
SELECT c.key, count(*)::int AS n
FROM public_places p JOIN categories c ON c.id = p.category_id
WHERE (p.division_id = $1 OR p.district_id = $1 OR p.upazila_id = $1 OR p.union_id = $1 OR p.city_corporation_id = $1)
GROUP BY c.key`;

export const NATIONAL_PLACE_COUNTS_SQL = `
SELECT c.key, count(*)::int AS n FROM public_places p JOIN categories c ON c.id = p.category_id GROUP BY c.key`;

export const LIST_SQL = `
SELECT ${AREA_SUMMARY_COLS} FROM public_admin_areas a
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
  (SELECT count(*)::int FROM public_places) AS places,
  (SELECT count(*)::int FROM public_places WHERE evidence_level = 'official') AS verified_places,
  json_build_object(
    'division', count(*) FILTER (WHERE level = 'division' AND production_eligible),
    'district', count(*) FILTER (WHERE level = 'district' AND production_eligible),
    'upazila', count(*) FILTER (WHERE level = 'upazila' AND production_eligible),
    'union', count(*) FILTER (WHERE level = 'union' AND production_eligible),
    'city_corporation', count(*) FILTER (WHERE level = 'city_corporation' AND production_eligible),
    'pourashava', count(*) FILTER (WHERE level = 'pourashava' AND production_eligible),
    'places', (SELECT count(*) FROM public_places WHERE production_eligible)) AS sourced
FROM public_admin_areas`;

/** Flat subtree to a depth (nested in the service). $1 root id, $2 max depth. */
export const TREE_SQL = `
WITH RECURSIVE t AS (
  SELECT a.*, 0 AS depth FROM public_admin_areas a WHERE a.id = $1
  UNION ALL
  SELECT c.*, t.depth + 1 FROM public_admin_areas c JOIN t ON c.parent_id = t.id WHERE t.depth < $2
)
SELECT ${AREA_SUMMARY_COLS}, a.depth FROM t a ORDER BY a.depth, a.level, a.name_en
LIMIT 6000`;

/** Most specific public area whose boundary covers the point. $1 lat, $2 lon. */
export const LOCATE_SQL = `
SELECT ${AREA_SUMMARY_COLS} FROM public_admin_areas a
WHERE a.boundary IS NOT NULL AND ST_Covers(a.boundary, ST_SetSRID(ST_MakePoint($2, $1), 4326)::geography)
ORDER BY array_position(ARRAY['union','pourashava','city_corporation','upazila','district','division']::text[], a.level::text)
LIMIT 1`;

export const BOUNDARY_LEVELS_SQL = `SELECT DISTINCT level::text FROM public_admin_areas WHERE boundary IS NOT NULL`;

export const BOUNDARY_SQL = `
SELECT a.id::int, a.name_bn, a.name_en, a.level::text, ST_AsGeoJSON(a.boundary::geometry, 5)::json AS geometry
FROM public_admin_areas a WHERE a.id = $1 AND a.boundary IS NOT NULL`;
