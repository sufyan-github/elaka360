#!/usr/bin/env python3
"""Fetch CAAB airport data for airports in Rajshahi Division (CAAB_AIRPORTS_RAJ_2026)."""
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

# --- CAAB_AIRPORTS_RAJ_2026 ---------------------------------------------------------------------------
KEY = "CAAB_AIRPORTS_RAJ_2026"
URL_HOME = "https://www.caab.gov.bd/"
URL_ALL = "https://new.caab.gov.bd/airportsf.html"
URL_CONTACTS = "https://new.caab.gov.bd/contactof.html"
AIRPORTS = [  # (page, name_bn as on caab.gov.bd menu, district, upazila)
    ("https://new.caab.gov.bd/airports/rajshahi.html", "শাহ মখদুম বিমানবন্দর", "Rajshahi", ""),
    ("https://new.caab.gov.bd/airports/ishwardi.html", "ঈশ্বরদী বিমানবন্দর", "Pabna", "Ishwardi"),
]


def dms(s, neg_letters="SW"):
    """'242619.39N' / '0883658.56E' -> decimal degrees (CAAB 'Latitude'/'Longitude' fields)."""
    m = re.match(r"^(\d{2,3})(\d{2})(\d{2}(?:\.\d+)?)([NSEW])$", s.strip())
    if not m:
        return None
    v = int(m.group(1)) + int(m.group(2)) / 60 + float(m.group(3)) / 3600
    return round(-v if m.group(4) in neg_letters else v, 6)


def field(lines, label):
    for i, l in enumerate(lines):
        if l.rstrip(" |").strip().lower() == label.lower():
            for nxt in lines[i + 1:i + 3]:
                v = nxt.strip(" |")
                if v:
                    return v
    return ""


