/**
 * Accounts and contributions on the edge (Turso): email sign-in with a one-time code, sessions, contributions and a
 * small moderation queue. Same request and response shapes as the NestJS API (apps/api), so the website works with
 * either. Tables: db/d1/schema.sql ("accounts and contributions"); the data sync never touches them.
 *
 * Email: Resend (RESEND_API_KEY, MAIL_FROM). Without a key, codes are refused (503), except MAIL_DEV=1 (local
 * development only), where the code comes back in the response as `dev_code`. Codes and tokens are stored only as
 * salted hashes and never logged.
 */
import type { Contribution, ContributionStatus, Me, UserRole } from '@elaka360/shared';
import { HttpError, bad, jsonBody, notFound, sha256, textField } from './http';

export interface AccountEnv {
  RESEND_API_KEY?: string;
  MAIL_FROM?: string;
  MAIL_DEV?: string;
  AUTH_SECRET?: string;
  EDGE_SHARED_SECRET?: string;
  APP_VERSION?: string;
}
interface Stmt {
  bind(...v: unknown[]): Stmt;
  first<T = Record<string, unknown>>(): Promise<T | null>;
  all<T = Record<string, unknown>>(): Promise<{ results: T[] }>;
  run(): Promise<unknown>;
}
interface Db { prepare(sql: string): Stmt }
export interface Ctx { req: Request; env: AccountEnv; db: Db; ip: string | null; url: URL; m: RegExpMatchArray }
type Handler = (c: Ctx) => Promise<unknown>;

const CODE_TTL_S = 10 * 60;
const SESSION_TTL_S = 30 * 86400;
const EMAIL_RE = /^[^\s@]{1,64}@[^\s@]{1,190}\.[^\s@]{2,63}$/;
const NOW = "strftime('%Y-%m-%dT%H:%M:%SZ', 'now')";
const MODERATORS = new Set<UserRole>(['moderator', 'data_admin', 'national_admin', 'super_admin']);
/** Contribution types accepted here: the website's wizard plus village locations and requests for missing information. */
const TYPES = new Set(['new_place', 'correction', 'report', 'area_info', 'village_location', 'request']);
const REQUEST_SUBJECTS = new Set(['village', 'road', 'service', 'place', 'boundary', 'other']);
const DECISIONS = new Set(['approved', 'rejected', 'needs_changes']);
const BD = { minLat: 20.3, maxLat: 26.8, minLon: 87.9, maxLon: 92.8 };

function secret(env: AccountEnv): string {
  const s = env.AUTH_SECRET ?? env.EDGE_SHARED_SECRET;
  if (s && s.length >= 32) return s;
  if (env.MAIL_DEV === '1') return 'elaka360-local-development-only';
  throw new HttpError(503, 'Service Unavailable', 'sign-in is not configured');
}
const unauthorized = () => new HttpError(401, 'Unauthorized', 'sign in required');
const tooMany = (d: string) => new HttpError(429, 'Too Many Requests', d);

