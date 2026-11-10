/* Admin reads use the base tables (all records, any evidence level). */

export const ADMIN_STATS_SQL = `
SELECT
  (SELECT count(*)::int FROM admin_areas WHERE level <> 'country') AS areas_total,
  (SELECT count(*)::int FROM admin_areas WHERE level <> 'country' AND production_eligible) AS areas_public,
  (SELECT json_object_agg(e, n) FROM (SELECT evidence_level::text e, count(*)::int n FROM admin_areas WHERE level <> 'country' GROUP BY 1) x) AS areas_by_evidence,
  (SELECT count(*)::int FROM places WHERE status = 'active') AS places_total,
  (SELECT count(*)::int FROM places WHERE status = 'active' AND production_eligible) AS places_public,
  (SELECT coalesce(json_object_agg(e, n), '{}'::json) FROM (SELECT evidence_level::text e, count(*)::int n FROM places WHERE status = 'active' GROUP BY 1) x) AS places_by_evidence,
  (SELECT count(*)::int FROM contributions WHERE status IN ('new', 'in_review')) AS contributions_pending,
  (SELECT count(*)::int FROM review_reports WHERE status = 'open') AS review_reports_open,
  (SELECT count(*)::int FROM duplicate_candidates WHERE status = 'open') AS duplicate_candidates_open,
  (SELECT count(*)::int FROM data_quality_issues WHERE status = 'open') AS quality_issues_open,
  (SELECT count(*)::int FROM users WHERE status = 'active' AND last_login_at > now() - interval '30 days') AS users_active_30d`;

export const AUDIT_COLS = `l.id::int, l.actor_id::int, u.name AS actor_name, l.action, l.entity, l.entity_id, l.before, l.after, l.reason,
  l.request_id, to_char(l.at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS at`;

/** $1 entity | null, $2 entity_id | null, $3 actor | null, $4 limit, $5 offset */
export const AUDIT_LIST_SQL = `
SELECT ${AUDIT_COLS} FROM audit_log l LEFT JOIN users u ON u.id = l.actor_id
WHERE ($1::text IS NULL OR l.entity = $1) AND ($2::text IS NULL OR l.entity_id = $2) AND ($3::bigint IS NULL OR l.actor_id = $3)
ORDER BY l.at DESC, l.id DESC LIMIT $4 OFFSET $5`;

export const ADMIN_AREA_COLS = `a.id::int, a.level::text, a.parent_id::int, a.name_bn, a.name_en, a.slug, a.path, a.bbs_code, a.website,
  a.lat::float8, a.lon::float8, a.status::text, a.verified, a.evidence_level::text, a.production_eligible, a.evidence_source_id::int,
  es.key AS evidence_source_key, a.data_source_id::int, ds.key AS data_source_key, a.verification_notes, a.notes,
  to_char(a.last_reviewed_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS last_reviewed_at`;

/** $1 level|null $2 parent|null $3 q|null $4 evidence|null $5 eligible bool|null $6 scope path|null $7 limit $8 offset */
export const ADMIN_AREA_LIST_SQL = `
SELECT ${ADMIN_AREA_COLS}, count(*) OVER()::int AS total
FROM admin_areas a LEFT JOIN data_sources es ON es.id = a.evidence_source_id LEFT JOIN data_sources ds ON ds.id = a.data_source_id
WHERE a.level <> 'country'
  AND ($1::text IS NULL OR a.level::text = $1) AND ($2::bigint IS NULL OR a.parent_id = $2)
  AND ($3::text IS NULL OR a.name_bn ILIKE '%' || $3 || '%' OR a.name_en ILIKE '%' || $3 || '%' OR a.name_key LIKE elaka_latin_key($3) || '%')
  AND ($4::text IS NULL OR a.evidence_level::text = $4) AND ($5::boolean IS NULL OR a.production_eligible = $5)
  AND ($6::text IS NULL OR a.path = $6 OR a.path LIKE $6 || '/%')
ORDER BY a.path LIMIT $7 OFFSET $8`;

export const ADMIN_AREA_SQL = `
SELECT ${ADMIN_AREA_COLS} FROM admin_areas a LEFT JOIN data_sources es ON es.id = a.evidence_source_id LEFT JOIN data_sources ds ON ds.id = a.data_source_id
WHERE a.id = $1`;

export const ADMIN_PLACE_COLS = `p.id::int, p.public_id, p.slug, p.name_bn, p.name_en, p.short_name, c.key AS category_key, sc.key AS subcategory_key,
  p.ownership, p.division_id::int, p.district_id::int, p.upazila_id::int, p.union_id::int, p.city_corporation_id::int,
  p.address_bn, p.address_en, p.postcode, p.lat::float8, p.lon::float8, p.phones, p.email, p.website, p.established,
  p.description_bn, p.description_en, p.attributes, p.opening_hours, p.status::text, p.verification_status::text,
  p.evidence_level::text, p.production_eligible, p.evidence_source_id::int, es.key AS evidence_source_key, p.verification_notes,
  p.source_notes, to_char(p.updated_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS updated_at, a.path AS area_path`;

