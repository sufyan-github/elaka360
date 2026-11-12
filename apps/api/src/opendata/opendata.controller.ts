import { BadRequestException, Body, Controller, Delete, Get, HttpException, HttpStatus, Injectable, NotFoundException, Param, Post, Query, Req, Res, UnauthorizedException, type CanActivate, type ExecutionContext, UseGuards } from '@nestjs/common';
import { ApiHeader, ApiOperation, ApiTags } from '@nestjs/swagger';
import { SkipThrottle } from '@nestjs/throttler';
import { randomBytes } from 'node:crypto';
import type { Response } from 'express';
import { Db, audit } from '../db/db.service';
import { CurrentUser, RequireAuth, type AuthUser, type AuthedRequest } from '../common/auth/auth.guard';
import { sha256 } from '../common/auth/tokens';
import { body, cursor, idParam, intParam, textField } from '../common/params';
import * as Q from './opendata.sql';

const LICENSE_NOTICE =
  'Each record names its source (source_key; see /v1/open-data/sources). Reuse must follow that source\'s licence and ' +
  'credit it — e.g. facts from Wikipedia are CC BY-SA 4.0 (attribution + share-alike). Only records with official or ' +
  'secondary evidence are exported; nothing here is officially verified unless evidence_level is "official".';

/** API-key check + per-key, per-minute limit counted in Postgres (works across replicas). */
@Injectable()
export class ApiKeyGuard implements CanActivate {
  constructor(private readonly db: Db) {}
  async canActivate(ctx: ExecutionContext): Promise<boolean> {
    const req = ctx.switchToHttp().getRequest<AuthedRequest>();
    const res = ctx.switchToHttp().getResponse<Response>();
    const key = req.header('x-api-key');
    if (!key || !/^e360_[A-Za-z0-9_-]{30,60}$/.test(key)) throw new UnauthorizedException('X-API-Key header required');
    const hit = await this.db.one<{ id: number; rate_per_min: number; count: number }>(Q.OD_KEY_HIT_SQL, [sha256(key)]);
    if (!hit) throw new UnauthorizedException('unknown or revoked API key');
    res.setHeader('X-RateLimit-Limit', String(hit.rate_per_min));
    res.setHeader('X-RateLimit-Remaining', String(Math.max(0, hit.rate_per_min - hit.count)));
    if (hit.count > hit.rate_per_min) throw new HttpException('rate limit exceeded for this key', HttpStatus.TOO_MANY_REQUESTS);
    return true;
  }
}

