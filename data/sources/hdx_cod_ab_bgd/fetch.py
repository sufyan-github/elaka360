#!/usr/bin/env python3
"""HDX COD-AB Bangladesh (OCHA / BBS, version v03) -> one division (default Rajshahi).

Downloads the "Bangladesh - Subnational Administrative Boundaries" dataset from HDX
(https://data.humdata.org/dataset/cod-ab-bgd), keeps one division (Rajshahi = P-code BD50) and writes:

  raw/hdx_cod_ab_bgd_package.json        HDX metadata snapshot (licence, dates, resource URLs)
  raw/bgd_adminpoints_rajshahi.geojson    HDX admin label points for BD50, unmodified (only source of ADM4 codes)
  boundaries.geojson                      division / district / upazila / city-corporation polygons (v03), simplified
  areas.csv                               v03 units (HDX_PCODE) + 2020 points: thanas, unions, paurashavas, wards (HDX_PCODE_2020)
  facts.csv                               area_km2 as published by HDX (area_sqkm)
  crosswalk.csv                           HDX units <-> data/seed/geo/admin_areas.csv ids (districts, upazilas, CC, pourashavas, unions)
  SOURCE.json                             manifest with sha256 of the files above

Dependencies: Python 3 standard library + requests. No GIS packages (simplification and point-in-polygon are
implemented here). Run from anywhere:
  python3 -I data/sources/hdx_cod_ab_bgd/fetch.py [--division rajshahi] [--out DIR] [--cache DIR]
Default (no arguments): Rajshahi Division into this folder, exactly as the first run. Another division writes to
../hdx_cod_ab_bgd_<division>/ (see data/sources/DIVISIONS.md) with raw/bgd_adminpoints_<division>.geojson, key
HDX_COD_AB_BGD_<DIVISION>, and its own SOURCE.json.
The ~38 MB HDX zip is cached in --cache (default: $TMPDIR/elaka360_cache) and is not committed.
"""
from collections import Counter
import argparse, csv, datetime, difflib, hashlib, io, json, math, os, re, sys, tempfile, time, unicodedata, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SEED = os.path.join(ROOT, "data", "seed", "geo", "admin_areas.csv")
UA = "Elaka360-data-pipeline (research; contact via repository)"
KEY = "HDX_COD_AB_BGD"
DATASET = "cod-ab-bgd"
PAGE = "https://data.humdata.org/dataset/cod-ab-bgd"
API = "https://data.humdata.org/api/3/action/package_show?id=" + DATASET
DIV_PCODE = "BD50"
KIND = "hdx_cod_ab"

# division -> (folder/key code, BBS geocode, seed admin_areas id, English name); see data/sources/DIVISIONS.md
DIVISIONS = {
    "rajshahi": ("raj", "50", "10002", "Rajshahi"), "rangpur": ("rang", "55", "10007", "Rangpur"),
    "dhaka": ("dhk", "30", "10006", "Dhaka"), "chattogram": ("ctg", "20", "10001", "Chattogram"),
    "khulna": ("khl", "40", "10003", "Khulna"), "barishal": ("bar", "10", "10004", "Barishal"),
    "sylhet": ("syl", "60", "10005", "Sylhet"), "mymensingh": ("mym", "45", "10008", "Mymensingh"),
}
SIMPLIFY_DEG = 0.0002  # ~20 m; Douglas-Peucker tolerance for the published polygons

_last = {}


