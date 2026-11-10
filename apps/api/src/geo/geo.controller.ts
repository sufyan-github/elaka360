import { BadRequestException, Controller, Get, Param, Query } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { GeoService } from './geo.service';
import { cursor, floatParam, idParam, intParam, normalisePath } from '../common/params';

const LEVELS = new Set(['division', 'district', 'upazila', 'city_corporation', 'pourashava', 'union', 'ward']);

@ApiTags('geo')
@Controller('v1')
export class GeoController {
  constructor(private readonly geo: GeoService) {}

  @Get('stats/national')
  @ApiOperation({ summary: 'Live public counts for the Home "about" strip, with the inclusion rule used' })
  national() {
    return this.geo.nationalStats();
  }

  @Get('areas')
  @ApiOperation({ summary: 'List public areas of one level, optionally under a parent (cursor-paginated)' })
  async list(@Query('level') level = 'division', @Query('parent_id') parentId?: string, @Query('limit') limitRaw?: string, @Query('cursor') cur?: string) {
    if (!LEVELS.has(level)) throw new BadRequestException(`level must be one of ${[...LEVELS].join(', ')}`);
    const limit = intParam(limitRaw, 'limit', { min: 1, max: 500, def: 100 })!;
    const offset = cursor.decode(cur);
    const items = await this.geo.list(level, intParam(parentId, 'parent_id', { min: 1 }), limit, offset);
    return { items, next_cursor: items.length === limit ? cursor.encode(offset + limit) : null };
  }

  @Get('areas/by-path')
  @ApiOperation({ summary: 'Area detail by URL path, e.g. rajshahi/rajshahi' })
  byPath(@Query('path') path?: string) {
    return this.geo.detailByPath(normalisePath(path));
  }

  @Get('areas/tree')
  @ApiOperation({ summary: 'Nested public subtree (default: Bangladesh, depth 2, max 3)' })
  tree(@Query('root_id') rootId?: string, @Query('depth') depth?: string) {
    return this.geo.tree(intParam(rootId, 'root_id', { min: 1, def: 1 })!, intParam(depth, 'depth', { min: 1, max: 3, def: 2 })!);
  }

  @Get('areas/:id')
  byId(@Param('id') id: string) {
    return this.geo.detailById(idParam(id));
  }

  @Get('areas/:id/children')
  children(@Param('id') id: string, @Query('level') level?: string) {
    if (level && !LEVELS.has(level)) throw new BadRequestException('invalid level');
    return this.geo.children(idParam(id), level);
  }

  @Get('areas/:id/stats')
  @ApiOperation({ summary: 'Counts of public and pending descendants, places per category, population and area with their basis' })
  stats(@Param('id') id: string) {
    return this.geo.stats(idParam(id));
  }

  @Get('areas/:id/boundary')
  @ApiOperation({ summary: 'Boundary polygon as a GeoJSON Feature (districts today)' })
  boundary(@Param('id') id: string) {
    return this.geo.boundary(idParam(id));
  }

  @Get('geo/locate')
  @ApiOperation({ summary: 'Which public area contains a point (resolves to the finest level with boundaries)' })
  locate(@Query('lat') lat?: string, @Query('lon') lon?: string) {
    return this.geo.locate(floatParam(lat, 'lat', 20, 27), floatParam(lon, 'lon', 88, 93));
  }
}
