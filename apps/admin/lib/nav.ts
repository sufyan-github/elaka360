export interface NavItem { href: string; bn: string; en: string; perm: string; icon: string }

/** Sidebar entries; each is shown only when the user holds `perm`. */
export const NAV: NavItem[] = [
  { href: '/', bn: 'ড্যাশবোর্ড', en: 'Dashboard', perm: 'stats.read', icon: 'dashboard' },
  { href: '/verification', bn: 'যাচাই কেন্দ্র', en: 'Verification centre', perm: 'verify', icon: 'verify' },
  { href: '/areas', bn: 'এলাকা', en: 'Areas', perm: 'areas.read', icon: 'areas' },
  { href: '/places', bn: 'স্থান', en: 'Places', perm: 'places.read', icon: 'places' },
  { href: '/moderation', bn: 'মডারেশন', en: 'Moderation', perm: 'contributions.moderate', icon: 'moderation' },
  { href: '/review-reports', bn: 'রিভিউ রিপোর্ট', en: 'Review reports', perm: 'reviews.moderate', icon: 'reports' },
  { href: '/sources', bn: 'উৎস', en: 'Sources', perm: 'sources.read', icon: 'sources' },
  { href: '/audit', bn: 'অডিট লগ', en: 'Audit log', perm: 'audit.read', icon: 'audit' },
  { href: '/users', bn: 'ব্যবহারকারী', en: 'Users', perm: 'users.manage', icon: 'users' },
];

/** "verify" is a virtual permission: either areas.verify or places.verify. */
export function has(perms: readonly string[], perm: string): boolean {
  if (perm === 'verify') return perms.includes('areas.verify') || perms.includes('places.verify');
  return perms.includes(perm);
}
