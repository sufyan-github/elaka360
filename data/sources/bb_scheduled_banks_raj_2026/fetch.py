#!/usr/bin/env python3
"""Extract Rajshahi-Division bank statistics from Bangladesh Bank's quarterly Scheduled Banks Statistics (BB_SCHEDULED_BANKS_RAJ_2026)."""
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


def num(s):
    return s.replace(",", "")


def main():
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
        i = txt.find("Rajshahi Division", txt.find("Table-1(Concl"))
        for line in txt[i:i + 3000].splitlines():
            m = re.match(r"^\s*(Rajshahi Division|[A-Z][a-z]+)\s+([\d,]+)\s+([\d,]+)\s+([\d.]+)\s+([\d,]+)\s+([\d.]+)\s*$", line)
            if not m:
                if line.strip().startswith(("Rangpur", "Sylhet")):
                    break
                continue
            name = m.group(1)
            lvl, d = ("division", "") if name == "Rajshahi Division" else ("district", DISTS.get(name, ""))
            if lvl == "district" and not d:
                break
            en = "Rajshahi" if lvl == "division" else d
            for fact, val, unit in (("bank_deposits", num(m.group(3)), "BDT lakh"), ("bank_deposits_per_capita", m.group(4), "BDT lakh per person"),
                                    ("bank_advances", num(m.group(5)), "BDT lakh"), ("bank_advances_per_capita", m.group(6), "BDT lakh per person")):
                facts.append(dict(entity_level=lvl, entity_name_en=en, district_en=d, fact=fact, value=val, unit=unit, basis="reported",
                                  year=year, source_key=KEY, source_url=pdf_url,
                                  notes=f"{base_note}, Table-1 (all scheduled banks). Per-capita figures use Bangladesh Bank's population basis ({num(m.group(2))} persons)."))
        # Table-33: deposits by divisions, districts and thanas (all banks)
        a = txt.find("Rajshahi Division", txt.rfind("Table-33: Deposits distributed"))
        b = txt.find("Rangpur Division", a)
        cur = ""
        for line in txt[a:b].splitlines():
            m = re.match(r"^\s*([A-Za-z_][A-Za-z_ ]*?)\s+([\d,]+)\s+(\d+)\s+([\d.]+%)\s*$", line)
            if not m:
                continue
            name = m.group(1).strip()
            if name == "Rajshahi Division":
                lvl, d, en, up = "division", "", "Rajshahi", ""
            elif name.endswith(" District"):
                cur = DISTS.get(name[:-9], "")
                lvl, d, en, up = "district", cur, cur, ""
            else:
                lvl, d, en, up = "thana", cur, name, UPA.get(name, "")
            note = f"{base_note}, Table-33 (all banks; thana-level as published by Bangladesh Bank)."
            if lvl == "thana" and not up:
                note += " Thana is a metropolitan/non-upazila thana or a spelling not mapped (upazila_en empty)."
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
            facts.append(dict(entity_level="division", entity_name_en="Rajshahi", fact=f"scheduled_bank_branches_{k}" if k != "total" else "scheduled_bank_branches",
                              value=T316[k], unit="branches", basis="reported", year=2026, source_key=KEY, source_url=pdf_url,
                              notes=f"Bangladesh Bank, Scheduled Banks Statistics {T316['quarter']}, Table-3.16 'Region-wise position of scheduled bank branches' "
                                    "(end of quarter); transcribed from the table image. No district-level branch counts are published."))
    else:
        print("NOTE: newer quarter published — Table-3.16 (image) must be re-transcribed by hand; not written")
    write_csv("facts.csv", FACT_COLS, facts)
    write_manifest(dict(
        key=KEY, name="Bangladesh Bank — Scheduled Banks Statistics (Rajshahi Division extract)", organization="Bangladesh Bank",
        source_type="government_portal", trust_level=4, urls=[URL_LIST, pdf_url], accessed=__import__("datetime").date.today().isoformat(),
        publication_date=None, license=None, license_url=None, attribution="Bangladesh Bank (bb.org.bd)",
        notes="No licence stated. bb.org.bd publishes no public, filterable scheduled-bank branch list (no branch names/addresses/routing "
              "numbers; the routing-number URL is blocked by the site's WAF). Only aggregate statistics are available: division branch "
              f"counts (Table-3.16, image), district deposits/advances (Table-1) and thana deposit accounts/amounts (Table-33). "
              "The 8.5 MB PDF is not committed; fetch.py re-downloads it and needs poppler's pdftotext to parse it."),
        ["facts.csv"])


if __name__ == "__main__":
    main()
