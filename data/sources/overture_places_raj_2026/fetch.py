#!/usr/bin/env python3
"""Overture Maps Foundation — places theme (type=place), one division of Bangladesh (default Rajshahi).

Source: the latest Overture release in the official public bucket s3://overturemaps-us-west-2/release/<version>/
theme=places/type=place/ (anonymous, no login), found through the release catalog https://stac.overturemaps.org/catalog.json.
Licences per upstream dataset: https://docs.overturemaps.org/attribution/ (Places section).

Steps
  1. download: one DuckDB query reads the GeoParquet straight from S3, keeps only rows whose bbox falls in a generous
     Bangladesh box (lon 87.9–92.8, lat 20.5–26.75) and writes a local extract (not committed, ~50–150 MB) to the cache
     folder (default <tmp>/elaka360_overture/<release>/, override with --cache or OVERTURE_CACHE).
  2. build: point-in-polygon against the HDX COD-AB boundaries of all 8 divisions (../hdx_cod_ab_bgd/ for Rajshahi,
     ../hdx_cod_ab_bgd_<division>/ otherwise), English district/upazila names from that folder's crosswalk.csv (seed
     names), Overture taxonomy -> categories.csv key, then places.csv (+ places_2.csv … when > 20 MB), raw/stats.json,
     raw/category_map.csv and SOURCE.json for the division.

Usage: python3 fetch.py                       # Rajshahi: download the extract (if not cached) and build this folder
       python3 fetch.py --division rangpur    # another division -> ../overture_places_rang_2026 (see ../DIVISIONS.md)
       python3 fetch.py --all                 # all 8 divisions from one extract
       python3 fetch.py --offline [--extract PATH]   # build from a cached extract only, no network
       python3 fetch.py --release 2026-10-21.0       # a specific release instead of the latest

Dependencies: requests + duckdb (pip install duckdb; tested with duckdb 2.0.0). DuckDB loads its official httpfs and
spatial extensions (INSTALL httpfs / spatial, downloaded once from extensions.duckdb.org). This deviates from the
"stdlib + requests" rule of COLLECTION_FORMAT.md because Overture is published only as GeoParquet.
REPORT.md is written by hand from raw/stats.json.
"""
import argparse, collections, csv, datetime, hashlib, io, json, os, re, sys, tempfile, time, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.dirname(HERE)
CODES = {"rajshahi": "raj", "rangpur": "rang", "dhaka": "dhk", "chattogram": "ctg", "khulna": "khl",
         "barishal": "bar", "sylhet": "syl", "mymensingh": "mym"}
UA = "Elaka360-data-pipeline (research; contact via repository)"
CATALOG = "https://stac.overturemaps.org/catalog.json"
ATTRIBUTION_URL = "https://docs.overturemaps.org/attribution/"
BUCKET = "s3://overturemaps-us-west-2/release/{release}/theme=places/type=place/*.parquet"
HTTPS_PREFIX = "https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com/release/{release}/theme=places/type=place/"
COLLECTION = "https://stac.overturemaps.org/{release}/places/place/collection.json"
FSQ_NOTICE = "https://opensource.foursquare.com/places-notice-txt/"
BD_BOX = (87.9, 92.8, 20.5, 26.75)          # lon min/max, lat min/max — generous, the polygons decide
MAX_BYTES = 19_500_000                      # each places file stays < 20 MB
# Licence of each upstream dataset, as listed in the Places section of https://docs.overturemaps.org/attribution/
# (checked 2026-11-18). Rows carry sources[].license themselves when Overture fills it; this is the fallback.
DATASET_LICENSE = {
    "meta": "CDLA-Permissive-2.0", "microsoft": "CDLA-Permissive-2.0", "pinmeto": "CDLA-Permissive-2.0",
    "krick": "CDLA-Permissive-2.0", "renderseo": "CDLA-Permissive-2.0", "dac": "CDLA-Permissive-2.0",
    "brightquery": "CDLA-Permissive-2.0", "birdeye": "CDLA-Permissive-2.0", "uberall": "CDLA-Permissive-2.0",
    "opentravel": "CDLA-Permissive-2.0", "opentravel alliance": "CDLA-Permissive-2.0",
    "foursquare": "Apache-2.0", "alltheplaces": "CC0-1.0",
}
ATTRIBUTION = {   # wording of the attribution page, per dataset
    "CDLA-Permissive-2.0": "Data from {names}. Available under CDLA Permissive 2.0.",
    "Apache-2.0": ("Data from Foursquare. Copyright 2024 Foursquare Labs, Inc. All rights reserved. Available under "
                   "Apache 2.0. Foursquare data was transformed to the Overture schema. Changed: 2026-03-18. NOTICE.txt "
                   "(https://opensource.foursquare.com/places-notice-txt/)."),
    "CC0-1.0": "Data from AllThePlaces. Available under CC0 1.0.",
}
LICENSE_URL = {"CDLA-Permissive-2.0": "https://cdla.dev/permissive-2-0/",
               "Apache-2.0": "https://www.apache.org/licenses/LICENSE-2.0",
               "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/"}

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--division", default="rajshahi", choices=sorted(CODES))
ap.add_argument("--all", action="store_true", help="build all 8 divisions (default output folders)")
ap.add_argument("--out", default=None, help="output folder (default: this folder for Rajshahi, else the sibling folder)")
ap.add_argument("--offline", action="store_true", help="no network: build from the cached extract")
ap.add_argument("--release", default=None, help="Overture release (default: latest in the STAC catalog / cache)")
ap.add_argument("--cache", default=os.environ.get("OVERTURE_CACHE") or os.path.join(tempfile.gettempdir(), "elaka360_overture"))
ap.add_argument("--extract", default=None, help="path of an existing extract parquet (implies its release)")
ARGS = ap.parse_args()


