import 'server-only';
import type {
  AdminAreaSummary, AreaDetail, Category, EmergencyNumber, NationalStats, Paginated, Place, PlaceSummary,
} from '@elaka360/shared';

const API_URL = process.env.API_URL ?? 'http://localhost:4000';

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function get<T>(path: string, revalidate = 300): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { next: { revalidate } });
  if (!res.ok) throw new ApiError(res.status, `${res.status} ${path}`);
  return (await res.json()) as T;
}

const qs = (o: Record<string, string | number | undefined>) => {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(o)) if (v !== undefined && v !== '') p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : '';
};

export const api = {
  nationalStats: () => get<NationalStats>('/v1/stats/national'),
  areas: (level: string, parentId?: number, limit = 200) =>
    get<Paginated<AdminAreaSummary>>(`/v1/areas${qs({ level, parent_id: parentId, limit })}`),
  areaByPath: (path: string) => get<AreaDetail>(`/v1/areas/by-path${qs({ path })}`),
  categories: () => get<Category[]>('/v1/categories', 3600),
  places: (o: { areaId?: number; category?: string; q?: string; limit?: number }) =>
    get<Paginated<PlaceSummary>>(`/v1/places${qs({ area_id: o.areaId, category: o.category, q: o.q, limit: o.limit })}`),
  place: (slug: string) => get<Place>(`/v1/places/${encodeURIComponent(slug)}`),
  emergency: () => get<EmergencyNumber[]>('/v1/emergency-numbers', 3600),
  search: (q: string) => get<{ areas: AdminAreaSummary[]; places: PlaceSummary[] }>(`/v1/search${qs({ q })}`, 60),
};

/** URL of an area page in the web app. The country lives at /explore. */
export function areaHref(a: { path: string; level: string }): string {
  return a.level === 'country' ? '/explore' : `/${a.path}`;
}
