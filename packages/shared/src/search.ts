/**
 * Normalise Latin-script place names so "Rajshahi", "rajsahi" and "Raj-shahi"
 * all map to the same search key. Used to build Banglish aliases at index time.
 */
export function latinKey(input: string): string {
  return input
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '')
    .replace(/sh/g, 's')
    .replace(/(oo|ou)/g, 'u')
    .replace(/(ee|ii)/g, 'i')
    .replace(/aa/g, 'a')
    .replace(/w/g, 'o')
    .replace(/([a-z])\1+/g, '$1');
}

/** Distinct alias keys for one name (the name itself, without spaces, and its latinKey). */
export function aliasesFor(nameEn: string): string[] {
  const lower = nameEn.toLowerCase().trim();
  return [...new Set([lower, lower.replace(/\s+/g, ''), latinKey(nameEn)])].filter(Boolean);
}
