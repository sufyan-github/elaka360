#!/usr/bin/env python3
"""Fetch thana / SP-office / control-room numbers for RMP and Rajshahi Range from the Police HQ contact workbook (BD_POLICE_CONTACTS_2020).

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

# --- BD_POLICE_CONTACTS_2020 --------------------------------------------------------------------------
import io, zipfile, xml.etree.ElementTree as ET
KEY = "BD_POLICE_CONTACTS_2020"
URL_PAGE = "https://www.police.gov.bd/en/contacts_of_bangladesh_police_-pdf"
XLSX_FALLBACK = "https://www.police.gov.bd/storage/upload/announcement/EcDDy28T7DJdOqyuVB2CSiTjUAX8kTiy1HBoOPHj.xlsx"
SHEETS = ["RMP", "Rajshahi Range"]
DIST = {"Rajshahi": "Rajshahi", "Naogaon": "Naogaon", "Natore": "Natore", "Chapainawabganj": "Chapainawabganj",
        "Bogura": "Bogura", "Joypurhat": "Joypurhat", "Pabna": "Pabna", "Sirajgonj": "Sirajganj"}
# source spelling of the thana (after removing 'OC', 'Model', 'PS'/'Thana') -> standard upazila (or RMP thana) name
UPA = {
    "RMP": {"Bowalia": "Boalia", "Rajapara": "Rajpara", "Chandrima": "Chandrima", "Motihar": "Motihar", "Katakhali": "Katakhali",
            "Belpukur": "Belpukur", "Shah Mokhdum": "Shah Makhdum", "Airport": "Airport", "Paba": "Paba",
            "Kashiadanga": "Kashiadanga", "Damkura": "Damkura", "Karnohar": "Karnahar"},
    "Rajshahi": {"Godogari": "Godagari", "Tanor": "Tanore", "Mohonpur": "Mohanpur", "Puthia": "Puthia", "Bagmara": "Bagmara",
                 "Durgapur": "Durgapur", "Charghat": "Charghat", "Bagha": "Bagha"},
    "Naogaon": {"Sador": "Naogaon Sadar", "Raninogor": "Raninagar", "Atrai": "Atrai", "Dhamoirhat": "Dhamoirhat",
                "Bodolgasi": "Badalgachhi", "Mohadeppur": "Mahadebpur", "Potnitola": "Patnitala", "Niamotpur": "Niamatpur",
                "Manda": "Manda", "Shapahar": "Sapahar", "Porsha": "Porsha"},
    "Natore": {"Natore": "Natore Sadar", "Singra": "Singra", "Bagatipara": "Bagatipara", "Gurodashpur": "Gurudaspur",
               "Lalpur": "Lalpur", "Boraigram": "Baraigram", "Noldnga": "Naldanga"},
    "Chapainawabganj": {"Sadar": "Chapainawabganj Sadar", "Shibganj": "Shibganj", "Gumostapur": "Gomastapur",
                        "Nachol": "Nachole", "Bholahat": "Bholahat"},
    "Bogura": {"Sador": "Bogura Sadar", "Shibgonj": "Shibganj", "Shonatola": "Sonatala", "Gabtoli": "Gabtali",
               "Shariakandhi": "Sariakandi", "Adhomdighi": "Adamdighi", "Dupchachia": "Dhupchanchia", "Kahalu": "Kahaloo",
               "Sherpur": "Sherpur", "Dhunot": "Dhunat", "Nondigram": "Nandigram", "Shahjahanpur": "Shajahanpur"},
    "Joypurhat": {"Sador": "Joypurhat Sadar", "Panchbibi": "Panchbibi", "Khetlal": "Khetlal", "Kalai": "Kalai", "Akkelpur": "Akkelpur"},
    "Pabna": {"Pabna": "Pabna Sadar", "Ishwardi": "Ishwardi", "Atgaoria": "Atgharia", "Chatmohor": "Chatmohar",
              "Vangura": "Bhangura", "Faridpur": "Faridpur", "Sujanagor": "Sujanagar", "Vera": "Bera", "Sathia": "Santhia"},
    "Sirajganj": {"Sirajgonj": "Sirajganj Sadar", "Shahjadpur": "Shahjadpur", "Ullapara": "Ullahpara", "Chowhali": "Chauhali",
                  "Tarash": "Tarash", "Kazipur": "Kazipur", "Kamarkhond": "Kamarkhanda", "Raygonj": "Raiganj", "Belkuchi": "Belkuchi"},
}
# Rangpur Division: sheets 'RRMP' (Rangpur Metropolitan Police) and 'Rangpur Range' (one block per district)
RANGPUR = dict(
    sheets=["RRMP", "Rangpur Range"], metro="Rangpur Metropolitan Police", metro_short="RpMP", head="Rangpur",
    dist={"Rangpur": "Rangpur", "Gaibandha": "Gaibandha", "Kurigram": "Kurigram", "Lalmonirhat": "Lalmonirhat",
          "Nilphamari": "Nilphamari", "Dinajpur": "Dinajpur", "Thakurgaon": "Thakurgaon", "Panchagarh": "Panchagarh"},
    upa={"RRMP": {"Kotwali": "Kotwali", "Tajhat": "Tajhat", "Mahiganj": "Mahiganj", "Haragach": "Haragachh",
                  "Poshuram": "Parshuram", "Hazirhat": "Hajirhat"},
         "Rangpur": {"Gangachara": "Gangachara", "Badarganj": "Badarganj", "Taraganj": "Taraganj", "Mithapukura": "Mithapukur",
                     "Pirganj": "Pirganj", "Pirgachha": "Pirgachha", "Kaunya": "Kaunia"},
         "Gaibandha": {"Gaibandha": "Gaibandha Sadar", "Sadullapur": "Sadullapur", "Sundarganj": "Sundarganj",
                       "Palashbari": "Palashbari", "Gobindaganj": "Gobindaganj", "Saghata": "Saghata", "Phulachari": "Phulchhari"},
         "Kurigram": {"Kurigram": "Kurigram Sadar", "Rajarhat": "Rajarhat", "Phulbari": "Phulbari", "Nageshwari": "Nageshwari",
                      "Bhurungabari": "Bhurungamari", "Ulipur": "Ulipur", "Chilmari": "Chilmari", "Roumari": "Raomari",
                      "Rajibpur": "Char Rajibpur"},
         "Lalmonirhat": {"Lalmonirhat": "Lalmonirhat Sadar", "Aditmari": "Aditmari", "Kaligonj": "Kaliganj",
                         "Hatibandha": "Hatibandha", "Patgram": "Patgram"},
         "Nilphamari": {"Nilphamari": "Nilphamari Sadar", "Syedpur": "Saidpur", "JalaDhaka": "Jaldhaka",
                        "Kishoreganj": "Kishoreganj", "Domar": "Domar", "Dimla": "Dimla"},
         "Dinajpur": {"Kotwali": "Dinajpur Sadar", "Chirirbandar": "Chirirbandar", "Birala": "Biral", "Parbatipur": "Parbatipur",
                      "Birganj": "Birganj", "BOChaganj": "Bochaganj", "Kaharol": "Kaharole", "Khansama": "Khansama",
                      "Phulbari": "Phulbari", "Birampur": "Birampur", "Nawabganj": "Nawabganj", "Ghoraghat": "Ghoraghat",
                      "Hakimpur": "Hakimpur"},
         "Thakurgaon": {"Thakurgaon": "Thakurgaon Sadar", "Baliadangi": "Baliadangi", "RaniShankail": "Ranisankail",
                        "Pirganj": "Pirganj", "Haripur": "Haripur"},
         "Panchagarh": {"Panchagarh": "Panchagarh Sadar", "Boda": "Boda", "Atwari": "Atwari", "Tetulia": "Tetulia",
                        "Debiganj": "Debiganj"}},
    raw="police_contacts_2020_rrmp_rangpur_range.csv")
# Dhaka Division: sheets 'DMP' (Dhaka Metropolitan Police), 'GMP' (Gazipur Metropolitan Police) and 'Dhaka Range' (one block per
# district; the range office and 'RRF, Dhaka' are not collected). Metro rows: upazila_en holds the metropolitan thana.
DHAKA = dict(
    sheets=["DMP", "GMP", "Dhaka Range"], range_sheet="Dhaka Range", head="Dhaka",
    metros={"DMP": ("Dhaka", "Dhaka Metropolitan Police", "DMP", "dmp"),
            "GMP": ("Gazipur", "Gazipur Metropolitan Police", "GMP", "gmp")},
    dist={"Dhaka": "Dhaka", "Narayanganj": "Narayanganj", "Narsingdi": "Narsingdi", "Gazipur": "Gazipur",
          "Munshiganj": "Munshiganj", "Manikganj": "Manikganj", "Kishoreganj": "Kishoreganj", "Tangail": "Tangail",
          "Faridpur": "Faridpur", "Madaripur": "Madaripur", "Gopalganj": "Gopalganj", "Soriotpur": "Shariatpur",
          "Rajbari": "Rajbari"},
    upa={"DMP": {"Ramna": "Ramna", "Shahbag": "Shahbagh", "Dhanmondi": "Dhanmondi", "New Market": "New Market",
                 "Hazaribag": "Hazaribagh", "Kalabagan": "Kalabagan", "Kotoali": "Kotwali", "Lalbag": "Lalbagh",
                 "Bongsal": "Bangshal", "Chakbazar": "Chawkbazar", "Kamrangirchar": "Kamrangirchar", "Sutrapur": "Sutrapur",
                 "Palton": "Paltan", "Motijheel": "Motijheel", "Sabujbag": "Sabujbagh", "Khilgaon": "Khilgaon",
                 "Rampura": "Rampura", "Mugdha": "Mugda", "Shahjahanpur": "Shahjahanpur", "Shampur": "Shyampur",
                 "Jatrabari": "Jatrabari", "Demra": "Demra", "Kodomtoli": "Kadamtali", "Gandaria": "Gendaria", "Wari": "Wari",
                 "Tejgaon": "Tejgaon", "Tejgaon Industrial": "Tejgaon Industrial Area", "Mohammadpur": "Mohammadpur",
                 "Adabor": "Adabor", "Sher-E-Bangla Nagar": "Sher-e-Bangla Nagar", "Hatirjheel": "Hatirjheel",
                 "Mirpur": "Mirpur", "Sha-ali": "Shah Ali", "Pallabi": "Pallabi", "Kafrul": "Kafrul", "Rupnagar": "Rupnagar",
                 "Vashantek": "Bhashantek", "Darussalam": "Darus Salam", "Gulshan": "Gulshan", "Badda": "Badda",
                 "Khilkhet": "Khilkhet", "Cantonment": "Cantonment", "Vatara": "Bhatara", "Banani": "Banani",
                 "Uttara East": "Uttara East", "Uttara West": "Uttara West", "Turag": "Turag", "Airport": "Airport",
                 "Dokkhin Khan": "Dakshinkhan", "Uttar Khan": "Uttarkhan"},
         "GMP": {"Sadar": "Gazipur Sadar", "Bason": "Basan", "Konabari": "Konabari", "Kasimpur": "Kashimpur",
                 "Gacha": "Gachha", "Pubail": "Pubail", "Tongi East": "Tongi East", "Tongi West": "Tongi West"},
         "Dhaka": {"Savar": "Savar", "Dhamrai": "Dhamrai", "Keraniganj": "Keraniganj", "Nobabgonj": "Nawabganj", "Dohar": "Dohar"},
         "Narayanganj": {"Sadar": "Narayanganj Sadar", "Bondar": "Bandar", "Rupgonj": "Rupganj", "Araihajar": "Araihazar",
                         "Shonargaon": "Sonargaon"},
         "Narsingdi": {"Narsingdi": "Narsingdi Sadar", "Palash": "Palash", "Shibpur": "Shibpur", "Monohardi": "Monohardi",
                       "Raipura": "Raipura", "Belabo": "Belabo"},
         "Gazipur": {"Joydebpur": "Gazipur Sadar", "Kaliakoir": "Kaliakair", "Shripur": "Sreepur", "Kapasia": "Kapasia",
                     "Kaligonj": "Kaliganj"},
         "Munshiganj": {"Munshiganj": "Munshiganj Sadar", "Tongibari": "Tongibari", "Gazaria": "Gazaria", "Louhajong": "Lohajang",
                        "Srinagar": "Sreenagar", "Sirajdikhan": "Sirajdikhan"},
         "Manikganj": {"Manikgonj": "Manikganj Sadar", "Saturia": "Saturia", "Singair": "Singair", "Horirampur": "Harirampur",
                       "Shibaloy": "Shibalaya", "Ghior": "Ghior", "Dowlatpur": "Daulatpur"},
         "Kishoreganj": {"Sadar": "Kishoreganj Sadar", "Korimgonj": "Karimganj", "Tarail": "Tarail", "Hosenpur": "Hossainpur",
                         "Pakundia": "Pakundia", "Kotiadi": "Katiadi", "Bajitpur": "Bajitpur", "Kuliarchor": "Kuliarchar",
                         "Bhoirob": "Bhairab", "Itna": "Itna", "Mithamoin": "Mithamain", "Nikoli": "Nikli", "Ostogram": "Austagram"},
         "Tangail": {"Tangail Sadar": "Tangail Sadar", "Delduar": "Delduar", "Nagorpur": "Nagarpur", "Mirzapur": "Mirzapur",
                     "Basail": "Basail", "Sokhipur": "Sakhipur", "Kalihati": "Kalihati", "Ghatail": "Ghatail", "Modhupur": "Madhupur",
                     "Donbari": "Dhanbari", "Gopalpur": "Gopalpur", "Bhuiyapur": "Bhuapur"},
         "Faridpur": {"kotwali": "Faridpur Sadar", "Modhukhali": "Madhukhali", "Boallmari": "Boalmari", "Alphadanga": "Alfadanga",
                      "Carvodrasan": "Char Bhadrasan", "Nogorkanda": "Nagarkanda", "Sadarpur": "Sadarpur", "Saltha": "Saltha",
                      "Vanga": "Bhanga"},
         "Madaripur": {"Sadar": "Madaripur Sadar", "Rajoir": "Rajoir", "Kalkini": "Kalkini", "Shibchor": "Shibchar", "Dasar": "Dasar"},
         "Gopalganj": {"Gopalganj": "Gopalganj Sadar", "Muksudpur": "Muksudpur", "Kashiani": "Kashiani", "Kotalipara": "Kotalipara",
                       "Tungipara": "Tungipara"},
         "Shariatpur": {"Palong": "Shariatpur Sadar", "Noria": "Naria", "Jajira": "Zanjira", "Vedorgonj": "Bhedarganj",
                        "Damudda": "Damudya", "Gosairhat": "Gosairhat"},
         "Rajbari": {"Rajbari Sadar": "Rajbari Sadar", "Baliakanda": "Baliakandi", "Pangsha": "Pangsha", "Goalnond": "Goalanda",
                     "Kalukhali": "Kalukhali"}},
    raw="police_contacts_2020_dmp_gmp_dhaka_range.csv")
# Chattogram Division: sheets 'CMP' (Chattogram Metropolitan Police) and 'Chattogram Range' (one block per district; the DIG range
# office and 'RRF Chattogram' are not collected). Thanas not named after an upazila (Jorargonj, Bhujpur, Chandraghona, Sajek,
# Chandraganj, Bangra Bazar) keep upazila_en empty. Metro rows: upazila_en holds the CMP thana.
CHATTOGRAM = dict(
    sheets=["CMP", "Chattogram Range"], range_sheet="Chattogram Range", head="Chattogram",
    metros={"CMP": ("Chattogram", "Chattogram Metropolitan Police", "CMP", "cmp")},
    dist={"Chattogram": "Chattogram", "Cox's Bazar": "Cox's Bazar", "Rangamati": "Rangamati", "Khagrachari": "Khagrachhari",
          "Bandarban": "Bandarban", "Noakhali": "Noakhali", "Laxmipur": "Lakshmipur", "Feni": "Feni", "Comilla": "Cumilla",
          "Brahmanbaria": "Brahmanbaria", "Chandpur": "Chandpur"},
    upa={"CMP": {"Chandgaon": "Chandgaon", "Panchlaish": "Panchlaish", "Khulshi": "Khulshi", "Biazid Bostami": "Bayezid Bostami",
                 "Kotowali": "Kotwali", "Bakolia": "Bakalia", "Chawkbazar": "Chawkbazar", "Sadarghat": "Sadarghat",
                 "Doublemoring": "Double Mooring", "Halishohor": "Halishahar", "Pahartoli": "Pahartali", "Akbor Shah": "Akbarshah",
                 "Port": "Bandar", "EPZ": "EPZ", "Potenga": "Patenga", "Kornophuli": "Karnaphuli"},
         "Chattogram": {"Sitakondo": "Sitakunda", "Sondip": "Sandwip", "Mirsarai": "Mirsharai", "Hathazari": "Hathazari",
                        "Fotikchori": "Fatikchhari", "Rangunia": "Rangunia", "Raojan": "Raozan", "Patiya": "Patiya",
                        "Boalkhali": "Boalkhali", "Satkaniya": "Satkania", "Lohagarh": "Lohagara", "Anawara": "Anwara",
                        "Banshkhali": "Banshkhali", "Chandnaish": "Chandanaish"},
         "Cox's Bazar": {"Sadar": "Cox's Bazar Sadar", "Ramu": "Ramu", "Ukhia": "Ukhia", "Teknaf": "Teknaf", "Chakaria": "Chakaria",
                         "Pekua": "Pekua", "Maheshkhali": "Maheshkhali", "Kutubdia": "Kutubdia"},
         "Rangamati": {"Kotwali": "Rangamati Sadar", "Naniarchar": "Naniarchar", "Kawkhali": "Kawkhali", "Kaptai": "Kaptai",
                       "Langadu": "Langadu", "Bagichhari": "Baghaichhari", "Rajasthali": "Rajasthali", "Jurachari": "Juraichhari",
                       "Bilaichhari": "Belaichhari", "Barkal": "Barkal"},
         "Khagrachhari": {"Khagrachari": "Khagrachhari Sadar", "Dighinala": "Dighinala", "Mohalchari": "Mahalchhari",
                          "Panchhari": "Panchhari", "Ramgarh": "Ramgarh", "Matiranga": "Matiranga", "Manikchari": "Manikchhari",
                          "Lakshmichhari": "Lakshmichhari", "Guimara": "Guimara"},
         "Bandarban": {"Sadar": "Bandarban Sadar", "Rowangchhari": "Rowangchhari", "Ruma": "Ruma", "Thanchi": "Thanchi",
                       "Lama": "Lama", "Ali kadam": "Alikadam", "Naikhongchhari": "Naikhongchhari"},
         "Noakhali": {"Sodaram": "Noakhali Sadar", "Begumganj": "Begumganj", "Senbagh": "Senbagh", "Sonaimuri": "Sonaimuri",
                      "Companiganj": "Companiganj", "Chatkhil": "Chatkhil", "Hatiya": "Hatiya", "Charjobbr": "Subarnachar",
                      "Kabirhat": "Kabirhat"},
         "Lakshmipur": {"Laxmipur": "Lakshmipur Sadar", "Raipur": "Raipur", "Ramganj": "Ramganj", "Ramgati": "Ramgati",
                        "Kamalnagar": "Kamalnagar"},
         "Feni": {"Feni": "Feni Sadar", "DaganBhuiyan": "Daganbhuiyan", "Sonagazi": "Sonagazi", "Chhagalnaiya": "Chhagalnaiya",
                  "Fulgazi": "Fulgazi", "Parshuram": "Parshuram"},
         "Cumilla": {"Kotwali": "Cumilla Adarsha Sadar", "Chauddagram": "Chauddagram", "Devidwar": "Debidwar", "Homna": "Homna",
                     "Laksham": "Laksam", "Daudkandi": "Daudkandi", "Burichang": "Burichang", "Chandina": "Chandina",
                     "Baruda": "Barura", "Nangalkot": "Nangalkot", "Muradnagar": "Muradnagar", "Brahmanpara": "Brahmanpara",
                     "Meghna": "Meghna", "Manoharganj": "Manoharganj", "Titas": "Titas", "Sadar South": "Cumilla Sadar Dakshin",
                     "Lalmai": "Lalmai"},
         "Brahmanbaria": {"Sadar": "Brahmanbaria Sadar", "Ashuganj": "Ashuganj", "Sarail": "Sarail", "Nasirnagar": "Nasirnagar",
                          "Nabinagar": "Nabinagar", "Bancharampur": "Bancharampur", "Kasba": "Kasba", "Akhaura": "Akhaura",
                          "Vijayanagar": "Bijoynagar"},
         "Chandpur": {"Sadar": "Chandpur Sadar", "Hajiganj": "Hajiganj", "North Motlob": "Matlab Uttar",
                      "Motlob South": "Matlab Dakshin", "Shahrashti": "Shahrasti", "Kachua": "Kachua", "Faridganj": "Faridganj",
                      "Haimchar": "Haimchar"}},
    raw="police_contacts_2020_cmp_chattogram_range.csv")
# Khulna Division: sheets 'KMP' (Khulna Metropolitan Police) and 'Khulna Range' (one block per district; the DIG range office
# and 'RRF, Khulna' are not collected). The Khulna Range sheet has two 'New Number' columns: the second (01320-140100 ...
# 01320-150599) continues the national per-range series (Rangpur Range 0132013xxxx, Barishal Range 0132015xxxx) and is used;
# the first (e.g. SP Khulna 01320-149100, which is SP Meherpur's number in the second column) is kept in extra_json.
# Thanas not named after an upazila (Patkelghata, Benapol Port, Naragati, EB = Islamic University, Darsana) keep upazila_en
# empty. Metro rows: upazila_en holds the KMP thana.
KHULNA = dict(
    sheets=["KMP", "Khulna Range"], range_sheet="Khulna Range", head="Khulna",
    metros={"KMP": ("Khulna", "Khulna Metropolitan Police", "KMP", "kmp")},
    dist={"Khulna": "Khulna", "Bagerhat": "Bagerhat", "Satkhira": "Satkhira", "Jessore": "Jashore", "Jhenaidah": "Jhenaidah",
          "Magura": "Magura", "Narail": "Narail", "Kushtia": "Kushtia", "Chuadanga": "Chuadanga", "Meherpur": "Meherpur"},
    upa={"KMP": {"Khulna": "Khulna Sadar", "Shonadanga": "Sonadanga", "Lobonchora": "Labanchara", "Horintana": "Harintana",
                 "Khalishpur": "Khalishpur", "Dowlatpur": "Daulatpur", "Arangghata": "Aranghata", "Khanjahan Ali": "Khan Jahan Ali"},
         "Khulna": {"Rupsha": "Rupsa", "Terokhada": "Terokhada", "Digholia": "Dighalia", "Fultala": "Phultala", "Dumuria": "Dumuria",
                    "Paikgasa": "Paikgachha", "Dakop": "Dacope", "Botiaghata": "Batiaghata", "Koyra": "Koyra"},
         "Bagerhat": {"Bagerhat": "Bagerhat Sadar", "Fokirhat": "Fakirhat", "Mollahat": "Mollahat", "Chitolmari": "Chitalmari",
                      "Kochua": "Kachua", "Morelgong": "Morrelganj", "Shoronkhola": "Sarankhola", "Mongla": "Mongla",
                      "Rampal": "Rampal"},
         "Satkhira": {"Sathkhira": "Satkhira Sadar", "Kolarowa": "Kalaroa", "Tala": "Tala", "Kaligonj": "Kaliganj",
                      "Shamnogor": "Shyamnagar", "Debhata": "Debhata", "Ashasuni": "Assasuni"},
         "Jashore": {"Kotwali": "Jashore Sadar", "Jhikorgasa": "Jhikargachha", "Monirampur": "Manirampur", "Bagharpara": "Bagherpara",
                     "Chowgacha": "Chaugachha", "Sharsha": "Sharsha", "Keshobpur": "Keshabpur", "Ovoynogor": "Abhaynagar"},
         "Jhenaidah": {"Jhenaidah Sadar": "Jhenaidah Sadar", "Shoilkupa": "Shailkupa", "Harinakundu": "Harinakunda",
                       "Kaligonj": "Kaliganj", "Kotchadpur": "Kotchandpur", "Mohespur": "Maheshpur"},
         "Magura": {"Magura": "Magura Sadar", "Shiripur": "Sreepur", "Mohammodpur": "Mohammadpur", "Shalikha": "Shalikha"},
         "Narail": {"Norail Sadar": "Narail Sadar", "Kaliya": "Kalia", "Lohagora": "Lohagara"},
         "Kushtia": {"Kushtia": "Kushtia Sadar", "Khoksha": "Khoksa", "Kumarkhali": "Kumarkhali", "Veramara": "Bheramara",
                     "Mirpur": "Mirpur", "Daulatpur": "Daulatpur"},
         "Chuadanga": {"Chuadanga": "Chuadanga Sadar", "AlamDanga": "Alamdanga", "Jibannagar": "Jibannagar", "Damurhuda": "Damurhuda"},
         "Meherpur": {"Meherpur": "Meherpur Sadar", "Gagni": "Gangni", "Mujibnagor": "Mujibnagar"}},
    raw="police_contacts_2020_kmp_khulna_range.csv")
# Barishal Division: sheets 'BMP' (Barishal Metropolitan Police) and 'Barisal Range' (one block per district; the DIG range
# office and 'RRF Barisal' are not collected). Posts are written 'Oc …' as well as 'OC …'. Thanas not named after an upazila
# (Kajirhat, Shashibhushan, South Aicha, Dularhat, Mohipur) keep upazila_en empty. Metro rows: upazila_en holds the BMP thana.
BARISHAL = dict(
    sheets=["BMP", "Barisal Range"], range_sheet="Barisal Range", head="Barishal",
    metros={"BMP": ("Barishal", "Barishal Metropolitan Police", "BMP", "bmp")},
    dist={"Barisal": "Barishal", "Jhalkhathi": "Jhalokathi", "Bhola": "Bhola", "Patuakhali": "Patuakhali", "Pirojpur": "Pirojpur",
          "Barguna": "Barguna"},
    upa={"BMP": {"Port": "Bandar", "Kaonia": "Kawnia", "Kowtoali": "Kotwali", "Airport": "Airport", "University": "University",
                 "Kashipur": "Kashipur", "Chormonai": "Charmonai", "Rupatoli": "Rupatoli"},
         "Barishal": {"Bakergang": "Bakerganj", "Babugang": "Babuganj", "Ujirpor": "Wazirpur", "Banaripara": "Banaripara",
                      "Ghornadi": "Gaurnadi", "Aguiljhara": "Agailjhara", "Moladi": "Muladi", "Hijla": "Hizla",
                      "Mahendigang": "Mehendiganj"},
         "Jhalokathi": {"Jhalkhathi": "Jhalokathi Sadar", "Nalciti": "Nalchity", "Rajpur": "Rajapur", "Kathaliya": "Kanthalia"},
         "Bhola": {"Bhula": "Bhola Sadar", "Dolotkhan": "Daulatkhan", "Tojomoddin": "Tazumuddin", "Borhanuddin": "Burhanuddin",
                   "Lal Mohon": "Lalmohan", "ChorFashion": "Char Fasson", "Monpura": "Manpura"},
         "Patuakhali": {"Patuakhali": "Patuakhali Sadar", "Baufol": "Bauphal", "Galachipa": "Galachipa", "Dhosmina": "Dashmina",
                        "Dumki": "Dumki", "Kalapara": "Kalapara", "Mirajagang": "Mirzaganj", "Rangabali": "Rangabali"},
         "Pirojpur": {"Pirojpur": "Pirojpur Sadar", "Nagirpur": "Nazirpur", "Indurkani": "Indurkani", "Mothbariya": "Mathbaria",
                      "Vandariya": "Bhandaria", "Nesarabad": "Nesarabad", "Kawokhali": "Kawkhali"},
         "Barguna": {"Barguna": "Barguna Sadar", "Amtoli": "Amtali", "Pathorghata": "Patharghata", "Betagi": "Betagi",
                     "Bamona": "Bamna", "Taltoli": "Taltali"}},
    # BMP thanas listed with only a 2020 'New Number' (no landline, no pre-2020 number, no e-mail), unlike the four others
    thana_notes={k: "Listed in the BMP sheet with only a 'New Number' (no landline, pre-2020 number or e-mail); may have been a "
                    "planned thana in 2020 - check that it exists. " for k in ("University", "Kashipur", "Chormonai", "Rupatoli")},
    raw="police_contacts_2020_bmp_barisal_range.csv")
# Sylhet Division: sheets 'SMP' (Sylhet Metropolitan Police) and 'Sylhet Range' (one block per district, headed 'District Police
# Sylhet' / 'Districr Police Hobigonj' …; the DIG range office and 'RRF Sylhet' are not collected). OC posts are written 'OC …',
# 'OC, …', 'OC. …', 'Oc, …' and 'OC.Sadar Thana'; 'OC. DB' and 'OC Watch' (Moulvibazar) are not thanas. Metro rows: upazila_en
# holds the SMP thana.
SYLHET = dict(
    sheets=["SMP", "Sylhet Range"], range_sheet="Sylhet Range", head="Sylhet",
    metros={"SMP": ("Sylhet", "Sylhet Metropolitan Police", "SMP", "smp")},
    dist={"Sylhet": "Sylhet", "Hobigonj": "Habiganj", "Moulvibazar": "Moulvibazar", "Sunamganj": "Sunamganj"},
    upa={"SMP": {"Kotoali": "Kotwali", "Jalalabad": "Jalalabad", "Airport": "Airport", "South Surma": "South Surma",
                 "Moglabazar": "Moglabazar", "Shahporan": "Shah Poran"},
         "Sylhet": {"Usmaninagar": "Osmani Nagar", "Balaganj": "Balaganj", "Biswanath": "Bishwanath", "Fenchuganj": "Fenchuganj",
                    "Golapganj": "Golapganj", "Beanibazar": "Beanibazar", "kanaighat": "Kanaighat", "Goainghat": "Gowainghat",
                    "Companyganj": "Companiganj", "Zakiganj": "Zakiganj", "jaintapur": "Jaintiapur"},
         "Habiganj": {"Sadar": "Habiganj Sadar", "Madhobpur": "Madhabpur", "Chunarughat": "Chunarughat", "Bahubal": "Bahubal",
                      "Lakhi": "Lakhai", "Nabigonj": "Nabiganj", "Baniachong": "Baniachong", "Ajmerigonj": "Ajmiriganj",
                      "Saestagonj": "Shayestaganj"},
         "Moulvibazar": {"Moulvibazar": "Moulvibazar Sadar", "Sreemangal": "Sreemangal", "Kamolgonj": "Kamalganj",
                         "Rajnagar": "Rajnagar", "kulaura": "Kulaura", "Barlekha": "Barlekha", "Juri": "Juri"},
         "Sunamganj": {"Sadar": "Sunamganj Sadar", "Chattak": "Chhatak", "Jagannathpur": "Jagannathpur", "Tahirpur": "Tahirpur",
                       "Vishwambharpur": "Bishwambarpur", "Doarabazar": "Dowarabazar", "Dheri": "Derai", "Salla": "Shalla",
                       "Jamalganj": "Jamalganj", "Dharmapasha": "Dharmapasha", "Maddhanagar": "Madhyanagar",
                       "South Sunamjanj": "South Sunamganj"}},
    raw="police_contacts_2020_smp_sylhet_range.csv")
# Mymensingh Division: one sheet, 'Mymenshing Range' (sic; blocks 'Range Office, Mymenshing' - not collected - and 'SP Office,
# Mymenshing / Netrokona / Jamalpur / Sherpur'). The workbook has no metropolitan sheet for Mymensingh (sheets: DMP, CMP, KMP,
# RMP, BMP, SMP, GMP, RRMP and the eight ranges). Layout as in the Rajshahi Range sheet ('Inspector | OC Kotoali PS').
# Pagla PS (Gafargaon upazila) is a thana, not an upazila. Sherpur's 'Duty Officer | (Wireless)' row is not a thana duty officer.
MYMENSINGH = dict(
    sheets=["Mymenshing Range"], range_sheet="Mymenshing Range", head="Mymensingh", metros={},
    dist={"Mymenshing": "Mymensingh", "Netrokona": "Netrokona", "Jamalpur": "Jamalpur", "Sherpur": "Sherpur"},
    upa={"Mymensingh": {"Kotoali": "Mymensingh Sadar", "Muktagacha": "Muktagacha", "Fulbaria": "Fulbaria", "Trishal": "Trishal",
                        "Valuka": "Bhaluka", "Goforgong": "Gafargaon", "Gauripur": "Gouripur", "Ishwarganj": "Iswarganj",
                        "Nandail": "Nandail", "Fulpur": "Phulpur", "Tarakanda": "Tarakanda", "Haluaghat": "Haluaghat",
                        "Dhobaura": "Dhobaura"},
         "Netrokona": {"Netrokona": "Netrokona Sadar", "Barhatta": "Barhatta", "Kalmakanda": "Kalmakanda", "Atpara": "Atpara",
                       "Durgapur": "Durgapur", "Purbadhala": "Purbadhala", "Kendua": "Kendua", "Madan": "Madan",
                       "Mohongong": "Mohongonj", "Khaliajuri": "Khaliajuri"},
         "Jamalpur": {"Jamalpur": "Jamalpur Sadar", "Sarishabari": "Sarishabari", "Melandha": "Melandah", "Matherganj": "Madarganj",
                      "Islampur": "Islampur", "Dawanganj": "Dewangonj", "Bakshiganj": "Bokshiganj"},
         "Sherpur": {"Sherpur": "Sherpur Sadar", "Nokla": "Nokla", "Nalitabari": "Nalitabari", "Sreebordi": "Sreebordi",
                     "Jhenaigati": "Jhenaigati"}},
    # an e-mail cell that looks like a person's own mailbox (not a thana mailbox) is not used
    personal_emails={"babul11net@gmail.com"},
    thana_notes={"Kotoali": "Kotwali (Kotoali) PS is the Mymensingh town thana; upazila_en = Mymensingh Sadar. ",
                 "Pagla": "Pagla PS lies in Gafargaon upazila (a thana, not an upazila). ",
                 "Madan": "The e-mail cell (a personal-looking gmail address) is not used and is blanked in raw/. "},
    raw="police_contacts_2020_mymensingh_range.csv")
OC_RE = re.compile(r"^OC[\s,.]+", re.I)   # Sylhet: 'OC, Usmaninagar Thana', 'OC.Sadar Thana', 'Oc, Jagannathpur Thana'
EMAIL_OK = re.compile(r"^[\w.+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$")
DIVISION = "rajshahi"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def read_sheet(data, name):
    z = zipfile.ZipFile(io.BytesIO(data))
    ss = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
            ss.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    wb = z.read("xl/workbook.xml").decode()
    rid = dict(re.findall(r'<sheet [^>]*name="([^"]+)"[^>]*r:id="([^"]+)"', wb))[name]
    rels = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', z.read("xl/_rels/workbook.xml.rels").decode()))
    target = "xl/" + rels[rid].lstrip("/").replace("xl/", "")
    rows = []
    for r in ET.fromstring(z.read(target)).iter("{%s}row" % NS["m"]):
        row = {}
        for c in r.findall("m:c", NS):
            t, v = c.get("t"), c.find("m:v", NS)
            if t == "s" and v is not None:
                txt = ss[int(v.text)]
            elif t == "inlineStr":
                txt = "".join(x.text or "" for x in c.iter("{%s}t" % NS["m"]))
            else:
                txt = v.text if v is not None else None
            col = re.match(r"[A-Z]+", c.get("r")).group(0)
            n = 0
            for ch in col:
                n = n * 26 + ord(ch) - 64
            row[n - 1] = (txt or "").strip()
        if row:
            rows.append([row.get(i, "") for i in range(max(row) + 1)])
    return rows


def thana_key(post):
    if DIVISION != "rajshahi":  # this sheet also writes 'thana' in lower case and 'RoumariThana' without a space
        s = re.sub(r"^OC\s+", "", post.strip(), flags=re.I if DIVISION == "barishal" else 0)  # Barishal also writes 'Oc'
        if DIVISION == "sylhet":
            s = OC_RE.sub("", post.strip())
        s = re.sub(r"\s*(Thana|PS)$", "", s, flags=re.I).strip()
        return re.sub(r"\s+", " ", re.sub(r"\s+Model$", "", s, flags=re.I).strip())
    s = re.sub(r"^OC\s+", "", post.strip())
    s = re.sub(r"\s+(Thana|PS)$", "", s).strip()
    s = re.sub(r"\s+Model$", "", s, flags=re.I).strip()
    return re.sub(r"\s+", " ", s)


def main():
    global HERE, RAW, KEY, SHEETS, DIST, UPA, DIVISION
    args, out, KEY = division_setup(HERE, KEY, ["rajshahi", "rangpur", "dhaka", "chattogram", "khulna", "barishal",
                                                        "sylhet", "mymensingh"])
    HERE, RAW, DIVISION = Path(out), Path(out) / "raw", args.division
    metro_sheet, range_sheet, metro, metro_short, head = "RMP", "Rajshahi Range", "Rajshahi Metropolitan Police", "rmp", "Rajshahi"
    raw_name = "police_contacts_2020_rmp_rajshahi_range.csv"
    if DIVISION == "rangpur":
        SHEETS, DIST, UPA, raw_name = RANGPUR["sheets"], RANGPUR["dist"], RANGPUR["upa"], RANGPUR["raw"]
        metro_sheet, range_sheet, metro, metro_short, head = "RRMP", "Rangpur Range", RANGPUR["metro"], "rpmp", RANGPUR["head"]
    # metro sheet -> (district, force, label used in names/notes, control-room id suffix)
    metros = {metro_sheet: (head, metro, metro_short.upper() if DIVISION == "rajshahi" else "RpMP", metro_short)}
    if DIVISION == "dhaka":  # two metropolitan forces (DMP, GMP)
        SHEETS, DIST, UPA, raw_name = DHAKA["sheets"], DHAKA["dist"], DHAKA["upa"], DHAKA["raw"]
        range_sheet, head, metros = DHAKA["range_sheet"], DHAKA["head"], DHAKA["metros"]
    if DIVISION == "chattogram":  # one metropolitan force (CMP); the sheet names it 'CMP Control Room' / 'CMP Hot-Line'
        SHEETS, DIST, UPA, raw_name = CHATTOGRAM["sheets"], CHATTOGRAM["dist"], CHATTOGRAM["upa"], CHATTOGRAM["raw"]
        range_sheet, head, metros = CHATTOGRAM["range_sheet"], CHATTOGRAM["head"], CHATTOGRAM["metros"]
    if DIVISION == "khulna":  # one metropolitan force (KMP); 'KMP Control Room' / 'KMP Hotline'
        SHEETS, DIST, UPA, raw_name = KHULNA["sheets"], KHULNA["dist"], KHULNA["upa"], KHULNA["raw"]
        range_sheet, head, metros = KHULNA["range_sheet"], KHULNA["head"], KHULNA["metros"]
    if DIVISION == "barishal":  # one metropolitan force (BMP); 'BMP Control Room' / 'BMP Hot-line'
        SHEETS, DIST, UPA, raw_name = BARISHAL["sheets"], BARISHAL["dist"], BARISHAL["upa"], BARISHAL["raw"]
        range_sheet, head, metros = BARISHAL["range_sheet"], BARISHAL["head"], BARISHAL["metros"]
    if DIVISION == "sylhet":  # one metropolitan force (SMP); 'SMP Control Room' / 'SMP Hot-line'
        SHEETS, DIST, UPA, raw_name = SYLHET["sheets"], SYLHET["dist"], SYLHET["upa"], SYLHET["raw"]
        range_sheet, head, metros = SYLHET["range_sheet"], SYLHET["head"], SYLHET["metros"]
    if DIVISION == "mymensingh":  # no metropolitan force in the 2020 workbook: the range sheet only
        SHEETS, DIST, UPA, raw_name = MYMENSINGH["sheets"], MYMENSINGH["dist"], MYMENSINGH["upa"], MYMENSINGH["raw"]
        range_sheet, head, metros = MYMENSINGH["range_sheet"], MYMENSINGH["head"], MYMENSINGH["metros"]
    last_key = None
    used_ids = set()
    places = []
    xurl = XLSX_FALLBACK
    r = get(URL_PAGE)
    if r is not None and r.ok:
        m = re.search(r'href="(https?://www\.police\.gov\.bd/storage/upload/announcement/[^"]+\.xlsx)"', r.text)
        if m:
            xurl = m.group(1)
    r = get(xurl)
    if r is None or not r.ok:
        print("could not download", xurl)
        return
    raw_rows = []
    for sheet in SHEETS:
        rows = read_sheet(r.content, sheet)
        office, dist = "", ""
        last_thana = None
        for i, row in enumerate(rows):
            if DIVISION == "khulna" and sheet == range_sheet:  # raw: the first 'New Number' column moved to the end
                rr = row + [""] * (8 - len(row))
                raw_rows.append([sheet] + rr[:5] + rr[6:8] + [rr[5]])
            else:
                raw_rows.append([sheet] + row)
            first = row[0] if row else ""
            if first.startswith("Unit/Office Name:") or (DIVISION == "sylhet" and re.match(r"Unit/Office Name\s*:", first)):
                office = first.split(":", 1)[1].strip().rstrip(".")
                if DIVISION == "sylhet":  # 'Unit/Office Name : District Police Sylhet .'
                    office = office.strip()
                dist = metros[sheet][0] if sheet in metros else next((v for k, v in DIST.items() if k.lower() in office.lower()), "")
                if "Range Office" in office:
                    dist = ""
                if DIVISION != "rajshahi" and sheet not in metros and \
                        not re.search(r"Distric[tr]|SP Office" if DIVISION == "sylhet" else r"District|SP Office", office):
                    dist = ""  # range office ('DIG Rangpur Range') and RRF blocks are not collected
                last_thana = None
                continue
            if first and not first[0].isdigit() and "Unit/Office" not in first and not first.startswith("SL"):
                if sheet == range_sheet and first.strip() and len([c for c in row if c]) == 1:
                    office, dist, last_thana = first.strip(), "", None   # e.g. 'RRF Rajshahi' — not collected
                    continue
                if DIVISION == "dhaka" and sheet in metros and len([c for c in row if c]) == 1:
                    last_thana = None   # DMP section heading ('Crime Division', 'Traffic Division' ...)
                    continue
            alt_new = ""
            if DIVISION == "khulna" and sheet == range_sheet:  # two 'New Number' columns: the second is used (see KHULNA)
                row = row + [""] * (8 - len(row))
                alt_new, row = re.sub(r"\s+", " ", row[5]).strip(), row[:5] + row[6:8]
            row = row + [""] * (7 - len(row))
            sl, desig, post, official, current, new, email = [re.sub(r"\s+", " ", x).strip() for x in row[:7]]
            if DIVISION == "rajshahi":
                email = email.replace(" ", "")
            else:  # several addresses separated by spaces; 'x @ police.gov.bd.' written with spaces and a full stop
                email = re.sub(r"\s*@\s*", "@", email)
                if DIVISION in ("chattogram", "khulna"):  # 'OCcom.mur@police.gov. bd': a space inside the domain
                    email = re.sub(r"\.\s+(bd|com)\b", r".\1", email)
                elif DIVISION in ("barishal", "sylhet", "mymensingh"):  # 'ocpir.kow@police. gov.bd'
                    email = re.sub(r"\.\s+(gov|bd|com)\b", r".\1", email)
                email = "; ".join(e.strip(".") for e in email.split() if "@" in e)
                if DIVISION == "mymensingh":  # 'oc.mohangonj@gmail.com-': a trailing hyphen; personal-looking mailboxes dropped
                    email = "; ".join(e.rstrip("-") for e in email.split("; ") if e and e.rstrip("-") not in MYMENSINGH["personal_emails"])
            bad_email = ""
            if DIVISION == "khulna" and email:  # 'spsatkhira@.police.gov.bd', 'spnarail@police.gov.com': not usable as printed
                es = email.split("; ")
                bad = [e for e in es if not EMAIL_OK.match(e) or e.endswith("police.gov.com")]
                if bad:
                    bad_email, email = re.sub(r"\s+", " ", row[6]).strip(), "; ".join(e for e in es if e not in bad)
            if DIVISION in ("barishal", "sylhet", "mymensingh"):  # same check, plus a cut-off domain ('ocbar.ago@police.gov.b'); a cell without
                # any '@' ('ocborhanuddinps.gmail.com') is kept as printed too
                es = [e for e in email.split("; ") if e]
                bad = [e for e in es if not EMAIL_OK.match(e) or e.endswith("police.gov.com") or not re.search(r"\.[A-Za-z]{2,}$", e)]
                if bad or (not es and re.sub(r"\s+", " ", row[6]).strip() and
                           not (DIVISION == "mymensingh" and row[6].strip() in MYMENSINGH["personal_emails"])):
                    bad_email, email = re.sub(r"\s+", " ", row[6]).strip(), "; ".join(e for e in es if e not in bad)
            if not dist:
                continue
            upa_map = UPA[sheet if sheet in metros else dist]
            is_thana = bool(OC_RE.match(post) if DIVISION == "sylhet" else re.match(r"^OC\s", post, re.I if DIVISION == "barishal" else 0))
            no_oc = DIVISION == "chattogram" and sheet not in metros and post == "Sadar Model Thana"  # Brahmanbaria, Chandpur: no 'OC'
            is_thana = is_thana or no_oc
            if is_thana and DIVISION == "chattogram" and re.match(r"^OC\s+invest", post, re.I):
                continue  # 'OC invest. Satkaniya Thana': the investigation OC, not a separate thana
            if is_thana and DIVISION in ("dhaka", "khulna", "sylhet") and not re.search(r"(Thana|PS)\s*$", post, re.I) and thana_key(post) not in upa_map:
                is_thana, last_thana = False, None   # e.g. DMP 'OC Ration Store, Mirpur', 'OC Telephone'
                continue
            if is_thana:
                key = thana_key(post)
                upa = upa_map.get(key, "")
                unit = "metropolitan_thana" if sheet in metros else "district_police_thana"
                sid = f"bdpol2020-{sheet.replace(' ', '')}-{sl}"
                if DIVISION != "rajshahi" and sheet not in metros:  # serials restart in every district block
                    sid = f"bdpol2020-{sheet.replace(' ', '')}-{dist.lower()}-{sl}"
                elif DIVISION == "dhaka":  # DMP serials restart in every division section: id by thana
                    sid = f"bdpol2020-{sheet}-{re.sub(r'[^a-z]+', '-', key.lower()).strip('-')}"
                last_key = key
                dup_note = ""
                if DIVISION != "rajshahi" and sid in used_ids:  # the sheet repeats a serial number (e.g. Lalmonirhat 'OC Kaligonj' copies Aditmari's SL 27)
                    sid = f"{sid}-{re.sub(r'[^a-z]', '', key.lower())}"
                    dup_note = "Serial number repeated in the source (row copied from the previous thana; official number/e-mail may belong to it). "
                used_ids.add(sid)
                last_thana = dict(
                    source_key=KEY, source_id=sid, name_bn="",
                    name_en=post if no_oc else OC_RE.sub("", post).strip() if DIVISION == "sylhet" else post[3:].strip(),
                    category_key="emergency.police_station", district_en=dist, upazila_en=upa, phone=new, email=email,
                    operator=metros[sheet][1] if sheet in metros else f"{dist} District Police", ownership="public",
                    _extra={"unit": unit, "office_in_source": office, "oc_new_number": new, "oc_current_number_2020": current,
                            "official_landline_raw": official, "oc_new_number_first_column": alt_new, "email_as_printed": bad_email},
                    source_url=xurl,
                    notes="Numbers as of the Police HQ list uploaded 03-10-2020 ('New Number' = official 01320-series SIM). "
                          + dup_note
                          + (f"upazila_en holds the {metros[sheet][2]} metropolitan thana. " if sheet in metros else "")
                          + ("" if upa else "Thana is not an upazila (or name not mapped); upazila_en left empty. ")
                          + (BARISHAL["thana_notes"].get(key, "") if DIVISION == "barishal" and sheet in metros else "")
                          + (MYMENSINGH["thana_notes"].get(key, "") if DIVISION == "mymensingh" else "")
                          + ("Post printed without 'OC' ('Sadar Model Thana'); the row's numbers are the thana OC's. " if no_oc else ""))
                places.append(last_thana)
            elif last_thana and re.search(r"duty officer", desig + " " + post, re.I) and \
                    (DIVISION not in ("dhaka", "chattogram", "sylhet") or not desig or thana_key(desig) == last_key) and \
                    (DIVISION != "mymensingh" or post == "Duty Officer"):   # DMP/CMP: 'Ramna PS | Duty officer'
                last_thana["_extra"]["duty_officer_new_number"] = new
                if current:
                    last_thana["_extra"]["duty_officer_current_number_2020"] = current
            elif (desig == "SP" or (DIVISION == "dhaka" and desig == "Police Super") or (DIVISION == "chattogram" and desig == "Sp") or
                  (DIVISION == "khulna" and desig == "Police Super")) and post in ("1", "01", "") and sl == "1" and ("SP Office" in office or (DIVISION != "rajshahi" and "District" in office)
                                                                                   or (DIVISION == "sylhet" and "Districr" in office)):
                places.append(dict(
                    source_key=KEY, source_id=f"bdpol2020-sp-{dist.lower()}", name_bn="",
                    name_en=office if "SP Office" in office else f"SP Office, {dist}",
                    category_key="government.sp_office", district_en=dist, phone=new, email=email,
                    operator=f"{dist} District Police", ownership="public",
                    _extra={"sp_new_number": new, "sp_current_number_2020": current, "official_landline_raw": official,
                            "sp_new_number_first_column": alt_new, "email_as_printed": bad_email},
                    source_url=xurl, notes="Phone = Superintendent of Police official number (role SIM) from the 2020 HQ list"
                                           + ("" if "SP Office" in office else f"; name composed from the sheet heading '{office}'")))
            elif (re.match(r"^(RMP )?Control Room$", desig, re.I) or desig == "Hotline") if DIVISION not in ("dhaka", "chattogram", "khulna", "barishal", "sylhet") else \
                    ((re.match(r"^((DMP|GMP) )?Control Room$", desig) and not post) or re.match(r"^(DMP )?Hot-?line$", desig)) if DIVISION == "dhaka" else \
                    ((re.match(r"^(KMP )?Control Room$", desig, re.I) and not post) or re.match(r"^(KMP )?Hot[- ]?line$", desig, re.I)) if DIVISION == "khulna" else \
                    ((re.match(r"^(BMP )?Control Room$", desig, re.I) and not post) or re.match(r"^(BMP )?Hot[- ]?line$", desig, re.I)) if DIVISION == "barishal" else \
                    ((re.match(r"^(SMP )?Control Room$", desig, re.I) and not post) or re.match(r"^(SMP )?Hot[- ]?line$", desig, re.I)) if DIVISION == "sylhet" else \
                    ((re.match(r"^(CMP )?Control Room$", desig, re.I) and not post) or re.match(r"^(CMP )?Hot[- ]?line$", desig, re.I)):
                cid = f"bdpol2020-control-{dist.lower() if sheet not in metros else metros[sheet][3]}"
                ex = next((p for p in places if p["source_id"] == cid), None)
                if ex is None:
                    ex = dict(source_key=KEY, source_id=cid, name_bn="",
                              name_en=(f"{metros[sheet][2]} Control Room" if sheet in metros else f"Control Room, {office}"),
                              category_key="emergency", district_en=dist, phone="", operator=(metros[sheet][1] if sheet in metros else f"{dist} District Police"),
                              ownership="public", _extra={}, source_url=xurl, notes="Police control room numbers from the 2020 HQ list")
                    places.append(ex)
                nums = [x for x in (new, current) if x]
                ex["phone"] = "; ".join([p for p in ex["phone"].split("; ") if p] + nums)
                if official:
                    ex["_extra"]["official_landline_raw"] = official
                if alt_new:
                    ex["_extra"].setdefault("new_number_first_column", []).append(alt_new)
                if desig == "Hotline" or (DIVISION == "dhaka" and re.match(r"^(DMP )?Hot-?line$", desig)) or \
                        (DIVISION in ("chattogram", "khulna", "barishal", "sylhet") and re.match(r"^(CMP |KMP |BMP |SMP )?Hot[- ]?line$", desig, re.I)):
                    ex["_extra"]["hotline"] = new
                if email:
                    ex["email"] = email.replace(" ", "")
    for p in places:
        p["extra_json"] = xj(p.pop("_extra"))
    RAW.mkdir(exist_ok=True)
    with open(RAW / raw_name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        ncol = 9 if DIVISION == "khulna" else 8
        w.writerow(["sheet", "sl", "designation", "post", "official_number", "current_number", "new_number", "email"]
                   + (["new_number_first_column"] if ncol == 9 else []))
        for row in raw_rows:
            if DIVISION == "mymensingh":  # the personal-looking mailbox is blanked in raw/ too (as in the DGHS extracts)
                row = ["" if c.strip() in MYMENSINGH["personal_emails"] else c for c in row]
            w.writerow((row + [""] * ncol)[:ncol])
    write_csv("places.csv", PLACE_COLS, places)
    sheet_label = (f"{SHEETS[0]} sheet" if len(SHEETS) == 1 else f"{' and '.join([', '.join(SHEETS[:-1]), SHEETS[-1]])} sheets")
    write_manifest(dict(
        key=KEY, division=DIVISION, kind="police_hq_2020",
        name=f"Bangladesh Police HQ — Contacts of Bangladesh Police ({sheet_label})",
        organization="Bangladesh Police Headquarters", source_type="government_portal", trust_level=4,
        urls=[URL_PAGE, xurl], accessed=__import__("datetime").date.today().isoformat(), publication_date="2020-10-03",
        license=None, license_url=None, attribution="Bangladesh Police (police.gov.bd)",
        notes=f"No licence stated. XLSX 'Contacts Of Bangladesh Police' uploaded 03-10-2020 (Last-Modified 2020-10-03). Only the "
              f"{sheet_label} {'is' if len(SHEETS) == 1 else 'are'} used (raw/ keeps those rows as CSV; the full 1.5 MB workbook is re-downloaded by fetch.py). "
              "Designations only, no personal names. Old 2020 numbers: the 01320-series 'New Number' values match the 2026 district/RMP "
              "portals where checked; the 'Current Number' column is the pre-2020 numbering."
              + ("" if DIVISION == "rajshahi" else " For this division the 2026 portals were not cross-checked by this collector.")),
        ["places.csv", "raw/" + raw_name])


if __name__ == "__main__":
    main()
