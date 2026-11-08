import { BadRequestException, Controller, Get, Query } from '@nestjs/common';
import type { AdminAreaSummary, PlaceSummary } from '@elaka360/shared';
import { Db } from '../db/db.service';
import { AREA_SUMMARY_COLS } from '../geo/geo.sql';
import { PLACE_LIST_SQL } from '../places/places.sql';

/** Interim search over Postgres until Typesense lands (Phase 1). $1 raw text, $2 latin key */
export const AREA_SEARCH_SQL = `
SELECT ${AREA_SUMMARY_COLS} FROM admin_areas a
WHERE a.level <> 'country' AND (
  a.name_bn ILIKE $1 || '%' OR a.name_bn ILIKE '% ' || $1 || '%'
  OR a.name_en ILIKE $1 || '%' OR a.name_en ILIKE '% ' || $1 || '%'
  OR ($2 <> '' AND regexp_replace(lower(a.name_en), '[^a-z0-9]', '', 'g') LIKE $2 || '%'))
ORDER BY array_position(ARRAY['division','district','city_corporation','upazila','pourashava','union']::text[], a.level::text), a.name_en
LIMIT 20`;

@Controller('v1/search')
export class SearchController {
  constructor(private readonly db: Db) {}

  /** GET /v1/search?q=রাজশাহী  or  ?q=rajshahi */
  @Get()
  async search(@Query('q') raw?: string): Promise<{ areas: AdminAreaSummary[]; places: PlaceSummary[] }> {
    const q = (raw ?? '').trim();
    if (q.length < 2) throw new BadRequestException('q must be at least 2 characters');
    if (q.length > 80) throw new BadRequestException('q is too long');
    const plain = q.replace(/[%_\\]/g, '');
    const key = /[a-z]/i.test(plain) ? plain.toLowerCase().replace(/[^a-z0-9]/g, '') : '';
    const [areas, places] = await Promise.all([
      this.db.many<AdminAreaSummary>(AREA_SEARCH_SQL, [plain, key]),
      this.db.many<PlaceSummary>(PLACE_LIST_SQL, [null, null, plain, 20, 0]),
    ]);
    return { areas, places };
  }
}
