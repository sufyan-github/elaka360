import { BadRequestException, Controller, Get, Param, ParseIntPipe, Query } from '@nestjs/common';
import { GeoService } from './geo.service';
import { cursor, intParam, normalisePath } from '../common/params';

const LEVELS = new Set(['division', 'district', 'upazila', 'city_corporation', 'pourashava', 'union']);

@Controller('v1')
export class GeoController {
  constructor(private readonly geo: GeoService) {}

  /** GET /v1/stats/national — live counts for the Home "about" strip. */
  @Get('stats/national')
  national() {
    return this.geo.nationalStats();
  }

  /** GET /v1/areas?level=district&parent_id=10002&limit=100&cursor=… */
  @Get('areas')
  async list(
    @Query('level') level = 'division',
    @Query('parent_id') parentId?: string,
    @Query('limit') limitRaw?: string,
    @Query('cursor') cur?: string,
  ) {
    if (!LEVELS.has(level)) throw new BadRequestException(`level must be one of ${[...LEVELS].join(', ')}`);
    const limit = intParam(limitRaw, 'limit', { min: 1, max: 500, def: 100 })!;
    const offset = cursor.decode(cur);
    const items = await this.geo.list(level, intParam(parentId, 'parent_id'), limit, offset);
    return { items, next_cursor: items.length === limit ? cursor.encode(offset + limit) : null };
  }

  /** GET /v1/areas/by-path?path=rajshahi/rajshahi/paba */
  @Get('areas/by-path')
  byPath(@Query('path') path?: string) {
    return this.geo.detailByPath(normalisePath(path));
  }

  @Get('areas/:id')
  byId(@Param('id', ParseIntPipe) id: number) {
    return this.geo.detailById(id);
  }

  @Get('areas/:id/children')
  children(@Param('id', ParseIntPipe) id: number, @Query('level') level?: string) {
    if (level && !LEVELS.has(level)) throw new BadRequestException('invalid level');
    return this.geo.children(id, level);
  }
}
