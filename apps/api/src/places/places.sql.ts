/* SQL for the Places module. Public reads use public_places / public_admin_areas (see geo.sql.ts). */

export const PLACE_SUMMARY_COLS = `
  p.public_id, p.slug, p.name_bn, p.name_en,
  c.key AS category_key, sc.key AS subcategory_key,
  NULLIF(concat_ws(', ', loc.name_bn, d.name_bn), '') AS area_label_bn,
  NULLIF(concat_ws(', ', loc.name_en, d.name_en), '') AS area_label_en,
  p.lat::float8, p.lon::float8, p.verification_status::text, p.evidence_level::text, p.production_eligible`;

export const PLACE_JOINS = `
FROM public_places p
JOIN categories c ON c.id = p.category_id
LEFT JOIN categories sc ON sc.id = p.subcategory_id
LEFT JOIN public_admin_areas loc ON loc.id = COALESCE(p.union_id, p.upazila_id, p.city_corporation_id)
LEFT JOIN public_admin_areas d ON d.id = p.district_id`;

/** Area filter on $1 (any of the five area columns). */
export const PLACE_AREA_FILTER = `($1::bigint IS NULL OR p.division_id = $1 OR p.district_id = $1 OR p.upazila_id = $1 OR p.union_id = $1 OR p.city_corporation_id = $1)`;

/** Every search term in $3 must match the Bangla name, the English name, the short name or the Banglish key. */
export const PLACE_TERMS_FILTER = `($3::text[] IS NULL OR NOT EXISTS (
    SELECT 1 FROM unnest($3::text[]) t
    WHERE NOT (p.name_bn ILIKE '%' || t || '%' OR coalesce(p.name_en, '') ILIKE '%' || t || '%'
               OR coalesce(p.short_name, '') ILIKE t OR p.name_key LIKE '%' || elaka_latin_key(t) || '%')))`;

/** $1 area id | null, $2 category key | null, $3 search terms text[] | null, $4 limit, $5 offset, $6 sort ('relevance'|'name') */
export const PLACE_LIST_SQL = `
SELECT ${PLACE_SUMMARY_COLS} ${PLACE_JOINS}
WHERE ${PLACE_AREA_FILTER}
  AND ($2::text IS NULL OR c.key = $2 OR sc.key = $2)
  AND ${PLACE_TERMS_FILTER}
ORDER BY CASE WHEN $6 = 'name' THEN 0 ELSE array_position(ARRAY['official','secondary','community','unverified']::text[], p.evidence_level::text) END,
         p.name_en NULLS LAST, p.name_bn
LIMIT $4 OFFSET $5`;

/** Total for the same filters (so pages can say "N found" truthfully — finding C16). */
export const PLACE_COUNT_SQL = `
SELECT count(*)::int AS n ${PLACE_JOINS}
WHERE ${PLACE_AREA_FILTER}
  AND ($2::text IS NULL OR c.key = $2 OR sc.key = $2)
  AND ${PLACE_TERMS_FILTER}`;

/** PostGIS radius search. $1 lat, $2 lon, $3 radius metres, $4 category key | null, $5 limit */
export const PLACE_NEARBY_SQL = `
WITH g AS (SELECT ST_SetSRID(ST_MakePoint($2, $1), 4326)::geography AS pt)
SELECT ${PLACE_SUMMARY_COLS}, round(ST_Distance(p.geom, g.pt))::int AS distance_m
${PLACE_JOINS}, g
WHERE p.geom IS NOT NULL AND ST_DWithin(p.geom, g.pt, $3)
  AND ($4::text IS NULL OR c.key = $4 OR sc.key = $4)
ORDER BY p.geom <-> g.pt
LIMIT $5`;

export const PLACE_DETAIL_SQL = `
SELECT ${PLACE_SUMMARY_COLS},
  p.id::int AS place_id, p.short_name, p.ownership, p.address_bn, p.address_en, p.postcode, p.phones, p.email, p.website,
  p.established, p.attributes, p.description_bn, p.description_en, p.source_notes, p.opening_hours,
  p.rating_avg::float8, p.rating_count, p.verification_notes,
  to_char(p.last_verified_at, 'YYYY-MM-DD') AS last_verified_at,
  COALESCE(p.union_id, p.upazila_id, p.city_corporation_id, p.district_id) AS area_id,
  CASE WHEN s.id IS NULL THEN NULL ELSE json_build_object('key', s.key, 'name', s.name, 'url', NULLIF(s.url, '')) END AS source
${PLACE_JOINS}
LEFT JOIN data_sources s ON s.id = COALESCE(p.evidence_source_id, p.data_source_id)
WHERE p.slug = $1`;

/** Map pins. $1 area id | null, $2 category key | null, $3..$6 optional bbox (west, south, east, north) */
export const PLACE_GEO_SQL = `
SELECT ${PLACE_SUMMARY_COLS} ${PLACE_JOINS}
WHERE p.geom IS NOT NULL
  AND ${PLACE_AREA_FILTER}
  AND ($2::text IS NULL OR c.key = $2 OR sc.key = $2)
  AND ($3::float8 IS NULL OR p.geom && ST_MakeEnvelope($3, $4, $5, $6, 4326)::geography)
LIMIT 5000`;

/** Internal id of a public place (for reviews/saves). */
export const PLACE_ID_SQL = `SELECT id::int FROM public_places WHERE slug = $1`;
