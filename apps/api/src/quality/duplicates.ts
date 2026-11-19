import type { Queryable } from '../db/db.service';
import { DUP_MATCH_SQL } from './duplicates.sql';

export const REVIEW_THRESHOLD = 80;
export const BLOCK_THRESHOLD = 95;
const RADIUS_M = 500;

export interface DupInput { name_bn: string; name_en?: string | null; categoryId: number; lat?: number | null; lon?: number | null; excludeId?: number | null }
export interface DupMatch { id: number; slug: string; name_bn: string; name_en: string | null; score: number; name_sim: number; dist_m: number | null }

/**
 * Score = 100 × (0.6 × name similarity + 0.4 × closeness within 500 m). Without coordinates on either
 * side the name alone counts, capped at 90 so a name match never blocks publication by itself.
 */
export function score(nameSim: number, distM: number | null): number {
  if (distM === null) return Math.round(Math.min(90, 100 * nameSim) * 10) / 10;
  const close = Math.max(0, 1 - distM / RADIUS_M);
  return Math.round(100 * (0.6 * nameSim + 0.4 * close) * 10) / 10;
}

export async function findDuplicates(q: Queryable, i: DupInput): Promise<DupMatch[]> {
  const rows = await q.many<{ id: number; slug: string; name_bn: string; name_en: string | null; name_sim: number; dist_m: number | null }>(
    DUP_MATCH_SQL, [i.name_bn, i.name_en ?? null, i.categoryId, i.lat ?? null, i.lon ?? null, i.excludeId ?? null]);
  return rows
    .map((r) => ({ ...r, score: score(r.name_sim, r.dist_m) }))
    .filter((r) => r.score >= REVIEW_THRESHOLD)
    .sort((a, b) => b.score - a.score);
}

/** Store review-worthy matches (skips pairs already recorded). */
export async function recordDuplicates(q: Queryable, matches: DupMatch[], o: { placeId?: number; contributionId?: number }) {
  for (const m of matches) {
    await q.many(
      `INSERT INTO duplicate_candidates(place_a_id, place_b_id, contribution_id, match_score, match_detail)
       SELECT $1, $2, $3, $4, $5
       WHERE NOT EXISTS (SELECT 1 FROM duplicate_candidates WHERE place_a_id = $1 AND place_b_id IS NOT DISTINCT FROM $2
                         AND contribution_id IS NOT DISTINCT FROM $3)`,
      [m.id, o.placeId ?? null, o.contributionId ?? null, m.score, JSON.stringify({ name_similarity: m.name_sim, distance_m: m.dist_m })]);
  }
}
