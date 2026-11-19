/**
 * Bangla display helpers. Data is always stored with ASCII digits;
 * these functions convert at render time only.
 */

const BN_DIGITS = ['০', '১', '২', '৩', '৪', '৫', '৬', '৭', '৮', '৯'] as const;

export const BN_MONTHS = [
  'জানুয়ারি', 'ফেব্রুয়ারি', 'মার্চ', 'এপ্রিল', 'মে', 'জুন',
  'জুলাই', 'আগস্ট', 'সেপ্টেম্বর', 'অক্টোবর', 'নভেম্বর', 'ডিসেম্বর',
] as const;

export const EN_MONTHS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
] as const;

export type Locale = 'bn' | 'en';

/** Replace ASCII digits 0–9 with Bengali digits. Other characters are kept. */
export function toBnDigits(value: string | number): string {
  return String(value).replace(/[0-9]/g, (d) => BN_DIGITS[Number(d)] ?? d);
}

/** Replace Bengali digits with ASCII digits (for parsing user input). */
export function fromBnDigits(value: string): string {
  return value.replace(/[০-৯]/g, (d) => String(BN_DIGITS.indexOf(d as (typeof BN_DIGITS)[number])));
}

/** Group an integer string the South Asian way: 12,34,567. */
export function groupIndian(intDigits: string): string {
  if (intDigits.length <= 3) return intDigits;
  const last3 = intDigits.slice(-3);
  const rest = intDigits.slice(0, -3);
  const pairs = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',');
  return `${pairs},${last3}`;
}

/** 2915009 → "২৯,১৫,০০৯" (bn) or "2,915,009" (en). */
export function formatNumber(n: number, locale: Locale = 'bn', fractionDigits?: number): string {
  if (!Number.isFinite(n)) return '';
  const negative = n < 0;
  const fixed = fractionDigits === undefined ? String(Math.abs(n)) : Math.abs(n).toFixed(fractionDigits);
  const [intPart = '0', frac] = fixed.split('.');
  const grouped = locale === 'bn' ? groupIndian(intPart) : intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  const out = `${negative ? '-' : ''}${grouped}${frac ? `.${frac}` : ''}`;
  return locale === 'bn' ? toBnDigits(out) : out;
}

/**
 * Compact population-style numbers.
 * bn: 2915009 → "২৯.১৫ লাখ", 45644586 → "৪.৫৬ কোটি"
 * en: 2915009 → "2.92M"
 */
export function formatCompact(n: number, locale: Locale = 'bn', fractionDigits = 2): string {
  // Pick the unit after rounding, so 99,99,999 reads "১.০০ কোটি", not "১০০.০০ লাখ".
  const scaled = (unit: number, digits: number) => Number((Math.abs(n) / unit).toFixed(digits));
  const sign = n < 0 ? '-' : '';
  if (locale === 'bn') {
    if (scaled(1e7, fractionDigits) >= 1) return `${toBnDigits(sign + (Math.abs(n) / 1e7).toFixed(fractionDigits))} কোটি`;
    if (scaled(1e5, fractionDigits) >= 1) return `${toBnDigits(sign + (Math.abs(n) / 1e5).toFixed(fractionDigits))} লাখ`;
    return formatNumber(n, 'bn');
  }
  if (scaled(1e9, fractionDigits) >= 1) return `${sign}${(Math.abs(n) / 1e9).toFixed(fractionDigits)}B`;
  if (scaled(1e6, fractionDigits) >= 1) return `${sign}${(Math.abs(n) / 1e6).toFixed(fractionDigits)}M`;
  if (scaled(1e3, 1) >= 1) return `${sign}${(Math.abs(n) / 1e3).toFixed(1)}K`;
  return String(n);
}

/** Count with the Bangla classifier: 9 → "৯টি". */
export function formatCount(n: number, locale: Locale = 'bn'): string {
  return locale === 'bn' ? `${formatNumber(n, 'bn')}টি` : formatNumber(n, 'en');
}

/** Area in km²: 2425.37 → "২,৪২৫.৩৭ বর্গ কিমি". */
export function formatArea(km2: number, locale: Locale = 'bn'): string {
  const digits = Number.isInteger(km2) ? 0 : 2;
  return locale === 'bn' ? `${formatNumber(km2, 'bn', digits)} বর্গ কিমি` : `${formatNumber(km2, 'en', digits)} km²`;
}

/** Distance in metres: 300 → "৩০০ মিটার", 2100 → "২.১ কিমি". */
export function formatDistance(meters: number, locale: Locale = 'bn'): string {
  if (meters < 1000) {
    const m = Math.round(meters);
    return locale === 'bn' ? `${toBnDigits(m)} মিটার` : `${m} m`;
  }
  const km = (meters / 1000).toFixed(1);
  return locale === 'bn' ? `${toBnDigits(km)} কিমি` : `${km} km`;
}

/**
 * Format an ISO date (YYYY-MM-DD or full ISO) without timezone drift:
 * "2026-11-09" → "৯ নভেম্বর ২০২৬" / "9 Nov 2026".
 */
export function formatDate(iso: string, locale: Locale = 'bn'): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return iso;
  const [, y, mo, d] = m;
  const monthIndex = Number(mo) - 1;
  if (locale === 'bn') return `${toBnDigits(Number(d))} ${BN_MONTHS[monthIndex] ?? ''} ${toBnDigits(y ?? '')}`;
  return `${Number(d)} ${EN_MONTHS[monthIndex] ?? ''} ${y}`;
}
