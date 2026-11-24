import type { Map as MlMap, RequestParameters, ResourceType } from 'maplibre-gl';

/** Default basemap: OpenFreeMap (free, no key). Override with NEXT_PUBLIC_MAP_STYLE_URL (e.g. self-hosted PMTiles style). */
export const STYLE_URL = process.env.NEXT_PUBLIC_MAP_STYLE_URL ?? 'https://tiles.openfreemap.org/styles/positron';

type MapLibre = typeof import('maplibre-gl');

/**
 * MapLibre draws one glyph per character, so Bangla on the map breaks: conjuncts fall apart and ি / ে / ৈ land after
 * their consonant. The complex-text plugin (public/maplibre/complex-text.js, built from vendor/maplibre-complex-text)
 * shapes labels with HarfBuzz into positioned glyphs, served from public/maplibre/glyphs. Call before creating a map.
 */
export function enableBanglaText(maplibregl: MapLibre) {
  if (maplibregl.getRTLTextPluginStatus() !== 'unavailable') return;   // once per page
  maplibregl.setRTLTextPlugin(new URL('/maplibre/complex-text.js', window.location.origin).href, false).catch(() => {});
}

// Glyph ranges of the positioned-glyph font that the plugin writes into (Bengali, Devanagari, Myanmar).
const SHAPED_RANGES = new Set([58880, 59136, 59392, 59648, 62208, 62464, 62720, 62976, 63232, 63488]);

/** transformRequest for maps: shaped-glyph ranges come from this site; everything else is unchanged. */
export function transformRequest(url: string, type?: ResourceType): RequestParameters | undefined {
  if (type !== 'Glyphs') return undefined;
  const m = url.match(/(\d+)-(\d+)\.pbf$/);
  if (!m || !SHAPED_RANGES.has(Number(m[1]))) return undefined;
  return { url: new URL(`/maplibre/glyphs/${m[1]}-${m[2]}.pbf`, window.location.origin).href };
}

/**
 * Basemap labels in the page's language: Bangla pages show the Bangla name (name:bn, else the local name, which in
 * Bangladesh is Bangla), English pages the English or Latin name. The stock style prints both, one under the other.
 */
export function localizeBasemap(map: MlMap, locale: string) {
  const field = locale === 'bn'
    ? ['coalesce', ['get', 'name:bn'], ['get', 'name:nonlatin'], ['get', 'name']]
    : ['coalesce', ['get', 'name:en'], ['get', 'name:latin'], ['get', 'name']];
  for (const layer of map.getStyle().layers ?? []) {
    if (layer.type !== 'symbol') continue;
    const tf = map.getLayoutProperty(layer.id, 'text-field');
    if (!tf || !JSON.stringify(tf).includes('name')) continue;
    map.setLayoutProperty(layer.id, 'text-field', field);
    // letter-spaced region names suit Latin capitals; in Bangla the spacing tears words apart
    if (locale === 'bn' && map.getLayoutProperty(layer.id, 'text-letter-spacing')) map.setLayoutProperty(layer.id, 'text-letter-spacing', 0);
  }
}

const BN_DIGITS = '০১২৩৪৫৬৭৮৯';

/** A map label expression with its digits in Bangla on Bangla pages ("485" → "৪৮৫"), e.g. cluster counts. */
export function localDigits(expr: unknown[], locale: string): unknown[] {
  if (locale !== 'bn') return expr;
  const s = ['to-string', expr];
  const char = (i: number) => {
    const c = ['slice', s, i, i + 1];
    return ['case', ['>', ['length', s], i], ['match', c, ...[...BN_DIGITS].flatMap((d, n) => [String(n), d]), c], ''];
  };
  return ['concat', ...Array.from({ length: 8 }, (_, i) => char(i))];
}
