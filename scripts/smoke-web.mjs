// Smoke test the built web app (next start) against a running API.
// Usage: WEB_URL=http://localhost:3000 node scripts/smoke-web.mjs
const WEB = process.env.WEB_URL ?? 'http://localhost:3000';
const pages = [
  ['/', 'বাংলাদেশের প্রতিটি এলাকার'],
  ['/explore', 'বাংলাদেশ ঘুরে দেখুন'],
  ['/explore?level=district&division=10002', 'জেলাসমূহ'],
  ['/rajshahi', 'রাজশাহী বিভাগ'],
  ['/rajshahi/rajshahi', 'রাজশাহী জেলা'],
  ['/rajshahi/rajshahi/paba', 'পবা উপজেলা'],
  ['/rajshahi/rajshahi/rajshahi-city-corporation', 'রাজশাহী সিটি কর্পোরেশন'],
  ['/p/university-of-rajshahi', 'রাজশাহী বিশ্ববিদ্যালয়'],
  ['/c/education', 'শিক্ষা প্রতিষ্ঠান'],
  ['/search?q=rajshahi', 'এলাকা'],
  ['/emergency', '999'],
  ['/near-me', 'আমার আশেপাশের সেবা'],
  ['/saved', 'শীঘ্রই আসছে'],
];
let failed = 0;
for (const [path, text] of pages) {
  const res = await fetch(WEB + path);
  const html = await res.text();
  const ok = res.status === 200 && html.includes(text);
  if (!ok) failed++;
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${path} → ${res.status}${ok ? '' : ` (expected text: ${text})`}`);
}
const nf = await fetch(WEB + '/no-such/area-here');
console.log(`${nf.status === 404 ? 'ok  ' : 'FAIL'} 404 page → ${nf.status}`);
if (nf.status !== 404) failed++;
const api = await fetch(WEB + '/api/nearby?lat=24.37&lon=88.6&radius_m=5000');
const body = await api.json().catch(() => ({}));
const apiOk = api.status === 200 && Array.isArray(body.items) && body.items.length > 0;
console.log(`${apiOk ? 'ok  ' : 'FAIL'} /api/nearby proxy → ${api.status}`);
if (!apiOk) failed++;
if (failed) { console.error(`\n${failed} web check(s) failed`); process.exit(1); }
console.log('\nWeb smoke: all checks passed');
