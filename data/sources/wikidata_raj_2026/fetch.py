#!/usr/bin/env python3
"""Wikidata items with coordinates (P625) in a Bangladesh division -> places.csv (+ SOURCE.json, REPORT.md).

stdlib + requests only. Usage:
    python3 fetch.py [--division rajshahi|rangpur|dhaka|chattogram|khulna|barishal|sylhet|mymensingh] [--out DIR] [--offline]
Default: Rajshahi Division into this folder (DIVISIONS.md). Other divisions write ../wikidata_<code>_2026/.
--offline rebuilds the outputs from raw/wikidata_<division>.json (no network).

How it works
1. Robots gate: query.wikidata.org/robots.txt is read first and evaluated with RFC 9309 rules (longest match wins,
   `*` and `$` supported). If `/sparql` is disallowed for our User-Agent, the script stops and writes nothing.
2. Discovery on the Wikidata Query Service (one query at a time, >= MIN_DELAY s apart, 429/Retry-After honoured):
   a. every item with P625 inside each district's bounding box (wikibase:box; split in four on timeout);
   b. every item with P625 whose P131 chain reaches the division item (split by the division's direct P131
      children on timeout).
3. Details for the union of both sets in batches: bn/en labels, P31 classes, P856, P1329, P571 (with precision),
   P131, bn/en Wikipedia sitelinks (URLs only; no article text). P131 ancestors are resolved for the chain labels.
4. Classes are mapped to categories.csv keys through P279* roots (ROOTS below). Administrative units (division,
   district, upazila, union, ward, mouza, thana, municipality / city corporation, and settlements such as
   villages, towns, cities, neighbourhoods) are excluded and counted.
5. Points are placed in district/upazila polygons of ../hdx_cod_ab_bgd*/boundaries.geojson; seed English names come
   from that folder's crosswalk.csv. Points outside the division polygon are dropped and counted.
"""
# --- polite HTTP helper (stdlib + requests only) --------------------------------------------------------
import argparse, collections, csv, datetime, email.utils, hashlib, io, json, os, re, sys, time, unicodedata
import urllib.parse
import requests

UA = "Elaka360-data-pipeline (research; contact via repository)"
MIN_DELAY = 2.0          # seconds between requests to the same host (WDQS asks for one query at a time)
MAX_429 = 6              # give up after this many consecutive 429 answers
WDQS = "https://query.wikidata.org/sparql"

_last, _robots = {}, {}
S = requests.Session()
S.headers["User-Agent"] = UA


class Refused(Exception):
    """The host refused us (robots.txt or repeated rate limiting). Recorded, never worked around."""


def _robots_parse(txt):
    groups, cur, last_ua = [], None, False
    for line in txt.splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        k, v = [x.strip() for x in line.split(":", 1)]
        k = k.lower()
        if k == "user-agent":
            if not last_ua:
                cur = {"ua": [], "rules": []}
                groups.append(cur)
            cur["ua"].append(v.lower())
            last_ua = True
        elif k in ("allow", "disallow") and cur is not None:
            cur["rules"].append((k == "allow", v))
            last_ua = False
        else:
            last_ua = False
    return groups


def _robots_rx(p):
    end = p.endswith("$")
    p = p[:-1] if end else p
    return re.compile("^" + ".*".join(re.escape(x) for x in p.split("*")) + ("$" if end else ""))


