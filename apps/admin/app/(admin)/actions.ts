'use server';

import { headers } from 'next/headers';
import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import type { DataSource } from '@elaka360/shared';
import { apiGet, apiSend, type MutationResult } from '@/lib/api';
import { isSameOrigin } from '@/lib/csrf';
import { HIGH_TRUST_TYPES, NEW_PLACE_TYPES, isSearchUrl } from '@/lib/labels';

export interface ActionState {
  ok?: boolean;
  error?: string;
  message?: string;
  /** Bumps on every completed submission so forms can reset. */
  n?: number;
}

/** Server actions are POSTs to page URLs; reject any that do not come from the admin's own origin. */
async function guard(): Promise<ActionState | null> {
  return isSameOrigin(await headers()) ? null : { ok: false, error: 'অননুমোদিত উৎস থেকে অনুরোধ (cross-origin request rejected)' };
}

const str = (fd: FormData, k: string) => {
  const v = fd.get(k);
  return typeof v === 'string' ? v.trim() : '';
};

function done(r: MutationResult, prev: ActionState, message: string, ...paths: string[]): ActionState {
  if (!r.ok) return { ok: false, error: r.error, n: (prev.n ?? 0) + 1 };
  for (const p of paths) revalidatePath(p);
  return { ok: true, message, n: (prev.n ?? 0) + 1 };
}

/** Same value? Compares the form's text with the record's current value. */
const same = (formValue: string, current: unknown) => formValue === (current === null || current === undefined ? '' : String(current));

/* ---------------- areas ---------------- */

type AreaRecord = Record<string, unknown> & { id: number };

export async function updateArea(id: number, prev: ActionState, fd: FormData): Promise<ActionState> {
  const bad = await guard();
  if (bad) return bad;
  const reason = str(fd, 'reason');
  if (reason.length < 5) return { ok: false, error: 'কারণ লিখুন (কমপক্ষে ৫ অক্ষর) · reason is required' };
  const cur = await apiGet<AreaRecord>(`/v1/admin/areas/${id}`);
  const body: Record<string, unknown> = { reason };
  const cleared: string[] = [];
  for (const k of ['name_bn', 'name_en', 'bbs_code', 'website', 'notes', 'status'] as const) {
    const v = str(fd, k);
    if (same(v, cur[k])) continue;
    if (v === '') cleared.push(k);
    else body[k] = v;
  }
  for (const k of ['lat', 'lon'] as const) {
    const v = str(fd, k);
    if (v === '' ? cur[k] == null : Number(v) === cur[k]) continue;
    if (v === '') cleared.push(k);
    else body[k] = Number(v);
  }
  const parent = str(fd, 'parent_id');
  if (parent && Number(parent) !== cur.parent_id) body.parent_id = Number(parent);
  if (cleared.length) return { ok: false, error: `API এই ঘর খালি করতে পারে না (cannot clear): ${cleared.join(', ')}` };
  if (Object.keys(body).length === 1) return { ok: false, error: 'কোনো পরিবর্তন নেই · nothing changed' };
  return done(await apiSend('PATCH', `/v1/admin/areas/${id}`, body), prev, 'সংরক্ষিত হয়েছে · saved', `/areas/${id}`, '/areas');
}

export async function verifyRecord(kind: 'areas' | 'places', id: number, prev: ActionState, fd: FormData): Promise<ActionState> {
  const bad = await guard();
  if (bad) return bad;
  const level = str(fd, 'evidence_level');
  const src = str(fd, 'evidence_source_id');
  const notes = str(fd, 'verification_notes');
  const publish = fd.get('production_eligible') === 'on';
  if (notes.length < 5) return { ok: false, error: 'কী যাচাই করা হয়েছে লিখুন (কমপক্ষে ৫ অক্ষর) · notes required' };
  if (publish && !['official', 'secondary'].includes(level)) return { ok: false, error: 'শুধু সরকারি বা দ্বিতীয় উৎসের তথ্য প্রকাশ করা যায়' };
  if (['official', 'secondary'].includes(level) && !src) return { ok: false, error: 'সরকারি বা দ্বিতীয় উৎসের জন্য একটি উৎস বেছে নিন · source required' };
  const r = await apiSend('POST', `/v1/admin/${kind}/${id}/verify`, {
    evidence_level: level, evidence_source_id: src ? Number(src) : null, production_eligible: publish, verification_notes: notes,
  });
  return done(r, prev, publish ? 'যাচাই সংরক্ষিত, রেকর্ড প্রকাশিত · published' : 'যাচাই সংরক্ষিত · saved (not public)', `/${kind}/${id}`, `/${kind}`, '/verification');
}

