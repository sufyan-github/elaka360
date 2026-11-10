import { Injectable, Logger } from '@nestjs/common';
import type { AdminAreaSummary, PlaceSummary } from '@elaka360/shared';
import { latinKey } from '@elaka360/shared';
import { Db } from '../db/db.service';
import { PLACE_LIST_SQL } from '../places/places.sql';
import { searchTerms } from '../common/params';
import { TypesenseClient } from './typesense';
import { toAreaSummary, toPlaceSummary, type AreaDoc, type PlaceDoc } from './search.index';
import { AREA_SEARCH_SQL, SUGGEST_SQL } from './search.sql';

export interface SearchResult {
  engine: 'typesense' | 'postgres';
  areas: AdminAreaSummary[];
  places: PlaceSummary[];
}

export interface SearchFilters {
  type?: 'area' | 'place';
  level?: string;
  category?: string;
  areaId?: number;
  areaPath?: string;
}

export interface Suggestion {
  kind: 'area' | 'place';
  name_bn: string;
  name_en: string;
  href_key: string;
  detail: string;
}

const COOL_DOWN_MS = Number(process.env.SEARCH_COOLDOWN_MS ?? 30000);

@Injectable()
export class SearchService {
  private readonly log = new Logger(SearchService.name);
  private readonly ts = TypesenseClient.fromEnv();
  /** Circuit breaker: after a Typesense failure, skip it until this time (finding C6). */
  private downUntil = 0;
  private lastError: string | null = null;

  constructor(private readonly db: Db) {}

  get engine(): 'typesense' | 'postgres' {
    return this.ts && Date.now() >= this.downUntil ? 'typesense' : 'postgres';
  }

  health() {
    if (!this.ts) return { engine: 'postgres', configured: false };
    return { engine: this.engine, configured: true, circuit: Date.now() < this.downUntil ? 'open' : 'closed', last_error: this.lastError };
  }

  async search(q: string, f: SearchFilters = {}, limit = 20): Promise<SearchResult> {
    // Area-scoped queries go to Postgres, which knows the hierarchy precisely.
    if (this.ts && !f.areaPath && !f.areaId && Date.now() >= this.downUntil) {
      try {
        const out = await this.typesense(this.ts, q, f, limit);
        this.lastError = null;
        return out;
      } catch (e) {
        this.downUntil = Date.now() + COOL_DOWN_MS;
        this.lastError = (e as Error).message.slice(0, 200);
        this.log.warn(`Typesense unavailable for ${COOL_DOWN_MS / 1000}s, using Postgres: ${this.lastError}`);
      }
    }
    return this.postgres(q, f, limit);
  }

  async suggest(q: string, limit = 8): Promise<Suggestion[]> {
    return this.db.many<Suggestion>(SUGGEST_SQL, [q, /[a-z]/i.test(q) ? latinKey(q) : '', limit]);
  }

  private async typesense(ts: TypesenseClient, q: string, f: SearchFilters, limit: number): Promise<SearchResult> {
    const common = { q, query_by: 'name_bn,name_en,aliases', prefix: 'true', per_page: limit, num_typos: 2, typo_tokens_threshold: 1 };
    const searches: Record<string, unknown>[] = [];
    if (f.type !== 'place') searches.push({ collection: 'areas', ...common, sort_by: '_text_match:desc,level_rank:desc', ...(f.level ? { filter_by: `level:=${f.level}` } : {}) });
    if (f.type !== 'area') searches.push({ collection: 'places', ...common, sort_by: '_text_match:desc,rank:desc', ...(f.category ? { filter_by: `category_key:=${f.category} || subcategory_key:=${f.category}` } : {}) });
    const { results } = await ts.multiSearch<AreaDoc | PlaceDoc>(searches);
    const err = results.find((r) => r.error)?.error;
    if (err) throw new Error(err);
    const [first, second] = results;
    const areaRes = f.type === 'place' ? undefined : first;
    const placeRes = f.type === 'place' ? first : f.type === 'area' ? undefined : second;
    return {
      engine: 'typesense',
      areas: (areaRes?.hits ?? []).map((h) => toAreaSummary(h.document as AreaDoc)),
      places: (placeRes?.hits ?? []).map((h) => toPlaceSummary(h.document as PlaceDoc)),
    };
  }

  private async postgres(q: string, f: SearchFilters, limit: number): Promise<SearchResult> {
    const key = /[a-z]/i.test(q) ? latinKey(q) : '';
    const [areas, places] = await Promise.all([
      f.type === 'place' ? [] : this.db.many<AdminAreaSummary>(AREA_SEARCH_SQL, [q, key, f.level ?? null, f.areaPath ?? null, limit]),
      f.type === 'area' ? [] : this.db.many<PlaceSummary>(PLACE_LIST_SQL, [f.areaId ?? null, f.category ?? null, searchTerms(q), limit, 0, 'relevance']),
    ]);
    return { engine: 'postgres', areas, places };
  }
}
