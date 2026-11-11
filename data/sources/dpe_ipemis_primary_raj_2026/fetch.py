#!/usr/bin/env python3
"""Fetch the DPE IPEMIS primary-school directory for Rajshahi Division (stdlib + requests only).

Usage: python3 fetch.py [--offline]   (--offline rebuilds the CSVs from raw/ and keeps previously fetched live statistics)."""
# --- polite HTTP helper (copy this block into each fetch.py; stdlib + requests only) -----------------
# Many *.gov.bd servers send only their leaf certificate and omit the intermediate CA. Browsers fetch the
# missing intermediate via the certificate's AIA URL; we do the same explicitly: download the published
# intermediates from the CA and add them to certifi's bundle. TLS verification stays ON.
import os, time, tempfile, urllib.parse, urllib.robotparser
import requests

UA = "Elaka360-data-pipeline (research; contact via repository)"
INTERMEDIATES = [  # CA-published intermediates (AIA "CA Issuers" URLs) that some gov.bd hosts fail to send
    "http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt",
    "http://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR36.crt",
    "http://crt.sectigo.com/SSL2BUYEMEARSADomainValidationSecureServerCA.crt",
]
MIN_DELAY = 1.2  # seconds between requests to the same host

_last, _robots, _bundle = {}, {}, None
S = requests.Session()
S.headers["User-Agent"] = UA


def _der_to_pem(der):
    import base64
    b = base64.encodebytes(der).decode().replace("\n", "")
    return "-----BEGIN CERTIFICATE-----\n" + "\n".join(b[i:i + 64] for i in range(0, len(b), 64)) + "\n-----END CERTIFICATE-----\n"


def ca_bundle():
    global _bundle
    if _bundle:
        return _bundle
    import certifi
    pems = [open(certifi.where(), encoding="ascii").read()]
    for u in INTERMEDIATES:
        try:
            r = requests.get(u, timeout=30, headers={"User-Agent": UA})
            if r.ok:
                pems.append(r.content.decode() if r.content.startswith(b"-----") else _der_to_pem(r.content))
        except requests.RequestException:
            pass
        time.sleep(MIN_DELAY)
    fd, path = tempfile.mkstemp(suffix=".pem")
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(pems))
    _bundle = path
    return path


