#!/usr/bin/env python3
"""Fetch BANBEIS institution lists (EIIN registry, e-survey 2024) and keep Rajshahi Division (stdlib + requests only).

Also cross-checks EIINs against the Rajshahi Education Board public institute list (flag only).
Usage: python3 fetch.py [--offline]   (--offline rebuilds the CSVs from raw/ without network)."""
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

# --- BANBEIS institution lists (e-survey 2024): Rajshahi Division -----------------------------------------
import sys, io, zipfile, xml.etree.ElementTree as ET
from collections import Counter

SOURCE_KEY = "BANBEIS_INST_RAJ_2026"
BANBEIS = "https://banbeis.gov.bd"
DETAIL = "https://institute-search.ieims.banbeis.gov.bd/details/{eiin}"
BOARD_LIST = "https://rajshahiboard.gov.bd/sonali/ins.php"  # JSON behind https://rajshahiboard.gov.bd/index.php/institute/
# BANBEIS file pages (each links one or more XLSX lists on the government object store)
FILE_PAGES = {
    "school": "/pages/files/69199760933eb65569ddc637",          # স্কুল-২০২৪
    "college": "/pages/files/6919975e933eb65569ddc579",         # কলেজ, স্কুল এন্ড কলেজ-২০২৪
    "madrasa": "/pages/files/69199763933eb65569ddc6e8",         # মাদ্রাসা-২০২৪
    "govt_technical": "/pages/files/69568a64a31054345f1038ee",  # সরকারি কারিগরি-২০২৪
    "technical": "/pages/files/69199762933eb65569ddc6d1",       # স্বতন্ত্র কারিগরি
    "university": "/pages/files/6919975f933eb65569ddc5ce",      # বিশ্ববিদ্যালয় (public + private)
    "professional": "/pages/files/69199761933eb65569ddc66f",    # প্রফেশনাল
}
FALLBACK_XLSX = {  # links seen on 2026-11-12, used if a file page cannot be parsed
    "school": ["5db6947e05cf4318a5bd45000f1bbcc6.xlsx"], "college": ["cb248464f0ed4f99b1e9c83d135a6e92.xlsx"],
    "madrasa": ["ecf2c7e9068c42aaa415021851be0831.xlsx"], "govt_technical": ["edff91ac6e7142c2892e285c3c59c679.xlsx"],
    "technical": ["b4abd9d741634fa8a72169154884bb3b.xlsx"],
    "university": ["e02aa2fabf4d4b70a85afa2fa3f43853.xlsx", "e9504e1e1c83496197730c5a2159901e.xlsx"],
    "professional": ["ae198d3ccdcd45b6879fdf7a2fd821b4.xlsx"],
}
OBJ = "https://objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/n/axvjbnqprylg/b/V2Ministry/o/office-banbeis/2024/12/"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def read_xlsx_bytes(data):
    z = zipfile.ZipFile(io.BytesIO(data))
    ss = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
            ss.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    sheet = sorted(n for n in z.namelist() if n.startswith("xl/worksheets/sheet"))[0]
    rows = []
    for r in ET.fromstring(z.read(sheet)).iter("{%s}row" % NS["m"]):
        row = {}
        for c in r.findall("m:c", NS):
            t, v = c.get("t"), c.find("m:v", NS)
            txt = None
            if t == "s" and v is not None:
                txt = ss[int(v.text)]
            elif t == "inlineStr":
                txt = "".join(x.text or "" for x in c.iter("{%s}t" % NS["m"]))
            elif v is not None:
                txt = v.text
            letters = _re.match(r"[A-Z]+", c.get("r")).group(0)
            idx = 0
            for ch in letters:
                idx = idx * 26 + ord(ch) - 64
            row[idx - 1] = txt
        if row:
            rows.append([row.get(i) for i in range(max(row) + 1)])
    return rows


def xlsx_links(kind):
    r = get(BANBEIS + FILE_PAGES[kind])
    links = []
    if r is not None and r.status_code == 200:
        for u in _re.findall(r"https://objectstorage[^\"'\s<>]+?\.xlsx", r.text):
            if u not in links:
                links.append(u)
    return links or [OBJ + f for f in FALLBACK_XLSX[kind]]


FREE_MAIL = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "ymail.com", "live.com", "yahoo.co.in",
             "rocketmail.com", "gmai.com", "ymai.com", "email.com", "mail.com", "googlemail.com", "icloud.com", "aol.com"}
INST_TOKENS = ["school", "schl", "college", "colg", "madras", "madrash", "dakhil", "dakil", "alim", "fazil", "kamil",
               "inst", "poly", "tech", "academy", "vidya", "bidya", "high", "girls", "balika", "mohila", "nursing",
               "varsity", "univ", "training", "voc", "office", "info", "principal", "headmaster", "eiin", "ttc",
               "registrar", "admission"]
