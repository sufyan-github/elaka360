import type { AdminLevel, Named } from './types';
import type { Locale } from './bangla';

export const LEVEL_LABEL: Record<AdminLevel, { bn: string; en: string; plural_bn: string; plural_en: string }> = {
  country: { bn: 'দেশ', en: 'Country', plural_bn: 'দেশ', plural_en: 'Countries' },
  division: { bn: 'বিভাগ', en: 'Division', plural_bn: 'বিভাগসমূহ', plural_en: 'Divisions' },
  district: { bn: 'জেলা', en: 'District', plural_bn: 'জেলাসমূহ', plural_en: 'Districts' },
  upazila: { bn: 'উপজেলা', en: 'Upazila', plural_bn: 'উপজেলাসমূহ', plural_en: 'Upazilas' },
  city_corporation: { bn: 'সিটি কর্পোরেশন', en: 'City corporation', plural_bn: 'সিটি কর্পোরেশন', plural_en: 'City corporations' },
  pourashava: { bn: 'পৌরসভা', en: 'Pourashava', plural_bn: 'পৌরসভাসমূহ', plural_en: 'Pourashavas' },
  union: { bn: 'ইউনিয়ন', en: 'Union', plural_bn: 'ইউনিয়নসমূহ', plural_en: 'Unions' },
  ward: { bn: 'ওয়ার্ড', en: 'Ward', plural_bn: 'ওয়ার্ডসমূহ', plural_en: 'Wards' },
  mouza: { bn: 'মৌজা', en: 'Mouza', plural_bn: 'মৌজাসমূহ', plural_en: 'Mouzas' },
  village: { bn: 'গ্রাম', en: 'Village', plural_bn: 'গ্রামসমূহ', plural_en: 'Villages' },
  thana: { bn: 'থানা', en: 'Thana', plural_bn: 'থানাসমূহ', plural_en: 'Thanas' },
};

/** The child level(s) shown on an area page, in display order. */
export const CHILD_LEVELS: Partial<Record<AdminLevel, AdminLevel[]>> = {
  country: ['division'],
  division: ['district'],
  district: ['upazila', 'city_corporation'],
  upazila: ['union', 'pourashava'],
  city_corporation: ['ward'],
  pourashava: ['ward'],
  union: ['ward', 'village'],
};

/** Name in the active locale, falling back to the other one. */
export function nameOf(x: Named, locale: Locale): string {
  return (locale === 'bn' ? x.name_bn || x.name_en : x.name_en || x.name_bn) ?? '';
}

/** "রাজশাহী জেলা" — the name followed by its level, unless the name already ends with it. */
export function titleOf(x: Named & { level: AdminLevel }, locale: Locale): string {
  const name = nameOf(x, locale);
  const lvl = LEVEL_LABEL[x.level][locale === 'bn' ? 'bn' : 'en'];
  if (x.level === 'country' || name.endsWith(lvl) || /(City Corporation|Pourashava|পৌরসভা|সিটি কর্পোরেশন)$/.test(name)) return name;
  return `${name} ${lvl}`;
}
