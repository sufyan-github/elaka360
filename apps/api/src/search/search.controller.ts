import { BadRequestException, Controller, Get, Query } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { Db } from '../db/db.service';
import { SearchService, type SearchResult } from './search.service';
import { intParam, normalisePath, searchText } from '../common/params';

const LEVELS = new Set(['division', 'district', 'upazila', 'city_corporation', 'pourashava', 'union']);

@ApiTags('search')
@Controller('v1/search')
export class SearchController {
  constructor(private readonly search: SearchService, private readonly db: Db) {}

  @Get()
  @ApiOperation({ summary: 'Search areas and places (Bangla, English, Banglish; typo-tolerant). Filters: type, level, category, area (path)' })
  async find(
    @Query('q') raw?: string, @Query('type') type?: string, @Query('level') level?: string,
    @Query('category') category?: string, @Query('area') area?: string, @Query('limit') limitRaw?: string,
  ): Promise<SearchResult> {
    const q = searchText(raw);
    if (type && type !== 'area' && type !== 'place') throw new BadRequestException('type must be area or place');
    if (level && !LEVELS.has(level)) throw new BadRequestException('invalid level');
    if (category && !/^[a-z_]{2,40}(\.[a-z_]{2,40})?$/.test(category)) throw new BadRequestException('invalid category');
    let areaPath: string | undefined;
    let areaId: number | undefined;
    if (area) {
      areaPath = normalisePath(area);
      const row = await this.db.one<{ id: number }>('SELECT id::int FROM public_admin_areas WHERE path = $1', [areaPath]);
      if (!row) throw new BadRequestException('unknown area');
      areaId = row.id;
    }
    const limit = intParam(limitRaw, 'limit', { min: 1, max: 50, def: 20 })!;
    return this.search.search(q, { type: type as 'area' | 'place' | undefined, level, category, areaPath, areaId }, limit);
  }

  @Get('suggest')
  @ApiOperation({ summary: 'Up to 8 area and 8 place name suggestions for a prefix' })
  async suggest(@Query('q') raw?: string) {
    return { items: await this.search.suggest(searchText(raw, { min: 1, max: 60 })) };
  }
}
