import { BadRequestException, Controller, Get, Param, Query } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { PlacesService } from './places.service';
import { cursor, floatParam, intParam, searchTerms, searchText } from '../common/params';

const SLUG_RE = /^[a-z0-9-]{1,120}$/;
const CATEGORY_RE = /^[a-z_]{2,40}(\.[a-z_]{2,40})?$/;

function category(raw?: string): string | undefined {
  if (!raw) return undefined;
  if (!CATEGORY_RE.test(raw)) throw new BadRequestException('invalid category');
  return raw;
}

@ApiTags('places')
@Controller('v1/places')
export class PlacesController {
  constructor(private readonly places: PlacesService) {}

  @Get()
  @ApiOperation({ summary: 'Public places, filtered by area / category / text (all words must match); returns a total' })
  async list(
    @Query('area_id') areaId?: string, @Query('category') cat?: string, @Query('q') q?: string,
    @Query('sort') sort?: string, @Query('limit') limitRaw?: string, @Query('cursor') cur?: string,
  ) {
    const limit = intParam(limitRaw, 'limit', { min: 1, max: 100, def: 20 })!;
    const offset = cursor.decode(cur);
    if (sort && sort !== 'relevance' && sort !== 'name') throw new BadRequestException('sort must be relevance or name');
    const terms = q ? searchTerms(searchText(q, { min: 1 })) : undefined;
    const { items, total } = await this.places.list({
      areaId: intParam(areaId, 'area_id', { min: 1 }), category: category(cat), terms, limit, offset, sort: sort as 'relevance' | 'name' | undefined,
    });
    return { items, total, next_cursor: offset + items.length < total ? cursor.encode(offset + limit) : null };
  }

  @Get('nearby')
  @ApiOperation({ summary: 'Public places within radius_m of a point, nearest first (PostGIS)' })
  async nearby(@Query('lat') lat?: string, @Query('lon') lon?: string, @Query('radius_m') radius?: string, @Query('category') cat?: string, @Query('limit') limitRaw?: string) {
    const items = await this.places.nearby(
      floatParam(lat, 'lat', 20, 27), floatParam(lon, 'lon', 88, 93),
      intParam(radius, 'radius_m', { min: 100, max: 50000, def: 2000 })!, category(cat),
      intParam(limitRaw, 'limit', { min: 1, max: 100, def: 30 })!,
    );
    return { items, next_cursor: null };
  }

  @Get('geojson')
  @ApiOperation({ summary: 'Map pins as GeoJSON; optional bbox=west,south,east,north limits to the viewport' })
  geojson(@Query('area_id') areaId?: string, @Query('category') cat?: string, @Query('bbox') bbox?: string) {
    let box: [number, number, number, number] | null = null;
    if (bbox) {
      const n = bbox.split(',').map(Number);
      if (n.length !== 4 || n.some((x) => !Number.isFinite(x)) || n[0]! >= n[2]! || n[1]! >= n[3]!) throw new BadRequestException('bbox must be west,south,east,north');
      box = n as [number, number, number, number];
    }
    return this.places.geojson(intParam(areaId, 'area_id', { min: 1 }), category(cat), box);
  }

  @Get(':slug')
  bySlug(@Param('slug') slug: string) {
    if (!SLUG_RE.test(slug)) throw new BadRequestException('invalid slug');
    return this.places.bySlug(slug);
  }
}