/* ---------------- places ---------------- */

const PLACE_TEXT = ['name_bn', 'name_en', 'short_name', 'address_bn', 'address_en', 'postcode', 'email', 'website', 'established',
  'description_bn', 'description_en', 'source_notes'] as const;

const phonesOf = (s: string) => s.split(/[\n,]+/).map((p) => p.trim()).filter(Boolean);

function placeBody(fd: FormData, cur: Record<string, unknown> | null): { body: Record<string, unknown>; error?: string } {
  const body: Record<string, unknown> = {};
  for (const k of PLACE_TEXT) {
    const v = str(fd, k);
    if (cur ? !same(v, cur[k]) : v !== '') body[k] = v === '' ? null : v;
  }
  const ownership = str(fd, 'ownership');
  if (cur ? !same(ownership, cur.ownership) : ownership) body.ownership = ownership || null;
  const cat = str(fd, 'category_key');
  const curCat = cur ? String(cur.subcategory_key ?? cur.category_key ?? '') : '';
  if (cat && cat !== curCat) body.category_key = cat;
  const area = str(fd, 'area_id');
  if (area) {
    if (!/^\d+$/.test(area)) return { body, error: 'area_id একটি সংখ্যা হতে হবে' };
    body.area_id = Number(area);
  }
  const lat = str(fd, 'lat');
  const lon = str(fd, 'lon');
  if ((lat === '') !== (lon === '')) return { body, error: 'অক্ষাংশ ও দ্রাঘিমাংশ একসঙ্গে দিন · lat and lon go together' };
  const coordChanged = cur ? !(lat === '' ? cur.lat == null : Number(lat) === cur.lat) || !(lon === '' ? cur.lon == null : Number(lon) === cur.lon) : lat !== '';
  if (coordChanged) { body.lat = lat === '' ? null : Number(lat); body.lon = lon === '' ? null : Number(lon); }
  const phones = phonesOf(str(fd, 'phones'));
  const curPhones = Array.isArray(cur?.phones) ? (cur!.phones as string[]) : [];
  if (cur ? phones.join('|') !== curPhones.join('|') : phones.length) body.phones = phones;
  const src = str(fd, 'data_source_id');
  if (fd.has('data_source_id') && (cur ? !same(src, cur.data_source_id) : src)) body.data_source_id = src ? Number(src) : null;
  if (cur) {
    const status = str(fd, 'status');
    if (status && status !== cur.status) body.status = status;
  }
  return { body };
}

export async function createPlace(prev: ActionState, fd: FormData): Promise<ActionState> {
  const bad = await guard();
  if (bad) return bad;
  const { body, error } = placeBody(fd, null);
  if (error) return { ok: false, error };
  if (!body.name_bn) return { ok: false, error: 'বাংলা নাম আবশ্যক · name_bn is required' };
  if (!body.category_key) return { ok: false, error: 'ক্যাটাগরি বেছে নিন · category is required' };
  if (!body.area_id) return { ok: false, error: 'এলাকা বেছে নিন · area is required' };
  const r = await apiSend<{ id: number }>('POST', '/v1/admin/places', body);
  if (!r.ok) return { ok: false, error: r.error, n: (prev.n ?? 0) + 1 };
  revalidatePath('/places');
  redirect(`/places/${r.data.id}?created=1`);
}

export async function updatePlace(id: number, prev: ActionState, fd: FormData): Promise<ActionState> {
  const bad = await guard();
  if (bad) return bad;
  const reason = str(fd, 'reason');
  if (reason.length < 5) return { ok: false, error: 'কারণ লিখুন (কমপক্ষে ৫ অক্ষর) · reason is required' };
  const cur = await apiGet<Record<string, unknown>>(`/v1/admin/places/${id}`);
  const { body, error } = placeBody(fd, cur);
  if (error) return { ok: false, error };
  if (!Object.keys(body).length) return { ok: false, error: 'কোনো পরিবর্তন নেই · nothing changed' };
  return done(await apiSend('PATCH', `/v1/admin/places/${id}`, { ...body, reason }), prev, 'সংরক্ষিত হয়েছে · saved', `/places/${id}`, '/places');
}

/* ---------------- moderation ---------------- */