function randomCode(): string {
  const a = new Uint32Array(1);
  crypto.getRandomValues(a);
  return String(a[0]! % 1_000_000).padStart(6, '0');
}
function randomToken(): string {
  const a = new Uint8Array(32);
  crypto.getRandomValues(a);
  return btoa(String.fromCharCode(...a)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function emailOf(b: Record<string, unknown>): string {
  const e = textField(b, 'email', { max: 254, required: true })!.toLowerCase();
  if (!EMAIL_RE.test(e)) throw bad('email looks invalid');
  return e;
}

/* ---------------------------------------------------------------- email */

async function sendCode(env: AccountEnv, to: string, code: string): Promise<'sent' | 'dev'> {
  if (!env.RESEND_API_KEY) {
    if (env.MAIL_DEV === '1') return 'dev';
    throw new HttpError(503, 'Service Unavailable', 'email sign-in is not configured');
  }
  const text = `Elaka360-এ সাইন ইনের কোড: ${code}\nকোডটি ১০ মিনিট পর্যন্ত কাজ করবে। কাউকে কোডটি জানাবেন না।\n\n` +
    `Your Elaka360 sign-in code: ${code}\nIt is valid for 10 minutes. Do not share it.\n\n` +
    'আপনি এই কোড না চাইলে ইমেইলটি উপেক্ষা করুন। If you did not ask for this code, you can ignore this email.';
  const html = `<div style="font-family:system-ui,sans-serif;font-size:15px;line-height:1.5">
<p>Elaka360-এ সাইন ইনের কোড / Your Elaka360 sign-in code:</p>
<p style="font-size:28px;font-weight:700;letter-spacing:4px">${code}</p>
<p>কোডটি ১০ মিনিট পর্যন্ত কাজ করবে। কাউকে কোডটি জানাবেন না।<br>Valid for 10 minutes. Do not share it.</p>
<p style="color:#666;font-size:13px">আপনি এই কোড না চাইলে ইমেইলটি উপেক্ষা করুন।<br>If you did not ask for this code, you can ignore this email.</p></div>`;
  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ from: env.MAIL_FROM ?? 'Elaka360 <noreply@elaka360.abusufyan.online>', to: [to], subject: 'Elaka360 সাইন ইন কোড / sign-in code', text, html }),
  });
  if (!res.ok) {
    // status only: the response may echo the address
    console.error(JSON.stringify({ event: 'email_send_failed', status: res.status }));
    throw new HttpError(502, 'Bad Gateway', 'the email could not be sent; try again in a few minutes');
  }
  return 'sent';
}

/* ---------------------------------------------------------------- users and sessions */

interface UserRow { id: number; email: string; name: string; role: UserRole; points: number; home_area_id: number | null; created_at: string }

function meOf(u: UserRow): Me {
  const perms = MODERATORS.has(u.role) ? ['contributions.moderate'] : [];
  return {
    id: u.id, name: u.name, phone: null, email: u.email, role: u.role, points: u.points, level: 1, home_area_id: u.home_area_id,
    scope_area_id: null, profile_public: false, created_at: u.created_at, deletion_requested_at: null, permissions: perms,
    mfa_enabled: false, mfa_verified: false, mfa_required: false,
  };
}

async function currentUser(c: Ctx): Promise<UserRow & { token_hash: string }> {
  const h = c.req.headers.get('authorization');
  const token = h?.startsWith('Bearer ') ? h.slice(7).trim() : '';
  if (!/^[A-Za-z0-9_-]{40,60}$/.test(token)) throw unauthorized();
  const th = await sha256(`${token}|${secret(c.env)}`);
  const u = await c.db.prepare(
    `SELECT u.id, u.email, u.name, u.role, u.points, u.home_area_id, u.created_at, s.token_hash FROM sessions s
     JOIN users u ON u.id = s.user_id WHERE s.token_hash = ? AND s.expires_at > ${NOW}`).bind(th).first<UserRow & { token_hash: string }>();
  if (!u) throw unauthorized();
  return u;
}

async function requestCode(c: Ctx) {
  const b = await jsonBody(c.req, 2048);
  const email = emailOf(b);
  const ipHash = c.ip ? await sha256(`${c.ip}|${secret(c.env)}`) : null;
  const recent = await c.db.prepare(
    `SELECT count(*) AS n FROM email_codes WHERE email = ? AND created_at > strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-15 minutes')`)
    .bind(email).first<{ n: number }>();
  if ((recent?.n ?? 0) >= 3) throw tooMany('too many codes for this address; wait 15 minutes');
  if (ipHash) {
    const r = await c.db.prepare(
      `SELECT count(*) AS n FROM email_codes WHERE ip_hash = ? AND created_at > strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-1 hour')`)
      .bind(ipHash).first<{ n: number }>();
    if ((r?.n ?? 0) >= 10) throw tooMany('too many sign-in attempts; try again later');
  }
  const code = randomCode();
  await c.db.prepare(
    `INSERT INTO email_codes(email, code_hash, ip_hash, expires_at) VALUES (?, ?, ?, strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '+${CODE_TTL_S} seconds'))`)
    .bind(email, await sha256(`${email}|${code}|${secret(c.env)}`), ipHash).run();
  const how = await sendCode(c.env, email, code);
  return { sent: true, expires_in: CODE_TTL_S, ...(how === 'dev' ? { dev_code: code } : {}) };
}

