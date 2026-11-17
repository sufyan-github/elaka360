#!/usr/bin/env python3
"""Fetch the UGC (University Grants Commission) university register and keep universities in Rajshahi Division.

stdlib + requests only. Usage: python3 fetch.py [--division rajshahi|rangpur] [--out DIR] [--offline]
(--offline rebuilds places.csv from raw/). Default: Rajshahi Division into this folder (DIVISIONS.md)."""
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

# --- other divisions: district / upazila names (BBS English spellings; latin keys as _key() makes them) -----------
# district -> [(standard English upazila, [spelling keys])]; looked up only inside the district that was found.
OTHER_UPAZILAS = {
    "rangpur": {
        "Panchagarh": [("Panchagarh Sadar", ["panchagarhsadar"]), ("Atwari", ["atwari", "atowari"]), ("Boda", ["boda"]),
                       ("Debiganj", ["debiganj", "debigonj"]), ("Tetulia", ["tetulia", "tentulia"])],
        "Dinajpur": [("Dinajpur Sadar", ["dinajpursadar"]), ("Birampur", ["birampur"]), ("Birganj", ["birganj", "birgonj"]),
                     ("Biral", ["biral", "birol"]), ("Bochaganj", ["bochaganj", "bochagonj"]), ("Chirirbandar", ["chirirbandar"]),
                     ("Phulbari", ["phulbari", "fulbari"]), ("Ghoraghat", ["ghoraghat"]), ("Hakimpur", ["hakimpur"]),
                     ("Kaharole", ["kaharole", "kaharol"]), ("Khansama", ["khansama"]), ("Nawabganj", ["nawabganj"]),
                     ("Parbatipur", ["parbatipur"])],
        "Lalmonirhat": [("Lalmonirhat Sadar", ["lalmonirhatsadar"]), ("Aditmari", ["aditmari"]), ("Hatibandha", ["hatibandha"]),
                        ("Kaliganj", ["kaliganj", "kaligonj"]), ("Patgram", ["patgram"])],
        "Nilphamari": [("Nilphamari Sadar", ["nilphamarisadar"]), ("Dimla", ["dimla"]), ("Domar", ["domar"]),
                       ("Jaldhaka", ["jaldhaka"]), ("Kishoreganj", ["kishoreganj", "kishorganj"]), ("Saidpur", ["saidpur", "syedpur"])],
        "Gaibandha": [("Gaibandha Sadar", ["gaibandhasadar"]), ("Phulchhari", ["phulchhari", "fulchhari", "phulchari"]),
                      ("Gobindaganj", ["gobindaganj", "gobindagonj"]), ("Palashbari", ["palashbari"]), ("Sadullapur", ["sadullapur"]),
                      ("Saghata", ["saghata"]), ("Sundarganj", ["sundarganj"])],
        "Thakurgaon": [("Thakurgaon Sadar", ["thakurgaonsadar"]), ("Baliadangi", ["baliadangi"]), ("Haripur", ["haripur"]),
                       ("Pirganj", ["pirganj"]), ("Ranisankail", ["ranisankail"])],
        "Rangpur": [("Rangpur Sadar", ["rangpursadar"]), ("Badarganj", ["badarganj"]), ("Gangachara", ["gangachara"]),
                    ("Kaunia", ["kaunia"]), ("Mithapukur", ["mithapukur"]), ("Pirgachha", ["pirgachha", "pirgacha"]),
                    ("Pirganj", ["pirganj"]), ("Taraganj", ["taraganj"])],
        "Kurigram": [("Kurigram Sadar", ["kurigramsadar"]), ("Bhurungamari", ["bhurungamari"]), ("Char Rajibpur", ["charrajibpur", "rajibpur"]),
                     ("Chilmari", ["chilmari"]), ("Phulbari", ["phulbari", "fulbari"]), ("Nageshwari", ["nageshwari", "nageswari"]),
                     ("Rajarhat", ["rajarhat"]), ("Raomari", ["raomari", "rowmari"]), ("Ulipur", ["ulipur"])],
    },
}

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
    if not m:  # first run for another division: start the manifest from the Rajshahi one's provenance fields
        m = {"key": SOURCE_KEY, "division": DIVISION, "kind": "ugc",
             "name": "UGC university register — universities in %s Division" % DIVISION.capitalize(),
             "organization": "University Grants Commission of Bangladesh (UGC)", "source_type": "government_portal",
             "trust_level": 4, "urls": ["https://www.ugc.gov.bd/universities"], "accessed": None, "publication_date": None,
             "license": None, "license_url": None, "attribution": "Source: University Grants Commission of Bangladesh (ugc.gov.bd)"}
    m["accessed"] = datetime.date.today().isoformat()
    m["files"] = {f: sha256(os.path.join(HERE, f)) for f in files if os.path.exists(os.path.join(HERE, f))}
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(m, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
# --- end output helpers -----------------------------------------------------------------------------------

# --- division selection (data/sources/DIVISIONS.md) ---------------------------------------------------------
import argparse
DIVISION_CODES = {"rajshahi": "raj", "rangpur": "rang", "dhaka": "dhk", "chattogram": "ctg", "khulna": "khl",
                  "barishal": "bar", "sylhet": "syl", "mymensingh": "mym"}


def division_setup(here, base_key, configured, extra_args=()):
    """Parse --division/--out -> (args, out_dir, source_key). Rajshahi (default) keeps this folder and key; another
    division writes to its own folder named per DIVISIONS.md and never touches the Rajshahi files."""
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    ap.add_argument("--division", default="rajshahi", choices=list(DIVISION_CODES))
    ap.add_argument("--out", help="output folder (default: this folder for rajshahi, the division's own folder otherwise)")
    for name, kw in extra_args:
        ap.add_argument(name, **kw)
    args = ap.parse_args()
    if args.division not in configured:
        ap.error("division %r is not configured in this collector yet (configured: %s)" % (args.division, ", ".join(configured)))
    here = os.path.abspath(str(here))
    folder = os.path.basename(here)
    if args.division == "rajshahi":
        name, key = folder, base_key
    else:
        code = DIVISION_CODES[args.division]
        name = folder.replace("_raj_", "_%s_" % code) if "_raj_" in folder else "%s_%s" % (folder, args.division)
        key = base_key.replace("_RAJ_", "_%s_" % code.upper()) if "_RAJ_" in base_key else "%s_%s" % (base_key, args.division.upper())
    out = os.path.abspath(args.out) if args.out else (here if args.division == "rajshahi" else os.path.join(os.path.dirname(here), name))
    if args.division != "rajshahi" and out == here:
        ap.error("refusing to write another division's output into the Rajshahi folder")
    os.makedirs(out, exist_ok=True)
    return args, out, key
# --- end division selection ---------------------------------------------------------------------------------

# --- UGC university register: universities located in Rajshahi Division (or --division) -------------------
import sys, html as _html
from collections import Counter

SOURCE_KEY = "UGC_UNIVERSITIES_RAJ_2026"   # Rajshahi; other divisions get their key from division_setup()
DIVISION = "rajshahi"
UGC = "https://www.ugc.gov.bd"
CATEGORIES = ["public-universities", "private-universities", "international-universities", "cbhe"]
OWNERSHIP = {"public-universities": "public", "private-universities": "private",
             "international-universities": "international", "cbhe": "cross_border"}
RAW = os.path.join(HERE, "raw", "ugc_universities_rajshahi_division.json")
DIST_RE = [("Rajshahi", r"rajshahi"), ("Natore", r"natore"), ("Naogaon", r"naogaon"),
           ("Chapainawabganj", r"chapai ?nawab ?g[ao]nj|nawabg[ao]nj"), ("Bogura", r"\bbogura\b|\bbogra\b"),
           ("Joypurhat", r"joypurhat|jaipurhat"), ("Pabna", r"\bpabna\b"), ("Sirajganj", r"sirajg[ao]nj")]
# district patterns per division (searched in the UGC address text, in this order)
DIST_RE_BY_DIV = {
    "rajshahi": DIST_RE,
    "rangpur": [("Rangpur", r"\brangpur\b"), ("Dinajpur", r"dinajpur"), ("Thakurgaon", r"thakurgaon|thakurgoan"),
                ("Panchagarh", r"panchagarh|panchagar\b"), ("Nilphamari", r"nilphamari|nilfamari"),
                ("Lalmonirhat", r"lalmonirhat"), ("Kurigram", r"kurigram"), ("Gaibandha", r"gaibandha")],
}
OFFICIAL_FIELDS = {"vice_chancellor", "pro_vice_chancellor", "treasurer", "registrar", "contact_person"}  # not kept
FREE_MAIL = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "ymail.com", "live.com"}


