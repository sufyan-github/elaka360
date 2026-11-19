/**
 * Fill the duplicate review queue (duplicate_candidates) from every active place. Staff decide each pair in the admin
 * app (Duplicates); nothing is merged here. Safe to re-run: pairs already recorded, whatever their status, are skipped.
 * Usage: DATABASE_URL=… node dist/cli/duplicate-scan.js        (pnpm db:duplicates)
 */
import { Pool } from 'pg';
import { REVIEW_THRESHOLD } from '../quality/duplicates';
import { DUP_BULK_SCAN_SQL } from '../quality/duplicates.sql';

async function main() {
  const pool = new Pool({ connectionString: process.env.DATABASE_URL ?? 'postgres://elaka360:elaka360@localhost:5432/elaka360' });
  const t0 = Date.now();
  try {
    const c = await pool.connect();
    try {
      await c.query(`SET statement_timeout = '30min'`);
      const r = await c.query(DUP_BULK_SCAN_SQL, [REVIEW_THRESHOLD]);
      const open = (await c.query(`SELECT count(*)::int AS n FROM duplicate_candidates WHERE status = 'open'`)).rows[0].n;
      await c.query(`INSERT INTO audit_log(actor_id, action, entity, entity_id, after, reason)
                     VALUES (NULL, 'duplicates.bulk_scan', 'duplicate_candidates', 'all', $1, 'duplicate scan from CLI')`,
        [JSON.stringify({ new_pairs: r.rowCount, open })]);
      console.log(`duplicate scan: ${r.rowCount} new pairs, ${open} open in the queue (${Math.round((Date.now() - t0) / 1000)} s)`);
    } finally {
      c.release();
    }
  } finally {
    await pool.end();
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
