import { BadRequestException } from '@nestjs/common';

export function intParam(value: string | undefined, name: string, opts: { min?: number; max?: number; def?: number } = {}): number | undefined {
  if (value === undefined || value === '') return opts.def;
  const n = Number(value);
  if (!Number.isInteger(n)) throw new BadRequestException(`${name} must be an integer`);
  if (opts.min !== undefined && n < opts.min) throw new BadRequestException(`${name} must be >= ${opts.min}`);
  if (opts.max !== undefined && n > opts.max) throw new BadRequestException(`${name} must be <= ${opts.max}`);
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
    if (!Number.isInteger(n) || n < 0) throw new BadRequestException('invalid cursor');
    return n;
  },
};

/** Normalise an area path from the URL: trims slashes, lower-cases, rejects odd characters. */
export function normalisePath(raw: string | undefined): string {
  const p = (raw ?? '').trim().replace(/^\/+|\/+$/g, '').toLowerCase();
  if (!p) return 'bangladesh';
  if (!/^[a-z0-9-]+(\/[a-z0-9-]+)*$/.test(p)) throw new BadRequestException('invalid path');
  return p;
}
