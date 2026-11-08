/** Domain types mirrored from db/migrations/0001_init.sql. */

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
  verified: boolean;
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
  production_eligible: boolean;
  notes: string | null;
  source: DataSourceRef | null;
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
  place_counts: Record<string, number>;
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
  breadcrumb: AdminAreaSummary[];
}

export interface EmergencyNumber extends Named {
  number: string;
  category: string;
  verified: boolean;
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
}

export interface Paginated<T> {
  items: T[];
  next_cursor: string | null;
}