def page_props(url):
    r = get(url)
    if r is None or r.status_code != 200:
        print("FAILED", url, None if r is None else r.status_code)
        return None
    m = _re.search(r'data-page="([^"]+)"', r.text)
    return json.loads(_html.unescape(m.group(1)))["props"] if m else None


def find_district(text):
    t = (text or "").lower()
    if DIVISION != "rajshahi":
        # an address can name a district of another division too ('Rangpur Road, Gokul, Bogura-5800'): the district
        # mentioned last wins, and it must belong to this division
        hits = [(m.start(), name) for div, pats in DIST_RE_BY_DIV.items() for name, rx in pats for m in _re.finditer(rx, t)]
        if not hits:
            return ""
        last = max(hits)[1]
        return last if any(last == n for n, _ in DIST_RE) else ""
    for name, rx in DIST_RE:
        if _re.search(rx, t):
            return name
    return ""


def find_upazila(addr, district=""):
    if DIVISION != "rajshahi":
        words = [w for w in _re.split(r"[^a-z]+", (addr or "").lower()) if w]
        grams = set(words) | {a + b for a, b in zip(words, words[1:])}
        for en, keys in OTHER_UPAZILAS[DIVISION].get(district, []):
            if grams & set(keys):
                return en
        return ""
    words = [w for w in _re.split(r"[^a-z]+", (addr or "").lower()) if w]
    grams = set(words) | {a + b for a, b in zip(words, words[1:])}
    extra = {"shahzadpur": "Shahjadpur"}
    for g in grams:
        if g in extra:
            return extra[g]
        u = norm_upazila(g)
        if u and g not in ("sherpur", "faridpur", "durgapur", "shibganj"):  # ambiguous across districts
            return u
    return ""


