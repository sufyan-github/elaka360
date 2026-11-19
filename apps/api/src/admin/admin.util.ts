import { BadRequestException } from '@nestjs/common';
import type { EvidenceLevel } from '@elaka360/shared';
import type { Queryable } from '../db/db.service';
import { cursor, intParam } from '../common/params';

export const EVIDENCE: EvidenceLevel[] = ['official', 'secondary', 'community', 'unverified'];

export function page(limitRaw?: string, cur?: string, max = 200) {
  return { limit: intParam(limitRaw, 'limit', { min: 1, max, def: 50 })!, offset: cursor.decode(cur) };
}

export function paged<T extends { total?: number }>(rows: T[], limit: number, offset: number) {
  const total = rows[0]?.total ?? 0;
  return { items: rows.map(({ total: _t, ...r }) => r), total, next_cursor: offset + rows.length < total ? cursor.encode(offset + limit) : null };
}

export function boolQuery(v?: string): boolean | null {
  if (v === undefined || v === '') return null;
  if (v === 'true') return true;
  if (v === 'false') return false;
  throw new BadRequestException('expected true or false');
}

export interface VerifyInput {
  evidence_level: EvidenceLevel;
  evidence_source_id: number | null;
  production_eligible: boolean;
  verification_notes: string;
}

/** Validate a verification decision against the trust policy before the DB constraint sees it. */
export async function readVerify(q: Queryable, b: Record<string, unknown>): Promise<VerifyInput> {
  const level = b.evidence_level;
  if (typeof level !== 'string' || !EVIDENCE.includes(level as EvidenceLevel)) throw new BadRequestException(`evidence_level must be one of ${EVIDENCE.join(', ')}`);
  const srcId = b.evidence_source_id == null || b.evidence_source_id === '' ? null : intParam(String(b.evidence_source_id), 'evidence_source_id', { min: 1 })!;
  const notes = typeof b.verification_notes === 'string' ? b.verification_notes.normalize('NFC').trim() : '';
  if (notes.length < 5 || notes.length > 1000) throw new BadRequestException('verification_notes (5–1000 characters) must say what was checked');
  const eligible = b.production_eligible === true;
  if ((level === 'official' || level === 'secondary') && !srcId) throw new BadRequestException('official or secondary evidence needs a source');
  if (eligible && !(level === 'official' || level === 'secondary')) throw new BadRequestException('only official or secondary evidence can be published');
  if (srcId) {
    const src = await q.one<{ active: boolean; url: string | null; trust_level: number }>('SELECT active, NULLIF(url, \'\') AS url, trust_level FROM data_sources WHERE id = $1', [srcId]);
    if (!src || !src.active) throw new BadRequestException('unknown or inactive source');
    if (eligible && !src.url) throw new BadRequestException('a published record needs a source with a URL');
    if (level === 'official' && src.trust_level < 4) throw new BadRequestException('official evidence needs a source with trust level 4 or 5 (government, BBS, gazette)');
  }
  return { evidence_level: level as EvidenceLevel, evidence_source_id: srcId, production_eligible: eligible, verification_notes: notes };
}
