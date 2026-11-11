"""Shared helpers for importing collected sources (data/sources/<key>/, see data/sources/COLLECTION_FORMAT.md).

Pure standard library so the seed build stays reproducible in CI without GIS packages.
"""
import csv, difflib, hashlib, json, os, re
from trust import nfc
from reconcile import latin_key

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(ROOT, "data", "sources")


# ---------------------------------------------------------------- loading

def manifests():
    """Every collected source folder with a SOURCE.json, sorted by key."""
    out = []
    for d in sorted(os.listdir(SOURCES)):
        p = os.path.join(SOURCES, d, "SOURCE.json")
        if os.path.isfile(p):
            m = json.load(open(p, encoding="utf-8"))
            m["_dir"] = os.path.join(SOURCES, d)
            out.append(m)
    return out


def read_csv(path):
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [{k: nfc((v or "").strip()) for k, v in r.items() if k} for r in csv.DictReader(f)]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_manifest(m):
    """Problems with a source manifest (missing provenance, stale checksums)."""
    errs = []
    for k in ("key", "name", "source_type", "trust_level", "accessed"):
        if m.get(k) in (None, ""):
            errs.append(f"{m.get('key', m['_dir'])}: SOURCE.json missing {k}")
    if not (m.get("urls") or []):
        errs.append(f"{m.get('key')}: SOURCE.json has no urls")
    for rel, digest in (m.get("files") or {}).items():
        p = os.path.join(m["_dir"], rel)
        if not os.path.isfile(p):
            errs.append(f"{m['key']}: listed file missing: {rel}")
        elif digest and sha256(p) != digest:
            errs.append(f"{m['key']}: checksum changed for {rel} (re-run fetch.py and update SOURCE.json)")
    return errs


# ---------------------------------------------------------------- names

_BN_STRIP = re.compile(r"[\s\-\(\)\.,।'\"/]")
_GENERIC = re.compile(r"\b(union|parishad|pourashava|paurashava|municipality|upazila|thana|sadar)\b", re.I)


def bn_key(s):
    return _BN_STRIP.sub("", nfc(s or ""))


def en_key(s):
    return latin_key(_GENERIC.sub(" ", s or ""))


def skeleton(s):
    """Spelling-insensitive key for romanised Bangla names: Gorgori/Gargari, Jewpara/Jiupara, Talondo/Talanda."""
    k = _GENERIC.sub(" ", (s or "").lower())
    k = re.sub(r"[^a-z]", "", k)
    for a, b in (("v", "bh"), ("x", "ks"), ("z", "j"), ("q", "k"), ("w", "o"), ("y", "i"), ("ph", "f"), ("f", "p")):
        k = k.replace(a, b)
    k = re.sub(r"([kgcjtdpb])h", r"\1", k)        # drop aspiration
    k = k.replace("sh", "s").replace("ch", "c")
    if not k:
        return ""
    k = k[0] + re.sub(r"[aeiou]", "", k[1:])          # consonant skeleton after the first letter
    return re.sub(r"(.)\1+", r"\1", k)


def en_similarity(a, b):
    """0..1 for two romanised names, max of normalised-key and skeleton similarity; prefix of a longer name counts."""
    if not a or not b:
        return 0.0
    x, y = en_key(a), en_key(b)
    if x and y and (x == y or (min(len(x), len(y)) >= 5 and (x.startswith(y) or y.startswith(x)))):
        return 1.0 if x == y else 0.9
    r1 = difflib.SequenceMatcher(None, x, y).ratio()
    sx, sy = skeleton(a), skeleton(b)
    r2 = 1.0 if sx and sx == sy else difflib.SequenceMatcher(None, sx, sy).ratio() if sx and sy else 0.0
    return max(r1, r2 * 0.95)


def name_similarity(a_bn, a_en, b_bn, b_en):
    """0..1 similarity of two names, using whichever scripts both sides have."""
    best = 0.0
    if a_bn and b_bn:
        x, y = bn_key(a_bn), bn_key(b_bn)
        if x and y:
            best = max(best, 1.0 if x == y else difflib.SequenceMatcher(None, x, y).ratio())
    if a_en and b_en:
        best = max(best, en_similarity(a_en, b_en))
    return best


# ---------------------------------------------------------------- geometry

def haversine_m(lat1, lon1, lat2, lon2):
    from math import asin, cos, radians, sin, sqrt
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * 6371000 * asin(sqrt(a))


