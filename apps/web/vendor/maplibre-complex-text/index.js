// Complex-text plugin for MapLibre GL JS: Bangla (and the Devanagari and Myanmar names seen near Bangladesh) shaped
// with HarfBuzz, then drawn from a positioned-glyph font. MapLibre itself draws one glyph per character, which
// splits conjuncts (ক্ষ, ন্ত) and puts the vowel sign of ি / ে / ৈ after the consonant instead of before it.
//
// Trimmed from wipfli/maplibre-gl-complex-text @ 45c5aa1 (MIT) to three scripts. Loaded through
// maplibregl.setRTLTextPlugin (it uses that hook; see components/map/basemap.ts), together with the glyph ranges in
// public/maplibre/glyphs. Build: node scripts/build-complex-text.mjs → public/maplibre/complex-text.js
import wasm from './hb.wasm';
import hbjs from './hbjs.js';
import fontBengali from './NotoSansBengali-Regular-without-glyf.ttf.base64.txt';
import csvBengali from './NotoSansBengali-Regular-v1.multiscript.csv';
import fontDevanagari from './NotoSansDevanagari-Regular-without-glyf.ttf.base64.txt';
import csvDevanagari from './NotoSansDevanagari-Regular-v1.multiscript.csv';
import fontMyanmar from './NotoSansMyanmar-Regular-without-glyf.ttf.base64.txt';
import csvMyanmar from './NotoSansMyanmar-Regular-v1.multiscript.csv';

const SCRIPTS = {
  Bengali: [fontBengali, csvBengali],
  Devanagari: [fontDevanagari, csvDevanagari],
  Myanmar: [fontMyanmar, csvMyanmar],
};
const fonts = {};
const encodings = {};
let hb = null;

function addFont(script, base64) {
  const bin = atob(base64.trim());
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  const font = hb.createFont(hb.createFace(hb.createBlob(bytes), 0));
  font.setScale(1000, 1000);
  fonts[script] = font;
}

function addEncoding(script, csv) {
  const map = (encodings[script] = new Map());
  for (const line of csv.split('\n').slice(1)) {
    const [index, dx, dy, ax, ay, codepoint] = line.trim().split(',');
    if (codepoint) map.set(`${index}/${dx}/${dy}/${ax}/${ay}`, +codepoint);
  }
}

/** The positioned-glyph codepoint for one shaped glyph (advances may be off by one after rounding). */
function codepointOf(g, script) {
  const enc = encodings[script];
  const dx = Math.round(g.dx / 64), dy = Math.round(g.dy / 64), ax = Math.round(g.ax / 64), ay = Math.round(g.ay / 64);
  for (const a of [ax, ax + 1, ax - 1]) {
    const cp = enc.get(`${g.g}/${dx}/${dy}/${a}/${ay}`);
    if (cp !== undefined) return cp;
  }
  return -1;
}

function encode(text, script) {
  const buffer = hb.createBuffer();
  buffer.addText(text);
  buffer.guessSegmentProperties();
  hb.shape(fonts[script], buffer);
  const glyphs = buffer.json(fonts[script]);
  buffer.destroy();
  let out = '';
  for (const g of glyphs) {
    const cp = codepointOf(g, script);
    if (cp !== -1) out += String.fromCharCode(cp);
  }
  return out;
}

const names = Object.keys(SCRIPTS);
const runs = new RegExp(
  `(${names.map((s) => `\\p{Script=${s}}+(?:[\\u200C\\u200D]\\p{Script=${s}}+)*`).join('|')}|[^${names.map((s) => `\\p{Script=${s}}`).join('')}]+)`,
  'gu',
);
const only = Object.fromEntries(names.map((s) => [s, new RegExp(`^[\\p{Script=${s}}\\u200C\\u200D]+$`, 'u')]));

// Called by MapLibre for every label (despite the name).
function applyArabicShaping(input) {
  const parts = input && input.match(runs);
  if (!parts) return input;
  let out = '';
  for (const part of parts) {
    const script = names.find((s) => only[s].test(part));
    out += script ? encode(part, script) : part;
  }
  return out;
}

function processBidirectionalText(input, breaks) {
  if (!input || !breaks || breaks.length === 0) return [input];
  const lines = [];
  let start = 0;
  for (const b of breaks) { lines.push(input.substring(start, b)); start = b; }
  if (start < input.length) lines.push(input.substring(start));
  return lines;
}

function processStyledBidirectionalText(text, styleIndices, breaks) {
  if (!text) return [];
  const points = [...breaks].sort((a, b) => a - b);
  if (!points.includes(text.length)) points.push(text.length);
  const out = [];
  let start = 0;
  for (const b of points) {
    if (b <= start) continue;
    const line = text.substring(start, b);
    const styles = styleIndices.slice(start, b);
    let seg = 0;
    for (let i = 1; i <= line.length; i++) {
      if (i === line.length || styles[i] !== styles[seg]) {
        const part = line.substring(seg, i);
        if (part !== '\n') out.push([part, Array(part.length).fill(styles[seg])]);
        seg = i;
      }
    }
    start = b;
  }
  return out;
}

WebAssembly.instantiate(wasm, {}).then(({ instance }) => {
  hb = hbjs(instance);
  for (const [script, [font, csv]] of Object.entries(SCRIPTS)) {
    addFont(script, font);
    addEncoding(script, csv);
  }
  self.registerRTLTextPlugin({ applyArabicShaping, processBidirectionalText, processStyledBidirectionalText });
});
