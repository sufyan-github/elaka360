import { BadRequestException, Body, Controller, Get, NotFoundException, Param, Patch, Post, Query, Req } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import type { DataSource, UserRole } from '@elaka360/shared';
import { Db, audit } from '../db/db.service';
import { CurrentUser, RequireAuth, type AuthUser, type AuthedRequest } from '../common/auth/auth.guard';
import { assignableRoles } from '../common/auth/permissions';
import { body, idParam, intParam, textField, urlField } from '../common/params';
import * as Q from './admin.sql';
import { page, paged } from './admin.util';

const SOURCE_TYPES = ['government_portal', 'gazette', 'census', 'census_aggregator', 'encyclopedia', 'news', 'institution_website',
  'community_dataset', 'project_reconciliation', 'field_survey', 'design_placeholder', 'none', 'unknown'];

function dateField(b: Record<string, unknown>, k: string): string | null | undefined {
  if (b[k] === undefined) return undefined;
  if (b[k] === null || b[k] === '') return null;
  if (typeof b[k] !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(b[k] as string)) throw new BadRequestException(`${k} must be YYYY-MM-DD`);
  return b[k] as string;
}

@ApiTags('admin')
@Controller('v1/admin')
export class AdminSourcesUsersController {
  constructor(private readonly db: Db) {}

  @Get('sources')
  @RequireAuth('sources.read')
  async sources(): Promise<{ items: DataSource[] }> {
    return { items: await this.db.many<DataSource>(Q.ADMIN_SOURCES_SQL) };
  }

  @Post('sources')
  @RequireAuth('sources.edit')
  @ApiOperation({ summary: 'Register a source. Search-result pages are rejected; trust 4–5 is for government/BBS/gazette.' })
  async createSource(@CurrentUser() u: AuthUser, @Body() raw: unknown, @Req() req: AuthedRequest) {
    const b = body(raw);
    const key = textField(b, 'key', { max: 40, min: 2, required: true })!.toUpperCase();
    if (!/^[A-Z0-9_]+$/.test(key)) throw new BadRequestException('key: letters, digits and _ only');
    const v = this.sourceFields(b, true);
    return this.db.tx(async (q) => {
      const row = await q.one<{ id: number }>(
        `INSERT INTO data_sources(key, name, url, license, trust_level, source_type, organization, access_date, publication_date, evidence_notes)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) RETURNING id`,
        [key, v.name, v.url ?? null, v.license ?? null, v.trust_level ?? 2, v.source_type ?? 'unknown', v.organization ?? null, v.access_date ?? null, v.publication_date ?? null, v.evidence_notes ?? null]);
      await audit(q, { actor: u.id, action: 'source.create', entity: 'data_source', entityId: row!.id, after: { key, ...v }, requestId: req.id, ip: req.ip });
      return row;
    });
  }

  @Patch('sources/:id')
  @RequireAuth('sources.edit')
  async updateSource(@CurrentUser() u: AuthUser, @Param('id') idRaw: string, @Body() raw: unknown, @Req() req: AuthedRequest) {
    const id = idParam(idRaw);
    const b = body(raw);
    const v = this.sourceFields(b, false);
    if (typeof b.active === 'boolean') v.active = b.active;
    return this.db.tx(async (q) => {
      const before = await q.one('SELECT * FROM data_sources WHERE id = $1 FOR UPDATE', [id]);
      if (!before) throw new NotFoundException('source not found');
      const cols = Object.keys(v);
      if (!cols.length) throw new BadRequestException('nothing to change');
      await q.many(`UPDATE data_sources SET ${cols.map((c, i) => `${c} = $${i + 2}`).join(', ')}, updated_at = now() WHERE id = $1`, [id, ...cols.map((c) => v[c])]);
      const after = await q.one('SELECT * FROM data_sources WHERE id = $1', [id]);
      await audit(q, { actor: u.id, action: 'source.update', entity: 'data_source', entityId: id, before, after, requestId: req.id, ip: req.ip });
      return after;
    });
  }

  @Get('users')
  @RequireAuth('users.manage')
  async users(@Query('q') q?: string, @Query('role') role?: string, @Query('limit') l?: string, @Query('cursor') c?: string) {
    const { limit, offset } = page(l, c);
    const rows = await this.db.many<{ total: number }>(Q.ADMIN_USERS_SQL, [q?.trim().slice(0, 40) || null, role || null, limit, offset]);
    return paged(rows, limit, offset);
  }