async function verifyCode(c: Ctx) {
  const b = await jsonBody(c.req, 2048);
  const email = emailOf(b);
  const code = textField(b, 'code', { max: 6, required: true })!;
  if (!/^\d{6}$/.test(code)) throw bad('code must be 6 digits');
  const name = textField(b, 'name', { max: 60 });
  const row = await c.db.prepare(
    `SELECT id, code_hash, attempts FROM email_codes WHERE email = ? AND expires_at > ${NOW} ORDER BY id DESC LIMIT 1`)
    .bind(email).first<{ id: number; code_hash: string; attempts: number }>();
  if (!row) throw bad('the code has expired or was not requested; ask for a new one');
  if (row.attempts >= 5) throw tooMany('too many wrong codes; ask for a new one');
  if (row.code_hash !== await sha256(`${email}|${code}|${secret(c.env)}`)) {
    await c.db.prepare('UPDATE email_codes SET attempts = attempts + 1 WHERE id = ?').bind(row.id).run();
    throw bad('wrong code');
  }
  await c.db.prepare('DELETE FROM email_codes WHERE email = ?').bind(email).run();
  const fallback = email.split('@')[0]!.slice(0, 60);
  const user = await c.db.prepare(
    `INSERT INTO users(email, name, last_login_at) VALUES (?, ?, ${NOW})
     ON CONFLICT(email) DO UPDATE SET last_login_at = excluded.last_login_at,
       name = CASE WHEN ? IS NOT NULL THEN ? ELSE users.name END
     RETURNING id, email, name, role, points, home_area_id, created_at`)
    .bind(email, name ?? fallback, name, name).first<UserRow>();
  if (!user) throw new HttpError(500, 'Internal Server Error', 'account could not be created');
  const token = randomToken();
  await c.db.prepare(
    `INSERT INTO sessions(token_hash, user_id, expires_at) VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '+${SESSION_TTL_S} seconds'))`)
    .bind(await sha256(`${token}|${secret(c.env)}`), user.id).run();
  await c.db.prepare(`DELETE FROM sessions WHERE user_id = ? AND expires_at <= ${NOW}`).bind(user.id).run();
  return { access_token: token, refresh_token: null, expires_in: SESSION_TTL_S, user: meOf(user) };
}

async function logout(c: Ctx) {
  const u = await currentUser(c);
  const b = await jsonBody(c.req, 256).catch(() => ({} as Record<string, unknown>));
  if (b.all === true) await c.db.prepare('DELETE FROM sessions WHERE user_id = ?').bind(u.id).run();
  else await c.db.prepare('DELETE FROM sessions WHERE token_hash = ?').bind(u.token_hash).run();
  return { ok: true };
}

async function updateMe(c: Ctx) {
  const u = await currentUser(c);
  const b = await jsonBody(c.req, 1024);
  const name = textField(b, 'name', { max: 60, min: 2 });
  let home: number | null | undefined;
  if (b.home_area_id === null) home = null;
  else if (b.home_area_id !== undefined) {
    if (!Number.isSafeInteger(b.home_area_id)) throw bad('home_area_id must be an area id');
    if (!await c.db.prepare('SELECT 1 AS x FROM areas WHERE id = ?').bind(b.home_area_id).first()) throw bad('unknown area');
    home = b.home_area_id as number;
  }
  const row = await c.db.prepare(
    `UPDATE users SET name = COALESCE(?, name), home_area_id = CASE WHEN ? THEN ? ELSE home_area_id END WHERE id = ?
     RETURNING id, email, name, role, points, home_area_id, created_at`)
    .bind(name, home !== undefined ? 1 : 0, home ?? null, u.id).first<UserRow>();
  return meOf(row!);
}

/* ---------------------------------------------------------------- contributions */

interface ContribRow {
  id: number; user_id: number; type: string; status: ContributionStatus; target_area_id: number | null; target_place_slug: string | null;
  payload: string; evidence: string; lat: number | null; lon: number | null; confirmed_accurate: number; reviewer_note: string | null;
  created_at: string; updated_at: string; reviewed_at: string | null;
}
const CONTRIB_COLS = `id, user_id, type, status, target_area_id, target_place_slug, payload, evidence, lat, lon, confirmed_accurate,
  reviewer_note, created_at, updated_at, reviewed_at`;

