#!/usr/bin/env python3
"""OpenStreetMap points of interest for one Bangladesh division, from the Geofabrik Bangladesh extract.

    python3 fetch.py                               # Rajshahi Division -> this folder (osm_rajshahi_division)
    python3 fetch.py --division rangpur            # -> ../osm_rangpur_division
    python3 fetch.py --division all                # all 8 divisions, one folder each
    python3 fetch.py --cache /tmp/osm              # where the .pbf and the parsed candidates are kept
    python3 fetch.py --offline                     # never download; use the cached .pbf / candidates
    python3 fetch.py --refresh                     # download the extract again and re-parse it
    python3 fetch.py --division khulna --manifest  # only refresh SOURCE.json checksums

Data access: ONE download of https://download.geofabrik.de/asia/bangladesh-latest.osm.pbf (about 360 MB,
checked against Geofabrik's .md5), parsed locally. Nothing is fetched per division. The .pbf and the parsed
national candidate list (candidates.jsonl.gz) live in --cache (default $OSM_CACHE or <tmp>/elaka360_osm) and are
never committed; every division folder is rebuilt from them.

Dependencies: Python 3.9+, `requests`, and **pyosmium** (`pip install osmium`, tested with 4.3.2 / libosmium
2.23.1). pyosmium is an exception to the stdlib + requests rule of COLLECTION_FORMAT.md: it is only needed to read
the .pbf, and only when candidates.jsonl.gz is not cached yet.

Per division the script writes: places.csv (split into places.csv, places_2.csv, ... so each file stays < 20 MB),
stats.json, SOURCE.json (files + sha256, OSM data timestamp). REPORT.md is written by hand from stats.json.

District / upazila: point-in-polygon against the HDX COD-AB polygons already collected for the division
(../hdx_cod_ab_bgd/ for Rajshahi, ../hdx_cod_ab_bgd_<division>/ otherwise), mapped to the seed's English names
through that folder's crosswalk.csv. Points outside the division polygon are dropped and counted.

Data © OpenStreetMap contributors, ODbL-1.0 (https://opendatacommons.org/licenses/odbl/1-0/).
"""
import argparse, csv, gzip, hashlib, json, math, os, re, sys, tempfile, time, unicodedata
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.dirname(HERE)
UA = "Elaka360-data-pipeline (research; contact via repository)"
PBF_URL = "https://download.geofabrik.de/asia/bangladesh-latest.osm.pbf"
CANDIDATES_VERSION = 1   # bump when the candidate selection below changes (forces a re-parse)

# division -> (code used in keys, HDX boundary folder)
DIVISIONS = {
    "rajshahi": ("raj", "hdx_cod_ab_bgd"),
    "rangpur": ("rang", "hdx_cod_ab_bgd_rangpur"),
    "dhaka": ("dhk", "hdx_cod_ab_bgd_dhaka"),
    "chattogram": ("ctg", "hdx_cod_ab_bgd_chattogram"),
    "khulna": ("khl", "hdx_cod_ab_bgd_khulna"),
    "barishal": ("bar", "hdx_cod_ab_bgd_barishal"),
    "sylhet": ("syl", "hdx_cod_ab_bgd_sylhet"),
    "mymensingh": ("mym", "hdx_cod_ab_bgd_mymensingh"),
}

COLS = ["source_key", "source_id", "name_bn", "name_en", "category_key", "lat", "lon", "address", "district_en",
        "upazila_en", "phone", "website", "email", "opening_hours", "operator", "ownership", "extra_json",
        "source_url", "notes"]
MAX_FILE_BYTES = 19_500_000


def folder_for(division):
    return os.path.join(SOURCES, f"osm_{division}_division")


def key_for(division):
    return f"OSM_{DIVISIONS[division][0].upper()}_2026"


# ------------------------------------------------------------------ download + parse (national, cached)

def download_pbf(cache, refresh=False, offline=False):
    import requests
    os.makedirs(cache, exist_ok=True)
    path = os.path.join(cache, "bangladesh-latest.osm.pbf")
    if os.path.isfile(path) and not refresh:
        return path
    if offline:
        raise SystemExit(f"--offline: {path} is missing")
    s = requests.Session()
    s.headers["User-Agent"] = UA
    md5_expected = s.get(PBF_URL + ".md5", timeout=60).text.split()[0]
    time.sleep(1)
    print(f"downloading {PBF_URL} …", file=sys.stderr)
    tmp = path + ".part"
    h = hashlib.md5()
    with s.get(PBF_URL, stream=True, timeout=(30, 600)) as r:
        r.raise_for_status()
        final_url = r.url
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
                h.update(chunk)
    if h.hexdigest() != md5_expected:
        os.remove(tmp)
        raise SystemExit(f"md5 mismatch for {final_url}: {h.hexdigest()} != {md5_expected}")
    os.replace(tmp, path)
    with open(os.path.join(cache, "download.json"), "w") as f:
        json.dump({"url": PBF_URL, "final_url": final_url, "md5": md5_expected,
                   "downloaded": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "bytes": os.path.getsize(path)}, f, indent=1)
    return path


POI_KEYS = ("amenity", "shop", "office", "healthcare", "tourism", "historic", "leisure", "craft", "emergency")
MAN_MADE_OK = {"water_tower", "water_works", "lighthouse", "tower", "works", "observatory", "telescope",
               "wastewater_plant", "pumping_station", "bridge", "windmill"}
BUILDING_OK = {"school", "college", "university", "kindergarten", "hospital", "mosque", "temple", "church",
               "shrine", "chapel", "cathedral", "government", "public", "civic", "train_station", "transportation",
               "commercial", "retail", "office", "hotel", "warehouse", "industrial", "religious", "pagoda"}
COLD = re.compile(r"cold ?storage|হিমাগার", re.I)


def is_candidate(t):
    """Broad pre-selection; the real decision (classify) is made per division so it can change without a re-parse."""
    if any(k in t for k in POI_KEYS):
        return True
    if t.get("railway") in ("station", "halt", "tram_stop") or t.get("public_transport") == "station":
        return True
    if t.get("highway") == "bus_stop" or t.get("aeroway") in ("aerodrome", "heliport"):
        return True
    if t.get("man_made") in MAN_MADE_OK and "name" in t:
        return True
    if t.get("landuse") == "cemetery" and "name" in t:
        return True
    if t.get("building") in BUILDING_OK and "name" in t:
        return True
    return bool("name" in t and COLD.search(t.get("name", "")))


def ring_centroid(coords):
    """Signed area and centroid of a closed ring [(lon, lat), ...] (planar, fine at this scale)."""
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(coords, coords[1:]):
        c = x1 * y2 - x2 * y1
        a += c
        cx += (x1 + x2) * c
        cy += (y1 + y2) * c
    if abs(a) < 1e-14:
        n = len(coords) - 1 or 1
        return 0.0, sum(p[0] for p in coords[:n]) / n, sum(p[1] for p in coords[:n]) / n
    return a / 2, cx / (3 * a), cy / (3 * a)


def bbox_radius_m(coords):
    xs, ys = [p[0] for p in coords], [p[1] for p in coords]
    return haversine((min(ys), min(xs)), (max(ys), max(xs))) / 2