  @Get('users/:id')
  @RequireAuth('users.manage')
  async user(@Param('id') idRaw: string) {
    const row = await this.db.one(
      `SELECT u.id::int, u.name, u.phone, u.email, u.role::text, u.status, u.scope_area_id::int, a.path AS scope_path, u.points, u.level,
              u.totp_enabled_at IS NOT NULL AS mfa_enabled, to_char(u.created_at, 'YYYY-MM-DD') AS created_at,
              to_char(u.last_login_at, 'YYYY-MM-DD"T"HH24:MI:SSZ') AS last_login_at, to_char(u.deletion_requested_at, 'YYYY-MM-DD') AS deletion_requested_at,
              (SELECT count(*)::int FROM contributions c WHERE c.user_id = u.id) AS contributions,
              (SELECT count(*)::int FROM reviews r WHERE r.user_id = u.id) AS reviews
       FROM users u LEFT JOIN admin_areas a ON a.id = u.scope_area_id WHERE u.id = $1`, [idParam(idRaw)]);
    if (!row) throw new NotFoundException('user not found');
    return row;
  }

  @Patch('users/:id')
  @RequireAuth('users.manage')
  @ApiOperation({ summary: 'Change role, geographic scope or status (only a super admin can grant super admin)' })
  async updateUser(@CurrentUser() u: AuthUser, @Param('id') idRaw: string, @Body() raw: unknown, @Req() req: AuthedRequest) {
    const id = idParam(idRaw);
    if (id === u.id) throw new BadRequestException('you cannot change your own role, scope or status');
    const b = body(raw);
    const reason = textField(b, 'reason', { max: 500, min: 5, required: true });
    return this.db.tx(async (q) => {
      const before = await q.one<{ role: UserRole; status: string; scope_area_id: number | null }>('SELECT role::text, status, scope_area_id::int FROM users WHERE id = $1 FOR UPDATE', [id]);
      if (!before) throw new NotFoundException('user not found');
      const allowed = assignableRoles(u.role);
      if (!allowed.includes(before.role)) throw new BadRequestException('you cannot manage this user');
      let role: UserRole | null = null;
      if (b.role !== undefined) {
        if (!allowed.includes(b.role as UserRole)) throw new BadRequestException('you cannot assign that role');
        role = b.role as UserRole;
      }
      const status = b.status === undefined ? null : ['active', 'suspended'].includes(String(b.status)) ? String(b.status) : (() => { throw new BadRequestException('invalid status'); })();
      const scopeSet = b.scope_area_id !== undefined;
      const scope = b.scope_area_id == null ? null : intParam(String(b.scope_area_id), 'scope_area_id', { min: 1 })!;
      if (scope && !(await q.one('SELECT 1 AS x FROM admin_areas WHERE id = $1', [scope]))) throw new BadRequestException('unknown area');
      await q.many(`UPDATE users SET role = COALESCE($2::user_role, role), status = COALESCE($3, status),
                      scope_area_id = CASE WHEN $4::boolean THEN $5::bigint ELSE scope_area_id END, updated_at = now() WHERE id = $1`,
        [id, role, status, scopeSet, scope]);
      if (status === 'suspended') await q.many('UPDATE sessions SET revoked_at = now() WHERE user_id = $1 AND revoked_at IS NULL', [id]);
      const after = await q.one('SELECT role::text, status, scope_area_id::int FROM users WHERE id = $1', [id]);
      await audit(q, { actor: u.id, action: 'user.update', entity: 'user', entityId: id, before, after, reason, requestId: req.id, ip: req.ip });
      return after;
    });
  }

  private sourceFields(b: Record<string, unknown>, create: boolean) {
    const v: Record<string, unknown> = {};
    const name = textField(b, 'name', { max: 200, min: 3, required: create });
    if (name) v.name = name;
    if (b.url !== undefined) v.url = b.url ? urlField(b.url, 'url') : null;
    for (const k of ['license', 'organization', 'evidence_notes'] as const) if (b[k] !== undefined) v[k] = textField(b, k, { max: k === 'evidence_notes' ? 1000 : 120 });
    if (b.trust_level !== undefined) v.trust_level = intParam(String(b.trust_level), 'trust_level', { min: 1, max: 5 });
    if (b.source_type !== undefined) {
      if (!SOURCE_TYPES.includes(String(b.source_type))) throw new BadRequestException(`source_type must be one of ${SOURCE_TYPES.join(', ')}`);
      v.source_type = b.source_type;
    }
    if ((v.trust_level as number) >= 4 && v.source_type && !['government_portal', 'gazette', 'census'].includes(String(v.source_type))) {
      throw new BadRequestException('trust level 4–5 is reserved for government portals, gazettes and census publications');
    }
    for (const k of ['access_date', 'publication_date'] as const) {
      const d = dateField(b, k);
      if (d !== undefined) v[k] = d;
    }
    return v;
  }
}
