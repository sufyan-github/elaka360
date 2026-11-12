/**
 * Bootstrap or change a staff role from the command line (the first super admin cannot be made through the API).
 * Usage: DATABASE_URL=… node dist/cli/grant-role.js +8801712345678 super_admin [scope_area_path]
 * The user must have signed in once. The change is written to the audit log with actor = null (CLI).
 */
import { Pool } from 'pg';
import { STAFF_ROLES } from '../common/auth/permissions';
import { normalisePhone } from '../common/auth/tokens';

async function main() {
  const [rawPhone, role, scopePath] = process.argv.slice(2);
  const phone = normalisePhone(rawPhone);
  if (!phone || !role || ![...STAFF_ROLES, 'user', 'contributor'].includes(role as never)) {
    console.error(`usage: grant-role <phone> <${[...STAFF_ROLES, 'user'].join('|')}> [scope_area_path]`);
    process.exit(2);
  }
  const pool = new Pool({ connectionString: process.env.DATABASE_URL });
  try {
    const scope = scopePath ? (await pool.query('SELECT id FROM admin_areas WHERE path = $1', [scopePath])).rows[0]?.id : null;
    if (scopePath && !scope) throw new Error(`unknown area path ${scopePath}`);
    const r = await pool.query('UPDATE users SET role = $2, scope_area_id = $3 WHERE phone = $1 RETURNING id', [phone, role, scope]);
    if (!r.rowCount) throw new Error('no user with that phone; sign in once first');
    await pool.query(`INSERT INTO audit_log(actor_id, action, entity, entity_id, after, reason) VALUES (NULL, 'user.role_cli', 'user', $1, $2, 'granted from CLI')`,
      [String(r.rows[0].id), JSON.stringify({ role, scope_area_id: scope })]);
    console.log(`user ${r.rows[0].id} → ${role}${scopePath ? ` (scope ${scopePath})` : ''}`);
  } finally {
    await pool.end();
  }
}

main().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