def main():
    places, facts = [], []
    menu = ""
    r = get(URL_HOME)
    if r is not None and r.ok:
        menu = r.text
    for url, name_bn, dist, upa in AIRPORTS:
        r = get(url)
        if r is None or not r.ok:
            print("unavailable", url)
            continue
        save_raw(url.rsplit("/", 1)[1].replace(".html", ".txt"), "\n".join(clean(l) for l in re.sub(r"<(script|style)[^>]*>.*?</\1>", "", r.text, flags=re.S | re.I).splitlines() if clean(l)))
        s = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", r.text, flags=re.S | re.I)
        s = re.sub(r"</(tr|p|div|li|h\d|td)>|<br\s*/?>", "\n", s, flags=re.I)
        lines = [clean(l) for l in s.splitlines()]
        lines = [l for l in lines if l]
        title = next((l for l in lines if l.endswith("Airport,")), "").rstrip(",")
        icao, iata = field(lines, "ICAO ID"), field(lines, "IATA CODE")
        lat_s, lon_s = field(lines, "Latitude"), field(lines, "Longitude")
        txt = " ".join(lines)
        ph = re.search(r"Phone:\s*([+\d ()]+)\(Off\)", txt)
        cell = re.search(r"Cell:\s*([+\d ,]+?)(?:\s+e-?mail|\s+email)", txt, flags=re.I)
        em = re.search(r"e-?mail\s*:\s*([\w.]+@caab\.gov\.bd)", txt, flags=re.I)
        phones = [p.strip() for p in ([ph.group(1)] if ph else []) + (cell.group(1).split(",") if cell else []) if p.strip()]
        extra = {"icao_on_page": icao, "iata": iata, "latitude_raw": lat_s, "longitude_raw": lon_s,
                 "twr_freq": field(lines, "TWR FREQ") or field(lines, "TWR FREQ."), "ndb": field(lines, "NDB"), "dvor": field(lines, "DVOR")}
        notes = ["Coordinates converted from the DDMMSS values on the CAAB airport page (aerodrome reference as published)"]
        if icao == "VISD":
            notes.append("CAAB page prints ICAO 'VISD'; Ishwardi's ICAO location indicator in ICAO Doc 7910 is VGIS — kept as printed, needs checking")
        if name_bn not in menu:
            notes.append("Bangla name taken from the caab.gov.bd airport menu (not found on this run)")
        places.append(dict(
            source_key=KEY, source_id=f"caab-{(iata or icao).lower()}", name_bn=name_bn, name_en=title,
            category_key="transport.airport", lat=dms(lat_s) or "", lon=dms(lon_s) or "", district_en=dist, upazila_en=upa,
            phone="; ".join(phones), email=em.group(1) if em else "", website=url, operator="বেসামরিক বিমান চলাচল কর্তৃপক্ষ, বাংলাদেশ (CAAB)",
            ownership="public", extra_json=xj(extra), source_url=url,
            notes="; ".join(notes) + ("; upazila_en from the airport name" if upa else "")))
    r = get(URL_ALL)
    if r is not None and r.ok:
        pass
        txt = clean(r.text)
        if "Bogura Airport" in txt:
            places.append(dict(
                source_key=KEY, source_id="caab-bogura", name_bn="", name_en="Bogura Airport", category_key="transport.airport",
                district_en="Bogura", operator="", ownership="public",
                extra_json=xj({"caab_status": "Needs prior approval for air operation"}), source_url=URL_ALL,
                notes="Listed by CAAB under 'Needs prior approval for air operation' (no passenger service); CAAB publishes no airport page, "
                      "codes, coordinates or contact for it"))
        m = re.search(r"Service not available-\(3\)(.*?)UNDER CONSTRUCTION", txt)
        for p in places:
            if p["source_id"] == "caab-ird" or "Ishwardi" in p["name_en"]:
                p["extra_json"] = xj(dict(json.loads(p["extra_json"] or "{}"), caab_status="Service not available (listed as 'Ishurdi Airport')"))
            if "Shah Makhdum" in p["name_en"]:
                p["extra_json"] = xj(dict(json.loads(p["extra_json"] or "{}"), caab_status="Domestic, operational"))
    r = get(URL_CONTACTS)
    if r is not None and r.ok:
        txt = clean(r.text)
        for p in places:
            if not p.get("email"):
                continue
            i = txt.find(p["email"])
            j = max(txt.rfind("Airport Manager", 0, i), txt.rfind("Director", 0, i))
            if i > 0 and j >= 0:
                seg = txt[j:i]
                found = [x.strip() for x in re.findall(r"\+?[\d][\d \-]{6,}\d", seg)]
                if found:
                    ex = json.loads(p["extra_json"] or "{}")
                    ex["numbers_on_contacts_page"] = found
                    p["extra_json"] = xj(ex)
                    own = {re.sub(r"\D", "", x)[-10:] for x in p["phone"].split("; ")}
                    diff = [x for x in found if re.sub(r"\D", "", x)[-10:] not in own]
                    if diff:
                        p["notes"] += "; CAAB contacts page lists " + ", ".join(diff) + " (not on the airport page)"
    write_csv("places.csv", PLACE_COLS, places)
    write_manifest(dict(
        key=KEY, name="Civil Aviation Authority of Bangladesh — airports in Rajshahi Division", organization="Civil Aviation Authority of Bangladesh (CAAB)",
        source_type="government_portal", trust_level=4, urls=[URL_HOME, URL_ALL, URL_CONTACTS] + [a[0] for a in AIRPORTS],
        accessed=__import__("datetime").date.today().isoformat(), publication_date=None, license=None, license_url=None,
        attribution="Civil Aviation Authority of Bangladesh (caab.gov.bd)",
        notes="No licence stated. Airline-office and individual staff numbers on the airport pages are not collected; only the "
              "Airport Manager office phone/cell/e-mail. caab.gov.bd omits the Sectigo OV R36 intermediate (handled by the AIA helper)."),
        ["places.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


if __name__ == "__main__":
    main()
