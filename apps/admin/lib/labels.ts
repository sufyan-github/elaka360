import type { ContributionType, EvidenceLevel, UserRole } from '@elaka360/shared';

export const EVIDENCE_LEVELS: EvidenceLevel[] = ['official', 'secondary', 'community', 'unverified'];
/** Only these tiers may be published (production_eligible), and only with a named source. */
export const PUBLISHABLE: EvidenceLevel[] = ['official', 'secondary'];

export const ROLE_LABEL: Record<UserRole, { bn: string; en: string }> = {
  user: { bn: 'ব্যবহারকারী', en: 'User' },
  contributor: { bn: 'অবদানকারী', en: 'Contributor' },
  readonly_staff: { bn: 'শুধু-পড়া কর্মী', en: 'Read-only staff' },
  analyst: { bn: 'বিশ্লেষক', en: 'Analyst' },
  content_manager: { bn: 'কনটেন্ট ম্যানেজার', en: 'Content manager' },
  verifier: { bn: 'যাচাইকারী', en: 'Geographic verifier' },
  moderator: { bn: 'মডারেটর', en: 'Place moderator' },
  data_admin: { bn: 'ডেটা ম্যানেজার', en: 'Data manager' },
  national_admin: { bn: 'অ্যাডমিনিস্ট্রেটর', en: 'Administrator' },
  super_admin: { bn: 'সুপার অ্যাডমিন', en: 'Super admin' },
};
export const ROLES = Object.keys(ROLE_LABEL) as UserRole[];

/** Mirrors assignableRoles() in the API, only to narrow the select; the API decides. */
export function assignableRoles(managerRole: UserRole): UserRole[] {
  const staff: UserRole[] = ['readonly_staff', 'analyst', 'content_manager', 'verifier', 'moderator', 'data_admin', 'national_admin', 'super_admin'];
  if (managerRole === 'super_admin') return ['user', 'contributor', ...staff];
  if (managerRole === 'national_admin') return ['user', 'contributor', ...staff.filter((r) => r !== 'super_admin' && r !== 'national_admin')];
  return [];
}

export const CONTRIBUTION_TYPE_LABEL: Record<ContributionType, { bn: string; en: string }> = {
  new_place: { bn: 'নতুন স্থান', en: 'New place' },
  new_business: { bn: 'নতুন ব্যবসা', en: 'New business' },
  new_tourist_spot: { bn: 'নতুন পর্যটন স্থান', en: 'New tourist spot' },
  area_info: { bn: 'এলাকার তথ্য', en: 'Area info' },
  photo: { bn: 'ছবি', en: 'Photo' },
  correction: { bn: 'সংশোধন', en: 'Correction' },
  report: { bn: 'রিপোর্ট', en: 'Report' },
};
export const NEW_PLACE_TYPES: ContributionType[] = ['new_place', 'new_business', 'new_tourist_spot'];

export const SOURCE_TYPES = ['government_portal', 'gazette', 'census', 'census_aggregator', 'encyclopedia', 'news', 'institution_website',
  'community_dataset', 'project_reconciliation', 'field_survey', 'design_placeholder', 'none', 'unknown'] as const;
/** Trust levels 4–5 are reserved for these source types (API rule). */
export const HIGH_TRUST_TYPES = ['government_portal', 'gazette', 'census'];

export const PLACE_STATUSES = ['draft', 'active', 'inactive', 'closed', 'archived'] as const;
export const AREA_STATUSES = ['active', 'inactive', 'archived'] as const;
export const OWNERSHIP = ['public', 'private', 'ngo', 'trust', 'autonomous'] as const;
export const OWNERSHIP_LABEL: Record<string, string> = { public: 'সরকারি', private: 'বেসরকারি', ngo: 'এনজিও', trust: 'ট্রাস্ট', autonomous: 'স্বায়ত্তশাসিত' };
export const STATUS_LABEL: Record<string, string> = {
  draft: 'খসড়া', active: 'সক্রিয়', inactive: 'নিষ্ক্রিয়', closed: 'বন্ধ', archived: 'আর্কাইভ', suspended: 'স্থগিত',
  open: 'খোলা', upheld: 'বহাল', dismissed: 'খারিজ',
};

/** Search-engine result pages are not sources (the API rejects Google /search pages; this also catches /url and ?q= links). */
export function isSearchUrl(u: string): boolean {
  try {
    const url = new URL(u);
    const host = url.hostname.toLowerCase();
    const engine = /(^|\.)google\.[a-z.]+$/.test(host) || /^(www\.)?(bing\.com|duckduckgo\.com|search\.yahoo\.com)$/.test(host);
    return engine && (url.pathname.startsWith('/search') || url.pathname.startsWith('/url') || url.searchParams.has('q'));
  } catch {
    return false;
  }
}