function csv(rows: Record<string, unknown>[]): string {
  if (!rows.length) return '';
  const cols = Object.keys(rows[0]!);
  const cell = (v: unknown) => {
    const s = v === null || v === undefined ? '' : typeof v === 'object' ? JSON.stringify(v) : String(v);
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return '﻿' + [cols.join(','), ...rows.map((r) => cols.map((c) => cell(r[c])).join(','))].join('\r\n') + '\r\n';
}

@ApiTags('open-data')
@ApiHeader({ name: 'X-API-Key', required: true })
@Controller('v1/open-data')
@UseGuards(ApiKeyGuard)
@SkipThrottle()
export class OpenDataController {
  constructor(private readonly db: Db) {}

  private async page(sql: string, filter: string | null, limitRaw: string | undefined, cur: string | undefined, format: string | undefined, res: Response, name: string) {
    const limit = intParam(limitRaw, 'limit', { min: 1, max: 5000, def: 1000 })!;
    const offset = cursor.decode(cur);
    if (format && format !== 'json' && format !== 'csv') throw new BadRequestException('format must be json or csv');
    const items = await this.db.many<Record<string, unknown>>(sql, [filter, limit, offset]);
    const next = items.length === limit ? cursor.encode(offset + limit) : null;
    res.setHeader('Cache-Control', 'public, max-age=300');
    if (format === 'csv') {
      res.setHeader('Content-Type', 'text/csv; charset=utf-8');
      res.setHeader('Content-Disposition', `attachment; filename="elaka360-${name}.csv"`);
      if (next) res.setHeader('Link', `<?cursor=${next}&limit=${limit}&format=csv>; rel="next"`);
      res.send(csv(items));
      return;
    }
    res.json({ license_notice: LICENSE_NOTICE, items, next_cursor: next });
  }

  @Get('areas')
  @ApiOperation({ summary: 'Sourced admin areas (JSON or ?format=csv), cursor-paginated' })
  areas(@Res() res: Response, @Query('level') level?: string, @Query('limit') l?: string, @Query('cursor') c?: string, @Query('format') f?: string) {
    if (level && !['division', 'district', 'upazila', 'city_corporation', 'pourashava', 'union'].includes(level)) throw new BadRequestException('invalid level');
    return this.page(Q.OD_AREAS_SQL, level ?? null, l, c, f, res, 'areas');
  }

  @Get('places')
  @ApiOperation({ summary: 'Sourced places (JSON or ?format=csv), cursor-paginated' })
  places(@Res() res: Response, @Query('category') cat?: string, @Query('limit') l?: string, @Query('cursor') c?: string, @Query('format') f?: string) {
    if (cat && !/^[a-z_]{2,40}(\.[a-z_]{2,40})?$/.test(cat)) throw new BadRequestException('invalid category');
    return this.page(Q.OD_PLACES_SQL, cat ?? null, l, c, f, res, 'places');
  }

  @Get('sources')
  @ApiOperation({ summary: 'Sources cited by exported records, with licences where known' })
  async sources() {
    return { license_notice: LICENSE_NOTICE, items: await this.db.many(Q.OD_SOURCES_SQL) };
  }
}

@ApiTags('admin')
@Controller('v1/admin/api-keys')
export class ApiKeysController {
  constructor(private readonly db: Db) {}

  @Get()
  @RequireAuth('users.manage')
  async list() {
    return { items: await this.db.many(Q.OD_KEYS_LIST_SQL) };
  }

  @Post()
  @RequireAuth('users.manage')
  @ApiOperation({ summary: 'Issue an Open Data key; the key is returned once and stored only as a hash' })
  async create(@CurrentUser() u: AuthUser, @Body() raw: unknown, @Req() req: AuthedRequest) {
    const b = body(raw);
    const name = textField(b, 'name', { max: 80, min: 3, required: true })!;
    const rate = intParam(b.rate_per_min === undefined ? undefined : String(b.rate_per_min), 'rate_per_min', { min: 1, max: 6000, def: 60 })!;
    const key = `e360_${randomBytes(30).toString('base64url')}`;
    return this.db.tx(async (q) => {
      const row = await q.one<{ id: number }>('INSERT INTO api_keys(name, key_prefix, key_hash, rate_per_min, created_by) VALUES ($1,$2,$3,$4,$5) RETURNING id',
        [name, key.slice(0, 10), sha256(key), rate, u.id]);
      await audit(q, { actor: u.id, action: 'api_key.create', entity: 'api_key', entityId: row!.id, after: { name, rate_per_min: rate }, requestId: req.id, ip: req.ip });
      return { id: row!.id, name, rate_per_min: rate, key };
    });
  }

  @Delete(':id')
  @RequireAuth('users.manage')
  async revoke(@CurrentUser() u: AuthUser, @Param('id') idRaw: string, @Req() req: AuthedRequest) {
    const id = idParam(idRaw);
    return this.db.tx(async (q) => {
      const r = await q.many('UPDATE api_keys SET revoked_at = now() WHERE id = $1 AND revoked_at IS NULL RETURNING id', [id]);
      if (!r.length) throw new NotFoundException('active key not found');
      await audit(q, { actor: u.id, action: 'api_key.revoke', entity: 'api_key', entityId: id, requestId: req.id, ip: req.ip });
      return { revoked: true };
    });
  }
}
