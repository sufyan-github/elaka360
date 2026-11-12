#!/usr/bin/env python3
"""Fetch Bangladesh Railway station phones and district-wise station counts for Rajshahi Division (BD_RAILWAY_RAJ_2026)."""
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


def main():
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
                name = {"Coxbazar": "Cox's Bazar"}.get(m.group(1), m.group(1))
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
    facts.append(dict(entity_level="division", entity_name_en="Rajshahi", fact="railway_stations", value=tot_st, unit="stations",
                      basis="derived (sum of district rows)", year=2024, source_key=KEY, source_url=pdf_url,
                      notes="Sum of the 8 Rajshahi-division districts in Table-4 (FY 2023-2024)"))
    facts.append(dict(entity_level="division", entity_name_en="Rajshahi", fact="railway_route_km", value=tot_km, unit="km",
                      basis="derived (sum of district rows)", year=2024, source_key=KEY, source_url=pdf_url,
                      notes="Sum of the 8 Rajshahi-division districts in Table-4 (FY 2023-2024)"))
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    files = ["places.csv", "facts.csv", "raw/railway_important_station_phones.txt"]
    if (RAW / "infobook_2023_24_table4.txt").exists():
        files.append("raw/infobook_2023_24_table4.txt")
    write_manifest(dict(
        key=KEY, name="Bangladesh Railway — station phones and district-wise station counts (Rajshahi Division)",
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
