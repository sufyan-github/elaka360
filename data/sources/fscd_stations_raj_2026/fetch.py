#!/usr/bin/env python3
"""Fetch Rajshahi-Division fire station & office numbers from fireservice.gov.bd (FSCD_STATIONS_RAJ_2026).

Usage: python3 fetch.py [--division rajshahi|rangpur|dhaka|chattogram|khulna|barishal|sylhet|mymensingh] [--out DIR]   (default: Rajshahi into this folder; DIVISIONS.md)"""
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

# --- common utilities (stdlib only) -------------------------------------------------------------------
import csv, hashlib, html as _html, json, re, shutil, subprocess, sys, unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
PLACE_COLS = ["source_key", "source_id", "name_bn", "name_en", "category_key", "lat", "lon", "address", "district_en",
              "upazila_en", "phone", "website", "email", "opening_hours", "operator", "ownership", "extra_json",
              "source_url", "notes"]
FACT_COLS = ["entity_level", "entity_name_en", "district_en", "upazila_en", "code", "fact", "value", "unit", "basis",
             "year", "source_key", "source_url", "notes"]
_BN = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def nfc(s):
    return unicodedata.normalize("NFC", s or "").strip()


def asc(s):
    """Bangla digits -> ASCII digits."""
    return (s or "").translate(_BN)


def clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = _html.unescape(s).replace("\xa0", " ")
    return nfc(re.sub(r"\s+", " ", s))


def tables(html_text):
    """All <table>s of a page as lists of rows (lists of cleaned cell strings)."""
    out = []
    for t in re.findall(r"<table\b.*?</table>", html_text, flags=re.S | re.I):
        rows = []
        for tr in re.findall(r"<tr\b.*?</tr>", t, flags=re.S | re.I):
            cells = [clean(c) for c in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", tr, flags=re.S | re.I)]
            if any(cells):
                rows.append(cells)
        out.append(rows)
    return out


def content_text(html_text):
    """Main content block of a national-portal (v2) page as text lines."""
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html_text, flags=re.S | re.I)
    s = re.sub(r"</(tr|p|div|li|h\d)>|<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</t[dh]>", " | ", s, flags=re.I)
    s = _html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ")
    lines = [nfc(re.sub(r"[ \t]+", " ", l)) for l in s.splitlines()]
    lines = [l for l in lines if l]
    try:
        a = next(i for i, l in enumerate(lines) if l.startswith("কন্টেন্ট:"))
        b = next(i for i, l in enumerate(lines) if i > a and "এই কনটেন্টটি শেয়ার" in l)
        return lines[a + 1:b]
    except StopIteration:
        return lines


def phone_norm(s):
    """ASCII digits, keep the source's grouping; several numbers joined with '; '."""
    s = asc(s)
    # (a single space between two complete numbers also separates them: Barishal control room '০১৯৮৩৮৮৬৬৭৭ ০২৪৭৮৮৩২৪৯৯')
    parts = [p.strip(" ,;/") for p in re.split(r"[,;/]|\s{2,}|(?<=\d{11})\s(?=0\d{9})", s)]
    return "; ".join(p for p in parts if re.search(r"\d{4}", p))


def save_raw(name, content):
    RAW.mkdir(exist_ok=True)
    p = RAW / name
    p.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    return p


def pdftotext(path, first=None, last=None, layout=True):
    """Text of a PDF via poppler's pdftotext if installed (optional dependency); None otherwise."""
    exe = shutil.which("pdftotext")
    if not exe:
        return None
    cmd = [exe] + (["-layout"] if layout else []) + (["-f", str(first)] if first else []) + (["-l", str(last)] if last else []) + [str(path), "-"]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=300).stdout
    except Exception:
        return None


def write_csv(name, cols, rows):
    with open(HERE / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="raise")
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r.get(c)) for c in cols})
    print(f"wrote {name}: {len(rows)} rows")


def write_manifest(meta, files):
    hashes = {}
    for rel in files:
        p = HERE / rel
        if p.exists():
            hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    meta = dict(meta, files=hashes)
    (HERE / "SOURCE.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote SOURCE.json")


def xj(d):
    d = {k: v for k, v in d.items() if v not in (None, "", [], {})}
    return json.dumps(d, ensure_ascii=False, separators=(",", ":")) if d else ""
# --- end common utilities -----------------------------------------------------------------------------

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

# --- FSCD_STATIONS_RAJ_2026 -----------------------------------------------------------------------------
KEY = "FSCD_STATIONS_RAJ_2026"
BASE = "https://fireservice.gov.bd"
URL_ALL_NUMBERS = BASE + "/pages/static-pages/6922dcc6933eb65569e11fd1"      # "সকল ফায়ার স্টেশনের নম্বর" (per-division PDFs)
URL_DIVISION = BASE + "/pages/static-pages/6922e13c933eb65569e2b07c"         # রাজশাহী বিভাগ (district offices)
URL_CONTROL = BASE + "/pages/static-pages/6922e013933eb65569e25586"          # বিভাগীয় নিয়ন্ত্রণ কক্ষ
URL_COUNTS = BASE + "/pages/static-pages/6922e0b9933eb65569e28555"           # চালুকৃত ফায়ার স্টেশন ও গাড়ী/পাম্পের সংখ্যা
URL_DIV_PORTAL = "https://fireservice.rajshahi.gov.bd/pages/static-pages/697f93bf35ce18e1c06be88b"  # Rajshahi divisional FSCD portal
PDF_FALLBACK = ("https://objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/n/axvjbnqprylg/b/V2Ministry/o/"
                "office-fireservice/2026/7/3a7a810c-0608-4597-98b2-bdc6aab3e6c9.pdf")