def allowed(url):
    """RFC 9309: the group naming our UA (else '*'); longest matching rule wins, Allow wins ties."""
    p = urllib.parse.urlsplit(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        txt = ""
        try:
            r = _get_raw(base + "/robots.txt")
            if r.status_code == 200 and "html" not in r.headers.get("content-type", ""):
                txt = r.content.decode("utf-8-sig", "replace")
        except requests.RequestException:
            pass
        _robots[base] = _robots_parse(txt)
    groups, ua = _robots[base], UA.lower()
    sel = [g for g in groups if any(u != "*" and u in ua for u in g["ua"])] or [g for g in groups if "*" in g["ua"]]
    path = (p.path or "/") + (("?" + p.query) if p.query else "")
    best = None
    for allow, rule in (r for g in sel for r in g["rules"] if r[1]):
        if _robots_rx(rule).match(path) and (best is None or len(rule) > len(best[1]) or (len(rule) == len(best[1]) and allow)):
            best = (allow, rule)
    return True if best is None else best[0]


def _wait(host):
    w = MIN_DELAY - (time.time() - _last.get(host, 0))
    if w > 0:
        time.sleep(w)


def _get_raw(url, **kw):
    host = urllib.parse.urlsplit(url).netloc
    _wait(host)
    try:
        return S.get(url, timeout=kw.pop("timeout", 60), **kw)
    finally:
        _last[host] = time.time()


def _retry_after(r):
    v = r.headers.get("retry-after", "")
    if v.isdigit():
        return int(v)
    try:
        return max(0, int(email.utils.parsedate_to_datetime(v).timestamp() - time.time()))
    except (TypeError, ValueError):
        return 60


WDQS_EXCEPTION = True   # see sparql(); set False to honour query.wikidata.org/robots.txt again


class Timeout(Exception):
    pass


def sparql(query):
    """One WDQS query (POST, JSON). Raises Timeout on a server-side timeout, Refused when the host refuses."""
    # WDQS is a documented public API; its robots.txt targets crawlers. Owner decision 2026-11-18 (COLLECTION_FORMAT.md,
    # "Exceptions"): the query endpoint is used despite the robots.txt rule, one query at a time, Retry-After honoured.
    if not allowed(WDQS) and not WDQS_EXCEPTION:
        raise Refused(f"robots.txt of query.wikidata.org disallows {urllib.parse.urlsplit(WDQS).path} for {UA!r}")
    host = urllib.parse.urlsplit(WDQS).netloc
    n429 = nerr = 0
    while True:
        _wait(host)
        try:
            r = S.post(WDQS, data={"query": query}, headers={"Accept": "application/sparql-results+json"}, timeout=90)
        except requests.RequestException as e:
            _last[host] = time.time()
            nerr += 1
            if nerr > 3:
                raise Timeout(str(e))
            time.sleep(15 * nerr)
            continue
        _last[host] = time.time()
        if r.status_code == 429:
            n429 += 1
            wait = _retry_after(r)
            print(f"  429 from WDQS, waiting {wait}s (Retry-After)", flush=True)
            if n429 >= MAX_429:
                raise Refused(f"WDQS kept answering 429 ({n429}x); last body: {r.text[:200]!r}")
            time.sleep(max(wait, 5))
            continue
        if r.status_code == 403:
            raise Refused(f"WDQS answered 403: {r.text[:200]!r}")
        if r.status_code in (500, 502, 504) and ("TimeoutException" in r.text or r.status_code == 504):
            raise Timeout(f"HTTP {r.status_code}")                  # query too big: caller splits it
        if r.status_code >= 500:
            nerr += 1
            if nerr > 3:
                raise Timeout(f"HTTP {r.status_code}")
            time.sleep(15 * nerr)
            continue
        r.raise_for_status()
        return r.json()["results"]["bindings"]
# --- end helper ---------------------------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.dirname(HERE)
TODAY = datetime.date.today().isoformat()

# division -> (code, boundaries folder, English labels of the division item on Wikidata, Bangla name)
DIVS = {
    "rajshahi": ("raj", "hdx_cod_ab_bgd", ["Rajshahi Division"], "রাজশাহী বিভাগ"),
    "rangpur": ("rang", "hdx_cod_ab_bgd_rangpur", ["Rangpur Division"], "রংপুর বিভাগ"),
    "dhaka": ("dhk", "hdx_cod_ab_bgd_dhaka", ["Dhaka Division"], "ঢাকা বিভাগ"),
    "chattogram": ("ctg", "hdx_cod_ab_bgd_chattogram", ["Chittagong Division", "Chattogram Division"], "চট্টগ্রাম বিভাগ"),
    "khulna": ("khl", "hdx_cod_ab_bgd_khulna", ["Khulna Division"], "খুলনা বিভাগ"),
    "barishal": ("bar", "hdx_cod_ab_bgd_barishal", ["Barisal Division", "Barishal Division"], "বরিশাল বিভাগ"),
    "sylhet": ("syl", "hdx_cod_ab_bgd_sylhet", ["Sylhet Division"], "সিলেট বিভাগ"),
    "mymensingh": ("mym", "hdx_cod_ab_bgd_mymensingh", ["Mymensingh Division"], "ময়মনসিংহ বিভাগ"),
}
Q_DIVISION_OF_BD = "Q878040"   # 'division of Bangladesh' (checked 2026-11-18)

# --- class roots (every QID checked against its Wikidata label on 2026-11-18) ----------------------------
# Administrative units of Bangladesh: always excluded (the seed has them).
ADMIN_HARD = {
    "Q878040": "division of Bangladesh", "Q152732": "district of Bangladesh", "Q620471": "upazila of Bangladesh",
    "Q3812392": "union council of Bangladesh", "Q15619375": "ward of Bangladesh", "Q96316075": "thana",
    "Q23759397": "municipality of Bangladesh", "Q15284": "municipality",
}
# Settlements and generic territorial units: excluded unless one of the place roots below also matches
# (a village item that is also an archaeological site stays as the site).
ADMIN_SOFT = {"Q6926427": "mouza", "Q532": "village", "Q123705": "neighborhood", "Q486972": "human settlement",
              "Q56061": "administrative territorial entity"}
# Place roots in priority order: the first root reached by any P31 class decides. (qid, label, category_key,
# proposed subcategory when the key is only a top-level one). Order matters: church/Buddhist temple are
# subclasses of temple, temple of shrine, botanical garden of research institute, bus station of bus stop …
ROOTS = [
    ("Q494230", "medical school", "education.medical_college", None),
    ("Q1813474", "teaching hospital", "health.medical_college_hospital", None),
    ("Q1059324", "university hospital", "health.medical_college_hospital", None),
    ("Q3918", "university", "education.university", None),
    ("Q132834", "madrasa", "education.madrasa", None),
    ("Q322563", "vocational school", "education.technical", None),
    ("Q189004", "college", "education.college", None),
    ("Q159334", "secondary school", "education.secondary_school", None),
    ("Q9842", "primary school", "education.primary_school", None),
    ("Q167346", "botanical garden", "tourism.park", None),
    ("Q43501", "zoo", "tourism.park", None),
    ("Q7075", "library", "education", "education.library"),
    ("Q31855", "research institute", "education", "education.research_institute"),
    ("Q3914", "school", "education", None),
    ("Q2385804", "educational institution", "education", None),
    ("Q16917", "hospital", "health.hospital", None),
    ("Q1774898", "clinic", "health.clinic", None),
    ("Q13107184", "pharmacy", "health.pharmacy", None),
    ("Q4260475", "medical facility", "health", None),
    ("Q32815", "mosque", "religious.mosque", None),
    ("Q3595469", "Eidgah", "religious.eidgah", None),
    ("Q16970", "church building", "religious.church", None),
    ("Q5393308", "Buddhist temple", "religious.buddhist_vihara", None),
    ("Q199451", "pagoda", "religious.buddhist_vihara", None),
    ("Q842402", "Hindu temple", "religious.temple", None),
    ("Q44539", "temple", "religious.temple", None),
    ("Q2639699", "dargah", "religious.mazar", None),
    ("Q39614", "cemetery", "religious", "religious.cemetery"),
    ("Q697295", "shrine", "religious", None),
    ("Q1370598", "structure of worship", "religious", None),
    ("Q861951", "police station", "emergency.police_station", None),
    ("Q1195942", "fire station", "emergency.fire_station", None),
    ("Q1137809", "courthouse", "government.court", None),
    ("Q35054", "post office", "government.post_office", None),
    ("Q40357", "prison", "government", "government.prison"),
    ("Q245016", "military base", "government", "government.military_base"),
    ("Q33506", "museum", "tourism.museum", None),
    ("Q46169", "national park", "tourism.park", None),
    ("Q22698", "park", "tourism.park", None),
    ("Q839954", "archaeological site", "tourism.archaeological", None),
    ("Q109607", "ruins", "tourism.archaeological", None),
    ("Q2099235", "Rajbari", "tourism.historical", None),
    ("Q16560", "palace", "tourism.historical", None),
    ("Q1802963", "mansion", "tourism.historical", None),
    ("Q57821", "fortification", "tourism.historical", None),
    ("Q162875", "mausoleum", "tourism.historical", None),
    ("Q381885", "tomb", "tourism.historical", None),
    ("Q4989906", "monument", "tourism.historical", None),
    ("Q5003624", "memorial", "tourism.historical", None),
    ("Q210272", "cultural heritage", "tourism.historical", None),
    ("Q34038", "waterfall", "tourism.waterfall", None),
    ("Q40080", "beach", "tourism.beach", None),
    ("Q8502", "mountain", "tourism.hill", None),
    ("Q54050", "hill", "tourism.hill", None),
    ("Q13060227", "haor", "tourism.river_haor", None),
    ("Q2900677", "beel", "tourism.river_haor", None),
    ("Q4022", "river", "tourism.river_haor", None),
    ("Q47521", "stream", "tourism.river_haor", None),
    ("Q209333", "oxbow lake", "tourism.river_haor", None),
    ("Q23397", "lake", "tourism.river_haor", None),
    ("Q170321", "wetland", "tourism.river_haor", None),
    ("Q131681", "reservoir", "tourism.river_haor", None),
    ("Q3253281", "artificial pond", "tourism.river_haor", None),
    ("Q4421", "forest", "tourism.natural", None),
    ("Q473972", "protected area", "tourism.natural", None),
    ("Q162602", "river island", "tourism.natural", None),
    ("Q23442", "island", "tourism.natural", None),
    ("Q1107656", "garden", "tourism.park", None),
    ("Q350495", "barrage", "agriculture", "agriculture.irrigation_structure"),
    ("Q12323", "dam", "agriculture", "agriculture.irrigation_structure"),
    ("Q12284", "canal", "agriculture", "agriculture.irrigation_structure"),
    ("Q188913", "plantation", "agriculture.farm", None),
    ("Q55488", "railway station", "transport.railway_station", None),
    ("Q1248784", "airport", "transport.airport", None),
    ("Q494829", "bus station", "transport.bus_terminal", None),
    ("Q953806", "bus stop", "transport.bus_stop", None),
    ("Q4303352", "passenger ship terminal", "transport.launch_ghat", None),
    ("Q1010155", "ghat", "transport.launch_ghat", None),
    ("Q44782", "port", "transport", "transport.port"),
    ("Q12280", "bridge", "transport", "transport.bridge"),
    ("Q34442", "road", "transport", "transport.road"),
    ("Q219760", "bazaar", "business.market", None),
    ("Q330284", "marketplace", "business.market", None),
    ("Q37654", "market", "business.market", None),
    ("Q11315", "shopping center", "business.shopping", None),
    ("Q11707", "restaurant", "business.restaurant", None),
    ("Q27686", "hotel", "business", "business.hotel"),
    ("Q41253", "movie theater", "business", "business.cinema"),
    ("Q22687", "bank", "finance.bank", None),
    ("Q1662100", "industrial park", "business", "business.industrial_facility"),
    ("Q83405", "factory", "business", "business.industrial_facility"),
    ("Q159719", "power station", "business", "business.industrial_facility"),
    ("Q483110", "stadium", "other", "other.sports_venue"),
    ("Q1076486", "sports venue", "other", "other.sports_venue"),
    ("Q79913", "non-governmental organization", "other.ngo", None),
    ("Q163740", "nonprofit organization", "other.ngo", None),
    ("Q570116", "tourist attraction", "tourism", None),
    ("Q4830453", "business", "business", None),
    ("Q783794", "company", "business", None),
    ("Q327333", "government agency", "government", None),
]
# Generic fallbacks, tried after the settlement check: closest top-level key.
GENERIC = [("Q41176", "building", "other", "other.building"), ("Q811979", "built structure", "other", "other.building"),
           ("Q13226383", "facility", "other", None), ("Q43229", "organization", "other", None)]
TEA_LABEL = re.compile(r"\btea (estate|garden|plantation)\b", re.I)   # tea estates: by class label (no single root)

ALL_ROOTS = list(ADMIN_HARD) + list(ADMIN_SOFT) + [r[0] for r in ROOTS] + [g[0] for g in GENERIC]
PLACE_COLS = ["source_key", "source_id", "name_bn", "name_en", "category_key", "lat", "lon", "address", "district_en",
              "upazila_en", "phone", "website", "email", "opening_hours", "operator", "ownership", "extra_json",
              "source_url", "notes"]


def qid(uri):
    return uri.rsplit("/", 1)[-1] if uri else ""


def nfc(s):
    return unicodedata.normalize("NFC", s or "").strip()


# --- geometry ------------------------------------------------------------------------------------------
def _rings(geom):
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    return polys


def _in_ring(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


class Poly:
    def __init__(self, feat):
        self.props = feat["properties"]
        self.polys = _rings(feat["geometry"])
        xs = [c[0] for p in self.polys for c in p[0]]
        ys = [c[1] for p in self.polys for c in p[0]]
        self.bbox = (min(xs), min(ys), max(xs), max(ys))

    def contains(self, x, y):
        b = self.bbox
        if not (b[0] <= x <= b[2] and b[1] <= y <= b[3]):
            return False
        return any(_in_ring(x, y, p[0]) and not any(_in_ring(x, y, h) for h in p[1:]) for p in self.polys)


def load_geo(bdir):
    gj = json.load(open(os.path.join(bdir, "boundaries.geojson"), encoding="utf-8"))
    by = collections.defaultdict(list)
    for f in gj["features"]:
        by[f["properties"]["level"]].append(Poly(f))
    cw = {}
    with open(os.path.join(bdir, "crosswalk.csv"), encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["source_code"] and r["our_name_en"] and r["our_level"] in ("district", "upazila", "city_corporation"):
                cw[r["source_code"]] = r["our_name_en"]
    return by, cw


def locate(geo, cw, lon, lat):
    """-> (inside_division, district_en, upazila_en, note)"""
    if not any(p.contains(lon, lat) for p in geo["division"]):
        return False, "", "", ""
    d = next((p for p in geo["district"] if p.contains(lon, lat)), None)
    u = next((p for p in geo["upazila"] if p.contains(lon, lat)), None)
    notes = []
    dn = un = ""
    if d:
        dn = cw.get(d.props["code"]) or d.props["name_en"]
        if d.props["code"] not in cw:
            notes.append(f"district name from HDX ({d.props['code']}), no seed match")
    else:
        notes.append("inside the division polygon but in no district polygon (border sliver)")
    if u:
        un = cw.get(u.props["code"]) or u.props["name_en"]
        if u.props["code"] not in cw:
            notes.append(f"upazila name from HDX ({u.props['code']} {u.props['name_en']}), no seed match")
    return True, dn, un, "; ".join(notes)


# --- Wikidata steps ------------------------------------------------------------------------------------
def _point(wkt):
    m = re.fullmatch(r"\s*Point\(\s*([-0-9.eE]+)\s+([-0-9.eE]+)\s*\)\s*", wkt or "")   # Earth only (no globe IRI)
    return (float(m.group(1)), float(m.group(2))) if m else None


def resolve_division(labels, geo):
    vals = " ".join(json.dumps(l) + "@en" for l in labels)
    rows = sparql(f"""SELECT DISTINCT ?d ?c WHERE {{ VALUES ?l {{ {vals} }}
      ?d rdfs:label|skos:altLabel ?l ; wdt:P31 wd:{Q_DIVISION_OF_BD} . OPTIONAL {{ ?d wdt:P625 ?c }} }}""")
    cands = {}
    for b in rows:
        pt = _point(b.get("c", {}).get("value"))
        cands.setdefault(qid(b["d"]["value"]), []).append(pt)
    inside = [q for q, pts in cands.items() if any(p and any(g.contains(*p) for g in geo["division"]) for p in pts)]
    pick = inside or sorted(cands)
    if len(pick) != 1:
        raise SystemExit(f"could not resolve the division item for {labels}: {cands}")
    return pick[0]


def box_query(sw, ne):
    return f"""SELECT ?item ?coord WHERE {{ SERVICE wikibase:box {{ ?item wdt:P625 ?coord .
      bd:serviceParam wikibase:cornerSouthWest "Point({sw[0]:.5f} {sw[1]:.5f})"^^geo:wktLiteral .
      bd:serviceParam wikibase:cornerNorthEast "Point({ne[0]:.5f} {ne[1]:.5f})"^^geo:wktLiteral . }} }}"""


def discover(div_q, geo, log):
    found = collections.defaultdict(lambda: {"coords": set(), "box": False, "via_p131": False})

    def add(rows, how):
        for b in rows:
            pt = _point(b["coord"]["value"])
            if pt:
                f = found[qid(b["item"]["value"])]
                f["coords"].add(pt)
                f[how] = True

    def box(bb, depth=0):
        try:
            add(sparql(box_query((bb[0], bb[1]), (bb[2], bb[3]))), "box")
        except Timeout:
            if depth >= 3:
                log.append(f"box {bb} timed out at depth {depth}; left out")
                return
            mx, my = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
            for q in ((bb[0], bb[1], mx, my), (mx, bb[1], bb[2], my), (bb[0], my, mx, bb[3]), (mx, my, bb[2], bb[3])):
                box(q, depth + 1)

    for d in sorted(geo["district"], key=lambda p: p.props["name_en"]):
        b = d.bbox
        print(f"  box {d.props['name_en']}", flush=True)
        box((b[0] - 0.01, b[1] - 0.01, b[2] + 0.01, b[3] + 0.01))
    print("  P131 chain", flush=True)
    try:
        add(sparql(f"SELECT ?item ?coord WHERE {{ ?item wdt:P131+ wd:{div_q} ; wdt:P625 ?coord . }}"), "via_p131")
    except Timeout:
        kids = [qid(b["c"]["value"]) for b in sparql(f"SELECT DISTINCT ?c WHERE {{ ?c wdt:P131 wd:{div_q} }}")]
        add(sparql(f"SELECT ?item ?coord WHERE {{ wd:{div_q} ^wdt:P131 ?item ; wdt:P625 ?coord . }}"), "via_p131")
        for k in kids:
            try:
                add(sparql(f"SELECT ?item ?coord WHERE {{ ?item wdt:P131+ wd:{k} ; wdt:P625 ?coord . }}"), "via_p131")
            except Timeout:
                log.append(f"P131 query under {k} timed out; those items rely on the box query")
    return found


PREC = {7: "century", 8: "decade", 9: "year", 10: "month", 11: "day"}


def _time(v, prec):
    """Wikidata time value -> string at its stated precision (never more precise than the source)."""
    m = re.match(r"([+-]?\d+)-(\d\d)-(\d\d)", v or "")
    if not m:
        return ""
    y, mo, d = m.groups()
    y = str(int(y))
    p = int(prec) if prec else 0
    if p >= 11:
        return f"{y}-{mo}-{d}"
    if p == 10:
        return f"{y}-{mo}"
    if p == 9:
        return y
    if p == 8:
        return f"{y[:-1]}0s"
    if p == 7:
        return f"century {int(y) // 100 + (0 if int(y) % 100 == 0 else 1)}"
    return ""


def details(qids, log):
    out = {}
    q = sorted(qids, key=lambda s: int(s[1:]))
    for i in range(0, len(q), 150):
        chunk = q[i:i + 150]
        print(f"  details {i + len(chunk)}/{len(q)}", flush=True)
        vals = " ".join("wd:" + x for x in chunk)
        rows = sparql(f"""SELECT ?item (SAMPLE(?bn) AS ?bnl) (SAMPLE(?en) AS ?enl)
          (GROUP_CONCAT(DISTINCT STRAFTER(STR(?c), "entity/"); separator="|") AS ?p31)
          (GROUP_CONCAT(DISTINCT STR(?web); separator="|") AS ?p856)
          (GROUP_CONCAT(DISTINCT STR(?ph); separator="|") AS ?p1329)
          (GROUP_CONCAT(DISTINCT CONCAT(STR(?t), "/", STR(?pr)); separator="|") AS ?p571)
          (GROUP_CONCAT(DISTINCT STRAFTER(STR(?p), "entity/"); separator="|") AS ?p131)
          (SAMPLE(?bnw) AS ?bnwiki) (SAMPLE(?enw) AS ?enwiki)
          WHERE {{ VALUES ?item {{ {vals} }}
            OPTIONAL {{ ?item rdfs:label ?bn FILTER(LANG(?bn) = "bn") }}
            OPTIONAL {{ ?item rdfs:label ?en FILTER(LANG(?en) = "en") }}
            OPTIONAL {{ ?item wdt:P31 ?c }}
            OPTIONAL {{ ?item wdt:P856 ?web }}
            OPTIONAL {{ ?item wdt:P1329 ?ph }}
            OPTIONAL {{ ?item p:P571 ?st . ?st wikibase:rank ?rk . FILTER(?rk != wikibase:DeprecatedRank)
                       ?st psv:P571 [ wikibase:timeValue ?t ; wikibase:timePrecision ?pr ] }}
            OPTIONAL {{ ?item wdt:P131 ?p }}
            OPTIONAL {{ ?bnw schema:about ?item ; schema:isPartOf <https://bn.wikipedia.org/> }}
            OPTIONAL {{ ?enw schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> }}
          }} GROUP BY ?item""")
        for b in rows:
            g = lambda k: b.get(k, {}).get("value", "")
            sp = lambda k: [x for x in g(k).split("|") if x]
            inc = []
            for tv in sp("p571"):
                t, _, pr = tv.rpartition("/")
                s = _time(t, pr)
                if s and s not in inc:
                    inc.append(s)
            out[qid(g("item"))] = {"bn": nfc(g("bnl")), "en": nfc(g("enl")), "p31": sorted(set(sp("p31"))),
                                    "web": sorted(set(sp("p856"))), "phone": sorted(set(sp("p1329"))),
                                    "inception": inc, "p131": sorted(set(sp("p131"))),
                                    "bnwiki": g("bnwiki"), "enwiki": g("enwiki")}
    return out


def units(start, log):
    """P131 ancestors: qid -> {bn, en, parents}."""
    got, todo = {}, set(start)
    for _ in range(10):
        todo -= set(got)
        if not todo:
            break
        q = sorted(todo)
        for i in range(0, len(q), 200):
            vals = " ".join("wd:" + x for x in q[i:i + 200])
            for b in sparql(f"""SELECT ?u (SAMPLE(?bn) AS ?bnl) (SAMPLE(?en) AS ?enl)
                (GROUP_CONCAT(DISTINCT STRAFTER(STR(?p), "entity/"); separator="|") AS ?par) WHERE {{ VALUES ?u {{ {vals} }}
                OPTIONAL {{ ?u rdfs:label ?bn FILTER(LANG(?bn) = "bn") }} OPTIONAL {{ ?u rdfs:label ?en FILTER(LANG(?en) = "en") }}
                OPTIONAL {{ ?u wdt:P131 ?p }} }} GROUP BY ?u"""):
                u = qid(b["u"]["value"])
                got[u] = {"bn": nfc(b.get("bnl", {}).get("value")), "en": nfc(b.get("enl", {}).get("value")),
                          "parents": sorted(x for x in b.get("par", {}).get("value", "").split("|") if x)}
        todo = {p for u in got.values() for p in u["parents"] if p != "Q902"} - set(got)
    return got


def classes(cls, log):
    """class qid -> {en, bn, roots}"""
    out = {}
    q = sorted(cls)
    roots = " ".join("wd:" + r for r in ALL_ROOTS)
    for i in range(0, len(q), 100):
        vals = " ".join("wd:" + x for x in q[i:i + 100])
        print(f"  classes {i + len(q[i:i + 100])}/{len(q)}", flush=True)
        for b in sparql(f"""SELECT ?c (SAMPLE(?en) AS ?enl) (SAMPLE(?bn) AS ?bnl)
            (GROUP_CONCAT(DISTINCT STRAFTER(STR(?r), "entity/"); separator="|") AS ?roots) WHERE {{ VALUES ?c {{ {vals} }}
            OPTIONAL {{ ?c wdt:P279* ?r . VALUES ?r {{ {roots} }} }}
            OPTIONAL {{ ?c rdfs:label ?en FILTER(LANG(?en) = "en") }} OPTIONAL {{ ?c rdfs:label ?bn FILTER(LANG(?bn) = "bn") }}
            }} GROUP BY ?c"""):
            out[qid(b["c"]["value"])] = {"en": nfc(b.get("enl", {}).get("value")), "bn": nfc(b.get("bnl", {}).get("value")),
                                         "roots": sorted(x for x in b.get("roots", {}).get("value", "").split("|") if x)}
    return out


# --- classification ------------------------------------------------------------------------------------
def classify(p31, cls):
    """-> (status, category_key, proposed, deciding class label). status: place | admin | unclassified"""
    hit = {}
    for c in p31:
        for r in cls.get(c, {}).get("roots", []):
            hit.setdefault(r, c)
    lab = lambda c: cls.get(c, {}).get("en") or c
    for r in ADMIN_HARD:
        if r in hit:
            return "admin", "", None, lab(hit[r])
    for c in p31:
        if TEA_LABEL.search(cls.get(c, {}).get("en", "")):
            return "place", "tourism.tea_garden", None, lab(c)
    for r, _, cat, prop in ROOTS:
        if r in hit:
            return "place", cat, prop, lab(hit[r])
    for r in ADMIN_SOFT:
        if r in hit:
            return "admin", "", None, lab(hit[r])
    for r, _, cat, prop in GENERIC:
        if r in hit:
            return "place", cat, prop, lab(hit[r])
    return "unclassified", "", None, ", ".join(lab(c) for c in p31) or "(no P31)"


def chain(q, item, unit):
    out, seen, cur = [], set(), (item["p131"] or [None])[0]
    while cur and cur not in seen and len(out) < 8:
        seen.add(cur)
        u = unit.get(cur)
        if cur == "Q902":
            out.append("Bangladesh")
            break
        if not u:
            out.append(cur)
            break
        out.append(u["en"] or u["bn"] or cur)
        cur = (u["parents"] or [None])[0]
    return out


def reaches(start, target, unit):
    seen, stack = set(), list(start)
    while stack:
        x = stack.pop()
        if x == target:
            return True
        if x in seen:
            continue
        seen.add(x)
        stack.extend(unit.get(x, {}).get("parents", []))
    return False


# --- main ----------------------------------------------------------------------------------------------
def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def build(raw, geo, cw, key, out, division, log):
    st = collections.Counter()
    admin_by_class, unclassified, proposed = collections.Counter(), collections.Counter(), collections.Counter()
    rows = []
    cls, unit = raw["classes"], raw["units"]
    for q in sorted(raw["items"], key=lambda s: int(s[1:])):
        it = raw["items"][q]
        st["candidates"] += 1
        status, cat, prop, why = classify(it["p31"], cls)
        pts = sorted(tuple(p) for p in it["coords"])
        loc = None
        for p in pts:
            ins, dn, un, note = locate(geo, cw, p[0], p[1])
            if ins:
                loc = (p, dn, un, note)
                break
        if status == "admin":
            if loc:
                st["admin_excluded"] += 1
                admin_by_class[why] += 1
            else:
                st["admin_outside"] += 1
            continue
        if not loc:
            st["dropped_outside"] += 1
            continue
        if status == "unclassified":
            st["unclassified"] += 1
            unclassified[why] += 1
            continue
        if not (it["bn"] or it["en"]):
            st["no_label"] += 1
            continue
        (lon, lat), dn, un, note = loc
        notes = [note] if note else []
        if not dn:
            st["no_district"] += 1
        if prop:
            proposed[(prop, why)] += 1
            notes.append(f"Wikidata class '{why}' has no sub-key; top-level key used (proposed {prop})")
        if len(pts) > 1:
            notes.append(f"{len(pts)} coordinates on Wikidata; the first inside the division is used")
        extra = {"wikidata_classes": [{"qid": c, "en": cls.get(c, {}).get("en", ""), "bn": cls.get(c, {}).get("bn", "")}
                                      for c in it["p31"]]}
        if it["inception"]:
            extra["inception"] = it["inception"][0] if len(it["inception"]) == 1 else it["inception"]
        if it["bnwiki"]:
            extra["wikipedia_bn"] = it["bnwiki"]
        if it["enwiki"]:
            extra["wikipedia_en"] = it["enwiki"]
        if it["p131"]:
            extra["p131"] = it["p131"]
            extra["p131_chain"] = chain(q, it, unit)
        if len(it["web"]) > 1:
            extra["websites"] = it["web"]
        if it["phone"]:
            extra["wikidata_phone"] = it["phone"]
        extra["found_by"] = [k for k, f in (("bbox", "box"), ("p131_chain", "via_p131")) if it.get(f)]
        rows.append({"source_key": key, "source_id": f"wikidata:{q}", "name_bn": it["bn"], "name_en": it["en"],
                     "category_key": cat, "lat": f"{lat:.6f}".rstrip("0").rstrip("."),
                     "lon": f"{lon:.6f}".rstrip("0").rstrip("."), "address": "", "district_en": dn, "upazila_en": un,
                     "phone": "", "website": it["web"][0] if it["web"] else "", "email": "", "opening_hours": "",
                     "operator": "", "ownership": "", "extra_json": json.dumps(extra, ensure_ascii=False, separators=(",", ":")),
                     "source_url": f"https://www.wikidata.org/wiki/{q}", "notes": "; ".join(notes)})
        st["kept"] += 1
        st["in_p131_chain"] += 1 if it["p131_div"] else 0
    # write places (split when large; importer reads places_<n>.csv)
    for f in os.listdir(out):
        if re.fullmatch(r"places(_\d+)?\.csv", f):
            os.remove(os.path.join(out, f))
    files = []

    def write(name, part):
        p = os.path.join(out, name)
        with open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, PLACE_COLS)
            w.writeheader()
            w.writerows(part)
        files.append(name)

    buf = io.StringIO()
    csv.DictWriter(buf, PLACE_COLS).writerows(rows)
    if len(buf.getvalue().encode()) < 19_000_000:
        write("places.csv", rows)
    else:
        n = 1 + len(buf.getvalue().encode()) // 15_000_000
        size = -(-len(rows) // n)
        for i in range(n):
            write(f"places_{i + 1}.csv", rows[i * size:(i + 1) * size])
    by_top = collections.Counter(r["category_key"].split(".")[0] for r in rows)
    by_cat = collections.Counter(r["category_key"] for r in rows)
    return st, by_top, by_cat, admin_by_class, unclassified, proposed, files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--division", default="rajshahi", choices=sorted(DIVS))
    ap.add_argument("--out")
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    code, bfolder, labels, div_bn = DIVS[a.division]
    folder = f"wikidata_{code}_2026"
    key = folder.upper()
    out = a.out or (HERE if a.division == "rajshahi" else os.path.join(SOURCES, folder))
    rawp = os.path.join(out, "raw", f"wikidata_{a.division}.json")
    bdir = os.path.join(SOURCES, bfolder)
    by, cw = load_geo(bdir)
    geo = dict(by)
    log = []
    accessed = TODAY
    if a.offline:
        raw = json.load(open(rawp, encoding="utf-8"))
        accessed = raw["accessed"]
    else:
        if not allowed(WDQS) and not WDQS_EXCEPTION:
            print(f"STOP: https://query.wikidata.org/robots.txt disallows /sparql for {UA!r}. Nothing written.")
            sys.exit(2)
        try:
            div_q = resolve_division(labels, geo)
            print(f"{a.division}: division item {div_q}", flush=True)
            found = discover(div_q, geo, log)
            print(f"  {len(found)} candidate items", flush=True)
            det = details(set(found), log)
            unit = units({p for d in det.values() for p in d["p131"]}, log)
            cls = classes({c for d in det.values() for c in d["p31"]}, log)
        except Refused as e:
            print(f"STOP: refused by the host: {e}. Nothing written.")
            sys.exit(3)
        os.makedirs(os.path.join(out, "raw"), exist_ok=True)
        # filtered raw: full records for items with a point inside the division; for the others only what the
        # counts need (classes, points), no labels or links
        items = {}
        for q, f in found.items():
            d = det.get(q)
            if not d:
                log.append(f"{q}: no details returned")
                continue
            pts = [list(p) for p in sorted(f["coords"])]
            rec = {**d, "coords": pts, "box": f["box"], "via_p131": f["via_p131"], "p131_div": reaches(d["p131"], div_q, unit)}
            if not any(any(g.contains(*p) for g in geo["division"]) for p in pts):
                rec.update(bn="", en="", web=[], phone=[], inception=[], bnwiki="", enwiki="", p131=[])
            items[q] = rec
        need_units = {p for it in items.values() for p in it["p131"]}
        keep_units = {}
        for u in need_units:      # ancestors along the first-parent chain only
            cur, seen = u, set()
            while cur and cur in unit and cur not in seen:
                seen.add(cur)
                keep_units[cur] = unit[cur]
                cur = (unit[cur]["parents"] or [None])[0]
        raw = {"division": a.division, "division_qid": div_q, "accessed": accessed, "log": log,
               "items": items, "units": keep_units,
               "classes": {c: cls[c] for c in {c for it in items.values() for c in it["p31"]} if c in cls}}
    st, by_top, by_cat, admin_by_class, unclassified, proposed, files = build(raw, geo, cw, key, out, a.division, raw.get("log", []))
    # raw only if small
    rawbytes = json.dumps(raw, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    raw_files = []
    if len(rawbytes) < 19_000_000:
        if not a.offline:
            open(rawp, "wb").write(rawbytes)
        raw_files.append(f"raw/wikidata_{a.division}.json")
    elif os.path.exists(rawp) and not a.offline:
        os.remove(rawp)
    manifest = {
        "key": key, "division": a.division, "kind": "wikidata",
        "name": f"Wikidata — items with coordinates in {a.division.title()} Division (places, not administrative units)",
        "organization": "Wikidata contributors (Wikimedia Foundation)",
        "source_type": "encyclopedia", "trust_level": 2,
        "urls": ["https://query.wikidata.org/", "https://www.wikidata.org/"],
        "accessed": accessed, "publication_date": None,
        "license": "CC0-1.0", "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "attribution": "Wikidata (CC0 1.0). Wikipedia article links are references only; no article text is copied.",
        "files": {f: sha(os.path.join(out, f)) for f in files + raw_files},
        "notes": (f"Division item {raw['division_qid']}. Candidates: P625 inside each district bounding box (wikibase:box) "
                  "plus P131-chain members of the division item; kept when a point lies inside the HDX COD-AB division "
                  f"polygon ({bfolder}/boundaries.geojson). District/upazila by point-in-polygon, seed names via "
                  f"{bfolder}/crosswalk.csv. Administrative units and settlements excluded. Community-edited data: every "
                  "row is unverified. P1329 phone numbers kept in extra_json.wikidata_phone only (not published by the "
                  "institution itself)."),
    }
    json.dump(manifest, open(os.path.join(out, "SOURCE.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    rep = [f"# {key} — Wikidata places, {a.division.title()} Division", "",
           f"Accessed {accessed}. Licence CC0-1.0 (Wikidata). Evidence: encyclopedia, trust 2 — all rows unverified.", "",
           "| Count | n |", "|---|---|"]
    for k in ("candidates", "kept", "admin_excluded", "admin_outside", "dropped_outside", "unclassified", "no_label",
              "no_district", "in_p131_chain"):
        rep.append(f"| {k} | {st.get(k, 0)} |")
    rep += ["", "## Kept, by top-level category", "", "| category | n |", "|---|---|"]
    rep += [f"| {k} | {v} |" for k, v in sorted(by_top.items())]
    rep += ["", "## Kept, by category key", "", "| category_key | n |", "|---|---|"]
    rep += [f"| {k} | {v} |" for k, v in sorted(by_cat.items())]
    rep += ["", "## Proposed new subcategories (rows placed under the top-level key)", "", "| proposed | Wikidata class | n |", "|---|---|---|"]
    rep += [f"| {p} | {c} | {n} |" for (p, c), n in sorted(proposed.items())]
    rep += ["", "## Administrative units excluded (inside the division)", "", "| class | n |", "|---|---|"]
    rep += [f"| {c} | {n} |" for c, n in admin_by_class.most_common()]
    rep += ["", "## Unclassified (left out), top classes", "", "| classes | n |", "|---|---|"]
    rep += [f"| {c} | {n} |" for c, n in unclassified.most_common(40)]
    if raw.get("log"):
        rep += ["", "## Query log", ""] + [f"- {l}" for l in raw["log"]]
    try:
        open(os.path.join(out, "REPORT.md"), "w", encoding="utf-8").write("\n".join(rep) + "\n")
    except OSError as e:
        print("could not write REPORT.md:", e)
    print("\n".join(rep))


if __name__ == "__main__":
    main()
