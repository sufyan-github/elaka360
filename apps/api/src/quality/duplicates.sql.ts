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

/** $1 status|null, $2 limit, $3 offset, $4 place id|null (pairs that involve this place) */
export const DUP_LIST_SQL = `
SELECT d.id::int, d.status::text, d.match_score::float8, d.match_detail, d.contribution_id::int,
       json_build_object('id', a.id, 'slug', a.slug, 'name_bn', a.name_bn, 'name_en', a.name_en, 'status', a.status,
                         'evidence_level', a.evidence_level, 'production_eligible', a.production_eligible, 'lat', a.lat::float8, 'lon', a.lon::float8) AS place_a,
       CASE WHEN b.id IS NULL THEN NULL ELSE json_build_object('id', b.id, 'slug', b.slug, 'name_bn', b.name_bn, 'name_en', b.name_en, 'status', b.status,
                         'evidence_level', b.evidence_level, 'production_eligible', b.production_eligible, 'lat', b.lat::float8, 'lon', b.lon::float8) END AS place_b,
       to_char(d.resolved_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS resolved_at, count(*) OVER()::int AS total
FROM duplicate_candidates d JOIN places a ON a.id = d.place_a_id LEFT JOIN places b ON b.id = d.place_b_id
WHERE ($1::text IS NULL OR d.status::text = $1) AND ($4::bigint IS NULL OR d.place_a_id = $4 OR d.place_b_id = $4)
ORDER BY d.match_score DESC, d.id DESC LIMIT $2 OFFSET $3`;

/** Open high-confidence candidates touching a place: publication is blocked while any exist. $1 place id */
export const DUP_BLOCKING_SQL = `
SELECT id::int, match_score::float8 FROM duplicate_candidates
WHERE status IN ('open', 'needs_more_review') AND match_score >= 95 AND (place_a_id = $1 OR place_b_id = $1)`;

/**
 * Whole-database duplicate scan (apps/api/src/cli/duplicate-scan.ts), set-based so it runs on all ~560k places.
 * Same score as score() in duplicates.ts: 100 × (0.6 × name similarity + 0.4 × closeness within 500 m), or the name
 * alone capped at 90 when either record has no point. Blocking keeps it tractable: a pair must share the category and
 * the first 4 letters of the Latin name key or the first 3 of the Bangla name, and lie in neighbouring 0.01° cells
 * (pairs with a point) or in the same union / city corporation / upazila (pairs where a point is missing). Names that
 * both carry numbers must carry the same numbers (numbered ATMs, wards and units are distinct).
 * Only pairs scoring ≥ $1 that are not recorded yet (in either order, any status) are inserted; nothing is merged.
 */
export const DUP_BULK_SCAN_SQL = `
WITH p AS (
  SELECT id, category_id, geom, name_bn, name_key, phones,
         floor(lon / 0.01)::int AS cx, floor(lat / 0.01)::int AS cy,
         NULLIF(left(name_key, 4), '') AS kk, NULLIF(left(name_bn, 3), '') AS kb,
         coalesce('u' || union_id, 'c' || city_corporation_id, 'z' || upazila_id) AS area,
         ARRAY(SELECT DISTINCT m[1] FROM regexp_matches(translate(coalesce(name_en, '') || ' ' || name_bn, '০১২৩৪৫৬৭৮৯', '0123456789'),
                                                        '(\\d+)', 'g') m ORDER BY 1) AS nums
  FROM places WHERE status NOT IN ('archived', 'closed')
),
cand AS (   -- each record against its own and the 8 neighbouring cells: a hash join on small buckets
  SELECT a.id AS a, b.id AS b FROM p a CROSS JOIN generate_series(-1, 1) dx CROSS JOIN generate_series(-1, 1) dy
  JOIN p b ON b.category_id = a.category_id AND b.kk = a.kk AND b.cx = a.cx + dx AND b.cy = a.cy + dy AND b.id > a.id
  WHERE ST_DWithin(a.geom, b.geom, 500)
  UNION
  SELECT a.id, b.id FROM p a CROSS JOIN generate_series(-1, 1) dx CROSS JOIN generate_series(-1, 1) dy
  JOIN p b ON b.category_id = a.category_id AND b.kb = a.kb AND b.cx = a.cx + dx AND b.cy = a.cy + dy AND b.id > a.id
  WHERE ST_DWithin(a.geom, b.geom, 500)
  UNION
  SELECT a.id, b.id FROM p a JOIN p b ON b.category_id = a.category_id AND b.area = a.area AND b.kk = a.kk AND b.id > a.id
  WHERE a.geom IS NULL OR b.geom IS NULL
  UNION
  SELECT a.id, b.id FROM p a JOIN p b ON b.category_id = a.category_id AND b.area = a.area AND b.kb = a.kb AND b.id > a.id
  WHERE a.geom IS NULL OR b.geom IS NULL
),
scored AS (
  SELECT c.a, c.b, s.sim, s.dist,
         CASE WHEN s.dist IS NULL THEN least(90, 100 * s.sim)
              ELSE 100 * (0.6 * s.sim + 0.4 * greatest(0, 1 - s.dist / 500)) END AS score,
         (pa.phones && pb.phones) AS same_phone
  FROM cand c JOIN p pa ON pa.id = c.a JOIN p pb ON pb.id = c.b
  CROSS JOIN LATERAL (SELECT greatest(similarity(pa.name_bn, pb.name_bn),
                                      CASE WHEN pa.name_key <> '' AND pb.name_key <> '' THEN similarity(pa.name_key, pb.name_key) ELSE 0 END)::float8 AS sim,
                             CASE WHEN pa.geom IS NULL OR pb.geom IS NULL THEN NULL ELSE ST_Distance(pa.geom, pb.geom)::float8 END AS dist) s
  -- numbered units ("ATM - 1" / "ATM - 2", "Ward 3" / "Ward 4") are different things, not duplicates
  WHERE cardinality(pa.nums) = 0 OR cardinality(pb.nums) = 0 OR pa.nums = pb.nums
)
INSERT INTO duplicate_candidates(place_a_id, place_b_id, match_score, match_detail)
SELECT a, b, round(score::numeric, 1),
       json_build_object('name_similarity', round(sim::numeric, 3), 'distance_m', round(dist::numeric), 'same_phone', coalesce(same_phone, false),
                         'method', 'bulk_scan')
FROM scored
WHERE score >= $1
  AND NOT EXISTS (SELECT 1 FROM duplicate_candidates d
                  WHERE (d.place_a_id = scored.a AND d.place_b_id = scored.b) OR (d.place_a_id = scored.b AND d.place_b_id = scored.a))
ORDER BY a, b`;
