import type { AdminLevel, AuditEntry, Contribution, ContributionStatus, ContributionType, EvidenceLevel, UserRole } from '@elaka360/shared';

/** Read shapes of the admin endpoints (see apps/api/src/admin/admin.sql.ts). */

export interface Page<T> { items: T[]; total: number; next_cursor: string | null }

export interface AdminAreaRow {
  id: number; level: AdminLevel; parent_id: number | null; name_bn: string; name_en: string; slug: string; path: string;
  bbs_code: string | null; website: string | null; lat: number | null; lon: number | null; status: string; verified: boolean;
  evidence_level: EvidenceLevel; production_eligible: boolean; evidence_source_id: number | null; evidence_source_key: string | null;
  data_source_id: number | null; data_source_key: string | null; verification_notes: string | null; notes: string | null;
  last_reviewed_at: string | null;
}

export interface AdminAreaDetail extends AdminAreaRow {
  children: { level: AdminLevel; n: number; public: number }[];
  history: AuditEntry[];
}

export interface AdminPlaceRow {
  id: number; public_id: string; slug: string; name_bn: string; name_en: string | null; short_name: string | null;
  category_key: string; subcategory_key: string | null; ownership: string | null;
  division_id: number | null; district_id: number | null; upazila_id: number | null; union_id: number | null; city_corporation_id: number | null;
  address_bn: string | null; address_en: string | null; postcode: string | null; lat: number | null; lon: number | null;
  phones: string[]; email: string | null; website: string | null; established: string | null;
  description_bn: string | null; description_en: string | null; attributes: Record<string, unknown>; opening_hours: Record<string, unknown> | null;
  status: string; verification_status: string; evidence_level: EvidenceLevel; production_eligible: boolean;
  evidence_source_id: number | null; evidence_source_key: string | null; verification_notes: string | null; source_notes: string | null;
  updated_at: string; area_path: string | null;
}

export interface AdminPlaceDetail extends AdminPlaceRow { history: AuditEntry[] }

export interface ContributionRow {
  id: number; type: ContributionType; status: ContributionStatus; priority: string; payload: Record<string, unknown>;
  evidence: { url: string; note?: string }[]; lat: number | null; lon: number | null; confirmed_accurate: boolean;
  area_path: string | null; reviewer_note: string | null; target_place_slug: string | null; target_place_name: string | null;
  target_area_id: number | null; submitter_name: string; submitter_id: number; created_at: string;
}

export type ContributionDetail = Contribution;

export interface ReviewReportRow {
  id: number; reason: string | null; status: string; created_at: string; review_id: number; rating: number; body: string | null;
  review_status: string; place_slug: string; place_name: string; author_name: string; reporter_name: string;
}

export interface UserRow {
  id: number; name: string; phone: string | null; email: string | null; role: UserRole; status: string; scope_area_id: number | null;
  scope_path: string | null; points: number; created_at: string; last_login_at: string | null; deletion_requested_at: string | null;
}

export interface AreaOption { id: number; name_bn: string; name_en: string; production_eligible: boolean; evidence_level: EvidenceLevel }
