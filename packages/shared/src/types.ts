/** Domain types mirrored from db/migrations/0001–0005 (read shapes returned by the API). */

/** Evidence tiers — see docs/data/DATA_TRUST_POLICY.md. */
export type EvidenceLevel = 'official' | 'secondary' | 'community' | 'unverified';

export type AdminLevel =
  | 'country' | 'division' | 'district' | 'upazila' | 'city_corporation'
  | 'pourashava' | 'union' | 'ward' | 'mouza' | 'village' | 'thana';

export interface Named {
  name_bn: string;
  name_en: string;
}

export interface AdminAreaSummary extends Named {
  id: number;
  level: AdminLevel;
  parent_id: number | null;
  slug: string;
  path: string;
  /** Legacy flag: true only for official (Tier 1) evidence. Use evidence_level for display. */
  verified: boolean;
  evidence_level: EvidenceLevel;
  production_eligible: boolean;
}

export interface AdminArea extends AdminAreaSummary {
  bbs_code: string | null;
  website: string | null;
  lat: number | null;
  lon: number | null;
  area_km2: number | null;
  area_basis: string | null;
  population_2022: number | null;
  population_basis: string | null;
  wards_count: number | null;
  established: string | null;
  notes: string | null;
  source: DataSourceRef | null;
  evidence_source: DataSourceRef | null;
  verification_notes: string | null;
  last_reviewed_at: string | null;
}

export interface DataSourceRef {
  key: string;
  name: string;
  url: string | null;
}

/** Child counts per level, e.g. { district: 8, upazila: 67 } */
export type LevelCounts = Partial<Record<AdminLevel, number>>;

export interface AreaDetail {
  area: AdminArea;
  breadcrumb: AdminAreaSummary[];
  children: AdminAreaSummary[];
  descendant_counts: LevelCounts;
  /** Descendants that exist but are not public yet (awaiting verification), per level. */
  pending_counts: LevelCounts;
  place_counts: Record<string, number>;
}

export interface AreaStats {
  area_id: number;
  descendant_counts: LevelCounts;
  pending_counts: LevelCounts;
  place_counts: Record<string, number>;
  population_2022: number | null;
  population_basis: string | null;
  area_km2: number | null;
  area_basis: string | null;
  /** How the numbers were counted. */
  inclusion_rule: string;
}

export interface AreaTreeNode extends AdminAreaSummary {
  children?: AreaTreeNode[];
}

export interface LocateResult {
  lat: number;
  lon: number;
  /** Most specific public area whose boundary contains the point (districts have boundaries today). */
  area: AdminAreaSummary | null;
  breadcrumb: AdminAreaSummary[];
  /** Which levels have boundary data; finer levels cannot be resolved yet. */
  resolved_levels: AdminLevel[];
}

export interface Category extends Named {
  id: number;
  key: string;
  parent_id: number | null;
  icon: string | null;
  color: string | null;
  sort_order: number;
  children?: Category[];
}

export type VerificationStatus = 'unverified' | 'pending' | 'verified' | 'disputed';

export interface PlaceSummary {
  public_id: string;
  slug: string;
  name_bn: string;
  name_en: string | null;
  category_key: string;
  subcategory_key: string | null;
  area_label_bn: string | null;
  area_label_en: string | null;
  lat: number | null;
  lon: number | null;
  verification_status: VerificationStatus;
  evidence_level: EvidenceLevel;
  production_eligible: boolean;
  distance_m?: number;
}

export interface Place extends PlaceSummary {
  short_name: string | null;
  ownership: string | null;
  address_bn: string | null;
  address_en: string | null;
  postcode: string | null;
  phones: string[];
  email: string | null;
  website: string | null;
  established: string | null;
  attributes: Record<string, unknown>;
  description_bn: string | null;
  description_en: string | null;
  source: DataSourceRef | null;
  source_notes: string | null;
  last_verified_at: string | null;
  opening_hours: Record<string, unknown> | null;
  rating_avg: number | null;
  rating_count: number;
  breadcrumb: AdminAreaSummary[];
}

