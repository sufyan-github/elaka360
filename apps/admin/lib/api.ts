import 'server-only';
import { cache } from 'react';
import { cookies, headers } from 'next/headers';
import { redirect } from 'next/navigation';
import type { Me, Problem } from '@elaka360/shared';
import { ACCESS_COOKIE, PATH_HEADER, REFRESH_COOKIE, safeNext } from './config';
import { API_URL, UNREACHABLE, apiFetchRaw, clearAuthCookies, refreshTokens, setAuthCookies } from './session';

/** An API error carrying the RFC 9457 problem `detail`, shown to staff as-is. */
export class ApiError extends Error {
  constructor(public status: number, public detail: string, public requestId?: string) {
    super(detail);
  }
}

async function problemOf(res: Response): Promise<ApiError> {
  let p: Partial<Problem> = {};
  try {
    p = (await res.json()) as Partial<Problem>;
  } catch { /* not JSON */ }
  const fieldErrors = p.errors ? ` (${Object.entries(p.errors).map(([k, v]) => `${k}: ${v}`).join('; ')})` : '';
  return new ApiError(res.status, `${p.detail ?? p.title ?? `HTTP ${res.status}`}${fieldErrors}`, p.request_id);
}

/** Where to send the browser to refresh its session and come back to the current page. */
async function refreshUrl(): Promise<string> {
  const h = await headers();
  return `/api/auth/refresh?next=${encodeURIComponent(safeNext(h.get(PATH_HEADER)))}`;
}

/**
 * Call the API as the signed-in staff member. Reads the access cookie and sends it as a Bearer token.
 * On 401 it refreshes once: inline when the refresh cookie is visible (only route handlers under /api
 * receive it, and those can rotate cookies), otherwise by redirecting the browser through
 * /api/auth/refresh, which sends it to /login if the session cannot be renewed.
 */
export async function adminFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const jar = await cookies();
  const call = (token: string | undefined) => {
    const h = new Headers(init.headers);
    if (token) h.set('authorization', `Bearer ${token}`);
    if (init.body && !h.has('content-type')) h.set('content-type', 'application/json');
    return apiFetchRaw(path, { ...init, headers: h });
  };
  const access = jar.get(ACCESS_COOKIE)?.value;
  const res = await call(access);
  if (res.status !== 401) return res;

  const rt = jar.get(REFRESH_COOKIE)?.value;
  if (rt) {
    const fresh = await refreshTokens(rt);
    if (fresh.ok) {
      setAuthCookies(jar, fresh.tokens);
      const again = await call(fresh.tokens.access_token);
      if (again.status !== 401) return again;
    } else if (fresh.reason === 'unreachable') {
      return res;
    }
    clearAuthCookies(jar);
    redirect('/login');
  }
  redirect(await refreshUrl());
}

/** GET a JSON resource; throws ApiError (rendered by the error boundary) on failure. */
export async function apiGet<T>(path: string): Promise<T> {
  const res = await adminFetch(path);
  if (!res.ok) throw await problemOf(res);
  return (await res.json()) as T;
}

/** Like apiGet, but returns the error instead of throwing (for optional panels). */
export async function apiTry<T>(path: string): Promise<{ data: T; error: null } | { data: null; error: ApiError }> {
  const res = await adminFetch(path);
  if (!res.ok) return { data: null, error: await problemOf(res) };
  return { data: (await res.json()) as T, error: null };
}

export type MutationResult<T = unknown> = { ok: true; data: T } | { ok: false; status: number; error: string };

/** Send a mutation; never throws for API errors so the form can show the problem `detail`. */
export async function apiSend<T = unknown>(method: 'POST' | 'PATCH' | 'DELETE', path: string, body?: unknown): Promise<MutationResult<T>> {
  const res = await adminFetch(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });
  if (!res.ok) {
    const e = await problemOf(res);
    return { ok: false, status: e.status, error: e.detail };
  }
  return { ok: true, data: (await res.json().catch(() => null)) as T };
}

/** Public (unauthenticated) API read, cached briefly. */
export async function publicGet<T>(path: string, revalidate = 300): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { next: { revalidate } });
  } catch {
    throw new ApiError(502, UNREACHABLE.detail);
  }
  if (!res.ok) throw await problemOf(res);
  return (await res.json()) as T;
}

/** The signed-in user, fetched once per request (layout and page share it). */
export const getMeResult = cache(() => apiTry<Me>('/v1/me'));

export async function getMe(): Promise<Me> {
  const r = await getMeResult();
  if (r.error) throw r.error;
  return r.data;
}

export function qs(o: Record<string, string | number | boolean | null | undefined>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(o)) if (v !== undefined && v !== null && v !== '') p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : '';
}
