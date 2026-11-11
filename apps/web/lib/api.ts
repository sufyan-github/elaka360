import 'server-only';
import type {
  AdminAreaSummary, AreaDetail, AreaStats, AreaTreeNode, Category, EmergencyNumber, Locale, NationalStats, Paginated, Place, PlaceSummary, Problem, Review,
} from '@elaka360/shared';
import { nameOf } from '@elaka360/shared';

export const API_URL = process.env.API_URL ?? 'http://localhost:4000';
const TIMEOUT_MS = Number(process.env.API_TIMEOUT_MS ?? 5000);

export class ApiError extends Error {
  constructor(public status: number, message: string, public problem?: Problem) {
    super(message);
  }
}

/** Server-side GET with a timeout (finding C3) and problem-details errors. */
async function get<T>(path: string, revalidate: number | false = 300, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      signal: AbortSignal.timeout(TIMEOUT_MS),
      ...(revalidate === false ? { cache: 'no-store' } : { next: { revalidate } }),
    });
  } catch (e) {
    throw new ApiError(503, `API unreachable: ${(e as Error).name}`);
  }
  if (!res.ok) {
    const problem = (await res.json().catch(() => undefined)) as Problem | undefined;
    throw new ApiError(res.status, problem?.detail ?? `${res.status} ${path}`, problem);
  }
  return (await res.json()) as T;
}

const qs = (o: Record<string, string | number | undefined | null>) => {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(o)) if (v !== undefined && v !== null && v !== '') p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : '';
};

export type PlacePage = Paginated<PlaceSummary> & { total: number };
export interface SearchResult { engine: string; areas: AdminAreaSummary[]; places: PlaceSummary[] }

export const api = {
  nationalStats: () => get<NationalStats>('/v1/stats/national'),
  areaStats: (id: number) => get<AreaStats>(`/v1/areas/${id}/stats`),
  tree: (rootId = 1, depth = 2) => get<AreaTreeNode>(`/v1/areas/tree${qs({ root_id: rootId, depth })}`, 3600),
  areas: (level: string, parentId?: number, limit = 200) =>
    get<Paginated<AdminAreaSummary>>(`/v1/areas${qs({ level, parent_id: parentId, limit })}`),
  areaByPath: (path: string) => get<AreaDetail>(`/v1/areas/by-path${qs({ path })}`),
  categories: () => get<Category[]>('/v1/categories', 3600),
  places: (o: { areaId?: number; category?: string; q?: string; limit?: number; cursor?: string }) =>
    get<PlacePage>(`/v1/places${qs({ area_id: o.areaId, category: o.category, q: o.q, limit: o.limit, cursor: o.cursor })}`),
  place: (slug: string) => get<Place>(`/v1/places/${encodeURIComponent(slug)}`),
  /** Public reviews (anonymous view), cached briefly so place pages stay ISR. */
  reviews: (slug: string) => get<Paginated<Review>>(`/v1/places/${encodeURIComponent(slug)}/reviews`, 60),
  emergency: () => get<EmergencyNumber[]>('/v1/emergency-numbers', 3600),
  search: (q: string, o: { type?: string; level?: string; category?: string } = {}) =>
    get<SearchResult>(`/v1/search${qs({ q, ...o })}`, 60),
};

/** Map a category key ("health.hospital") to its name in the given locale using the taxonomy. */
export function categoryName(categories: Category[], key: string | null | undefined, locale: Locale = 'bn'): string | null {
  if (!key) return null;
  for (const c of categories) {
    if (c.key === key) return nameOf(c, locale);
    const sub = c.children?.find((s) => s.key === key);
    if (sub) return nameOf(sub, locale);
  }
  return null;
}