export async function decideContribution(id: number, prev: ActionState, fd: FormData): Promise<ActionState> {
  const bad = await guard();
  if (bad) return bad;
  const decision = str(fd, 'decision');
  const note = str(fd, 'note');
  if (!['start_review', 'approve', 'request_changes', 'reject'].includes(decision)) return { ok: false, error: 'invalid decision' };
  if (decision !== 'start_review' && note.length < 3) return { ok: false, error: 'সিদ্ধান্তের নোট লিখুন (কমপক্ষে ৩ অক্ষর) · note is required' };
  const body: Record<string, unknown> = { decision };
  if (note) body.note = note;
  const area = str(fd, 'area_id');
  if (decision === 'approve' && NEW_PLACE_TYPES.includes(str(fd, 'type') as never) && !area) {
    return { ok: false, error: 'অনুমোদনের আগে নতুন স্থানের এলাকা বেছে নিন · choose area_id to approve' };
  }
  if (decision === 'approve' && area) {
    if (!/^\d+$/.test(area)) return { ok: false, error: 'area_id একটি সংখ্যা হতে হবে' };
    body.area_id = Number(area);
  }
  return done(await apiSend('POST', `/v1/admin/contributions/${id}/decision`, body), prev, 'সিদ্ধান্ত সংরক্ষিত · decision saved', `/moderation/${id}`, '/moderation');
}

export async function decideReport(id: number, prev: ActionState, fd: FormData): Promise<ActionState> {
  const bad = await guard();
  if (bad) return bad;
  const decision = str(fd, 'decision');
  if (decision !== 'uphold' && decision !== 'dismiss') return { ok: false, error: 'invalid decision' };
  return done(await apiSend('POST', `/v1/admin/review-reports/${id}/decision`, { decision }), prev,
    decision === 'uphold' ? 'রিপোর্ট বহাল, রিভিউ লুকানো হয়েছে · upheld' : 'রিপোর্ট খারিজ · dismissed', '/review-reports');
}

/* ---------------- duplicates ---------------- */

export async function decideDuplicate(id: number, prev: ActionState, fd: FormData): Promise<ActionState> {
  const bad = await guard();
  if (bad) return bad;
  const decision = str(fd, 'decision');
  const note = str(fd, 'note');
  if (!['merged', 'kept_separate', 'not_duplicate', 'needs_more_review'].includes(decision)) return { ok: false, error: 'invalid decision' };
  if (note.length < 3) return { ok: false, error: 'সিদ্ধান্তের নোট লিখুন (কমপক্ষে ৩ অক্ষর) · note is required' };
  return done(await apiSend('POST', `/v1/admin/duplicates/${id}/decision`, { decision, note }), prev, 'সিদ্ধান্ত সংরক্ষিত · decision saved', '/duplicates');
}

export async function scanDuplicates(prev: ActionState): Promise<ActionState> {
  const bad = await guard();
  if (bad) return bad;
  const r = await apiSend<{ scanned: number; new_pairs: number }>('POST', '/v1/admin/duplicates/scan', {});
  if (!r.ok) return { ok: false, error: r.error, n: (prev.n ?? 0) + 1 };
  revalidatePath('/duplicates');
  return { ok: true, message: `${r.data.scanned}টি স্থান পরীক্ষা হয়েছে; নতুন সম্ভাব্য জোড়া ${r.data.new_pairs}টি`, n: (prev.n ?? 0) + 1 };
}

/* ---------------- open data keys ---------------- */

export interface KeyState extends ActionState { key?: string }

export async function createApiKey(prev: KeyState, fd: FormData): Promise<KeyState> {
  const bad = await guard();
  if (bad) return bad;
  const name = str(fd, 'name');
  const rate = Number(str(fd, 'rate_per_min') || 60);
  if (name.length < 3) return { ok: false, error: 'নাম লিখুন (কমপক্ষে ৩ অক্ষর)' };
  const r = await apiSend<{ key: string }>('POST', '/v1/admin/api-keys', { name, rate_per_min: rate });
  if (!r.ok) return { ok: false, error: r.error, n: (prev.n ?? 0) + 1 };
  revalidatePath('/api-keys');
  return { ok: true, key: r.data.key, message: 'কী তৈরি হয়েছে — এখনই কপি করুন, আর দেখানো হবে না', n: (prev.n ?? 0) + 1 };
}