export const ADMIN_PLACE_JOINS = `
FROM places p JOIN categories c ON c.id = p.category_id LEFT JOIN categories sc ON sc.id = p.subcategory_id
LEFT JOIN data_sources es ON es.id = p.evidence_source_id
LEFT JOIN admin_areas a ON a.id = COALESCE(p.union_id, p.upazila_id, p.city_corporation_id, p.district_id, p.division_id)`;

/** $1 q|null $2 category|null $3 evidence|null $4 eligible|null $5 status|null $6 scope path|null $7 limit $8 offset */
export const ADMIN_PLACE_LIST_SQL = `
SELECT ${ADMIN_PLACE_COLS}, count(*) OVER()::int AS total ${ADMIN_PLACE_JOINS}
WHERE ($1::text IS NULL OR p.name_bn ILIKE '%' || $1 || '%' OR coalesce(p.name_en, '') ILIKE '%' || $1 || '%' OR p.public_id = $1)
  AND ($2::text IS NULL OR c.key = $2 OR sc.key = $2)
  AND ($3::text IS NULL OR p.evidence_level::text = $3) AND ($4::boolean IS NULL OR p.production_eligible = $4)
  AND ($5::text IS NULL OR p.status::text = $5)
  AND ($6::text IS NULL OR a.path = $6 OR a.path LIKE $6 || '/%')
ORDER BY p.updated_at DESC LIMIT $7 OFFSET $8`;

export const ADMIN_PLACE_SQL = `SELECT ${ADMIN_PLACE_COLS} ${ADMIN_PLACE_JOINS} WHERE p.id = $1`;

export const ADMIN_SOURCES_SQL = `
SELECT s.id, s.key, s.name, NULLIF(s.url, '') AS url, s.license, s.trust_level, s.source_type, s.organization,
       to_char(s.access_date, 'YYYY-MM-DD') AS access_date, to_char(s.publication_date, 'YYYY-MM-DD') AS publication_date,
       s.evidence_notes, s.active,
       (SELECT count(*)::int FROM admin_areas a WHERE a.evidence_source_id = s.id OR a.data_source_id = s.id)
       + (SELECT count(*)::int FROM places p WHERE p.evidence_source_id = s.id OR p.data_source_id = s.id) AS usage_count
FROM data_sources s ORDER BY s.trust_level DESC, s.key`;

/** $1 status|null $2 type|null $3 scope path|null $4 limit $5 offset */
export const ADMIN_CONTRIBUTIONS_SQL = `
SELECT c.id::int, c.type::text, c.status::text, c.priority, c.payload, c.evidence, c.lat::float8, c.lon::float8, c.confirmed_accurate,
       c.area_path, c.reviewer_note, p.slug AS target_place_slug, p.name_bn AS target_place_name, c.target_area_id::int,
       u.name AS submitter_name, u.id::int AS submitter_id,
       to_char(c.created_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS created_at, count(*) OVER()::int AS total
FROM contributions c JOIN users u ON u.id = c.user_id LEFT JOIN places p ON p.id = c.target_place_id
WHERE c.status <> 'draft' AND ($1::text IS NULL OR c.status::text = $1) AND ($2::text IS NULL OR c.type::text = $2)
  AND ($3::text IS NULL OR c.area_path = $3 OR c.area_path LIKE $3 || '/%')
ORDER BY CASE c.priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END, c.created_at
LIMIT $4 OFFSET $5`;

export const ADMIN_REVIEW_REPORTS_SQL = `
SELECT rr.id::int, rr.reason, rr.status, to_char(rr.created_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS created_at,
       r.id::int AS review_id, r.rating, r.body, r.status::text AS review_status, p.slug AS place_slug, p.name_bn AS place_name,
       au.name AS author_name, ru.name AS reporter_name
FROM review_reports rr JOIN reviews r ON r.id = rr.review_id JOIN places p ON p.id = r.place_id
JOIN users au ON au.id = r.user_id JOIN users ru ON ru.id = rr.reporter_id
WHERE ($1::text IS NULL OR rr.status = $1) ORDER BY rr.created_at LIMIT 200`;

/** $1 q|null $2 role|null $3 limit $4 offset */
export const ADMIN_USERS_SQL = `
SELECT u.id::int, u.name, u.phone, u.email, u.role::text, u.status, u.scope_area_id::int, a.path AS scope_path, u.points,
       to_char(u.created_at, 'YYYY-MM-DD') AS created_at, to_char(u.last_login_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS last_login_at,
       to_char(u.deletion_requested_at, 'YYYY-MM-DD') AS deletion_requested_at, count(*) OVER()::int AS total
FROM users u LEFT JOIN admin_areas a ON a.id = u.scope_area_id
WHERE ($1::text IS NULL OR u.name ILIKE '%' || $1 || '%' OR u.phone LIKE '%' || $1 || '%')
  AND ($2::text IS NULL OR u.role::text = $2)
ORDER BY u.created_at DESC LIMIT $3 OFFSET $4`;
