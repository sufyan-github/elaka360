import { Injectable, NotFoundException } from '@nestjs/common';
import type { AdminArea, AdminAreaSummary, AreaDetail, LevelCounts, NationalStats } from '@elaka360/shared';
import { Db } from '../db/db.service';
import * as Q from './geo.sql';

@Injectable()
export class GeoService {
  constructor(private readonly db: Db) {}

  async detailByPath(path: string): Promise<AreaDetail> {
    const area = await this.db.one<AdminArea>(Q.AREA_DETAIL_SQL, [path]);
    if (!area) throw new NotFoundException(`area not found: ${path}`);
    const [breadcrumb, children, counts, places] = await Promise.all([
      this.db.many<AdminAreaSummary>(Q.BREADCRUMB_SQL, [area.id]),
      this.db.many<AdminAreaSummary>(Q.CHILDREN_SQL, [area.id, null]),
      this.db.many<{ level: string; n: number }>(Q.DESCENDANT_COUNTS_SQL, [area.id]),
      area.level === 'country'
        ? this.db.many<{ key: string; n: number }>(Q.NATIONAL_PLACE_COUNTS_SQL)
        : this.db.many<{ key: string; n: number }>(Q.PLACE_COUNTS_SQL, [area.id]),
    ]);
    const descendant_counts: LevelCounts = {};
    for (const r of counts) descendant_counts[r.level as keyof LevelCounts] = r.n;
    return {
      area,
      breadcrumb,
      children,
      descendant_counts,
      place_counts: Object.fromEntries(places.map((r) => [r.key, r.n])),
    };
  }

  async detailById(id: number): Promise<AreaDetail> {
    const row = await this.db.one<{ path: string }>(Q.AREA_BY_ID_PATH_SQL, [id]);
    if (!row) throw new NotFoundException(`area not found: ${id}`);
    return this.detailByPath(row.path);
  }

  children(id: number, level?: string): Promise<AdminAreaSummary[]> {
    return this.db.many<AdminAreaSummary>(Q.CHILDREN_SQL, [id, level ?? null]);
  }

  list(level: string, parentId: number | undefined, limit: number, offset: number): Promise<AdminAreaSummary[]> {
    return this.db.many<AdminAreaSummary>(Q.LIST_SQL, [level, parentId ?? null, limit, offset]);
  }

  async nationalStats(): Promise<NationalStats> {
    const row = await this.db.one<NationalStats>(Q.NATIONAL_STATS_SQL);
    return row as NationalStats;
  }
}
