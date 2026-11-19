import { BadRequestException } from '@nestjs/common';

export function intParam(value: string | undefined, name: string, opts: { min?: number; max?: number; def?: number } = {}): number | undefined {
  if (value === undefined || value === '') return opts.def;
  if (!/^-?\d{1,16}$/.test(value)) throw new BadRequestException(`${name} must be an integer`);
  const n = Number(value);
  if (!Number.isSafeInteger(n)) throw new BadRequestException(`${name} must be an integer`);
  if (opts.min !== undefined && n < opts.min) throw new BadRequestException(`${name} must be >= ${opts.min}`);
  if (opts.max !== undefined && n > opts.max) throw new BadRequestException(`${name} must be <= ${opts.max}`);
  return n;
}

/** Positive database id from a path segment. Rejects overflow (finding C12) with 400, never 500. */
export function idParam(value: string | undefined, name = 'id'): number {
  const n = intParam(value, name, { min: 1 });
  if (n === undefined) throw new BadRequestException(`${name} is required`);
  return n;
}

export function floatParam(value: string | undefined, name: string, min: number, max: number): number {
  const n = Number(value);
  if (value === undefined || value === '' || !Number.isFinite(n) || n < min || n > max) {
    throw new BadRequestException(`${name} must be a number between ${min} and ${max}`);
  }
  return n;
}

/** Opaque offset cursor. */
export const cursor = {
  encode: (offset: number): string => Buffer.from(String(offset)).toString('base64url'),
  decode: (value: string | undefined): number => {
    if (!value) return 0;
    const n = Number(Buffer.from(value, 'base64url').toString());
    if (!Number.isInteger(n) || n < 0 || n > 1_000_000) throw new BadRequestException('invalid cursor');
    return n;
  },
};

/** Normalise an area path from the URL: trims slashes, lower-cases, rejects odd characters. */
export function normalisePath(raw: string | undefined): string {
  const p = (raw ?? '').trim().replace(/^\/+|\/+$/g, '').toLowerCase();
  if (!p) return 'bangladesh';
  if (p.length > 200 || !/^[a-z0-9-]+(\/[a-z0-9-]+)*$/.test(p)) throw new BadRequestException('invalid path');
  return p;
}

/** Free-text search input: trimmed, NFC-normalised, LIKE wildcards removed (finding C13). */
export function searchText(raw: string | undefined, { min = 2, max = 80 } = {}): string {
  const q = (raw ?? '').normalize('NFC').replace(/[%_\\]/g, ' ').replace(/\s+/g, ' ').trim();
  if (q.length < min) throw new BadRequestException(`q must be at least ${min} characters`);
  if (q.length > max) throw new BadRequestException('q is too long');
  return q;
}

/** Up to 5 search terms for token-AND matching. */
export function searchTerms(q: string): string[] {
  return [...new Set(q.toLowerCase().split(' ').filter(Boolean))].slice(0, 5);
}

/** Optional short text field from a JSON body. */
export function textField(body: Record<string, unknown>, key: string, opts: { max: number; required?: boolean; min?: number }): string | null {
  const v = body[key];
  if (v === undefined || v === null || v === '') {
    if (opts.required) throw new BadRequestException(`${key} is required`);
    return null;
  }
  if (typeof v !== 'string') throw new BadRequestException(`${key} must be text`);
  const s = v.normalize('NFC').trim();
  if (opts.min && s.length < opts.min) throw new BadRequestException(`${key} must be at least ${opts.min} characters`);
  if (s.length > opts.max) throw new BadRequestException(`${key} must be at most ${opts.max} characters`);
  return s || null;
}

export function enumField<T extends string>(body: Record<string, unknown>, key: string, allowed: readonly T[], required = true): T | null {
  const v = body[key];
  if (v === undefined || v === null || v === '') {
    if (required) throw new BadRequestException(`${key} is required`);
    return null;
  }
  if (typeof v !== 'string' || !allowed.includes(v as T)) throw new BadRequestException(`${key} must be one of ${allowed.join(', ')}`);
  return v as T;
}

export function urlField(v: unknown, key: string): string {
  if (typeof v !== 'string' || v.length > 500) throw new BadRequestException(`${key} must be a URL`);
  let u: URL;
  try {
    u = new URL(v);
  } catch {
    throw new BadRequestException(`${key} must be a URL`);
  }
  if (u.protocol !== 'https:' && u.protocol !== 'http:') throw new BadRequestException(`${key} must be http(s)`);
  if (/(^|\.)google\.[a-z.]+$/.test(u.hostname) && u.pathname.startsWith('/search')) throw new BadRequestException(`${key}: a search-results page is not a source`);
  return u.toString();
}

export function body(raw: unknown): Record<string, unknown> {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw new BadRequestException('JSON object body required');
  return raw as Record<string, unknown>;
}
