import { AREA_SUMMARY_COLS } from '../geo/geo.sql';

/* Source rows for the Typesense index — public views only, so the index never holds non-eligible records. */

export const AREA_DOCS_SQL = `
SELECT a.id::int, a.level::text, a.parent_id::int, a.name_bn, a.name_en, a.slug, a.path, a.verified,
       a.evidence_level::text, a.production_eligible, a.population_2022, p.name_bn AS parent_bn, p.name_en AS parent_en
FROM public_admin_areas a LEFT JOIN public_admin_areas p ON p.id = a.parent_id
WHERE a.level <> 'country'`;

export const PLACE_DOCS_SQL = `
SELECT p.public_id, p.slug, p.name_bn, p.name_en, c.key AS category_key, sc.key AS subcategory_key,
       NULLIF(concat_ws(', ', loc.name_bn, d.name_bn), '') AS area_label_bn,
       NULLIF(concat_ws(', ', loc.name_en, d.name_en), '') AS area_label_en,
       p.lat::float8, p.lon::float8, p.verification_status::text, p.evidence_level::text, p.production_eligible, p.district_id::int
FROM public_places p
JOIN categories c ON c.id = p.category_id
LEFT JOIN categories sc ON sc.id = p.subcategory_id
LEFT JOIN public_admin_areas loc ON loc.id = COALESCE(p.union_id, p.upazila_id, p.city_corporation_id)
LEFT JOIN public_admin_areas d ON d.id = p.district_id`;

/**
 * Postgres fallback when Typesense is not configured or down.
 * $1 raw text, $2 Banglish key (latinKey of the text, '' for Bangla input), $3 level | null, $4 area path prefix | null, $5 limit.
 * Matches prefixes of any word, the Banglish key (so "rajsahi" finds Rajshahi), and trigram similarity for typos.
 */
export const AREA_SEARCH_SQL = `
SELECT ${AREA_SUMMARY_COLS} FROM public_admin_areas a
WHERE a.level <> 'country'
  AND ($3::text IS NULL OR a.level::text = $3)
  AND ($4::text IS NULL OR a.path LIKE $4 || '/%')
  AND (
    a.name_bn ILIKE $1 || '%' OR a.name_bn ILIKE '% ' || $1 || '%'
    OR lower(a.name_en) LIKE lower($1) || '%' OR lower(a.name_en) LIKE '% ' || lower($1) || '%'
    OR ($2 <> '' AND (a.name_key LIKE $2 || '%' OR (length($2) >= 4 AND a.name_key % $2)))
    OR (length($1) >= 3 AND a.name_bn % $1))
ORDER BY (a.name_key = $2 OR a.name_bn = $1 OR lower(a.name_en) = lower($1)) DESC,
         array_position(ARRAY['division','district','city_corporation','upazila','pourashava','union']::text[], a.level::text),
         greatest(similarity(a.name_key, $2), similarity(a.name_bn, $1)) DESC, a.name_en
LIMIT $5`;

/** Prefix suggestions for the search box. $1 raw text, $2 Banglish key, $3 limit */
export const SUGGEST_SQL = `
(SELECT 'area' AS kind, a.name_bn, a.name_en, a.path AS href_key, a.level::text AS detail
 FROM public_admin_areas a
 WHERE a.level <> 'country' AND (a.name_bn ILIKE $1 || '%' OR lower(a.name_en) LIKE lower($1) || '%' OR ($2 <> '' AND a.name_key LIKE $2 || '%'))
 ORDER BY array_position(ARRAY['division','district','city_corporation','upazila','pourashava','union']::text[], a.level::text), a.name_en
 LIMIT $3)
UNION ALL
(SELECT 'place', p.name_bn, coalesce(p.name_en, ''), p.slug, p.evidence_level::text
 FROM public_places p
 WHERE p.name_bn ILIKE $1 || '%' OR lower(coalesce(p.name_en, '')) LIKE lower($1) || '%' OR ($2 <> '' AND p.name_key LIKE $2 || '%')
 ORDER BY p.name_en
 LIMIT $3)`;