export interface EmergencyNumber extends Named {
  number: string;
  category: string;
  verified: boolean;
  evidence_level: EvidenceLevel;
  notes: string | null;
}

export interface NationalStats {
  division: number;
  district: number;
  upazila: number;
  union: number;
  city_corporation: number;
  pourashava: number;
  places: number;
  verified_places: number;
  /** How the numbers were counted (public = production-eligible records only, unless configured otherwise). */
  inclusion_rule: string;
}

export interface Paginated<T> {
  items: T[];
  next_cursor: string | null;
}

/* ---------- accounts ---------- */

export type UserRole =
  | 'user' | 'contributor' | 'moderator' | 'data_admin' | 'national_admin' | 'super_admin'
  | 'verifier' | 'content_manager' | 'analyst' | 'readonly_staff';

export interface Me {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  role: UserRole;
  points: number;
  level: number;
  home_area_id: number | null;
  scope_area_id: number | null;
  profile_public: boolean;
  created_at: string;
  deletion_requested_at: string | null;
  permissions: string[];
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: Me;
}

/* ---------- reviews, saved, contributions ---------- */

export interface Review {
  id: number;
  place_slug: string;
  rating: number;
  body: string | null;
  author_name: string;
  is_own: boolean;
  created_at: string;
  updated_at: string;
}

export interface SavedItem {
  id: number;
  collection_id: number | null;
  created_at: string;
  place: PlaceSummary | null;
  area: AdminAreaSummary | null;
}

export interface Collection {
  id: number;
  name: string;
  description: string | null;
  item_count: number;
  created_at: string;
}

export type ContributionType = 'new_place' | 'new_business' | 'new_tourist_spot' | 'area_info' | 'photo' | 'correction' | 'report';
export type ContributionStatus = 'draft' | 'new' | 'in_review' | 'needs_changes' | 'approved' | 'rejected';

export interface ContributionEvidence {
  url: string;
  note?: string;
}

export interface Contribution {
  id: number;
  type: ContributionType;
  status: ContributionStatus;
  target_place_slug: string | null;
  target_area_id: number | null;
  payload: Record<string, unknown>;
  evidence: ContributionEvidence[];
  lat: number | null;
  lon: number | null;
  confirmed_accurate: boolean;
  reviewer_note: string | null;
  created_at: string;
  updated_at: string;
  reviewed_at: string | null;
  events?: ContributionEvent[];
}

export interface ContributionEvent {
  from_status: ContributionStatus | null;
  to_status: ContributionStatus;
  note: string | null;
  actor_name: string | null;
  at: string;
}

/* ---------- admin ---------- */

export interface DataSource {
  id: number;
  key: string;
  name: string;
  url: string | null;
  license: string | null;
  trust_level: number;
  source_type: string;
  organization: string | null;
  access_date: string | null;
  publication_date: string | null;
  evidence_notes: string | null;
  active: boolean;
  usage_count?: number;
}

export interface AdminStats {
  areas_total: number;
  areas_public: number;
  areas_by_evidence: Record<EvidenceLevel, number>;
  places_total: number;
  places_public: number;
  places_by_evidence: Record<EvidenceLevel, number>;
  contributions_pending: number;
  review_reports_open: number;
  duplicate_candidates_open: number;
  quality_issues_open: number;
  users_active_30d: number;
  recent_activity: AuditEntry[];
}

export interface AuditEntry {
  id: number;
  actor_id: number | null;
  actor_name: string | null;
  action: string;
  entity: string;
  entity_id: string;
  before: unknown;
  after: unknown;
  reason: string | null;
  request_id: string | null;
  at: string;
}

/** RFC 9457 problem details, returned for every API error. */
export interface Problem {
  type: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
  request_id?: string;
  errors?: Record<string, string>;
}
