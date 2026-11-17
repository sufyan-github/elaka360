#!/usr/bin/env python3
"""Fetch thana / SP-office / control-room numbers for RMP and Rajshahi Range from the Police HQ contact workbook (BD_POLICE_CONTACTS_2020).

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
        s = re.sub(r"^OC\s+", "", post.strip())
        s = re.sub(r"\s*(Thana|PS)$", "", s, flags=re.I).strip()
        return re.sub(r"\s+", " ", re.sub(r"\s+Model$", "", s, flags=re.I).strip())
    s = re.sub(r"^OC\s+", "", post.strip())
    s = re.sub(r"\s+(Thana|PS)$", "", s).strip()
    s = re.sub(r"\s+Model$", "", s, flags=re.I).strip()
    return re.sub(r"\s+", " ", s)


def main():
    global HERE, RAW, KEY, SHEETS, DIST, UPA, DIVISION
    args, out, KEY = division_setup(HERE, KEY, ["rajshahi", "rangpur"])
    HERE, RAW, DIVISION = Path(out), Path(out) / "raw", args.division
    metro_sheet, range_sheet, metro, metro_short, head = "RMP", "Rajshahi Range", "Rajshahi Metropolitan Police", "rmp", "Rajshahi"
    raw_name = "police_contacts_2020_rmp_rajshahi_range.csv"
    if DIVISION == "rangpur":
        SHEETS, DIST, UPA, raw_name = RANGPUR["sheets"], RANGPUR["dist"], RANGPUR["upa"], RANGPUR["raw"]
        metro_sheet, range_sheet, metro, metro_short, head = "RRMP", "Rangpur Range", RANGPUR["metro"], "rpmp", RANGPUR["head"]
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
            raw_rows.append([sheet] + row)
            first = row[0] if row else ""
            if first.startswith("Unit/Office Name:"):
                office = first.split(":", 1)[1].strip().rstrip(".")
                dist = head if sheet == metro_sheet else next((v for k, v in DIST.items() if k.lower() in office.lower()), "")
                if "Range Office" in office:
                    dist = ""
                if DIVISION != "rajshahi" and sheet != metro_sheet and not re.search(r"District|SP Office", office):
                    dist = ""  # range office ('DIG Rangpur Range') and RRF blocks are not collected
                last_thana = None
                continue
            if first and not first[0].isdigit() and "Unit/Office" not in first and not first.startswith("SL"):
                if sheet == range_sheet and first.strip() and len([c for c in row if c]) == 1:
                    office, dist, last_thana = first.strip(), "", None   # e.g. 'RRF Rajshahi' — not collected
                    continue
            row = row + [""] * (7 - len(row))
            sl, desig, post, official, current, new, email = [re.sub(r"\s+", " ", x).strip() for x in row[:7]]
            if DIVISION == "rajshahi":
                email = email.replace(" ", "")
            else:  # several addresses separated by spaces; 'x @ police.gov.bd.' written with spaces and a full stop
                email = re.sub(r"\s*@\s*", "@", email)
                email = "; ".join(e.strip(".") for e in email.split() if "@" in e)
            if not dist:
                continue
            upa_map = UPA[metro_sheet if sheet == metro_sheet else dist]
            if re.match(r"^OC\s", post):
                key = thana_key(post)
                upa = upa_map.get(key, "")
                unit = "metropolitan_thana" if sheet == metro_sheet else "district_police_thana"
                sid = f"bdpol2020-{sheet.replace(' ', '')}-{sl}"
                if DIVISION != "rajshahi" and sheet != metro_sheet:  # serials restart in every district block
                    sid = f"bdpol2020-{sheet.replace(' ', '')}-{dist.lower()}-{sl}"
                dup_note = ""
                if DIVISION != "rajshahi" and sid in used_ids:  # the sheet repeats a serial number (e.g. Lalmonirhat 'OC Kaligonj' copies Aditmari's SL 27)
                    sid = f"{sid}-{re.sub(r'[^a-z]', '', key.lower())}"
                    dup_note = "Serial number repeated in the source (row copied from the previous thana; official number/e-mail may belong to it). "
                used_ids.add(sid)
                last_thana = dict(
                    source_key=KEY, source_id=sid, name_bn="", name_en=post[3:].strip(),
                    category_key="emergency.police_station", district_en=dist, upazila_en=upa, phone=new, email=email,
                    operator=metro if sheet == metro_sheet else f"{dist} District Police", ownership="public",
                    _extra={"unit": unit, "office_in_source": office, "oc_new_number": new, "oc_current_number_2020": current,
                            "official_landline_raw": official},
                    source_url=xurl,
                    notes="Numbers as of the Police HQ list uploaded 03-10-2020 ('New Number' = official 01320-series SIM). "
                          + dup_note
                          + (f"upazila_en holds the {metro_short.upper() if DIVISION == 'rajshahi' else 'RpMP'} metropolitan thana. " if sheet == metro_sheet else "")
                          + ("" if upa else "Thana is not an upazila (or name not mapped); upazila_en left empty. "))
                places.append(last_thana)
            elif last_thana and re.search(r"duty officer", desig + " " + post, re.I):
                last_thana["_extra"]["duty_officer_new_number"] = new
                if current:
                    last_thana["_extra"]["duty_officer_current_number_2020"] = current
            elif desig == "SP" and post in ("1", "01", "") and sl == "1" and ("SP Office" in office or (DIVISION != "rajshahi" and "District" in office)):
                places.append(dict(
                    source_key=KEY, source_id=f"bdpol2020-sp-{dist.lower()}", name_bn="",
                    name_en=office if "SP Office" in office else f"SP Office, {dist}",
                    category_key="government.sp_office", district_en=dist, phone=new, email=email,
                    operator=f"{dist} District Police", ownership="public",
                    _extra={"sp_new_number": new, "sp_current_number_2020": current, "official_landline_raw": official},
                    source_url=xurl, notes="Phone = Superintendent of Police official number (role SIM) from the 2020 HQ list"
                                           + ("" if "SP Office" in office else f"; name composed from the sheet heading '{office}'")))
            elif re.match(r"^(RMP )?Control Room$", desig, re.I) or desig == "Hotline":
                cid = f"bdpol2020-control-{dist.lower() if sheet != metro_sheet else metro_short}"
                ex = next((p for p in places if p["source_id"] == cid), None)
                if ex is None:
                    ex = dict(source_key=KEY, source_id=cid, name_bn="",
                              name_en=(f"{metro_short.upper() if DIVISION == 'rajshahi' else 'RpMP'} Control Room" if sheet == metro_sheet else f"Control Room, {office}"),
                              category_key="emergency", district_en=dist, phone="", operator=(metro if sheet == metro_sheet else f"{dist} District Police"),
                              ownership="public", _extra={}, source_url=xurl, notes="Police control room numbers from the 2020 HQ list")
                    places.append(ex)
                nums = [x for x in (new, current) if x]
                ex["phone"] = "; ".join([p for p in ex["phone"].split("; ") if p] + nums)
                if official:
                    ex["_extra"]["official_landline_raw"] = official
                if desig == "Hotline":
                    ex["_extra"]["hotline"] = new
                if email:
                    ex["email"] = email.replace(" ", "")
    for p in places:
        p["extra_json"] = xj(p.pop("_extra"))
    RAW.mkdir(exist_ok=True)
    with open(RAW / raw_name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sheet", "sl", "designation", "post", "official_number", "current_number", "new_number", "email"])
        for row in raw_rows:
            w.writerow((row + [""] * 8)[:8])
    write_csv("places.csv", PLACE_COLS, places)
    write_manifest(dict(
        key=KEY, division=DIVISION, kind="police_hq_2020",
        name=f"Bangladesh Police HQ — Contacts of Bangladesh Police ({SHEETS[0]} and {SHEETS[1]} sheets)",
        organization="Bangladesh Police Headquarters", source_type="government_portal", trust_level=4,
        urls=[URL_PAGE, xurl], accessed=__import__("datetime").date.today().isoformat(), publication_date="2020-10-03",
        license=None, license_url=None, attribution="Bangladesh Police (police.gov.bd)",
        notes=f"No licence stated. XLSX 'Contacts Of Bangladesh Police' uploaded 03-10-2020 (Last-Modified 2020-10-03). Only the {SHEETS[0]} and "
              f"{SHEETS[1]} sheets are used (raw/ keeps those rows as CSV; the full 1.5 MB workbook is re-downloaded by fetch.py). "
              "Designations only, no personal names. Old 2020 numbers: the 01320-series 'New Number' values match the 2026 district/RMP "
              "portals where checked; the 'Current Number' column is the pre-2020 numbering."
              + ("" if DIVISION == "rajshahi" else " For this division the 2026 portals were not cross-checked by this collector.")),
        ["places.csv", "raw/" + raw_name])


if __name__ == "__main__":
    main()
