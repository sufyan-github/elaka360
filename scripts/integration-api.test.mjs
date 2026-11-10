// Integration tests: a running API (SMS_PROVIDER=dev) on a freshly reset, seeded database.
// Usage: API_URL=http://localhost:4000 DATABASE_URL=… node --test scripts/integration-api.test.mjs
// Creates test users with 0170000xxxx numbers; run against development/CI databases only.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';

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

function grant(p, role, scope) {
  execFileSync('node', ['apps/api/dist/cli/grant-role.js', p, role, ...(scope ? [scope] : [])], { env: process.env, stdio: 'pipe' });
}

test('public reads only return production-eligible records', async () => {
  const stats = await call('GET', '/v1/stats/national');
  assert.equal(stats.status, 200);
  assert.equal(stats.json.union, 0, 'community-only unions must not be public');
  assert.ok(stats.json.inclusion_rule);
  assert.equal((await call('GET', '/v1/places/rajshahi-college')).status, 404, 'unverified place hidden');
  assert.equal((await call('GET', '/v1/areas/by-path?path=dhaka/dhaka/savar')).status, 404, 'community upazila hidden');
  const raj = await call('GET', '/v1/areas/by-path?path=rajshahi/rajshahi');
  assert.equal(raj.json.area.evidence_level, 'secondary');
  assert.equal(raj.json.pending_counts.union, 71, 'pending unions are counted, not listed');
  const hot = await call('GET', '/v1/emergency-numbers');
  assert.ok(hot.json.every((h) => h.evidence_level === 'official' || h.evidence_level === 'secondary'));
  assert.ok(!hot.json.some((h) => h.number === '16163'), 'retired fire hotline never served');
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
  const reuse = await call('POST', '/v1/auth/refresh', { body: { refresh_token: t.refresh_token } });
  assert.equal(reuse.status, 401);
  const me = await call('GET', '/v1/me', { token: r1.json.access_token });
  assert.equal(me.status, 401, 'reuse must revoke the whole session');
});

test('user features: save, review (one per place), contribution lifecycle', async () => {
  const t = await login(phone(2), 'Reviewer');
  assert.equal((await call('POST', '/v1/me/saved', { token: t.access_token, body: { place_slug: 'ruet' } })).status, 201);
  assert.equal((await call('POST', '/v1/me/saved', { token: t.access_token, body: { place_slug: 'rajshahi-college' } })).status, 404, 'cannot save hidden place');
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

  const modPhone = phone(5);
  await login(modPhone, 'Moderator');
  grant(modPhone, 'data_admin', 'rajshahi');
  const mod = await login(modPhone, 'Moderator');
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
  assert.equal(place.production_eligible, false, 'approval alone does not publish');
  assert.equal((await call('GET', `/v1/places/${place.slug}`)).status, 404);

  const bad = await call('POST', `/v1/admin/places/${place.id}/verify`, { token: mod.access_token, body: { evidence_level: 'community', production_eligible: true, verification_notes: 'try to publish' } });
  assert.equal(bad.status, 400, 'community evidence cannot be published');
  const sources = await call('GET', '/v1/admin/sources', { token: mod.access_token });
  const wiki = sources.json.items.find((s) => s.key === 'WIKI_RAJ');
  const offi = await call('POST', `/v1/admin/places/${place.id}/verify`, { token: mod.access_token, body: { evidence_level: 'official', evidence_source_id: wiki.id, production_eligible: true, verification_notes: 'wiki is not official' } });
  assert.equal(offi.status, 400, 'official evidence needs a trust 4–5 source');
  const ok = await call('POST', `/v1/admin/places/${place.id}/verify`, { token: mod.access_token, body: { evidence_level: 'secondary', evidence_source_id: wiki.id, production_eligible: true, verification_notes: 'Listed on source page' } });
  assert.equal(ok.status, 201, JSON.stringify(ok.json));
  assert.equal((await call('GET', `/v1/places/${place.slug}`)).status, 200, 'now public');

  const audit = await call('GET', `/v1/admin/audit?entity=place&entity_id=${place.id}`, { token: mod.access_token });
  assert.ok(audit.json.items.some((a) => a.action === 'place.verify' && a.actor_name === 'Moderator'));

  // scope: a Rajshahi-scoped admin cannot touch a Dhaka area
  const dhaka = await call('GET', '/v1/admin/areas/20001', { token: mod.access_token });
  assert.equal(dhaka.status, 403);
  // cannot moderate own contribution, cannot change own role
  assert.equal((await call('PATCH', `/v1/admin/users/${mod.user.id}`, { token: mod.access_token, body: { role: 'super_admin', reason: 'self promote' } })).status, 403);
});