export async function revokeApiKey(id: number, prev: ActionState): Promise<ActionState> {
  const bad = await guard();
  if (bad) return bad;
  return done(await apiSend('DELETE', `/v1/admin/api-keys/${id}`), prev, 'কী বাতিল হয়েছে · revoked', '/api-keys');
}

/* ---------------- sources ---------------- */

const SOURCE_TEXT = ['name', 'url', 'license', 'organization', 'evidence_notes', 'access_date', 'publication_date', 'source_type'] as const;

function sourceChecks(url: string, trust: number, type: string): string | null {
  if (url && isSearchUrl(url)) return 'সার্চ ফলাফলের পাতা উৎস নয় · a search-results page is not a source';
  if (trust >= 4 && !HIGH_TRUST_TYPES.includes(type)) return 'আস্থা ৪–৫ শুধু সরকারি পোর্টাল, গেজেট ও আদমশুমারির জন্য · trust 4–5 is reserved for government_portal, gazette, census';
  return null;
}

export async function createSource(prev: ActionState, fd: FormData): Promise<ActionState> {
  const bad = await guard();
  if (bad) return bad;
  const body: Record<string, unknown> = { key: str(fd, 'key') };
  for (const k of SOURCE_TEXT) if (str(fd, k)) body[k] = str(fd, k);
  body.trust_level = Number(str(fd, 'trust_level') || 2);
  const err = sourceChecks(str(fd, 'url'), body.trust_level as number, str(fd, 'source_type') || 'unknown');
  if (err) return { ok: false, error: err };
  return done(await apiSend('POST', '/v1/admin/sources', body), prev, 'উৎস যোগ হয়েছে · source created', '/sources');
}

export async function updateSource(id: number, prev: ActionState, fd: FormData): Promise<ActionState> {
  const bad = await guard();
  if (bad) return bad;
  const { items } = await apiGet<{ items: DataSource[] }>('/v1/admin/sources');
  const cur = items.find((s) => s.id === id);
  if (!cur) return { ok: false, error: 'source not found' };
  const body: Record<string, unknown> = {};
  for (const k of SOURCE_TEXT) {
    const v = str(fd, k);
    if (!same(v, cur[k])) body[k] = v === '' ? null : v;
  }
  if (body.name === null) return { ok: false, error: 'নাম আবশ্যক · name is required' };
  if (body.source_type === null) delete body.source_type;
  const trust = Number(str(fd, 'trust_level'));
  if (trust && trust !== cur.trust_level) body.trust_level = trust;
  const active = fd.get('active') === 'on';
  if (active !== cur.active) body.active = active;
  // The API checks trust vs type only when both are sent; send both so the rule always applies.
  if (body.trust_level !== undefined || body.source_type !== undefined) {
    body.trust_level = trust || cur.trust_level;
    body.source_type = str(fd, 'source_type') || cur.source_type;
  }
  const err = sourceChecks(str(fd, 'url'), trust || cur.trust_level, str(fd, 'source_type') || cur.source_type);
  if (err) return { ok: false, error: err };
  if (!Object.keys(body).length) return { ok: false, error: 'কোনো পরিবর্তন নেই · nothing changed' };
  return done(await apiSend('PATCH', `/v1/admin/sources/${id}`, body), prev, 'সংরক্ষিত হয়েছে · saved', '/sources');
}

/* ---------------- users ---------------- */

export async function updateUser(id: number, prev: ActionState, fd: FormData): Promise<ActionState> {
  const bad = await guard();
  if (bad) return bad;
  const reason = str(fd, 'reason');
  if (reason.length < 5) return { ok: false, error: 'কারণ লিখুন (কমপক্ষে ৫ অক্ষর) · reason is required' };
  const body: Record<string, unknown> = { reason };
  const role = str(fd, 'role');
  const status = str(fd, 'status');
  const scope = str(fd, 'scope_area_id');
  if (role && role !== str(fd, 'orig_role')) body.role = role;
  if (status && status !== str(fd, 'orig_status')) body.status = status;
  if (scope !== str(fd, 'orig_scope_area_id')) {
    if (scope && !/^\d+$/.test(scope)) return { ok: false, error: 'scope_area_id একটি সংখ্যা হতে হবে' };
    body.scope_area_id = scope ? Number(scope) : null;
  }
  if (Object.keys(body).length === 1) return { ok: false, error: 'কোনো পরিবর্তন নেই · nothing changed' };
  return done(await apiSend('PATCH', `/v1/admin/users/${id}`, body), prev, 'সংরক্ষিত হয়েছে · saved', '/users');
}