function contributionOf(r: ContribRow): Contribution {
  return {
    id: r.id, type: r.type as Contribution['type'], status: r.status, target_place_slug: r.target_place_slug, target_area_id: r.target_area_id,
    payload: JSON.parse(r.payload) as Record<string, unknown>, evidence: JSON.parse(r.evidence) as Contribution['evidence'],
    lat: r.lat, lon: r.lon, confirmed_accurate: !!r.confirmed_accurate, reviewer_note: r.reviewer_note,
    created_at: r.created_at, updated_at: r.updated_at, reviewed_at: r.reviewed_at,
  };
}

/** Text fields (≤ 2,000 characters) and lists of up to 5 short texts; nothing else. */
function payloadOf(raw: unknown): Record<string, unknown> {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw bad('payload must be an object');
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(raw as Record<string, unknown>)) {
    if (!/^[a-z_]{1,40}$/.test(k)) throw bad(`payload field ${k} is not allowed`);
    if (v === undefined || v === null || v === '') continue;
    if (typeof v === 'string') {
      const s = v.normalize('NFC').trim();
      if (s.length > 2000) throw bad(`payload.${k} is too long`);
      if (s) out[k] = s;
    } else if (Array.isArray(v) && v.length <= 5 && v.every((x) => typeof x === 'string' && x.length <= 200)) {
      out[k] = v.map((x) => (x as string).normalize('NFC').trim()).filter(Boolean);
    } else throw bad(`payload.${k} must be text`);
  }
  if (Object.keys(out).length > 30) throw bad('too many payload fields');
  return out;
}
function evidenceOf(raw: unknown): { url: string; note?: string }[] {
  if (raw === undefined || raw === null) return [];
  if (!Array.isArray(raw) || raw.length > 5) throw bad('evidence must be a list of up to 5 links');
  return raw.map((e, i) => {
    const o = (e ?? {}) as Record<string, unknown>;
    const url = typeof o.url === 'string' ? o.url.trim() : '';
    if (!/^https?:\/\/[^\s]{3,490}$/.test(url)) throw bad(`evidence[${i}].url must be a web link`);
    const note = typeof o.note === 'string' ? o.note.trim().slice(0, 300) : '';
    return note ? { url, note } : { url };
  });
}
function pointOf(b: Record<string, unknown>): { lat: number | null; lon: number | null } {
  if ((b.lat === undefined || b.lat === null) && (b.lon === undefined || b.lon === null)) return { lat: null, lon: null };
  const lat = Number(b.lat), lon = Number(b.lon);
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || lat < BD.minLat || lat > BD.maxLat || lon < BD.minLon || lon > BD.maxLon) {
    throw bad('the location must be a point inside Bangladesh');
  }
  return { lat: Math.round(lat * 1e6) / 1e6, lon: Math.round(lon * 1e6) / 1e6 };
}