def allowed(url):
    p = urllib.parse.urlsplit(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = get_raw(base + "/robots.txt")
            rp.parse(r.text.splitlines() if (r is not None and r.status_code == 200 and "html" not in r.headers.get("content-type", "")) else [])
        except Exception:
            rp.parse([])
        _robots[base] = rp
    return _robots[base].can_fetch(UA, url)


def get_raw(url, **kw):
    host = urllib.parse.urlsplit(url).netloc
    wait = MIN_DELAY - (time.time() - _last.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    try:
        return S.get(url, timeout=kw.pop("timeout", 60), verify=ca_bundle(), **kw)
    finally:
        _last[host] = time.time()


def get(url, retries=2, **kw):
    """Polite GET; returns Response or None (never raises)."""
    if not allowed(url):
        print("robots.txt disallows", url)
        return None
    for i in range(retries + 1):
        try:
            r = get_raw(url, **kw)
            if r.status_code < 500:
                return r
        except requests.RequestException as e:
            print("fetch failed", url, e)
        time.sleep(3 * (i + 1))
    return None
# --- end helper ---------------------------------------------------------------------------------------

# --- admin-name normalisation (source spellings -> standard English names) ------------------------------
import re as _re
DIVISION_DISTRICTS = ["Rajshahi", "Natore", "Naogaon", "Chapainawabganj", "Bogura", "Joypurhat", "Pabna", "Sirajganj"]
_DISTRICT_ALIASES = {
    "rajshahi": "Rajshahi", "natore": "Natore", "naogaon": "Naogaon", "chapainawabganj": "Chapainawabganj",
    "chapainawabgonj": "Chapainawabganj", "nawabganj": "Chapainawabganj", "bogura": "Bogura", "bogra": "Bogura",
    "joypurhat": "Joypurhat", "jaipurhat": "Joypurhat", "pabna": "Pabna", "sirajganj": "Sirajganj", "sirajgonj": "Sirajganj",
}
# metropolitan thanas of Rajshahi City (not upazilas)
METRO_THANAS = {"Boalia", "Rajpara", "Motihar", "Shah Makhdum"}
_UPAZILA_ALIASES = {
    # Rajshahi
    "bagha": "Bagha", "baghmara": "Bagmara", "bagmara": "Bagmara", "charghat": "Charghat", "durgapur": "Durgapur",
    "godagari": "Godagari", "mohanpur": "Mohanpur", "mohonpur": "Mohanpur", "paba": "Paba", "puthia": "Puthia",
    "tanore": "Tanore", "boalia": "Boalia", "boaliasadar": "Boalia", "rajpara": "Rajpara", "matihar": "Motihar",
    "motihar": "Motihar", "shahmakhdum": "Shah Makhdum",
    # Bogura
    "adamdighi": "Adamdighi", "bograsadar": "Bogura Sadar", "bogurasadar": "Bogura Sadar", "dhunat": "Dhunat",
    "dhunut": "Dhunat", "dhupchanchia": "Dhupchanchia", "dhupchachia": "Dhupchanchia", "gabtali": "Gabtali",
    "gabtoli": "Gabtali", "kahaloo": "Kahaloo", "nandigram": "Nandigram", "sariakandi": "Sariakandi",
    "shariakandi": "Sariakandi", "shajahanpur": "Shajahanpur", "sherpur": "Sherpur", "shibganj": "Shibganj",
    "shibgonj": "Shibganj", "sonatola": "Sonatala", "sonatala": "Sonatala", "shonatola": "Sonatala",
    # Joypurhat
    "akkelpur": "Akkelpur", "joypurhatsadar": "Joypurhat Sadar", "jaipurhatsadar": "Joypurhat Sadar", "kalai": "Kalai",
    "khetlal": "Khetlal", "panchbibi": "Panchbibi", "pachbibi": "Panchbibi",
    # Naogaon
    "atrai": "Atrai", "badalgachhi": "Badalgachhi", "dhamoirhat": "Dhamoirhat", "dhamurhat": "Dhamoirhat",
    "mahadebpur": "Mohadevpur", "mohadebpur": "Mohadevpur", "mohadevpur": "Mohadevpur", "manda": "Manda",
    "naogaonsadar": "Naogaon Sadar", "niamatpur": "Niamatpur", "patnitala": "Patnitala", "porsha": "Porsha",
    "raninagar": "Raninagar", "sapahar": "Sapahar", "shapahar": "Sapahar",
    # Natore
    "bagatipara": "Bagatipara", "baraigram": "Baraigram", "gurudaspur": "Gurudaspur", "gurudashpur": "Gurudaspur",
    "lalpur": "Lalpur", "naldanga": "Naldanga", "natoresadar": "Natore Sadar", "singra": "Singra", "shingra": "Singra",
    # Chapainawabganj
    "bholahat": "Bholahat", "chapainawabganjsadar": "Chapainawabganj Sadar",
    "chapainawabgonjsadar": "Chapainawabganj Sadar", "gomastapur": "Gomastapur", "nachole": "Nachole",
    "nachol": "Nachole",
    # Pabna
    "atgharia": "Atgharia", "bera": "Bera", "bhangura": "Bhangura", "chatmohar": "Chatmohar", "chatmahar": "Chatmohar",
    "faridpur": "Faridpur", "ishwardi": "Ishwardi", "pabnasadar": "Pabna Sadar", "santhia": "Santhia",
    "sujanagar": "Sujanagar",
    # Sirajganj
    "belkuchi": "Belkuchi", "chauhali": "Chauhali", "chowhali": "Chauhali", "kamarkhanda": "Kamarkhanda",
    "kazipur": "Kazipur", "royganj": "Raiganj", "raygonj": "Raiganj", "raiganj": "Raiganj",
    "shahjadpur": "Shahjadpur", "shajadpur": "Shahjadpur", "sirajganjsadar": "Sirajganj Sadar",
    "sirajgonjsadar": "Sirajganj Sadar", "tarash": "Tarash", "ullahpara": "Ullahpara", "ullapara": "Ullahpara",
}


def _key(s):
    return _re.sub(r"[^a-z]", "", (s or "").lower().replace("upazila", ""))


def norm_district(s):
    return _DISTRICT_ALIASES.get(_key(s), "")


def norm_upazila(s):
    return _UPAZILA_ALIASES.get(_key(s), "")
# --- end normalisation -----------------------------------------------------------------------------------

# --- output helpers ---------------------------------------------------------------------------------------
import csv, json, hashlib, unicodedata, datetime

PLACE_COLS = ["source_key", "source_id", "name_bn", "name_en", "category_key", "lat", "lon", "address", "district_en",
              "upazila_en", "phone", "website", "email", "opening_hours", "operator", "ownership", "extra_json",
              "source_url", "notes"]
FACT_COLS = ["entity_level", "entity_name_en", "district_en", "upazila_en", "code", "fact", "value", "unit", "basis",
             "year", "source_key", "source_url", "notes"]
HERE = os.path.dirname(os.path.abspath(__file__))


def nfc(s):
    if s is None:
        return ""
    s = unicodedata.normalize("NFC", str(s)).replace("\xa0", " ")
    return _re.sub(r"\s+", " ", s).strip()


def cj(d):
    return json.dumps({k: v for k, v in d.items() if v not in (None, "", [], {})}, ensure_ascii=False, separators=(",", ":"))


def write_csv(name, cols, rows):
    with open(os.path.join(HERE, name), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r.get(c)) for c in cols})


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def update_manifest(files):
    p = os.path.join(HERE, "SOURCE.json")
    m = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    m["accessed"] = datetime.date.today().isoformat()
    m["files"] = {f: sha256(os.path.join(HERE, f)) for f in files if os.path.exists(os.path.join(HERE, f))}
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(m, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
# --- end output helpers -----------------------------------------------------------------------------------

# --- DPE IPEMIS primary-school directory: Rajshahi Division ---------------------------------------------
import sys
from collections import Counter, defaultdict

SOURCE_KEY = "DPE_IPEMIS_PRIMARY_RAJ_2026"
SITE = "https://ipemis.dpe.gov.bd"
API = "https://api.ipemis.dpe.gov.bd"
LIST_URL = SITE + "/load-lite-school-list?draw=1&start={start}&length=500&divisionId=1&districtId={did}"
DETAIL_URL = SITE + "/school-details-view/{sid}"
SEARCH_PAGE = SITE + "/search-school"
DIVISION_ID = 1  # IPEMIS id of Rajshahi Division (from the search page's division <select>)
RAW = os.path.join(HERE, "raw", "ipemis_school_list_rajshahi_division.json")


def getjson(url):
    r = get(url, headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"})
    if r is None or r.status_code != 200:
        print("FAILED", url, None if r is None else r.status_code)
        return None
    try:
        return r.json()
    except ValueError:
        print("not JSON", url)
        return None


def main():
    offline = "--offline" in sys.argv
    districts = getjson(f"{API}/api/districts/lite/division/{DIVISION_ID}") if not offline else None
    districts = (districts or {}).get("data") or []
    schools = []
    if not offline:
        for d in districts:
            start, total = 0, None
            while total is None or start < total:
                j = getjson(LIST_URL.format(start=start, did=d["districtId"]))
                if not j:
                    break
                total = j.get("recordsTotal", 0)
                schools += j.get("aaData") or []
                start += 500
            print(d["name"], total)
    if schools:
        os.makedirs(os.path.dirname(RAW), exist_ok=True)
        with open(RAW, "w", encoding="utf-8") as f:
            json.dump(schools, f, ensure_ascii=False, separators=(",", ":"))
    elif os.path.exists(RAW):
        print("using cached raw", RAW)
        schools = json.load(open(RAW, encoding="utf-8"))

    rows, seen = [], set()
    for s in schools:
        if s["schoolId"] in seen:
            continue
        seen.add(s["schoolId"])
        dist = norm_district(s.get("districtName"))
        upz = norm_upazila(s.get("upazilaName"))
        notes = []
        if not upz:
            notes.append(f"upazila '{s.get('upazilaName')}' not normalised")
        if upz in METRO_THANAS:
            notes.append("IPEMIS unit BOALIA(SADAR) = Rajshahi City Corporation area (metropolitan thana), not an upazila")
        union = nfc(s.get("geoUnionNameLocal") or s.get("geoUnionName"))
        rows.append({
            "source_key": SOURCE_KEY,
            "source_id": f"ipemis:{s['schoolId']}",
            "name_bn": nfc(s.get("schoolNameLocal")),
            "name_en": nfc(s.get("schoolName")),
            "category_key": "education.primary_school",
            "address": ", ".join(x for x in [union, nfc(s.get("upazilaNameLocal")), nfc(s.get("districtNameLocal"))] if x),
            "district_en": dist,
            "upazila_en": upz,
            "operator": "Directorate of Primary Education",
            "ownership": "government",
            "extra_json": cj({
                "school_code": s.get("schoolCode"), "ipemis_school_id": s.get("schoolId"),
                "school_type": s.get("schoolTypeName"), "school_type_bn": nfc(s.get("schoolTypeNameLocal")),
                "union_or_ward_bn": union, "cluster": nfc(s.get("geoClusterName")),
                "cluster_bn": nfc(s.get("geoClusterNameLocal")),
                "upazila_src": s.get("upazilaName"), "district_src": s.get("districtName"),
                "teachers": s.get("totalTeacher"), "students": s.get("totalStudent"),
                "admin_unit": "metropolitan_thana" if upz in METRO_THANAS else "upazila",
            }),
            "source_url": DETAIL_URL.format(sid=s["schoolId"]),
            "notes": "; ".join(notes),
        })
    rows.sort(key=lambda r: (r["district_en"] != "Rajshahi", r["district_en"], r["upazila_en"], r["name_en"]))
    write_csv("places.csv", PLACE_COLS, rows)

    # facts: official IPEMIS public statistics per division / district / upazila + listed-record counts by type
    facts = []
    year = datetime.date.today().year
    stat_fields = [("totalSchool", "primary_schools", "schools"), ("govtSchool", "govt_primary_schools", "schools"),
                   ("experimentalSchool", "experimental_schools", "schools"),
                   ("totalTeacher", "primary_teachers", "persons"), ("totalStudent", "primary_students", "persons")]

    def add_stats(level, name, dist, upz, code, params):
        url = f"{API}/api/school-stat-public?{params}"
        j = getjson(url)
        if not j or not j.get("data"):
            return
        for k, fact, unit in stat_fields:
            if j["data"].get(k) is not None:
                facts.append({"entity_level": level, "entity_name_en": name, "district_en": dist, "upazila_en": upz,
                              "code": code, "fact": fact, "value": j["data"][k], "unit": unit,
                              "basis": "official_live_statistic", "year": year, "source_key": SOURCE_KEY,
                              "source_url": SEARCH_PAGE,
                              "notes": f"IPEMIS public school statistic API ({url}); live figure on access date; "
                                       "covers schools in IPEMIS (govt, newly nationalised, experimental)"})

    if offline and os.path.exists(os.path.join(HERE, "facts.csv")):  # keep previously fetched live statistics
        facts += [r for r in csv.DictReader(open(os.path.join(HERE, "facts.csv"), encoding="utf-8"))
                  if r["basis"] == "official_live_statistic"]
    if not offline:
        add_stats("division", "Rajshahi", "", "", f"ipemis_division:{DIVISION_ID}", f"divisionId={DIVISION_ID}")
        for d in districts:
            dist = norm_district(d["name"])
            add_stats("district", dist, dist, "", f"ipemis_district:{d['districtId']}",
                      f"divisionId={DIVISION_ID}&districtId={d['districtId']}")
            ups = getjson(f"{API}/api/upazilas/lite/district/{d['districtId']}")
            for u in (ups or {}).get("data") or []:
                upz = norm_upazila(u["name"])
                add_stats("thana" if upz in METRO_THANAS else "upazila", upz or u["name"], dist, upz,
                          f"ipemis_upazila:{u['upazilaId']}",
                          f"divisionId={DIVISION_ID}&districtId={d['districtId']}&upazilaId={u['upazilaId']}")
    cnt = Counter((r["district_en"], r["upazila_en"], json.loads(r["extra_json"]).get("school_type")) for r in rows)
    for (dist, upz, typ), n in sorted(cnt.items()):
        facts.append({"entity_level": "thana" if upz in METRO_THANAS else "upazila", "entity_name_en": upz,
                      "district_en": dist, "upazila_en": upz, "code": "",
                      "fact": "primary_schools_listed_" + _re.sub(r"[^a-z]+", "_", typ.lower()).strip("_"),
                      "value": n, "unit": "schools", "basis": "count_of_listed_records", "year": year,
                      "source_key": SOURCE_KEY, "source_url": SEARCH_PAGE,
                      "notes": f"count of IPEMIS directory rows with school type '{typ}'"})
    write_csv("facts.csv", FACT_COLS, facts)
    update_manifest(["places.csv", "facts.csv", "raw/ipemis_school_list_rajshahi_division.json"])
    print("places", len(rows), "facts", len(facts))
    print(Counter(r["district_en"] for r in rows))


if __name__ == "__main__":
    main()
