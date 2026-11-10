import type { AdminAreaSummary, PlaceSummary } from '@elaka360/shared';
import { aliasesFor } from '@elaka360/shared';

/** Higher = shown first among equally good text matches. */
export const LEVEL_RANK: Record<string, number> = {
  division: 6, district: 5, city_corporation: 4, upazila: 3, pourashava: 2, union: 1,
};

/** Better evidence ranks higher among equally good text matches. */
export const EVIDENCE_RANK: Record<string, number> = { official: 3, secondary: 2, community: 1, unverified: 0 };

export const AREAS_SCHEMA = {
  fields: [
    { name: 'name_bn', type: 'string' },
    { name: 'name_en', type: 'string' },
    { name: 'aliases', type: 'string[]' },
    { name: 'level', type: 'string', facet: true },
    { name: 'level_rank', type: 'int32' },
    { name: 'parent_id', type: 'int32', optional: true, facet: true },
    { name: 'population', type: 'int64', optional: true },
    { name: 'evidence_level', type: 'string', facet: true },
  ],
  default_sorting_field: 'level_rank',
};

export const PLACES_SCHEMA = {
  fields: [
    { name: 'name_bn', type: 'string' },
    { name: 'name_en', type: 'string', optional: true },
    { name: 'aliases', type: 'string[]' },
    { name: 'category_key', type: 'string', facet: true },
    { name: 'subcategory_key', type: 'string', facet: true, optional: true },
    { name: 'district_id', type: 'int32', facet: true, optional: true },
    { name: 'location', type: 'geopoint', optional: true },
    { name: 'rank', type: 'int32' },
    { name: 'evidence_level', type: 'string', facet: true },
  ],
  default_sorting_field: 'rank',
};

export interface AreaRow extends AdminAreaSummary {
  population_2022: number | null;
  parent_bn: string | null;
  parent_en: string | null;
}

export interface PlaceRow extends PlaceSummary {
  district_id: number | null;
}

export function areaDoc(a: AreaRow) {
  return {
    id: `a${a.id}`,
    area_id: a.id,
    level: a.level,
    level_rank: LEVEL_RANK[a.level] ?? 0,
    parent_id: a.parent_id ?? undefined,
    name_bn: a.name_bn,
    name_en: a.name_en,
    aliases: aliasesFor(a.name_en),
    slug: a.slug,
    path: a.path,
    verified: a.verified,
    evidence_level: a.evidence_level,
    production_eligible: a.production_eligible,
    population: a.population_2022 ?? undefined,
    parent_bn: a.parent_bn,
    parent_en: a.parent_en,
  };
}

export function placeDoc(p: PlaceRow) {
  return {
    id: p.public_id,
    public_id: p.public_id,
    slug: p.slug,
    name_bn: p.name_bn,
    name_en: p.name_en ?? '',
    aliases: p.name_en ? aliasesFor(p.name_en) : [],
    category_key: p.category_key,
    subcategory_key: p.subcategory_key ?? undefined,
    district_id: p.district_id ?? undefined,
    location: p.lat !== null && p.lon !== null ? [p.lat, p.lon] : undefined,
    rank: EVIDENCE_RANK[p.evidence_level] ?? 0,
    evidence_level: p.evidence_level,
    production_eligible: p.production_eligible,
    area_label_bn: p.area_label_bn,
    area_label_en: p.area_label_en,
    lat: p.lat,
    lon: p.lon,
    verification_status: p.verification_status,
  };
}

export type AreaDoc = ReturnType<typeof areaDoc>;
export type PlaceDoc = ReturnType<typeof placeDoc>;

export function toAreaSummary(d: AreaDoc): AdminAreaSummary {
  return {
    id: d.area_id, level: d.level, parent_id: d.parent_id ?? null, name_bn: d.name_bn, name_en: d.name_en, slug: d.slug, path: d.path,
    verified: d.verified, evidence_level: d.evidence_level, production_eligible: d.production_eligible,
  };
}

export function toPlaceSummary(d: PlaceDoc): PlaceSummary {
  return {
    public_id: d.public_id, slug: d.slug, name_bn: d.name_bn, name_en: d.name_en || null,
    category_key: d.category_key, subcategory_key: d.subcategory_key ?? null,
    area_label_bn: d.area_label_bn, area_label_en: d.area_label_en, lat: d.lat, lon: d.lon,
    verification_status: d.verification_status, evidence_level: d.evidence_level, production_eligible: d.production_eligible,
  };
}
