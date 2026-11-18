#!/usr/bin/env python3
"""Extract Rajshahi-Division bank statistics from Bangladesh Bank's quarterly Scheduled Banks Statistics (BB_SCHEDULED_BANKS_RAJ_2026).

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

# --- BB_SCHEDULED_BANKS_RAJ_2026 ----------------------------------------------------------------------
KEY = "BB_SCHEDULED_BANKS_RAJ_2026"
URL_LIST = "https://www.bb.org.bd/en/index.php/publication/publictn/2/14"   # Scheduled Banks Statistics (quarterly)
PDF_FALLBACK = "https://www.bb.org.bd//pub/quaterly/schbanksta/sbs23apriljune2026.pdf"
DISTS = {"Bogura": "Bogura", "Chapainawabganj": "Chapainawabganj", "Jaypurhat": "Joypurhat", "Naogaon": "Naogaon", "Natore": "Natore",
         "Pabna": "Pabna", "Rajshahi": "Rajshahi", "Sirajganj": "Sirajganj"}
# Table-33 thana spellings -> standard upazila (RMP thanas and non-upazila thanas map to '')
UPA = {"Adamdighi": "Adamdighi", "Dhunat": "Dhunat", "Dupchanchia": "Dhupchanchia", "Gabtali": "Gabtali", "Kahaloo": "Kahaloo",
       "Nandigram": "Nandigram", "Sariakandi": "Sariakandi", "Shahjahanpur": "Shajahanpur", "Sherpur": "Sherpur", "Sonatola": "Sonatala",
       "Bholahat": "Bholahat", "Chapainawabganj Sada": "Chapainawabganj Sadar", "Gomostapur": "Gomastapur", "Nachole": "Nachole",
       "Akkelpur": "Akkelpur", "Jaypurhat": "Joypurhat Sadar", "Kalai": "Kalai", "Khetlal": "Khetlal", "Panch Bibi": "Panchbibi",
       "Atrai": "Atrai", "Badalgachi": "Badalgachhi", "Dhamoirhat": "Dhamoirhat", "Manda": "Manda", "Mohadevpur": "Mahadebpur",
       "Naogaon Sadar": "Naogaon Sadar", "Niamotpur": "Niamatpur", "Patnitola": "Patnitala", "Porsha": "Porsha", "Rani Nagar": "Raninagar",
       "Sapahar": "Sapahar", "Bagatipara": "Bagatipara", "Baraigram": "Baraigram", "Gurudaspur": "Gurudaspur", "Lalpur": "Lalpur",
       "Nal Danga": "Naldanga", "Natore Sadar": "Natore Sadar", "Singra": "Singra", "Atghoria": "Atgharia", "Bera": "Bera",
       "Bhangura": "Bhangura", "Chatmohar": "Chatmohar", "Faridpur": "Faridpur", "Ishwardi": "Ishwardi", "Pabna Sadar": "Pabna Sadar",
       "Santhia": "Santhia", "Sujanagar": "Sujanagar", "Bagha": "Bagha", "Bagmara": "Bagmara", "Charghat": "Charghat",
       "Durgapur": "Durgapur", "Godagari": "Godagari", "Mohanpur": "Mohanpur", "Paba": "Paba", "Puthia": "Puthia", "Tanore": "Tanore",
       "Belkuchi": "Belkuchi", "Chowhali": "Chauhali", "Kamarkanda": "Kamarkhanda", "Kazipur": "Kazipur", "Raiganj": "Raiganj",
       "Shahjadpur": "Shahjadpur", "Sirajganj Sadar": "Sirajganj Sadar", "Tarash": "Tarash", "Ullapara": "Ullahpara",
       "Shibganj": "Shibganj"}
# Table-3.16 'Region-wise position of scheduled bank branches' is an image in the PDF: values for Rajshahi division transcribed
# from the rendered page (PDF page 35, printed page 27) for the quarter in PDF_FALLBACK.
T316 = {"quarter": "April-June 2026", "urban": 600, "rural": 542, "total": 1142}

# Rangpur Division. Table-33 thana names repeat across districts (Kotwali, Fulbari, Pirganj), so the map is per district;
# '' = metropolitan / non-upazila thana. Table-3.16 (Concld.) image: PDF page 36, printed page 28, 'Rangpur division' column.
RANGPUR = dict(
    dists={"Dinajpur": "Dinajpur", "Gaibandah": "Gaibandha", "Kurigram": "Kurigram", "Lalmonirhat": "Lalmonirhat",
           "Nilphamari": "Nilphamari", "Panchagarh": "Panchagarh", "Rangpur": "Rangpur", "Thakurgaon": "Thakurgaon"},
    upa={"Dinajpur": {"Birampur": "Birampur", "Birganj": "Birganj", "Birol": "Biral", "Bochaganj": "Bochaganj",
                      "Chirirbandar": "Chirirbandar", "Fulbari": "Phulbari", "Ghoraghat": "Ghoraghat", "Hakimpur": "Hakimpur",
                      "Kaharole": "Kaharole", "Khanshama": "Khansama", "Kotwali": "Dinajpur Sadar", "Nawabganj": "Nawabganj",
                      "Parbotipur": "Parbatipur"},
         "Gaibandha": {"Fulchhari": "Phulchhari", "Gaibandah Sadar": "Gaibandha Sadar", "Gobindaganj": "Gobindaganj",
                       "Palashbari": "Palashbari", "Sadullapur": "Sadullapur", "Saghatta": "Saghata", "Sundarganj": "Sundarganj"},
         "Kurigram": {"Bhurungamari": "Bhurungamari", "Chilmari": "Chilmari", "Fulbari": "Phulbari", "Kurigram Sadar": "Kurigram Sadar",
                      "Nageswari": "Nageshwari", "Rajarhat": "Rajarhat", "Rajibpur": "Char Rajibpur", "Rowmari": "Raomari",
                      "Ulipur": "Ulipur"},
         "Lalmonirhat": {"Aditmari": "Aditmari", "Hatibandha": "Hatibandha", "Kaliganj": "Kaliganj",
                         "Lalmonirhat Sadar": "Lalmonirhat Sadar", "Patgram": "Patgram"},
         "Nilphamari": {"Dimla": "Dimla", "Domar": "Domar", "Jaldhaka": "Jaldhaka", "Kishoreganj": "Kishoreganj",
                        "Nilphamari Sadar": "Nilphamari Sadar", "Sayedpur": "Saidpur"},
         "Panchagarh": {"Atwari": "Atwari", "Boda": "Boda", "Debiganj": "Debiganj", "Panchagarh Sadar": "Panchagarh Sadar",
                        "Tetulia": "Tetulia"},
         "Rangpur": {"Badarganj": "Badarganj", "Gangachara": "Gangachara", "Kaunia": "Kaunia", "Mithapukur": "Mithapukur",
                     "Pirgacha": "Pirgachha", "Pirganj": "Pirganj", "Taraganj": "Taraganj"},
         "Thakurgaon": {"Baliadangi": "Baliadangi", "Haripur": "Haripur", "Pirganj": "Pirganj", "Ranisankail": "Ranisankail",
                        "Thakurgaon Sadar": "Thakurgaon Sadar"}},
    t316={"quarter": "April-June 2026", "urban": 345, "rural": 428, "total": 773}, next_division="Sylhet Division")

# Dhaka Division. Table-1 for Dhaka sits in the first part of the table (not 'Concl'd'); Table-33 thana names here also use
# '.', '-', '/', '(' and ')' ('Dhaka Int. Airport', 'Sher-E-Bangla Nagar', 'Tejgaon I/A', 'Bandar(M)', 'Palong/Sadar').
# '' = metropolitan (DMP/GMP) or other non-upazila thana. Table-3.16 image: PDF page 35, printed page 27, 'Dhaka division'.
_DHAKA_CITY = ["Adabor", "Badda", "Banani", "Bangshal", "Bhashantek", "Cantonment", "Chawkbazar", "Darus Salam", "Daskhinkhan",
               "Demra", "Dhaka Int. Airport", "Dhanmondi", "Gendaria", "Gulshan", "Hatirjheel", "Hazaribagh", "Jatrabari", "Kadamtoli",
               "Kafrul", "Kalabagan", "Kamrangirchar", "Khilgaon", "Khilkhet", "Kotwali_Dhaka", "Lalbagh", "Mirpur", "Mohammadpur",
               "Motijheel", "Mugdha", "New Market", "Pallabi", "Paltan", "Ramna", "Rampura", "Rupnagar", "Sabujbagh", "Shah Ali",
               "Shahbag", "Shahjahanpur", "Shyampur", "Sutrapur", "Tejgaon", "Turag", "Uttara East", "Uttara West", "Uttarkhan",
               "Vatara", "Wari", "Sher-E-Bangla Nagar", "Tejgaon I/A"]
DHAKA = dict(
    dists={"Dhaka": "Dhaka", "Faridpur": "Faridpur", "Gazipur": "Gazipur", "Gopalganj": "Gopalganj", "Kishoreganj": "Kishoreganj",
           "Madaripur": "Madaripur", "Manikganj": "Manikganj", "Munshiganj": "Munshiganj", "Narayanganj": "Narayanganj",
           "Narshingdi": "Narsingdi", "Rajbari": "Rajbari", "Shariatpur": "Shariatpur", "Tangail": "Tangail"},
    upa={"Dhaka": dict({n: "" for n in _DHAKA_CITY}, **{"Ashulia": "", "South Keraniganj": "", "Dhamrai": "Dhamrai", "Dohar": "Dohar",
                                                          "Keraniganj": "Keraniganj", "Nawabganj": "Nawabganj", "Savar": "Savar"}),
         "Faridpur": {"Alfadanga": "Alfadanga", "Bhanga": "Bhanga", "Boalmari": "Boalmari", "Charbhadrasan": "Char Bhadrasan",
                      "Kotwali_Faridpur": "Faridpur Sadar", "Madhukhali": "Madhukhali", "Nagarkanda": "Nagarkanda",
                      "Sadarpur": "Sadarpur", "Salda": "Saltha"},
         "Gazipur": {"Gazipur Sadar": "Gazipur Sadar", "Kaliakoir": "Kaliakair", "Kaliganj": "Kaliganj", "Kapasia": "Kapasia",
                     "Sreepur": "Sreepur"},
         "Gopalganj": {"Gopalganj Sadar": "Gopalganj Sadar", "Kasiani": "Kashiani", "Kotwalipara": "Kotalipara",
                       "Muksudpur": "Muksudpur", "Tungipara": "Tungipara"},
         "Kishoreganj": {"Astagram": "Austagram", "Bajitpur": "Bajitpur", "Bhairab": "Bhairab", "Hossainpur": "Hossainpur",
                         "Itna": "Itna", "Karimganj": "Karimganj", "Katiadi": "Katiadi", "Kishoreganj Sadar": "Kishoreganj Sadar",
                         "Kuliarchar": "Kuliarchar", "Mithamon": "Mithamain", "Nikli": "Nikli", "Pakundia": "Pakundia",
                         "Tarail": "Tarail"},
         "Madaripur": {"Dasar": "Dasar", "Kalkini": "Kalkini", "Madaripur Sadar": "Madaripur Sadar", "Rajoir": "Rajoir",
                       "Shibchar": "Shibchar"},
         "Manikganj": {"Daulatpur": "Daulatpur", "Ghior": "Ghior", "Harirampur": "Harirampur", "Manikganj Sadar": "Manikganj Sadar",
                       "Saturia": "Saturia", "Shivalaya": "Shibalaya", "Singair": "Singair"},
         "Munshiganj": {"Gazaria": "Gazaria", "Lohajong": "Lohajang", "Munshiganj Sadar": "Munshiganj Sadar",
                        "Serajdikhan": "Sirajdikhan", "Sreenagar": "Sreenagar", "Tongi Bari": "Tongibari"},
         "Narayanganj": {"Arihazar": "Araihazar", "Bandar(M)": "Bandar", "Narayanganj Sadar": "Narayanganj Sadar",
                         "Rupganj": "Rupganj", "Sonargaon": "Sonargaon"},
         "Narsingdi": {"Belabo": "Belabo", "Monohardi": "Monohardi", "Narshingdi Sadar": "Narsingdi Sadar", "Palash": "Palash",
                       "Raipura": "Raipura", "Shibpur": "Shibpur"},
         "Rajbari": {"Baliakandi": "Baliakandi", "Goalanda": "Goalanda", "Kalukhali": "Kalukhali", "Pangsha": "Pangsha",
                     "Rajbari Sadar": "Rajbari Sadar"},
         "Shariatpur": {"Bhederganj": "Bhedarganj", "Damodiya": "Damudya", "Gooshairhat": "Gosairhat", "Naria": "Naria",
                        "Palong/Sadar": "Shariatpur Sadar", "Zajira": "Zanjira"},
         "Tangail": {"Basail": "Basail", "Bhuapur": "Bhuapur", "Delduar": "Delduar", "Dhanbari": "Dhanbari", "Ghatail": "Ghatail",
                     "Gopalpur": "Gopalpur", "Kalihati": "Kalihati", "Madhupur": "Madhupur", "Mirzapur": "Mirzapur",
                     "Nagarpur": "Nagarpur", "Shakhipur": "Sakhipur", "Tangail Sadar": "Tangail Sadar"}},
    notes={"Joydebpur (Gazipur)/": "Thana as published ('Joydebpur (Gazipur)/'); not mapped to an upazila because the table also "
                                   "lists 'Gazipur Sadar' separately."},
    t316={"quarter": "April-June 2026", "urban": 2613, "rural": 1341, "total": 3954}, next_division="Khulna Division",
    table1_anchor="Table-1: Division and district-wise distribution of per capita deposits and advances on the basis")

# Chattogram Division. Table-1 sits in the first part of the table (like Dhaka); BB spells "Cox'S Bazar" and "Khagrachari".
# Table-33 thana names also use "'" and "." ('Cox'S Bazar Sadar', 'Bandar Ctg.'). '' = CMP thana or other non-upazila thana
# (Bhujpur, Jorarganj, Bangora, Chandraganj, Chandraghona; 'Char Jabber' is listed beside 'Subarnachar', so it is not mapped).
# Table-3.16 image: PDF page 35, printed page 27, 'Chattogram division' column.
_CMP = ["Akbor Shah", "Baiozid Bostami", "Bakolia", "Bandar Ctg.", "Chandgaon", "Chawkbazar", "Double Mooring", "Epz", "Halishar",
        "Kotwali_Chattogram", "Kulshi", "Pahartali", "Panchlaish", "Patenga", "Sadarghat"]
CHATTOGRAM = dict(
    dists={"Bandarban": "Bandarban", "Brahmanbaria": "Brahmanbaria", "Chandpur": "Chandpur", "Chattogram": "Chattogram",
           "Cox'S Bazar": "Cox's Bazar", "Cumilla": "Cumilla", "Feni": "Feni", "Khagrachari": "Khagrachhari",
           "Lakshmipur": "Lakshmipur", "Noakhali": "Noakhali", "Rangamati": "Rangamati"},
    upa={"Bandarban": {"Ali Kadam": "Alikadam", "Bandarban Sadar": "Bandarban Sadar", "Lama": "Lama",
                       "Naikhangchari": "Naikhongchhari", "Rowangchari": "Rowangchhari", "Ruma": "Ruma", "Thanchi": "Thanchi"},
         "Brahmanbaria": {"Akhaura": "Akhaura", "Ashuganj": "Ashuganj", "Bancharampur": "Bancharampur", "Bijoynagar": "Bijoynagar",
                          "Brahmanbaria Sadar": "Brahmanbaria Sadar", "Kasba": "Kasba", "Nabinagar": "Nabinagar",
                          "Nasir Nagar": "Nasirnagar", "Sarail": "Sarail"},
         "Chandpur": {"Chandpur Sadar": "Chandpur Sadar", "Faridganj": "Faridganj", "Haimchar": "Haimchar", "Hajiganj": "Hajiganj",
                      "Kachua": "Kachua", "Matlab South": "Matlab Dakshin", "Matlab Uttar": "Matlab Uttar", "Shahrasti": "Shahrasti"},
         "Chattogram": dict({n: "" for n in _CMP}, **{
             "Bhujpur": "", "Jorarganj": "", "Karnaphuli": "Karnaphuli", "Anwara": "Anwara", "Banshkhali": "Banshkhali",
             "Boalkhali": "Boalkhali", "Chandanaish": "Chandanaish", "Fatikchari": "Fatikchhari", "Hathazari": "Hathazari",
             "Lohagara": "Lohagara", "Mirsarai": "Mirsharai", "Patiya": "Patiya", "Rangunia": "Rangunia", "Raozan": "Raozan",
             "Sandwip": "Sandwip", "Satkania": "Satkania", "Sitakunda": "Sitakunda"}),
         "Cox's Bazar": {"Chakaria": "Chakaria", "Cox'S Bazar Sadar": "Cox's Bazar Sadar", "Eidgaon": "Eidgaon", "Kutubdia": "Kutubdia",
                         "Maheskhali": "Maheshkhali", "Pekua": "Pekua", "Ramu": "Ramu", "Teknaf": "Teknaf", "Ukhia": "Ukhia"},
         "Cumilla": {"Bangora": "", "Barura": "Barura", "Brahmanpara": "Brahmanpara", "Burichang": "Burichang", "Chandina": "Chandina",
                     "Chauddagram": "Chauddagram", "Cumilla Sadar South": "Cumilla Sadar Dakshin", "Daudkandi": "Daudkandi",
                     "Debidwar": "Debidwar", "Homna": "Homna", "Kotwali_Cumilla": "Cumilla Adarsha Sadar", "Laksham": "Laksam",
                     "Lalmai": "Lalmai", "Meghna": "Meghna", "Monohorganj": "Manoharganj", "Muradnagar": "Muradnagar",
                     "Nangolkot": "Nangalkot", "Titas": "Titas"},
         "Feni": {"Chhagalnaiya": "Chhagalnaiya", "Daganbhuiyan": "Daganbhuiyan", "Feni Sadar": "Feni Sadar", "Fulgazi": "Fulgazi",
                  "Parshuram": "Parshuram", "Sonagazi": "Sonagazi"},
         "Khagrachhari": {"Dighinala": "Dighinala", "Guimara": "Guimara", "Khagrachari Sadar": "Khagrachhari Sadar",
                          "Lakshmichari": "Lakshmichhari", "Mahalchari": "Mahalchhari", "Manikchari": "Manikchhari",
                          "Matiranga": "Matiranga", "Panchari": "Panchhari", "Ramgarh": "Ramgarh"},
         "Lakshmipur": {"Chandraganj": "", "Kamalnagar": "Kamalnagar", "Lakshmipur Sadar": "Lakshmipur Sadar", "Raipur": "Raipur",
                        "Ramganj": "Ramganj", "Ramgati": "Ramgati"},
         "Noakhali": {"Begumganj": "Begumganj", "Char Jabber": "", "Chatkhil": "Chatkhil", "Companiganj": "Companiganj",
                      "Hatia": "Hatiya", "Kabirhat": "Kabirhat", "Senbagh": "Senbagh", "Sonaimuri": "Sonaimuri",
                      "Subarnachar": "Subarnachar", "Sudharam": "Noakhali Sadar"},
         "Rangamati": {"Baghaichari": "Baghaichhari", "Barkal": "Barkal", "Belaichari": "Belaichhari", "Chandraghona": "",
                       "Juraichari": "Juraichhari", "Kaowkhali": "Kawkhali", "Kaptai": "Kaptai", "Kotwali_Rangamati": "Rangamati Sadar",
                       "Langadu": "Langadu", "Nanuerchar": "Naniarchar", "Rajasthali": "Rajasthali"}},
    notes={"Char Jabber": "Thana as published ('Char Jabber'); not mapped to an upazila because the table also lists 'Subarnachar' "
                          "separately (Char Jabbar is the police station of Subarnachar upazila).",
           "Sudharam": "'Sudharam' = Noakhali Sadar (Sudharam) thana."},
    t316={"quarter": "April-June 2026", "urban": 1435, "rural": 1247, "total": 2682}, next_division="Dhaka Division",
    table1_anchor="Table-1: Division and district-wise distribution of per capita deposits and advances on the basis",
    t1_name=r"[A-Z][a-z]+(?:'S Bazar)?", row33=r"^\s*([A-Za-z_][A-Za-z_ .'\-/()]*?)\s+([\d,]+)\s+(\d+)\s+([\d.]+%)\s*$")

# Khulna Division. Table-1 sits in the first part of the table (like Dhaka). '' = KMP thana (Kotwali_Khulna, Daulatpur in Khulna
# district, Harintana, Khalishpur, Khan Jahan Ali, Labonchora, Sonadanga) or other non-upazila thana (Darshana, Benapole,
# Islami University, Naragati, Patkelghata). Table-3.16 image: PDF page 35, printed page 27, 'Khulna division' column.
KHULNA = dict(
    dists={"Bagerhat": "Bagerhat", "Chuadanga": "Chuadanga", "Jashore": "Jashore", "Jhenaidah": "Jhenaidah", "Khulna": "Khulna",
           "Kushtia": "Kushtia", "Magura": "Magura", "Meherpur": "Meherpur", "Narail": "Narail", "Satkhira": "Satkhira"},
    upa={"Bagerhat": {"Bagerhat Sadar": "Bagerhat Sadar", "Chitalmari": "Chitalmari", "Fakirhat": "Fakirhat", "Kachua": "Kachua",
                      "Mollahat": "Mollahat", "Mongla": "Mongla", "Morrelganj": "Morrelganj", "Rampal": "Rampal",
                      "Sarankhola": "Sarankhola"},
         "Chuadanga": {"Alamdanga": "Alamdanga", "Chuadanga Sadar": "Chuadanga Sadar", "Damurhuda": "Damurhuda", "Darshana": "",
                       "Jiban Nagar": "Jibannagar"},
         "Jashore": {"Abhoynagar": "Abhaynagar", "Bagerpara": "Bagherpara", "Benapole": "", "Chowgacha": "Chaugachha",
                     "Jhikargacha": "Jhikargachha", "Keshabpur": "Keshabpur", "Kotwali": "Jashore Sadar", "Monirampur": "Manirampur",
                     "Sarsha": "Sharsha"},
         "Jhenaidah": {"Harinakundu": "Harinakunda", "Jhenidah Sadar": "Jhenaidah Sadar", "Kaliganj": "Kaliganj",
                       "Kotchandpur": "Kotchandpur", "Moheshpur": "Maheshpur", "Sailkupa": "Shailkupa"},
         "Khulna": {"Batiaghata": "Batiaghata", "Dacope": "Dacope", "Daulatpur": "", "Dighalia": "Dighalia", "Dumuria": "Dumuria",
                    "Harintana": "", "Khalishpur": "", "Khan Jahan Ali": "", "Kotwali_Khulna": "", "Koyra": "Koyra", "Labonchora": "",
                    "Paikgacha": "Paikgachha", "Phultala": "Phultala", "Rupsa": "Rupsa", "Sonadanga": "", "Terokhada": "Terokhada"},
         "Kushtia": {"Bheramara": "Bheramara", "Daulatpur": "Daulatpur", "Islami University": "", "Khoksa": "Khoksa",
                     "Kumarkhali": "Kumarkhali", "Kushtia Sadar": "Kushtia Sadar", "Mirpur": "Mirpur"},
         "Magura": {"Magura Sadar": "Magura Sadar", "Mohammadpur": "Mohammadpur", "Shalikha": "Shalikha", "Sreepur": "Sreepur"},
         "Meherpur": {"Gangni": "Gangni", "Meherpur": "Meherpur Sadar", "Muzibnagar": "Mujibnagar"},
         "Narail": {"Kalia": "Kalia", "Lohagora": "Lohagara", "Naragati": "", "Narail": "Narail Sadar"},
         "Satkhira": {"Ashasuni": "Assasuni", "Debhata": "Debhata", "Kalaroa": "Kalaroa", "Kaliganj": "Kaliganj", "Patkelghata": "",
                      "Satkhira Sadar": "Satkhira Sadar", "Shyamnagar": "Shyamnagar", "Tala": "Tala"}},
    notes={"Meherpur": "'Meherpur' = Meherpur Sadar thana.", "Narail": "'Narail' = Narail Sadar thana.",
           "Kotwali_Khulna": "'Kotwali_Khulna' = Khulna Sadar (Kotwali) thana of the Khulna Metropolitan Police; not an upazila."},
    t316={"quarter": "April-June 2026", "urban": 547, "rural": 555, "total": 1102}, next_division="Mymensingh Division",
    table1_anchor="Table-1: Division and district-wise distribution of per capita deposits and advances on the basis")

# Barishal Division. Table-1 sits in Table-1(Concl'd) (like Rajshahi); Table-33 is followed by Chattogram Division. '' = BMP
# thana (Kotwali_Barishal, Airport) or other non-upazila thana (Kazirhat, Char Shasivuson = Shashibhushan, Mohipur).
# Table-3.16 image: PDF page 36, printed page 28 (Table-3.16 Concld.), 'Barishal division' column.
BARISHAL = dict(
    dists={"Barguna": "Barguna", "Barishal": "Barishal", "Bhola": "Bhola", "Jhalokathi": "Jhalokathi", "Patuakhali": "Patuakhali",
           "Pirojpur": "Pirojpur"},
    upa={"Barguna": {"Amtali": "Amtali", "Bamna": "Bamna", "Barguna Sadar": "Barguna Sadar", "Betagi": "Betagi",
                     "Pathorghata": "Patharghata", "Taltoli": "Taltali"},
         "Barishal": {"Agailjhara": "Agailjhara", "Airport": "", "Babuganj": "Babuganj", "Bakerganj": "Bakerganj",
                      "Banaripara": "Banaripara", "Gouranadi": "Gaurnadi", "Hijla": "Hizla", "Kazirhat": "", "Kotwali_Barishal": "",
                      "Mehendiganj": "Mehendiganj", "Muladi": "Muladi", "Wazirpur": "Wazirpur"},
         "Bhola": {"Bhola Sadar": "Bhola Sadar", "Burhanuddin": "Burhanuddin", "Char Shasivuson": "", "Charfeshion": "Char Fasson",
                   "Daulatkhan": "Daulatkhan", "Lalmohan": "Lalmohan", "Monpura": "Manpura", "Tazumuddin": "Tazumuddin"},
         "Jhalokathi": {"Jhalokati Sadar": "Jhalokathi Sadar", "Kathalia": "Kanthalia", "Nalchity": "Nalchity", "Rajapur": "Rajapur"},
         "Patuakhali": {"Bawphal": "Bauphal", "Dashmina": "Dashmina", "Dumki": "Dumki", "Galachipa": "Galachipa", "Kalapara": "Kalapara",
                        "Mirjaganj": "Mirzaganj", "Mohipur": "", "Patuakhali Sadar": "Patuakhali Sadar", "Rangabali": "Rangabali"},
         "Pirojpur": {"Bhandaria": "Bhandaria", "Indurkani": "Indurkani", "Kaowkhali": "Kawkhali", "Mathbaria": "Mathbaria",
                      "Nazirpur": "Nazirpur", "Nesarabad": "Nesarabad", "Pirojpur Sadar": "Pirojpur Sadar"}},
    notes={"Kotwali_Barishal": "'Kotwali_Barishal' = Kotwali thana of the Barishal Metropolitan Police; not an upazila.",
           "Airport": "'Airport' = Airport thana of the Barishal Metropolitan Police; not an upazila.",
           "Char Shasivuson": "'Char Shasivuson' = Shashibhushan thana; not an upazila.",
           "Mohipur": "'Mohipur' = Mohipur thana; not an upazila.",
           "Kazirhat": "'Kazirhat' = Kazirhat thana; not an upazila."},
    t316={"quarter": "April-June 2026", "urban": 306, "rural": 271, "total": 577}, next_division="Chattogram Division")

# Sylhet Division. Table-1 sits in Table-1(Concl'd) (like Rajshahi); Table-33 ends the table (followed by 'Grand Total').
# '' = SMP thana (Kotwali_Sylhet, Jalalabad, Bimanbondar = Airport, Shahporan, Maglabazar = Moglabazar, Dakhin Surma = South
# Surma). Table-3.16 image: PDF page 36, printed page 28 (Table-3.16 Concld.), 'Sylhet division' column.
_SMP_NOTE = "thana of the Sylhet Metropolitan Police; not an upazila."
SYLHET = dict(
    dists={"Habiganj": "Habiganj", "Moulvibazar": "Moulvibazar", "Sunamganj": "Sunamganj", "Sylhet": "Sylhet"},
    upa={"Habiganj": {"Ajmiriganj": "Ajmiriganj", "Bahubal": "Bahubal", "Banichang": "Baniachong", "Chunarughat": "Chunarughat",
                      "Habiganj Sadar": "Habiganj Sadar", "Lakhai": "Lakhai", "Madhabpur": "Madhabpur", "Nabiganj": "Nabiganj",
                      "Shayestaganj": "Shayestaganj"},
         "Moulvibazar": {"Baralekha": "Barlekha", "Juri": "Juri", "Kamalganj": "Kamalganj", "Kulaura": "Kulaura",
                         "Moulvibazar Sadar": "Moulvibazar Sadar", "Rajanagar": "Rajnagar", "Sreemangal": "Sreemangal"},
         "Sunamganj": {"Bishwamvarpur": "Bishwambarpur", "Chhatak": "Chhatak", "Dakshin Sunamganj": "South Sunamganj", "Derai": "Derai",
                       "Dharmapasha": "Dharmapasha", "Dowar Bazar": "Dowarabazar", "Jagannathpur": "Jagannathpur",
                       "Jamalganj": "Jamalganj", "Madhaya Nagar": "Madhyanagar", "Salla": "Shalla", "Sunamganj Sadar": "Sunamganj Sadar",
                       "Tahirpur": "Tahirpur"},
         "Sylhet": {"Balaganj": "Balaganj", "Biani Bazar": "Beanibazar", "Bimanbondar": "", "Bishwanath": "Bishwanath",
                    "Companiganj": "Companiganj", "Dakhin Surma": "", "Fenchuganj": "Fenchuganj", "Golapganj": "Golapganj",
                    "Gowainghat": "Gowainghat", "Jaintiapur": "Jaintiapur", "Jalalabad": "", "Kanaighat": "Kanaighat",
                    "Kotwali_Sylhet": "", "Maglabazar": "", "Osmani Nagar": "Osmani Nagar", "Shahporan": "", "Zakiganj": "Zakiganj"}},
    notes={"Kotwali_Sylhet": "'Kotwali_Sylhet' = Kotwali " + _SMP_NOTE,
           "Bimanbondar": "'Bimanbondar' = Airport (বিমানবন্দর) " + _SMP_NOTE,
           "Jalalabad": "'Jalalabad' = Jalalabad " + _SMP_NOTE,
           "Shahporan": "'Shahporan' = Shah Poran " + _SMP_NOTE,
           "Maglabazar": "'Maglabazar' = Moglabazar " + _SMP_NOTE,
           "Dakhin Surma": "'Dakhin Surma' is listed beside the SMP thanas (Kotwali_Sylhet, Jalalabad, Bimanbondar, Shahporan, "
                           "Maglabazar); read as the SMP South Surma thana and not mapped to Dakshin Surma upazila."},
    t316={"quarter": "April-June 2026", "urban": 397, "rural": 428, "total": 825}, next_division="Grand Total")

# Mymensingh Division. Table-1 sits in Table-1(Concl'd) (like Rajshahi, after Barishal); Table-33 is followed by Rajshahi
# Division. No metropolitan police: 'Kotwali_Mymensingh' is the Mymensingh Sadar (Kotwali) thana (like 'Kotwali_Bogura');
# '' = Pagla thana (in Gafargaon upazila). Table-3.16 image: PDF page 36, printed page 28 (Table-3.16 Concld.),
# 'Mymensingh division' column.
MYMENSINGH = dict(
    dists={"Jamalpur": "Jamalpur", "Mymensingh": "Mymensingh", "Netrokona": "Netrokona", "Sherpur": "Sherpur"},
    upa={"Jamalpur": {"Bakshiganj": "Bokshiganj", "Dewanganj": "Dewangonj", "Islampur": "Islampur", "Jamalpur Sadar": "Jamalpur Sadar",
                      "Madarganj": "Madarganj", "Melandah": "Melandah", "Sarishabari": "Sarishabari"},
         "Mymensingh": {"Bhaluka": "Bhaluka", "Dhobaura": "Dhobaura", "Fulbaria": "Fulbaria", "Goffargaon": "Gafargaon",
                        "Gouripur": "Gouripur", "Haluaghat": "Haluaghat", "Ishwarganj": "Iswarganj",
                        "Kotwali_Mymensingh": "Mymensingh Sadar", "Muktagacha": "Muktagacha", "Nandail": "Nandail", "Pagla": "",
                        "Phulpur": "Phulpur", "Tarakanda": "Tarakanda", "Trisal": "Trishal"},
         "Netrokona": {"Atpara": "Atpara", "Barhatta": "Barhatta", "Durgapur": "Durgapur", "Kaliajuri": "Khaliajuri",
                       "Kalmakanda": "Kalmakanda", "Kendua": "Kendua", "Madan": "Madan", "Mohonganj": "Mohongonj",
                       "Netrokona": "Netrokona Sadar", "Purbadhala": "Purbadhala"},
         "Sherpur": {"Jhenaigati": "Jhenaigati", "Nakla": "Nokla", "Nalitabari": "Nalitabari", "Sherpur Sadar": "Sherpur Sadar",
                     "Sreebordi": "Sreebordi"}},
    notes={"Netrokona": "'Netrokona' = Netrokona Sadar thana.",
           "Pagla": "'Pagla' = Pagla thana (in Gafargaon upazila); not an upazila.",
           "Kaliajuri": "'Kaliajuri' = Khaliajuri as spelled by the source."},
    t316={"quarter": "April-June 2026", "urban": 242, "rural": 231, "total": 473}, next_division="Rajshahi Division")


def num(s):
    return s.replace(",", "")


def main():
    global HERE, RAW, KEY, DISTS, UPA, T316
    args, out, KEY = division_setup(HERE, KEY, ["rajshahi", "rangpur", "dhaka", "chattogram", "khulna", "barishal", "sylhet",
                                                  "mymensingh"])
    HERE, RAW = Path(out), Path(out) / "raw"
    division, head = args.division, args.division.capitalize()
    div_label, next_div, upa_by_dist = f"{head} Division", "Rangpur Division", None
    if division == "rangpur":
        DISTS, T316, next_div, upa_by_dist = RANGPUR["dists"], RANGPUR["t316"], RANGPUR["next_division"], RANGPUR["upa"]
    cfg = DHAKA if division == "dhaka" else CHATTOGRAM if division == "chattogram" else KHULNA if division == "khulna" else \
        BARISHAL if division == "barishal" else SYLHET if division == "sylhet" else \
        MYMENSINGH if division == "mymensingh" else {}
    if cfg:
        DISTS, T316, next_div, upa_by_dist = cfg["dists"], cfg["t316"], cfg["next_division"], cfg["upa"]
    row33 = r"^\s*([A-Za-z_][A-Za-z_ ]*?)\s+([\d,]+)\s+(\d+)\s+([\d.]+%)\s*$"
    if cfg:  # names with . - / ( )
        row33 = cfg.get("row33", r"^\s*([A-Za-z_][A-Za-z_ .\-/()]*?)\s+([\d,]+)\s+(\d+)\s+([\d.]+%)\s*$")
    facts = []
    pdf_url, quarter = PDF_FALLBACK, "April-June, 2026"
    r = get(URL_LIST)
    if r is not None and r.ok:
        m = re.search(r"<tr><td>([^<]+?)<a[^>]*pdf-link\s*=\s*'([^']+\.pdf)'", r.text)
        if m:
            quarter, pdf_url = clean(m.group(1)).rstrip(". "), m.group(2).replace(" ", "%20")
    r = get(pdf_url, timeout=180)
    txt = None
    if r is not None and r.ok and r.content[:4] == b"%PDF":
        tmp = save_raw("_sbs.pdf", r.content)
        txt = pdftotext(tmp)
        tmp.unlink(missing_ok=True)
        if RAW.exists() and not any(RAW.iterdir()):
            RAW.rmdir()
    if not txt:
        print("WARNING: PDF text unavailable (needs poppler pdftotext); only the transcribed Table-3.16 values are written")
    asof = re.search(r"As on (\d{2}-\d{2}-\d{4})", txt or "")
    year = int(asof.group(1)[-4:]) if asof else ""
    base_note = f"Bangladesh Bank, Scheduled Banks Statistics {quarter}" + (f" (as on {asof.group(1)})" if asof else "")
    if txt:
        # Table-1: Division and district-wise per capita deposits and advances (Taka in lac)
        i = txt.find(div_label, txt.find(cfg.get("table1_anchor", "Table-1(Concl")))
        for line in txt[i:i + 3000].splitlines():
            m = re.match(r"^\s*(%s|%s)\s+([\d,]+)\s+([\d,]+)\s+([\d.]+)\s+([\d,]+)\s+([\d.]+)\s*$" % (div_label, cfg.get("t1_name", "[A-Z][a-z]+")), line)
            if not m:
                if line.strip().startswith(("Rangpur", "Sylhet") if division == "rajshahi" else ("Grand Total", "Sylhet")):
                    break
                continue
            name = m.group(1)
            lvl, d = ("division", "") if name == div_label else ("district", DISTS.get(name, ""))
            if lvl == "district" and not d:
                break
            en = head if lvl == "division" else d
            for fact, val, unit in (("bank_deposits", num(m.group(3)), "BDT lakh"), ("bank_deposits_per_capita", m.group(4), "BDT lakh per person"),
                                    ("bank_advances", num(m.group(5)), "BDT lakh"), ("bank_advances_per_capita", m.group(6), "BDT lakh per person")):
                facts.append(dict(entity_level=lvl, entity_name_en=en, district_en=d, fact=fact, value=val, unit=unit, basis="reported",
                                  year=year, source_key=KEY, source_url=pdf_url,
                                  notes=f"{base_note}, Table-1 (all scheduled banks). Per-capita figures use Bangladesh Bank's population basis ({num(m.group(2))} persons)."))
        # Table-33: deposits by divisions, districts and thanas (all banks)
        a = txt.find(div_label, txt.rfind("Table-33: Deposits distributed"))
        b = txt.find(next_div, a)
        cur = ""
        for line in txt[a:b].splitlines():
            m = re.match(row33, line)
            if not m:
                continue
            name = m.group(1).strip()
            if name == div_label:
                lvl, d, en, up = "division", "", head, ""
            elif name.endswith(" District"):
                cur = DISTS.get(name[:-9], "")
                lvl, d, en, up = "district", cur, cur, ""
            else:
                lvl, d, en, up = "thana", cur, name, (UPA.get(name, "") if upa_by_dist is None else upa_by_dist.get(cur, {}).get(name, ""))
            note = f"{base_note}, Table-33 (all banks; thana-level as published by Bangladesh Bank)."
            if lvl == "thana" and not up:
                note += " Thana is a metropolitan/non-upazila thana or a spelling not mapped (upazila_en empty)."
            if division != "rajshahi" and lvl == "thana" and name == "Kotwali" and up:
                note += f" 'Kotwali' = {up} (Kotwali) thana."
            if cfg and name.startswith("Kotwali_") and up:
                note += f" '{name}' = {up} (Kotwali) thana as spelled by the source."
            if cfg and name in cfg["notes"]:
                note += " " + cfg["notes"][name]
            if name == "Kotwali_Bogura":
                note += " 'Kotwali_Bogura' = Bogura Sadar (Kotwali) thana as spelled by the source."
                up = "Bogura Sadar"
            for fact, val, unit in (("bank_deposit_accounts", num(m.group(2)), "accounts"), ("bank_deposits", m.group(3), "BDT lakh")):
                if lvl != "thana" and fact == "bank_deposits":
                    continue  # district/division deposits already from Table-1
                facts.append(dict(entity_level=lvl, entity_name_en=en, district_en=d, upazila_en=up, fact=fact, value=val, unit=unit,
                                  basis="reported", year=year, source_key=KEY, source_url=pdf_url, notes=note))
    if pdf_url == PDF_FALLBACK:
        for k in ("urban", "rural", "total"):
            facts.append(dict(entity_level="division", entity_name_en=head, fact=f"scheduled_bank_branches_{k}" if k != "total" else "scheduled_bank_branches",
                              value=T316[k], unit="branches", basis="reported", year=2026, source_key=KEY, source_url=pdf_url,
                              notes=f"Bangladesh Bank, Scheduled Banks Statistics {T316['quarter']}, Table-3.16 'Region-wise position of scheduled bank branches' "
                                    "(end of quarter); transcribed from the table image. No district-level branch counts are published."))
    else:
        print("NOTE: newer quarter published — Table-3.16 (image) must be re-transcribed by hand; not written")
    write_csv("facts.csv", FACT_COLS, facts)
    write_manifest(dict(
        key=KEY, division=division, kind="bb_banks",
        name=f"Bangladesh Bank — Scheduled Banks Statistics ({head} Division extract)", organization="Bangladesh Bank",
        source_type="government_portal", trust_level=4, urls=[URL_LIST, pdf_url], accessed=__import__("datetime").date.today().isoformat(),
        publication_date=None, license=None, license_url=None, attribution="Bangladesh Bank (bb.org.bd)",
        notes="No licence stated. bb.org.bd publishes no public, filterable scheduled-bank branch list (no branch names/addresses/routing "
              "numbers; the routing-number URL is blocked by the site's WAF). Only aggregate statistics are available: division branch "
              f"counts (Table-3.16, image), district deposits/advances (Table-1) and thana deposit accounts/amounts (Table-33). "
              "The 8.5 MB PDF is not committed; fetch.py re-downloads it and needs poppler's pdftotext to parse it."),
        ["facts.csv"])


if __name__ == "__main__":
    main()
