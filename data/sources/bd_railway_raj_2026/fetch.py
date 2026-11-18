#!/usr/bin/env python3
"""Fetch Bangladesh Railway station phones and district-wise station counts for Rajshahi Division (BD_RAILWAY_RAJ_2026).

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

# --- BD_RAILWAY_RAJ_2026 ------------------------------------------------------------------------------
KEY = "BD_RAILWAY_RAJ_2026"
URL_PHONES = "https://railway.gov.bd/pages/static-pages/691997be933eb65569ddebc6"     # গুরুত্বপূর্ন স্টেশনের টেলিফোন
URL_INFOBOOK_PAGE = "https://railway.gov.bd/pages/files/6919975c933eb65569ddc4da"     # ইনফরমেশন বুক
INFOBOOK_FALLBACK = ("https://objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/n/axvjbnqprylg/b/V2Ministry/o/"
                     "office-railway/2026/5/f526722f-5331-425f-b5a6-e13b91b509a3.pdf")
DISTRICTS = ["Bogura", "Chapainawabganj", "Joypurhat", "Naogaon", "Natore", "Pabna", "Rajshahi", "Sirajganj"]
# Table-4 "District-wise station & route kilometers", Information Book 2023-2024 (PDF page 46), transcribed for runs without pdftotext
TABLE4 = {"Bogura": (20, "84.850"), "Chapainawabganj": (8, "50.000"), "Joypurhat": (7, "45.500"), "Naogaon": (5, "18.100"),
          "Natore": (11, "77.070"), "Pabna": (21, "145.640"), "Rajshahi": (11, "70.000"), "Sirajganj": (8, "47.475")}
# Stations on the 'important stations' telephone page that lie in Rajshahi Division. The page gives only the station name;
# the district (and Rohanpur's upazila) is added here from the station's known location -> flagged in notes.
IN_DIVISION = {"রাজশাহী": ("Rajshahi", ""), "রাজশাহী কোর্ট": ("Rajshahi", ""), "চাঁপাই নবাবগঞ্জ": ("Chapainawabganj", ""),
               "রোহনপুর": ("Chapainawabganj", "Gomastapur"), "নাটোর": ("Natore", ""), "জয়পুরহাট": ("Joypurhat", ""),
               "বগুড়া": ("Bogura", ""), "ঈশ্বরদী": ("Pabna", "Ishwardi"), "সান্তাহার": ("Bogura", "Adamdighi"),
               "আব্দুলপুর": ("Natore", "Lalpur"), "পাবনা": ("Pabna", ""), "সিরাজগঞ্জ বাজার": ("Sirajganj", "")}

# Rangpur Division: same two railway.gov.bd sources; Table-4 values transcribed from the same Information Book page
BY_DIV = {
    "rajshahi": dict(districts=DISTRICTS, table4=TABLE4, stations=IN_DIVISION),
    "rangpur": dict(
        districts=["Dinajpur", "Gaibandha", "Kurigram", "Lalmonirhat", "Nilphamari", "Panchagarh", "Rangpur", "Thakurgaon"],
        table4={"Dinajpur": (24, "143.800"), "Gaibandha": (14, "80.950"), "Kurigram": (8, "42.500"), "Lalmonirhat": (15, "114.000"),
                "Nilphamari": (9, "65.300"), "Panchagarh": (3, "18.320"), "Rangpur": (9, "63.800"), "Thakurgaon": (6, "47.180")},
        stations={"বোনারপাড়া": ("Gaibandha", "Saghata"), "গাইবান্ধা": ("Gaibandha", ""), "রংপুর": ("Rangpur", ""),
                  "কুড়িগ্রাম": ("Kurigram", ""), "ঠাকুরগাঁও": ("Thakurgaon", ""), "নীলফামারী": ("Nilphamari", ""),
                  "সৈয়দপুর": ("Nilphamari", "Saidpur"), "দিনাজপুর": ("Dinajpur", ""), "পার্বতীপুর": ("Dinajpur", "Parbatipur"),
                  "লালমনিরহাট": ("Lalmonirhat", ""), "পঞ্চগড়": ("Panchagarh", "")}),
    # Dhaka Division: Manikganj has no railway (no Table-4 row); Table-4 spells Kishoreganj 'Kishorganj'
    "dhaka": dict(
        districts=["Dhaka", "Faridpur", "Gazipur", "Gopalganj", "Kishoreganj", "Madaripur", "Munshiganj", "Narayanganj",
                   "Narsingdi", "Rajbari", "Shariatpur", "Tangail"],
        table4={"Dhaka": (7, "45.560"), "Faridpur": (16, "109.690"), "Gazipur": (9, "99.580"), "Gopalganj": (10, "79.150"),
                "Kishoreganj": (12, "63.100"), "Madaripur": (1, "15.420"), "Munshiganj": (3, "27.260"), "Narayanganj": (4, "8.500"),
                "Narsingdi": (14, "39.000"), "Rajbari": (15, "89.900"), "Shariatpur": (1, "9.260"), "Tangail": (8, "87.525")},
        stations={"ঢাকা": ("Dhaka", ""), "তেজগাঁও": ("Dhaka", ""), "ঢাকা ক্যান্টনমেন্ট": ("Dhaka", ""),
                  "ঢাকা বিমান বন্দর": ("Dhaka", ""), "টঙ্গী": ("Gazipur", "Gazipur Sadar"), "নরসিংদী": ("Narsingdi", ""),
                  "ভৈরব বাজার": ("Kishoreganj", "Bhairab"), "কিশোরগঞ্জ": ("Kishoreganj", ""), "রাজবাড়ী": ("Rajbari", "")}),    # Chattogram Division: Lakshmipur, Rangamati, Khagrachhari and Bandarban have no railway (no Table-4 row); Table-4 spells
    # Cox's Bazar 'Coxbazar'; the phone page spells Brahmanbaria 'ব্রাহ্মণবাড়ীয়া'
    "chattogram": dict(
        districts=["Brahmanbaria", "Chandpur", "Chattogram", "Cox's Bazar", "Cumilla", "Feni", "Noakhali"],
        table4={"Brahmanbaria": (16, "66.600"), "Chandpur": (10, "52.050"), "Chattogram": (49, "176.830"),
                "Cox's Bazar": (6, "46.490"), "Cumilla": (18, "101.230"), "Feni": (13, "96.560"), "Noakhali": (7, "47.310")},
        stations={"ব্রাহ্মণবাড়ীয়া": ("Brahmanbaria", ""), "আশুগঞ্জ": ("Brahmanbaria", "Ashuganj"),
                  "আখাউড়া": ("Brahmanbaria", "Akhaura"), "কুমিল্লা": ("Cumilla", ""), "চাঁদপুর": ("Chandpur", ""),
                  "ফেনী": ("Feni", ""), "চট্টগ্রাম": ("Chattogram", "")}),
    # Khulna Division: Satkhira, Meherpur and Magura have no railway (no Table-4 row); Table-4 spells Jhenaidah 'Jhenaidaha'
    "khulna": dict(
        districts=["Bagerhat", "Chuadanga", "Jashore", "Jhenaidah", "Khulna", "Kushtia", "Narail"],
        table4={"Bagerhat": (6, "38.007"), "Chuadanga": (10, "56.600"), "Jashore": (12, "102.100"), "Jhenaidah": (5, "36.000"),
                "Khulna": (8, "51.050"), "Kushtia": (10, "79.520"), "Narail": (2, "29.500")},
        stations={nfc(k): v for k, v in {"কুষ্টিয়া": ("Kushtia", ""), "কুষ্টিয়া কোর্ট": ("Kushtia", ""), "যশোর": ("Jashore", ""),
                                         "বেনাপোল": ("Jashore", "Sharsha"), "খুলনা": ("Khulna", "")}.items()}),
    # Barishal Division: no railway. None of its six districts has a Table-4 row and no station of the division is on the
    # phone list, so the run writes empty places/facts (with headers) and keeps the two raw texts as evidence.
    "barishal": dict(districts=[], table4={}, stations={}),
    # Sylhet Division: all four districts have a Table-4 row (Sunamganj: the Chhatak branch)
    "sylhet": dict(
        districts=["Habiganj", "Moulvibazar", "Sunamganj", "Sylhet"],
        table4={"Habiganj": (14, "89.100"), "Moulvibazar": (11, "116.700"), "Sunamganj": (2, "13.300"), "Sylhet": (6, "49.400")},
        stations={nfc(k): v for k, v in {"শায়েস্তাগঞ্জ": ("Habiganj", "Shayestaganj"), "শ্রীমঙ্গল": ("Moulvibazar", "Sreemangal"),
                                         "কুলাউড়া": ("Moulvibazar", "Kulaura"), "সিলেট": ("Sylhet", ""),
                                         "হবিগঞ্জ": ("Habiganj", "")}.items()}),
    # Mymensingh Division: Sherpur has no railway (no Table-4 row); the phone page lists Netrokona, Mymensingh and Jamalpur
    "mymensingh": dict(
        districts=["Jamalpur", "Mymensingh", "Netrokona"],
        table4={"Jamalpur": (21, "107.000"), "Mymensingh": (20, "146.000"), "Netrokona": (17, "66.000")},
        stations={nfc(k): v for k, v in {"ময়মনসিংহ": ("Mymensingh", ""), "জামালপুর": ("Jamalpur", ""),
                                         "নেত্রকোনা": ("Netrokona", "")}.items()}),
}


def main():
    global HERE, RAW, KEY, DISTRICTS, TABLE4, IN_DIVISION
    args, out, KEY = division_setup(HERE, KEY, list(BY_DIV))
    HERE, RAW = Path(out), Path(out) / "raw"
    division, head = args.division, args.division.capitalize()
    DISTRICTS, TABLE4, IN_DIVISION = (BY_DIV[division][k] for k in ("districts", "table4", "stations"))
    places, facts = [], []
    r = get(URL_PHONES)
    if r is not None and r.ok:
        save_raw("railway_important_station_phones.txt", "\n".join(content_text(r.text)))
        for t in tables(r.text):
            for row in t:
                if len(row) >= 3 and nfc(row[1]) in IN_DIVISION and re.search(r"[০-৯0-9]{4}", row[2]):
                    nm = nfc(row[1])
                    dist, upa = IN_DIVISION[nm]
                    places.append(dict(
                        source_key=KEY, source_id=f"br-important-{asc(row[0]).strip()}", name_bn=nm, name_en="",
                        category_key="transport.railway_station", district_en=dist, upazila_en=upa, phone=phone_norm(row[2]),
                        operator="বাংলাদেশ রেলওয়ে", ownership="public",
                        extra_json=xj({"phone_type": "বিটিসিএল ফোন (BTCL landline)", "list": "গুরুত্বপূর্ন স্টেশনের টেলিফোন",
                                       "serial": asc(row[0]).strip()}),
                        source_url=URL_PHONES,
                        notes="Source gives the station name only; district" + (" and upazila" if upa else "") +
                              " added from the station's location (not stated by the source). Landline printed without area code."))
    # Information Book: district-wise stations & route km
    pdf_url = INFOBOOK_FALLBACK
    r = get(URL_INFOBOOK_PAGE)
    if r is not None and r.ok:
        links = re.findall(r'href="(https://objectstorage[^"]+\.pdf)"[^>]*>', r.text)
        # pick the link that follows the newest 'ইনফরমেশন বুক-YYYY' label
        best = None
        for m in re.finditer(r"ইনফরমেশন বুক-([০-৯0-9]{4}).*?href=\"(https://objectstorage[^\"]+\.pdf)\"", r.text, flags=re.S):
            y = int(asc(m.group(1)))
            if best is None or y > best[0]:
                best = (y, m.group(2))
        if best:
            pdf_url = best[1]
    table, basis_note = dict(TABLE4), "transcribed values (pdftotext unavailable)"
    r = get(pdf_url)
    if r is not None and r.ok and r.content[:4] == b"%PDF":
        tmp = HERE / "raw" / "_infobook.pdf"
        save_raw("_infobook.pdf", r.content)
        txt = None
        for page in range(40, 52):
            t = pdftotext(tmp, page, page)
            if t and "DISTRICT-WISE STATION" in t:
                txt = t
                break
        tmp.unlink(missing_ok=True)
        if txt:
            parsed = {}
            for m in re.finditer(r"\d+\.\s+([A-Za-z]+)\s+(\d+)\s+([\d.]+)", txt):
                name = {"Coxbazar": "Cox's Bazar", "Kishorganj": "Kishoreganj", "Jhenaidaha": "Jhenaidah"}.get(m.group(1), m.group(1))
                parsed[name] = (int(m.group(2)), m.group(3))
            if all(d in parsed for d in DISTRICTS):
                table, basis_note = {d: parsed[d] for d in DISTRICTS}, "parsed from PDF page text"
                save_raw("infobook_2023_24_table4.txt", txt)
            else:
                print("WARNING: could not parse Table-4; using transcribed values")
    for d in DISTRICTS:
        st, km = table[d]
        for fact, val, unit in (("railway_stations", st, "stations"), ("railway_route_km", km, "km")):
            facts.append(dict(entity_level="district", entity_name_en=d, district_en=d, fact=fact, value=val, unit=unit,
                              basis="reported", year=2024, source_key=KEY, source_url=pdf_url,
                              notes=f"Bangladesh Railway Information Book, Table-4 'District-wise station & route kilometers', end of FY 2023-2024; {basis_note}. "
                                    "Station count includes block huts, halts and goods booking points."))
    tot_st = sum(table[d][0] for d in DISTRICTS)
    tot_km = round(sum(float(table[d][1]) for d in DISTRICTS), 3)
    for fact, val, unit in ((("railway_stations", tot_st, "stations"), ("railway_route_km", tot_km, "km")) if DISTRICTS else ()):
        facts.append(dict(entity_level="division", entity_name_en=head, fact=fact, value=val, unit=unit,
                          basis="derived (sum of district rows)", year=2024, source_key=KEY, source_url=pdf_url,
                          notes=f"Sum of the {len(DISTRICTS)} {head}-division districts in Table-4 (FY 2023-2024)"))
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    files = ["places.csv", "facts.csv", "raw/railway_important_station_phones.txt"]
    if (RAW / "infobook_2023_24_table4.txt").exists():
        files.append("raw/infobook_2023_24_table4.txt")
    write_manifest(dict(
        key=KEY, division=division, kind="railway",
        name=f"Bangladesh Railway — station phones and district-wise station counts ({head} Division)",
        organization="Bangladesh Railway", source_type="government_portal", trust_level=4,
        urls=[URL_PHONES, URL_INFOBOOK_PAGE, pdf_url], accessed=__import__("datetime").date.today().isoformat(),
        publication_date=None, license=None, license_url=None, attribution="Bangladesh Railway (railway.gov.bd)",
        notes="No licence stated. railway.gov.bd publishes no station register (no per-station list with district/code/class); only "
              "an 'important stations' BTCL phone list and district-wise station counts in the annual Information Book (2023-24 "
              "edition, 1.5 MB PDF, not committed — fetch.py re-downloads it). eticket.railway.gov.bd robots.txt disallows all "
              "crawling, so its station list was not used. Timetable/fare files list stops but are not a station registry."),
        files)


if __name__ == "__main__":
    main()
