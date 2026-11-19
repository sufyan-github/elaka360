import { Injectable, NotFoundException } from '@nestjs/common';
import type { AdminAreaSummary, Place, PlaceSummary } from '@elaka360/shared';
import { Db } from '../db/db.service';
import { BREADCRUMB_SQL } from '../geo/geo.sql';
import * as Q from './places.sql';

export interface PlaceQuery {
  areaId?: number;
  category?: string;
  terms?: string[];
  limit: number;
  offset: number;
  sort?: 'relevance' | 'name';
}

@Injectable()
export class PlacesService {
  constructor(private readonly db: Db) {}

  async list(f: PlaceQuery): Promise<{ items: PlaceSummary[]; total: number }> {
    const params = [f.areaId ?? null, f.category ?? null, f.terms?.length ? f.terms : null];
    const [items, count] = await Promise.all([
      this.db.many<PlaceSummary>(Q.PLACE_LIST_SQL, [...params, f.limit, f.offset, f.sort ?? 'relevance']),
      this.db.one<{ n: number }>(Q.PLACE_COUNT_SQL, params),
    ]);
    return { items, total: count?.n ?? 0 };
  }

  nearby(lat: number, lon: number, radiusM: number, category: string | undefined, limit: number): Promise<PlaceSummary[]> {
    return this.db.many<PlaceSummary>(Q.PLACE_NEARBY_SQL, [lat, lon, radiusM, category ?? null, limit]);
  }

  async geojson(areaId: number | undefined, category: string | undefined, bbox: [number, number, number, number] | null) {
    const rows = await this.db.many<PlaceSummary>(Q.PLACE_GEO_SQL, [areaId ?? null, category ?? null, ...(bbox ?? [null, null, null, null])]);
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
    const row = await this.db.one<Place & { area_id: number | null; place_id: number }>(Q.PLACE_DETAIL_SQL, [slug]);
    if (!row) throw new NotFoundException(`place not found: ${slug}`);
    const { area_id, place_id: _id, ...place } = row;
    const breadcrumb = area_id ? await this.db.many<AdminAreaSummary>(BREADCRUMB_SQL, [area_id]) : [];
    return { ...place, breadcrumb };
  }

  async idOf(slug: string): Promise<number> {
    const row = await this.db.one<{ id: number }>(Q.PLACE_ID_SQL, [slug]);
    if (!row) throw new NotFoundException(`place not found: ${slug}`);
    return row.id;
  }
}
