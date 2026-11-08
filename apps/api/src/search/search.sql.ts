import { AREA_SUMMARY_COLS } from '../geo/geo.sql';

/* Source rows for the Typesense index. */

export const AREA_DOCS_SQL = `
SELECT a.id::int, a.level::text, a.parent_id::int, a.name_bn, a.name_en, a.slug, a.path, a.verified,
       a.population_2022, p.name_bn AS parent_bn, p.name_en AS parent_en
FROM admin_areas a LEFT JOIN admin_areas p ON p.id = a.parent_id
WHERE a.level <> 'country' AND a.status = 'active'`;

export const PLACE_DOCS_SQL = `
SELECT p.public_id, p.slug, p.name_bn, p.name_en, c.key AS category_key, sc.key AS subcategory_key,
       concat_ws(', ', loc.name_bn, d.name_bn) AS area_label_bn,
       concat_ws(', ', loc.name_en, d.name_en) AS area_label_en,
       p.lat::float8, p.lon::float8, p.verification_status::text, p.district_id::int
FROM places p
JOIN categories c ON c.id = p.category_id
LEFT JOIN categories sc ON sc.id = p.subcategory_id
LEFT JOIN admin_areas loc ON loc.id = COALESCE(p.union_id, p.upazila_id, p.city_corporation_id)
LEFT JOIN admin_areas d ON d.id = p.district_id
WHERE p.status = 'active'`;

/** Postgres fallback when Typesense is not configured or down. $1 raw text, $2 latin key */
export const AREA_SEARCH_SQL = `
SELECT ${AREA_SUMMARY_COLS} FROM admin_areas a
WHERE a.level <> 'country' AND (
  a.name_bn ILIKE $1 || '%' OR a.name_bn ILIKE '% ' || $1 || '%'
  OR a.name_en ILIKE $1 || '%' OR a.name_en ILIKE '% ' || $1 || '%'
  OR ($2 <> '' AND regexp_replace(lower(a.name_en), '[^a-z0-9]', '', 'g') LIKE $2 || '%'))
ORDER BY array_position(ARRAY['division','district','city_corporation','upazila','pourashava','union']::text[], a.level::text), a.name_en
LIMIT 20`;
