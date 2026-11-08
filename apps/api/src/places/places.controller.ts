import { Controller, Get, Param, Query } from '@nestjs/common';
import { PlacesService } from './places.service';
import { cursor, floatParam, intParam } from '../common/params';

@Controller('v1/places')
export class PlacesController {
  constructor(private readonly places: PlacesService) {}

  /** GET /v1/places?area_id=20015&category=education&q=…&limit=20&cursor=… */
  @Get()
  async list(
    @Query('area_id') areaId?: string,
    @Query('category') category?: string,
    @Query('q') q?: string,
    @Query('limit') limitRaw?: string,
    @Query('cursor') cur?: string,
  ) {
    const limit = intParam(limitRaw, 'limit', { min: 1, max: 100, def: 20 })!;
    const offset = cursor.decode(cur);
    const items = await this.places.list({ areaId: intParam(areaId, 'area_id'), category: category || undefined, q: q?.trim() || undefined, limit, offset });
    return { items, next_cursor: items.length === limit ? cursor.encode(offset + limit) : null };
  }

  /** GET /v1/places/nearby?lat=24.37&lon=88.60&radius_m=2000&category=health */
  @Get('nearby')
  async nearby(
    @Query('lat') lat?: string,
    @Query('lon') lon?: string,
    @Query('radius_m') radius?: string,
    @Query('category') category?: string,
    @Query('limit') limitRaw?: string,
  ) {
    const items = await this.places.nearby(
      floatParam(lat, 'lat', 20, 27),
      floatParam(lon, 'lon', 88, 93),
      intParam(radius, 'radius_m', { min: 100, max: 50000, def: 2000 })!,
      category || undefined,
      intParam(limitRaw, 'limit', { min: 1, max: 100, def: 30 })!,
    );
    return { items, next_cursor: null };
  }

  @Get(':slug')
  bySlug(@Param('slug') slug: string) {
    return this.places.bySlug(slug);
  }
}
