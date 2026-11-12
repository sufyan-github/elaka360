import 'server-only';
import { apiFetch } from './edge';
import { cookies } from 'next/headers';
import type { Me } from '@elaka360/shared';
import { API_URL } from './api';
import { AT_COOKIE } from './http';

/** Access token from the httpOnly cookie (refreshed by middleware.ts when it expires). */
export async function accessToken(): Promise<string | undefined> {
  return (await cookies()).get(AT_COOKIE)?.value;
}

/** The signed-in user, or null. Never cached. */
export async function currentUser(): Promise<Me | null> {
  const token = await accessToken();
  if (!token) return null;
  try {
    const res = await apiFetch(`${API_URL}/v1/me`, { headers: { Authorization: `Bearer ${token}` }, cache: 'no-store', signal: AbortSignal.timeout(5000) });
    return res.ok ? ((await res.json()) as Me) : null;
  } catch {
    return null;
  }
}

/** Authenticated GET for server components. */
export async function authedGet<T>(path: string): Promise<T | null> {
  const token = await accessToken();
  if (!token) return null;
  try {
    const res = await apiFetch(`${API_URL}${path}`, { headers: { Authorization: `Bearer ${token}` }, cache: 'no-store', signal: AbortSignal.timeout(5000) });
    return res.ok ? ((await res.json()) as T) : null;
  } catch {
    return null;
  }
}
