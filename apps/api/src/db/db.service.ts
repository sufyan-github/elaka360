import { Injectable, Logger, OnModuleDestroy } from '@nestjs/common';
import { Pool, PoolClient, QueryResultRow } from 'pg';

export const INCLUDE_UNVERIFIED = process.env.PUBLIC_INCLUDE_UNVERIFIED === 'true';

export interface Queryable {
  many<T extends QueryResultRow>(sql: string, params?: unknown[]): Promise<T[]>;
  one<T extends QueryResultRow>(sql: string, params?: unknown[]): Promise<T | null>;
}

@Injectable()
export class Db implements OnModuleDestroy, Queryable {
  private readonly log = new Logger('Db');
  readonly pool = new Pool({
    connectionString: process.env.DATABASE_URL ?? 'postgres://elaka360:elaka360@localhost:5432/elaka360',
    max: Number(process.env.DB_POOL_MAX ?? 10),
    connectionTimeoutMillis: 5000,
    idleTimeoutMillis: 30000,
    // Public read views (db/migrations/0005) honour this setting; see docs/data/DATA_TRUST_POLICY.md.
    options: `-c statement_timeout=${Number(process.env.DB_STATEMENT_TIMEOUT_MS ?? 8000)} -c elaka360.include_unverified=${INCLUDE_UNVERIFIED ? 'on' : 'off'}`,
  });

  constructor() {
    this.pool.on('error', (e) => this.log.error(`idle client error: ${e.message}`));
  }

  async many<T extends QueryResultRow>(sql: string, params: unknown[] = []): Promise<T[]> {
    const res = await this.pool.query<T>(sql, params);
    return res.rows;
  }

  async one<T extends QueryResultRow>(sql: string, params: unknown[] = []): Promise<T | null> {
    const rows = await this.many<T>(sql, params);
    return rows[0] ?? null;
  }

  /** Run fn inside a transaction; rolls back on any error. */
  async tx<R>(fn: (q: Queryable & { client: PoolClient }) => Promise<R>): Promise<R> {
    const client = await this.pool.connect();
    const q: Queryable & { client: PoolClient } = {
      client,
      many: async <T extends QueryResultRow>(sql: string, params: unknown[] = []): Promise<T[]> => (await client.query<T>(sql, params)).rows,
      one: async <T extends QueryResultRow>(sql: string, params: unknown[] = []): Promise<T | null> => (await client.query<T>(sql, params)).rows[0] ?? null,
    };
    try {
      await client.query('BEGIN');
      const out = await fn(q);
      await client.query('COMMIT');
      return out;
    } catch (e) {
      await client.query('ROLLBACK').catch(() => undefined);
      throw e;
    } finally {
      client.release();
    }
  }

  async onModuleDestroy() {
    await this.pool.end();
  }
}

/** Append one audit record (inside the caller's transaction). */
export async function audit(
  q: Queryable,
  e: { actor: number | null; action: string; entity: string; entityId: string | number; before?: unknown; after?: unknown; reason?: string | null; requestId?: string; ip?: string | null },
) {
  await q.many(
    `INSERT INTO audit_log(actor_id, action, entity, entity_id, before, after, diff, reason, request_id, ip)
     VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::inet)`,
    [e.actor, e.action, e.entity, String(e.entityId), json(e.before), json(e.after), json(diff(e.before, e.after)), e.reason ?? null, e.requestId ?? null, e.ip ?? null],
  );
}

function json(v: unknown) {
  return v === undefined || v === null ? null : JSON.stringify(v);
}

/** Field-level diff of two flat objects: {field: [before, after]}. */
export function diff(before: unknown, after: unknown): Record<string, [unknown, unknown]> | null {
  if (!before || !after || typeof before !== 'object' || typeof after !== 'object') return null;
  const out: Record<string, [unknown, unknown]> = {};
  const b = before as Record<string, unknown>;
  const a = after as Record<string, unknown>;
  for (const k of new Set([...Object.keys(b), ...Object.keys(a)])) {
    if (JSON.stringify(b[k]) !== JSON.stringify(a[k])) out[k] = [b[k] ?? null, a[k] ?? null];
  }
  return Object.keys(out).length ? out : null;
}