# The Rajshahi-division PDF ("ফায়ার সার্ভিস ও সিভিল ডিফেন্স, রাজশাহী বিভাগ, রাজশাহী", Word export dated 2026-08-11) has a
# broken Bangla text layer (glyph mapping), so names were transcribed by hand from the rendered PDF pages and are keyed
# here by phone number, which the text layer carries correctly. fetch.py re-checks every number against the live PDF.
# (district_en, name_bn as printed, phone as printed, kind, upazila_en if the station is named after an upazila)
T = [
    ("Rajshahi", "উপ-পরিচালক, রাজশাহী", "01901-020120", "office", ""),
    ("Rajshahi", "সহকারী পরিচালক,রাজশাহী", "01901-020122", "office", ""),
    ("Rajshahi", "উপসহকারী পরিচালক,রাজশাহী", "01901-022204", "office", ""),
    ("Rajshahi", "রাজশাহী ফায়ার স্টেশন", "01901-022227", "station", ""),
    ("Rajshahi", "রাজশাহী উত্তর ফায়ার স্টেশন", "01901-022231", "station", ""),
    ("Rajshahi", "বিশ্ববিদ্যালয় ফায়ার স্টেশন", "01901-022229", "station", ""),
    ("Rajshahi", "নওহাটা ফায়ার স্টেশন", "01901-022247", "station", ""),
    ("Rajshahi", "পুঠিয়া ফায়ার স্টেশন", "01901-022249", "station", "Puthia"),
    ("Rajshahi", "চারঘাট ফায়ার স্টেশন", "01901-022237", "station", "Charghat"),
    ("Rajshahi", "গোদাগাড়ী ফায়ার স্টেশন", "01901-022241", "station", "Godagari"),
    ("Rajshahi", "তানোর ফায়ার স্টেশন", "01901-022251", "station", "Tanore"),
    ("Rajshahi", "বাগমারা ফায়ার স্টেশন", "01901-022235", "station", "Bagmara"),
    ("Rajshahi", "দুর্গাপুর ফায়ার স্টেশন", "01901-022239", "station", "Durgapur"),
    ("Rajshahi", "বাঘা ফায়ার স্টেশন", "01901-022253", "station", "Bagha"),
    ("Rajshahi", "মোহনপুর ফায়ার স্টেশন", "01901-022245", "station", "Mohanpur"),
    ("Chapainawabganj", "উপসহকারী পরিচালক, চাঁপাইনবাবগঞ্জ", "01901-022205", "office", ""),
    ("Chapainawabganj", "চাঁপাইনবাবগঞ্জ ফায়ার স্টেশন", "01901-022309", "station", "Chapainawabganj Sadar"),
    ("Chapainawabganj", "শিবগঞ্জ ফায়ার স্টেশন", "01901-022317", "station", "Shibganj"),
    ("Chapainawabganj", "গোমস্তাপুর ফায়ার স্টেশন", "01901-022313", "station", "Gomastapur"),
    ("Chapainawabganj", "ভোলাহাট ফায়ার স্টেশন", "01901-022311", "station", "Bholahat"),
    ("Chapainawabganj", "নাচোল ফায়ার স্টেশন", "01901-022315", "station", "Nachole"),
    ("Natore", "উপসহকারী পরিচালক, নাটোর", "01901-022207", "office", ""),
    ("Natore", "নাটোর ফায়ার স্টেশন", "01901-022283", "station", "Natore Sadar"),
    ("Natore", "লালপুর ফায়ার স্টেশন", "01901-022293", "station", "Lalpur"),
    ("Natore", "দয়রামপুর ফায়ার স্টেশন", "01901-022285", "station", ""),
    ("Natore", "গুরুদাশপুর ফায়ার স্টেশন", "01901-022289", "station", "Gurudaspur"),
    ("Natore", "বনপাড়া ফায়ার স্টেশন", "01901-022287", "station", ""),
    ("Natore", "সিংড়া ফায়ার স্টেশন", "01901-022295", "station", "Singra"),
    ("Natore", "নলডাঙ্গা ফায়ার স্টেশন", "01901-022297", "station", "Naldanga"),
    ("Naogaon", "উপসহকারী পরিচালক, নওগাঁ", "01901-022206", "office", ""),
    ("Naogaon", "নওগাঁ ফায়ার স্টেশন", "01901-022255", "station", "Naogaon Sadar"),
    ("Naogaon", "পত্নীতলা ফায়ার স্টেশন", "01901-022269", "station", "Patnitala"),
    ("Naogaon", "আত্রাই ফায়ার স্টেশন", "01901-022263", "station", "Atrai"),
    ("Naogaon", "নিয়ামতপুর ফায়ার স্টেশন", "01901-022267", "station", "Niamatpur"),
    ("Naogaon", "মহাদেবপুর ফায়ার স্টেশন", "01901-022259", "station", "Mahadebpur"),
    ("Naogaon", "রাণীনগর ফায়ার স্টেশন", "01901-022271", "station", "Raninagar"),
    ("Naogaon", "মান্দা ফায়ার স্টেশন", "01901-022265", "station", "Manda"),
    ("Naogaon", "বদলগাছি ফায়ার স্টেশন", "01901-022277", "station", "Badalgachhi"),
    ("Naogaon", "পোরশা ফায়ার স্টেশন", "01901-022281", "station", "Porsha"),
    ("Naogaon", "ধামুইরহাট ফায়ার স্টেশন", "01901-022275", "station", "Dhamoirhat"),
    ("Naogaon", "সাপাহার ফায়ার স্টেশন", "01901-022273", "station", "Sapahar"),
    ("Bogura", "সহকারী পরিচালক, বগুড়া", "01901-020124", "office", ""),
    ("Bogura", "উপসহকারী পরিচালক, বগুড়া", "01901-022211", "office", ""),
    ("Bogura", "বগুড়া ফায়ার স্টেশন", "01901-022381", "station", "Bogura Sadar"),
    ("Bogura", "সোনাতলা ফায়ার স্টেশন", "01901-022411", "station", "Sonatala"),
    ("Bogura", "শেরপুর ফায়ার স্টেশন", "01901-022405", "station", "Sherpur"),
    ("Bogura", "ধুনট ফায়ার স্টেশন", "01901-022391", "station", "Dhunat"),
    ("Bogura", "সারিয়াকান্দি ফায়ার স্টেশন", "01901-022403", "station", "Sariakandi"),
    ("Bogura", "গাবতলী ফায়ার স্টেশন", "01901-022395", "station", "Gabtali"),
    ("Bogura", "শিবগঞ্জ ফায়ার স্টেশন", "01901-022407", "station", "Shibganj"),
    ("Bogura", "কাহালু ফায়ার স্টেশন", "01901-022399", "station", "Kahaloo"),
    ("Bogura", "নন্দীগ্রাম ফায়ার স্টেশন", "01901-022401", "station", "Nandigram"),
    ("Bogura", "আদমদিঘী ফায়ার স্টেশন", "01901-022387", "station", "Adamdighi"),
    ("Bogura", "দুপচাঁচিয়া ফায়ার স্টেশন", "01901-022393", "station", "Dhupchanchia"),
    ("Bogura", "শাহজাহানপুর ফায়ার স্টেশন", "01901-022413", "station", "Shajahanpur"),
    ("Joypurhat", "উপসহকারী পরিচালক, জয়পুরহাট", "01901-022208", "office", ""),
    ("Joypurhat", "জয়পুরহাট ফায়ার স্টেশন", "01901-022299", "station", "Joypurhat Sadar"),
    ("Joypurhat", "আক্কেলপুর ফায়ার স্টেশন", "01901-022301", "station", "Akkelpur"),
    ("Joypurhat", "পাঁচবিবি ফায়ার স্টেশন", "01901-022305", "station", "Panchbibi"),
    ("Joypurhat", "কালাই ফায়ার স্টেশন", "01901-022307", "station", "Kalai"),
    ("Joypurhat", "ক্ষেতলাল ফায়ার স্টেশন", "01901-022303", "station", "Khetlal"),
    ("Pabna", "সহকারী পরিচালক, পাবনা", "01901-020126", "office", ""),
    ("Pabna", "উপসহকারী পরিচালক, পাবনা", "01901-022209", "office", ""),
    ("Pabna", "পাবনা ফায়ার স্টেশন", "01901-022325", "station", "Pabna Sadar"),
    ("Pabna", "ঈশ্বরদী ফায়ার স্টেশন", "01901-022335", "station", "Ishwardi"),
    ("Pabna", "বেড়া ফায়ার স্টেশন", "01901-022329", "station", "Bera"),
    ("Pabna", "চাটমোহর ফায়ার স্টেশন", "01901-022331", "station", "Chatmohar"),
    ("Pabna", "সুজানগর ফায়ার স্টেশন", "01901-022349", "station", "Sujanagar"),
    ("Pabna", "কাশিনাথপুর ফায়ার স্টেশন", "01901-022345", "station", ""),
    ("Pabna", "ঈশ্বরদী ইপিজেড ফায়ার স্টেশন", "01901-022337", "station", "Ishwardi"),
    ("Pabna", "সাথিয়া ফায়ার স্টেশন", "01901-022343", "station", "Santhia"),
    ("Pabna", "ফরিদপুর ফায়ার স্টেশন", "01901-022333", "station", "Faridpur"),
    ("Pabna", "আটঘড়িয়া ফায়ার স্টেশন", "01901-022327", "station", "Atgharia"),
    ("Pabna", "গ্রীনসিটি ফায়ার স্টেশন", "01901-022339", "station", ""),
    ("Pabna", "রুপপুর মর্ডান ফায়ার স্টেশন", "01901-022340", "station", ""),
    ("Pabna", "রুপপুর ফায়ার স্টেশন", "01901-022341", "station", ""),
    ("Sirajganj", "উপসহকারী পরিচালক, সিরাজগঞ্জ", "01901-022210", "office", ""),
    ("Sirajganj", "সিরাজগঞ্জ ফায়ার স্টেশন", "01901022353", "station", "Sirajganj Sadar"),
    ("Sirajganj", "বাঘাবাড়ী নদী ফায়ার স্টেশন", "01901-022371", "station", ""),
    ("Sirajganj", "উল্লাপাড়া ফায়ার স্টেশন", "01901-022375", "station", "Ullahpara"),
    ("Sirajganj", "শাহজাদপুর ফায়ার স্টেশন", "01901-022369", "station", "Shahjadpur"),
    ("Sirajganj", "কাজিপুর ফায়ার স্টেশন", "01901-022363", "station", "Kazipur"),
    ("Sirajganj", "রায়গঞ্জ ফায়ার স্টেশন", "01901-022365", "station", "Raiganj"),
    ("Sirajganj", "বেলকুচি ফায়ার স্টেশন", "01901-022357", "station", "Belkuchi"),
    ("Sirajganj", "কামারখন্দ ফায়ার স্টেশন", "01901-022359", "station", "Kamarkhanda"),
    ("Sirajganj", "তাড়াশ ফায়ার স্টেশন", "01901-022373", "station", "Tarash"),
    ("Sirajganj", "নর্থ ওয়েস্ট ফায়ার স্টেশন", "01313-425824", "station", ""),
]
# Rangpur-division PDF ("ফায়ার সার্ভিস ও সিভিল ডিফেন্স, রংপুর বিভাগ, রংপুর", Word export dated 2026-08-11): same broken text
# layer; names transcribed by hand from the rendered pages (3 pages, 8 district tables), in PDF order.
T_RANGPUR = [
    ("Rangpur", "উপপরিচালক,রংপুর", "01901-020140", "office", ""),
    ("Rangpur", "সহকারী পরিচালক,রংপুর", "01901-020142", "office", ""),
    ("Rangpur", "উপসহকারী পরিচালক,রংপুর", "01901-023203", "office", ""),
    ("Rangpur", "রংপুর ফায়ার স্টেশন", "01901-023231", "station", ""),
    ("Rangpur", "হারাগাছ ফায়ার স্টেশন", "01901-023241", "station", ""),
    ("Rangpur", "বদরগঞ্জ ফায়ার স্টেশন", "01901-023235", "station", "Badarganj"),
    ("Rangpur", "কাউনিয়া ফায়ার স্টেশন", "01901-023239", "station", "Kaunia"),
    ("Rangpur", "মিঠাপুকুর ফায়ার স্টেশন", "01901-023243", "station", "Mithapukur"),
    ("Rangpur", "পীরগাছা ফায়ার স্টেশন", "01901-023245", "station", "Pirgachha"),
    ("Rangpur", "পীরগঞ্জ ফায়ার স্টেশন", "01901-023247", "station", "Pirganj"),
    ("Rangpur", "তারাগঞ্জ ফায়ার স্টেশন", "01901-023249", "station", "Taraganj"),
    ("Rangpur", "গংগাচড়া ফায়ার স্টেশন", "01901-023237", "station", "Gangachara"),
    ("Gaibandha", "উপসহকারী পরিচালক,গাইবান্ধা", "01901-023204", "office", ""),
    ("Gaibandha", "গাইবান্ধা ফায়ার স্টেশন", "01901-023337", "station", ""),
    ("Gaibandha", "গোবিন্দগঞ্জ ফায়ার স্টেশন", "01901-023325", "station", "Gobindaganj"),
    ("Gaibandha", "ফুলছড়ী ফায়ার স্টেশন", "01901-023333", "station", "Phulchhari"),
    ("Gaibandha", "সাঘাটা ফায়ার স্টেশন", "01901-023332", "station", "Saghata"),
    ("Gaibandha", "সুন্দরগঞ্জ ফায়ার স্টেশন", "01901-023327", "station", "Sundarganj"),
    ("Gaibandha", "সাদুল্লাপুর ফায়ার স্টেশন", "01901-023335", "station", "Sadullapur"),
    ("Gaibandha", "পলাশবাড়ী ফায়ার স্টেশন", "01901-023329", "station", "Palashbari"),
    ("Kurigram", "উপসহকারী পরিচালক,কুড়িগ্রাম", "01901-023205", "office", ""),
    ("Kurigram", "কুড়িগ্রাম ফায়ার স্টেশন", "01901-023337", "station", ""),
    ("Kurigram", "উলিপুর ফায়ার স্টেশন", "01901-023341", "station", "Ulipur"),
    ("Kurigram", "নাগেশ্বরী ফায়ার স্টেশন", "01901-023343", "station", "Nageshwari"),
    ("Kurigram", "চিলমারী ফায়ার স্টেশন", "01901-023345", "station", "Chilmari"),
    ("Kurigram", "কর্তিমারী ফায়ার স্টেশন", "01901-023347", "station", ""),
    ("Kurigram", "রাজারহাট ফায়ার স্টেশন", "01901-023349", "station", "Rajarhat"),
    ("Kurigram", "ফুলবাড়ী ফায়ার স্টেশন", "01723-976767", "station", "Phulbari"),
    ("Kurigram", "রাজিবপুর ফায়ার স্টেশন", "01901-023353", "station", "Char Rajibpur"),
    ("Lalmonirhat", "উপসহকারী পরিচালক,লালমনিরহাট", "01901-023206", "office", ""),
    ("Lalmonirhat", "লালমনিরহাট ফায়ার স্টেশন", "01901-023359", "station", ""),
    ("Lalmonirhat", "পাটগ্রাম ফায়ার স্টেশন", "01901-023361", "station", "Patgram"),
    ("Lalmonirhat", "হাতিবান্ধা ফায়ার স্টেশন", "01901-023367", "station", "Hatibandha"),
    ("Lalmonirhat", "কালীগঞ্জ ফায়ার স্টেশন", "01901-023365", "station", "Kaliganj"),
    ("Lalmonirhat", "আদিতমারী ফায়ার স্টেশন", "01901-023369", "station", "Aditmari"),
    ("Nilphamari", "উপসহকারী পরিচালক,নীলফামারী", "01901-023207", "office", ""),
    ("Nilphamari", "নীলফামারী ফায়ার স্টেশন", "01901-023307", "station", ""),
    ("Nilphamari", "সৈয়দপুর ফায়ার স্টেশন", "01901-023311", "station", "Saidpur"),
    ("Nilphamari", "উত্তরা ইপিজেড ফায়ার স্টেশন", "01901-023309", "station", ""),
    ("Nilphamari", "কিশোরগঞ্জ ফায়ার স্টেশন", "01901-023319", "station", "Kishoreganj"),
    ("Nilphamari", "জলঢাকা ফায়ার স্টেশন", "01901-023317", "station", "Jaldhaka"),
    ("Nilphamari", "ডোমার ফায়ার স্টেশন", "01901-023313", "station", "Domar"),
    ("Nilphamari", "ডিমলা ফায়ার স্টেশন", "01901-023321", "station", "Dimla"),
    ("Nilphamari", "চিলাহাটি ফায়ার স্টেশন", "01901-023315", "station", ""),
    ("Dinajpur", "সহকারী পরিচালক,দিনাজপুর", "01901-020144", "office", ""),
    ("Dinajpur", "উপসহকারী পরিচালক,দিনাজপুর", "01901-023210", "office", ""),
    ("Dinajpur", "দিনাজপুর ফায়ার স্টেশন", "01901-023251", "station", ""),
    ("Dinajpur", "পার্বতীপুর ফায়ার স্টেশন", "01901-023259", "station", "Parbatipur"),
    ("Dinajpur", "ফুলবাড়ী ফায়ার স্টেশন", "01901-023261", "station", "Phulbari"),
    ("Dinajpur", "বিরামপুর ফায়ার স্টেশন", "01901-023269", "station", "Birampur"),
    ("Dinajpur", "সেতাবগঞ্জ ফায়ার স্টেশন", "01901-023263", "station", ""),
    ("Dinajpur", "হিলি ফায়ার স্টেশন", "01901-023273", "station", ""),
    ("Dinajpur", "বীরগঞ্জ ফায়ার স্টেশন", "01901-023279", "station", "Birganj"),
    ("Dinajpur", "চিরিরবন্দর ফায়ার স্টেশন", "01901-023265", "station", "Chirirbandar"),
    ("Dinajpur", "খানসামা ফায়ার স্টেশন", "01901-023277", "station", "Khansama"),
    ("Dinajpur", "ঘোড়াঘাট ফায়ার স্টেশন", "01901-023271", "station", "Ghoraghat"),
    ("Dinajpur", "নবাবগঞ্জ ফায়ার স্টেশন", "01901-023281", "station", "Nawabganj"),
    ("Dinajpur", "কাহারোল ফায়ার স্টেশন", "01901-023275", "station", "Kaharole"),
    ("Dinajpur", "বিরল ফায়ার স্টেশন", "01901-023283", "station", "Biral"),
    ("Thakurgaon", "উপসহকারী পরিচালক,ঠাকুরগাঁও", "01901-023208", "office", ""),
    ("Thakurgaon", "ঠাকুরগাঁও ফায়ার স্টেশন", "01901-023285", "station", ""),
    ("Thakurgaon", "পীরগঞ্জ ফায়ার স্টেশন", "01901-023291", "station", "Pirganj"),
    ("Thakurgaon", "রানীশংকৈল ফায়ার স্টেশন", "01901-023295", "station", "Ranisankail"),
    ("Thakurgaon", "বালিয়াডাঙ্গী ফায়ার স্টেশন", "01901-023287", "station", "Baliadangi"),
    ("Thakurgaon", "হরিপুর ফায়ার স্টেশন", "01901-023289", "station", "Haripur"),
    ("Panchagarh", "উপসহকারী পরিচালক,পঞ্চগড়", "01901-023209", "office", ""),
    ("Panchagarh", "পঞ্চগড় ফায়ার স্টেশন", "01901-023297", "station", ""),
    ("Panchagarh", "তেতুলিয়া ফায়ার স্টেশন", "01901-023299", "station", "Tetulia"),
    ("Panchagarh", "বোদা ফায়ার স্টেশন", "01901-023301", "station", "Boda"),
    ("Panchagarh", "দেবীগঞ্জ ফায়ার স্টেশন", "01901-023303", "station", "Debiganj"),
    ("Panchagarh", "আটোয়ারী ফায়ার স্টেশন", "01901-023305", "station", "Atwari"),
]
# Remarks on single rows of the Rangpur transcription (keyed by name as transcribed)
T_NOTES = {
    "কর্তিমারী ফায়ার স্টেশন": "name read from the rendered PDF, where the conjunct is hard to read (may be printed 'কত্তিমারী'); upazila not inferred",
    "গাইবান্ধা ফায়ার স্টেশন": "the PDF prints the same number (01901-023337) for Gaibandha and Kurigram fire stations",
    "কুড়িগ্রাম ফায়ার স্টেশন": "the PDF prints the same number (01901-023337) for Gaibandha and Kurigram fire stations",
    "ফুলবাড়ী ফায়ার স্টেশন|01723-976767": "number printed in the official list is outside the FSCD 01901 series",
    "সাঘাটা ফায়ার স্টেশন": "number as printed (01901-023332)",
}
# Dhaka-division PDF ("ফায়ার সার্ভিস ও সিভিল ডিফেন্স, ঢাকা বিভাগ, ঢাকা", Word export dated 2026-08-11, 5 pages, 13 district
# tables): same broken text layer; names transcribed by hand from the rendered pages, in PDF order. The PDF prints the
# mobile numbers without a hyphen; they are written here as 01901-0xxxxx. Kalyanpur (serials 32 and 35, same number) once.
T_DHAKA = [
    ("Dhaka", "উপপরিচালক, ঢাকা বিভাগ", "01901-020100", "office", ""),
    ("Dhaka", "সহকারী পরিচালক, ঢাকা", "01901-020102", "office", ""),
    ("Dhaka", "উপসহকারী পরিচালক, জোন-১", "01901-020704", "office", ""),
    ("Dhaka", "উপসহকারী পরিচালক, জোন-২", "01901-020705", "office", ""),
    ("Dhaka", "উপসহকারী পরিচালক, জোন-৩", "01901-020706", "office", ""),
    ("Dhaka", "উপসহকারী পরিচালক, জোন-৪", "01901-020707", "office", ""),
    ("Dhaka", "উপসহকারী পরিচালক, জোন-৫", "01901-020708", "office", ""),
    ("Dhaka", "সিদ্দিকবাজার ফায়ার স্টেশন", "01901-020748", "station", ""),
    ("Dhaka", "সদরঘাট ফায়ার স্টেশন", "01901-020750", "station", ""),
    ("Dhaka", "সদরঘাট নদী ফায়ার স্টেশন", "01901-020752", "station", ""),
    ("Dhaka", "পোস্তগোলা ফায়ার স্টেশন", "01901-020756", "station", ""),
    ("Dhaka", "লালবাগ ফায়ার স্টেশন", "01901-020770", "station", ""),
    ("Dhaka", "পলাশী ব্যারাক ফায়ার স্টেশন", "01901-020774", "station", ""),
    ("Dhaka", "খিলগাঁও ফায়ার স্টেশন", "01901-020760", "station", ""),
    ("Dhaka", "তেজগাঁও ফায়ার স্টেশন", "01901-020758", "station", ""),
    ("Dhaka", "মোহাম্মদপুর ফায়ার স্টেশন", "01901-020762", "station", ""),
    ("Dhaka", "মিরপুর ফায়ার স্টেশন", "01901-020764", "station", ""),
    ("Dhaka", "কুর্মিটোলা ফায়ার স্টেশন", "01901-020768", "station", ""),
    ("Dhaka", "উত্তরা ফায়ার স্টেশন", "01901-020782", "station", ""),
    ("Dhaka", "হযরত শাহজালাল আন্তর্জাতিক বিমান বন্দর অস্থায়ী ফায়ার স্টেশন", "01901-020041", "station", ""),
    ("Dhaka", "ডিইপিজেড ফায়ার স্টেশন", "01901-020822", "station", ""),
    ("Dhaka", "ডেমরা ফায়ার স্টেশন", "01901-020778", "station", ""),
    ("Dhaka", "বারিধারা ফায়ার স্টেশন", "01901-020780", "station", ""),
    ("Dhaka", "সাভার ফায়ার স্টেশন", "01901-020820", "station", "Savar"),
    ("Dhaka", "দোহার ফায়ার স্টেশন", "01901-020808", "station", "Dohar"),
    ("Dhaka", "হাজারীবাগ ফায়ার স্টেশন", "01901-020776", "station", ""),
    ("Dhaka", "ধামরাই ফায়ার স্টেশন", "01901-020804", "station", "Dhamrai"),
    ("Dhaka", "কেরানীগঞ্জ ফায়ার স্টেশন", "01901-020810", "station", "Keraniganj"),
    ("Dhaka", "কেরানীগঞ্জ স্যাটেলাইট ফায়ার স্টেশন", "01901-020814", "station", "Keraniganj"),
    ("Dhaka", "সচিবালয় ফায়ার স্টেশন", "02-9515555", "station", ""),
    ("Dhaka", "সূত্রাপুর ফায়ার স্টেশন", "01901-020754", "station", ""),
    ("Dhaka", "কল্যাণপুর ফায়ার স্টেশন", "01901-020766", "station", ""),
    ("Dhaka", "চামড়া শিল্পনগরী ফায়ার স্টেশন", "01901-020824", "station", ""),
    ("Dhaka", "ভাষানটেক ফায়ার স্টেশন", "01901-020772", "station", ""),
    ("Dhaka", "সাভার (জিরাবো) ফায়ার স্টেশন", "01901-020826", "station", "Savar"),
    ("Dhaka", "পল্লবী ফায়ার স্টেশন", "01901-020784", "station", ""),
    ("Narayanganj", "উপসহকারী পরিচালক, নারায়ণগঞ্জ, জোন-১", "01901-020710", "office", ""),
    ("Narayanganj", "উপসহকারী পরিচালক, নারায়ণগঞ্জ, জোন-২", "01901-020705", "office", ""),
    ("Narayanganj", "নারায়ণগঞ্জ ফায়ার স্টেশন", "01901-020828", "station", ""),
    ("Narayanganj", "কাঁচপুর মডার্ণ ফায়ার স্টেশন", "01901-020848", "station", ""),
    ("Narayanganj", "হাজীগঞ্জ ফায়ার স্টেশন", "01901-020830", "station", ""),
    ("Narayanganj", "বন্দর ফায়ার স্টেশন", "01901-020850", "station", "Bandar"),
    ("Narayanganj", "নারায়ণগঞ্জ নদী ফায়ার স্টেশন", "01901-020836", "station", ""),
    ("Narayanganj", "কাঞ্চন নদী ফায়ার স্টেশন", "01901-020854", "station", ""),
    ("Narayanganj", "আদমজী (ইপিজেড) ফায়ার স্টেশন", "01901-020832", "station", ""),
    ("Narayanganj", "আড়াইহাজার ফায়ার স্টেশন", "01901-020842", "station", "Araihazar"),
    ("Narayanganj", "ফতুল্লা ফায়ার স্টেশন", "01901-020838", "station", ""),
    ("Narayanganj", "পাগলা স্থল কাম নদী ফায়ার স্টেশন", "01901-020840", "station", ""),
    ("Narayanganj", "সোনারগাঁও ফায়ার স্টেশন", "01901-020846", "station", "Sonargaon"),
    ("Narayanganj", "পূর্বাচল ফায়ার স্টেশন", "01901-020858", "station", ""),
    ("Gazipur", "উপসহকারী পরিচালক, গাজীপুর", "01901-020709", "office", ""),
    ("Gazipur", "জয়দেবপুর ফায়ার স্টেশন", "01901-020868", "station", ""),
    ("Gazipur", "টঙ্গী ফায়ার স্টেশন", "01901-020866", "station", ""),
    ("Gazipur", "কালিয়াকৈর ফায়ার স্টেশন", "01901-020892", "station", "Kaliakair"),
    ("Gazipur", "শ্রীপুর ফায়ার স্টেশন", "01901-020900", "station", "Sreepur"),
    ("Gazipur", "কালীগঞ্জ ফায়ার স্টেশন", "01901-020896", "station", "Kaliganj"),
    ("Gazipur", "সমরাস্ত্র কারখানা ফায়ার স্টেশন", "01901-020721", "station", ""),
    ("Gazipur", "কাশিমপুর মিনি ফায়ার স্টেশন", "01755-630094", "station", ""),
    ("Gazipur", "কাপাসিয়া ফায়ার স্টেশন", "01901-020898", "station", "Kapasia"),
    ("Gazipur", "গাজীপুর চৌরাস্তা মডার্ণ ফায়ার স্টেশন", "01901-020874", "station", ""),
    ("Gazipur", "কোনাবাড়ী মডার্ণ ফায়ার স্টেশন", "01901-020878", "station", ""),
    ("Gazipur", "সারাবো (কাশিমপুর) ফায়ার স্টেশন", "01901-020872", "station", ""),
    ("Munshiganj", "উপসহকারী পরিচালক, মুন্সীগঞ্জ", "01901-020712", "office", ""),
    ("Munshiganj", "মুন্সীগঞ্জ ফায়ার স্টেশন", "01901-020924", "station", ""),
    ("Munshiganj", "কমলাঘাট নদী ফায়ার স্টেশন", "01901-020926", "station", ""),
    ("Munshiganj", "শ্রীনগর ফায়ার স্টেশন", "01901-020934", "station", "Sreenagar"),
    ("Munshiganj", "গজারিয়া ফায়ার স্টেশন", "01901-020928", "station", "Gazaria"),
    ("Munshiganj", "গজারিয়া বিসিক ফায়ার স্টেশন", "01901-020930", "station", "Gazaria"),
    ("Munshiganj", "সিরাজদিখান ফায়ার স্টেশন", "01901-020940", "station", "Sirajdikhan"),
    ("Munshiganj", "লৌহজং ফায়ার স্টেশন", "01901-020936", "station", "Lohajang"),
    ("Narsingdi", "উপসহকারী পরিচালক, নরসিংদী", "01901-020713", "office", ""),
    ("Narsingdi", "নরসিংদী ফায়ার স্টেশন", "01901-020902", "station", ""),
    ("Narsingdi", "মনোহরদী ফায়ার স্টেশন", "01901-020912", "station", "Monohardi"),
    ("Narsingdi", "পলাশ ফায়ার স্টেশন", "01901-020914", "station", "Palash"),
    ("Narsingdi", "মাধবদী ফায়ার স্টেশন", "01901-020904", "station", ""),
    ("Narsingdi", "রায়পুরা ফায়ার স্টেশন", "01901-020918", "station", "Raipura"),
    ("Narsingdi", "শিবপুর ফায়ার স্টেশন", "01901-020920", "station", "Shibpur"),
    ("Narsingdi", "বেলাব ফায়ার স্টেশন", "01901-020910", "station", "Belabo"),
    ("Manikganj", "উপসহকারী পরিচালক, মানিকগঞ্জ", "01901-020714", "office", ""),
    ("Manikganj", "মানিকগঞ্জ ফায়ার স্টেশন", "01901-020946", "station", ""),
    ("Manikganj", "ঘিওর ফায়ার স্টেশন", "01901-020948", "station", "Ghior"),
    ("Manikganj", "আরিচা স্থল-কাম-নদী ফায়ার স্টেশন", "01901-020952", "station", ""),
    ("Manikganj", "হরিরামপুর ফায়ার স্টেশন", "01901-020950", "station", "Harirampur"),
    ("Manikganj", "সিংগাইর ফায়ার স্টেশন", "01901-020954", "station", "Singair"),
    ("Manikganj", "দৌলতপুর ফায়ার স্টেশন", "01901-020960", "station", "Daulatpur"),
    ("Manikganj", "সাটুরিয়া ফায়ার স্টেশন", "01901-020956", "station", "Saturia"),
    ("Tangail", "সহকারী পরিচালক, টাঙ্গাইল", "01901-020104", "office", ""),
    ("Tangail", "টাঙ্গাইল ফায়ার স্টেশন", "01901-020962", "station", ""),
    ("Tangail", "মধুপুর ফায়ার স্টেশন", "01901-020976", "station", "Madhupur"),
    ("Tangail", "মির্জাপুর ফায়ার স্টেশন", "01901-020980", "station", "Mirzapur"),
    ("Tangail", "বাসাইল ফায়ার স্টেশন", "01901-020964", "station", "Basail"),
    ("Tangail", "সখিপুর ফায়ার স্টেশন", "01901-020986", "station", "Sakhipur"),
    ("Tangail", "নাগরপুর ফায়ার স্টেশন", "01901-020984", "station", "Nagarpur"),
    ("Tangail", "ভূঞাপুর ফায়ার স্টেশন", "01901-020966", "station", "Bhuapur"),
    ("Tangail", "ধনবাড়ী ফায়ার স্টেশন", "01901-020978", "station", "Dhanbari"),
    ("Tangail", "কালিহাতী ফায়ার স্টেশন", "01901-020970", "station", "Kalihati"),
    ("Tangail", "গোপালপুর ফায়ার স্টেশন", "01901-020968", "station", "Gopalpur"),
    ("Tangail", "ঘাটাইল ফায়ার স্টেশন", "01901-020988", "station", "Ghatail"),
    ("Tangail", "এলেঙ্গা ফায়ার স্টেশন", "01901-020972", "station", ""),
    ("Tangail", "দেলদুয়ার ফায়ার স্টেশন", "01901-020992", "station", "Delduar"),
    ("Faridpur", "সহকারী পরিচালক, ফরিদপুর", "01901-020106", "office", ""),
    ("Faridpur", "ফরিদপুর ফায়ার স্টেশন", "01901-020996", "station", ""),
    ("Faridpur", "বোয়ালমারী ফায়ার স্টেশন", "01901-021008", "station", "Boalmari"),
    ("Faridpur", "ভাঙ্গা ফায়ার স্টেশন", "01901-021006", "station", "Bhanga"),
    ("Faridpur", "মধুখালী ফায়ার স্টেশন", "01901-021014", "station", "Madhukhali"),
    ("Faridpur", "সদরপুর ফায়ার স্টেশন", "01901-021010", "station", "Sadarpur"),
    ("Faridpur", "সালথা ফায়ার স্টেশন", "01901-021016", "station", "Saltha"),
    ("Faridpur", "নগরকান্দা ফায়ার স্টেশন", "01901-021002", "station", "Nagarkanda"),
    ("Faridpur", "চরভদ্রাশন ফায়ার স্টেশন", "01901-021018", "station", "Char Bhadrasan"),
    ("Faridpur", "আলফাডাঙ্গা ফায়ার স্টেশন", "01901-021022", "station", "Alfadanga"),
    ("Rajbari", "উপসহকারী পরিচালক, রাজবাড়ী", "01901-020719", "office", ""),
    ("Rajbari", "পাংশা ফায়ার স্টেশন", "01901-021030", "station", "Pangsha"),
    ("Rajbari", "রাজবাড়ী ফায়ার স্টেশন", "01901-021024", "station", ""),
    ("Rajbari", "বালিয়াকান্দি ফায়ার স্টেশন", "01901-021026", "station", "Baliakandi"),
    ("Rajbari", "গোয়ালন্দ ফায়ার স্টেশন", "01901-021028", "station", "Goalanda"),
    ("Rajbari", "কালুখালী ফায়ার স্টেশন", "01901-021032", "station", "Kalukhali"),
    ("Madaripur", "উপসহকারী পরিচালক, মাদারীপুর", "01901-020718", "office", ""),
    ("Madaripur", "মাদারীপুর ফায়ার স্টেশন", "01901-021034", "station", ""),
    ("Madaripur", "শিবচর ফায়ার স্টেশন", "01901-021036", "station", "Shibchar"),
    ("Madaripur", "রাজৈর ফায়ার স্টেশন", "01901-021038", "station", "Rajoir"),
    ("Madaripur", "কালকিনি ফায়ার স্টেশন", "01901-021042", "station", "Kalkini"),
    ("Madaripur", "টেকেরহাট বন্দর স্থল কাম নদী ফায়ার স্টেশন", "01901-021040", "station", ""),
    ("Gopalganj", "উপসহকারী পরিচালক, গোপালগঞ্জ", "01901-020717", "office", ""),
    ("Gopalganj", "গোপালগঞ্জ ফায়ার স্টেশন", "01901-021046", "station", ""),
    ("Gopalganj", "টুঙ্গিপাড়া ফায়ার স্টেশন", "01901-021054", "station", "Tungipara"),
    ("Gopalganj", "মুকসুদপুর ফায়ার স্টেশন", "01901-021052", "station", "Muksudpur"),
    ("Gopalganj", "কোটালীপাড়া ফায়ার স্টেশন", "01901-021050", "station", "Kotalipara"),
    ("Gopalganj", "কাশিয়ানী ফায়ার স্টেশন", "01901-021056", "station", "Kashiani"),
    ("Shariatpur", "উপসহকারী পরিচালক, শরীয়তপুর", "01901-020720", "office", ""),
    ("Shariatpur", "শরীয়তপুর ফায়ার স্টেশন", "01901-021058", "station", ""),
    ("Shariatpur", "ডামুড্যা ফায়ার স্টেশন", "01901-021060", "station", "Damudya"),
    ("Shariatpur", "গোসাইরহাট ফায়ার স্টেশন", "01901-021062", "station", "Gosairhat"),
    ("Shariatpur", "জাজিরা ফায়ার স্টেশন", "01901-021066", "station", "Zanjira"),
    ("Shariatpur", "নাড়িয়া ফায়ার স্টেশন", "01901-021064", "station", "Naria"),
    ("Shariatpur", "ভেদরগঞ্জ ফায়ার স্টেশন", "01901-021070", "station", "Bhedarganj"),
    ("Kishoreganj", "উপসহকারী পরিচালক, কিশোরগঞ্জ", "01901-020722", "office", ""),
    ("Kishoreganj", "কিশোরগঞ্জ ফায়ার স্টেশন", "01901-021074", "station", ""),
    ("Kishoreganj", "বাজিতপুর ফায়ার স্টেশন", "01901-021080", "station", "Bajitpur"),
    ("Kishoreganj", "ভৈরব বাজার ফায়ার স্টেশন", "01901-021082", "station", "Bhairab"),
    ("Kishoreganj", "ভৈরব নদী ফায়ার স্টেশন", "01901-021084", "station", "Bhairab"),
    ("Kishoreganj", "কুলিয়ারচর ফায়ার স্টেশন", "01901-021086", "station", "Kuliarchar"),
    ("Kishoreganj", "তাড়াইল ফায়ার স্টেশন", "01901-021088", "station", "Tarail"),
    ("Kishoreganj", "কটিয়াদী ফায়ার স্টেশন", "01901-021096", "station", "Katiadi"),
    ("Kishoreganj", "পাকুন্দিয়া ফায়ার স্টেশন", "01901-021090", "station", "Pakundia"),
    ("Kishoreganj", "হোসেনপুর ফায়ার স্টেশন", "01901-021100", "station", "Hossainpur"),
    ("Kishoreganj", "করিমগঞ্জ ফায়ার স্টেশন", "01901-021094", "station", "Karimganj"),
    ("Kishoreganj", "ইটনা ফায়ার স্টেশন", "01901-021106", "station", "Itna"),
    ("Kishoreganj", "মিঠামইন ফায়ার স্টেশন", "01901-021104", "station", "Mithamain"),
    ("Kishoreganj", "অষ্টগ্রাম ফায়ার স্টেশন", "01901-021098", "station", "Austagram"),
    ("Kishoreganj", "নিকলী স্থলকাম নদী ফায়ার স্টেশন", "01901-021102", "station", "Nikli"),
]
# Remarks on single rows of the Dhaka transcription (keyed by name as transcribed)
T_NOTES_DHAKA = {
    "কল্যাণপুর ফায়ার স্টেশন": "listed twice in the PDF (serials 32 and 35) with the same number; kept once",
    "উপসহকারী পরিচালক, জোন-২": "the PDF prints the same number (01901-020705) for Zone-2 in Dhaka and Zone-2 in Narayanganj",
    "উপসহকারী পরিচালক, নারায়ণগঞ্জ, জোন-২": "the PDF prints the same number (01901-020705) for Zone-2 in Dhaka and Zone-2 in Narayanganj",
    "সচিবালয় ফায়ার স্টেশন": "only a landline is printed (02-9515555, old 7-digit Dhaka format)",
    "কাশিমপুর মিনি ফায়ার স্টেশন": "number printed in the official list is outside the FSCD 01901 series",
    "হযরত শাহজালাল আন্তর্জাতিক বিমান বন্দর অস্থায়ী ফায়ার স্টেশন": "listed as a temporary (অস্থায়ী) station",
}
# Chattogram-division PDF ("ফায়ার সার্ভিস ও সিভিল ডিফেন্স, চট্টগ্রাম বিভাগ, চট্টগ্রাম", Word export dated 2026-08-11, 5 pages,
# 14 tables: Chattogram district in zones 1-4, then the other 10 districts): same broken text layer; names transcribed by
# hand from the rendered pages, in PDF order; numbers as printed (six are printed with 12 digits, see T_NOTES_CHATTOGRAM).
# Kaptai fire station is listed under Chattogram Zone-3 and under Rangamati with the same number: kept once, in Rangamati.
T_CHATTOGRAM = [
    ("Chattogram", "উপপরিচালক চট্টগ্রাম", "019010210110", "office", ""),
    ("Chattogram", "সহকারী পরিচালক,চট্টগ্রাম জেলা", "01901020112", "office", ""),
    ("Chattogram", "উপসহকারী পরিচালক চট্টগ্রাম -১", "019010201506", "office", ""),
    ("Chattogram", "আগ্রাবাদ ফায়ার স্টেশন", "019010201540", "station", ""),
    ("Chattogram", "বন্দর ফায়ার স্টেশন", "01901021555", "station", ""),
    ("Chattogram", "সিইপিজেড ফায়ার স্টেশন", "01901021551", "station", ""),
    ("Chattogram", "কেইপিজেড ফায়ার স্টেশন", "01901021553", "station", ""),
    ("Chattogram", "নন্দনকানন ফায়ার স্টেশন", "01901-021545", "station", ""),
    ("Chattogram", "উপসহকারী পরিচালক, চট্টগ্রাম জোন-২", "01901021507", "office", ""),
    ("Chattogram", "পটিয়া ফায়ার স্টেশন", "01901021601", "station", "Patiya"),
    ("Chattogram", "লামারবাজার ফায়ার স্টেশন", "01901-021549", "station", ""),
    ("Chattogram", "বোয়ালখালী ফায়ার স্টেশন", "01901021597", "station", "Boalkhali"),
    ("Chattogram", "বাঁশখালী ফায়ার স্টেশন", "01901021595", "station", "Banshkhali"),
    ("Chattogram", "আনোয়ারা ফায়ার স্টেশন", "01901021593", "station", "Anwara"),
    ("Chattogram", "চন্দনাইশ ফায়ার স্টেশন", "01901021599", "station", "Chandanaish"),
    ("Chattogram", "সাতকানিয়া ফায়ার স্টেশন", "01901021603", "station", "Satkania"),
    ("Chattogram", "লোহাগাড়া ফায়ার স্টেশন", "01901021605", "station", "Lohagara"),
    ("Chattogram", "উপসহকারী পরিচালক, চট্টগ্রাম জোন-৩", "01901021508", "office", ""),
    ("Chattogram", "চন্দনপুরা ফায়ার স্টেশন", "01901021559", "station", ""),
    ("Chattogram", "কালুরঘাট ফায়ার স্টেশন", "01901021557", "station", ""),
    ("Chattogram", "হাটহাজারী ফায়ার স্টেশন", "01901021575", "station", "Hathazari"),
    ("Chattogram", "রাউজান ফায়ার স্টেশন", "01901021583", "station", "Raozan"),
    ("Chattogram", "রাঙ্গুনিয়া ফায়ার স্টেশন", "01901021581", "station", "Rangunia"),
    ("Chattogram", "ফটিকছড়ি ফায়ার স্টেশন", "01901021571", "station", "Fatikchhari"),
    ("Chattogram", "কুমিরা ফায়ার স্টেশন", "01901021591", "station", ""),
    ("Chattogram", "বায়েজিদ ফায়ার স্টেশন", "01901021543", "station", ""),
    ("Chattogram", "সীতাকুন্ড ফায়ার স্টেশন", "01901021589", "station", "Sitakunda"),
    ("Chattogram", "সন্দ্বীপ ফায়ার স্টেশন", "01901021587", "station", "Sandwip"),
    ("Chattogram", "মিরসরাই ফায়ার স্টেশন", "01901021577", "station", "Mirsharai"),
    ("Chattogram", "বারৈয়ারহাট ফায়ার স্টেশন", "01901021579", "station", ""),
    ("Cox's Bazar", "উপসহকারী পরিচালক, কক্সবাজার", "01901021511", "office", ""),
    ("Cox's Bazar", "কক্সবাজার ফায়ার স্টেশন", "01901021607", "station", ""),
    ("Cox's Bazar", "চকরিয়া ফায়ার স্টেশন", "01901021617", "station", "Chakaria"),
    ("Cox's Bazar", "রামু ফায়ার স্টেশন", "01901021621", "station", "Ramu"),
    ("Cox's Bazar", "পেকুয়া ফায়ার স্টেশন", "01901021629", "station", "Pekua"),
    ("Cox's Bazar", "মহেশখালী ফায়ার স্টেশন", "01901021619", "station", "Maheshkhali"),
    ("Cox's Bazar", "কুতুবদিয়া ফায়ার স্টেশন", "01901021631", "station", "Kutubdia"),
    ("Cox's Bazar", "উখিয়া ফায়ার স্টেশন", "01901021627", "station", "Ukhia"),
    ("Cox's Bazar", "টেকনাফ ফায়ার স্টেশন", "01901021625", "station", "Teknaf"),
    ("Bandarban", "সহকারী পরিচালক,বান্দরবান", "01901020119", "office", ""),
    ("Bandarban", "বান্দরবান ফায়ার স্টেশন", "01901021679", "station", ""),
    ("Bandarban", "আলীকদম ফায়ার স্টেশন", "01901021683", "station", "Alikadam"),
    ("Bandarban", "লামা ফায়ার স্টেশন", "01901-021685", "station", "Lama"),
    ("Bandarban", "রোয়াংছড়ি ফায়ার স্টেশন", "01901-021687", "station", "Rowangchhari"),
    ("Bandarban", "রুমা ফায়ার স্টেশন", "01901-021691", "station", "Ruma"),
    ("Bandarban", "নাইক্ষ্যংছড়ি ফায়ার স্টেশন", "01897-878797", "station", "Naikhongchhari"),
    ("Bandarban", "থানচি ফায়ার স্টেশন", "01901-021689", "station", "Thanchi"),
    ("Rangamati", "সহকারী পরিচালক, রাঙ্গামাটি", "01901020118", "office", ""),
    ("Rangamati", "রাঙ্গামাটি ফায়ার স্টেশন", "01901021637", "station", ""),
    ("Rangamati", "কাপ্তাই ফায়ার স্টেশন", "01901021641", "station", "Kaptai"),
    ("Rangamati", "কাউখালী ফায়ার স্টেশন", "01901021643", "station", "Kawkhali"),
    ("Rangamati", "লংগদু ফায়ার স্টেশন", "01901021645", "station", "Langadu"),
    ("Khagrachhari", "উপসহকারী পরিচালক, খাগড়াছড়ি", "01901021508", "office", ""),
    ("Khagrachhari", "খাগড়াছড়ি ফায়ার স্টেশন", "01901021661", "station", ""),
    ("Khagrachhari", "দীঘিনালা ফায়ার স্টেশন", "01901021663", "station", "Dighinala"),
    ("Khagrachhari", "রামগড় ফায়ার স্টেশন", "01901021665", "station", "Ramgarh"),
    ("Khagrachhari", "মাটিরাঙ্গা ফায়ার স্টেশন", "01901021667", "station", "Matiranga"),
    ("Khagrachhari", "লক্ষিছড়ি ফায়ার স্টেশন", "01901021669", "station", "Lakshmichhari"),
    ("Khagrachhari", "পানছড়ি ফায়ার স্টেশন", "01901021671", "station", "Panchhari"),
    ("Cumilla", "সহকারী পরিচালক, কুমিল্লা", "01901020114", "office", ""),
    ("Cumilla", "উপসহকারী পরিচালক, কুমিল্লা", "01901021510", "office", ""),
    ("Cumilla", "কুমিল্লা ফায়ার স্টেশন", "01901021695", "station", ""),
    ("Cumilla", "কুমিল্লা ইপিজেড ফায়ার", "01901021699", "station", ""),
    ("Cumilla", "দৌলতগঞ্জবাজার ফায়ার", "01901021717", "station", ""),
    ("Cumilla", "চৌদ্দগ্রাম ফায়ার স্টেশন", "01901021711", "station", "Chauddagram"),
    ("Cumilla", "চৌয়ারাবাজার ফায়ার স্টেশন", "01901021697", "station", ""),
    ("Cumilla", "বরুড়া ফায়ার স্টেশন", "01901021715", "station", "Barura"),
    ("Cumilla", "চান্দিনা ফায়ার স্টেশন", "01901021701", "station", "Chandina"),
    ("Cumilla", "দাউদকান্দি ফায়ার স্টেশন", "01901021703", "station", "Daudkandi"),
    ("Cumilla", "মুরাদনগর ফায়ার স্টেশন", "01901021707", "station", "Muradnagar"),
    ("Cumilla", "বুড়িচং ফায়ার স্টেশন", "01901021713", "station", "Burichang"),
    ("Cumilla", "হোমনা ফায়ার স্টেশন", "01901021705", "station", "Homna"),
    ("Cumilla", "মেঘনা ফায়ার স্টেশন", "01901021721", "station", "Meghna"),
    ("Cumilla", "মনোহরগঞ্জ ফায়ার স্টেশন", "01901021719", "station", "Manoharganj"),
    ("Brahmanbaria", "উপসহকারী পরিচালক, ব্রাহ্মণবাড়িয়া", "019010201514", "office", ""),
    ("Brahmanbaria", "ব্রাহ্মণবাড়িয়া ফায়ার স্টেশন", "01901021735", "station", ""),
    ("Brahmanbaria", "আশুগঞ্জ ফায়ার স্টেশন", "01901021737", "station", "Ashuganj"),
    ("Brahmanbaria", "আখাউড়া ফায়ার স্টেশন", "01901021739", "station", "Akhaura"),
    ("Brahmanbaria", "কসবা ফায়ার স্টেশন", "01901021745", "station", "Kasba"),
    ("Brahmanbaria", "সরাইল ফায়ার স্টেশন", "01901021747", "station", "Sarail"),
    ("Brahmanbaria", "বাঞ্ছারামপুর ফায়ার স্টেশন", "01901021743", "station", "Bancharampur"),
    ("Brahmanbaria", "নবীনগর ফায়ার স্টেশন", "01901021749", "station", "Nabinagar"),
    ("Brahmanbaria", "নাসিরনগর ফায়ার স্টেশন", "01901021751", "station", "Nasirnagar"),
    ("Brahmanbaria", "বিজয়নগর ফায়ার স্টেশন", "01901021753", "station", "Bijoynagar"),
    ("Chandpur", "উপসহকারী পরিচালক, চাঁদপুর", "019010201515", "office", ""),
    ("Chandpur", "চাঁদপুর উত্তর ফায়ার স্টেশন", "01901021755", "station", ""),
    ("Chandpur", "চাঁদপুর দক্ষিণ ফায়ার স্টেশন", "01901021757", "station", ""),
    ("Chandpur", "নদী ফায়ার স্টেশন", "01901021759", "station", ""),
    ("Chandpur", "হাজীগঞ্জ ফায়ার স্টেশন", "01901-021761", "station", "Hajiganj"),
    ("Chandpur", "কচুয়া ফায়ার স্টেশন", "01901021765", "station", "Kachua"),
    ("Chandpur", "শাহরাস্তি ফায়ার স্টেশন", "01901021769", "station", "Shahrasti"),
    ("Chandpur", "মতলব ফায়ার স্টেশন", "01901021767", "station", ""),
    ("Chandpur", "মতলব উত্তর ফায়ার স্টেশন", "01901021771", "station", "Matlab Uttar"),
    ("Chandpur", "ফরিদগঞ্জ ফায়ার স্টেশন", "01901-021773", "station", "Faridganj"),
    ("Chandpur", "হাইমচর ফায়ার স্টেশন", "01901021763", "station", "Haimchar"),
    ("Noakhali", "সহকারী পরিচালক, নোয়াখালী", "01901020116", "office", ""),
    ("Noakhali", "মাইজদী ফায়ার স্টেশন", "01901021775", "station", ""),
    ("Noakhali", "চৌমুহনী ফায়ার স্টেশন", "01901021783", "station", ""),
    ("Noakhali", "চাটখিল ফায়ার স্টেশন", "01901021781", "station", "Chatkhil"),
    ("Noakhali", "সুবর্নচর ফায়ার স্টেশন", "01901021797", "station", "Subarnachar"),
    ("Noakhali", "সোনাইমুড়ী ফায়ার স্টেশন", "01901021787", "station", "Sonaimuri"),
    ("Noakhali", "কোম্পানীগঞ্জ ফায়ার স্টেশন", "01901021789", "station", "Companiganj"),
    ("Noakhali", "হাতিয়া ফায়ার স্টেশন", "01901021791", "station", "Hatiya"),
    ("Noakhali", "কবিরহাট ফায়ার স্টেশন", "01901021795", "station", "Kabirhat"),
    ("Noakhali", "সেনবাগ ফায়ার স্টেশন", "019011021801", "station", "Senbagh"),
    ("Feni", "উপসহকারী পরিচালক, ফেনী", "01901021534", "office", ""),
    ("Feni", "ফেনী ফায়ার স্টেশন", "01901021823", "station", ""),
    ("Feni", "ছাগলনাইয়া ফায়ার স্টেশন", "01901021825", "station", "Chhagalnaiya"),
    ("Feni", "পরশুরাম ফায়ার স্টেশন", "01901021827", "station", "Parshuram"),
    ("Feni", "সোনাগাজী ফায়ার স্টেশন", "01901021829", "station", "Sonagazi"),
    ("Feni", "ফুলগাজী ফায়ার স্টেশন", "01901021831", "station", "Fulgazi"),
    ("Lakshmipur", "উপসকারী পরিচালক, লক্ষীপুর", "01901021516", "office", ""),
    ("Lakshmipur", "লক্ষীপুর ফায়ার স্টেশন", "01901021805", "station", ""),
    ("Lakshmipur", "রায়পুর ফায়ার স্টেশন", "01901021811", "station", "Raipur"),
    ("Lakshmipur", "কমলনগর ফায়ার স্টেশন", "01901021817", "station", "Kamalnagar"),
    ("Lakshmipur", "রামগঞ্জ ফায়ার স্টেশন", "01901021813", "station", "Ramganj"),
    ("Lakshmipur", "রামগতি ফায়ার স্টেশন", "01901021815", "station", "Ramgati"),
]
_TWELVE = "the PDF prints a 12-digit number (%s), not a valid 11-digit mobile number; phone left empty, number kept in extra_json"
T_NOTES_CHATTOGRAM = {
    "উপপরিচালক চট্টগ্রাম": _TWELVE % "০১৯০১০২১০১১০",
    "উপসহকারী পরিচালক চট্টগ্রাম -১": _TWELVE % "০১৯০১০২০১৫০৬",
    "আগ্রাবাদ ফায়ার স্টেশন": _TWELVE % "০১৯০১০২০১৫৪০",
    "উপসহকারী পরিচালক, ব্রাহ্মণবাড়িয়া": _TWELVE % "০১৯০১০২০১৫১৪",
    "উপসহকারী পরিচালক, চাঁদপুর": _TWELVE % "০১৯০১০২০১৫১৫",
    "সেনবাগ ফায়ার স্টেশন": _TWELVE % "০১৯০১১০২১৮০১",
    "উপসহকারী পরিচালক, চট্টগ্রাম জোন-৩": "the PDF prints the same number (01901-021508) for Chattogram Zone-3 and Khagrachhari Deputy Assistant Directors",
    "উপসহকারী পরিচালক, খাগড়াছড়ি": "the PDF prints the same number (01901-021508) for Chattogram Zone-3 and Khagrachhari Deputy Assistant Directors",
    "কাপ্তাই ফায়ার স্টেশন": "listed twice in the PDF (Chattogram district Zone-3, serial 2, and Rangamati district, serial 3) with the same number; kept once, under Rangamati",
    "নাইক্ষ্যংছড়ি ফায়ার স্টেশন": "number printed in the official list is outside the FSCD 01901 series; the name's text layer is in Bijoy encoding (read from the rendered page)",
    "আলীকদম ফায়ার স্টেশন": "printed without spaces ('আলীকদমফায়ারস্টেশন')",
    "কুমিল্লা ইপিজেড ফায়ার": "name printed without 'স্টেশন'",
    "দৌলতগঞ্জবাজার ফায়ার": "name printed without 'স্টেশন'",
    "নদী ফায়ার স্টেশন": "printed as 'নদী ফায়ার স্টেশন' (river fire station) in the Chandpur table, without a place name",
    "উপসকারী পরিচালক, লক্ষীপুর": "post printed 'উপসকারী পরিচালক' (sic)",
    "রায়পুর ফায়ার স্টেশন": "printed with serial 2 (the Lakshmipur table repeats serial 2)",
}
# Khulna Division PDF ("ফায়ার সার্ভিস ও সিভিল ডিফেন্স, খুলনা বিভাগ, খুলনা", Word export 2026-08-11, 3 pages, 10 district
# tables): same broken text layer; names transcribed by hand from the rendered pages, in PDF order; numbers as printed.
T_KHULNA = [
    ("Khulna", "উপ পরিচালক ,খুলনা", "01901-020130", "office", ""),
    ("Khulna", "সহকারী পরিচালক ,খুলনা", "01901-020132", "office", ""),
    ("Khulna", "উপ সহকারী পরিচালক ,খুলনা", "01901-022704", "office", ""),
    ("Khulna", "ফোরম্যান ,খুলনা", "01920-659967", "office", ""),
    ("Khulna", "ও সি কন্ট্রোল, খুলনা", "01717-934439", "office", ""),
    ("Khulna", "খুলনা সদর ফায়ার স্টেশন", "01901022730", "station", ""),
    ("Khulna", "খালিশপুর ফায়ার স্টেশন", "01901022732", "station", ""),
    ("Khulna", "টুটপাড়া ফায়ার স্টেশন", "01901022734", "station", ""),
    ("Khulna", "দৌলাতপুর ফায়ার স্টেশন", "01901022736", "station", ""),
    ("Khulna", "স্থলকাম নদী ফায়ার স্টেশন", "01301022748", "station", ""),
    ("Khulna", "নদী ফায়ার স্টেশন", "01901022738", "station", ""),
    ("Khulna", "রুপসা ফায়ার স্টেশন", "01901022752", "station", "Rupsa"),
    ("Khulna", "খানজাহান আলী ফায়ার স্টেশন", "01901022744", "station", ""),
    ("Khulna", "ডুমুরিয়া বটিয়াঘাটা ফায়ার স্টেশন", "01901022750", "station", ""),
    ("Khulna", "দাকোপ ফায়ার স্টেশন", "01901022758", "station", "Dacope"),
    ("Khulna", "বটিয়াঘাটা ফায়ার স্টেশন", "01901022756", "station", "Batiaghata"),
    ("Khulna", "তেরখাদা ফায়ার স্টেশন", "01901022760", "station", "Terokhada"),
    ("Khulna", "কয়রা ফায়ার স্টেশন", "01901022762", "station", "Koyra"),
    ("Bagerhat", "উপ সহকারী পরিচালক ,বাগেরহাট", "01901-022705", "office", ""),
    ("Bagerhat", "বাগেরহাট সদর ফায়ার স্টেশন", "01901-022768", "station", "Bagerhat Sadar"),
    ("Bagerhat", "রামপাল ফায়ার স্টেশন", "01901-022786", "station", "Rampal"),
    ("Bagerhat", "মোংলা ইপিজেড ফায়ার স্টেশন", "01901-022774", "station", ""),
    ("Bagerhat", "মোংলা ফায়ার স্টেশন", "01901-022772", "station", "Mongla"),
    ("Bagerhat", "শরনখোলা ফায়ার স্টেশন", "01901-022782", "station", "Sarankhola"),
    ("Bagerhat", "মোড়েলগঞ্জ ফায়ার স্টেশন", "01901-022778", "station", "Morrelganj"),
    ("Bagerhat", "কচুয়া ফায়ার স্টেশন", "01901-022792", "station", "Kachua"),
    ("Bagerhat", "মোল্লাহাট ফায়ার স্টেশন", "01901-022784", "station", "Mollahat"),
    ("Bagerhat", "চিতলমারী ফায়ার স্টেশন", "01901-022794", "station", "Chitalmari"),
    ("Bagerhat", "ফকিরহাট ফায়ার স্টেশন", "01901-022788", "station", "Fakirhat"),
    ("Satkhira", "উপ সহকারী পরিচালক ,সাতক্ষীরা", "01901-022706", "office", ""),
    ("Satkhira", "সাতক্ষীরা সদর ফায়ার স্টেশন", "01901-022796", "station", "Satkhira Sadar"),
    ("Satkhira", "দেবহাটা ফায়ার স্টেশন", "01901-022806", "station", "Debhata"),
    ("Satkhira", "কালীগঞ্জ ফায়ার স্টেশন", "01901-022800", "station", "Kaliganj"),
    ("Satkhira", "আশাশুনি ফায়ার স্টেশন", "01901-022798", "station", "Assasuni"),
    ("Satkhira", "কলারোয়া ফায়ার স্টেশন", "01901-022804", "station", "Kalaroa"),
    ("Satkhira", "শ্যামনগর ফায়ার স্টেশন", "01901-022808", "station", "Shyamnagar"),
    ("Satkhira", "তালা ফায়ার স্টেশন", "01901-022810", "station", "Tala"),
    ("Jashore", "সহকারী পরিচালক ,যশোর", "01901-020134", "office", ""),
    ("Jashore", "উপ সহকারী পরিচালক ,যশোর", "01901-022712", "office", ""),
    ("Jashore", "যশোর সদর ফায়ার স্টেশন", "01901-022814", "station", "Jashore Sadar"),
    ("Jashore", "সেনানিবাস ফায়ার স্টেশন", "01901-022816", "station", ""),
    ("Jashore", "নওয়াপাড়া ফায়ার স্টেশন", "01912-6828", "station", ""),
    ("Jashore", "ঝিকরগাছা ফায়ার স্টেশন", "01901022826", "station", "Jhikargachha"),
    ("Jashore", "বেনাপোল ফায়ার স্টেশন", "01901-022830", "station", ""),
    ("Jashore", "মনিরামপুর ফায়ার স্টেশন", "01740-322834", "station", "Manirampur"),
    ("Jashore", "বাঘারপাড়া ফায়ার স্টেশন", "01901-022836", "station", "Bagherpara"),
    ("Jashore", "কেশবপুর ফায়ার স্টেশন", "01901-022842", "station", "Keshabpur"),
    ("Jashore", "চৌগাছা ফায়ার স্টেশন", "01901-022840", "station", "Chaugachha"),
    ("Narail", "উপ সহকারী পরিচালক ,নড়াইল", "01901-022707", "office", ""),
    ("Narail", "নড়াইল সদর ফায়ার স্টেশন", "01901-022860", "station", "Narail Sadar"),
    ("Narail", "লোহাগাড়া ফায়ার স্টেশন", "01901-022864", "station", "Lohagara"),
    ("Narail", "কালিয়া ফায়ার স্টেশন", "01901-022866", "station", "Kalia"),
    ("Jhenaidah", "উপ সহকারী পরিচালক ,ঝিনাইদহ", "01901-022709", "office", ""),
    ("Jhenaidah", "ঝিনাইদহ সদর ফায়ার স্টেশন", "01901-022844", "station", "Jhenaidah Sadar"),
    ("Jhenaidah", "শৈলকুপা ফায়ার স্টেশন", "01901-022850", "station", "Shailkupa"),
    ("Jhenaidah", "কোটচাদপুর ফায়ার স্টেশন", "01901-022848", "station", "Kotchandpur"),
    ("Jhenaidah", "হরিনাকুন্ড ফায়ার স্টেশন", "01901-022852", "station", "Harinakunda"),
    ("Jhenaidah", "মহেশপুর ফায়ার স্টেশন", "01901-022857", "station", "Maheshpur"),
    ("Jhenaidah", "কালিগঞ্জ ফায়ার স্টেশন", "01901-022852", "station", "Kaliganj"),
    ("Magura", "উপ সহকারী পরিচালক ,মাগুরা", "01901-022708", "office", ""),
    ("Magura", "মাগুরা সদর ফায়ার স্টেশন", "01901-022868", "station", "Magura Sadar"),
    ("Magura", "মোহাম্মাদপুর ফায়ার স্টেশন", "01901-022872", "station", "Mohammadpur"),
    ("Magura", "শ্রীপুর ফায়ার স্টেশন", "01901-022874", "station", "Sreepur"),
    ("Magura", "শালিখা ফায়ার স্টেশন", "01901-022876", "station", "Shalikha"),
    ("Kushtia", "সহকারী পরিচালক ,কুষ্টিয়া", "01901020136", "office", ""),
    ("Kushtia", "উপ সহকারী পরিচালক ,কুষ্টিয়া", "01901-022713", "office", ""),
    ("Kushtia", "কুষ্টিয়া সদর ফায়ার স্টেশন", "01901-022878", "station", "Kushtia Sadar"),
    ("Kushtia", "খুকসা ফায়ার স্টেশন", "01901-022888", "station", "Khoksa"),
    ("Kushtia", "ভেড়ামারা ফায়ার স্টেশন", "01901-022886", "station", "Bheramara"),
    ("Kushtia", "কুমারখালী ফায়ার স্টেশন", "01901-022882", "station", "Kumarkhali"),
    ("Kushtia", "মিরপুর ফায়ার স্টেশন", "01901-022884", "station", "Mirpur"),
    ("Chuadanga", "উপ সহকারী পরিচালক ,চুয়াডাংগা", "01901022710", "office", ""),
    ("Chuadanga", "চুয়াডাংগা সদর ফায়ার স্টেশন", "01901-022898", "station", "Chuadanga Sadar"),
    ("Chuadanga", "আলমডাংগা ফায়ার স্টেশন", "01901-022902", "station", "Alamdanga"),
    ("Chuadanga", "জীবন নগর ফায়ার স্টেশন", "01901-022906", "station", "Jibannagar"),
    ("Chuadanga", "দর্শনা ফায়ার স্টেশন", "01901-022908", "station", ""),
    ("Meherpur", "উপ সহকারী পরিচালক ,মেহেরপুর", "01901022711", "office", ""),
    ("Meherpur", "মেহেরপুর সদর ফায়ার স্টেশন", "01901-022892", "station", "Meherpur Sadar"),
    ("Meherpur", "বামুন্দি ফায়ার স্টেশন", "01901-022894", "station", ""),
    ("Meherpur", "মুজিব নগর ফায়ার স্টেশন", "01901-022896", "station", "Mujibnagar"),
]
_SAME_852 = "the PDF prints the same number (01901-022852) for the Harinakunda and Kaliganj fire stations"
T_NOTES_KHULNA = {
    "ফোরম্যান ,খুলনা": "post 'ফোরম্যান' (foreman), not a Director post; number outside the FSCD 01901 series",
    "ও সি কন্ট্রোল, খুলনা": "post 'ও সি কন্ট্রোল' (officer in charge, control room), not a Director post; number outside the FSCD 01901 series",
    "স্থলকাম নদী ফায়ার স্টেশন": "land-cum-river (স্থলকাম নদী) station listed without a place name; number printed 01301-022748, outside the FSCD 01901 series (possibly a misprint)",
    "নদী ফায়ার স্টেশন": "printed as 'নদী ফায়ার স্টেশন' (river fire station) in the Khulna table, without a place name",
    "ডুমুরিয়া বটিয়াঘাটা ফায়ার স্টেশন": "printed 'ডুমুরিয়া বটিয়াঘাটা' (two upazila names); a separate 'বটিয়াঘাটা ফায়ার স্টেশন' follows; upazila not set",
    "নওয়াপাড়া ফায়ার স্টেশন": "the PDF prints a 9-digit number (০১৯১২-৬৮২৮), not a valid mobile number; phone left empty, number kept in extra_json",
    "মনিরামপুর ফায়ার স্টেশন": "number printed in the official list is outside the FSCD 01901 series",
    "হরিনাকুন্ড ফায়ার স্টেশন": _SAME_852, "কালিগঞ্জ ফায়ার স্টেশন": _SAME_852,
    "খুকসা ফায়ার স্টেশন": "spelt 'খুকসা' in the PDF (Khoksa)",
    "দৌলাতপুর ফায়ার স্টেশন": "spelt 'দৌলাতপুর' in the PDF",
    "কোটচাদপুর ফায়ার স্টেশন": "spelt 'কোটচাদপুর' (no chandrabindu) in the PDF",
    "লোহাগাড়া ফায়ার স্টেশন": "spelt 'লোহাগাড়া' in the PDF (Lohagara, Narail)",
}
# Barishal Division PDF ("ফায়ার সার্ভিস ও সিভিল ডিফেন্স, বরিশাল বিভাগ, বরিশাল", Word export 2026-08-11, 2 pages, 6 district
# tables): same broken text layer; names transcribed by hand from the rendered pages, in PDF order; numbers as printed.
T_BARISHAL = [
    ("Barishal", "উপপরিচালক", "01901020160", "office", ""),
    ("Barishal", "সহকারী পরিচালক", "01901020162", "office", ""),
    ("Barishal", "বরিশাল সদর ফায়ার স্টেশন", "01901023921", "station", "Barishal Sadar"),
    ("Barishal", "বরিশাল দক্ষিন ফায়ার স্টেশন", "01901023929", "station", ""),
    ("Barishal", "বরিশাল নদী ফায়ার স্টেশন", "01901023923", "station", ""),
    ("Barishal", "গৌরনদী ফায়ার স্টেশন", "01901023931", "station", "Gaurnadi"),
    ("Barishal", "বানরিপাড়া ফায়ার স্টেশ", "01901023937", "station", "Banaripara"),
    ("Barishal", "উজিরপুর ফায়ার স্টেশন", "01901023933", "station", "Wazirpur"),
    ("Barishal", "মেহেন্দিগঞ্জ ফায়ার স্টেশন", "01901-023939", "station", "Mehendiganj"),
    ("Barishal", "বাবুগঞ্জ ফায়ার স্টেশন", "01901023941", "station", "Babuganj"),
    ("Barishal", "বাখেরগঞ্জ ফায়ার স্টেশন", "01901023943", "station", "Bakerganj"),
    ("Barishal", "হিজলা ফায়ার স্টেশন", "01901023947", "station", "Hizla"),
    ("Barishal", "মুলাদি ফায়ার স্টেশন", "01901023949", "station", "Muladi"),
    ("Pirojpur", "উপ সহকারী পরিচালক পিরোজপুর", "01901023904", "office", ""),
    ("Pirojpur", "পিরোজপুর ফায়ার স্টেশন", "01901023959", "station", "Pirojpur Sadar"),
    ("Pirojpur", "মঠবাড়িয়া ফায়ার স্টেশন", "01901023963", "station", "Mathbaria"),
    ("Pirojpur", "ভান্ডারিয়া ফায়ার স্টেশন", "01901023961", "station", "Bhandaria"),
    ("Pirojpur", "কাউখালি ফায়ার স্টেশন", "01901023967", "station", "Kawkhali"),
    ("Pirojpur", "নাজিরপুর ফায়ার স্টেশন", "01901023965", "station", "Nazirpur"),
    ("Pirojpur", "নেছারাবাদ ফায়ার স্টেশন", "01901023969", "station", "Nesarabad"),
    ("Pirojpur", "জিয়ানগর ফায়ার স্টেশন", "01901023973", "station", "Indurkani"),
    ("Jhalokathi", "উপ সহকারী পরিচালক ঝালকাঠী", "01901023905", "office", ""),
    ("Jhalokathi", "ঝালকাঠি ফায়ার স্টেশন", "01901023951", "station", "Jhalokathi Sadar"),
    ("Jhalokathi", "নলছিটি ফায়ার স্টেশন", "01901023955", "station", "Nalchity"),
    ("Jhalokathi", "কাঠালিয়া ফায়ার স্টেশন", "01901023953", "station", "Kanthalia"),
    ("Jhalokathi", "রাজাপুর ফায়ার স্টেশন", "01901023957", "station", "Rajapur"),
    ("Bhola", "উপ সহকারী পরিচালক ভোলা", "01901023906", "office", ""),
    ("Bhola", "ভোলা ফায়ার স্টেশন", "01901023975", "station", "Bhola Sadar"),
    ("Bhola", "বোরহানউদ্দিন ফায়ার স্টেশন", "01901023979", "station", "Burhanuddin"),
    ("Bhola", "চরফ্যাশন ফায়ার স্টেশন", "01901023981", "station", "Char Fasson"),
    ("Bhola", "লালমোহন ফায়ার স্টেশন", "01901023985", "station", "Lalmohan"),
    ("Bhola", "দৌলতখান ফায়ার স্টেশন", "01901023983", "station", "Daulatkhan"),
    ("Bhola", "তজুমদ্দিন ফায়ার স্টেশন", "01901023989", "station", "Tazumuddin"),
    ("Bhola", "মনপুরা ফায়ার স্টেশন", "01901023987", "station", "Manpura"),
    ("Patuakhali", "সহকারী পরিচালক পটুয়াখালী", "01901020164", "office", ""),
    ("Patuakhali", "পটুয়াখালি সদর ফায়ার স্টেশন", "01901023995", "station", "Patuakhali Sadar"),
    ("Patuakhali", "পটুয়াখালি নদী ফায়ার স্টেশন", "01901023997", "station", ""),
    ("Patuakhali", "বাউফল ফায়ার স্টেশন", "01901023999", "station", "Bauphal"),
    ("Patuakhali", "মির্জাগঞ্জ ফায়ার স্টেশন", "01901024007", "station", "Mirzaganj"),
    ("Patuakhali", "খেপুপাড়া ফায়ার স্টেশন", "01901024009", "station", ""),
    ("Patuakhali", "দশমিনা ফায়ার স্টেশন", "01901024001", "station", "Dashmina"),
    ("Patuakhali", "গলাচিপা ফায়ার স্টেশন", "01901024015", "station", "Galachipa"),
    ("Barguna", "উপ সহকারী পরিচালক বরগুনা", "01901023907", "office", ""),
    ("Barguna", "বরগুনা ফায়ার স্টেশন", "01901024017", "station", "Barguna Sadar"),
    ("Barguna", "আমতলী ফায়ার স্টেশন", "01901024019", "station", "Amtali"),
    ("Barguna", "পাথরঘাটা ফায়ার স্টেশন", "01901024021", "station", "Patharghata"),
    ("Barguna", "বামনা ফায়ার স্টেশন", "01901024023", "station", "Bamna"),
    ("Barguna", "বেতাগী ফায়ার স্টেশন", "01901024025", "station", "Betagi"),
    ("Barguna", "তালতলী ফায়ার স্টেশন", "01901024027", "station", "Taltali"),
]
_PTK_HEAD = "the PDF heads this table 'পিরোজপুর জেলা' (Pirojpur), but its rows are Patuakhali's offices and stations"
T_NOTES_BARISHAL = {
    "উপপরিচালক": "printed 'উপপরিচালক' without a place name, in the Barishal District table",
    "সহকারী পরিচালক": "printed 'সহকারী পরিচালক' without a place name, in the Barishal District table",
    "বরিশাল দক্ষিন ফায়ার স্টেশন": "printed 'বরিশাল দক্ষিন' (Barishal South); no upazila set",
    "বরিশাল নদী ফায়ার স্টেশন": "printed as 'বরিশাল নদী ফায়ার স্টেশন' (river fire station); no upazila set",
    "বানরিপাড়া ফায়ার স্টেশ": "printed 'বানরিপাড়া ফায়ার স্টেশ' (sic) in the PDF (Banaripara)",
    "জিয়ানগর ফায়ার স্টেশন": "printed 'জিয়ানগর' (Zianagar), the former name of Indurkani upazila",
    "ঝালকাঠি ফায়ার স্টেশন": "named after the district town; upazila set to the Sadar upazila",
    "পিরোজপুর ফায়ার স্টেশন": "named after the district town; upazila set to the Sadar upazila",
    "ভোলা ফায়ার স্টেশন": "named after the district town; upazila set to the Sadar upazila",
    "বরগুনা ফায়ার স্টেশন": "named after the district town; upazila set to the Sadar upazila",
    "পটুয়াখালি নদী ফায়ার স্টেশন": "printed as 'পটুয়াখালি নদী ফায়ার স্টেশন' (river fire station); no upazila set; " + _PTK_HEAD,
    "খেপুপাড়া ফায়ার স্টেশন": "named after a locality (খেপুপাড়া); no upazila set; " + _PTK_HEAD,
    "সহকারী পরিচালক পটুয়াখালী": _PTK_HEAD, "পটুয়াখালি সদর ফায়ার স্টেশন": _PTK_HEAD, "বাউফল ফায়ার স্টেশন": _PTK_HEAD,
    "মির্জাগঞ্জ ফায়ার স্টেশন": _PTK_HEAD, "দশমিনা ফায়ার স্টেশন": _PTK_HEAD, "গলাচিপা ফায়ার স্টেশন": _PTK_HEAD,
    "বাখেরগঞ্জ ফায়ার স্টেশন": "spelt 'বাখেরগঞ্জ' in the PDF (Bakerganj)",
}
# Sylhet Division PDF ("ফায়ার সার্ভিস ও সিভিল ডিফেন্স, সিলেট বিভাগ, সিলেট", Word export 2026-08-11, 2 pages, 4 district
# tables): same broken text layer; names transcribed by hand from the rendered pages, in PDF order; numbers as printed.
T_SYLHET = [
    ("Sylhet", "উপপরিচালক, সিলেট", "01901-020150", "office", ""),
    ("Sylhet", "সহকারী পরিচালক, বৃহওর সিলেট জেলা", "01901-020152", "office", ""),
    ("Sylhet", "উপসহকারী পরিচালক,সিলেট", "01901-023602", "office", ""),
    ("Sylhet", "সিলেট ফায়ার স্টেশন", "01901-023616", "station", "Sylhet Sadar"),
    ("Sylhet", "সিলেট দক্ষিণ ফায়ার স্টেশন", "01901-023628", "station", ""),
    ("Sylhet", "সিলেট সেনানিবাস ফায়ার স্টেশন", "01901-023618", "station", ""),
    ("Sylhet", "বিয়ানীবাজার ফায়ার স্টেশন", "01901-023634", "station", "Beanibazar"),
    ("Sylhet", "জকিগঞ্জ ফায়ার স্টেশন", "01901-023636", "station", "Zakiganj"),
    ("Sylhet", "ওসমানীনগর ফায়ার স্টেশন", "01901-023638", "station", "Osmani Nagar"),
    ("Sylhet", "ফেঞ্চুগঞ্জ ফায়ার স্টেশন", "01901-023640", "station", "Fenchuganj"),
    ("Sylhet", "গোলাপগঞ্জ ফায়ার স্টেশন", "01901-023642", "station", "Golapganj"),
    ("Sylhet", "জৈন্তাপুর ফায়ার স্টেশন", "01901-023644", "station", "Jaintiapur"),
    ("Sylhet", "কানাইঘাট ফায়ার স্টেশন", "01901-023646", "station", "Kanaighat"),
    ("Sylhet", "বিশ্বনাথ ফায়ার স্টেশন", "01901-023648", "station", "Bishwanath"),
    ("Sylhet", "কোম্পানীগঞ্জ ফায়ার স্টেশন", "01901-023650", "station", "Companiganj"),
    ("Sunamganj", "উপসহকারী পরিচালক,সুনামগঞ্জ", "01901-023605", "office", ""),
    ("Sunamganj", "সুনামগঞ্জ ফায়ার স্টেশন", "01901-023698", "station", "Sunamganj Sadar"),
    ("Sunamganj", "ছাতক ফায়ার স্টেশন", "01901-023700", "station", "Chhatak"),
    ("Sunamganj", "জগন্নাথপুর ফায়ার স্টেশন", "01901-023704", "station", "Jagannathpur"),
    ("Sunamganj", "দক্ষিণ সুনামগঞ্জ ফায়ার স্টেশন", "01901-023706", "station", "South Sunamganj"),
    ("Sunamganj", "দিরাই ফায়ার স্টেশন", "01901-023708", "station", "Derai"),
    ("Sunamganj", "বিশ্বম্ভরপুর ফায়ার স্টেশন", "01901-023710", "station", "Bishwambarpur"),
    ("Sunamganj", "দোয়ারাবাজার ফায়ার স্টেশন", "01901-023712", "station", "Dowarabazar"),
    ("Sunamganj", "তাহিরপুর ফায়ার স্টেশন", "01901-023714", "station", "Tahirpur"),
    ("Sunamganj", "ধর্মপাশা ফায়ার স্টেশন", "01901-023716", "station", "Dharmapasha"),
    ("Sunamganj", "জামালগঞ্জ ফায়ার স্টেশন", "01901-023720", "station", "Jamalganj"),
    ("Sunamganj", "শাল্লা ফায়ার স্টেশন", "01901-023722", "station", "Shalla"),
    ("Moulvibazar", "উপসহকারী পরিচালক, মৌলভীবাজার", "01901-023603", "office", ""),
    ("Moulvibazar", "মৌলভীবাজার ফায়ার স্টেশন", "01901-023658", "station", "Moulvibazar Sadar"),
    ("Moulvibazar", "কুলাউড়া ফায়ার স্টেশন", "01901-023664", "station", "Kulaura"),
    ("Moulvibazar", "কমলগঞ্জ ফায়ার স্টেশন", "01901-023666", "station", "Kamalganj"),
    ("Moulvibazar", "শ্রীমঙ্গল ফায়ার স্টেশন", "01901-023668", "station", "Sreemangal"),
    ("Moulvibazar", "বড়লেখা ফায়ার স্টেশন", "01901-023670", "station", "Barlekha"),
    ("Moulvibazar", "রাজনগর ফায়ার স্টেশন", "01901-023672", "station", "Rajnagar"),
    ("Moulvibazar", "জুড়ী ফায়ার স্টেশন", "01901-023674", "station", "Juri"),
    ("Habiganj", "উপসহকারী পরিচালক, হবিগঞ্জ", "01901-023604", "office", ""),
    ("Habiganj", "হবিগঞ্জ ফায়ার স্টেশন", "01901-023678", "station", "Habiganj Sadar"),
    ("Habiganj", "বানিয়াচং ফায়ার স্টেশন", "01901-023680", "station", "Baniachong"),
    ("Habiganj", "মাধবপুর ফায়ার স্টেশন", "01901-023682", "station", "Madhabpur"),
    ("Habiganj", "নবীগঞ্জ ফায়ার স্টেশন", "01901-023686", "station", "Nabiganj"),
    ("Habiganj", "শায়েস্তাগঞ্জ ফায়ার স্টেশন", "01901-023688", "station", "Shayestaganj"),
    ("Habiganj", "চুনারুঘাট ফায়ার স্টেশন", "01901-023690", "station", "Chunarughat"),
    ("Habiganj", "লাখাই স্থলকাম-নদী ফায়ার স্টেশন", "01901023692", "station", "Lakhai"),
    ("Habiganj", "বাহুবল ফায়ার স্টেশন", "01901023696", "station", "Bahubal"),
]
_TOWN = "named after the district town; upazila set to the Sadar upazila"
T_NOTES_SYLHET = {
    "সহকারী পরিচালক, বৃহওর সিলেট জেলা": "printed 'বৃহওর' (for বৃহত্তর, 'greater'): 'সহকারী পরিচালক, বৃহত্তর সিলেট জেলা'",
    "সিলেট ফায়ার স্টেশন": _TOWN, "সুনামগঞ্জ ফায়ার স্টেশন": _TOWN, "মৌলভীবাজার ফায়ার স্টেশন": _TOWN,
    "হবিগঞ্জ ফায়ার স্টেশন": _TOWN,
    "সিলেট দক্ষিণ ফায়ার স্টেশন": "printed 'সিলেট দক্ষিণ' (Sylhet South); no upazila set",
    "সিলেট সেনানিবাস ফায়ার স্টেশন": "printed 'সিলেট সেনানিবাস' (Sylhet Cantonment); no upazila set",
    "দক্ষিণ সুনামগঞ্জ ফায়ার স্টেশন": "upazila 'South Sunamganj' (দক্ষিণ সুনামগঞ্জ; also called Shantiganj)",
    "ধর্মপাশা ফায়ার স্টেশন": "printed as serial 11 of the Sunamganj table, after serial 09 (no serial 10 is printed)",
    "লাখাই স্থলকাম-নদী ফায়ার স্টেশন": "printed 'স্থলকাম-নদী' (land-cum-river station; the national page counts one such station in Sylhet Division)",
}
# Mymensingh Division PDF ("ফায়ার সার্ভিস ও সিভিল ডিফেন্স, ময়মনসিংহ বিভাগ, ময়মনসিংহ", Word export 2026-08-11, 2 pages,
# 4 district tables): same broken text layer; names transcribed by hand from the rendered pages, in PDF order; numbers as printed.
T_MYMENSINGH = [
    ("Mymensingh", "উপপরিচালক, ময়মনসিংহ", "01980271354", "office", ""),
    ("Mymensingh", "সহকারী পরিচালক, ময়মনসিংহ", "01819848030", "office", ""),
    ("Mymensingh", "উপসহকারী পরিচালক, ময়মনসিংহ", "01730002353", "office", ""),
    ("Mymensingh", "ময়মনসিংহ ফায়ার স্টেশন", "01901024217", "station", "Mymensingh Sadar"),
    ("Mymensingh", "মুক্তাগাছা ফায়ার স্টেশন", "01901024225", "station", "Muktagacha"),
    ("Mymensingh", "ঈশ্বরগঞ্জ ফায়ার স্টেশন", "01901024235", "station", "Iswarganj"),
    ("Mymensingh", "ভালুকা ফায়ার স্টেশন", "01901024229", "station", "Bhaluka"),
    ("Mymensingh", "ফুলবাড়ীয়া ফায়ার স্টেশন", "01901024239", "station", "Fulbaria"),
    ("Mymensingh", "ফুলপুর ফায়ার স্টেশন", "01901024241", "station", "Phulpur"),
    ("Mymensingh", "গফরগাঁও ফায়ার স্টেশন", "01901024231", "station", "Gafargaon"),
    ("Mymensingh", "হালুয়াঘাট ফায়ার স্টেশন", "01901024243", "station", "Haluaghat"),
    ("Mymensingh", "ত্রিশাল ফায়ার স্টেশন", "01901024245", "station", "Trishal"),
    ("Mymensingh", "ধোবাউড়া ফায়ার স্টেশন", "01901024247", "station", "Dhobaura"),
    ("Mymensingh", "নান্দাইল ফায়ার স্টেশন", "01901024249", "station", "Nandail"),
    ("Mymensingh", "কৃষিবিশ্ববিদ্যালয় ফায়ার স্টেশন", "01901024225", "station", ""),
    ("Mymensingh", "গৌরীপুর ফায়ার স্টেশন", "01901024253", "station", "Gouripur"),
    ("Jamalpur", "সহকারী পরিচালক, জামালপুর", "01901020174", "office", ""),
    ("Jamalpur", "জামালপুর ফায়ার স্টেশন", "01901024275", "station", "Jamalpur Sadar"),
    ("Jamalpur", "সরিষাবাড়ী ফায়ার স্টেশন", "01901024293", "station", "Sarishabari"),
    ("Jamalpur", "ইসলামপুর ফায়ার স্টেশন", "01901024285", "station", "Islampur"),
    ("Jamalpur", "মেলান্দহ ফায়ার স্টেশন", "01901024290", "station", "Melandah"),
    ("Jamalpur", "দেওয়ানগঞ্জ ফায়ার স্টেশন", "01901024283", "station", "Dewangonj"),
    ("Jamalpur", "মাদারগঞ্জ ফায়ার স্টেশন", "01901024289", "station", "Madarganj"),
    ("Jamalpur", "বকশীগঞ্জ ফায়ার স্টেশন", "01901024297", "station", "Bokshiganj"),
    ("Sherpur", "উপসহকারী পরিচালক, শেরপুর", "01901024204", "office", ""),
    ("Sherpur", "শেরপুর ফায়ার স্টেশন", "01901024299", "station", "Sherpur Sadar"),
    ("Sherpur", "নালিতাবাড়ী ফায়ার স্টেশন", "01901024305", "station", "Nalitabari"),
    ("Sherpur", "ঝিনাইগাতী ফায়ার স্টেশন", "01901024301", "station", "Jhenaigati"),
    ("Sherpur", "শ্রীবরদী ফায়ার স্টেশন", "01901024311", "station", "Sreebordi"),
    ("Netrokona", "উপসহকারী পরিচালক, নেত্রকোনা", "01718092909", "office", ""),
    ("Netrokona", "নেত্রকোনা ফায়ার স্টেশন", "01901024255", "station", "Netrokona Sadar"),
    ("Netrokona", "মোহনগঞ্জ ফায়ার স্টেশন", "01901024269", "station", "Mohongonj"),
    ("Netrokona", "কেন্দুয়া ফায়ার স্টেশন", "01901024265", "station", "Kendua"),
    ("Netrokona", "কলমাকান্দা ফায়ার স্টেশন", "01901024263", "station", "Kalmakanda"),
    ("Netrokona", "মদন ফায়ার স্টেশন", "01901024267", "station", "Madan"),
    ("Netrokona", "দুর্গাপুর ফায়ার স্টেশন", "01901024261", "station", "Durgapur"),
    ("Netrokona", "আটপাড়া ফায়ার স্টেশন", "01901024257", "station", "Atpara"),
    ("Netrokona", "বারহাট্টা ফায়ার স্টেশন", "01901024259", "station", "Barhatta"),
    ("Netrokona", "পূর্বধলা ফায়ার স্টেশন", "01901024271", "station", "Purbadhala"),
]
_SAME_NO = "printed with the same number (01901024225) as %s; kept as printed"
T_NOTES_MYMENSINGH = {
    "ময়মনসিংহ ফায়ার স্টেশন": _TOWN, "জামালপুর ফায়ার স্টেশন": _TOWN, "শেরপুর ফায়ার স্টেশন": _TOWN,
    "নেত্রকোনা ফায়ার স্টেশন": _TOWN,
    "উপসহকারী পরিচালক, ময়মনসিংহ": "the same number (01730-002353) is listed for the Mymensingh divisional control room on fireservice.gov.bd",
    "মুক্তাগাছা ফায়ার স্টেশন": _SAME_NO % "কৃষিবিশ্ববিদ্যালয় ফায়ার স্টেশন",
    "কৃষিবিশ্ববিদ্যালয় ফায়ার স্টেশন": (_SAME_NO % "মুক্তাগাছা ফায়ার স্টেশন") + "; printed 'কৃষিবিশ্ববিদ্যালয়' "
        "(Krishi Bishwabidyalay, i.e. the agricultural-university area); no upazila set",
    "নান্দাইল ফায়ার স্টেশন": "printed as serial 15 of the Mymensingh table, after serial 13 (no serial 14 is printed)",
}
# per division: (label in the national tables, transcription, divisional portal page or None, vehicle-table column, folder name word)
BY_DIV = {
    "rajshahi": dict(bn="রাজশাহী", T=None, portal=URL_DIV_PORTAL, veh_col=5),
    "rangpur": dict(bn="রংপুর", T=T_RANGPUR, portal=None, veh_col=6),
    # Dhaka: also re-checks the one landline in the list (Secretariat); row remarks in T_NOTES_DHAKA
    "dhaka": dict(bn="ঢাকা", T=T_DHAKA, portal=None, veh_col=2, notes=T_NOTES_DHAKA, landline=True),
    # Chattogram: some numbers are printed with 12 digits ('long_numbers': re-checked as printed, phone left empty)
    "chattogram": dict(bn="চট্টগ্রাম", T=T_CHATTOGRAM, portal=None, veh_col=4, notes=T_NOTES_CHATTOGRAM, long_numbers=True),
    # Khulna: one number is printed with 9 digits ('phone_re' widens the re-check so it is still found; phone left empty)
    "khulna": dict(bn="খুলনা", T=T_KHULNA, portal=None, veh_col=7, notes=T_NOTES_KHULNA, phone_re=r"01\d{3}-?\d{4,7}"),
    "barishal": dict(bn="বরিশাল", T=T_BARISHAL, portal=None, veh_col=8, notes=T_NOTES_BARISHAL),
    # Sylhet: 'station_type' tells land-cum-river (স্থলকাম-নদী) stations from river stations
    "sylhet": dict(bn="সিলেট", T=T_SYLHET, portal=None, veh_col=9, notes=T_NOTES_SYLHET, land_cum_river=True),
    # Mymensingh: the vehicle table's column is headed 'মঃসিংহ'
    "mymensingh": dict(bn="ময়মনসিংহ", T=T_MYMENSINGH, portal=None, veh_col=3, notes=T_NOTES_MYMENSINGH),
}
DIVISION, HEAD, CODE = "rajshahi", "Rajshahi", "raj"
DIV_BN = {"Rajshahi": "রাজশাহী", "Chapainawabganj": "চাঁপাইনবাবগঞ্জ", "Natore": "নাটোর", "Naogaon": "নওগাঁ",
          "Bogura": "বগুড়া", "Joypurhat": "জয়পুরহাট", "Pabna": "পাবনা", "Sirajganj": "সিরাজগঞ্জ"}


