#!/usr/bin/env python3
"""Fetch Rajshahi-Division fire station & office numbers from fireservice.gov.bd (FSCD_STATIONS_RAJ_2026).

Usage: python3 fetch.py [--division rajshahi|rangpur] [--out DIR]   (default: Rajshahi into this folder; DIVISIONS.md)"""
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
    parts = [p.strip(" ,;/") for p in re.split(r"[,;/]|\s{2,}", s)]
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
# per division: (label in the national tables, transcription, divisional portal page or None, vehicle-table column, folder name word)
BY_DIV = {
    "rajshahi": dict(bn="রাজশাহী", T=None, portal=URL_DIV_PORTAL, veh_col=5),
    "rangpur": dict(bn="রংপুর", T=T_RANGPUR, portal=None, veh_col=6),
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
            live_phones = [digits(x) for x in re.findall(r"01\d{3}-?\d{6}", txt)]
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
        notes = []
        if kind == "station":
            counts[dist] = counts.get(dist, 0) + 1
            cat = "emergency.fire_station"
            if upa:
                notes.append("upazila_en inferred from the station name (source gives district only)")
            if "নদী" in name:
                extra["station_type"] = "river (নদী) fire station"
        else:
            cat = "government"
            extra["office_post"] = True
            notes.append("row is an FSCD office post (Deputy/Assistant/Deputy-Assistant Director) listed with an official number; office address not given in the PDF")
        if phone != ph:
            notes.append(f"number printed without hyphen in PDF ({phone})")
        if DIVISION != "rajshahi":
            notes.append(f"name transcribed from the rendered PDF page (text layer has broken Bangla glyphs)")
            for k in (name, f"{name}|{phone}"):
                if k in T_NOTES and (k != "ফুলবাড়ী ফায়ার স্টেশন" or dist != "Dinajpur"):
                    notes.append(T_NOTES[k])
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
