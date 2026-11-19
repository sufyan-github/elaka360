import type { EvidenceLevel, Place, VerificationStatus } from './types';

/**
 * Public record status on the eight-step scale of the data policy, derived from three stored fields:
 * record status (active / inactive / closed / archived), verification status (unverified / pending / verified /
 * disputed) and evidence level (official / secondary / community / unverified).
 *
 * "Officially" and "source verified" say that a named source lists the record; they do not say it is operating today.
 * "Community verified" needs confirmations from trusted contributors, which the platform does not record yet, so no
 * record has it; an imported community dataset is "unverified".
 */
export type RecordStatus =
  | 'officially_verified' | 'source_verified' | 'field_verified' | 'community_verified'
  | 'unverified' | 'needs_review' | 'inactive_closed' | 'archived';

export function recordStatus(p: { evidence_level: EvidenceLevel; verification_status: VerificationStatus; status?: string | null }): RecordStatus {
  if (p.status === 'archived') return 'archived';
  if (p.status === 'inactive' || p.status === 'closed') return 'inactive_closed';
  if (p.verification_status === 'disputed' || p.verification_status === 'pending') return 'needs_review';
  if (p.verification_status === 'verified') return 'field_verified';
  if (p.evidence_level === 'official') return 'officially_verified';
  if (p.evidence_level === 'secondary') return 'source_verified';
  return 'unverified';
}

export type ConfidencePart = 'source' | 'corroboration' | 'location' | 'completeness' | 'recency';

export interface Confidence {
  /** 0–100. A transparent indicator for readers, not a certification. */
  score: number;
  parts: { key: ConfidencePart; points: number; max: number }[];
}

const SOURCE_POINTS: Record<EvidenceLevel, number> = { official: 40, secondary: 28, community: 12, unverified: 0 };

/**
 * Confidence from what the record itself shows (max points in brackets):
 *   source quality [40]  official 40, secondary 28, community 12, none 0
 *   corroboration [10]   listed by 2 sources 5, by 3 or more 10
 *   location [20]        a map point 20, else a written address 8
 *   completeness [20]    Bangla name, contact (phone / e-mail / website), address, sub-category: 5 each
 *   recency [10]         checked in the field within 1 year 10, within 3 years 5 (a source's own date is not a check)
 */
export function confidenceOf(p: Pick<Place, 'evidence_level' | 'lat' | 'address_bn' | 'address_en' | 'phones' | 'email' | 'website'
  | 'subcategory_key' | 'attributes' | 'last_verified_at'>, today: Date = new Date()): Confidence {
  const sources = Array.isArray(p.attributes?._sources) ? new Set(p.attributes._sources as unknown[]).size : 1;
  const address = Boolean(p.address_bn || p.address_en);
  const completeness = [!p.attributes?._name_bn_missing, p.phones.length > 0 || Boolean(p.email || p.website), address,
                        Boolean(p.subcategory_key)].filter(Boolean).length * 5;
  let recency = 0;
  if (p.last_verified_at) {
    const days = (today.getTime() - new Date(p.last_verified_at).getTime()) / 86_400_000;
    recency = days <= 366 ? 10 : days <= 3 * 366 ? 5 : 0;
  }
  const parts: Confidence['parts'] = [
    { key: 'source', points: SOURCE_POINTS[p.evidence_level] ?? 0, max: 40 },
    { key: 'corroboration', points: sources >= 3 ? 10 : sources === 2 ? 5 : 0, max: 10 },
    { key: 'location', points: p.lat !== null ? 20 : address ? 8 : 0, max: 20 },
    { key: 'completeness', points: completeness, max: 20 },
    { key: 'recency', points: recency, max: 10 },
  ];
  return { score: parts.reduce((s, x) => s + x.points, 0), parts };
}
