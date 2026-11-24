# MapLibre complex text (Bangla on the map)

MapLibre GL JS draws one glyph per character, so Bangla map labels break: conjuncts (ক্ষ, ঞ্জ) fall apart and the
vowel signs ি ে ৈ ো appear after their consonant. This plugin shapes each label with HarfBuzz and writes it as
"positioned glyphs" from a font prepared for MapLibre, so the label renders as a reader expects.

- `index.js`: our trimmed entry (Bengali, Devanagari and Myanmar only, the scripts in names around Bangladesh).
- `hbjs.js`, `hb.wasm`: HarfBuzz compiled to WebAssembly, from harfbuzzjs.
- `NotoSans*-without-glyf.ttf.base64.txt`: Noto Sans shaping tables (no outlines), for HarfBuzz.
- `NotoSans*-v1.multiscript.csv`: the map from shaped glyph (id + offsets) to positioned-glyph codepoint.
- `../../public/maplibre/glyphs/*.pbf`: the positioned glyphs (MapLibre glyph ranges, NotoSansMultiscript-Regular-v1).

Built into `public/maplibre/complex-text.js` with `node scripts/build-complex-text.mjs` (committed). Loaded by
`components/map/basemap.ts` through `maplibregl.setRTLTextPlugin` (MapLibre calls the plugin for every label). The site's
CSP allows `'wasm-unsafe-eval'` for it.

## Provenance and licences

- github.com/wipfli/maplibre-gl-complex-text @ 45c5aa1 (2 May 2025): plugin code and encodings, MIT (LICENSE).
- github.com/harfbuzz/harfbuzzjs: `hbjs.js` and `hb.wasm`, see the harfbuzzjs licence (MIT-style "Old MIT" / Apache as
  stated by the upstream plugin).
- wipfli.github.io/pgf-glyph-ranges, font NotoSansMultiscript-Regular-v1: glyph ranges 58880–59903 and 62208–63743,
  derived from Google Noto fonts, SIL Open Font License 1.1.
- The upstream plugin uses the API of mapbox-gl-rtl-text (BSD-2-Clause).

To update: replace the files from upstream, keep `index.js` in step with upstream's `src/maplibre-gl-complex-text.js`,
rebuild, and check a Bangla page's map (চাঁপাইনবাবগঞ্জ, নাটোর, জঙ্গিপুর should render correctly).
