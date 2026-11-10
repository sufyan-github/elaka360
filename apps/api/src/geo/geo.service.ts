import { Injectable, NotFoundException } from '@nestjs/common';
import type { AdminArea, AdminAreaSummary, AdminLevel, AreaDetail, AreaStats, AreaTreeNode, LevelCounts, LocateResult, NationalStats } from '@elaka360/shared';
import { Db, INCLUDE_UNVERIFIED } from '../db/db.service';
import * as Q from './geo.sql';

export const INCLUSION_RULE = INCLUDE_UNVERIFIED
  ? 'All active records, including ones not yet verified (labelled by evidence level).'
  : 'Only records that are production-eligible (official or secondary evidence with a named source).';

@Injectable()
export class GeoService {
  constructor(private readonly db: Db) {}

  async detailByPath(path: string): Promise<AreaDetail> {
    const area = await this.db.one<AdminArea>(Q.AREA_DETAIL_SQL, [path]);
    if (!area) throw new NotFoundException(`area not found: ${path}`);
    const [breadcrumb, children, counts, places] = await Promise.all([
      this.db.many<AdminAreaSummary>(Q.BREADCRUMB_SQL, [area.id]),
      this.db.many<AdminAreaSummary>(Q.CHILDREN_SQL, [area.id, null]),
      this.counts(area.id),
      this.placeCounts(area),
    ]);
    return { area, breadcrumb, children, ...counts, place_counts: places };
  }

  async detailById(id: number): Promise<AreaDetail> {
    return this.detailByPath(await this.pathOf(id));
  }

  async stats(id: number): Promise<AreaStats> {
    const area = await this.db.one<AdminArea>(Q.AREA_DETAIL_SQL, [await this.pathOf(id)]);
    if (!area) throw new NotFoundException(`area not found: ${id}`);
    const [counts, places] = await Promise.all([this.counts(id), this.placeCounts(area)]);
    return {
      area_id: id, ...counts, place_counts: places,
      population_2022: area.population_2022, population_basis: area.population_basis,
      area_km2: area.area_km2, area_basis: area.area_basis, inclusion_rule: INCLUSION_RULE,
    };
  }

  async tree(rootId: number, depth: number): Promise<AreaTreeNode> {
    const rows = await this.db.many<AreaTreeNode & { depth: number }>(Q.TREE_SQL, [rootId, depth]);
    if (!rows.length) throw new NotFoundException(`area not found: ${rootId}`);
    const byId = new Map<number, AreaTreeNode>();
    for (const { depth: _d, ...r } of rows) byId.set(r.id, { ...r });
    for (const node of byId.values()) {
      if (node.id === rootId || node.parent_id === null) continue;
      const parent = byId.get(node.parent_id);
      if (parent) (parent.children ??= []).push(node);
    }
    return byId.get(rootId)!;
  }

  async locate(lat: number, lon: number): Promise<LocateResult> {
    const [area, levels] = await Promise.all([
      this.db.one<AdminAreaSummary>(Q.LOCATE_SQL, [lat, lon]),
      this.db.many<{ level: AdminLevel }>(Q.BOUNDARY_LEVELS_SQL),
    ]);
    const breadcrumb = area ? await this.db.many<AdminAreaSummary>(Q.BREADCRUMB_SQL, [area.id]) : [];
    return { lat, lon, area, breadcrumb, resolved_levels: levels.map((l) => l.level) };
  }

  async boundary(id: number) {
    const row = await this.db.one<{ id: number; name_bn: string; name_en: string; level: string; geometry: unknown }>(Q.BOUNDARY_SQL, [id]);
    if (!row) throw new NotFoundException(`no public boundary for area ${id}`);
    const { geometry, ...properties } = row;
    return { type: 'Feature' as const, id: row.id, properties, geometry };
  }

  children(id: number, level?: string): Promise<AdminAreaSummary[]> {
    return this.db.many<AdminAreaSummary>(Q.CHILDREN_SQL, [id, level ?? null]);
  }

  list(level: string, parentId: number | undefined, limit: number, offset: number): Promise<AdminAreaSummary[]> {
    return this.db.many<AdminAreaSummary>(Q.LIST_SQL, [level, parentId ?? null, limit, offset]);
  }

  async nationalStats(): Promise<NationalStats> {
    const row = await this.db.one<Omit<NationalStats, 'inclusion_rule'>>(Q.NATIONAL_STATS_SQL);
    return { ...(row as Omit<NationalStats, 'inclusion_rule'>), inclusion_rule: INCLUSION_RULE };
  }

  private async pathOf(id: number): Promise<string> {
    const row = await this.db.one<{ path: string }>(Q.AREA_BY_ID_PATH_SQL, [id]);
    if (!row) throw new NotFoundException(`area not found: ${id}`);
    return row.path;
  }

  private async counts(id: number): Promise<{ descendant_counts: LevelCounts; pending_counts: LevelCounts }> {
    const rows = await this.db.many<{ level: AdminLevel; n: number; pending: number }>(Q.DESCENDANT_COUNTS_SQL, [id]);
    const descendant_counts: LevelCounts = {};
    const pending_counts: LevelCounts = {};
    for (const r of rows) {
      if (r.n) descendant_counts[r.level] = r.n;
      if (r.pending) pending_counts[r.level] = r.pending;
    }
    return { descendant_counts, pending_counts };
  }

  private async placeCounts(area: AdminAreaSummary): Promise<Record<string, number>> {
    const rows = area.level === 'country'
      ? await this.db.many<{ key: string; n: number }>(Q.NATIONAL_PLACE_COUNTS_SQL)
      : await this.db.many<{ key: string; n: number }>(Q.PLACE_COUNTS_SQL, [area.id]);
    return Object.fromEntries(rows.map((r) => [r.key, r.n]));
  }
}
