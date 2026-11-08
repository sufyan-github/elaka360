// End-to-end smoke test against a running API seeded with db/seed/seed.sql.
// Usage: API_URL=http://localhost:4000 node scripts/smoke-api.mjs
import assert from 'node:assert/strict';

const API = process.env.API_URL ?? 'http://localhost:4000';
let failed = 0;

async function check(name, path, fn, expectStatus = 200) {
  try {
    const res = await fetch(API + path);
    assert.equal(res.status, expectStatus, `status ${res.status}`);
    if (fn) await fn(await res.json());
    console.log(`ok   ${name}`);
  } catch (e) {
    failed++;
    console.error(`FAIL ${name} (${path}): ${e.message}`);
  }
}

await check('health', '/health', (b) => assert.equal(b.status, 'ok'));
await check('national stats', '/v1/stats/national', (b) => {
  assert.equal(b.division, 8);
  assert.equal(b.district, 64);
  assert.equal(b.upazila, 495);
  assert.equal(b.city_corporation, 13);
  assert.ok(b.union >= 4541);
});
await check('divisions', '/v1/areas?level=division', (b) => assert.equal(b.items.length, 8));
await check('rajshahi district', '/v1/areas/by-path?path=rajshahi/rajshahi', (b) => {
  assert.equal(b.area.name_bn, 'রাজশাহী');
  assert.equal(b.area.level, 'district');
  assert.equal(b.children.filter((c) => c.level === 'upazila').length, 9);
  assert.equal(b.descendant_counts.union, 71);
  assert.equal(b.breadcrumb.at(0).level, 'country');
  assert.ok(b.place_counts.education >= 2);
});
await check('unknown area 404', '/v1/areas/by-path?path=nowhere/at-all', null, 404);
await check('bad path 400', '/v1/areas/by-path?path=' + encodeURIComponent("a/'b"), null, 400);
await check('categories', '/v1/categories', (b) => {
  assert.equal(b.length, 11);
  assert.ok(b.find((c) => c.key === 'education').children.length >= 5);
});
await check('place detail', '/v1/places/university-of-rajshahi', (b) => {
  assert.equal(b.name_en, 'University of Rajshahi');
  assert.equal(b.verification_status, 'verified');
  assert.ok(b.breadcrumb.length >= 3);
  assert.equal(b.source.key, 'WIKI_RU');
});
await check('places in district', '/v1/places?area_id=20015&category=education', (b) => assert.ok(b.items.length >= 3));
await check('nearby', '/v1/places/nearby?lat=24.37&lon=88.60&radius_m=5000', (b) => {
  assert.ok(b.items.length >= 4);
  assert.ok(b.items[0].distance_m <= b.items.at(-1).distance_m);
});
await check('search bn', '/v1/search?q=' + encodeURIComponent('পবা'), (b) => assert.ok(b.areas.some((a) => a.name_en === 'Paba')));
await check('search en', '/v1/search?q=puthia', (b) => {
  assert.ok(b.areas.some((a) => a.level === 'upazila'));
  assert.ok(b.places.some((p) => p.slug === 'puthia-rajbari'));
});
await check('emergency numbers', '/v1/emergency-numbers', (b) => {
  assert.equal(b[0].number, '999');
  assert.ok(b.some((n) => n.number === '102'));
});

if (failed) {
  console.error(`\n${failed} check(s) failed`);
  process.exit(1);
}
console.log('\nAPI smoke: all checks passed');
