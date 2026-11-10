/**
 * Rebuild the Typesense collections from Postgres with a zero-downtime alias swap.
 * Usage: DATABASE_URL=… TYPESENSE_URL=… TYPESENSE_API_KEY=… node dist/search/reindex.js
 */
import { Pool } from 'pg';
import { TypesenseClient, TypesenseError } from './typesense';
import { AREA_DOCS_SQL, PLACE_DOCS_SQL } from './search.sql';
import { AREAS_SCHEMA, PLACES_SCHEMA, areaDoc, placeDoc, type AreaRow, type PlaceRow } from './search.index';

async function rebuild(ts: TypesenseClient, alias: string, schema: object, docs: object[]) {
  const name = `${alias}_${Date.now()}`;
  await ts.request('POST', '/collections', { name, ...schema });
  try {
    if (docs.length) {
      const body = docs.map((d) => JSON.stringify(d)).join('\n');
      const out = await ts.request<string>('POST', `/collections/${name}/documents/import?action=create`, body, true);
      const failures = out.split('\n').filter((l) => l && !l.includes('"success":true'));
      if (failures.length) throw new Error(`${alias}: ${failures.length} documents failed, e.g. ${failures[0]}`);
    }
  } catch (e) {
    await ts.request('DELETE', `/collections/${name}`).catch(() => undefined);   // never leave a half-built collection behind
    throw e;
  }
  let previous: string | null = null;
  try {
    previous = (await ts.request<{ collection_name: string }>('GET', `/aliases/${alias}`)).collection_name;
  } catch (e) {
    if (!(e instanceof TypesenseError && e.status === 404)) throw e;
  }
  await ts.request('PUT', `/aliases/${alias}`, { collection_name: name });
  if (previous && previous !== name) await ts.request('DELETE', `/collections/${previous}`);
  console.log(`${alias}: ${docs.length} documents → ${name}${previous ? ` (replaced ${previous})` : ''}`);
}

export async function reindex(): Promise<void> {
  const ts = TypesenseClient.fromEnv();
  if (!ts) throw new Error('TYPESENSE_URL and TYPESENSE_API_KEY must be set');
  const pool = new Pool({
    connectionString: process.env.DATABASE_URL ?? 'postgres://elaka360:elaka360@localhost:5432/elaka360',
    // Same visibility rule as the API: the index holds only what the public views return.
    options: `-c elaka360.include_unverified=${process.env.PUBLIC_INCLUDE_UNVERIFIED === 'true' ? 'on' : 'off'}`,
  });
  try {
    await ts.health();
    const areas = (await pool.query<AreaRow>(AREA_DOCS_SQL)).rows;
    const places = (await pool.query<PlaceRow>(PLACE_DOCS_SQL)).rows;
    await rebuild(ts, 'areas', AREAS_SCHEMA, areas.map(areaDoc));
    await rebuild(ts, 'places', PLACES_SCHEMA, places.map(placeDoc));
  } finally {
    await pool.end();
  }
}

if (require.main === module) {
  reindex().catch((e) => {
    console.error(e);
    process.exit(1);
  });
}