INST_SUFFIX = _re.compile(r"(hs|ghs|jhs|jgs|hsc|sc|dm|am|fm|km|mdm|bmc|bm|tsc|ttc|tpi|pi|dc|mc|gc|sm|hm)\d*$")


def institutional_email(email, eiin, shared):
    """BANBEIS publishes one e-mail per institution. Keep it only when it looks like the institution's own
    address (own domain, contains the EIIN, or an institution word/abbreviation); drop placeholders, addresses
    shared by several institutions and personal-looking free-mail addresses."""
    e = (email or "").strip().lower()
    if not _re.match(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", e) or e.endswith("@banbeis.gov.bd"):
        return ""
    lp, dom = e.split("@", 1)
    if shared.get(e, 0) > 1 and eiin not in lp:
        return ""
    if dom not in FREE_MAIL:
        return e
    alnum = _re.sub(r"[^a-z0-9]", "", lp)
    if eiin and eiin in alnum or any(t in alnum for t in INST_TOKENS) or INST_SUFFIX.search(alnum):
        return e
    return ""


OWN = {"GOVERNMENT": "government", "NON-GOVERNMENT": "non_government", "LOCAL GOVERNMENT": "local_government",
       "AUTONOMOUS": "autonomous", "CRISTIAN MISSIONARY": "christian_missionary", "CANTONMENT BOARD": "cantonment_board",
       "NGO": "ngo", "OTHER": "other"}


def category(kind, x):
    name = (x.get("INSTITUTE_NAME") or "").upper()
    level = (x.get("EDUCATION_LEVEL_NAME") or "").upper()
    if kind == "school":
        return "education.primary_school" if "PRIMARY" in level else "education.secondary_school"
    if kind == "college":
        return "education.college"
    if kind == "madrasa":
        return "education.madrasa"
    if kind == "university":
        return "education.university"
    if kind == "professional":
        if "MEDICAL COLLEGE" in name:
            return "education.medical_college"
        if "TRAINING" in name or "TRAINING" in level or "INSTITUTE" in level:
            return "education.training_center"
        return "education.college"
    # technical lists
    if "POLYTECHNIC" in level or _re.search(r"POLY ?T[EI]CHNIC|POLITECHNIC", name):
        return "education.polytechnic"
    if _re.search(r"TRAINING|TRANING|TRAING|PROSHIK|PROSHIKH", name) or "NATIONAL SKILL" in level:
        return "education.training_center"
    return "education.technical"


def main():
    offline = "--offline" in sys.argv
    rawdir = os.path.join(HERE, "raw")
    os.makedirs(rawdir, exist_ok=True)
    records = {}  # eiin -> (kind, row dict, [files])
    file_urls = {}
    header = None
    for kind in FILE_PAGES:
        raw_path = os.path.join(rawdir, f"banbeis_{kind}_rajshahi_division.csv")
        div_rows = []
        if not offline:
            for url in xlsx_links(kind):
                r = get(url, timeout=180)
                if r is None or r.status_code != 200:
                    print("FAILED", url)
                    continue
                file_urls.setdefault(kind, []).append(url)
                rows = read_xlsx_bytes(r.content)
                hi = next(i for i, rr in enumerate(rows) if "DIVISION_NAME" in rr)
                h = [c.strip() for c in rows[hi]]
                for rr in rows[hi + 1:]:
                    d = dict(zip(h, rr))
                    if (d.get("DIVISION_NAME") or "").strip() == "Rajshahi":
                        d["_file"] = url.rsplit("/", 1)[-1]
                        div_rows.append(d)
            if div_rows:
                cols = sorted({k for d in div_rows for k in d}, key=lambda c: (c.startswith("_"), c))
                with open(raw_path, "w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=cols)
                    w.writeheader()
                    w.writerows(div_rows)
        if not div_rows and os.path.exists(raw_path):
            div_rows = list(csv.DictReader(open(raw_path, encoding="utf-8")))
        print(kind, len(div_rows))
        for d in div_rows:
            eiin = (d.get("EIIN_NO") or "").strip()
            if not eiin:
                continue
            if eiin in records:
                records[eiin][2].append(kind)
                continue
            records[eiin] = (kind, d, [kind])

    board = set()
    if not offline:
        r = get(BOARD_LIST, timeout=120)
        try:
            board = {x["eiin"] for x in r.json()["aaData"]} if r is not None else set()
        except (ValueError, KeyError):
            board = set()
        if board:  # keep only EIINs of Rajshahi-Division institutions (the board list also covers Rangpur Division)
            with open(os.path.join(rawdir, "rajshahi_board_eiin_list.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(board & set(records))) + "\n")
    elif os.path.exists(os.path.join(rawdir, "rajshahi_board_eiin_list.txt")):
        board = set(open(os.path.join(rawdir, "rajshahi_board_eiin_list.txt")).read().split())

    shared = Counter((d.get("EMAIL") or "").strip().lower() for _, d, _ in records.values())
    rows = []
    for eiin, (kind, d, kinds) in records.items():
        dist = norm_district(d.get("DISTRICT_NAME"))
        upz = norm_upazila(d.get("THANA_NAME"))
        notes = []
        if not upz:
            notes.append(f"thana '{d.get('THANA_NAME')}' not normalised")
        if upz in METRO_THANAS:
            notes.append("metropolitan thana of Rajshahi City, not an upazila")
        cat = category(kind, d)
        if kind == "school" and cat == "education.primary_school":
            notes.append("BANBEIS level 'Govt. Primary (pre to Eight)': primary school extended to class 8")
        if kind == "college" and (d.get("INSTITUTE_TYPE_NAME") or "") == "SCHOOL & COLLEGE":
            notes.append("school & college (classes 6-12); categorised as college")
        email = institutional_email(d.get("EMAIL"), eiin, shared)
        po = (d.get("POST_OFFICE_NAME") or "").strip()
        mpo = (d.get("IS_MPO") or "").strip()
        lvl = (d.get("EDUCATION_LEVEL_NAME") or "").strip()
        extra = {
            "eiin": eiin, "institute_type": d.get("INSTITUTE_TYPE_NAME"),
            "education_level": None if lvl in ("", "None") else lvl,
            "management": d.get("MANAGEMENT_NAME"), "mpo": None if mpo in ("", "None") else mpo,
            "for_whom": d.get("INSTITUTE_FOR_WHOM"), "geographical_position": d.get("GEOGRAPHICAL_POSITION_NAME"),
            "area_status": d.get("AREA_STATUS_NAME"), "post_office": None if po in ("", "None") else nfc(po),
            "thana_src": d.get("THANA_NAME"), "district_src": d.get("DISTRICT_NAME"),
            "banbeis_survey_year": d.get("BANBEIS_SURVEY_YEAR") or "2024", "banbeis_lists": kinds,
            "admin_unit": "metropolitan_thana" if upz in METRO_THANAS else "upazila",
        }
        if board and kind in ("school", "college"):
            extra["rajshahi_board_listed"] = eiin in board
        rows.append({
            "source_key": SOURCE_KEY, "source_id": f"eiin:{eiin}", "name_bn": "",
            "name_en": nfc(d.get("INSTITUTE_NAME")), "category_key": cat,
            "district_en": dist, "upazila_en": upz, "email": email,
            "ownership": OWN.get((d.get("MANAGEMENT_NAME") or "").strip(), ""),
            "extra_json": cj(extra), "source_url": DETAIL.format(eiin=eiin), "notes": "; ".join(notes),
        })
    rows.sort(key=lambda r: (r["district_en"] != "Rajshahi", r["district_en"], r["upazila_en"], r["category_key"], r["name_en"]))
    write_csv("places.csv", PLACE_COLS, rows)

    facts = []
    cnt = Counter((r["district_en"], r["upazila_en"], r["category_key"]) for r in rows)
    dcnt = Counter((r["district_en"], r["category_key"]) for r in rows)
    note = "count of institutions with EIIN in BANBEIS e-survey 2024 lists (deduplicated by EIIN)"
    for (dist, cat), n in sorted(dcnt.items()):
        facts.append({"entity_level": "district", "entity_name_en": dist, "district_en": dist, "upazila_en": "",
                      "fact": "institutions_" + cat.split(".")[1], "value": n, "unit": "institutions",
                      "basis": "count_of_listed_records", "year": 2024, "source_key": SOURCE_KEY,
                      "source_url": BANBEIS + "/pages/files/69199760933eb65569ddc637", "notes": note})
    for (dist, upz, cat), n in sorted(cnt.items()):
        facts.append({"entity_level": "thana" if upz in METRO_THANAS else "upazila", "entity_name_en": upz,
                      "district_en": dist, "upazila_en": upz, "fact": "institutions_" + cat.split(".")[1],
                      "value": n, "unit": "institutions", "basis": "count_of_listed_records", "year": 2024,
                      "source_key": SOURCE_KEY, "source_url": BANBEIS + "/pages/files/69199760933eb65569ddc637",
                      "notes": note})
    write_csv("facts.csv", FACT_COLS, facts)
    files = ["places.csv", "facts.csv"] + [f"raw/{f}" for f in sorted(os.listdir(rawdir))]
    update_manifest(files)
    print("places", len(rows), "facts", len(facts))
    print(Counter(r["category_key"] for r in rows))
    print(Counter(r["district_en"] for r in rows))


if __name__ == "__main__":
    main()
