import {
  Building2, Bus, Church, GraduationCap, HeartPulse, Landmark, Leaf, MoreHorizontal, Palmtree, ShieldAlert, Store,
  Banknote, type LucideIcon,
} from 'lucide-react';

export const CATEGORY_ICON: Record<string, LucideIcon> = {
  education: GraduationCap,
  health: HeartPulse,
  government: Landmark,
  religious: Church,
  emergency: ShieldAlert,
  tourism: Palmtree,
  business: Store,
  transport: Bus,
  agriculture: Leaf,
  finance: Banknote,
  other: MoreHorizontal,
};

export function categoryIcon(key: string | null | undefined): LucideIcon {
  const top = (key ?? '').split('.')[0] ?? '';
  return CATEGORY_ICON[top] ?? Building2;
}

export function categoryColor(key: string | null | undefined): string {
  const top = (key ?? 'other').split('.')[0] || 'other';
  return `var(--e360-cat-${top}, var(--e360-secondary))`;
}