def parse_pbf(pbf, out_path):
    """Read the .pbf once and write every candidate (node, way centroid, multipolygon centroid) as JSON lines."""
    import osmium
    t0 = time.time()
    keys = (*POI_KEYS, "railway", "public_transport", "highway", "aeroway", "man_made", "landuse", "building", "name")
    fp = (osmium.FileProcessor(pbf)
          .with_locations("flex_mem")
          .with_areas(osmium.filter.KeyFilter(*keys))
          .with_filter(osmium.filter.KeyFilter(*keys)))   # untagged / irrelevant objects never reach Python
    header = fp.header
    osm_ts = header.get("osmosis_replication_timestamp") or ""
    seq = header.get("osmosis_replication_sequence_number") or ""
    counts = Counter()
    seen = set()
    tmp = out_path + ".part"
    with gzip.open(tmp, "wt", encoding="utf-8") as out:
        out.write(json.dumps({"_meta": {"version": CANDIDATES_VERSION, "osm_timestamp": osm_ts, "sequence": seq,
                                        "pbf": os.path.basename(pbf)}}) + "\n")
        for obj in fp:
            if obj.is_area():
                if obj.from_way():
                    continue   # closed ways are handled as ways below
                t = dict(obj.tags)
                if not is_candidate(t):
                    continue
                total_a = sx = sy = 0.0
                pts = []
                for outer in obj.outer_rings():
                    ring = [(n.lon, n.lat) for n in outer]
                    a, x, y = ring_centroid(ring)
                    total_a += abs(a); sx += abs(a) * x; sy += abs(a) * y
                    pts += ring
                    for inner in obj.inner_rings(outer):
                        iring = [(n.lon, n.lat) for n in inner]
                        a, x, y = ring_centroid(iring)
                        total_a -= abs(a); sx -= abs(a) * x; sy -= abs(a) * y
                if not pts:
                    counts["relation without geometry"] += 1
                    continue
                if total_a > 1e-14:
                    lon, lat = sx / total_a, sy / total_a
                else:
                    lon, lat = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
                rid = obj.orig_id()
                seen.add(("relation", rid))
                counts["relation"] += 1
                out.write(json.dumps({"type": "relation", "id": rid, "lat": round(lat, 6), "lon": round(lon, 6),
                                      "r": round(bbox_radius_m(pts)), "tags": t}, ensure_ascii=False) + "\n")
            elif obj.is_node():
                if not obj.tags:
                    continue
                t = dict(obj.tags)
                if not is_candidate(t) or not obj.location.valid():
                    continue
                counts["node"] += 1
                out.write(json.dumps({"type": "node", "id": obj.id, "lat": round(obj.location.lat, 6),
                                      "lon": round(obj.location.lon, 6), "tags": t}, ensure_ascii=False) + "\n")
            elif obj.is_way():
                if not obj.tags:
                    continue
                t = dict(obj.tags)
                if not is_candidate(t):
                    continue
                try:
                    ring = [(n.lon, n.lat) for n in obj.nodes if n.location.valid()]
                except osmium.InvalidLocationError:
                    ring = []
                if not ring:
                    counts["way without node locations"] += 1
                    continue
                if len(ring) >= 4 and ring[0] == ring[-1]:
                    _, lon, lat = ring_centroid(ring)
                else:
                    lon, lat = sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)
                counts["way"] += 1
                out.write(json.dumps({"type": "way", "id": obj.id, "lat": round(lat, 6), "lon": round(lon, 6),
                                      "r": round(bbox_radius_m(ring)), "closed": ring[0] == ring[-1],
                                      "tags": t}, ensure_ascii=False) + "\n")
            elif obj.is_relation():
                t = dict(obj.tags)
                if is_candidate(t) and t.get("type") not in ("multipolygon", "boundary"):
                    counts[f"relation type={t.get('type', '')} (no point geometry, skipped)"] += 1
    os.replace(tmp, out_path)
    print(f"parsed {pbf} in {time.time() - t0:.0f}s: {dict(counts)}; osm timestamp {osm_ts}", file=sys.stderr)
    with open(os.path.join(os.path.dirname(out_path), "parse_stats.json"), "w") as f:
        json.dump({"osm_timestamp": osm_ts, "sequence": seq, "counts": counts}, f, indent=1)


def load_candidates(args):
    cpath = os.path.join(args.cache, "candidates.jsonl.gz")
    meta = None
    if os.path.isfile(cpath) and not args.refresh:
        with gzip.open(cpath, "rt", encoding="utf-8") as f:
            meta = json.loads(f.readline()).get("_meta", {})
        if meta.get("version") != CANDIDATES_VERSION:
            meta = None
    if meta is None:
        pbf = download_pbf(args.cache, refresh=args.refresh, offline=args.offline)
        parse_pbf(pbf, cpath)
    els, meta = [], None
    with gzip.open(cpath, "rt", encoding="utf-8") as f:
        for line in f:
            o = json.loads(line)
            if "_meta" in o:
                meta = o["_meta"]
            else:
                els.append(o)
    dl = os.path.join(args.cache, "download.json")
    if os.path.isfile(dl):
        meta["download"] = json.load(open(dl))
    return els, meta


# ------------------------------------------------------------------ boundaries (HDX COD-AB, already collected)

class Polygon:
    STRIP = 0.01  # degrees of latitude per index strip

    def __init__(self, rings):
        self.edges = defaultdict(list)
        self.bbox = [180, 90, -180, -90]
        for ring in rings:
            for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
                if y1 == y2:
                    continue
                lo, hi = min(y1, y2), max(y1, y2)
                for k in range(int(math.floor(lo / self.STRIP)), int(math.floor(hi / self.STRIP)) + 1):
                    self.edges[k].append((x1, y1, x2, y2))
            for x, y in ring:
                self.bbox = [min(self.bbox[0], x), min(self.bbox[1], y), max(self.bbox[2], x), max(self.bbox[3], y)]

    def contains(self, x, y):
        b = self.bbox
        if not (b[0] <= x <= b[2] and b[1] <= y <= b[3]):
            return False
        inside = False
        for x1, y1, x2, y2 in self.edges.get(int(math.floor(y / self.STRIP)), ()):
            if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                inside = not inside
        return inside


def geom_rings(g):
    polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    rings = []
    for p in polys:
        for ring in p:
            r = [tuple(c[:2]) for c in ring]
            if r[0] != r[-1]:
                r.append(r[0])
            rings.append(r)
    return rings   # even-odd ray casting over all rings handles holes and multipart polygons


