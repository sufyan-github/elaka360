#!/usr/bin/env python3
"""Fetch BRTC bus depots located in Rajshahi Division from brtc.gov.bd (BRTC_DEPOTS_RAJ_2026)."""
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

# --- BRTC_DEPOTS_RAJ_2026 -----------------------------------------------------------------------------
KEY = "BRTC_DEPOTS_RAJ_2026"
URL = "https://brtc.gov.bd/pages/static-pages/6922e14e933eb65569e2b6c0"   # ডিপো/ইউনিটসমূহের কর্মকর্তাবৃন্দের তালিকা
DIST = {nfc("বগুড়া"): "Bogura", nfc("পাবনা"): "Pabna", nfc("রাজশাহী"): "Rajshahi", nfc("সিরাজগঞ্জ"): "Sirajganj", nfc("নাটোর"): "Natore",
        nfc("নওগাঁ"): "Naogaon", nfc("জয়পুরহাট"): "Joypurhat", nfc("চাঁপাইনবাবগঞ্জ"): "Chapainawabganj"}


def main():
    places = []
    r = get(URL)
    if r is not None and r.ok:
        for t in tables(r.text):
            for row in t:
                if len(row) < 3:
                    continue
                m = re.search(r"(\S+) (বাস ডিপো(?: ও প্রশিক্ষণ কেন্দ্র)?|প্রশিক্ষণ কেন্দ্র)$", nfc(row[1]))
                if not m or nfc(m.group(1)) not in DIST:
                    continue
                name = f"{m.group(1)} {m.group(2)}"
                is_depot = "বাস ডিপো" in name
                if not is_depot:
                    continue  # training centres are not terminals
                office = phone_norm(row[2]) if len(row) > 2 else ""
                places.append(dict(
                    source_key=KEY, source_id=f"brtc-{DIST[nfc(m.group(1))].lower()}-{'depot' if is_depot else 'training'}",
                    name_bn=f"বিআরটিসি {name}", name_en="", category_key="transport.bus_terminal" if is_depot else "transport",
                    district_en=DIST[nfc(m.group(1))], phone=office, operator="বাংলাদেশ সড়ক পরিবহন কর্পোরেশন (বিআরটিসি)", ownership="public",
                    extra_json=xj({"unit_type": "bus depot" if is_depot else "training centre", "office_phone_raw": row[2] if len(row) > 2 else ""}),
                    source_url=URL,
                    notes=("BRTC bus depot (BRTC buses start here) mapped to transport.bus_terminal. " if is_depot else "BRTC training centre, not a terminal. ")
                          + "Name prefixed with 'বিআরটিসি' (source lists it under BRTC depots). Only the office number is kept; the unit head's "
                          "mobile and name are not collected." + (" Office number printed as '০২-০৫১৬৬১৪৫' (02- prefix plus old Bogura code 051); the Bogura district portal "
                          "lists BRTC as 051-66145 (বাসস্ট্যান্ড)." if "০৫১৬৬১৪৫" in row[2] else "")))
    write_csv("places.csv", PLACE_COLS, places)
    write_manifest(dict(
        key=KEY, name="BRTC — bus depots in Rajshahi Division", organization="Bangladesh Road Transport Corporation (BRTC)",
        source_type="government_portal", trust_level=4, urls=[URL], accessed=__import__("datetime").date.today().isoformat(),
        publication_date=None, license=None, license_url=None, attribution="Bangladesh Road Transport Corporation (brtc.gov.bd)",
        notes="No licence stated. BRTC lists depots with the unit head's name/mobile; only depot names and office landlines are kept. "
              "No Rajshahi-district BRTC depot is listed. No addresses or coordinates."),
        ["places.csv"])


if __name__ == "__main__":
    main()