async function createContribution(c: Ctx) {
  const u = await currentUser(c);
  const b = await jsonBody(c.req, 16 * 1024);
  const type = textField(b, 'type', { max: 30, required: true })!;
  if (!TYPES.has(type)) throw bad(`type must be one of ${[...TYPES].join(', ')}`);
  const payload = payloadOf(b.payload ?? {});
  const evidence = evidenceOf(b.evidence);
  const { lat, lon } = pointOf(b);
  const confirmed = b.confirmed_accurate === true;
  const submit = b.submit !== false;
  if (submit && !confirmed) throw bad('confirm the information is accurate before submitting');

  let areaId: number | null = null, areaLevel: string | null = null, placeSlug: string | null = null;
  const areaPath = textField(b, 'target_area_path', { max: 200 });
  if (areaPath) {
    if (!/^[a-z0-9-]+(\/[a-z0-9-]+)*$/.test(areaPath)) throw bad('invalid target_area_path');
    const a = await c.db.prepare('SELECT id, level FROM areas WHERE path = ?').bind(areaPath).first<{ id: number; level: string }>();
    if (!a) throw bad('unknown area');
    areaId = a.id; areaLevel = a.level;
  } else if (b.target_area_id !== undefined && b.target_area_id !== null) {
    const a = await c.db.prepare('SELECT id, level FROM areas WHERE id = ?').bind(Number(b.target_area_id)).first<{ id: number; level: string }>();
    if (!a) throw bad('unknown area');
    areaId = a.id; areaLevel = a.level;
  }
  const slug = textField(b, 'target_place_slug', { max: 120 });
  if (slug) {
    if (!/^[a-z0-9-]{1,120}$/.test(slug) || !await c.db.prepare('SELECT 1 AS x FROM places WHERE slug = ?').bind(slug).first()) throw bad('unknown place');
    placeSlug = slug;
  }

  if (type === 'new_place' && (typeof payload.name_bn !== 'string' || (payload.name_bn as string).length < 2 || !payload.category_key)) {
    throw bad('a new place needs name_bn and category_key');
  }
  if ((type === 'correction' || type === 'report') && !areaId && !placeSlug) throw bad('say which place or area this is about');
  if (type === 'village_location') {
    if (!areaId || (areaLevel !== 'village' && areaLevel !== 'mouza')) throw bad('a village location needs a village or mouza as target_area_path');
    if (lat === null) throw bad('a village location needs a point (lat, lon)');
  }
  if (type === 'request') {
    if (!REQUEST_SUBJECTS.has(String(payload.subject ?? ''))) throw bad(`payload.subject must be one of ${[...REQUEST_SUBJECTS].join(', ')}`);
    if (typeof payload.description !== 'string' || (payload.description as string).length < 10) throw bad('describe what is missing (at least 10 characters)');
    if (!areaId) throw bad('say which area is missing information (target_area_path)');
  }
  const today = await c.db.prepare(
    `SELECT count(*) AS n FROM contributions WHERE user_id = ? AND created_at > strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-1 day')`)
    .bind(u.id).first<{ n: number }>();
  if ((today?.n ?? 0) >= 30) throw tooMany('at most 30 submissions a day');

  const status: ContributionStatus = submit ? 'new' : 'draft';
  const row = await c.db.prepare(
    `INSERT INTO contributions(user_id, type, status, target_area_id, target_place_slug, payload, evidence, lat, lon, confirmed_accurate)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING ${CONTRIB_COLS}`)
    .bind(u.id, type, status, areaId, placeSlug, JSON.stringify(payload), JSON.stringify(evidence), lat, lon, confirmed ? 1 : 0).first<ContribRow>();
  await c.db.prepare('INSERT INTO contribution_events(contribution_id, from_status, to_status, actor_id) VALUES (?, NULL, ?, ?)')
    .bind(row!.id, status, u.id).run();
  return contributionOf(row!);
}

async function myContributions(c: Ctx) {
  const u = await currentUser(c);
  const { results } = await c.db.prepare(`SELECT ${CONTRIB_COLS} FROM contributions WHERE user_id = ? ORDER BY id DESC LIMIT 200`)
    .bind(u.id).all<ContribRow>();
  return { items: results.map(contributionOf), next_cursor: null };
}

async function myStats(c: Ctx) {
  const u = await currentUser(c);
  const { results } = await c.db.prepare('SELECT status, count(*) AS n FROM contributions WHERE user_id = ? GROUP BY status')
    .bind(u.id).all<{ status: string; n: number }>();
  const by = Object.fromEntries(results.map((r) => [r.status, r.n]));
  return { total: results.reduce((s, r) => s + r.n, 0), by_status: by };
}

async function oneContribution(c: Ctx) {
  const u = await currentUser(c);
  const id = Number(c.m[1]);
  const r = await c.db.prepare(`SELECT ${CONTRIB_COLS} FROM contributions WHERE id = ?`).bind(id).first<ContribRow>();
  if (!r || (r.user_id !== u.id && !MODERATORS.has(u.role))) throw notFound(`contribution not found: ${id}`);
  const { results } = await c.db.prepare(
    `SELECT e.from_status, e.to_status, e.note, x.name AS actor_name, e.at FROM contribution_events e LEFT JOIN users x ON x.id = e.actor_id
     WHERE e.contribution_id = ? ORDER BY e.id`).bind(id).all<Record<string, unknown>>();
  return { ...contributionOf(r), events: results };
}

/* ---------------------------------------------------------------- moderation */

async function moderator(c: Ctx) {
  const u = await currentUser(c);
  if (!MODERATORS.has(u.role)) throw new HttpError(403, 'Forbidden', 'moderators only');
  return u;
}

