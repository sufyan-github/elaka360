// Integration tests: a running API (SMS_PROVIDER=dev) on a freshly reset, seeded database.
// Usage: API_URL=http://localhost:4000 DATABASE_URL=… node --test scripts/integration-api.test.mjs
// Creates test users with 0170000xxxx numbers; run against development/CI databases only.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createHmac } from 'node:crypto';

const API = process.env.API_URL ?? 'http://localhost:4000';
const run = Date.now() % 100000;
const phone = (n) => `0170${String(run).padStart(6, '0')}${n}`;

async function call(method, path, { token, body } = {}) {
  const res = await fetch(API + path, {
    method,
    headers: { ...(body ? { 'Content-Type': 'application/json' } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let json = null;
  try { json = text ? JSON.parse(text) : null; } catch { /* not json */ }
  return { status: res.status, json, headers: res.headers };
}

async function login(p, name) {
  const r = await call('POST', '/v1/auth/otp/request', { body: { phone: p } });
  assert.equal(r.status, 200, JSON.stringify(r.json));
  assert.match(r.json.dev_code, /^\d{6}$/, 'API must run with SMS_PROVIDER=dev for these tests');
  const v = await call('POST', '/v1/auth/otp/verify', { body: { phone: p, code: r.json.dev_code, name } });
  assert.equal(v.status, 200, JSON.stringify(v.json));
  return v.json;
}

/** RFC 6238 TOTP, as an authenticator app would compute it. */
function totp(base32, offsetSteps = 0) {
  const A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = 0, value = 0;
  const bytes = [];
  for (const ch of base32) {
    value = (value << 5) | A.indexOf(ch);
    bits += 5;
    if (bits >= 8) { bytes.push((value >>> (bits - 8)) & 255); bits -= 8; }
  }
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000) + offsetSteps));
  const h = createHmac('sha1', Buffer.from(bytes)).update(counter).digest();
  const o = h[h.length - 1] & 15;
  return String((((h[o] & 127) << 24) | (h[o + 1] << 16) | (h[o + 2] << 8) | h[o + 3]) % 1e6).padStart(6, '0');
}

/** Sign in as staff; completes 2FA enrolment when the server requires it. Returns tokens + the TOTP secret. */
async function staffLogin(p, name, role, scope) {
  await login(p, name);
  grant(p, role, scope);
  const t = await login(p, name);
  if (!t.user.mfa_required) return { ...t, secret: null };
  const setup = await call('POST', '/v1/me/2fa/setup', { token: t.access_token });
  const en = await call('POST', '/v1/me/2fa/enable', { token: t.access_token, body: { code: totp(setup.json.secret) } });
  assert.equal(en.status, 200, JSON.stringify(en.json));
  return { ...t, secret: setup.json.secret };
}

function grant(p, role, scope) {
  execFileSync('node', ['apps/api/dist/cli/grant-role.js', p, role, ...(scope ? [scope] : [])], { env: process.env, stdio: 'pipe' });
}

/** The API reports its visibility mode: labelled (default) shows unverified records, strict hides them. */
async function labelledMode() {
  return (await call('GET', '/health')).json.public_include_unverified === true;
}

test('public reads follow the visibility mode and always carry evidence', async () => {
  const labelled = await labelledMode();
  const stats = await call('GET', '/v1/stats/national');
  assert.equal(stats.status, 200);
  assert.equal(stats.json.sourced.union, 0, 'community-only unions are never counted as sourced');
  assert.equal(stats.json.sourced.upazila, 10);
  assert.equal(stats.json.union, labelled ? stats.json.union : 0);
  assert.ok(stats.json.inclusion_rule);
  const college = await call('GET', '/v1/places/rajshahi-college');
  const savar = await call('GET', '/v1/areas/by-path?path=dhaka/dhaka/savar');
  if (labelled) {
    assert.ok(stats.json.union >= 4538);
    assert.equal(college.status, 200);
    assert.equal(college.json.production_eligible, false);
    assert.equal(college.json.evidence_level, 'unverified');
    assert.equal(savar.json.area.evidence_level, 'community');
    assert.equal(savar.json.area.production_eligible, false);
  } else {
    assert.equal(college.status, 404, 'unverified place hidden in strict mode');
    assert.equal(savar.status, 404, 'community upazila hidden in strict mode');
  }
  const raj = await call('GET', '/v1/areas/by-path?path=rajshahi/rajshahi');
  assert.equal(raj.json.area.evidence_level, 'secondary');
  assert.equal(labelled ? raj.json.descendant_counts.union : raj.json.pending_counts.union, 71);
  const hot = await call('GET', '/v1/emergency-numbers');
  assert.ok(hot.json.every((h) => h.evidence_level === 'official' || h.evidence_level === 'secondary'), 'hotlines are sourced in every mode');
  assert.ok(!hot.json.some((h) => ['16163', '16263', '1098', '16430'].includes(h.number)));
});

test('errors are problem details; bad ids are 400 not 500', async () => {
  const r = await call('GET', '/v1/areas/999999999999999999999');
  assert.equal(r.status, 400);
  assert.equal(r.json.status, 400);
  assert.ok(r.json.request_id);
  assert.match(r.headers.get('content-type'), /application\/problem\+json/);
});

test('search: Banglish, multi-word, suggestions, locate, nearby', async () => {
  const s1 = await call('GET', '/v1/search?q=rajsahi');
  assert.ok(s1.json.areas.some((a) => a.name_en === 'Rajshahi'));
  const s2 = await call('GET', `/v1/search?q=${encodeURIComponent('rajshahi university')}`);
  assert.ok(s2.json.places.some((p) => p.slug === 'university-of-rajshahi'));
  const s3 = await call('GET', `/v1/search?q=${encodeURIComponent('রাজশাহী')}&type=area`);
  assert.equal(s3.json.places.length, 0);
  assert.ok(s3.json.areas.length >= 1);
  const sug = await call('GET', '/v1/search/suggest?q=raj');
  assert.ok(sug.json.items.length >= 1);
  const loc = await call('GET', '/v1/geo/locate?lat=24.37&lon=88.6');
  assert.equal(loc.json.area.name_en, 'Rajshahi');
  const near = await call('GET', '/v1/places/nearby?lat=24.37&lon=88.6&radius_m=5000');
  const d = near.json.items.map((p) => p.distance_m);
  assert.deepEqual(d, [...d].sort((a, b) => a - b), 'nearest first');
  const wild = await call('GET', '/v1/places?q=%25');
  assert.equal(wild.status, 400, 'a lone % is not a search');
});

test('auth: OTP, wrong code, refresh rotation, reuse revokes the session', async () => {
  const p = phone(1);
  const bad = await call('POST', '/v1/auth/otp/verify', { body: { phone: p, code: '000000' } });
  assert.equal(bad.status, 401);
  const t = await login(p, 'Integration User');
  assert.equal(t.user.role, 'user');
  const r1 = await call('POST', '/v1/auth/refresh', { body: { refresh_token: t.refresh_token } });
  assert.equal(r1.status, 200);
  // A concurrent refresh with the token just replaced is tolerated (grace window)...
  const race = await call('POST', '/v1/auth/refresh', { body: { refresh_token: t.refresh_token } });
  assert.equal(race.status, 200, 'concurrent refresh within the grace window');
  assert.equal(race.json.refresh_token, null, 'the racing response must not replace the refresh token');
  // ...but a token two rotations old is theft: the whole session is revoked.
  const r2 = await call('POST', '/v1/auth/refresh', { body: { refresh_token: r1.json.refresh_token } });
  assert.equal(r2.status, 200);
  const reuse = await call('POST', '/v1/auth/refresh', { body: { refresh_token: t.refresh_token } });
  assert.equal(reuse.status, 401);
  const me = await call('GET', '/v1/me', { token: r2.json.access_token });
  assert.equal(me.status, 401, 'reuse must revoke the whole session');
});

test('user features: save, review (one per place), contribution lifecycle', async () => {
  const t = await login(phone(2), 'Reviewer');
  assert.equal((await call('POST', '/v1/me/saved', { token: t.access_token, body: { place_slug: 'ruet' } })).status, 201);
  const hiddenSave = await call('POST', '/v1/me/saved', { token: t.access_token, body: { place_slug: 'rajshahi-college' } });
  assert.equal(hiddenSave.status, (await labelledMode()) ? 201 : 404, 'only visible places can be saved');
  const saved = await call('GET', '/v1/me/saved', { token: t.access_token });
  assert.ok(saved.json.items.some((i) => i.place?.slug === 'ruet'));
  assert.equal((await call('POST', '/v1/places/puthia-rajbari/reviews', { token: t.access_token, body: { rating: 5, body: 'Beautiful' } })).status, 201);
  assert.equal((await call('POST', '/v1/places/puthia-rajbari/reviews', { token: t.access_token, body: { rating: 3 } })).status, 409);
  assert.equal((await call('POST', '/v1/places/puthia-rajbari/reviews', { token: t.access_token, body: { rating: 9 } })).status, 400);
  const draft = await call('POST', '/v1/contributions', { token: t.access_token, body: { type: 'correction', target_place_slug: 'ruet', payload: { field: 'phone', proposed_value: '0721-000000' } } });
  assert.equal(draft.status, 201);
  assert.equal(draft.json.status, 'draft');
  const noConfirm = await call('POST', `/v1/contributions/${draft.json.id}/submit`, { token: t.access_token });
  assert.equal(noConfirm.status, 400, 'must confirm accuracy');
  await call('PATCH', `/v1/contributions/${draft.json.id}`, { token: t.access_token, body: { confirmed_accurate: true } });
  const sub = await call('POST', `/v1/contributions/${draft.json.id}/submit`, { token: t.access_token });
  assert.equal(sub.json.status, 'new');
  assert.deepEqual(sub.json.events.map((e) => e.to_status), ['draft', 'new']);
  const other = await login(phone(3), 'Other');
  assert.equal((await call('GET', `/v1/contributions/${draft.json.id}`, { token: other.access_token })).status, 404, 'users only see their own');
  assert.equal((await call('GET', '/v1/admin/stats', { token: t.access_token })).status, 403);
});

test('moderation + verification follow the trust policy and are audited', async () => {
  const user = await login(phone(4), 'Submitter');
  const c = await call('POST', '/v1/contributions', {
    token: user.access_token,
    body: { type: 'new_place', payload: { name_bn: 'পরীক্ষা ফার্মেসি', name_en: 'Integration Pharmacy', category_key: 'health.pharmacy' }, lat: 24.36, lon: 88.62, confirmed_accurate: true, submit: true },
  });
  assert.equal(c.status, 201, JSON.stringify(c.json));

  const mod = await staffLogin(phone(5), 'Moderator', 'data_admin', 'rajshahi');
  assert.ok(mod.user.permissions.includes('contributions.moderate'));

  const queue = await call('GET', '/v1/admin/contributions?status=new', { token: mod.access_token });
  assert.ok(queue.json.items.some((i) => i.id === c.json.id), 'in-scope contribution visible');
  const approve = await call('POST', `/v1/admin/contributions/${c.json.id}/decision`, { token: mod.access_token, body: { decision: 'approve', note: 'Checked on site', area_id: 30134 } });
  assert.equal(approve.status, 201, JSON.stringify(approve.json));
  const createdId = /\[created (\S+)\]/.exec(approve.json.reviewer_note)?.[1];
  assert.ok(createdId);

  const list = await call('GET', `/v1/admin/places?q=${createdId}`, { token: mod.access_token });
  const place = list.json.items[0];
  assert.equal(place.evidence_level, 'community');
  assert.equal(place.production_eligible, false, 'approval alone does not make it sourced');
  const before = await call('GET', `/v1/places/${place.slug}`);
  if (await labelledMode()) assert.equal(before.json.production_eligible, false);
  else assert.equal(before.status, 404);

  const bad = await call('POST', `/v1/admin/places/${place.id}/verify`, { token: mod.access_token, body: { evidence_level: 'community', production_eligible: true, verification_notes: 'try to publish' } });
  assert.equal(bad.status, 400, 'community evidence cannot be published');
  const sources = await call('GET', '/v1/admin/sources', { token: mod.access_token });
  const wiki = sources.json.items.find((s) => s.key === 'WIKI_RAJ');
  const offi = await call('POST', `/v1/admin/places/${place.id}/verify`, { token: mod.access_token, body: { evidence_level: 'official', evidence_source_id: wiki.id, production_eligible: true, verification_notes: 'wiki is not official' } });
  assert.equal(offi.status, 400, 'official evidence needs a trust 4–5 source');
  const ok = await call('POST', `/v1/admin/places/${place.id}/verify`, { token: mod.access_token, body: { evidence_level: 'secondary', evidence_source_id: wiki.id, production_eligible: true, verification_notes: 'Listed on source page' } });
  assert.equal(ok.status, 201, JSON.stringify(ok.json));
  const after = await call('GET', `/v1/places/${place.slug}`);
  assert.equal(after.status, 200);
  assert.equal(after.json.production_eligible, true, 'now sourced');

  const audit = await call('GET', `/v1/admin/audit?entity=place&entity_id=${place.id}`, { token: mod.access_token });
  assert.ok(audit.json.items.some((a) => a.action === 'place.verify' && a.actor_name === 'Moderator'));

  // scope: a Rajshahi-scoped admin cannot touch a Dhaka area
  const dhaka = await call('GET', '/v1/admin/areas/20001', { token: mod.access_token });
  assert.equal(dhaka.status, 403);
  // cannot moderate own contribution, cannot change own role
  assert.equal((await call('PATCH', `/v1/admin/users/${mod.user.id}`, { token: mod.access_token, body: { role: 'super_admin', reason: 'self promote' } })).status, 403);
});

test('staff two-factor authentication: enrol, verify per session, recovery codes, disable', async () => {
  const p = phone(6);
  await login(p, 'Two Factor');
  grant(p, 'analyst');
  const t = await login(p, 'Two Factor');
  assert.equal(t.user.mfa_enabled, false);
  const setup = await call('POST', '/v1/me/2fa/setup', { token: t.access_token });
  assert.match(setup.json.secret, /^[A-Z2-7]{32}$/);
  assert.match(setup.json.otpauth_uri, /^otpauth:\/\/totp\/Elaka360/);
  assert.equal((await call('POST', '/v1/me/2fa/enable', { token: t.access_token, body: { code: '000000' } })).status, 401);
  const en = await call('POST', '/v1/me/2fa/enable', { token: t.access_token, body: { code: totp(setup.json.secret) } });
  assert.equal(en.status, 200);
  assert.equal(en.json.recovery_codes.length, 8);

  // A new session starts unverified; staff routes are refused when the server requires 2FA.
  const t2 = await login(p, 'Two Factor');
  assert.equal(t2.user.mfa_enabled, true);
  assert.equal(t2.user.mfa_verified, false);
  const stats = await call('GET', '/v1/admin/stats', { token: t2.access_token });
  if (t2.user.mfa_required) {
    assert.equal(stats.status, 403);
    assert.equal(stats.json.type, 'urn:elaka360:mfa-required');
  }
  assert.equal((await call('POST', '/v1/auth/2fa/verify', { token: t2.access_token, body: { code: '123456' } })).status, 401);
  const rc = en.json.recovery_codes[0];
  assert.equal((await call('POST', '/v1/auth/2fa/verify', { token: t2.access_token, body: { code: rc } })).status, 200, 'recovery code works once');
  assert.equal((await call('GET', '/v1/me', { token: t2.access_token })).json.mfa_verified, true);
  assert.equal((await call('GET', '/v1/admin/stats', { token: t2.access_token })).status, 200);
  const t3 = await login(p, 'Two Factor');
  assert.equal((await call('POST', '/v1/auth/2fa/verify', { token: t3.access_token, body: { code: rc } })).status, 401, 'recovery codes are single-use');
  const off = await call('POST', '/v1/me/2fa/disable', { token: t3.access_token, body: { code: en.json.recovery_codes[1] } });
  assert.equal(off.json.enabled, false);
});

test('duplicate detection: flags lookalikes, blocks publishing ≥95, staff decide', async () => {
  const staff = await staffLogin(phone(7), 'Data Manager', 'data_admin', 'rajshahi');
  const T = staff.access_token;
  const created = await call('POST', '/v1/admin/places', {
    token: T,
    body: { name_bn: 'রাজশাহী বিশ্ববিদ্যালয়', name_en: 'University of Rajshahi', category_key: 'education.university', area_id: 30134, lat: 24.3701, lon: 88.6371 },
  });
  assert.equal(created.status, 201, JSON.stringify(created.json));
  const original = created.json.possible_duplicates.find((d) => d.slug === 'university-of-rajshahi');
  assert.ok(original, JSON.stringify(created.json.possible_duplicates));
  assert.ok(original.score >= 95, `score ${original.score}`);

  const sources = await call('GET', '/v1/admin/sources', { token: T });
  const wiki = sources.json.items.find((s) => s.key === 'WIKI_RU');
  const blocked = await call('POST', `/v1/admin/places/${created.json.id}/verify`, {
    token: T, body: { evidence_level: 'secondary', evidence_source_id: wiki.id, production_eligible: true, verification_notes: 'try to publish copy' },
  });
  assert.equal(blocked.status, 400);
  assert.match(blocked.json.detail, /suspected duplicate/);

  const open = await call('GET', '/v1/admin/duplicates', { token: T });
  const pair = open.json.items.find((d) => d.place_b?.id === created.json.id);
  assert.ok(pair, 'pair listed for review');
  const merged = await call('POST', `/v1/admin/duplicates/${pair.id}/decision`, { token: T, body: { decision: 'merged', note: 'Same university, created twice' } });
  assert.equal(merged.status, 200);
  const archived = await call('GET', `/v1/admin/places/${created.json.id}`, { token: T });
  assert.equal(archived.json.status, 'archived', 'the copy is archived, the original kept');

  // A contribution that looks like RUET is flagged for the moderator.
  const user = await login(phone(8), 'Suggester');
  const c = await call('POST', '/v1/contributions', {
    token: user.access_token,
    body: { type: 'new_place', payload: { name_bn: 'রাজশাহী প্রকৌশল ও প্রযুক্তি বিশ্ববিদ্যালয়', name_en: 'Rajshahi University of Engineering & Technology', category_key: 'education.university' },
            lat: 24.3636, lon: 88.6281, confirmed_accurate: true, submit: true },
  });
  const detail = await call('GET', `/v1/admin/contributions/${c.json.id}`, { token: T });
  assert.ok(detail.json.duplicates.some((d) => d.slug === 'ruet' && d.match_score >= 80), JSON.stringify(detail.json.duplicates));
});

test('open data: keyed, sourced-only, CSV, per-key rate limit, revocation', async () => {
  const admin = await staffLogin(phone(9), 'Open Data Admin', 'national_admin');
  const created = await call('POST', '/v1/admin/api-keys', { token: admin.access_token, body: { name: 'integration test', rate_per_min: 4 } });
  assert.equal(created.status, 201, JSON.stringify(created.json));
  const key = created.json.key;
  assert.match(key, /^e360_/);
  const od = (path) => fetch(API + path, { headers: { 'X-API-Key': key } });

  assert.equal((await fetch(API + '/v1/open-data/areas')).status, 401, 'key required');
  const areas = await od('/v1/open-data/areas?limit=500');
  assert.equal(areas.status, 200);
  const body = await areas.json();
  assert.ok(body.license_notice.includes('CC BY-SA'));
  assert.ok(body.items.length >= 95);
  assert.ok(body.items.every((a) => a.evidence_level === 'official' || a.evidence_level === 'secondary'), 'sourced only');
  const unions = await (await od('/v1/open-data/areas?level=union')).json();
  assert.equal(unions.items.length, 0, 'community unions never exported, in any visibility mode');
  const csv = await od('/v1/open-data/places?format=csv');
  assert.match(csv.headers.get('content-type'), /text\/csv/);
  assert.ok((await csv.text()).split('\r\n')[0].includes('public_id'));
  assert.equal((await od('/v1/open-data/sources')).status, 200, 'fourth request is within rate_per_min 4');
  assert.equal((await od('/v1/open-data/sources')).status, 429, 'fifth request in the minute exceeds rate_per_min 4');

  const revoked = await call('DELETE', `/v1/admin/api-keys/${created.json.id}`, { token: admin.access_token });
  assert.equal(revoked.status, 200);
  assert.equal((await od('/v1/open-data/sources')).status, 401, 'revoked keys stop working');
});
