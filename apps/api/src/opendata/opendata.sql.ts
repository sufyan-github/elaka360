/* Open Data reads the base tables with an explicit eligibility filter: exports are sourced-only in every
   visibility mode (data trust policy). */

/** $1 level|null, $2 limit, $3 offset */
export const OD_AREAS_SQL = `
SELECT a.id::int, a.level::text, a.parent_id::int, a.name_bn, a.name_en, a.path, a.bbs_code,
       a.lat::float8, a.lon::float8, a.area_km2::float8, a.area_basis, a.population_2022, a.population_basis,
       a.evidence_level::text, es.key AS source_key, to_char(a.last_reviewed_at, 'YYYY-MM-DD') AS last_reviewed
FROM admin_areas a LEFT JOIN data_sources es ON es.id = a.evidence_source_id
WHERE a.production_eligible AND a.status = 'active' AND a.level <> 'country' AND ($1::text IS NULL OR a.level::text = $1)
ORDER BY a.id LIMIT $2 OFFSET $3`;

/** $1 category key|null, $2 limit, $3 offset */
export const OD_PLACES_SQL = `
SELECT p.public_id, p.slug, p.name_bn, p.name_en, c.key AS category, sc.key AS subcategory, p.ownership,
       COALESCE(p.union_id, p.upazila_id, p.city_corporation_id, p.district_id)::int AS area_id,
       p.lat::float8, p.lon::float8, p.website, p.established, p.evidence_level::text, es.key AS source_key,
       to_char(p.last_verified_at, 'YYYY-MM-DD') AS last_verified
FROM places p JOIN categories c ON c.id = p.category_id LEFT JOIN categories sc ON sc.id = p.subcategory_id
LEFT JOIN data_sources es ON es.id = COALESCE(p.evidence_source_id, p.data_source_id)
WHERE p.production_eligible AND p.status = 'active' AND ($1::text IS NULL OR c.key = $1 OR sc.key = $1)
ORDER BY p.id LIMIT $2 OFFSET $3`;

/** Sources cited by at least one exported record. */
export const OD_SOURCES_SQL = `
SELECT s.key, s.name, NULLIF(s.url, '') AS url, s.license, s.organization, s.source_type, to_char(s.access_date, 'YYYY-MM-DD') AS access_date
FROM data_sources s
WHERE EXISTS (SELECT 1 FROM admin_areas a WHERE a.production_eligible AND a.evidence_source_id = s.id)
   OR EXISTS (SELECT 1 FROM places p WHERE p.production_eligible AND COALESCE(p.evidence_source_id, p.data_source_id) = s.id)
ORDER BY s.key`;

/** Count one request for a key in the current minute; returns the key's limit and the new count. $1 key hash */
export const OD_KEY_HIT_SQL = `
WITH k AS (UPDATE api_keys SET last_used_at = now() WHERE key_hash = $1 AND revoked_at IS NULL RETURNING id, rate_per_min),
u AS (INSERT INTO api_key_usage(key_id, minute, count) SELECT id, date_trunc('minute', now()), 1 FROM k
      ON CONFLICT (key_id, minute) DO UPDATE SET count = api_key_usage.count + 1 RETURNING count)
SELECT k.id::int, k.rate_per_min, u.count FROM k, u`;

export const OD_KEYS_LIST_SQL = `
SELECT k.id, k.name, k.key_prefix, k.rate_per_min, to_char(k.created_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS created_at,
       to_char(k.last_used_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS last_used_at, to_char(k.revoked_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS revoked_at,
       u.name AS created_by_name
FROM api_keys k LEFT JOIN users u ON u.id = k.created_by ORDER BY k.created_at DESC`;
