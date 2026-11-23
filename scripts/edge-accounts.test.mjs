// Email sign-in, contributions and moderation on the edge API (apps/edge-api/src/accounts.ts).
// Needs the Worker running with MAIL_DEV=1 (codes come back as dev_code) and its libSQL database (to make a moderator).
// Usage: EDGE_URL=http://127.0.0.1:8789 LIBSQL_URL=http://127.0.0.1:8080 node --test scripts/edge-accounts.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createClient } from '@libsql/client';

const EDGE = process.env.EDGE_URL ?? 'http://127.0.0.1:8789';
const db = createClient({ url: process.env.LIBSQL_URL ?? 'http://127.0.0.1:8080' });
const run = Date.now().toString(36);

async function call(method, path, { body, token } = {}) {
  const res = await fetch(EDGE + path, {
    method, headers: { ...(body ? { 'content-type': 'application/json' } : {}), ...(token ? { authorization: `Bearer ${token}` } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  return { status: res.status, json: await res.json().catch(() => null) };
}

async function signIn(email, name) {
  const r = await call('POST', '/v1/auth/email/request', { body: { email } });
  assert.equal(r.status, 200, JSON.stringify(r.json));
  assert.match(r.json.dev_code, /^\d{6}$/);
  const v = await call('POST', '/v1/auth/email/verify', { body: { email, code: r.json.dev_code, name } });
  assert.equal(v.status, 200, JSON.stringify(v.json));
  return v.json;
}

async function someVillage() {
  const r = await db.execute("SELECT path FROM areas WHERE level = 'village' ORDER BY id LIMIT 1");
  return r.rows[0].path;
}

test('email sign-in: codes, wrong codes, sessions', async () => {
  const email = `edge-${run}@example.com`;
  const bad = await call('POST', '/v1/auth/email/request', { body: { email: 'not-an-email' } });
  assert.equal(bad.status, 400);
  const r = await call('POST', '/v1/auth/email/request', { body: { email: email.toUpperCase() } });   // case-insensitive
  const wrong = await call('POST', '/v1/auth/email/verify', { body: { email, code: r.json.dev_code === '000000' ? '111111' : '000000' } });
  assert.equal(wrong.status, 400);
  assert.match(wrong.json.detail, /wrong code/);
  const ok = await call('POST', '/v1/auth/email/verify', { body: { email, code: r.json.dev_code, name: 'Edge Test' } });
  assert.equal(ok.status, 200);
  assert.equal(ok.json.user.email, email);
  assert.equal(ok.json.user.name, 'Edge Test');
  const reuse = await call('POST', '/v1/auth/email/verify', { body: { email, code: r.json.dev_code } });
  assert.equal(reuse.status, 400, 'a code works once');
  const me = await call('GET', '/v1/me', { token: ok.json.access_token });
  assert.equal(me.status, 200);
  assert.deepEqual(me.json.permissions, []);
  assert.equal((await call('GET', '/v1/me')).status, 401);
  assert.equal((await call('POST', '/v1/auth/logout', { token: ok.json.access_token, body: {} })).status, 200);
  assert.equal((await call('GET', '/v1/me', { token: ok.json.access_token })).status, 401, 'logged-out token is dead');
});

test('too many codes for one address are refused', async () => {
  const email = `limit-${run}@example.com`;
  for (let i = 0; i < 3; i++) assert.equal((await call('POST', '/v1/auth/email/request', { body: { email } })).status, 200);
  assert.equal((await call('POST', '/v1/auth/email/request', { body: { email } })).status, 429);
});

test('contributions: request, village pin, validation, moderation', async () => {
  const user = await signIn(`contrib-${run}@example.com`, 'Contributor');
  const village = await someVillage();
  const T = user.access_token;
  const req = await call('POST', '/v1/contributions', { token: T, body: {
    type: 'request', target_area_path: village.split('/').slice(0, 4).join('/'), confirmed_accurate: true,
    payload: { subject: 'road', description: 'The road to the bazar is not on the map.' } } });
  assert.equal(req.status, 201, JSON.stringify(req.json));
  assert.equal(req.json.status, 'new');
  const pin = await call('POST', '/v1/contributions', { token: T, body: {
    type: 'village_location', target_area_path: village, lat: 24.37, lon: 88.6, confirmed_accurate: true, payload: { note: 'by the school' } } });
  assert.equal(pin.status, 201, JSON.stringify(pin.json));
  const outside = await call('POST', '/v1/contributions', { token: T, body: { type: 'village_location', target_area_path: village, lat: 40, lon: 88, confirmed_accurate: true } });
  assert.equal(outside.status, 400);
  const notVillage = await call('POST', '/v1/contributions', { token: T, body: { type: 'village_location', target_area_path: 'rajshahi', lat: 24.37, lon: 88.6, confirmed_accurate: true } });
  assert.equal(notVillage.status, 400);
  const unconfirmed = await call('POST', '/v1/contributions', { token: T, body: { type: 'request', target_area_path: 'rajshahi', payload: { subject: 'other', description: 'Something is missing here.' } } });
  assert.equal(unconfirmed.status, 400);
  assert.equal((await call('POST', '/v1/contributions', { body: { type: 'request' } })).status, 401);
  const mine = await call('GET', '/v1/me/contributions', { token: T });
  assert.deepEqual(mine.json.items.map((c) => c.type).sort(), ['request', 'village_location']);

  // moderation: users cannot, moderators can (a decision needs a note)
  assert.equal((await call('GET', '/v1/mod/contributions', { token: T })).status, 403);
  const mod = await signIn(`mod-${run}@example.com`, 'Moderator');
  await db.execute({ sql: "UPDATE users SET role = 'moderator' WHERE email = ?", args: [`mod-${run}@example.com`] });
  const queue = await call('GET', '/v1/mod/contributions?status=new', { token: mod.access_token });
  assert.equal(queue.status, 200);
  assert.ok(queue.json.items.some((c) => c.id === pin.json.id));
  assert.ok(queue.json.items.every((c) => !('email' in c)), 'the queue never shows contributor emails');
  const noNote = await call('POST', `/v1/mod/contributions/${pin.json.id}/decision`, { token: mod.access_token, body: { decision: 'approved' } });
  assert.equal(noNote.status, 400);
  const ok = await call('POST', `/v1/mod/contributions/${pin.json.id}/decision`, { token: mod.access_token, body: { decision: 'approved', note: 'Matches the map' } });
  assert.equal(ok.status, 200);
  const detail = await call('GET', `/v1/contributions/${pin.json.id}`, { token: T });
  assert.equal(detail.json.status, 'approved');
  assert.equal(detail.json.reviewer_note, 'Matches the map');
  assert.deepEqual(detail.json.events.map((e) => e.to_status), ['new', 'approved']);
  assert.equal((await call('GET', '/v1/me', { token: T })).json.points, 10);
});
