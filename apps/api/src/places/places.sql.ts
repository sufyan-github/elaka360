/* SQL for the Places module (see geo.sql.ts for why these are constants). */

export const PLACE_SUMMARY_COLS = `
  p.public_id, p.slug, p.name_bn, p.name_en,
  c.key AS category_key, sc.key AS subcategory_key,
  concat_ws(', ', loc.name_bn, d.name_bn) AS area_label_bn,
  concat_ws(', ', loc.name_en, d.name_en) AS area_label_en,
  p.lat::float8, p.lon::float8, p.verification_status::text`;

export const PLACE_JOINS = `
FROM places p
JOIN categories c ON c.id = p.category_id
LEFT JOIN categories sc ON sc.id = p.subcategory_id
LEFT JOIN admin_areas loc ON loc.id = COALESCE(p.union_id, p.upazila_id, p.city_corporation_id)
LEFT JOIN admin_areas d ON d.id = p.district_id`;

/** $1 area id | null, $2 category key | null, $3 text | null, $4 limit, $5 offset */
export const PLACE_LIST_SQL = `
SELECT ${PLACE_SUMMARY_COLS} ${PLACE_JOINS}
WHERE p.status = 'active'
  AND ($1::bigint IS NULL OR $1 IN (p.division_id, p.district_id, p.upazila_id, p.union_id, p.city_corporation_id))
  AND ($2::text IS NULL OR c.key = $2 OR sc.key = $2)
  AND ($3::text IS NULL OR p.name_bn ILIKE '%' || $3 || '%' OR p.name_en ILIKE '%' || $3 || '%')
ORDER BY (p.verification_status = 'verified') DESC, p.name_en
LIMIT $4 OFFSET $5`;

/** $1 lat, $2 lon, $3 radius metres, $4 category key | null, $5 limit */
export const PLACE_NEARBY_SQL = `
SELECT * FROM (
  SELECT ${PLACE_SUMMARY_COLS},
    round(6371000 * 2 * asin(sqrt(
      power(sin(radians(p.lat::float8 - $1) / 2), 2) +
      cos(radians($1)) * cos(radians(p.lat::float8)) * power(sin(radians(p.lon::float8 - $2) / 2), 2)
    )))::int AS distance_m
  ${PLACE_JOINS}
  WHERE p.status = 'active' AND p.lat IS NOT NULL
    AND p.lat BETWEEN $1 - ($3 / 111000.0) AND $1 + ($3 / 111000.0)
    AND ($4::text IS NULL OR c.key = $4 OR sc.key = $4)
) x
WHERE x.distance_m <= $3
ORDER BY x.distance_m
LIMIT $5`;

export const PLACE_DETAIL_SQL = `
SELECT ${PLACE_SUMMARY_COLS},
  p.short_name, p.ownership, p.address_bn, p.address_en, p.postcode, p.phones, p.email, p.website,
  p.established, p.attributes, p.description_bn, p.description_en, p.source_notes,
  to_char(p.last_verified_at, 'YYYY-MM-DD') AS last_verified_at,
  COALESCE(p.union_id, p.upazila_id, p.city_corporation_id, p.district_id) AS area_id,
  CASE WHEN s.id IS NULL THEN NULL ELSE json_build_object('key', s.key, 'name', s.name, 'url', s.url) END AS source
${PLACE_JOINS}
LEFT JOIN data_sources s ON s.id = p.data_source_id
WHERE p.slug = $1 AND p.status = 'active'`;

/** Map pins. $1 area id | null, $2 category key | null */
export const PLACE_GEO_SQL = `
SELECT ${PLACE_SUMMARY_COLS} ${PLACE_JOINS}
WHERE p.status = 'active' AND p.lat IS NOT NULL AND p.lon IS NOT NULL
  AND ($1::bigint IS NULL OR $1 IN (p.division_id, p.district_id, p.upazila_id, p.union_id, p.city_corporation_id))
  AND ($2::text IS NULL OR c.key = $2 OR sc.key = $2)
LIMIT 5000`;