def get(url, **kw):
    import requests
    host = url.split("/")[2]
    wait = 1.0 - (time.time() - _last.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    r = requests.get(url, headers={"User-Agent": UA}, timeout=300, **kw)
    _last[host] = time.time()
    r.raise_for_status()
    return r


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ geometry (pure python)

def _dp(pts, tol):
    """Iterative Douglas-Peucker on a list of [x, y]."""
    n = len(pts)
    if n < 3:
        return pts
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    t2 = tol * tol
    while stack:
        a, b = stack.pop()
        ax, ay = pts[a]; bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        dd = dx * dx + dy * dy
        best, idx = -1.0, -1
        for i in range(a + 1, b):
            px, py = pts[i]
            if dd == 0:
                d = (px - ax) ** 2 + (py - ay) ** 2
            else:
                t = ((px - ax) * dx + (py - ay) * dy) / dd
                t = 0 if t < 0 else 1 if t > 1 else t
                d = (px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2
            if d > best:
                best, idx = d, i
        if best > t2:
            keep[idx] = True
            stack.append((a, idx)); stack.append((idx, b))
    return [p for p, k in zip(pts, keep) if k]


def simplify_ring(ring, tol, nd=5):
    pts = [[round(x, nd), round(y, nd)] for x, y, *_ in ring]
    out = []
    for p in pts:
        if not out or out[-1] != p:
            out.append(p)
    if len(out) < 4:
        return None
    s = _dp(out, tol) if tol else out
    if s[0] != s[-1]:
        s.append(s[0])
    return s if len(s) >= 4 else None


def polys(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return geom["coordinates"]
    return []


def simplify_geom(geom, tol, nd=5):
    out = []
    for poly in polys(geom):
        shell = simplify_ring(poly[0], tol, nd)
        if not shell:
            # keep tiny islands visible: fall back to the rounded, unsimplified ring
            shell = simplify_ring(poly[0], 0, nd)
            if not shell:
                continue
        holes = [h for h in (simplify_ring(r, tol, nd) for r in poly[1:]) if h]
        out.append([shell] + holes)
    if not out:
        return None
    return {"type": "Polygon", "coordinates": out[0]} if len(out) == 1 else {"type": "MultiPolygon", "coordinates": out}


def ring_area_m2(ring):
    """Geodesic area of a lon/lat ring on a sphere (same method as turf.js / d3)."""
    R = 6378137.0
    s = 0.0
    n = len(ring)
    for i in range(n - 1):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[i + 1][0], ring[i + 1][1]
        s += math.radians(x2 - x1) * (2 + math.sin(math.radians(y1)) + math.sin(math.radians(y2)))
    return abs(s * R * R / 2.0)


def geom_area_km2(geom):
    a = 0.0
    for poly in polys(geom):
        a += ring_area_m2(poly[0]) - sum(ring_area_m2(h) for h in poly[1:])
    return a / 1e6


def geom_centroid(geom):
    """Area-weighted planar centroid (lon, lat) of all shells minus holes."""
    A = cx = cy = 0.0
    for poly in polys(geom):
        for k, ring in enumerate(poly):
            sgn = 1 if k == 0 else -1
            a = x = y = 0.0
            for i in range(len(ring) - 1):
                x0, y0 = ring[i][0], ring[i][1]; x1, y1 = ring[i + 1][0], ring[i + 1][1]
                c = x0 * y1 - x1 * y0
                a += c; x += (x0 + x1) * c; y += (y0 + y1) * c
            a /= 2
            if a == 0:
                continue
            x /= (6 * a); y /= (6 * a)
            w = sgn * abs(a)
            A += w; cx += w * x; cy += w * y
    return (cx / A, cy / A) if A else (None, None)


def in_ring(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]; xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def point_in_geom(x, y, geom):
    for poly in polys(geom):
        if in_ring(x, y, poly[0]) and not any(in_ring(x, y, h) for h in poly[1:]):
            return True
    return False


def bbox(geom):
    xs, ys = [], []
    for poly in polys(geom):
        for p in poly[0]:
            xs.append(p[0]); ys.append(p[1])
    return min(xs), min(ys), max(xs), max(ys)


# ------------------------------------------------------------------ names / crosswalk

def latin_key(s):
    """Same as pipelines/reconcile.py latin_key (twin of packages/shared search.ts latinKey)."""
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", "", s)
    for a, b in (("sh", "s"), ("oo", "u"), ("ou", "u"), ("ee", "i"), ("ii", "i"), ("aa", "a"), ("w", "o")):
        s = s.replace(a, b)
    return re.sub(r"([a-z])\1+", r"\1", s)


GENERIC = re.compile(r"\b(union|parishad|paurashava|pourashava|paurasava|municipality|upazila|thana|city corp(oration)?|city corp\.)\b", re.I)


def banglish_key(s):
    """Looser key for romanised Bangla: drops aspiration (bh/chh/dh/gh/kh/ph/th -> b/c/d/g/k/f/t), x->ks, v->b, z->j,
    y->i, w->o, ee->i, oo/ou->u, doubled letters collapsed. Vowel quality (o/a/u) is only ignored by skeleton()."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = GENERIC.sub(" ", s)
    s = re.sub(r"[^a-z]", "", s)
    for a, b in (("sh", "s"), ("ph", "f"), ("fh", "f"), ("x", "ks"), ("v", "b"), ("z", "j"), ("q", "k"), ("w", "o"),
                 ("y", "i"), ("ck", "k")):
        s = s.replace(a, b)
    s = re.sub(r"([bcdgjkt])h+", r"\1", s)
    s = s.replace("ee", "i").replace("oo", "u").replace("ou", "u")
    return re.sub(r"(.)\1+", r"\1", s)


def skeleton(s):
    """Consonant skeleton of banglish_key: vowels dropped, h dropped next to a consonant, initial vowel -> 'a'."""
    k = banglish_key(s)
    if not k:
        return ""
    k = re.sub(r"h(?=[^aeiou])|(?<=[^aeiou])h", "", k)
    head = "a" if k[0] in "aeiou" else k[0]
    return re.sub(r"(.)\1+", r"\1", head + re.sub(r"[aeiou]", "", k[1:]))


def parenthetical_variants(s):
    """The name, plus: without a trailing '(...)', the bracket content, and without the word 'Sadar'."""
    s = s or ""
    out = [s]
    m = re.match(r"^(.*?)\s*\((.*?)\)\s*$", s)
    if m:
        out += [m.group(1), m.group(2)]
    out += [re.sub(r"\bsadar\b", " ", x, flags=re.I) for x in list(out) if re.search(r"\bsadar\b", x, re.I)]
    return [x.strip() for x in out if x.strip()]


# Bangla direction words in romanised union names (Uttar Gobindapur = Gobindapur (North)); used only when a division
# turns it on (DIRECTION_WORD_DIVS), so the earlier divisions' crosswalks are unchanged.
DIRECTION_WORDS = {"uttar": "North", "north": "North", "dakshin": "South", "dakkhin": "South", "dakhsin": "South",
                   "dakhin": "South", "dhakhin": "South", "dakkin": "South", "south": "South", "purba": "East",
                   "east": "East", "paschim": "West", "pashchim": "West", "pachim": "West", "west": "West"}
DIRECTION_WORD_DIVS = {"chattogram", "khulna", "barishal", "sylhet"}


def direction_split(name):
    """(name without its direction word, direction in English or None). A name with two different directions, or
    nothing left besides the direction, is returned unchanged with direction None. A one-word name with the direction
    glued on (Purbagujra, Uttarhowla, Chitoshiwest) is split when at least 4 letters remain."""
    words = re.findall(r"[A-Za-z]+", name or "")
    dirs = {DIRECTION_WORDS[w.lower()] for w in words if w.lower() in DIRECTION_WORDS}
    if not dirs and re.fullmatch(r"[A-Za-z]+", (name or "").strip()):
        alts = "|".join(DIRECTION_WORDS)
        m = re.fullmatch(r"(" + alts + r")([a-z]{4,})", name.strip(), re.I) or \
            re.fullmatch(r"([a-z]{4,}?)(north|south|east|west)", name.strip(), re.I)
        if m:
            d, base = (m.group(1), m.group(2)) if m.group(1).lower() in DIRECTION_WORDS else (m.group(2), m.group(1))
            return base, DIRECTION_WORDS[d.lower()]
    if len(dirs) != 1:
        return name, None
    base = re.sub(r"\b(" + "|".join(DIRECTION_WORDS) + r")\b", " ", name, flags=re.I)
    base = re.sub(r"\(\s*\)", " ", base)
    base = re.sub(r"\(\s+", "(", re.sub(r"\s+\)", ")", " ".join(base.split())))
    return (base, dirs.pop()) if re.search(r"[A-Za-z]", base) else (name, None)


def match_names(src, ours, directions=False):
    """src/ours: lists of (key, name_en). One-to-one matching, never forced.
    directions=True: direction words (Uttar/Dakshin/Purba/Paschim = North/South/East/West) are taken out of both names
    before comparing; a pair whose names carry different directions is never considered, and a pair where only one
    name carries a direction is at most 'low' confidence and only considered when neither list has another name with
    the same remainder (Paschim/Purba Rupasdi vs one Rupushdi stays unmatched).
    Returns {src_key: (our_key or None, method, confidence, note)}."""
    sdir, odir = {}, {}
    if directions:
        src_orig, ours_orig = dict(src), dict(ours)
        for k, n in src:
            sdir[k] = direction_split(n)
        for k, n in ours:
            odir[k] = direction_split(n)
        src = [(k, sdir[k][0]) for k, _ in src]
        ours = [(k, odir[k][0]) for k, _ in ours]
        sib_s = Counter(skeleton(n) for _, n in src)
        sib_o = Counter(skeleton(n) for _, n in ours)

    def ok_dir(sk, ok):
        if not directions:
            return True
        if sdir[sk][1] and odir[ok][1]:
            return sdir[sk][1] == odir[ok][1]
        if sdir[sk][1] or odir[ok][1]:  # one-sided: only when the remainder is unique on both sides
            return sib_s[skeleton(sdir[sk][0])] == 1 and sib_o[skeleton(odir[ok][0])] == 1
        return True

    def one_sided(sk, ok):
        return directions and bool(sdir[sk][1]) != bool(odir[ok][1])

    def dir_note(sk, ok, note):
        if directions and (sdir[sk][1] or odir[ok][1]):
            note = "; ".join(x for x in (note, (f"direction word read as {sdir[sk][1] or odir[ok][1]}" +
                                                (" on one side only" if one_sided(sk, ok) else "") +
                                                f": '{src_orig[sk]}' ~ '{ours_orig[ok]}'")) if x)
        return note

    res = {}
    tiers = [
        ("name_exact", "high", lambda a, b: latin_key(GENERIC.sub(" ", a)) == latin_key(GENERIC.sub(" ", b))),
        ("name_banglish", "high", lambda a, b: banglish_key(a) == banglish_key(b)),
        ("name_skeleton", "medium", lambda a, b: len(skeleton(a)) >= 3 and skeleton(a) == skeleton(b)),
    ]
    taken = {}
    pending = list(src)
    for method, conf, eq in tiers:
        nxt = []
        for sk, sn in pending:
            cands, via = [], {}
            for ok, on in ours:
                if ok in taken or not ok_dir(sk, ok):
                    continue
                hit = [(v, w) for v in parenthetical_variants(sn) for w in parenthetical_variants(on) if eq(v, w)]
                if hit:
                    cands.append(ok)
                    v, w = hit[0]
                    if (v, w) != (sn, on):
                        via[ok] = f"matched on name variant '{v}' ~ '{w}'"
            if len(cands) == 1:
                res[sk] = (cands[0], method, "low" if one_sided(sk, cands[0]) else conf,
                           dir_note(sk, cands[0], via.get(cands[0], "")))
                taken[cands[0]] = sk
            elif len(cands) > 1:
                res[sk] = (None, "ambiguous", "none", f"{method}: {len(cands)} candidates")
            else:
                nxt.append((sk, sn))
        pending = nxt
    # fuzzy: unique best >= 0.8 and clear of runner-up by 0.08
    for sk, sn in pending:
        scored = []
        for ok, on in ours:
            if ok in taken or not ok_dir(sk, ok):
                continue
            r = max(difflib.SequenceMatcher(None, banglish_key(v), banglish_key(w)).ratio()
                    for v in parenthetical_variants(sn) for w in parenthetical_variants(on))
            scored.append((r, ok, on))
        scored.sort(reverse=True)
        if scored and scored[0][0] >= 0.8 and (len(scored) == 1 or scored[0][0] - scored[1][0] >= 0.08):
            res[sk] = (scored[0][1], "name_fuzzy", "low" if scored[0][0] < 0.88 else "medium",
                       dir_note(sk, scored[0][1], f"similarity {scored[0][0]:.2f} to '{scored[0][2]}'"))
            taken[scored[0][1]] = sk
        else:
            if directions:
                scored = [(r, ok, ours_orig[ok]) for r, ok, on in scored]
            best = "; ".join(f"{on} {r:.2f}" for r, ok, on in scored[:2])
            res[sk] = (None, "unmatched", "none", f"best candidates: {best}" if best else
                       ("no candidates without a conflicting direction word under parent" if directions and any(
                           not ok_dir(sk, ok) for ok, _ in ours) else "no candidates under parent"))
    return res


def load_seed(div_id="10002"):
    """Seed admin units below the division with seed id div_id (default Rajshahi 10002), plus all rows by id."""
    with open(SEED, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    by_id = {r["id"]: r for r in rows}

    def in_div(r):
        while r.get("parent_id"):
            r = by_id[r["parent_id"]]
            if r["id"] == div_id:
                return True
        return False
    return [r for r in rows if in_div(r)], by_id


# district name differences between HDX (v03 / 2020) and the seed, decided by hand (same P-code district)
DISTRICT_SEED = {"BD5010": "Bogura", "BD5038": "Joypurhat", "BD5064": "Naogaon", "BD5069": "Natore",
                 "BD5070": "Chapainawabganj", "BD5076": "Pabna", "BD5081": "Rajshahi", "BD5088": "Sirajganj"}
# per division (HDX/DGHS district code -> seed district name_en); a division missing here is matched by name
DISTRICT_SEED_BY_DIV = {
    "rajshahi": DISTRICT_SEED,
    "rangpur": {"BD5527": "Dinajpur", "BD5532": "Gaibandha", "BD5549": "Kurigram", "BD5552": "Lalmonirhat",
                "BD5573": "Nilphamari", "BD5577": "Panchagarh", "BD5585": "Rangpur", "BD5594": "Thakurgaon"},
    "dhaka": {"BD3026": "Dhaka", "BD3029": "Faridpur", "BD3033": "Gazipur", "BD3035": "Gopalganj", "BD3048": "Kishoreganj",
              "BD3054": "Madaripur", "BD3056": "Manikganj", "BD3059": "Munshiganj", "BD3067": "Narayanganj",
              "BD3068": "Narsingdi", "BD3082": "Rajbari", "BD3086": "Shariatpur", "BD3093": "Tangail"},
    "chattogram": {"BD2003": "Bandarban", "BD2012": "Brahmanbaria", "BD2013": "Chandpur", "BD2015": "Chattogram",
                   "BD2019": "Cumilla", "BD2022": "Cox's Bazar", "BD2030": "Feni", "BD2046": "Khagrachhari",
                   "BD2051": "Lakshmipur", "BD2075": "Noakhali", "BD2084": "Rangamati"},
    "khulna": {"BD4001": "Bagerhat", "BD4018": "Chuadanga", "BD4041": "Jashore", "BD4044": "Jhenaidah", "BD4047": "Khulna",
               "BD4050": "Kushtia", "BD4055": "Magura", "BD4057": "Meherpur", "BD4065": "Narail", "BD4087": "Satkhira"},
    "barishal": {"BD1004": "Barguna", "BD1006": "Barishal", "BD1009": "Bhola", "BD1042": "Jhalokathi",
                 "BD1078": "Patuakhali", "BD1079": "Pirojpur"},
    "sylhet": {"BD6036": "Habiganj", "BD6058": "Moulvibazar", "BD6090": "Sunamganj", "BD6091": "Sylhet"},
    "mymensingh": {"BD4539": "Jamalpur", "BD4561": "Mymensingh", "BD4572": "Netrokona", "BD4589": "Sherpur"},
}
# per division: source code -> seed admin_areas id for units the name matcher cannot pair (or pairs wrongly), decided by
# hand from the Bangla seed name. Chattogram: "Uttar"/"Dakkhin" are North/South (the fuzzy tier paired Matlab Uttar
# with Matlab South), and Cumilla's Adarsha Sadar / Sadar Dakkhin are the seed's Comilla Sadar (কুমিল্লা সদর) / Sadarsouth
# (সদর দক্ষিণ). Divisions without an entry are matched by name only, as before.
UNIT_SEED_BY_DIV = {
    "chattogram": {"BD20130076": "30056", "BD20130079": "30058", "BD20190067": "30011", "BD20190033": "30014"},
    # Khulna: Dacope = seed Dakop (দাকোপ; no tier pairs them); Paikgachha = seed Paikgasa (পাইকগাছা; only a low fuzzy pair)
    "khulna": {"BD40470017": "30213", "BD40470064": "30206"},
    # Barishal: v03 Indurkani = seed Zianagar (জিয়ানগর); HDX's own 2020 point for the same upazila (BD107990) is named
    # Zianagar, and its three unions (Bali Para, Parerhat, Pattashi) are the seed Zianagar's three unions
    "barishal": {"BD10790090": "30245"},
    # Sylhet: v03 Shantiganj = seed South Sunamganj (দক্ষিণ সুনামগঞ্জ, "Dakshin Sunamganj"); the upazila was renamed and
    # recoded (2020 point BD609027 Dakshin Sunamganj, see UPAZILA_RECODED_BY_DIV), and its eight 2020 unions are the seed
    # South Sunamganj's eight unions
    "sylhet": {"BD60900087": "30301"},
}
# per division: 2020 label-point P-code of an upazila -> v03 P-code, for upazilas renamed with a new code since 2020
# (decided by hand: same unions under both). Without this the 2020 point would be read as a city thana and its unions
# would have no upazila. Divisions without an entry behave as before.
UPAZILA_RECODED_BY_DIV = {
    # Sylhet: Dakshin Sunamganj (2020 BD609027; its 8 union points Durgapasha … Shimulbak) = v03 Shantiganj (BD60900087),
    # BBS 2022 geocode 60-90-87 Shantiganj with the same 8 unions
    "sylhet": {"BD609027": "BD60900087"},
}


def build_crosswalk(units, seed_rows, by_id, source_label, district_key=lambda code: code[:6], district_map=DISTRICT_SEED,
                    pinned=None, directions=False):
    """units: dicts with level, code, name_en, parent_code (district P-code for upazila; upazila code for union ...).
    district_map: district code -> seed district name_en (default Rajshahi); None = match districts by name.
    pinned: source code -> seed id, hand-checked pairs applied before name matching (method code_hand_checked).
    directions: passed to match_names (direction words must agree), for unions and below only.
    Returns crosswalk rows (one per source unit + one per unmatched seed unit)."""
    pinned = pinned or {}
    out = []
    seed_by_level_parent = {}
    for r in seed_rows:
        seed_by_level_parent.setdefault((r["level"], r["parent_id"]), []).append(r)
    code2our = {}

    def row(r, u, method, conf, notes):
        out.append({"our_id": r["id"] if r else "", "our_level": r["level"] if r else "", "our_name_en": r["name_en"] if r else "",
                    "our_path": r["path"] if r else "", "source_code": u["code"] if u else "",
                    "source_name_en": u["name_en"] if u else "", "match_method": method, "confidence": conf,
                    "notes": ((f"source level {u['level']}; " if u else "") + notes).strip("; ")})

    matched_our = set()
    # districts
    districts = {r["name_en"]: r for r in seed_rows if r["level"] == "district"}
    src_d = [u for u in units if u["level"] == "district"]
    if district_map is None:  # no hand-checked table for this division: one-to-one name matching
        res = match_names([(u["code"], u["name_en"]) for u in src_d], [(r["name_en"], r["name_en"]) for r in districts.values()])
        district_map = {district_key(u["code"]): res[u["code"]][0] for u in src_d if res[u["code"]][0]}
    for u in src_d:
        r = districts.get(district_map.get(district_key(u["code"])))
        if r:
            same = latin_key(r["name_en"]) == latin_key(u["name_en"])
            row(r, u, "code_district" if not same else "name_exact", "high",
                "" if same else f"spelling differs ({u['name_en']} vs {r['name_en']}); matched via district code {u['code']}")
            code2our[u["code"]] = r["id"]; matched_our.add(r["id"])
        else:
            row(None, u, "unmatched", "none", "")
    # children level by level
    for lvl_src, lvl_ours in (("upazila", ("upazila",)), ("city_corporation", ("city_corporation",)), ("thana", ()),
                              ("pourashava", ("pourashava",)), ("union", ("union",)), ("ward", ())):
        groups = {}
        for u in units:
            if u["level"] == lvl_src:
                groups.setdefault(u["match_parent"], []).append(u)
        leftovers = []
        for pcode, us in groups.items():
            if not lvl_ours:
                for u in us:
                    row(None, u, "no_seed_level", "none", f"our seed has no {lvl_src} level")
                continue
            parent_id = code2our.get(pcode)
            if not parent_id:
                for u in us:
                    row(None, u, "unmatched", "none", f"parent {pcode} not matched to a seed unit")
                continue
            cands = [r for l in lvl_ours for r in seed_by_level_parent.get((l, parent_id), [])]
            for u in [u for u in us if pinned.get(u["code"]) in {r["id"] for r in cands}]:
                r = by_id[pinned[u["code"]]]
                code2our[u["code"]] = r["id"]; matched_our.add(r["id"])
                row(r, u, "code_hand_checked", "high", f"hand-checked pair ({u['name_en']} = {r['name_en']} {r['name_bn']}); "
                    "the name matcher does not pair these")
                us = [x for x in us if x is not u]
                cands = [x for x in cands if x["id"] != r["id"]]
            if not us:
                continue
            if not cands:
                for u in us:
                    row(None, u, "no_seed_unit", "none", f"our seed has no {lvl_src} under {by_id[parent_id]['name_en']}")
                continue
            res = match_names([(u["code"], u["name_en"]) for u in us], [(r["id"], r["name_en"]) for r in cands],
                              directions and lvl_src in ("pourashava", "union"))
            for u in us:
                oid, method, conf, note = res[u["code"]]
                r = by_id.get(oid) if oid else None
                if r:
                    code2our[u["code"]] = r["id"]; matched_our.add(r["id"])
                    row(r, u, method, conf, note)
                else:
                    leftovers.append((u, parent_id, method, note))
        # second pass: same district, different upazila (boundary/parent changes such as new upazilas)
        by_dist = {}
        for u, parent_id, method, note in leftovers:
            d = by_id[parent_id]["parent_id"] if by_id[parent_id]["level"] != "district" else parent_id
            by_dist.setdefault(d, []).append((u, parent_id, method, note))
        for d, items in by_dist.items():
            pool = [r for r in seed_rows if r["level"] in lvl_ours and r["id"] not in matched_our
                    and by_id.get(r["parent_id"], {}).get("parent_id") == d]
            res2 = match_names([(u["code"], u["name_en"]) for u, *_ in items], [(r["id"], r["name_en"]) for r in pool],
                               directions and lvl_src in ("pourashava", "union"))
            for u, parent_id, method, note in items:
                oid, m2, c2, n2 = res2[u["code"]]
                r = by_id.get(oid) if oid and m2 in ("name_exact", "name_banglish", "name_skeleton") else None
                if r:
                    code2our[u["code"]] = r["id"]; matched_our.add(r["id"])
                    row(r, u, m2 + "_other_parent", "low" if m2 == "name_skeleton" else "medium",
                        f"source parent {by_id[parent_id]['name_en']}, our parent {by_id[r['parent_id']]['name_en']}; check parent change")
                else:
                    row(None, u, method, "none", note)
    # seed units in the division with no source unit
    for r in seed_rows:
        if r["level"] in {u["level"] for u in units} - {"thana", "ward"} and r["id"] not in matched_our:
            p = by_id.get(r["parent_id"], {})
            out.append({"our_id": r["id"], "our_level": r["level"], "our_name_en": r["name_en"], "our_path": r["path"],
                        "source_code": "", "source_name_en": "", "match_method": "no_source_unit", "confidence": "none",
                        "notes": f"no {source_label} unit matched under {p.get('name_en', '?')}"})
    return out, code2our


# ------------------------------------------------------------------ main

def write_csv(path, cols, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r.get(c)) for c in cols})


AREA_COLS = ["level", "name_en", "name_bn", "parent_level", "parent_name_en", "parent_name_bn", "district_en", "upazila_en",
             "code", "code_scheme", "website", "lat", "lon", "source_key", "source_url", "notes"]
FACT_COLS = ["entity_level", "entity_name_en", "district_en", "upazila_en", "code", "fact", "value", "unit", "basis", "year",
             "source_key", "source_url", "notes"]
XW_COLS = ["our_id", "our_level", "our_name_en", "our_path", "source_code", "source_name_en", "match_method", "confidence", "notes"]


def adm4_level(name):
    if re.search(r"paurashav", name, re.I):
        return "pourashava"
    if re.match(r"ward\b", name, re.I):
        return "ward"
    return "union"


def out_dir(folder, division, out=None):
    """--out, else the collector folder for Rajshahi, else the sibling folder <folder>_<division> (DIVISIONS.md)."""
    if out:
        return os.path.abspath(out)
    return folder if division == "rajshahi" else os.path.join(os.path.dirname(folder), os.path.basename(folder) + "_" + division)


def division_key(key, division):
    """National key + division suffix (DIVISIONS.md); Rajshahi keeps the original key."""
    return key if division == "rajshahi" else f"{key}_{division.upper()}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--division", default="rajshahi", choices=sorted(DIVISIONS))
    ap.add_argument("--out", default=None, help="output folder (default: this folder for rajshahi, else ../hdx_cod_ab_bgd_<division>)")
    ap.add_argument("--cache", default=os.path.join(tempfile.gettempdir(), "elaka360_cache"))
    a = ap.parse_args()
    recoded = UPAZILA_RECODED_BY_DIV.get(a.division, {})
    global KEY, DIV_PCODE
    _, bbs, seed_id, div_name = DIVISIONS[a.division]
    KEY = division_key(KEY, a.division)
    DIV_PCODE = "BD" + bbs
    OUT = out_dir(HERE, a.division, a.out)
    os.makedirs(a.cache, exist_ok=True)
    os.makedirs(os.path.join(OUT, "raw"), exist_ok=True)

    meta = get(API).json()["result"]
    res = {r["name"]: r for r in meta["resources"]}
    gj = res["bgd_admin_boundaries.geojson.zip"]
    zpath = os.path.join(a.cache, "hdx_bgd_admin_boundaries.geojson.zip")
    if not os.path.isfile(zpath) or os.path.getsize(zpath) != int(gj.get("size") or -1):
        with open(zpath, "wb") as f:
            f.write(get(gj["url"]).content)
    snap = {k: meta.get(k) for k in ("name", "title", "license_id", "license_title", "license_url", "dataset_source",
                                     "dataset_date", "last_modified", "metadata_modified", "caveats", "notes",
                                     "methodology_other")}
    snap["organization"] = meta["organization"]["title"]
    snap["resources"] = [{k: r.get(k) for k in ("name", "format", "size", "url", "last_modified")} for r in meta["resources"]]
    json.dump(snap, open(os.path.join(OUT, "raw", "hdx_cod_ab_bgd_package.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    z = zipfile.ZipFile(zpath)
    load = lambda n: json.load(io.TextIOWrapper(z.open(n), encoding="utf-8"))
    adm = {}
    for lvl in (1, 2, 3):
        adm[lvl] = [f for f in load(f"bgd_admin{lvl}.geojson")["features"] if f["properties"]["adm1_pcode"] == DIV_PCODE]
    pts = [f for f in load("bgd_adminpoints.geojson")["features"] if f["properties"].get("adm1_pcode") == DIV_PCODE]
    json.dump({"type": "FeatureCollection", "name": f"bgd_adminpoints ({div_name} Division {DIV_PCODE})", "features": pts},
              open(os.path.join(OUT, "raw", f"bgd_adminpoints_{a.division}.geojson"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))

    # ---------------- boundaries.geojson (v03 polygons)
    feats, areas, facts, units = [], [], [], []
    div = adm[1][0]["properties"]
    lvl_name = {1: "division", 2: "district", 3: "upazila"}
    pt3 = {f["properties"]["adm3_pcode"]: f["properties"] for f in pts if f["properties"]["admin_level"] == 3}
    old3 = {f["properties"]["adm3_pcode"][:6] + f["properties"]["adm3_pcode"][-2:] for f in adm[3]} | set(recoded)
    city_pts = any(c not in old3 for c in pt3)  # 2020 level-3 points that are city thanas, not v03 upazilas
    for lvl in (1, 2, 3):
        for f in sorted(adm[lvl], key=lambda f: f["properties"][f"adm{lvl}_pcode"]):
            p = f["properties"]
            code = p[f"adm{lvl}_pcode"]
            name = p[f"adm{lvl}_name"]
            level = lvl_name[lvl]
            if lvl == 3 and "city corporation" in name.lower():
                level = "city_corporation"
            parent_code = p.get(f"adm{lvl - 1}_pcode") if lvl > 1 else "BD"
            g = simplify_geom(f["geometry"], SIMPLIFY_DEG)
            feats.append({"type": "Feature", "properties": {
                "level": level, "name_en": name, "name_bn": p.get(f"adm{lvl}_name1") or "", "code": code,
                "code_scheme": "HDX_PCODE", "parent_code": parent_code, "district_en": p.get("adm2_name") or "",
                "upazila_en": name if level == "upazila" else "", "source_key": KEY}, "geometry": g})
            notes = [f"COD-AB v03, valid_on {p.get('valid_on')}"]
            if lvl == 3:
                old = next((k for k, v in recoded.items() if v == code), code[:6] + code[-2:])
                if level == "upazila" and old in pt3:
                    notes.append(f"2020 P-code {old} ({pt3[old]['name']})" + ("; renamed and recoded since 2020 "
                                 "(same unions; hand-checked)" if old in recoded else ""))
                elif level == "upazila":
                    notes.append("no 2020 label point for this upazila (created after the 2020 list or merged in it)")
                if level == "city_corporation":
                    notes.append("thana-level units of the city are in the 2020 points (level thana)" if city_pts
                                 else "no thana or ward units of the city in the 2020 points")
            areas.append({"level": level, "name_en": name, "name_bn": p.get(f"adm{lvl}_name1") or "",
                          "parent_level": {1: "country", 2: "division", 3: "district"}[lvl],
                          "parent_name_en": p.get(f"adm{lvl - 1}_name") if lvl > 1 else "Bangladesh",
                          "district_en": p.get("adm2_name") or "", "upazila_en": name if level == "upazila" else "",
                          "code": code, "code_scheme": "HDX_PCODE", "lat": round(p["center_lat"], 5),
                          "lon": round(p["center_lon"], 5), "source_key": KEY, "source_url": PAGE,
                          "notes": "; ".join(notes) + "; lat/lon = HDX center_lat/center_lon"})
            facts.append({"entity_level": level, "entity_name_en": name, "district_en": p.get("adm2_name") or "",
                          "upazila_en": name if level == "upazila" else "", "code": code, "fact": "area_km2",
                          "value": round(p["area_sqkm"], 2), "unit": "km2", "basis": "computed_by_source_from_polygon",
                          "year": "2025", "source_key": KEY, "source_url": PAGE,
                          "notes": "HDX area_sqkm attribute of the COD-AB v03 polygon; not an official BBS area figure"})
            if lvl >= 2:
                units.append({"level": level, "code": code, "name_en": name,
                              "match_parent": code if lvl == 2 else parent_code})

    # ---------------- 2020 label points: thanas (level 3) and ADM4 (unions, paurashavas, city wards)
    v03_by_old = {}
    for f in adm[3]:
        c = f["properties"]["adm3_pcode"]
        v03_by_old[c[:6] + c[-2:]] = c
    v03_by_old.update(recoded)
    for f in sorted(pts, key=lambda f: (f["properties"]["admin_level"], f["properties"].get("adm4_pcode") or f["properties"].get("adm3_pcode") or "")):
        p = f["properties"]
        x, y = f["geometry"]["coordinates"][:2]
        if p["admin_level"] == 3 and p["adm3_pcode"] not in v03_by_old:
            level, code, name = "thana", p["adm3_pcode"], p["adm3_name"]
            parent_level, parent_name, upz = "district", p["adm2_name"], ""
            match_parent = "BD5081" if p["adm2_pcode"] == "BD5081" else p["adm2_pcode"]
        elif p["admin_level"] == 4:
            code, name = p["adm4_pcode"], p["adm4_name"]
            level = adm4_level(name)
            is_thana = p["adm3_pcode"] not in v03_by_old
            parent_level, parent_name, upz = ("thana" if is_thana else "upazila"), p["adm3_name"], ("" if is_thana else p["adm3_name"])
            match_parent = v03_by_old.get(p["adm3_pcode"], p["adm3_pcode"])
        else:
            continue
        areas.append({"level": level, "name_en": name, "name_bn": p.get("adm4_name1") or "", "parent_level": parent_level,
                      "parent_name_en": parent_name, "district_en": p["adm2_name"], "upazila_en": upz, "code": code,
                      "code_scheme": "HDX_PCODE_2020", "lat": round(y, 5), "lon": round(x, 5), "source_key": KEY,
                      "source_url": PAGE,
                      "notes": f"from bgd_adminpoints (valid_on {p.get('valid_on')}); lat/lon = HDX label point, not a centroid; "
                               "no ADM4 polygon in COD-AB v03 (see GEOBOUNDARIES_BGD_ADM4)"})
        units.append({"level": level, "code": code, "name_en": name, "match_parent": match_parent})

    fc = {"type": "FeatureCollection", "name": f"{KEY} {div_name} Division ({DIV_PCODE}) levels 1-3", "features": feats}
    with open(os.path.join(OUT, "boundaries.geojson"), "w", encoding="utf-8") as fh:
        json.dump(fc, fh, ensure_ascii=False, separators=(",", ":"))
    write_csv(os.path.join(OUT, "areas.csv"), AREA_COLS, areas)
    write_csv(os.path.join(OUT, "facts.csv"), FACT_COLS, facts)

    seed_rows, by_id = load_seed(seed_id)
    xw, _ = build_crosswalk(units, seed_rows, by_id, "HDX", district_map=DISTRICT_SEED_BY_DIV.get(a.division),
                            pinned=UNIT_SEED_BY_DIV.get(a.division), directions=a.division in DIRECTION_WORD_DIVS)
    write_csv(os.path.join(OUT, "crosswalk.csv"), XW_COLS, xw)

    files = ["areas.csv", "boundaries.geojson", "facts.csv", "crosswalk.csv", f"raw/bgd_adminpoints_{a.division}.geojson",
             "raw/hdx_cod_ab_bgd_package.json"]
    manifest = {
        "key": KEY,
        "name": f"Bangladesh - Subnational Administrative Boundaries (COD-AB v03), {div_name} Division extract",
        "organization": "OCHA (ROAP / FIS) on HDX; source: Bangladesh Bureau of Statistics (BBS)",
        "source_type": "humanitarian_dataset",
        "trust_level": 3,
        "urls": [PAGE, gj["url"], API],
        "accessed": datetime.date.today().isoformat(),
        "publication_date": (meta.get("last_modified") or "")[:10] or None,
        "license": "CC-BY-IGO-3.0",
        "license_url": meta.get("license_url"),
        "attribution": "Bangladesh Bureau of Statistics (BBS); OCHA ROAP; published by OCHA FIS / HDX (CC BY-IGO)",
        "files": {f: sha256(os.path.join(OUT, f)) for f in files},
        "notes": ("COD-AB v03: ADM1-ADM3 polygons, valid_on 2023-05-21, reviewed 2025-06-01, HDX resource last modified "
                  f"{meta.get('last_modified')}. HDX dataset_date {meta.get('dataset_date')}; 'boundaries created by the "
                  "source 01 January 2010'. No ADM4 (union) polygons in v03; union/paurashava/ward codes come from the "
                  "bgd_adminpoints layer (valid_on 2020-11-13, older P-code scheme BD+div+dist+upz+union, 2 digits each). "
                  "Polygons simplified (Douglas-Peucker 0.0002 deg, 5 decimals) ring by ring, so shared borders can have "
                  "slivers of a few metres."),
        "division": a.division,
        "kind": KIND,
    }
    json.dump(manifest, open(os.path.join(OUT, "SOURCE.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    from collections import Counter
    print("areas", Counter(r["level"] for r in areas))
    print("crosswalk", Counter((r["our_level"] or "-", r["match_method"]) for r in xw))
    print("boundaries.geojson", os.path.getsize(os.path.join(OUT, "boundaries.geojson")), "bytes")


if __name__ == "__main__":
    sys.exit(main())
