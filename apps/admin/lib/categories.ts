import 'server-only';
import type { Category } from '@elaka360/shared';
import type { CategoryOption } from '@/components/PlaceForm';
import { publicGet } from './api';

/** Categories (public taxonomy) flattened for selects; keys like "health" or "health.hospital". */
export async function categoryOptions(): Promise<{ options: CategoryOption[]; label: (key: string | null) => string; error: string | null }> {
  let tree: Category[] = [];
  let error: string | null = null;
  try {
    tree = await publicGet<Category[]>('/v1/categories');
  } catch (e) {
    error = (e as Error).message;
  }
  const options: CategoryOption[] = [];
  const names = new Map<string, string>();
  for (const c of tree) {
    names.set(c.key, c.name_bn);
    options.push({ key: c.key, label: `${c.name_bn} (সাধারণ)`, group: c.name_bn });
    for (const s of c.children ?? []) {
      names.set(s.key, s.name_bn);
      options.push({ key: s.key, label: `${s.name_bn} · ${s.name_en}`, group: c.name_bn });
    }
  }
  return { options, label: (k) => (k ? names.get(k) ?? k : '—'), error };
}
