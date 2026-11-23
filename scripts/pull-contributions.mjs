#!/usr/bin/env node
// Bring approved contributions from the edge database (Turso) into the seed sources, so the next release publishes
// them: data/sources/community_contributions_2026/village_locations.csv (approved village / mouza pins), read by
// pipelines/localities.py. Only the contribution id, the area path, the point and the approval date are written:
// no names, emails or other personal data. Run before `pnpm seed:build`, then commit the folder.
//
// Usage: TURSO_DATABASE_URL=libsql://… TURSO_AUTH_TOKEN=… node scripts/pull-contributions.mjs
//        (without them: the local libSQL server at http://127.0.0.1:8080)
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createClient } from '@libsql/client';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const DIR = join(ROOT, 'data', 'sources', 'community_contributions_2026');
const db = createClient({ url: process.env.TURSO_DATABASE_URL ?? 'http://127.0.0.1:8080', authToken: process.env.TURSO_AUTH_TOKEN, intMode: 'number' });

const { rows } = await db.execute(`
  SELECT c.id, a.path, c.lat, c.lon, substr(c.reviewed_at, 1, 10) AS approved
  FROM contributions c JOIN areas a ON a.id = c.target_area_id
  WHERE c.type = 'village_location' AND c.status = 'approved' AND c.lat IS NOT NULL
  ORDER BY a.path, c.reviewed_at DESC, c.id DESC`);
// one pin per area: the most recently approved
const seen = new Set();
const pins = rows.filter((r) => !seen.has(r.path) && seen.add(r.path));
const csv = ['contribution_id,area_path,lat,lon,approved_at', ...pins.map((r) => `${r.id},${r.path},${r.lat},${r.lon},${r.approved}`)].join('\n') + '\n';
mkdirSync(DIR, { recursive: true });
writeFileSync(join(DIR, 'village_locations.csv'), csv);
const sha = (f) => createHash('sha256').update(readFileSync(join(DIR, f))).digest('hex');
const manifest = {
  key: 'COMMUNITY_CONTRIB_2026',
  name: 'Elaka360 contributors — village locations approved by moderators',
  organization: 'Elaka360 community',
  source_type: 'community_contribution',
  trust_level: 1,
  urls: ['https://elaka360.abusufyan.online/guidelines'],
  accessed: new Date().toISOString().slice(0, 10),
  publication_date: null,
  license: null,
  attribution: 'Elaka360 contributors',
  kind: 'community_contributions',
  files: { 'village_locations.csv': sha('village_locations.csv') },
  notes: 'Pins for census villages and mouzas placed by signed-in contributors and approved by a moderator ' +
    '(scripts/pull-contributions.mjs from the edge database). Community data: shown as unverified. No personal data.',
};
writeFileSync(join(DIR, 'SOURCE.json'), JSON.stringify(manifest, null, 2) + '\n');
console.log(`village pins: ${pins.length} (from ${rows.length} approved)`);
db.close();