async function modList(c: Ctx) {
  await moderator(c);
  const status = c.url.searchParams.get('status') ?? 'new';
  if (!['new', 'needs_changes', 'approved', 'rejected', 'all'].includes(status)) throw bad('invalid status');
  const type = c.url.searchParams.get('type');
  if (type && !TYPES.has(type)) throw bad('invalid type');
  const limit = Math.min(100, Math.max(1, Number(c.url.searchParams.get('limit') ?? 50) || 50));
  const before = Number(c.url.searchParams.get('before') ?? 0) || 0;
  const { results } = await c.db.prepare(
    `SELECT ${CONTRIB_COLS.split(',').map((x) => `c.${x.trim()}`).join(', ')}, u.name AS contributor_name, a.path AS area_path, a.name_en AS area_name
     FROM contributions c JOIN users u ON u.id = c.user_id LEFT JOIN areas a ON a.id = c.target_area_id
     WHERE (? = 'all' OR c.status = ?) AND c.status <> 'draft' AND (? IS NULL OR c.type = ?) AND (? = 0 OR c.id < ?)
     ORDER BY c.id DESC LIMIT ?`)
    .bind(status, status, type, type, before, before, limit).all<ContribRow & { contributor_name: string; area_path: string | null; area_name: string | null }>();
  const counts = await c.db.prepare("SELECT status, count(*) AS n FROM contributions WHERE status <> 'draft' GROUP BY status").all<{ status: string; n: number }>();
  return {
    items: results.map((r) => ({ ...contributionOf(r), contributor_name: r.contributor_name, area_path: r.area_path, area_name: r.area_name })),
    counts: Object.fromEntries(counts.results.map((r) => [r.status, r.n])),
    next_before: results.length === limit ? results.at(-1)!.id : null,
  };
}

async function modDecide(c: Ctx) {
  const u = await moderator(c);
  const id = Number(c.m[1]);
  const b = await jsonBody(c.req, 4096);
  const decision = textField(b, 'decision', { max: 20, required: true })!;
  if (!DECISIONS.has(decision)) throw bad('decision must be approved, rejected or needs_changes');
  const note = textField(b, 'note', { max: 1000, min: 3, required: true });
  const cur = await c.db.prepare('SELECT status FROM contributions WHERE id = ?').bind(id).first<{ status: string }>();
  if (!cur || cur.status === 'draft') throw notFound(`contribution not found: ${id}`);
  await c.db.prepare(`UPDATE contributions SET status = ?, reviewer_note = ?, reviewed_by = ?, reviewed_at = ${NOW}, updated_at = ${NOW} WHERE id = ?`)
    .bind(decision, note, u.id, id).run();
  await c.db.prepare('INSERT INTO contribution_events(contribution_id, from_status, to_status, note, actor_id) VALUES (?, ?, ?, ?, ?)')
    .bind(id, cur.status, decision, note, u.id).run();
  if (decision === 'approved' && cur.status !== 'approved') {
    await c.db.prepare('UPDATE users SET points = points + 10 WHERE id = (SELECT user_id FROM contributions WHERE id = ?)').bind(id).run();
  }
  return { id, status: decision };
}

/* ---------------------------------------------------------------- routes */

export const ACCOUNT_ROUTES: [string, RegExp, Handler][] = [
  ['POST', /^\/v1\/auth\/email\/request$/, requestCode],
  ['POST', /^\/v1\/auth\/email\/verify$/, verifyCode],
  ['POST', /^\/v1\/auth\/logout$/, logout],
  ['GET', /^\/v1\/me$/, async (c) => meOf(await currentUser(c))],
  ['PATCH', /^\/v1\/me$/, updateMe],
  ['GET', /^\/v1\/me\/contributions$/, myContributions],
  ['GET', /^\/v1\/me\/contributions\/stats$/, myStats],
  ['POST', /^\/v1\/contributions$/, createContribution],
  ['GET', /^\/v1\/contributions\/(\d{1,12})$/, oneContribution],
  ['GET', /^\/v1\/mod\/contributions$/, modList],
  ['POST', /^\/v1\/mod\/contributions\/(\d{1,12})\/decision$/, modDecide],
];