def load_boundaries(division):
    folder = os.path.join(SOURCES, DIVISIONS[division][1])
    gj = json.load(open(os.path.join(folder, "boundaries.geojson"), encoding="utf-8"))
    cw = {}
    with open(os.path.join(folder, "crosswalk.csv"), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r["our_level"] in ("district", "upazila", "city_corporation") and r["source_code"] and r["our_id"]:
                cw[r["source_code"]] = r
    src_key = json.load(open(os.path.join(folder, "SOURCE.json"), encoding="utf-8"))["key"]
    b = {"division": None, "district": [], "upazila": [], "city_corporation": [], "folder": os.path.basename(folder),
         "source_key": src_key, "unmapped": []}
    for ft in gj["features"]:
        p = ft["properties"]
        poly = Polygon(geom_rings(ft["geometry"]))
        if p["level"] == "division":
            b["division"] = poly
            continue
        if p["level"] not in ("district", "upazila", "city_corporation"):
            continue
        m = cw.get(p["code"])
        if not m:
            b["unmapped"].append(p["code"])
        b[p["level"]].append({"code": p["code"], "poly": poly, "hdx_name": p["name_en"],
                              "name": m["our_name_en"] if m else "", "seed_id": m["our_id"] if m else "",
                              "district_code": p["code"][:6]})
    names = {d["code"]: d["name"] for d in b["district"]}
    for u in b["upazila"] + b["city_corporation"]:
        u["district"] = names.get(u["district_code"], "")
    return b


def locate(b, lon, lat):
    """-> (inside_division, district_en, upazila_en, city_corporation or None, note)"""
    if not b["division"].contains(lon, lat):
        return False, "", "", None, ""
    up = next((u for u in b["upazila"] if u["poly"].contains(lon, lat)), None)
    cc = next((c for c in b["city_corporation"] if c["poly"].contains(lon, lat)), None)
    if up:
        return True, up["district"], up["name"], cc, ""
    if cc:
        return True, cc["district"], "", cc, ""
    d = next((d for d in b["district"] if d["poly"].contains(lon, lat)), None)
    if d:
        return True, d["name"], "", None, "not inside any HDX upazila polygon (boundary sliver)"
    return True, "", "", None, "inside the division polygon but no HDX district polygon (boundary sliver)"


# ------------------------------------------------------------------ normalisation

BN = re.compile(r"[ঀ-৿]")
LATIN = re.compile(r"[A-Za-z]")


def nfc(s):
    return unicodedata.normalize("NFC", (s or "").strip())


def has(pattern, *texts):
    return any(re.search(pattern, t or "", re.I) for t in texts)


MADRASA = r"madras|madrash|মাদ্রাসা|মাদরাসা|মাদ্রাসাহ|দাখিল|আলিম|ফাজিল|কামিল|হাফেজিয়া|হাফিজিয়া|কওমি|dakhil|alim\b|fazil|kamil|hafezia|hafizia|qawmi|quami"
PRIMARY = r"primary|প্রাথমিক|\bG\.?P\.?S\b|\bR\.?N\.?G\.?P\.?S|ebtedayee|ebtedayi|ইবতেদায়ী"
SECONDARY = r"high school|secondary|উচ্চ বিদ্যালয়|মাধ্যমিক|বালিকা বিদ্যালয়|girls'? school|\bhigh\b|উচ্চ বালিকা|\bschool and college|স্কুল এন্ড কলেজ|স্কুল ও কলেজ|স্কুল অ্যান্ড কলেজ"
POLY = r"poly ?tec?h?nic|পলিটেকনিক"
TECH = r"technical|vocational|কারিগরি|টেকনিক্যাল|\bTTC\b|textile|nursing|নার্সিং|\bIHT\b|\bMATS\b"
MEDCOL = r"medical college|মেডিকেল কলেজ|dental college|ডেন্টাল কলেজ"
TRAINING = r"training|প্রশিক্ষণ|ট্রেনিং|academy for|\bPTI\b|\bRDA\b|coaching|কোচিং"
GOV_HINT = r"parishad|porishad|পরিষদ|অধিদপ্তর|অধিদফতর|কার্যালয়|department|directorate|\boffice\b|অফিস|পৌরসভা|pourashava|paurashava"
RESIDENCE = r"\b(?:house|home|residence|bari|bari\b|basha|basa|villa|cottage|bungalow)\b|বাড়ি|বাড়ী|বাসা|বাসভবন|ভিলা|কুটির|মঞ্জিল|manzil|monjil"
PUBLIC_HOUSE = r"circuit house|rest ?house|guest ?house|ware ?house|dak bungalow|club ?house|power ?house|custom ?house|court ?house|town ?house|সার্কিট হাউস|রেস্ট হাউস|ডাক বাংলো"
PRIVATE_GRAVE = r"family (?:grave|cemetery)|পারিবারিক কবর|পারিবারিক গোরস্থান|পারিবারিক শ্মশান"

SKIP_AMENITY = {
    "bench", "waste_basket", "parking_space", "bicycle_parking", "motorcycle_parking", "vending_machine", "post_box",
    "telephone", "waste_disposal", "recycling", "clock", "hunting_stand", "parking_entrance", "grit_bin", "fountain",
    "shower", "watering_place", "loading_dock", "letter_box", "dressing_room", "give_box", "lounger", "bbq",
    "photo_booth", "kneipp_water_cure", "smoking_area", "waste_transfer_station", "sanitary_dump_station", "trolley_bay",
    "dormitory", "hostel", "house", "residential", "yes", "no", "disused", "abandoned", "construction",
}
RESIDENTIAL_BUILDINGS = {"house", "residential", "apartments", "detached", "hut", "bungalow", "semidetached_house",
                         "terrace", "dormitory", "farm", "cabin", "static_caravan", "houseboat"}


def classify(t):
    """Return (category_key, note) or (None, reason) to drop. A top-level key means: no sub-category fits."""
    # multi-valued main tags ("restaurant;atm"): the first value decides
    t = {k: (v.split(";")[0].strip() if k in PRIMARY_TAGS and ";" in v else v) for k, v in t.items()}
    a, sh, off = t.get("amenity", ""), t.get("shop", ""), t.get("office", "")
    hc, tour, hist, lei = t.get("healthcare", ""), t.get("tourism", ""), t.get("historic", ""), t.get("leisure", "")
    craft, emer, bld, mm = t.get("craft", ""), t.get("emergency", ""), t.get("building", ""), t.get("man_made", "")
    names = (t.get("name", ""), t.get("name:en", ""), t.get("name:bn", ""), t.get("official_name", ""))
    n = lambda p: has(p, *names)
    strong = a or sh or off or hc or tour or hist or lei or craft
    if t.get("disused") == "yes" or t.get("abandoned") == "yes" or any(k.startswith(("disused:", "abandoned:", "was:"))
                                                                       for k in t) and not strong:
        return None, "disused / abandoned"

    # --- private residences and private-person features
    if bld in RESIDENTIAL_BUILDINGS and not strong:
        return None, "private residence (building only)"
    other_poi = any(t.get(k) for k in ("railway", "public_transport", "highway", "aeroway", "emergency", "man_made",
                                           "landuse"))
    weak = (bld and not strong and not other_poi and bld not in BUILDING_OK) or off == "yes" or lei == "garden"
    if weak and not (a or sh or hc or tour or hist) and n(RESIDENCE) and not n(PUBLIC_HOUSE):
        return None, "private residence / private garden (name)"
    if t.get("access") in ("private", "no") and (lei or a in ("toilets", "drinking_water", "water_point", "parking",
                                                              "swimming_pool")):
        return None, "access=private"

    # a bare building (no amenity/office/…) named like one block of a campus is not a separate place
    if bld and not strong and \
            n(r"\bbuilding\b|\bbhaban\b|\bbhavan\b|\bblock\b|\bannex|\bwing\b|ভবন|\bhall\b|\bhostel\b|ছাত্রাবাস|ছাত্রী নিবাস|canteen|quarter"):
        return None, "campus building"
    if a in SKIP_AMENITY:
        return None, f"amenity={a}"

    # --- education
    if a in ("school", "college", "university", "kindergarten", "prep_school") or bld in ("school", "college", "university", "kindergarten") \
            or off == "educational_institution" or a == "training":
        if n(MADRASA) or t.get("school:type") in ("madrasa", "islamic") or t.get("religion") == "muslim" and a == "school":
            return "education.madrasa", ""
        if n(MEDCOL):
            return "education.medical_college", ""
        if n(POLY):
            return "education.polytechnic", ""
        if (a == "university" or bld == "university" or n(r"university|বিশ্ববিদ্যালয়")) \
                and not n(r"university college|বিশ্ববিদ্যালয় কলেজ"):
            return "education.university", ""
        if n(TECH):
            return "education.technical", ""
        if a == "training" or n(TRAINING):
            return "education.training_center", ""
        if a == "kindergarten" or bld == "kindergarten" or n(r"kindergarten|\bK\.?G\b|কিন্ডারগার্টেন|কিন্ডার গার্টেন|pre-?school|শিশু নিকেতন|শিশু কানন"):
            return "education", "kindergarten"
        if n(PRIMARY) or t.get("isced:level", "").strip() in ("1", "0;1", "1;0"):
            return "education.primary_school", ""
        if a == "college" or bld == "college" or n(r"college|কলেজ"):
            # "School & College" offers secondary + higher secondary; keep as college only if no school word
            if n(r"school|স্কুল|বিদ্যালয়"):
                return "education.secondary_school", "school and college"
            return "education.college", ""
        if n(SECONDARY) or t.get("isced:level", "") in ("2", "3", "2;3"):
            return "education.secondary_school", ""
        return "education", "school level not stated"
    if a == "library":
        return "education", "library"
    if a == "research_institute" or off == "research":
        return "education", "research institute"
    if a == "internet_cafe":
        return "business.it_service", "internet cafe"
    if a in ("mobile_money_agent",):
        return "finance.mobile_banking_agent", ""
    if a in ("canteen",):
        return "business.restaurant", "canteen"
    if a == "post_depot":
        return "government.post_office", "post depot"
    if a == "public_bath":
        return "emergency.water_sanitation", "public bath"
    if a == "animal_breeding":
        return "agriculture.farm", "animal breeding"
    if a == "historic_place":
        return "tourism.historical", ""
    if a == "boat_rental":
        return "transport", "boat rental"
    if a == "dojo":
        return "other", "sports venue (amenity=dojo)"
    if a in ("driving_school", "language_school", "music_school", "dancing_school", "tutoring", "childcare") \
            or off == "tutoring":
        return "business.education_service", a or off

    # --- health
    if a in ("hospital", "clinic", "doctors", "dentist") or hc or bld == "hospital":
        if a in ("doctors", "dentist") or hc in ("doctor", "dentist"):
            return "business.health_service", "doctor's / dentist's practice"
        if hc == "pharmacy":
            return "health.pharmacy", ""
        if n(r"medical college hospital|মেডিকেল কলেজ হাসপাতাল|মেডিক্যাল কলেজ হাসপাতাল"):
            return "health.medical_college_hospital", ""
        if n(MEDCOL) and a != "hospital" and hc != "hospital":
            return "education.medical_college", "tagged as clinic/healthcare"
        if n(r"health complex|স্বাস্থ্য কমপ্লেক্স|স্বাস্থ্য কমপ্লেক্"):
            return "health.upazila_health_complex", ""
        if n(r"community clinic|কমিউনিটি ক্লিনিক"):
            return "health.community_clinic", ""
        if n(r"city health|নগর স্বাস্থ্য|urban primary health|UPHCP|সিটি স্বাস্থ্য"):
            return "health.city_health_center", ""
        if n(r"diag(?:o)?nos|diagonestic|ডায়াগনস্টিক|ডায়াগনোস্টিক|ডায়গনস্টিক|imaging|pathology|প্যাথলজি") or hc in ("laboratory", "radiology"):
            return "health.diagnostic_center", ""
        if a == "hospital" or hc == "hospital" or bld == "hospital":
            return "health.hospital", ""
        if a == "clinic" or hc in ("clinic", "centre"):
            return "health.clinic", ""
        if hc in ("blood_donation", "blood_bank"):
            return "health", "blood bank"
        if hc in ("alternative", "physiotherapist", "optometrist", "psychotherapist", "rehabilitation", "counselling",
                  "nurse", "midwife", "vaccination_centre", "audiologist", "speech_therapist", "dialysis",
                  "podiatrist", "hospice", "sample_collection"):
            return "business.health_service", hc
        if hc not in ("yes",):
            return "health", f"healthcare={hc}"
        return "health", "healthcare=yes"
    if a == "pharmacy" or sh == "chemist" and n(r"pharm|ফার্মে|ঔষধ|drug|medicine|মেডিসিন"):
        return "health.pharmacy", ""
    if a in ("nursing_home",):
        return "health", "nursing home"
    if a == "veterinary":
        return "agriculture", "veterinary"

    # --- emergency
    if a == "police":
        if n(r"পুলিশ সুপার|superintendent of police|\bSP office|এসপি অফিস|police super"):
            return "government.sp_office", ""
        if n(r"ফাঁড়ি|ফাড়ি|fari\b|faari|phari|outpost|camp|ক্যাম্প|box|বক্স|check ?post|চেকপোস্ট|তদন্ত কেন্দ্র|investigation cent"):
            return "emergency.police_outpost", ""
        if n(r"থানা|thana|police station|model"):
            return "emergency.police_station", ""
        return "emergency", "police (type not stated)"
    if a == "fire_station":
        return "emergency.fire_station", ""
    if a == "ambulance_station" or emer == "ambulance_station":
        return "emergency.ambulance", ""
    if a == "rescue_station" or emer in ("lifeguard", "lifeguard_base", "water_rescue", "mountain_rescue"):
        return "emergency.rescue", ""
    if a == "shelter" or emer == "disaster_shelter":
        if emer == "disaster_shelter" or t.get("shelter_type") in ("disaster_shelter", "cyclone_shelter") or \
                n(r"flood|বন্যা|আশ্রয়কেন্দ্র|আশ্রয় কেন্দ্র|cyclone|ঘূর্ণিঝড়|disaster|দুর্যোগ|মুজিব কিল্লা|killa"):
            return "emergency.disaster_shelter", ""
        return None, "generic shelter"
    if a == "toilets":
        return "emergency.water_sanitation", "public toilet"
    if a in ("drinking_water", "water_point") or mm in ("water_tower", "water_works", "wastewater_plant", "pumping_station"):
        return "emergency.water_sanitation", a or f"man_made={mm}"
    if emer and not a:
        return None, f"emergency={emer}"

    # --- finance
    if a == "bank":
        return "finance.bank", ""
    if a == "atm":
        return "finance.atm", ""
    if a in ("money_transfer", "payment_centre") or n(r"bkash|বিকাশ|nagad|নগদ|rocket agent|mobile banking|এজেন্ট ব্যাংকিং|agent banking"):
        if a in ("money_transfer", "payment_centre") or n(r"agent|এজেন্ট|bkash|বিকাশ|nagad|নগদ"):
            return "finance.mobile_banking_agent", ""
    if a == "bureau_de_change":
        return "finance", "bureau de change"
    if off in ("insurance", "financial", "financial_advisor", "tax_advisor", "accountant") or sh in ("money_lender", "pawnbroker") \
            or a == "microfinance":
        return "finance", off or sh or a

    # --- government
    if a == "post_office":
        return "government.post_office", ""
    if a == "courthouse":
        return "government.court", ""
    if a in ("embassy",) or off == "diplomatic":
        return "government", "embassy / diplomatic"
    if a == "prison":
        return "government", "prison"
    if a == "townhall" or off in ("government", "administrative", "public_service") or bld in ("government", "public", "civic") \
            or a in ("community_centre", "social_centre", "public_building") and n(GOV_HINT):
        if n(r"divisional commissioner|বিভাগীয় কমিশনার"):
            return "government.divisional_commissioner", ""
        if n(r"deputy commissioner|\bDC office|জেলা প্রশাসক|ডিসি অফিস|collectorate|কালেক্টরেট"):
            return "government.dc_office", ""
        if n(r"পুলিশ সুপার|superintendent of police|\bSP office|police super"):
            return "government.sp_office", ""
        if n(r"civil surgeon|সিভিল সার্জন"):
            return "government.civil_surgeon", ""
        if n(r"pass?port|পাসপোর্ট"):
            return "government.passport_office", ""
        if n(r"city corporation|সিটি কর্পোরেশন|সিটি করপোরেশন|নগর ভবন|nagar bhaban"):
            return "government.city_corporation_office", ""
        if n(r"pourashava|paurashava|pourosova|pourashova|paurasava|municipal|পৌরসভা|পৌর ভবন"):
            return "government.pourashava_office", ""
        if n(r"union (?:parishad|porishad|porishod|parisad|porisad|council)|ইউনিয়ন পরিষদ|ইউপি কার্যালয়|\bU\.?P\.? (office|complex|bhaban)|ইউনিয়ন ডিজিটাল"):
            return "government.union_parishad", ""
        if n(r"\bUNO\b|nirbahi|upazila (?:parishad|porishad|porishod|parisad)|upazila complex|উপজেলা পরিষদ|উপজেলা নির্বাহী|উপজেলা কমপ্লেক্স"):
            return "government.uno_office", ""
        if n(r"land office|ভূমি অফিস|ভূমি কার্যালয়|AC ?land|তহশিল|tahsil|tohshil|সহকারী কমিশনার \(ভূমি\)|settlement"):
            return "government.land_office", ""
        if n(r"post office|ডাকঘর|পোস্ট অফিস"):
            return "government.post_office", ""
        if n(r"court|আদালত|judge|জজ"):
            return "government.court", ""
        if n(r"agricultur|কৃষি|\bDAE\b|BADC|বিএডিসি|BMDA|বরেন্দ্র বহুমুখী|seed|বীজ|fisher|মৎস্য|livestock|প্রাণিসম্পদ"):
            return "agriculture.agri_office", ""
        if a == "townhall" and n(r"community|কমিউনিটি|town hall|টাউন হল|auditorium|মিলনায়তন"):
            return "other.community_center", "town hall / auditorium"
        if bld in ("public", "civic") and not (a or off):
            return None, "public building without office hint"
        return "government", "office type not stated"
    if off in ("energy_supplier", "water_utility", "gas_utility"):
        return "government", f"utility office ({off})"

    # --- religious
    if a in ("place_of_worship", "monastery") or bld in ("mosque", "temple", "church", "shrine", "chapel", "cathedral",
                                                       "pagoda", "religious") \
            or a in ("grave_yard", "crematorium") or t.get("landuse") == "cemetery":
        rel = t.get("religion", "")
        if n(r"mazar|majar|dargah|darga\b|মাজার|দরগাহ|দরগা\b|shrine|tomb") or bld == "shrine":
            return "religious.mazar", ""
        if a in ("grave_yard", "crematorium") or t.get("landuse") == "cemetery":
            if n(PRIVATE_GRAVE):
                return None, "family graveyard (private)"
            return "religious", "graveyard / cremation ground"
        if n(r"eidgah|idgah|eid gah|ঈদগাহ|ইদগাহ|ঈদগা|ইদগা|\beid\b|ঈদের"):
            return "religious.eidgah", ""
        if n(MADRASA) and not n(r"mosque|masjid|মসজিদ|\bjame\b|জামে|মসজীদ|mosjid"):
            return "education.madrasa", "tagged as place of worship"
        if rel == "muslim" or bld == "mosque" or n(r"mosque|masjid|মসজিদ|\bjame\b|জামে|মসজীদ"):
            return "religious.mosque", ""
        if rel == "hindu" or bld == "temple" or n(r"mandir|mondir|temple|মন্দির|কালী|ashram|আশ্রম|সেবাশ্রম|দেবালয়|পূজা মণ্ডপ|মন্ডপ|akhra|আখড়া"):
            return "religious.temple", ""
        if rel == "christian" or bld in ("church", "chapel", "cathedral") or n(r"church|গির্জা|চার্চ|mission|মিশন"):
            return "religious.church", ""
        if rel == "buddhist" or bld == "pagoda" or n(r"vihar|বিহার|pagoda|প্যাগোডা|kyang"):
            return "religious.buddhist_vihara", ""
        return "religious", rel or "religion not stated"
    if off == "religion":
        return "religious", "religious organisation office"

    # --- transport
    if a == "bus_station":
        return "transport.bus_terminal", ""
    rw = t.get("railway", "")
    if rw in ("station", "halt"):
        if t.get("station") in ("subway", "light_rail", "monorail") or n(r"metro|মেট্রো"):
            return "transport", "metro rail station"
        return "transport.railway_station", "halt" if rw == "halt" else ""
    if t.get("public_transport") == "station":
        if t.get("train") == "yes" or n(r"railway|রেল"):
            return "transport.railway_station", ""
        if t.get("bus") == "yes" or n(r"bus|বাস|terminal|টার্মিনাল"):
            return "transport.bus_terminal", ""
        if t.get("ferry") == "yes" or n(r"ghat|ঘাট|launch|লঞ্চ"):
            return "transport.launch_ghat", ""
        return "transport", "public transport station"
    if t.get("highway") == "bus_stop":
        if n(r"terminal|টার্মিনাল"):
            return "transport.bus_terminal", "tagged as bus stop"
        return "transport.bus_stop", ""
    if t.get("aeroway") == "aerodrome":
        return "transport.airport", ""
    if t.get("aeroway") == "heliport":
        return None, "heliport"
    if a == "fuel":
        return "transport.fuel_station", ""
    if a == "ferry_terminal":
        return "transport.launch_ghat", ""
    if a in ("taxi", "bus_stand"):
        return "transport", f"amenity={a} (stand)"
    if a == "parking":
        return "transport", "parking"
    if a == "charging_station":
        return "transport", "EV charging station"
    if a in ("car_wash", "car_rental", "vehicle_inspection", "motorcycle_rental", "bicycle_rental", "compressed_air"):
        return "business.vehicle_service", a
    if rw == "tram_stop":
        return None, "railway=tram_stop"

    # --- business: food and markets
    if a in ("restaurant", "fast_food", "food_court", "bbq"):
        return "business.restaurant", "" if a == "restaurant" else a.replace("_", " ")
    if a in ("cafe", "ice_cream"):
        return "business.cafe", "" if a == "cafe" else "ice cream"
    if a in ("bar", "pub", "biergarten", "nightclub"):
        return "business", f"amenity={a}"
    if a == "marketplace":
        if n(r"\bhat\b|\bhaat\b|হাট"):
            return "agriculture.haat", ""
        return "business.market", ""

    # --- agriculture: cold storage
    if n(r"cold ?storage|হিমাগার"):
        return "agriculture.cold_storage", ""

    # --- other
    if a in ("community_centre", "social_centre", "events_venue", "conference_centre", "community_hall", "townhall"):
        return "other.community_center", "" if a == "community_centre" else a.replace("_", " ")
    if off in ("ngo", "association", "foundation", "charity", "non_profit") or a in ("social_facility",) and off == "ngo":
        return "other.ngo", "" if off == "ngo" else off
    if a in ("social_facility", "orphanage", "animal_shelter", "refugee_site", "nursing_home"):
        return "other", f"amenity={a}"
    if a in ("cinema", "theatre", "arts_centre", "casino", "planetarium", "exhibition_centre", "studio"):
        return "other", f"amenity={a}"
    if off in ("political_party", "union", "trade_union", "cooperative", "quango", "club"):
        return "other", f"office={off}"
    if t.get("club"):
        return "other", f"club={t['club']}"

    # --- tourism / leisure / history
    if tour == "museum":
        return "tourism.museum", ""
    if lei == "garden" and not tour:
        # named leisure=garden in BD OSM is mostly a private plot ("Betel nut garden of <person>")
        if n(r"nursery|নার্সারি|horticultur|হর্টিকালচার"):
            return "agriculture.nursery", "leisure=garden"
        if not n(r"park|পার্ক|উদ্যান|botanic|বোটানিক|eco|ইকো|public|শিশু|children|memorial|স্মৃতি|city|সিটি|pourashava|পৌর"):
            return None, "garden / private plot (leisure=garden)"
    if tour in ("zoo", "theme_park", "aquarium", "picnic_site") or lei in ("park", "garden", "water_park"):
        if lei == "garden" and t.get("garden:type") in ("residential", "private") or t.get("access") == "private":
            return None, "private garden"
        return "tourism.park", tour or lei
    if lei == "nature_reserve":
        return "tourism.natural", "nature reserve"
    if lei == "beach_resort":
        return "tourism.beach", ""
    if tour == "viewpoint":
        return "tourism.natural", "viewpoint"
    if hist:
        if hist in ("milestone", "boundary_stone", "yes", "district_boundary", "pillory", "survey_point"):
            return None, f"historic={hist}"
        if hist in ("archaeological_site", "ruins"):
            return "tourism.archaeological", hist
        if hist in ("tomb",) or n(r"mazar|মাজার|dargah|দরগাহ"):
            return "religious.mazar", hist
        if hist in ("wayside_shrine",):
            return "tourism.religious_site", hist
        return "tourism.historical", hist
    if tour in ("attraction", "artwork", "camp_site", "caravan_site", "gallery", "information") and not (
            tour == "information" and t.get("information") in ("board", "guidepost", "map", "route_marker")):
        if tour == "information" and not off:
            return None, f"tourism=information ({t.get('information', '')})"
        return "tourism", f"tourism={tour}"
    if tour == "information":
        return None, "tourism=information board"
    if tour in ("hostel",):
        return None, "hostel / student mess"
    if tour == "apartment":
        return None, "private residence (tourism=apartment: mostly residential buildings in BD)"
    if tour in ("hotel", "guest_house", "motel", "resort", "chalet") or lei == "resort":
        return "business", f"lodging ({tour or 'resort'})"
    if lei in ("stadium", "sports_centre", "pitch", "track", "golf_course", "sports_hall", "swimming_pool",
               "ice_rink", "horse_riding", "miniature_golf", "dance", "bowling_alley", "shooting_ground"):
        if lei in ("pitch", "track", "swimming_pool") and not t.get("name"):
            return None, f"unnamed leisure={lei}"
        return "other", f"sports venue (leisure={lei})"
    if lei in ("fitness_centre", "fitness_station"):
        return "business.service", "gym / fitness centre"
    if lei in ("playground", "recreation_ground", "common", "amusement_arcade", "adult_gaming_centre",
               "fishing", "marina", "picnic_table", "slipway", "bird_hide", "outdoor_seating", "bandstand",
               "firepit", "dog_park", "sauna", "hackerspace", "escape_game"):
        if lei in ("playground", "recreation_ground", "common") and t.get("name"):
            return "other", f"playground / open field (leisure={lei})"
        return None, f"leisure={lei}"

    # --- shops and crafts
    if sh:
        if sh in ("vacant", "no", "yes;vacant"):
            return None, "vacant shop"
        if sh == "supermarket":
            return "business.supermarket", ""
        if sh in ("mall", "department_store"):
            return "business.shopping", ""
        if sh in ("clothes", "fashion", "shoes", "jewelry", "tailor", "boutique", "fabric", "bag", "cosmetics",
                  "fashion_accessories", "watches", "leather", "sewing", "perfumery", "wedding"):
            return "business.fashion", ""
        if sh in ("car_repair", "motorcycle", "motorcycle_repair", "car", "car_parts", "tyres", "bicycle", "truck",
                  "auto_rickshaw", "fuel"):
            return "business.vehicle_service", ""
        if sh in ("mobile_phone", "computer", "electronics", "telecommunication", "copyshop", "printer_ink",
                  "video_games", "mobile_phone_accessories"):
            return "business.it_service", ""
        if sh in ("chemist", "medical_supply", "optician", "hearing_aids", "herbalist", "nutrition_supplements"):
            return "business.health_service", sh
        if sh in ("hairdresser", "beauty", "laundry", "dry_cleaning", "travel_agency", "funeral_directors", "tattoo",
                  "massage", "photo", "ticket", "rental", "repair", "pest_control", "locksmith", "printing",
                  "courier", "storage_rental"):
            return "business.service", f"shop={sh}"
        if sh in ("agrarian", "garden_centre", "farm", "seeds", "fertilizer", "feed"):
            return ("agriculture.nursery", "") if sh == "garden_centre" else ("agriculture", f"shop={sh}")
        return "business.shop", "" if sh != "yes" else "shop type not stated"
    if craft:
        if craft in ("tailor", "dressmaker", "shoemaker"):
            return "business.fashion", f"craft={craft}"
        if craft in ("carpenter", "electrician", "plumber", "painter", "glaziery", "hvac", "roofer", "tiler",
                     "builder", "insulation", "floorer", "plasterer", "cleaning", "gardener", "upholsterer"):
            return "business.home_service", f"craft={craft}"
        if craft in ("electronics_repair", "computer_repair", "mobile_phone_repair"):
            return "business.it_service", f"craft={craft}"
        if craft in ("car_repair", "motorcycle_repair", "bicycle_repair"):
            return "business.vehicle_service", f"craft={craft}"
        return "business.service", f"craft={craft}"
    if off:
        if off in ("it", "telecommunication", "software"):
            return "business.it_service", f"office={off}"
        if off in ("lawyer", "notary", "estate_agent", "travel_agent", "employment_agency", "advertising_agency",
                   "courier", "logistics", "company", "consulting", "architect", "engineer", "newspaper",
                   "property_management", "moving_company", "surveyor", "security", "event_management", "visa",
                   "construction_company", "manufacturer", "transport", "bus_company", "shipping_agent", "guide",
                   "graphic_design", "marketing", "translator", "photographer", "private_investigator", "yes",
                   "parcel", "publisher", "media", "printing", "broadcaster", "television", "radio"):
            return "business.service", f"office={off}"
        if off in ("educational_institution", "school"):
            return "education", f"office={off}"
        if off in ("medical", "doctor", "healthcare"):
            return "business.health_service", f"office={off}"
        if re.search(r"mill|factory|industr", off, re.I):
            return "business", "factory / works (office=%s)" % off
        if off in ("agricultural", "agriculture", "forestry"):
            return "agriculture.agri_office", f"office={off}"
        return "business", f"office={off}"

    # --- remaining man_made / buildings / amenities
    if mm in ("lighthouse", "observatory", "windmill"):
        return "tourism", f"man_made={mm}"
    if mm == "works":
        return "business", "factory / works (man_made=works)"
    if mm in ("tower", "bridge", "telescope"):
        return None, f"man_made={mm}"
    if bld in ("train_station", "transportation"):
        return "transport", f"building={bld}"
    if bld in ("commercial", "retail", "office"):
        return "business", f"named building={bld}"
    if bld in ("hotel",):
        return "business", "lodging (building=hotel)"
    if bld in ("warehouse", "industrial"):
        return "business", f"named building={bld}"
    if a:
        return None, f"amenity={a} (no rule)"
    return None, "no matching rule"


OWNERSHIP = {"government": "public", "public": "public", "military": "public", "state": "public", "municipal": "public",
             "private": "private", "business": "private", "commercial": "private", "private_non_profit": "trust",
             "ngo": "ngo", "religious": "trust", "community": "trust", "trust": "trust", "autonomous": "autonomous"}

EXTRA_KEYS = ["amenity", "shop", "office", "healthcare", "healthcare:speciality", "tourism", "historic", "leisure",
              "craft", "emergency", "railway", "station", "public_transport", "highway", "aeroway", "man_made",
              "building", "landuse", "club", "sport", "information", "social_facility", "shelter_type", "beds",
              "operator:type", "isced:level", "school:type", "religion", "denomination", "wheelchair", "wikidata",
              "wikipedia", "brand", "brand:wikidata", "brand:en", "brand:bn", "network", "iata", "icao",
              "fuel:cng", "fuel:octane_95", "fuel:octane_92", "fuel:diesel", "fuel:lpg", "atm", "cuisine", "name",
              "name:bn", "name:en", "alt_name", "old_name", "official_name", "short_name", "start_date", "heritage",
              "capacity", "stars", "rooms", "check_date", "source", "access", "fee", "internet_access", "ref",
              "addr:postcode"]
UNNAMED_OK = {"finance.atm", "transport.fuel_station", "emergency.police_station", "emergency.police_outpost",
              "emergency", "emergency.fire_station", "emergency.water_sanitation", "emergency.disaster_shelter",
              "emergency.ambulance"}
# unnamed toilets / drinking water are kept only when tagged as publicly accessible (most unnamed ones are camp or
# household latrines and tube wells)
UNNAMED_WATER_OK = {"toilets", "drinking_water"}
PUBLIC_ACCESS = {"yes", "public", "permissive", "customers"}


def address(t):
    if t.get("addr:full"):
        return nfc(t["addr:full"])
    parts = []
    hn, st = t.get("addr:housenumber", ""), t.get("addr:street", "")
    if hn or st:
        parts.append(" ".join(x for x in (hn, st) if x))
    for k in ("addr:place", "addr:suburb", "addr:village", "addr:hamlet", "addr:city", "addr:district",
              "addr:postcode"):
        v = t.get(k)
        if v and v not in parts:
            parts.append(v)
    return nfc(", ".join(parts))


def phone_of(t):
    vals = []
    for k in ("contact:phone", "phone", "contact:mobile", "mobile", "phone:mobile"):
        for v in re.split(r"\s*[;,]\s*", t.get(k, "")):
            v = nfc(v)
            if v and v not in vals:
                vals.append(v)
    return "; ".join(vals)


def website_of(t):
    for k in ("contact:website", "website", "url", "contact:facebook", "facebook"):
        if t.get(k):
            return nfc(t[k].split(";")[0])
    return ""


# Many recent features carry an English category after a comma ("Azim Mosjid, Mosque", "X, Government office",
# "Y, Bus ticket agenc"), in the style of commercial map listings. The suffix is removed from the name, the
# original is kept in extra_json.name, and the row is flagged (provenance worth checking before publication).
SUFFIX_RE = re.compile(r"^(.*\S)\s*,\s+([A-Z][A-Za-z&'\-]*(?:[ /][A-Za-z&'\-()]+){0,6})$")
GENERIC_WORD = re.compile(
    r"\b(mosque|masjid|school|office|hospital|pharmacy|temple|station|bank|restaurant|market|cent(?:er|re)|store|shop|"
    r"college|institut\w*|kindergarten|service|services|warehouse|farm|park|landmark|agenc\w*|clinic|university|"
    r"organi[sz]ation|ground|mall|hotel|cafe|bakery|academy|doctor|dentist|police|library|court|post|atm|attraction|"
    r"museum|stadium|church|monastery|shrine|cemetery|graveyard|hall|club|supplier|dealer|manufacturer|company|repair|"
    r"salon|parlou?r|wholesaler|worship|government|madrasa|madrasah|seminary|lab|laboratory|depot|terminal|stand|stop|"
    r"godown|factory|mill|plant|house|bazar|bazaar|zoo|garden|playground|field|fitness|gym|studio|agent|atm|"
    r"maintenance|charity|foundation|association|chamber|retailer|contractor|consultant|producer|pump|outlet|"
    r"complex|tower|building|apartment|residence|lodge|motel|resort|bistro|eatery|takeaway|food|sweets?|"
    r"diagnostic|medical|healthcare|health|ngo|non-governmental|bus|railway|train|airport)\b", re.I)


def strip_category_suffix(name):
    m = SUFFIX_RE.match(name or "")
    if m and GENERIC_WORD.search(m.group(2)) and len(m.group(1)) >= 2:
        return m.group(1).strip(), m.group(2)
    return name, ""


def split_bilingual(name):
    """'Latin part বাংলা অংশ' or 'বাংলা (Latin)' -> (bn, en); otherwise ('', '')."""
    if not (BN.search(name) and LATIN.search(name)):
        return "", ""
    i = BN.search(name).start()
    j = LATIN.search(name).start()
    if j < i:   # Latin first
        en, bn = name[:i], name[i:]
    else:
        bn, en = name[:j], name[j:]

    def strip(x):
        x = x.strip(" -–—,;:/|")
        while x.endswith(("(", "[")):
            x = x[:-1].strip(" -–—,;:/|")
        if x.startswith("(") and x.endswith(")"):
            x = x[1:-1].strip()
        if x.count("(") < x.count(")") and x.endswith(")"):
            x = x[:-1].strip()
        if x.count("(") > x.count(")") and x.startswith("("):
            x = x[1:].strip()
        return x
    en, bn = strip(en), strip(bn)
    if LATIN.search(bn) or BN.search(en) or len(en) < 2 or len(bn) < 2:
        return "", ""
    if en.count("(") != en.count(")") or bn.count("(") != bn.count(")"):
        return "", ""
    return bn, en


def norm_name(s):
    s = nfc(s).lower()
    return re.sub(r"[\s\-\(\)\.,।'\"/&]+", "", s)


def haversine(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(min(1.0, h)))


PRIMARY_TAGS = ("amenity", "shop", "office", "healthcare", "tourism", "historic", "leisure", "craft", "emergency",
                "railway", "public_transport", "highway", "aeroway", "man_made", "landuse", "building")


def tag_combo(t):
    for k in PRIMARY_TAGS:
        if t.get(k):
            return f"{k}={t[k]}"
    return "name only"


def build(els, b, source_key):
    rows, drops, outside = [], Counter(), Counter()
    in_bbox = 0
    x0, y0, x1, y1 = b["division"].bbox
    for el in els:
        lat, lon, t = el["lat"], el["lon"], el["tags"]
        if not (x0 <= lon <= x1 and y0 <= lat <= y1):
            continue
        in_bbox += 1
        inside, dist, upn, cc, loc_note = locate(b, lon, lat)
        if not inside:
            outside[el["type"]] += 1
            continue
        cat, reason = classify(t)
        if not cat:
            drops[reason] += 1
            continue
        raw_name = nfc(t.get("name", ""))
        name, suffix = strip_category_suffix(raw_name)
        nbn, nen = nfc(t.get("name:bn", "")), nfc(t.get("name:en", ""))
        nen, suffix_en = strip_category_suffix(nen)
        suffix = suffix or suffix_en
        sbn, sen = split_bilingual(name)
        if sbn:
            nbn, nen = nbn or sbn, nen or sen
        if not nbn and BN.search(name) and not LATIN.search(name):
            nbn = name
        if not nen and name and not BN.search(name) and LATIN.search(name):
            nen = name
        if not (nbn or nen) and name:   # mixed / other script names that could not be split: keep as published
            if BN.search(name):
                nbn = name
            else:
                nen = name
        notes = []
        if not (nbn or nen):
            ok = cat in UNNAMED_OK and (cat != "emergency.water_sanitation" or (
                t.get("amenity") in UNNAMED_WATER_OK and t.get("access") in PUBLIC_ACCESS))
            if not ok:
                drops[f"unnamed ({tag_combo(t)})" if cat.split(".")[0] in ("emergency", "business", "transport")
                      else f"unnamed ({cat.split('.')[0]})"] += 1
                continue
            notes.append("unnamed in OSM")
        if reason:
            notes.append(reason)
        if suffix:
            notes.append(f"category suffix ', {suffix}' removed from OSM name; provenance worth checking")
        if loc_note:
            notes.append(loc_note)
        extra = {k: t[k] for k in EXTRA_KEYS if t.get(k)}
        if "name" in extra and extra["name"] in (nbn, nen):
            del extra["name"]   # kept only when it differs from name_bn / name_en
        for k in ("beds", "capacity", "rooms", "stars"):
            if k in extra and extra[k].isdigit():
                extra[k] = int(extra[k])
        extra["osm_type"], extra["osm_id"] = el["type"], el["id"]
        if el["type"] != "node":
            extra["geometry"] = "centroid of " + ("closed way" if el.get("closed") else el["type"]
                                                  if el["type"] == "relation" else "way")
        if cc:
            extra["city_corporation"] = cc["name"]
            if not upn:
                notes.append(f"inside {cc['name']} (no upazila polygon)")
        rows.append({
            "source_key": source_key,
            "source_id": f"{el['type']}/{el['id']}",
            "name_bn": nbn, "name_en": nen, "category_key": cat,
            "lat": f"{lat:.6f}", "lon": f"{lon:.6f}",
            "address": address(t), "district_en": dist, "upazila_en": upn,
            "phone": phone_of(t),
            "website": website_of(t),
            "email": nfc(t.get("contact:email") or t.get("email") or ""),
            "opening_hours": nfc(t.get("opening_hours", "")),
            "operator": nfc(t.get("operator", "")),
            "ownership": OWNERSHIP.get(t.get("operator:type", "").lower(), ""),
            "extra_json": extra,
            "source_url": f"https://www.openstreetmap.org/{el['type']}/{el['id']}",
            "notes": notes,
            "_ntags": len(t), "_r": min(max(50, el.get("r", 0)), 500), "_combo": tag_combo(t),
        })
    # de-duplicate within OSM: same normalised name + category, node vs way/relation of the same object
    # (within the area's half-diagonal, 50-500 m) or two features within 50 m. The richest-tagged one is kept.
    rows.sort(key=lambda r: (-r["_ntags"], r["source_id"]))
    kept, grid = [], defaultdict(list)
    dup_count, dup_kinds = 0, Counter()
    for r in rows:
        nk = norm_name(r["name_bn"] or r["name_en"])
        if nk:
            pt = (float(r["lat"]), float(r["lon"]))
            gk = (nk, r["category_key"])
            hit = None
            for k in grid[gk]:
                d = haversine(pt, (float(k["lat"]), float(k["lon"])))
                lim = max(k["_r"], r["_r"]) if (k["source_id"][0] != "n" or r["source_id"][0] != "n") else 50
                if d <= lim:
                    hit = k
                    break
            if hit:
                hit.setdefault("_dups", []).append(r["source_id"])
                dup_kinds[f"{hit['source_id'].split('/')[0]}+{r['source_id'].split('/')[0]}"] += 1
                dup_count += 1
                continue
            grid[gk].append(r)
        kept.append(r)
    for r in kept:
        if r.get("_dups"):
            r["notes"].append("same object also mapped as " + ", ".join(sorted(r["_dups"])) + " (merged)")
            r["extra_json"]["merged_osm"] = sorted(r["_dups"])
        r["extra_json"] = json.dumps(r["extra_json"], ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        r["notes"] = "; ".join(r["notes"])
    kept.sort(key=lambda r: (r["district_en"], r["upazila_en"], r["category_key"], r["source_id"]))
    return kept, drops, dup_count, dup_kinds, outside, in_bbox


def write_csvs(rows, out_dir):
    """places.csv, places_2.csv, … each below MAX_FILE_BYTES. Returns the file names written."""
    import io
    for f in os.listdir(out_dir):
        if re.fullmatch(r"places(_\d+)?\.csv", f):
            os.remove(os.path.join(out_dir, f))

    def line(values):
        buf = io.StringIO()
        csv.writer(buf, lineterminator="\n").writerow(values)
        return buf.getvalue().encode("utf-8")
    header = line(COLS)
    files, cur, size = [], [], len(header)
    for r in rows:
        ln = line([r.get(c, "") for c in COLS])
        if cur and size + len(ln) > MAX_FILE_BYTES:
            files.append(cur)
            cur, size = [], len(header)
        cur.append(ln)
        size += len(ln)
    files.append(cur)
    names = []
    for i, chunk in enumerate(files, 1):
        name = "places.csv" if i == 1 else f"places_{i}.csv"
        with open(os.path.join(out_dir, name), "wb") as f:
            f.write(header)
            f.writelines(chunk)
        names.append(name)
    return names


def stats(rows, drops, dups, dup_kinds, outside, in_bbox, meta, b, division, files):
    top = lambda r: r["category_key"].split(".")[0]
    n = len(rows)
    pct = lambda k: round(100 * k / n, 1) if n else 0
    by_dist = defaultdict(Counter)
    for r in rows:
        by_dist[r["district_en"] or "(none)"][top(r)] += 1
    proposals = defaultdict(Counter)
    for r in rows:
        if "." not in r["category_key"]:
            proposals[r["category_key"]][r["_combo"]] += 1
    return {
        "division": division,
        "osm_timestamp": meta.get("osm_timestamp"),
        "extract": meta.get("download", {}).get("final_url") or PBF_URL,
        "boundaries": b["folder"],
        "files": files,
        "rows": n,
        "candidates_in_division_bbox": in_bbox,
        "dropped_outside_division_polygon": sum(outside.values()),
        "dropped_outside_by_type": dict(outside),
        "duplicates_merged": dups,
        "duplicates_merged_by_kind": dict(dup_kinds),
        "dropped": dict(drops.most_common()),
        "by_top_category": dict(Counter(top(r) for r in rows).most_common()),
        "by_category": dict(Counter(r["category_key"] for r in rows).most_common()),
        "top_level_only_by_osm_tag": {k: dict(v.most_common()) for k, v in sorted(proposals.items())},
        "by_district_top": {d: dict(c) for d, c in sorted(by_dist.items())},
        "by_upazila": dict(Counter(f"{r['district_en']}/{r['upazila_en'] or '-'}" for r in rows).most_common()),
        "with_phone": sum(1 for r in rows if r["phone"]),
        "with_website": sum(1 for r in rows if r["website"]),
        "with_email": sum(1 for r in rows if r["email"]),
        "with_address": sum(1 for r in rows if r["address"]),
        "with_opening_hours": sum(1 for r in rows if r["opening_hours"]),
        "with_name_bn": sum(1 for r in rows if r["name_bn"]),
        "with_name_en": sum(1 for r in rows if r["name_en"]),
        "unnamed": sum(1 for r in rows if "unnamed in OSM" in r["notes"]),
        "without_upazila": sum(1 for r in rows if not r["upazila_en"]),
        "without_district": sum(1 for r in rows if not r["district_en"]),
        "category_suffix_flagged": sum(1 for r in rows if "category suffix" in r["notes"]),
        "pct_name_bn": pct(sum(1 for r in rows if r["name_bn"])),
        "elements_by_type": dict(Counter(r["source_id"].split("/")[0] for r in rows)),
        "unmapped_hdx_codes": b["unmapped"],
    }


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def write_manifest(division, out_dir, osm_ts=None, extract_url=None, accessed=None):
    mp = os.path.join(out_dir, "SOURCE.json")
    old = json.load(open(mp, encoding="utf-8")) if os.path.isfile(mp) else {}
    name = division.capitalize()
    m = {
        "key": key_for(division),
        "name": f"OpenStreetMap contributors — {name} Division extract (points of interest)",
        "organization": "OpenStreetMap Foundation",
        "source_type": "community_dataset",
        "trust_level": 1,
        "urls": ["https://download.geofabrik.de/asia/bangladesh.html", PBF_URL,
                 "https://www.openstreetmap.org/copyright"],
        "accessed": accessed or old.get("accessed"),
        "publication_date": None,
        "osm_data_timestamp": osm_ts or old.get("osm_data_timestamp"),
        "license": "ODbL-1.0",
        "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
        "attribution": "© OpenStreetMap contributors",
        "division": division,
        "kind": "osm",
        "files": {},
        "notes": (f"Geofabrik Bangladesh extract ({extract_url or old.get('extract') or PBF_URL}), OSM data as of "
                  f"{osm_ts or old.get('osm_data_timestamp')}, parsed locally with pyosmium by "
                  f"osm_rajshahi_division/fetch.py --division {division}. Named POI-like nodes, ways and multipolygon "
                  f"relations (ways/relations by area centroid); unnamed kept only for ATM, fuel, toilets, drinking "
                  f"water with a public access tag, police, fire, ambulance, shelters. District/upazila by point-in-polygon against "
                  f"{DIVISIONS[division][1]}/boundaries.geojson (seed names via its crosswalk.csv). Community data: "
                  f"every row is unverified. Contacts are those published on the feature. ODbL is share-alike: a "
                  f"published database derived from these rows must be offered under ODbL with attribution. "
                  f"The .pbf is not committed (fetch.py downloads it again)."),
    }
    if old.get("extract") or extract_url:
        m["extract"] = extract_url or old.get("extract")
    files = sorted(f for f in os.listdir(out_dir) if re.fullmatch(r"places(_\d+)?\.csv", f))
    files.sort(key=lambda f: int(re.findall(r"\d+", f)[0]) if re.findall(r"\d+", f) else 1)
    for rel in files + ["stats.json"] + (["fetch.py"] if out_dir == HERE else []):
        if os.path.isfile(os.path.join(out_dir, rel)):
            m["files"][rel] = sha256(os.path.join(out_dir, rel))
    with open(mp, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
        f.write("\n")


def run_division(division, els, meta, out_dir):
    b = load_boundaries(division)
    os.makedirs(out_dir, exist_ok=True)
    rows, drops, dups, dup_kinds, outside, in_bbox = build(els, b, key_for(division))
    files = write_csvs(rows, out_dir)
    st = stats(rows, drops, dups, dup_kinds, outside, in_bbox, meta, b, division, files)
    st["file_bytes"] = {f: os.path.getsize(os.path.join(out_dir, f)) for f in files}
    with open(os.path.join(out_dir, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
        f.write("\n")
    accessed = (meta.get("download", {}).get("downloaded") or time.strftime("%Y-%m-%d"))[:10]
    write_manifest(division, out_dir, meta.get("osm_timestamp"), meta.get("download", {}).get("final_url"), accessed)
    print(f"{division}: {st['rows']} rows -> {out_dir} {files}; outside {st['dropped_outside_division_polygon']}, "
          f"dups {dups}", file=sys.stderr)
    return st, {(r["source_id"]) for r in rows}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--division", default="rajshahi", choices=list(DIVISIONS) + ["all"])
    ap.add_argument("--out", help="output folder (default: ../osm_<division>_division; Rajshahi: this folder)")
    ap.add_argument("--cache", default=os.environ.get("OSM_CACHE") or os.path.join(tempfile.gettempdir(), "elaka360_osm"),
                    help="directory for the .pbf and parsed candidates (not committed)")
    ap.add_argument("--offline", action="store_true", help="never download")
    ap.add_argument("--refresh", action="store_true", help="download and parse the extract again")
    ap.add_argument("--manifest", action="store_true", help="only refresh SOURCE.json checksums")
    args = ap.parse_args()
    divisions = list(DIVISIONS) if args.division == "all" else [args.division]
    if args.out and len(divisions) > 1:
        raise SystemExit("--out needs a single --division")
    if args.manifest:
        for d in divisions:
            write_manifest(d, args.out or folder_for(d))
        return
    els, meta = load_candidates(args)
    print(f"{len(els)} national candidates, OSM timestamp {meta.get('osm_timestamp')}", file=sys.stderr)
    assigned = Counter()
    for d in divisions:
        _, ids = run_division(d, els, meta, args.out or folder_for(d))
        for i in ids:
            assigned[i] += 1
    if args.division == "all":
        # candidates that fall in no division polygon (sea, India/Myanmar part of the extract, boundary slivers)
        bs = [load_boundaries(d)["division"] for d in DIVISIONS]
        nowhere = Counter()
        for el in els:
            if not any(p.contains(el["lon"], el["lat"]) for p in bs):
                nowhere["named" if el["tags"].get("name") else "unnamed"] += 1
        twice = sum(1 for v in assigned.values() if v > 1)
        print(json.dumps({"candidates": len(els), "in_no_division_polygon": dict(nowhere),
                          "rows_in_two_divisions": twice}), file=sys.stderr)
        with open(os.path.join(args.cache, "national_summary.json"), "w") as f:
            json.dump({"candidates": len(els), "in_no_division_polygon": nowhere, "rows_in_two_divisions": twice}, f)


if __name__ == "__main__":
    main()
