import { Injectable, Logger } from '@nestjs/common';
import type { AdminAreaSummary, PlaceSummary } from '@elaka360/shared';
import { Db } from '../db/db.service';
import { PLACE_LIST_SQL } from '../places/places.sql';
import { TypesenseClient } from './typesense';
import { toAreaSummary, toPlaceSummary, type AreaDoc, type PlaceDoc } from './search.index';
import { AREA_SEARCH_SQL } from './search.sql';

export interface SearchResult {
  engine: 'typesense' | 'postgres';
  areas: AdminAreaSummary[];
  places: PlaceSummary[];
}

@Injectable()
export class SearchService {
  private readonly log = new Logger(SearchService.name);
  private readonly ts = TypesenseClient.fromEnv();

  constructor(private readonly db: Db) {}

  get engine(): 'typesense' | 'postgres' {
    return this.ts ? 'typesense' : 'postgres';
  }

  async search(q: string): Promise<SearchResult> {
    if (this.ts) {
      try {
        return await this.typesense(this.ts, q);
      } catch (e) {
        this.log.warn(`Typesense unavailable, falling back to Postgres: ${(e as Error).message}`);
      }
    }
    return this.postgres(q);
  }

  private async typesense(ts: TypesenseClient, q: string): Promise<SearchResult> {
    const common = { q, query_by: 'name_bn,name_en,aliases', prefix: 'true', per_page: 20, num_typos: 2, typo_tokens_threshold: 1 };
    const { results } = await ts.multiSearch<AreaDoc | PlaceDoc>([
      { collection: 'areas', ...common, sort_by: '_text_match:desc,level_rank:desc' },
      { collection: 'places', ...common, sort_by: '_text_match:desc,rank:desc' },
    ]);
    const [a, p] = results;
    if (a?.error || p?.error) throw new Error(a?.error ?? p?.error);
    return {
      engine: 'typesense',
      areas: (a?.hits ?? []).map((h) => toAreaSummary(h.document as AreaDoc)),
      places: (p?.hits ?? []).map((h) => toPlaceSummary(h.document as PlaceDoc)),
    };
  }

  private async postgres(q: string): Promise<SearchResult> {
    const plain = q.replace(/[%_\\]/g, '');
    const key = /[a-z]/i.test(plain) ? plain.toLowerCase().replace(/[^a-z0-9]/g, '') : '';
    const [areas, places] = await Promise.all([
      this.db.many<AdminAreaSummary>(AREA_SEARCH_SQL, [plain, key]),
      this.db.many<PlaceSummary>(PLACE_LIST_SQL, [null, null, plain, 20, 0]),
    ]);
    return { engine: 'postgres', areas, places };
  }
}