def _in_ring(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def _polys(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return geom["coordinates"]
    return []


def _bbox(geom):
    xs, ys = [], []
    for poly in _polys(geom):
        for x, y, *_ in poly[0]:
            xs.append(x); ys.append(y)
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


class PolygonIndex:
    """Point-in-polygon lookup over GeoJSON features (bbox prefilter, even-odd rule, holes respected)."""

    def __init__(self, features):
        self.items = []
        for f in features:
            g = f.get("geometry")
            if not g:
                continue
            b = _bbox(g)
            if b:
                self.items.append((b, _polys(g), f))

    def find(self, lon, lat):
        hits = []
        for (x0, y0, x1, y1), polys, f in self.items:
            if not (x0 <= lon <= x1 and y0 <= lat <= y1):
                continue
            for poly in polys:
                if _in_ring(lon, lat, poly[0]) and not any(_in_ring(lon, lat, h) for h in poly[1:]):
                    hits.append(f)
                    break
        return hits


# ---------------------------------------------------------------- evidence

def evidence_for(trust_level, has_source_url):
    """Evidence tier of a collected record from its source's trust level (DATA_TRUST_POLICY.md)."""
    t = int(trust_level or 1)
    if t >= 4:
        return "official" if has_source_url else "secondary"
    if t == 3:
        return "secondary"
    return "community"


# ---------------------------------------------------------------- romanisation (for URL slugs only)

_BN_VOWELS = {"অ": "a", "আ": "a", "ই": "i", "ঈ": "i", "উ": "u", "ঊ": "u", "ঋ": "ri", "এ": "e", "ঐ": "oi", "ও": "o", "ঔ": "ou"}
_BN_SIGNS = {"া": "a", "ি": "i", "ী": "i", "ু": "u", "ূ": "u", "ৃ": "ri", "ে": "e", "ৈ": "oi", "ো": "o", "ৌ": "ou"}
_BN_CONS = {"ক": "k", "খ": "kh", "গ": "g", "ঘ": "gh", "ঙ": "ng", "চ": "ch", "ছ": "chh", "জ": "j", "ঝ": "jh", "ঞ": "n",
            "ট": "t", "ঠ": "th", "ড": "d", "ঢ": "dh", "ণ": "n", "ত": "t", "থ": "th", "দ": "d", "ধ": "dh", "ন": "n",
            "প": "p", "ফ": "f", "ব": "b", "ভ": "bh", "ম": "m", "য": "j", "র": "r", "ল": "l", "শ": "sh", "ষ": "sh",
            "স": "s", "হ": "h", "ড়": "r", "ঢ়": "rh", "য়": "y", "ৎ": "t"}
_NUKTA = {"ড": "ড়", "ঢ": "ঢ়", "য": "য়"}


def romanize_bn(s):
    """Rough Bangla -> Latin romanisation, good enough for readable URL slugs (not for display)."""
    chars = []
    for ch in nfc(s or ""):
        if ch == "়" and chars and chars[-1] in _NUKTA:      # NFC keeps ড় as ড + nukta
            chars[-1] = _NUKTA[chars[-1]]
        else:
            chars.append(ch)
    out = []
    for i, ch in enumerate(chars):
        nxt = chars[i + 1] if i + 1 < len(chars) else ""
        if ch in _BN_CONS:
            if ch == "য" and i and chars[i - 1] == "্":
                out.append("y")
            else:
                out.append(_BN_CONS[ch])
            # inherent vowel: kept after a word's first consonant and before ং; dropped when the next consonant carries
            # its own vowel sign (রাজশাহী -> rajshahi, পাহাড়পুর -> paharpur); never at the end of a word
            first = i == 0 or chars[i - 1] in " ,.-()/" or chars[i - 1] in _BN_VOWELS
            after = chars[i + 2] if i + 2 < len(chars) else ""
            if ch != "ৎ" and nxt not in _BN_SIGNS and nxt != "্" and (
                    (nxt and nxt in "ংঃ") or (nxt in _BN_CONS and (first or (after not in _BN_SIGNS and after != "্")))):
                out.append("o" if first else "a")
        elif ch in _BN_VOWELS:
            out.append(_BN_VOWELS[ch])
        elif ch in _BN_SIGNS:
            out.append(_BN_SIGNS[ch])
        elif ch == "ং":
            out.append("ng")
        elif ch == "ঃ":
            out.append("h")
        elif ch in "্ঁ":
            continue
        elif "০" <= ch <= "৯":
            out.append(str(ord(ch) - ord("০")))
        else:
            out.append(ch)
    return "".join(out)
