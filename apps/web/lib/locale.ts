/** Locale helpers for data shown in the UI (server and client safe). */
import { EVIDENCE_LABEL, toBnDigits, type EvidenceLevel, type Locale } from '@elaka360/shared';

export type { Locale };

export function asLocale(value: string | undefined | null): Locale {
  return value === 'en' ? 'en' : 'bn';
}

export function otherLocale(locale: Locale): Locale {
  return locale === 'bn' ? 'en' : 'bn';
}

/** Digits in the locale's script (Bangla digits in Bangla, ASCII in English). No grouping. */
export function digits(value: string | number, locale: Locale): string {
  return locale === 'bn' ? toBnDigits(value) : String(value);
}

/** Name in the active locale for records whose English name may be missing (places). */
export function localName(x: { name_bn: string; name_en: string | null | undefined }, locale: Locale): string {
  return locale === 'en' ? x.name_en || x.name_bn : x.name_bn || x.name_en || '';
}

/** The name in the other language, when it exists and differs (shown underneath on detail pages). */
export function otherName(x: { name_bn: string; name_en: string | null | undefined }, locale: Locale): string | null {
  const other = locale === 'en' ? x.name_bn : x.name_en;
  return other && other !== localName(x, locale) ? other : null;
}

/** "Rajshahi, Rajshahi" area label of a place in the active locale. */
export function areaLabel(x: { area_label_bn: string | null; area_label_en: string | null }, locale: Locale): string | null {
  return locale === 'en' ? x.area_label_en ?? x.area_label_bn : x.area_label_bn ?? x.area_label_en;
}

/** Public evidence wording (EVIDENCE_LABEL from @elaka360/shared); unknown levels read as not verified. */
export function evidenceText(level: EvidenceLevel | undefined, locale: Locale): { label: string; hint: string } {
  const l = EVIDENCE_LABEL[level && level in EVIDENCE_LABEL ? level : 'unverified'];
  return locale === 'en' ? { label: l.en, hint: l.hint_en } : { label: l.bn, hint: l.hint_bn };
}
