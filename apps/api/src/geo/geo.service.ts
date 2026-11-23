import { Injectable, NotFoundException } from '@nestjs/common';
import { PLACE_LEVELS } from '@elaka360/shared';
import type { AdminArea, AdminAreaSummary, AdminLevel, AreaDetail, AreaRoad, CoverageReport, CoverageRow, CoverageService, AreaStats, AreaTreeNode, LevelCounts, LocateResult, NationalStats } from '@elaka360/shared';
import { Db, INCLUDE_UNVERIFIED } from '../db/db.service';
import * as Q from './geo.sql';

export const INCLUSION_RULE = INCLUDE_UNVERIFIED
  ? 'All active records, including ones not yet verified (labelled by evidence level); `sourced` counts only records with official or secondary evidence.'
  : 'Only records that are production-eligible (official or secondary evidence with a named source).';

/** Levels that roads are filed under (pipelines/roads.py). */
const ROAD_LEVELS = new Set<AdminLevel>(['union', 'pourashava', 'ward', 'city_corporation']);

export const COVERAGE_SERVICES: CoverageService[] = ['union_parishad', 'pharmacy', 'hospital', 'community_clinic', 'police', 'fire',
  'post_office', 'market', 'bank', 'transport', 'school'];
/** Child grouping and child levels per coverage level. */
const COVERAGE_CHILD: Partial<Record<AdminLevel, { group: string; levels: AdminLevel[] }>> = {
  country: { group: 'division', levels: ['division'] },
  division: { group: 'district', levels: ['district'] },
  district: { group: 'upazila', levels: ['upazila', 'city_corporation'] },
  upazila: { group: 'union', levels: ['union'] },
};
export const COVERAGE_LEVELS = Object.keys(COVERAGE_CHILD) as AdminLevel[];

type CoverageCounts = Omit<CoverageRow, 'area' | 'unions' | 'mouzas' | 'villages' | 'missing'> & { child_id: number | null; total: boolean };
type CoverageArea = CoverageRow['area'] & { unions: number; mouzas: number; villages: number };

@Injectable()
export class GeoService {
  /** Place counts by scope area id, kept for the life of this instance. Only the edge export turns it on: a union's
   *  counts are then queried once for all of its mouzas and villages, not once per page. */
  placeCountMemo: Map<number, Promise<Record<string, number>>> | null = null;

  constructor(private readonly db: Db) {}

  async detailByPath(path: string): Promise<AreaDetail> {
    const area = await this.db.one<AdminArea>(Q.AREA_DETAIL_SQL, [path]);
    if (!area) throw new NotFoundException(`area not found: ${path}`);
    const [breadcrumb, children, counts, links, roads] = await Promise.all([
      this.db.many<AdminAreaSummary>(Q.BREADCRUMB_SQL, [area.id]),
      this.db.many<AdminAreaSummary>(Q.CHILDREN_SQL, [area.id, null]),
      this.counts(area.id),
      this.db.many<AreaDetail['links'][number]>(Q.AREA_LINKS_SQL, [area.id]),
      ROAD_LEVELS.has(area.level) ? this.db.many<AreaRoad>(Q.AREA_ROADS_SQL, [area.id]) : Promise.resolve([]),
    ]);
    const place_scope = placeScope(area, breadcrumb);
    const places = await this.placeCounts(place_scope ?? area);
    return { area, breadcrumb, children, ...counts, place_counts: places, links, place_scope, roads };
  }

  async detailById(id: number): Promise<AreaDetail> {
    return this.detailByPath(await this.pathOf(id));
  }