def clean_emails(raw, website):
    stem = _re.sub(r"^(https?://)?(www\.)?", "", (website or "").lower()).split(".")[0]
    out = []
    for e in _re.split(r"[,;\s]+", raw or ""):
        e = e.strip().strip(".").lower()
        if not _re.match(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", e):
            continue
        lp, dom = e.split("@", 1)
        site = ".".join(_re.sub(r"^(https?://)?(www\.)?", "", (website or "").lower()).split("/")[0].split(".")[-3:])
        if dom in FREE_MAIL:
            if not (any(t in lp for t in ("registrar", "info", "univ", "admission")) or (stem and stem in lp)):
                continue  # personal-looking free-mail address
        elif not (site and (dom.endswith(site) or site.endswith(dom))):
            continue  # address on a third-party domain (e.g. a sponsor's), not the university's own
        if e not in out:
            out.append(e)
    return "; ".join(out)


def clean_phones(raw):
    """Keep landline / hotline numbers (office lines); drop mobile numbers (01x…), which may be personal."""
    out = []
    for p in _re.split(r"[,;/]", raw or ""):
        p = _re.sub(r"\([^)]*[A-Za-z][^)]*\)|ext\.?:?.*$", "", p, flags=_re.I).strip()
        digits = _re.sub(r"\D", "", p)
        if len(digits) < 6:
            continue
        local = digits[3:] if digits.startswith("880") else digits
        local = local if local.startswith("0") else "0" + local
        if local.startswith("01"):
            continue
        if p not in out:
            out.append(p)
    return "; ".join(out)


def main():
    global HERE, RAW, SOURCE_KEY, DIST_RE, DIVISION
    args, HERE, SOURCE_KEY = division_setup(HERE, SOURCE_KEY, ["rajshahi", "rangpur"],
                                            [("--offline", dict(action="store_true", help="rebuild places.csv from raw/"))])
    DIVISION, DIST_RE = args.division, DIST_RE_BY_DIV[args.division]
    RAW = os.path.join(HERE, "raw", "ugc_universities_%s_division.json" % DIVISION)
    head = DIST_RE[0][0]  # the division's head district sorts first
    offline = args.offline
    unis = []
    if not offline:
        for cat in CATEGORIES:
            props = page_props(f"{UGC}/universities/{cat}")
            for u in (props or {}).get("universities") or []:
                det = (page_props(f"{UGC}/university/{u['slug']}") or {}).get("university") or {}
                det = {k: v for k, v in det.items() if k not in OFFICIAL_FIELDS}
                unis.append({"category": cat, "list": {k: u.get(k) for k in ("id", "name_en", "name_bn", "slug", "website", "marker")},
                             "detail": det})
    keep = []
    for x in unis:
        d = x["detail"]
        addr = " | ".join(v for v in [d.get("present_campus"), d.get("permanent_campus"), d.get("address")] if v)
        dist = find_district(addr) or ""
        basis = "address"
        if not dist and not addr:
            dist = find_district(x["list"]["name_en"])
            basis = "name"
        if dist:
            x["_district"], x["_basis"] = dist, basis
            keep.append(x)
    if keep:
        os.makedirs(os.path.dirname(RAW), exist_ok=True)
        with open(RAW, "w", encoding="utf-8") as f:
            json.dump(keep, f, ensure_ascii=False, indent=1)
    elif os.path.exists(RAW):
        keep = json.load(open(RAW, encoding="utf-8"))

    rows = []
    for x in keep:
        d, l = x["detail"], x["list"]
        addr = nfc(d.get("present_campus") or d.get("permanent_campus") or d.get("address"))
        notes = []
        if x["_basis"] == "name":
            notes.append("UGC gives no address; district taken from the university's name")
        if d.get("present_campus") and d.get("permanent_campus") and nfc(d["present_campus"]) != nfc(d["permanent_campus"]):
            notes.append("present and permanent campus differ (address = present campus)")
        if l.get("marker"):
            notes.append(f"UGC list marks this university with '{l['marker']}' (see UGC page legend)")
        pc = _re.findall(r"\b(\d{4})\b", addr)
        upz = find_upazila(addr, x["_district"])
        web = nfc(d.get("website") or l.get("website") or "")
        web = web.split(",")[0].strip()
        if web and not web.startswith("http"):
            web = "https://" + web.rstrip(".")
        rows.append({
            "source_key": SOURCE_KEY, "source_id": f"ugc:{l['slug']}", "name_bn": nfc(d.get("name_bn") or l.get("name_bn")),
            "name_en": nfc(d.get("name_en") or l["name_en"]), "category_key": "education.university",
            "address": addr, "district_en": x["_district"], "upazila_en": upz,
            "phone": clean_phones(d.get("telephone_mobile")), "website": web,
            "email": clean_emails(d.get("email"), web), "ownership": OWNERSHIP.get(x["category"], ""),
            "extra_json": cj({"ugc_category": x["category"], "year_of_establishment": d.get("year_of_establishment"),
                              "permanent_campus": nfc(d.get("permanent_campus")), "present_campus": nfc(d.get("present_campus")),
                              "postcode": pc[-1] if pc else None, "fax": nfc(d.get("fax")), "ugc_id": l.get("id")}),
            "source_url": f"{UGC}/university/{l['slug']}", "notes": "; ".join(notes),
        })
    rows.sort(key=lambda r: (r["district_en"] != head, r["district_en"], r["ownership"], r["name_en"]))
    write_csv("places.csv", PLACE_COLS, rows)
    update_manifest(["places.csv", "raw/" + os.path.basename(RAW)])
    print("places", len(rows), Counter(r["district_en"] for r in rows), Counter(r["ownership"] for r in rows))


if __name__ == "__main__":
    main()
