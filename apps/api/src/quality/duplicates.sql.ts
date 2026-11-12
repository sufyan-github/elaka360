/* Duplicate detection (plan thresholds: ≥95 blocks publication, 80–95 goes to review, <80 is new). */

/** Places that look like the given record. $1 name_bn, $2 name_en|null, $3 top category id, $4 lat|null, $5 lon|null, $6 exclude place id|null */
export const DUP_MATCH_SQL = `
WITH q AS (SELECT CASE WHEN $4::float8 IS NOT NULL AND $5::float8 IS NOT NULL
                       THEN ST_SetSRID(ST_MakePoint($5::float8, $4::float8), 4326)::geography END AS pt)
SELECT p.id::int, p.slug, p.name_bn, p.name_en,
       greatest(similarity(p.name_bn, $1),
                CASE WHEN $2::text IS NULL OR $2 = '' THEN 0 ELSE similarity(p.name_key, elaka_latin_key($2)) END)::float8 AS name_sim,
       CASE WHEN q.pt IS NULL OR p.geom IS NULL THEN NULL ELSE ST_Distance(p.geom, q.pt)::float8 END AS dist_m
FROM places p, q
WHERE p.status NOT IN ('archived', 'closed') AND p.category_id = $3 AND ($6::bigint IS NULL OR p.id <> $6)
  AND (p.name_bn % $1 OR ($2::text IS NOT NULL AND $2 <> '' AND p.name_key % elaka_latin_key($2)))
  AND (q.pt IS NULL OR p.geom IS NULL OR ST_DWithin(p.geom, q.pt, 500))
ORDER BY name_sim DESC, dist_m NULLS LAST, p.id   -- strongest first: thousands of registry places share name words
LIMIT 20`;

/** $1 status|null, $2 limit, $3 offset */
export const DUP_LIST_SQL = `
SELECT d.id::int, d.status::text, d.match_score::float8, d.match_detail, d.contribution_id::int,
       json_build_object('id', a.id, 'slug', a.slug, 'name_bn', a.name_bn, 'name_en', a.name_en, 'status', a.status,
                         'evidence_level', a.evidence_level, 'production_eligible', a.production_eligible, 'lat', a.lat::float8, 'lon', a.lon::float8) AS place_a,
       CASE WHEN b.id IS NULL THEN NULL ELSE json_build_object('id', b.id, 'slug', b.slug, 'name_bn', b.name_bn, 'name_en', b.name_en, 'status', b.status,
                         'evidence_level', b.evidence_level, 'production_eligible', b.production_eligible, 'lat', b.lat::float8, 'lon', b.lon::float8) END AS place_b,
       to_char(d.resolved_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS resolved_at, count(*) OVER()::int AS total
FROM duplicate_candidates d JOIN places a ON a.id = d.place_a_id LEFT JOIN places b ON b.id = d.place_b_id
WHERE ($1::text IS NULL OR d.status::text = $1)
ORDER BY d.match_score DESC, d.id DESC LIMIT $2 OFFSET $3`;

/** Open high-confidence candidates touching a place: publication is blocked while any exist. $1 place id */
export const DUP_BLOCKING_SQL = `
SELECT id::int, match_score::float8 FROM duplicate_candidates
WHERE status IN ('open', 'needs_more_review') AND match_score >= 95 AND (place_a_id = $1 OR place_b_id = $1)`;