  async stats(id: number): Promise<AreaStats> {
    const area = await this.db.one<AdminArea>(Q.AREA_DETAIL_SQL, [await this.pathOf(id)]);
    if (!area) throw new NotFoundException(`area not found: ${id}`);
    const scope = PLACE_LEVELS.includes(area.level) ? null : placeScope(area, await this.db.many<AdminAreaSummary>(Q.BREADCRUMB_SQL, [id]));
    const [counts, places] = await Promise.all([this.counts(id), this.placeCounts(scope ?? area)]);
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

  /** Child-area boundaries (any depth) as a FeatureCollection for the live map. */
  async childBoundaries(id: number, levels: string[]) {
    // finer levels keep more detail; 0.0001° is about 11 m
    const tolerance = levels.some((l) => l === 'union' || l === 'ward' || l === 'pourashava') ? 0.0001 : 0.0003;
    const rows = await this.db.many<{ id: number; geometry: unknown } & Record<string, unknown>>(Q.CHILD_BOUNDARIES_SQL, [id, levels, tolerance]);
    return {
      type: 'FeatureCollection' as const,
      features: rows.map(({ geometry, ...properties }) => ({ type: 'Feature' as const, id: properties.id, properties, geometry })),
    };
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

  /** Coverage of public places under an area (country, division, district or upazila), per child area. */
  async coverage(id: number): Promise<CoverageReport> {
    const area = await this.db.one<AdminAreaSummary>(Q.AREA_DETAIL_SQL, [await this.pathOf(id)]);
    const child = area && COVERAGE_CHILD[area.level];
    if (!area || !child) throw new NotFoundException(`no coverage report for area ${id} (country, division, district or upazila only)`);
    const [areas, counts] = await Promise.all([
      this.db.many<CoverageArea>(Q.COVERAGE_AREAS_SQL, [id, child.levels]),
      this.db.many<CoverageCounts>(area.level === 'country' ? Q.COVERAGE_NATIONAL_SQL : Q.COVERAGE_PLACES_SQL, [id, child.group]),
    ]);
    const byChild = new Map(counts.filter((c) => !c.total && c.child_id !== null).map((c) => [c.child_id, c]));
    const total = counts.find((c) => c.total);
    const empty = { places: 0, official: 0, secondary: 0, community: 0, with_point: 0, with_contact: 0, with_name_bn: 0, unions_with_places: 0,
                    services: Object.fromEntries(COVERAGE_SERVICES.map((k) => [k, 0])) as Record<CoverageService, number> };
    const row = (a: CoverageArea, c: CoverageCounts | undefined): CoverageRow => {
      const { unions, mouzas, villages, ...summary } = a;
      const n = c ? { places: c.places, official: c.official, secondary: c.secondary, community: c.community, with_point: c.with_point,
                      with_contact: c.with_contact, with_name_bn: c.with_name_bn, unions_with_places: c.unions_with_places, services: c.services } : empty;
      // a city corporation has no Union Parishad, and a union-level row is not expected to have every service
      const expected = COVERAGE_SERVICES.filter((k) => !(k === 'union_parishad' && a.level === 'city_corporation'));
      return { area: summary, ...n, unions, mouzas, villages,
               missing: a.level === 'union' ? [] : expected.filter((k) => !n.services[k]) };
    };
    const self = areas.find((a) => a.id === id)!;
    return {
      area: row(self, total),
      rows: areas.filter((a) => a.id !== id).map((a) => row(a, byChild.get(a.id))),
      unfiled: counts.find((c) => !c.total && c.child_id === null)?.places ?? 0,
      services: COVERAGE_SERVICES,
      inclusion_rule: INCLUSION_RULE,
    };
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

  private placeCounts(area: AdminAreaSummary): Promise<Record<string, number>> {
    if (!this.placeCountMemo) return this.queryPlaceCounts(area);
    let p = this.placeCountMemo.get(area.id);
    if (!p) this.placeCountMemo.set(area.id, (p = this.queryPlaceCounts(area)));
    return p;
  }

  private async queryPlaceCounts(area: AdminAreaSummary): Promise<Record<string, number>> {
    const rows = area.level === 'country'
      ? await this.db.many<{ key: string; n: number }>(Q.NATIONAL_PLACE_COUNTS_SQL)
      : await this.db.many<{ key: string; n: number }>(Q.PLACE_COUNTS_SQL, [area.id]);
    return Object.fromEntries(rows.map((r) => [r.key, r.n]));
  }
}

/** Nearest area at or above `area` that places are filed under (PLACE_LEVELS); null when that is the area itself. */
export function placeScope(area: AdminAreaSummary, breadcrumb: AdminAreaSummary[]): AdminAreaSummary | null {
  if (PLACE_LEVELS.includes(area.level)) return null;
  return [...breadcrumb].reverse().find((b) => PLACE_LEVELS.includes(b.level)) ?? null;
}