def digits(s):
    return re.sub(r"\D", "", asc(s))


def find_pdf_url():
    r = get(URL_ALL_NUMBERS)
    if r is None or not r.ok:
        return PDF_FALLBACK
    # table rows: ক্রঃ নং | বিভাগের নাম | ডাউনলোড(link)
    for tr in re.findall(r"<tr\b.*?</tr>", r.text, flags=re.S):
        if BY_DIV[DIVISION]["bn"] in clean(tr):
            m = re.search(r'href="(https://objectstorage[^"]+\.pdf)"', tr)
            if m:
                return m.group(1)
    return PDF_FALLBACK


def main():
    global HERE, RAW, KEY, T, URL_DIV_PORTAL, DIVISION, HEAD, CODE
    args, out, KEY = division_setup(HERE, KEY, list(BY_DIV))
    HERE, RAW = Path(out), Path(out) / "raw"
    DIVISION, HEAD, CODE = args.division, args.division.capitalize(), DIVISION_CODES[args.division]
    cfg = BY_DIV[DIVISION]
    T, URL_DIV_PORTAL = cfg["T"] or T, cfg["portal"]
    bn = cfg["bn"]
    pdf_name = "fscd_%s_division_numbers.pdf" % DIVISION
    places, facts = [], []
    pdf_url = find_pdf_url()
    pdf_note = ""
    live_phones = None
    r = get(pdf_url)
    if r is not None and r.ok and r.content[:4] == b"%PDF":
        p = save_raw(pdf_name, r.content)
        txt = pdftotext(p)
        if txt and DIVISION != "rajshahi":
            txt = asc(txt)  # this PDF's text layer prints the numbers in Bangla (some mixed) digits
        if txt:
            live_phones = [digits(x) for x in re.findall(cfg.get("phone_re") or (r"01\d{3}-?\d{6,7}" if cfg.get("long_numbers") else r"01\d{3}-?\d{6}"), txt)]
            if cfg.get("landline"):
                live_phones += [digits(x) for x in re.findall(r"\b0\d{1,2}-\d{7}\b", txt)]
    else:
        pdf_note = "PDF could not be downloaded this run; rows come from the transcription table. "
    known = {digits(t[2]) for t in T}
    if live_phones is not None:
        missing = [t for t in T if digits(t[2]) not in live_phones]
        new = [x for x in live_phones if x not in known]
        if missing or new:
            print("WARNING: PDF changed. missing:", [m[1] for m in missing], "new numbers:", new)
            pdf_note += f"PDF changed since transcription: new numbers {new} not transcribed. "
    else:
        missing = []
        print("pdftotext not available or PDF missing: numbers not re-verified this run")

    # Rajshahi divisional FSCD portal (cross-check for Rajshahi District)
    alt, ctrl_landlines = {}, []
    rp = get(URL_DIV_PORTAL) if URL_DIV_PORTAL else None
    if rp is not None and rp.ok:
        ctrl_landlines = sorted(set(re.findall(r"02588-\d{6}", asc(rp.text))))
        for t in tables(rp.text):
            for row in t:
                if len(row) >= 3 and "ফায়ার স্টেশন" in row[1]:
                    alt[row[1]] = [phone_norm(c) for c in row[2:] if phone_norm(c)]
    alt_by_phone = {}
    for nm, ph in alt.items():
        for x in ph:
            alt_by_phone[digits(x)] = (nm, ph)

    counts, used_ids = {}, set()
    for i, (dist, name, phone, kind, upa) in enumerate(T, 1):
        if t_missing := [m for m in missing if m[2] == phone]:
            continue  # number no longer in live PDF
        d = digits(phone)
        ph = phone if "-" in phone else f"{d[:5]}-{d[5:]}"
        extra = {"fscd_division": HEAD, "list": "নতুন যোগাযোগ নাম্বার", "pdf_serial_order": i}
        if DIVISION != "rajshahi" and d.startswith("01") and len(d) != 11:  # misprinted mobile number: not usable as a phone
            extra["phone_as_printed"], ph, phone = phone, "", ""
        notes = []
        if kind == "station":
            counts[dist] = counts.get(dist, 0) + 1
            cat = "emergency.fire_station"
            if upa:
                notes.append("upazila_en inferred from the station name (source gives district only)")
            if cfg.get("land_cum_river") and re.search(r"স্থল\s*-?\s*কাম", name):
                extra["station_type"] = "land-cum-river (স্থলকাম-নদী) fire station"
            elif "নদী" in name:
                extra["station_type"] = "river (নদী) fire station"
        else:
            cat = "government"
            extra["office_post"] = True
            notes.append("row is an FSCD office post (Deputy/Assistant/Deputy-Assistant Director) listed with an official number; office address not given in the PDF")
        if phone != ph:
            notes.append(f"number printed without hyphen in PDF ({phone})")
        if DIVISION != "rajshahi":
            notes.append(f"name transcribed from the rendered PDF page (text layer has broken Bangla glyphs)")
            tn = cfg.get("notes", T_NOTES)
            for k in (name, f"{name}|{phone}"):
                if k in tn and (k != "ফুলবাড়ী ফায়ার স্টেশন" or dist != "Dinajpur"):
                    notes.append(tn[k])
        sid = f"fscd-{CODE}-{d}"
        if sid in used_ids:  # same number printed for two rows: keep both, disambiguate the id by district
            sid = f"{sid}-{dist.lower()}"
        used_ids.add(sid)
        if d in alt_by_phone:
            anm, aph = alt_by_phone[d]
            if anm != name:
                extra["name_on_divisional_portal"] = anm
            others = [x for x in aph if digits(x) != d]
            if others:
                extra["other_numbers_divisional_portal"] = others
                notes.append("fireservice.rajshahi.gov.bd also lists " + ", ".join(others) +
                             " for this station; fireservice.gov.bd lists 01730-336655 as the Rajshahi divisional control-room mobile")
        elif dist == "Rajshahi" and kind == "station" and alt:
            notes.append("not listed on fireservice.rajshahi.gov.bd station-number page")
        places.append(dict(source_key=KEY, source_id=sid, name_bn=nfc(name), name_en="", category_key=cat,
                           district_en=dist, upazila_en=upa, phone=ph, operator="ফায়ার সার্ভিস ও সিভিল ডিফেন্স অধিদপ্তর",
                           ownership="public", extra_json=xj(extra), source_url=pdf_url,
                           notes=(pdf_note + "; ".join(notes)).strip()))

    # Divisional control room (fireservice.gov.bd control-room page)
    rc = get(URL_CONTROL)
    if rc is not None and rc.ok:
        for t in tables(rc.text):
            for row in t:
                if row and row[0].startswith(f"{bn} নিয়ন্ত্রণ কক্ষ") and len(row) > 1:
                    places.append(dict(source_key=KEY, source_id=f"fscd-{CODE}-control-room",
                                       name_bn=f"ফায়ার সার্ভিস ও সিভিল ডিফেন্স, {bn} নিয়ন্ত্রণ কক্ষ", name_en="",
                                       category_key="emergency", district_en=HEAD, phone=phone_norm(row[1]),
                                       operator="ফায়ার সার্ভিস ও সিভিল ডিফেন্স অধিদপ্তর", ownership="public",
                                       extra_json=xj({"label_in_source": row[0], "role": f"divisional control room ({HEAD} division)",
                                                      "landlines_on_divisional_portal": ctrl_landlines}),
                                       source_url=URL_CONTROL,
                                       notes=("Name composed from the table label 'রাজশাহী নিয়ন্ত্রণ কক্ষ' on the FSCD control-room page. "
                                              "fireservice.rajshahi.gov.bd prints the divisional control room landlines in the new 02588-85xxxx format "
                                              "while fireservice.gov.bd still prints 0721-77xxxx; 01730-336655 appears on both.") if DIVISION == "rajshahi" else
                                             f"Name composed from the table label '{row[0]}' on the FSCD control-room page."))

    # Station counts per district (counted from the PDF list)
    for dist, n in counts.items():
        facts.append(dict(entity_level="district", entity_name_en=dist, district_en=dist, fact="fire_stations_listed",
                          value=n, unit="stations", basis="counted from station-number list", year=2026, source_key=KEY,
                          source_url=pdf_url, notes=f"Count of 'ফায়ার স্টেশন' rows in the {HEAD}-division number list (PDF dated 2026-08-11)"))

    # National page with station counts per class by division (Rajshahi row)
    rn = get(URL_COUNTS)
    if rn is not None and rn.ok:
        heads = ["বিশেষ শ্রেণীভুক্ত", "এ-শ্রেণীভুক্ত", "বি-শ্রেণীভুক্ত", "বি স্থল কাম নদী", "সি-শ্রেণীভুক্ত", "নদী ফায়ার স্টেশন", "মোট"]
        keys = ["fire_stations_special_class", "fire_stations_class_a", "fire_stations_class_b", "fire_stations_class_b_land_cum_river",
                "fire_stations_class_c", "fire_stations_river", "fire_stations_total"]
        for t in tables(rn.text):
            for row in t:
                if len(row) >= 9 and row[1].startswith(f"{bn} বিভাগ"):
                    for k, h, v in zip(keys, heads, row[2:9]):
                        facts.append(dict(entity_level="division", entity_name_en=HEAD, fact=k, value=asc(v), unit="stations",
                                          basis="reported", year="", source_key=KEY, source_url=URL_COUNTS,
                                          notes=f"Column '{h}'; page total 'সর্বমোট চালুকৃত স্টেশন - ৫৩৮ টি' (national). Page undated."))
                if len(row) >= 6 and row[1] in ("এ্যাম্বুলেন্স", "পাম্প") or (row and row[0].startswith("অগ্নি নির্বাপনী ভিহিক্যাল")):
                    # columns: ক্রঃ নং | নাম | ঢাকা | মঃসিংহ | চট্রগ্রাম | রাজশাহী | রংপুর | ...
                    col = cfg["veh_col"]
                    if row[0].startswith("অগ্নি নির্বাপনী"):
                        val, label = row[col - 1], "vehicles_and_pumps_total"
                    else:
                        val, label = row[col], {"এ্যাম্বুলেন্স": "fscd_ambulances", "পাম্প": "fscd_pumps"}[row[1]]
                    facts.append(dict(entity_level="division", entity_name_en=HEAD, fact=label, value=asc(val), unit="units",
                                      basis="reported", year=2024, source_key=KEY, source_url=URL_COUNTS,
                                      notes=f"Vehicle/pump summary dated 20 Oct 2024 ({HEAD} column)"))
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    write_manifest(dict(
        key=KEY, division=DIVISION, kind="fscd", name=f"Fire Service & Civil Defence — {HEAD} Division station & office numbers",
        organization="Fire Service and Civil Defence Directorate (FSCD), Bangladesh", source_type="government_portal",
        trust_level=4, urls=[u for u in (URL_ALL_NUMBERS, pdf_url, URL_CONTROL, URL_COUNTS, URL_DIV_PORTAL) if u],
        accessed=__import__("datetime").date.today().isoformat(), publication_date="2026-08-11",
        license=None, license_url=None, attribution="Fire Service and Civil Defence Directorate, Bangladesh (fireservice.gov.bd)",
        notes="No licence stated on fireservice.gov.bd. publication_date = creation date in the PDF metadata. Station names were "
              "transcribed from the rendered PDF because its text layer has broken Bangla glyph mapping; phone numbers come from the "
              "text layer. No addresses or coordinates are published."), ["places.csv", "facts.csv", "raw/" + pdf_name])


if __name__ == "__main__":
    main()