def duck():
    import duckdb
    c = duckdb.connect(config={"custom_user_agent": UA})
    for ext in ("httpfs", "spatial"):
        try:
            c.execute(f"LOAD {ext}")
        except Exception:
            if ARGS.offline and ext == "httpfs":
                continue
            c.execute(f"INSTALL {ext}; LOAD {ext}")
    return c


# --- release + download ------------------------------------------------------------------------------------------
def latest_release():
    import requests
    r = requests.get(CATALOG, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    cat = r.json()
    rel = cat.get("latest") or next(l["title"].split()[0] for l in cat["links"] if l.get("latest"))
    time.sleep(1.2)
    r = requests.get(f"https://stac.overturemaps.org/{rel}/catalog.json", headers={"User-Agent": UA}, timeout=60)
    schema = r.json().get("schema:version") if r.ok else None
    return rel, schema


def extract_path(release):
    return os.path.join(ARGS.cache, release, "places_bd_bbox.parquet")


def stac_files(release):
    """S3 URLs of the release's places files whose STAC item bbox intersects the Bangladesh box (one file in 2026-10)."""
    import requests
    col = requests.get(COLLECTION.format(release=release), headers={"User-Agent": UA}, timeout=60).json()
    x0, x1, y0, y1 = BD_BOX
    files = []
    for l in col["links"]:
        if l["rel"] != "item":
            continue
        time.sleep(1.2)
        it = requests.get(l["href"], headers={"User-Agent": UA}, timeout=60).json()
        bx = it["bbox"]
        if bx[0] <= x1 and bx[2] >= x0 and bx[1] <= y1 and bx[3] >= y0:
            href = it["assets"]["aws"]["href"]
            files.append("s3://overturemaps-us-west-2/" + href.split(".amazonaws.com/", 1)[1])
    return files


def fetch_notice(folder):
    """Foursquare's NOTICE.txt (Apache-2.0 requires passing it on with the data), as text, next to the extract."""
    import html, requests
    path = os.path.join(folder, "FOURSQUARE_NOTICE.txt")
    if os.path.isfile(path):
        return
    try:
        r = requests.get(FSQ_NOTICE, headers={"User-Agent": UA}, timeout=60)
    except requests.RequestException as e:
        print("notice not fetched:", e)
        return
    t = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", "", r.text)
    t = re.sub(r"<(br|/p|/li|/h\d|/div)[^>]*>", "\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = "\n".join(x.strip() for x in t.splitlines() if x.strip())
    j = t.find("limitations under the License.")
    i = t.rfind("Foursquare OS Places Notice", 0, t.find("All rights reserved."))   # the heading, not <title>
    if r.ok and i >= 0 and j > i:
        with open(path, "w", encoding="utf-8") as f:
            f.write(t[i:j + len("limitations under the License.")] + f"\n\n(Retrieved {datetime.date.today()} from {FSQ_NOTICE})\n")
    else:
        print("notice page layout changed; not saved")


def download(release, schema):
    path = extract_path(release)
    if os.path.isfile(path) and os.path.isfile(path + ".json"):
        print("cached extract", path)
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    files = stac_files(release)
    print("files intersecting Bangladesh:", files)
    c = duck()
    c.execute("SET s3_region='us-west-2'")
    x0, x1, y0, y1 = BD_BOX
    t = time.time()
    tmp = path + ".part"
    for attempt in range(3):
        try:
            c.execute(f"""COPY (
                SELECT id, ST_X(geometry) AS lon, ST_Y(geometry) AS lat, ST_GeometryType(geometry)::VARCHAR AS geom_type,
                       confidence, websites, emails, socials, phones, brand, addresses, names, sources, operating_status,
                       basic_category, taxonomy, version
                FROM read_parquet({files!r})
                WHERE bbox.xmin <= {x1} AND bbox.xmax >= {x0} AND bbox.ymin <= {y1} AND bbox.ymax >= {y0}
            ) TO '{tmp}' (FORMAT parquet, COMPRESSION zstd)""")
            break
        except Exception as e:      # transient DNS/HTTP errors
            print("extract failed:", e)
            if attempt == 2:
                raise
            time.sleep(30)
    n = c.execute(f"SELECT count(*) FROM read_parquet('{tmp}')").fetchone()[0]
    os.replace(tmp, path)
    meta = dict(release=release, schema_version=schema, extracted=datetime.date.today().isoformat(), files=files,
                bbox=dict(zip(("lon_min", "lon_max", "lat_min", "lat_max"), BD_BOX)), rows=n, seconds=round(time.time() - t))
    json.dump(meta, open(path + ".json", "w"), indent=2)
    print(f"extract: {n} rows in {meta['seconds']} s -> {path}")
    return path


# --- boundaries ------------------------------------------------------------------------------------------------------
def hdx_dir(div):
    return os.path.join(SOURCES, "hdx_cod_ab_bgd" if div == "rajshahi" else f"hdx_cod_ab_bgd_{div}")


def load_polys(c):
    """All 8 divisions' HDX polygons into DuckDB table polys; returns crosswalk code -> seed English name per division."""
    c.execute("CREATE OR REPLACE TABLE polys (div VARCHAR, level VARCHAR, code VARCHAR, parent_code VARCHAR, "
              "name_en VARCHAR, geom GEOMETRY, x0 DOUBLE, x1 DOUBLE, y0 DOUBLE, y1 DOUBLE)")
    xw = {}
    for div in CODES:
        d = hdx_dir(div)
        g = json.load(open(os.path.join(d, "boundaries.geojson"), encoding="utf-8"))
        rows = [(div, f["properties"]["level"], f["properties"]["code"], f["properties"].get("parent_code") or "",
                 f["properties"]["name_en"], json.dumps(f["geometry"])) for f in g["features"]
                if f["properties"]["level"] in ("division", "district", "upazila", "city_corporation")]
        c.executemany("INSERT INTO polys SELECT ?, ?, ?, ?, ?, ST_GeomFromGeoJSON(?), 0, 0, 0, 0", rows)
        with open(os.path.join(d, "crosswalk.csv"), encoding="utf-8-sig", newline="") as f:
            xw[div] = {r["source_code"]: r["our_name_en"] for r in csv.DictReader(f)
                       if r["source_code"] and r["our_name_en"] and r["our_level"] in ("district", "upazila", "city_corporation")}
    c.execute("UPDATE polys SET x0 = ST_XMin(geom), x1 = ST_XMax(geom), y0 = ST_YMin(geom), y1 = ST_YMax(geom)")
    return xw


def assign(c, extract):
    """Point -> (division, district code, unit code, unit level) for every extract row inside some division polygon."""
    c.execute(f"CREATE OR REPLACE TABLE pts AS SELECT id, lon, lat FROM read_parquet('{extract}')")
    hits = collections.defaultdict(list)
    for pid, div, level, code, parent in c.execute("""
            SELECT p.id, q.div, q.level, q.code, q.parent_code FROM pts p JOIN polys q
              ON p.lon BETWEEN q.x0 AND q.x1 AND p.lat BETWEEN q.y0 AND q.y1
             AND ST_Intersects(q.geom, ST_Point(p.lon, p.lat))""").fetchall():
        hits[pid].append((div, level, code, parent))
    out, amb = {}, collections.Counter()
    for pid, hs in hits.items():
        divs = sorted({h[0] for h in hs if h[1] == "division"})
        if not divs:
            continue                     # only inside a lower-level polygon: simplification sliver, treated as outside
        if len(divs) > 1:                # shared border, independently simplified: the division with a unit polygon wins
            with_unit = sorted({h[0] for h in hs if h[1] in ("upazila", "city_corporation")} & set(divs))
            amb["border_points"] += 1
            divs = with_unit[:1] or divs[:1]
        div = divs[0]
        units = sorted((h for h in hs if h[0] == div and h[1] in ("city_corporation", "upazila")),
                       key=lambda h: (h[1] != "city_corporation", h[2]))
        dists = sorted(h[2] for h in hs if h[0] == div and h[1] == "district")
        if len(units) > 1:
            amb[f"{div}:point_in_two_units"] += 1
        unit = units[0] if units else None
        dist = unit[3] if unit else (dists[0] if dists else None)
        out[pid] = (div, dist, unit[2] if unit else None, unit[1] if unit else None)
    return out, amb


# --- normalisation -------------------------------------------------------------------------------------------------
BN = re.compile(r"[ঀ-৿]")
LATIN = re.compile(r"[A-Za-z]")


def nfc(s):
    return unicodedata.normalize("NFC", re.sub(r"\s+", " ", s or "").strip())


def as_map(m):
    if not m:
        return {}
    if isinstance(m, dict) and set(m) == {"key", "value"}:
        return dict(zip(m["key"], m["value"]))
    return dict(m)


def names_of(names):
    """(name_bn, name_en, other_names) from Overture names: primary, common{lang: value}, rules[{language, value}]."""
    names = names or {}
    prim = nfc(names.get("primary"))
    common = {k: nfc(v) for k, v in as_map(names.get("common")).items() if v}
    rules = [r for r in (names.get("rules") or []) if r and r.get("value")]
    bn_cands = [common.get("bn")] + [nfc(r["value"]) for r in rules if (r.get("language") or "").startswith("bn")]
    en_cands = [common.get("en")] + [nfc(r["value"]) for r in rules if (r.get("language") or "").startswith("en")]
    name_bn = prim if BN.search(prim) else next((x for x in bn_cands if x and BN.search(x)), "")
    if prim and not BN.search(prim):
        name_en = prim
    else:
        name_en = next((x for x in en_cands if x and not BN.search(x)), "")
    other = {k: v for k, v in common.items() if v not in (name_bn, name_en)}
    for r in rules:
        v = nfc(r["value"])
        if v not in (name_bn, name_en):
            other[f"{r.get('variant') or 'rule'}:{r.get('language') or ''}"] = v
    return name_bn, name_en, other


def url_ok(u):
    return bool(u) and re.match(r"^https?://\S+$", u.strip()) is not None


def phones_of(ps):
    out = []
    for p in ps or []:
        p = re.sub(r"[^\d+]", "", p or "")
        if len(re.sub(r"\D", "", p)) >= 5 and p not in out:
            out.append(p)
    return out


def emails_of(es):
    return [e.strip() for e in es or [] if e and re.fullmatch(r"[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+", e.strip())]


def band(cf):
    if cf is None:
        return "none"
    for lo in (0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2):
        if cf >= lo:
            return f">={lo}"
    return "<0.2"


# --- taxonomy -> categories.csv ------------------------------------------------------------------------------------
# Overture taxonomy category -> categories.csv key. Looked up for taxonomy.primary first, then up taxonomy.hierarchy
# (most specific first). APPROX marks a deliberate "closest fit" (reported as a proposed new subcategory); the L0
# fallback (TOP) is always reported. Places without any Overture category go to "other" (counted separately).
CAT = {
    # education
    "elementary_school": "education.primary_school", "high_school": "education.secondary_school",
    "middle_school": "education.secondary_school", "college_university": "education.college",
    "medical_school": "education.medical_college", "vocational_and_technical_school": "education.technical",
    "specialty_school": "education.training_center", "computer_coaching": "education.training_center",
    "language_school": "education.training_center", "driving_school": "education.training_center",
    "art_school": "education.training_center", "music_school": "education.training_center",
    "cooking_school": "education.training_center", "nursing_school": "education.training_center",
    "educational_service": "business.education_service", "tutoring_service": "business.education_service",
    "test_preparation": "business.education_service", "private_tutor": "business.education_service",
    "religious_school": "education", "school": "education", "place_of_learning": "education",
    # health
    "hospital": "health.hospital", "doctors_office": "health.clinic", "outpatient_care_facility": "health.clinic",
    "specialized_medical_facility": "health.clinic", "dental_clinic": "health.clinic",
    "diagnostics_imaging_or_lab_service": "health.diagnostic_center", "laboratory_testing": "health.diagnostic_center",
    "pharmacy": "health.pharmacy", "pharmacy_and_drug_store": "health.pharmacy",
    "ambulance_or_ems_service": "emergency.ambulance", "medical_service": "business.health_service",
    "home_health_care": "business.health_service", "medical_supply_store": "business.health_service",
    # government / emergency
    "government_office": "government", "courthouse": "government.court", "post_office": "government.post_office",
    "police_station": "emergency.police_station", "fire_station": "emergency.fire_station",
    # religious
    "muslim_place_of_worship": "religious.mosque", "hindu_place_of_worship": "religious.temple",
    "buddhist_place_of_worship": "religious.buddhist_vihara", "christian_place_of_worship": "religious.church",
    "place_of_worship": "religious",
    # tourism / culture / nature
    "historic_site": "tourism.historical", "memorial_site": "tourism.historical", "monument": "tourism.historical",
    "archaeological_site": "tourism.archaeological", "museum": "tourism.museum", "park": "tourism.park",
    "nature_reserve": "tourism.natural", "land_feature": "tourism.natural", "mountain": "tourism.hill",
    "beach": "tourism.beach", "waterfall": "tourism.waterfall", "water_feature": "tourism.river_haor",
    "river": "tourism.river_haor", "lake": "tourism.river_haor",
    # business
    "restaurant": "business.restaurant", "casual_eatery": "business.restaurant",
    "cafe": "business.cafe", "coffee_shop": "business.cafe", "tea_room": "business.cafe",
    "non_alcoholic_beverage_venue": "business.cafe", "bakery": "business.shop", "dessert_shop": "business.shop",
    "candy_store": "business.shop", "shopping_mall": "business.shopping", "department_store": "business.shopping",
    "supermarket": "business.supermarket", "superstore": "business.supermarket", "grocery_store": "business.shop",
    "convenience_store": "business.shop", "specialty_store": "business.shop", "discount_store": "business.shop",
    "food_and_beverage_store": "business.shop", "second_hand_store": "business.shop", "vehicle_dealer": "business.shop",
    "market": "business.market", "farmers_market": "business.market", "fashion_and_apparel_store": "business.fashion",
    "it_service_and_computer_repair": "business.it_service", "software_development": "business.it_service",
    "internet_service_provider": "business.it_service", "web_designer": "business.it_service",
    "information_technology_company": "business.it_service", "computer_hardware_company": "business.it_service",
    "home_service": "business.home_service", "vehicle_service": "business.vehicle_service",
    "personal_or_beauty_service": "business.service", "professional_service": "business.service",
    "legal_service": "business.service", "event_or_party_service": "business.service",
    "printing_service": "business.service", "real_estate_service": "business.service",
    "design_service": "business.service", "media_service": "business.service", "laundry_service": "business.service",
    "shipping_or_delivery_service": "business.service", "rental_service": "business.service",
    "technical_service": "business.service", "travel_service": "business.service", "family_service": "business.service",
    "security_service": "business.service", "telecommunications_service": "business.service",
    # finance
    "bank_or_credit_union": "finance.bank", "bank": "finance.bank", "atm": "finance.atm", "financial_service": "finance",
    # transport
    "bus_station": "transport.bus_terminal", "bus_stop": "transport.bus_stop", "train_station": "transport.railway_station",
    "airport": "transport.airport", "fueling_station": "transport.fuel_station", "gas_station": "transport.fuel_station",
    "ferry_terminal": "transport.launch_ghat",
    # agriculture
    "agricultural_service": "agriculture", "b2b_agriculture_service": "agriculture", "farm": "agriculture.farm", "dairy_farm": "agriculture.farm",
    "fish_farm": "agriculture.farm", "fish_farm_hatchery": "agriculture.farm", "livestock_breeder": "agriculture.farm",
    "poultry_farm": "agriculture.farm", "urban_farm": "agriculture.farm",
    "nursery_and_gardening_store": "agriculture.nursery",
    # other
    "community_center": "other.community_center", "non_governmental_association": "other.ngo",
    "charity_organization": "other.ngo",
}
APPROX = {   # closest fit, no matching key: reported as proposed subcategories
    "alcoholic_beverage_venue": "business.restaurant", "food_service": "business.service",
    "lodging": "business", "arts_and_entertainment": "business", "sport_or_fitness_facility": "business.service",
    "sport_or_recreation_club": "other", "sport_league": "other", "sport_team": "other",
    "wellness_service": "business.service", "animal_or_pet_service": "business.service",
    "b2b_service": "business", "corporate_or_business_office": "business", "industrial_facility_or_service": "business",
    "building_or_construction_service": "business.service", "storage_facility": "business.service",
    "housing_or_property_service": "business.service", "environmental_or_ecological_service": "other",
    "warehouse_club_store": "business.shop", "public_utility": "government", "military_site": "government",
    "embassy": "government", "town_hall": "government", "housing_authority": "government",
    "civic_organization": "other", "social_or_community_service": "other", "religious_organization": "religious",
    "cultural_center": "other.community_center", "public_facility": "other", "built_feature": "other",
    "stadium_arena": "other", "art_gallery": "tourism.museum", "amusement_attraction": "tourism.park",
    "animal_attraction": "tourism.park", "parking": "transport", "air_transport_facility_or_service": "transport",
    "ground_transport_facility_or_service": "transport", "blood_and_plasma_donation_center": "health",
    "emergency_or_urgent_care_facility": "health", "preschool": "education", "library": "education",
    "research_institute": "education", "educational_facility": "education",
}
TOP = {"education": "education", "health_care": "health", "community_and_government": "other",
       "cultural_and_historic": "tourism", "food_and_drink": "business", "shopping": "business.shopping",
       "services_and_business": "business", "travel_and_transportation": "transport", "lodging": "business",
       "lifestyle_services": "business", "sports_and_recreation": "other", "arts_and_entertainment": "business",
       "geographic_entities": "tourism.natural"}
NAME_RULES = [   # (applies to keys starting with, name regex, key) — refinements from the place's own name
    (("education",), r"medical college|মেডিকেল কলেজ", "education.medical_college"),
    (("education",), r"polytechnic|পলিটেকনিক", "education.polytechnic"),
    (("education",), r"universit|বিশ্ববিদ্যালয়|বিশ্ববিদ্যালয়", "education.university"),
    (("education", "religious"), r"madrass?a|madrasah|madrasha|মাদ্রাসা|মাদরাসা", "education.madrasa"),
    (("education",), r"high school|উচ্চ বিদ্যালয়|উচ্চ বিদ্যালয়|secondary school|মাধ্যমিক বিদ্যালয়|মাধ্যমিক বিদ্যালয়", "education.secondary_school"),
    (("education",), r"primary school|প্রাথমিক বিদ্যালয়|প্রাথমিক বিদ্যালয়", "education.primary_school"),
    (("health.hospital",), r"medical college hospital|মেডিকেল কলেজ হাসপাতাল", "health.medical_college_hospital"),
    (("health",), r"upazila health complex|উপজেলা স্বাস্থ্য কমপ্লেক্স", "health.upazila_health_complex"),
    (("health",), r"community clinic|কমিউনিটি ক্লিনিক", "health.community_clinic"),
    (("religious",), r"eidgah|idgah|ঈদগাহ", "religious.eidgah"),
    (("religious",), r"mazar|majar|dargah|মাজার|দরগা", "religious.mazar"),
    (("tourism",), r"tea estate|tea garden|চা বাগান", "tourism.tea_garden"),
    (("agriculture", "business", "other"), r"cold storage|হিমাগার", "agriculture.cold_storage"),
]
NAME_RULES = [(p, re.compile(rx, re.I), k) for p, rx, k in NAME_RULES]


def map_category(prim, hier, basic, alts, name=""):
    """(category_key, how): how is 'exact', 'approx', 'top' (L0 fallback) or 'none' (no Overture category)."""
    chain = [prim] + list(reversed(hier or [])) if prim else list(reversed(hier or []))
    key, how = None, None
    for c in chain:
        if c in CAT:
            key, how = CAT[c], "exact"
            break
        if c in APPROX:
            key, how = APPROX[c], "approx"
            break
    if not key and hier:
        key, how = TOP.get(hier[0]), "top"
    if not key:
        key, how = "other", "none"
    for prefixes, rx, k in NAME_RULES:
        if key.startswith(prefixes) and key != k and rx.search(name or ""):
            if not (k == "health.medical_college_hospital" and key != "health.hospital"):
                return k, how if how == "none" else "exact"
    return key, how


# Private individuals: Overture (mostly Meta/Facebook pages) has no "person" category in Bangladesh; pages named only
# with a personal name are recognised by a Bangladeshi personal-name prefix (Md/Mohammad/Mst/মোঃ …) followed by 1–4
# name words and no business/place word. Conservative: other person pages without such a prefix are kept.
PERSON_PFX = re.compile(r"^\s*(md|mohammad|mohammed|muhammad|mohd|mst|mosammat|mossammat|মোঃ|মো:|মোহাম্মদ|মুহাম্মদ|মোছাঃ|"
                        r"মোসাঃ|মোসাম্মৎ|মোছাম্মৎ)(?:[.:ঃ]\s*|\s+)", re.I)
PLACE_WORD = re.compile(
    r"school|college|universit|academy|institut|madras|mosque|masjid|masque|jame|jami|mandir|temple|church|store|shop|"
    r"enterprise|trader|corporation|company|\bco\b|ltd|limited|telecom|pharma|clinic|hospital|diagnost|center|centre|"
    r"bhaban|bhabon|house|market|bazar|bazaar|agency|service|electronic|electric|cloth|fashion|tailor|hotel|restaurant|"
    r"biriyani|kitchen|food|farm|agro|poultry|dairy|fisher|aquarium|library|club|foundation|samity|society|group|press|"
    r"printing|studio|computer|mobile|hardware|furniture|motors?\b|garage|workshop|coaching|chamber|office|bank|brick|"
    r"mill|factory|industr|travels?|tours?|holiday|tech|garden|park|pump|filling|station|gallery|showroom|optics|dental|"
    r"medical|kindergarten|kg\b|plaza|tower|stadium|trading|builder|construction|associat|auto|car|pur\b|nagar|para\b|"
    r"road|zone|point|corner|hall|tex|garment|\bbd\b|bangladesh|\d|&|\band\b|bidyalay|biddaloy|vidyalaya|"
    r"স্কুল|বিদ্যালয়|বিদ্যালয়|কলেজ|মাদ্রাসা|মাদরাসা|মসজিদ|মন্দির|দোকান|স্টোর|ষ্টোর|এন্টারপ্রাইজ|ট্রেডার্স|ফার্মেসী|"
    r"ফার্মেসি|হাসপাতাল|ক্লিনিক|বাজার|মার্কেট|সেন্টার|একাডেমি|ফাউন্ডেশন|সমিতি|ক্লাব|লাইব্রেরি|পাঠাগার|অফিস|ভবন|বাড়ি|ঘর|"
    r"কোচিং|চেম্বার|এজেন্সি|ফ্যাশন|টেইলার্স|হোটেল|রেস্টুরেন্ট|খামার|ফার্ম|এগ্রো|পোল্ট্রি|ডেইরি|মিল|ফ্যাক্টরি|ইলেকট্রনিক্স|"
    r"ইলেকট্রিক|টেলিকম|কম্পিউটার|মোবাইল|ফার্নিচার|গ্যারেজ|ওয়ার্কশপ|শোরুম|ট্রাভেলস|গোষ্ঠি|গোষ্ঠী|এন্ড|অ্যান্ড|ও\s", re.I)


def is_person(name):
    m = PERSON_PFX.match(name or "")
    if not m or PLACE_WORD.search(name):
        return False
    toks = [x for x in re.split(r"[\s.]+", name[m.end():].strip(" .,")) if x]
    return 1 <= len(toks) <= 4 and all(re.fullmatch(r"[A-Za-zঀ-৿'’()-]+", x) for x in toks)


# --- build -------------------------------------------------------------------------------------------------------
def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


COLS = ["source_key", "source_id", "name_bn", "name_en", "category_key", "lat", "lon", "address", "district_en", "upazila_en",
        "phone", "website", "email", "opening_hours", "operator", "ownership", "extra_json", "source_url", "notes"]


def write_places(out, rows):
    for f in os.listdir(out):
        if re.fullmatch(r"places(_\d+)?\.csv", f):
            os.remove(os.path.join(out, f))
    files, n, buf, size = [], 1, None, 0
    header = io.StringIO(); csv.writer(header, lineterminator="\n").writerow(COLS)
    header = header.getvalue().encode("utf-8")

    def open_next():
        nonlocal n, size
        name = "places.csv" if n == 1 else f"places_{n}.csv"
        files.append(name); n += 1
        fh = open(os.path.join(out, name), "wb"); fh.write(header); size = len(header)
        return fh

    fh = open_next()
    for r in rows:
        s = io.StringIO(); csv.writer(s, lineterminator="\n").writerow([r.get(k, "") for k in COLS])
        b = s.getvalue().encode("utf-8")
        if size + len(b) > MAX_BYTES:
            fh.close(); fh = open_next()
        fh.write(b); size += len(b)
    fh.close()
    return files


def build(div, c, extract, meta, where, xw):
    code = CODES[div]
    key = f"OVERTURE_PLACES_{code.upper()}_2026"
    out = os.path.abspath(ARGS.out) if (ARGS.out and not ARGS.all) else (
        HERE if div == "rajshahi" else os.path.join(SOURCES, f"overture_places_{code}_2026"))
    os.makedirs(os.path.join(out, "raw"), exist_ok=True)
    release = meta["release"]
    rel_url = COLLECTION.format(release=release)
    # rows of the extract inside this division's polygon bbox (for the "outside" count)
    bx = c.execute("SELECT x0, x1, y0, y1 FROM polys WHERE div = ? AND level = 'division'", [div]).fetchone()
    q = c.execute(f"""SELECT id, lon, lat, geom_type, confidence, websites, emails, socials, phones, brand, addresses, names,
                             sources, operating_status, basic_category, taxonomy, version
                      FROM read_parquet('{extract}') WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ? ORDER BY id""", list(bx))
    cols = [d[0] for d in q.description]
    st = collections.Counter()
    by_top, by_band, by_cat, by_status, by_dataset, by_lic, proposed, persons = (collections.Counter() for _ in range(8))
    by_district = collections.Counter()
    rows = []
    while True:
        chunk = q.fetchmany(20000)
        if not chunk:
            break
        for t in chunk:
            r = dict(zip(cols, t))
            st["in_division_bbox"] += 1
            w = where.get(r["id"])
            if not w or w[0] != div:
                st["dropped_outside_division"] += 1
                if w:
                    st["outside_in_other_division"] += 1
                continue
            st["inside_division"] += 1
            status = r["operating_status"] or ""
            by_status[status or "(none)"] += 1
            if status == "permanently_closed":
                st["skipped_permanently_closed"] += 1
                continue
            tax = r["taxonomy"] or {}
            prim = tax.get("primary") or ""
            hier = list(tax.get("hierarchy") or [])
            alts = list(tax.get("alternates") or [])
            name_bn, name_en, other_names = names_of(r["names"])
            raw_name = nfc((r["names"] or {}).get("primary"))
            if is_person(raw_name):
                st["skipped_private_individual"] += 1
                persons[prim or "(none)"] += 1
                continue
            if not (name_bn or name_en):
                st["skipped_no_name"] += 1
                continue
            cat, how = map_category(prim, hier, r["basic_category"], alts, f"{name_en} {name_bn}")
            st[f"category_{how}"] += 1
            if how in ("approx", "top", "none"):
                proposed[(prim or "(none)", "/".join(hier), cat)] += 1
            by_cat[(prim or "(none)", r["basic_category"] or "", "/".join(hier), cat)] += 1
            _, dcode, ucode, ulevel = w
            district = xw[div].get(dcode or "", "")
            upazila = xw[div].get(ucode or "", "") if ulevel == "upazila" else ""
            city = xw[div].get(ucode or "", "") if ulevel == "city_corporation" else ""
            if not district:
                st["no_district"] += 1
            by_district[district or "(none)"] += 1
            phones = phones_of(r["phones"])
            sites = [u.strip() for u in r["websites"] or [] if url_ok(u)]
            socials = [u.strip() for u in r["socials"] or [] if url_ok(u)]
            emails = emails_of(r["emails"])
            addr = (r["addresses"] or [None])[0] or {}
            srcs = []
            for s in r["sources"] or []:
                ds = s.get("dataset") or ""
                if ds == "Overture" and s.get("property") == "/properties/confidence":
                    continue          # Overture's own confidence scorer, not an upstream dataset
                lic = s.get("license") or DATASET_LICENSE.get(ds.lower())
                ent = {"dataset": ds, "record_id": s.get("record_id")}
                if s.get("property"):
                    ent["property"] = s["property"]
                if s.get("update_time"):
                    ent["update_time"] = s["update_time"][:10]
                if lic:
                    ent["license"] = lic
                if ent not in srcs:
                    srcs.append(ent)
            for ds in {s["dataset"] for s in srcs if not s.get("property")} or {s["dataset"] for s in srcs}:
                by_dataset[ds] += 1
            for lic in {s.get("license") or "unknown" for s in srcs}:
                by_lic[lic] += 1
            brand = r["brand"] or {}
            extra = {"confidence": round(r["confidence"], 4) if r["confidence"] is not None else None,
                     "taxonomy_primary": prim or None, "taxonomy_hierarchy": hier or None,
                     "taxonomy_alternates": alts or None, "basic_category": r["basic_category"],
                     "operating_status": status or None, "category_fit": how,
                     "phones": phones[1:] or None, "websites": sites[1:] or None, "emails": emails[1:] or None,
                     "socials": socials or None,
                     "address_locality": nfc(addr.get("locality")) or None, "postcode": nfc(addr.get("postcode")) or None,
                     "address_region": nfc(addr.get("region")) or None, "address_country": addr.get("country"),
                     "brand": nfc((brand.get("names") or {}).get("primary")) or None, "brand_wikidata": brand.get("wikidata"),
                     "other_names": other_names or None, "city_corporation": city or None,
                     "overture_release": release, "overture_version": r["version"], "sources": srcs}
            extra = {k: v for k, v in extra.items() if v not in (None, "", [], {})}
            notes = ["Overture Maps places (community/commercial aggregate): not verified"]
            if status == "temporarily_closed":
                notes.append("Overture operating_status temporarily_closed")
                st["temporarily_closed_kept"] += 1
            if how == "none":
                notes.append("no Overture category; filed under other")
            if name_en and not LATIN.search(name_en):
                notes.append("name_en is the Overture primary name in a non-Latin, non-Bangla script")
            if city:
                notes.append(f"point inside {city} (HDX polygon); upazila_en left empty")
            if r["geom_type"] and r["geom_type"].upper() != "POINT":
                notes.append(f"geometry {r['geom_type']}; lat/lon is its first coordinate")
            rows.append(dict(source_key=key, source_id=f"overture:{r['id']}", name_bn=name_bn, name_en=name_en,
                             category_key=cat, lat=f"{r['lat']:.6f}", lon=f"{r['lon']:.6f}",
                             address=nfc(addr.get("freeform")), district_en=district, upazila_en=upazila,
                             phone="; ".join(phones[:1]), website=sites[0] if sites else "", email=emails[0] if emails else "",
                             opening_hours="", operator="", ownership="",
                             extra_json=json.dumps(extra, ensure_ascii=False, separators=(",", ":")),
                             source_url=rel_url, notes="; ".join(notes)))
            st["rows"] += 1
            by_top[cat.split(".")[0]] += 1
            by_band[band(r["confidence"])] += 1
            st["with_phone"] += bool(phones)
            st["with_website"] += bool(sites)
            st["with_email"] += bool(emails)
            st["with_social"] += bool(socials)
            st["with_name_bn"] += bool(name_bn)
            st["with_upazila"] += bool(upazila)
            st["in_city_corporation"] += bool(city)
    files = write_places(out, rows)
    notice = os.path.join(os.path.dirname(extract), "FOURSQUARE_NOTICE.txt")
    if by_dataset.get("Foursquare") and os.path.isfile(notice):
        with open(notice, encoding="utf-8") as f, open(os.path.join(out, "raw", "FOURSQUARE_NOTICE.txt"), "w", encoding="utf-8") as g:
            g.write(f.read())
    with open(os.path.join(out, "raw", "category_map.csv"), "w", encoding="utf-8", newline="") as f:
        wr = csv.writer(f, lineterminator="\n")
        wr.writerow(["taxonomy_primary", "basic_category", "taxonomy_hierarchy", "category_key", "count"])
        for (p, b, h, k), n in sorted(by_cat.items(), key=lambda x: (-x[1], x[0])):
            wr.writerow([p, b, h, k, n])
    lic_present = sorted(l for l in by_lic if l != "unknown")
    stats = dict(release=release, schema_version=meta.get("schema_version"), extract_rows_bd_bbox=meta.get("rows"),
                 counts=dict(st), by_top_level=dict(by_top.most_common()), confidence_bands=dict(sorted(by_band.items())),
                 operating_status=dict(by_status.most_common()), by_dataset=dict(by_dataset.most_common()),
                 by_license=dict(by_lic.most_common()), by_district=dict(by_district.most_common()),
                 private_individual_categories=dict(persons.most_common()),
                 proposed_subcategories=[dict(taxonomy_primary=p, hierarchy=h, mapped_to=k, count=n)
                                         for (p, h, k), n in proposed.most_common()])
    with open(os.path.join(out, "raw", "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=1); f.write("\n")
    write_manifest(out, div, key, release, lic_present, files)
    print(f"{div}: {st['rows']} places in {len(files)} file(s); {dict(st)}")
    return stats


def write_manifest(out, div, key, release, lics, files):
    p = os.path.join(out, "SOURCE.json")
    old = json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else {}
    cdla = [n for n in ("Meta", "Microsoft", "PinMeTo", "Krick", "RenderSEO", "DAC", "BrightQuery", "Birdeye", "Uberall",
                        "OpenTravel Alliance")]
    attr = ["Overture Maps Foundation, overturemaps.org."]
    for l in lics:
        attr.append(ATTRIBUTION.get(l, f"{l}").format(names=", ".join(cdla)))
    m = {
        "key": key,
        "name": f"Overture Maps Foundation — places theme, release {release}, {div.title()} Division extract",
        "organization": "Overture Maps Foundation",
        "source_type": "community_dataset",
        "trust_level": 1,
        "urls": [COLLECTION.format(release=release), HTTPS_PREFIX.format(release=release), ATTRIBUTION_URL,
                 "https://docs.overturemaps.org/guides/places/"],
        "accessed": old.get("accessed") if old.get("release") == release else datetime.date.today().isoformat(),
        "publication_date": release.split(".")[0],
        "release": release,
        "license": " AND ".join(lics) or None,
        "license_url": ATTRIBUTION_URL,
        "license_urls": {l: LICENSE_URL[l] for l in lics if l in LICENSE_URL},
        "attribution": " ".join(attr),
        "division": div,
        "kind": "overture",
        "files": {},
        "notes": (f"Overture places (schema 2.x: taxonomy/basic_category; the old categories field was removed in Sept 2026) "
                  f"read with DuckDB from s3://overturemaps-us-west-2/release/{release}/theme=places/type=place/, "
                  "bbox-filtered to Bangladesh, then assigned by point-in-polygon to HDX COD-AB upazila/city-corporation "
                  "polygons (district/upazila English names from the HDX folder's crosswalk.csv). All places kept "
                  "regardless of confidence (confidence is in extra_json); permanently_closed skipped; pages that are "
                  "clearly a private individual (personal-name pattern, see REPORT.md) skipped. Contacts are as published by "
                  "Overture (business pages); not verified. No per-record public URL is documented by Overture, so "
                  "source_url is the release's STAC collection. Licence differs per upstream dataset: see "
                  "extra_json.sources[].license and REPORT.md. Places is not OSM-derived (no ODbL share-alike)."),
    }
    rels = files + ["raw/stats.json", "raw/category_map.csv", "raw/FOURSQUARE_NOTICE.txt"]
    m["files"] = {rel: sha(os.path.join(out, rel)) for rel in rels if os.path.isfile(os.path.join(out, rel))}
    if os.path.isfile(os.path.join(out, "REPORT.md")):
        m["files"]["REPORT.md"] = sha(os.path.join(out, "REPORT.md"))
    with open(p, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2); f.write("\n")


def main():
    if ARGS.extract:
        extract = os.path.abspath(ARGS.extract)
    else:
        if ARGS.offline:
            rel = ARGS.release or sorted(d for d in os.listdir(ARGS.cache)
                                         if os.path.isfile(extract_path(d) + ".json"))[-1]
            extract = extract_path(rel)
        else:
            rel, schema = (ARGS.release, None) if ARGS.release else latest_release()
            extract = download(rel, schema)
            fetch_notice(os.path.dirname(extract))
    meta = json.load(open(extract + ".json")) if os.path.isfile(extract + ".json") else {"release": ARGS.release}
    if not meta.get("release"):
        sys.exit("release unknown: pass --release with --extract")
    c = duck()
    xw = load_polys(c)
    where, amb = assign(c, extract)
    print("assignment:", dict(amb))
    divs = list(CODES) if ARGS.all else [ARGS.division]
    allstats = {}
    for d in divs:
        allstats[d] = build(d, c, extract, meta, where, xw)
        allstats[d]["assignment_notes"] = {k: v for k, v in amb.items() if k == "border_points" or k.startswith(d + ":")}
    if ARGS.all:
        inside = sum(1 for w in where.values())
        print(json.dumps(dict(extract_rows=meta.get("rows"), inside_some_division=inside,
                              outside_all_divisions=(meta.get("rows") or 0) - inside, **{k: v for k, v in amb.items()}), indent=1))


if __name__ == "__main__":
    main()
