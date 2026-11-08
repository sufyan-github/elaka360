import { Injectable, NotFoundException } from '@nestjs/common';
import type { AdminAreaSummary, Place, PlaceSummary } from '@elaka360/shared';
import { Db } from '../db/db.service';
import { BREADCRUMB_SQL } from '../geo/geo.sql';
import * as Q from './places.sql';

export interface PlaceQuery {
  areaId?: number;
  category?: string;
  q?: string;
  limit: number;
  offset: number;
}

@Injectable()
export class PlacesService {
  constructor(private readonly db: Db) {}

  list(f: PlaceQuery): Promise<PlaceSummary[]> {
    return this.db.many<PlaceSummary>(Q.PLACE_LIST_SQL, [f.areaId ?? null, f.category ?? null, f.q ?? null, f.limit, f.offset]);
  }

  nearby(lat: number, lon: number, radiusM: number, category: string | undefined, limit: number): Promise<PlaceSummary[]> {
    return this.db.many<PlaceSummary>(Q.PLACE_NEARBY_SQL, [lat, lon, radiusM, category ?? null, limit]);
  }

  async geojson(areaId: number | undefined, category: string | undefined) {
    const rows = await this.db.many<PlaceSummary>(Q.PLACE_GEO_SQL, [areaId ?? null, category ?? null]);
    return {
      type: 'FeatureCollection' as const,
      features: rows.map(({ lat, lon, ...props }) => ({
        type: 'Feature' as const,
        geometry: { type: 'Point' as const, coordinates: [lon, lat] },
        properties: props,
      })),
    };
  }

  async bySlug(slug: string): Promise<Place> {
    const row = await this.db.one<Place & { area_id: number | null }>(Q.PLACE_DETAIL_SQL, [slug]);
    if (!row) throw new NotFoundException(`place not found: ${slug}`);
    const { area_id, ...place } = row;
    const breadcrumb = area_id ? await this.db.many<AdminAreaSummary>(BREADCRUMB_SQL, [area_id]) : [];
    return { ...place, breadcrumb };
  }
}
