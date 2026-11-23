/** Errors and small helpers shared by the edge API's modules. */
export class HttpError extends Error {
  constructor(public status: number, public title: string, detail: string) { super(detail); }
}
export const bad = (detail: string) => new HttpError(400, 'Bad Request', detail);
export const notFound = (detail: string) => new HttpError(404, 'Not Found', detail);

/** SHA-256 as hex, first 32 characters (128 bits). */
export async function sha256(s: string) {
  const d = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, '0')).join('').slice(0, 32);
}

export function textField(b: Record<string, unknown>, key: string, o: { max: number; min?: number; required?: boolean }): string | null {
  const v = b[key];
  if (v === undefined || v === null || v === '') { if (o.required) throw bad(`${key} is required`); return null; }
  if (typeof v !== 'string') throw bad(`${key} must be text`);
  const s = v.normalize('NFC').trim();
  if (o.min && s.length < o.min) throw bad(`${key} must be at least ${o.min} characters`);
  if (s.length > o.max) throw bad(`${key} must be at most ${o.max} characters`);
  return s;
}

/** A JSON object body of at most `max` bytes. */
export async function jsonBody(req: Request, max = 16 * 1024): Promise<Record<string, unknown>> {
  const raw = await req.text();
  if (raw.length > max) throw new HttpError(413, 'Payload Too Large', 'request too large');
  let b: unknown;
  try { b = JSON.parse(raw || '{}'); } catch { throw bad('body must be JSON'); }
  if (!b || typeof b !== 'object' || Array.isArray(b)) throw bad('body must be a JSON object');
  return b as Record<string, unknown>;
}
