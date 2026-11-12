#!/usr/bin/env python3
"""Fetch DGME (Directorate General of Medical Education) medical & dental college lists; keep Rajshahi Division.

stdlib + requests only. Usage: python3 fetch.py"""
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

# --- DGME medical & dental college lists: colleges located in Rajshahi Division ---------------------------
import sys, html as _html
from collections import Counter

SOURCE_KEY = "DGME_MEDICAL_COLLEGES_RAJ_2026"
DGME = "https://dgme.gov.bd"
MEDICAL_PAGE = DGME + "/pages/static-pages/6922e0a5933eb65569e27ff3"   # সরকারি/বেসরকারি মেডিকেল কলেজ (code, year, seats)
DENTAL_PAGE = DGME + "/pages/static-pages/6922dfb1933eb65569e237f5"    # সরকারি/বেসরকারি ডেন্টাল কলেজ/ইউনিট
GOVT_WEB_PAGE = DGME + "/pages/static-pages/6922dcbc933eb65569e11be5"  # সরকারী মেডিকেল কলেজ (সকল): English names + websites
BN_DISTRICTS = {"রাজশাহী": "Rajshahi", "নাটোর": "Natore", "নওগাঁ": "Naogaon", "চাঁপাইনবাবগঞ্জ": "Chapainawabganj",
                "বগুড়া": "Bogura", "জয়পুরহাট": "Joypurhat", "পাবনা": "Pabna", "সিরাজগঞ্জ": "Sirajganj"}
EN_DISTRICT_WORDS = {"Rajshahi": ["rajshahi"], "Natore": ["natore"], "Naogaon": ["naogaon"],
                     "Chapainawabganj": ["nawabganj"], "Bogura": ["bogura", "bogra"], "Joypurhat": ["joypurhat"],
                     "Pabna": ["pabna"], "Sirajganj": ["sirajganj"]}
BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def fetch_html(url):
    r = get(url)
    if r is not None and r.status_code == 200:
        r.encoding = "utf-8"
        return r.text
    print("FAILED", url)
    return ""


def content_part(h):
    h = unicodedata.normalize("NFC", h)
    i = h.find("কন্টেন্ট")
    return h[i:] if i >= 0 else h


