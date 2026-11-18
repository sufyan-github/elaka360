/**
 * Search from the browser through this site's route handlers (/api/search, /api/suggest), which forward to the API's
 * /v1/search: Typesense or Postgres on the NestJS API, SQLite full-text search on the edge API.
 */
import type { AdminAreaSummary, PlaceSummary } from '@elaka360/shared';

export interface SearchResult { areas: AdminAreaSummary[]; places: PlaceSummary[] }
export interface Suggestion { kind: 'area' | 'place'; name_bn: string; name_en: string; href_key: string; detail: string }

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(url, { signal });
  if (!res.ok) throw new Error(`${url}: ${res.status}`);
  return (await res.json()) as T;
}

export async function search(q: string, o: { type?: 'area' | 'place'; signal?: AbortSignal } = {}): Promise<SearchResult> {
  const qs = new URLSearchParams({ q, ...(o.type ? { type: o.type } : {}) });
  const r = await getJson<SearchResult>(`/api/search?${qs}`, o.signal);
  return { areas: r.areas ?? [], places: r.places ?? [] };
}

/** Prefix suggestions for the search box: areas first (by level), then places. */
export async function suggest(q: string, signal?: AbortSignal): Promise<Suggestion[]> {
  return (await getJson<{ items: Suggestion[] }>(`/api/suggest?q=${encodeURIComponent(q)}`, signal)).items ?? [];
}