def blocks(h):
    """Yield ('head', text) and ('row', cells, hrefs) in document order."""
    for m in _re.finditer(r"<(h\d|p|strong|caption)[^>]*>(.*?)</\1>|<tr[^>]*>(.*?)</tr>", h, _re.S):
        if m.group(3) is None:
            t = nfc(_html.unescape(_re.sub(r"<[^>]+>", "", m.group(2))))
            if t:
                yield ("head", t, None)
        else:
            cells = [nfc(_html.unescape(_re.sub(r"<[^>]+>", "", c))) for c in _re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", m.group(3), _re.S)]
            yield ("row", cells, _re.findall(r'href="([^"]+)"', m.group(3)))


def district_of(name):
    tail = name.split(",")[-1].strip()
    if tail in BN_DISTRICTS:
        return BN_DISTRICTS[tail]
    for bn, en in BN_DISTRICTS.items():
        if bn in name:
            return en
    return ""


def num(s):
    s = (s or "").translate(BN_DIGITS).strip()
    return int(s) if s.isdigit() else None


def main():
    pages = {"medical": fetch_html(MEDICAL_PAGE),
             "dental": fetch_html(DENTAL_PAGE),
             "govt_web": fetch_html(GOVT_WEB_PAGE)}

    # English names + websites of government medical colleges, keyed by district
    gov_web = {}
    for kind, cells, hrefs in blocks(content_part(pages["govt_web"])):
        if kind != "row" or not cells or not cells[0]:
            continue
        low = cells[0].lower()
        for dist, words in EN_DISTRICT_WORDS.items():
            if any(w in low for w in words) and "medical college" in low and "dental" not in low:
                site = next((u for u in hrefs if "dgme.gov.bd" not in u), "") or (cells[1] if len(cells) > 1 else "")
                gov_web.setdefault(dist, (cells[0], site))

    rows = []
    # medical colleges: 5-column table = government, 6-column (with ছাত্র/ছাত্রী) = private
    mode = None
    for kind, cells, _ in blocks(content_part(pages["medical"])):
        if kind != "row" or len(cells) < 4:
            continue
        if "কলেজ কোড" in cells:
            mode = "private" if any("ছাত্র" in c for c in cells) else "government"
            continue
        name, dist = cells[2], district_of(cells[2])
        if not dist:
            continue
        if mode == "government":
            year, seats, gender = num(cells[3]), num(cells[4]), None
        else:
            gender, seats, year = cells[3], num(cells[4]), num(cells[5]) if len(cells) > 5 else None
        own = "armed_forces" if "আর্মি" in name else mode
        en, web = gov_web.get(dist, ("", "")) if mode == "government" else ("", "")
        rows.append({"source_key": SOURCE_KEY, "source_id": f"dgme_mbbs:{num(cells[1]) or name}",
                     "name_bn": name, "name_en": en, "category_key": "education.medical_college",
                     "district_en": dist, "website": web, "ownership": own,
                     "operator": "Directorate General of Medical Education" if mode == "government" else "",
                     "extra_json": {"dgme_college_code": num(cells[1]), "programme": "MBBS", "year_established": year,
                                    "mbbs_seats": seats, "students": gender, "dgme_list": f"{mode} medical colleges"},
                     "source_url": MEDICAL_PAGE,
                     "notes": "; ".join(n for n in [
                         "English name and website from the DGME 'সরকারী মেডিকেল কলেজ (সকল)' page, matched by district" if en else "",
                         "listed in the private-college table; Army Medical College (armed forces)" if own == "armed_forces" else ""] if n)})

    # dental colleges / units
    section = ("government", "college")
    units = []
    for kind, cells, _ in blocks(content_part(pages["dental"])):
        if kind == "head":
            t = cells
            if "বেসরকারি" in t:
                section = ("private", "unit" if "ইউনিট" in t else "college")
            elif "ডেন্টাল ইউনিট" in t and "কলেজ/" not in t:
                section = (section[0], "unit")
            elif "ডেন্টাল কলেজ" == t.strip():
                section = (section[0], "college")
            continue
        if len(cells) < 3 or cells[0] in ("ক্রম", "") or "মোট" in cells[0]:
            continue
        name, dist = cells[1], district_of(cells[1])
        if not dist:
            continue
        year = num(cells[2])
        seats = num(cells[3]) if len(cells) > 3 else None
        if section[1] == "unit":
            units.append((section[0], name, dist, cells[2], seats))
            continue
        rows.append({"source_key": SOURCE_KEY, "source_id": f"dgme_dental:{name}", "name_bn": name, "name_en": "",
                     "category_key": "education.medical_college", "district_en": dist, "ownership": section[0],
                     "extra_json": {"programme": "BDS", "year_established": year if year else None,
                                    "approval_status": None if year else cells[2], "bds_seats": seats,
                                    "dgme_list": f"{section[0]} dental colleges"},
                     "source_url": DENTAL_PAGE, "notes": "dental college"})
    # attach dental units to their parent medical college (same name before 'ডেন্টাল ইউনিট')
    for own, name, dist, yr, seats in units:
        parent = name.split("ডেন্টাল ইউনিট")[0].strip()
        hit = next((r for r in rows if r["district_en"] == dist and r["name_bn"].split(",")[0].strip() == parent), None)
        if hit:
            hit["extra_json"].update({"dental_unit": True, "dental_unit_year_established": num(yr), "bds_seats": seats})
        else:
            print("dental unit without parent:", name)

    for r in rows:
        r["extra_json"] = cj(r["extra_json"])
    rows.sort(key=lambda r: (r["district_en"] != "Rajshahi", r["district_en"], r["ownership"], r["name_bn"]))
    write_csv("places.csv", PLACE_COLS, rows)
    update_manifest(["places.csv"])
    print("places", len(rows), Counter(r["district_en"] for r in rows), Counter(r["ownership"] for r in rows))


if __name__ == "__main__":
    main()
