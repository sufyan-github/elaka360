#!/usr/bin/env python3
"""Collect bus terminals/stands and stations named on a division's district/upazila portal transport pages (default Rajshahi, DISTRICT_PORTALS_TRANSPORT_RAJ_2026).

Usage: python3 fetch.py [--division rangpur] [--out DIR]  (rangpur -> DISTRICT_PORTALS_TRANSPORT_RANG_2026)."""
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

# --- DISTRICT_PORTALS_TRANSPORT_RAJ_2026 --------------------------------------------------------------
KEY = "DISTRICT_PORTALS_TRANSPORT_RAJ_2026"
# No district or upazila portal in Rajshahi Division publishes a bus-terminal register. These rows are terminals / stands /
# stations that the portals' "যোগাযোগ ব্যবস্থা" (how to get here) pages name explicitly. Each entry is kept only if the
# quoted phrase is still on the live page. (page url, phrase on page, name_bn, category, district, upazila, note)
PAGES = {
    "paba": "https://paba.rajshahi.gov.bd/pages/static-pages/697fc1d435ce18e1c06cdf9d",
    "tanore": "https://tanore.rajshahi.gov.bd/pages/static-pages/697f93c835ce18e1c06bed67",
    "durgapur": "https://durgapur.rajshahi.gov.bd/pages/static-pages/697fbb0a35ce18e1c06cba79",
    "bagha": "https://bagha.rajshahi.gov.bd/pages/static-pages/697fdcf435ce18e1c06d91ec",
    "rajshahi": "https://rajshahi.gov.bd/pages/static-pages/697fb32435ce18e1c06ca906",
    "naogaon": "https://naogaon.gov.bd/pages/static-pages/travel-dqg2l3-6ad6d76afd9ba071690f8283",
    "joypurhat": "https://joypurhat.gov.bd/pages/static-pages/697f804235ce18e1c06b7cdf",
    "sirajganj": "https://sirajganj.gov.bd/pages/static-pages/697fbb0e35ce18e1c06cbc46",
    "sirajganj_schedule": "https://sirajganj.gov.bd/pages/static-pages/697ff46435ce18e1c06de89f",
    "bogura": "https://bogura.gov.bd/pages/static-pages/697fbb3f35ce18e1c06cd359",
    "pabna": "https://pabna.gov.bd/pages/static-pages/697fbb1f35ce18e1c06cc403",
    "chapainawabganj": "https://chapainawabganj.gov.bd/pages/static-pages/697f99c635ce18e1c06c093f",
}
ENTRIES = [
    (["paba", "tanore"], "শিরোইল বাস স্ট্যান্ড", "শিরোইল বাস স্ট্যান্ড", "transport.bus_terminal", "Rajshahi", "",
     "Named in the Paba and Tanore upazila portals as the Rajshahi arrival point of Dhaka buses; inside Rajshahi city (no upazila given)."),
    (["durgapur"], "শিবপুরহাট বাসস্ট্যান্ড", "শিবপুরহাট বাসস্ট্যান্ড", "transport.bus_stop", "Rajshahi", "",
     "Named in the Durgapur upazila portal as the stop on the Rajshahi/Chapainawabganj bus route for Durgapur; upazila of the stand not stated."),
    (["durgapur"], "বানেশ্বর বাসস্ট্যান্ড", "বানেশ্বর বাসস্ট্যান্ড", "transport.bus_stop", "Rajshahi", "",
     "Named in the Durgapur upazila portal as an alighting point; upazila of the stand not stated."),
    (["bagha"], "আড়ানীতে একটি রেল ষ্টেশন", "আড়ানী রেল ষ্টেশন", "transport.railway_station", "Rajshahi", "Bagha",
     "Bagha upazila portal: a railway station at Arani, 20 km from the upazila HQ. Name composed from that sentence."),
    (["naogaon"], "ঢাকা বাসস্ট্যান্ড", "ঢাকা বাসস্ট্যান্ড", "transport.bus_terminal", "Naogaon", "",
     "Naogaon district portal: the stand in Naogaon from which Dhaka buses leave."),
    (["naogaon"], "বালুডাঙ্গা বাসস্ট্যান্ড", "বালুডাঙ্গা বাসস্ট্যান্ড", "transport.bus_terminal", "Naogaon", "",
     "Naogaon district portal: the stand in Naogaon from which Rajshahi buses leave every 30 minutes."),
    (["joypurhat"], "জয়পুরহাট কেন্দ্রীয় বাস টার্মিনাল", "জয়পুরহাট কেন্দ্রীয় বাস টার্মিনাল", "transport.bus_terminal", "Joypurhat", "",
     "Joypurhat district portal: main departure point for long-distance and regional buses."),
    (["sirajganj"], "এম এ মতিন পৌর বাস টার্মিনাল", "এম এ মতিন পৌর বাস টার্মিনাল", "transport.bus_terminal", "Sirajganj", "",
     "Sirajganj district portal: one of the 2 bus terminals of Sirajganj town; described as the district's main terminal."),
    (["sirajganj"], "মিরপুর বাস টার্মিনাল", "মিরপুর বাস টার্মিনাল", "transport.bus_terminal", "Sirajganj", "",
     "Sirajganj district portal: one of the 2 bus terminals of Sirajganj town."),
    (["sirajganj_schedule"], "সদানন্দপুর রেল স্টেশন", "সদানন্দপুর রেল স্টেশন", "transport.railway_station", "Sirajganj", "",
     "Sirajganj district portal: 7 km from the district town beside the Dhaka–Bogura highway; intercity, mail and local trains."),
    (["sirajganj_schedule"], "সিরাজগঞ্জ বাজার স্টেশন", "সিরাজগঞ্জ বাজার স্টেশন", "transport.railway_station", "Sirajganj", "",
     "Sirajganj district portal: station in the district town (local train via Ishwardi)."),
]


NOTE_SUFFIX = " Mentioned in travel directions, not a registry entry; no address/coordinates/contact."


def main():
    configure()
    places, facts, text = [], [], {}
    for k, url in PAGES.items():
        r = get(url)
        if r is None or not r.ok or "/pages/static-pages/" not in r.url:
            print("unavailable or redirected:", url)
            continue
        text[k] = "\n".join(content_text(r.text))
        save_raw(f"{k}_transport.txt", text[k])
    for i, (keys, phrase, name, cat, dist, upa, note) in enumerate(ENTRIES, 1):
        hit = [k for k in keys if phrase in text.get(k, "")]
        if not hit:
            print("phrase not found any more:", phrase)
            continue
        places.append(dict(source_key=KEY, source_id=f"dpt-{i:02d}", name_bn=name, name_en="", category_key=cat, district_en=dist,
                           upazila_en=upa, ownership="", extra_json=xj({"phrase_on_page": phrase, "also_on": [PAGES[k] for k in hit[1:]]}),
                           source_url=PAGES[hit[0]], notes=note + NOTE_SUFFIX))
    if "sirajganj" in text and re.search(r"সিরাজগঞ্জ শহরে ০২টি বাস টার্মিনাল", text["sirajganj"]):
        facts.append(dict(entity_level="pourashava", entity_name_en="Sirajganj", district_en="Sirajganj", fact="bus_terminals", value=2,
                          unit="terminals", basis="reported", year="", source_key=KEY, source_url=PAGES["sirajganj"],
                          notes="'সিরাজগঞ্জ শহরে ০২টি বাস টার্মিনাল রয়েছে' (Sirajganj town)"))
    if "rpcc" in text and re.search(r"কোচ/বাস/ট্রাক স্টান্ড[\s|]*৪ টি", text["rpcc"]):
        facts.append(dict(entity_level="city_corporation", entity_name_en="Rangpur City Corporation", district_en="Rangpur",
                          fact="coach_bus_truck_stands", value=4, unit="stands", basis="reported", year="", source_key=KEY,
                          source_url=PAGES["rpcc"], notes="'কোচ/বাস/ট্রাক স্টান্ড ৪ টি': ঢাকা কোচ স্টান্ড, কেন্দ্রীয় বাস টার্মিনাল, "
                                                          "ট্রাক স্টান্ড, পীরগাছা বাস স্টান্ড (RPCC এক নজরে)"))
    if DIVISION != "rajshahi":
        write_csv("places.csv", PLACE_COLS, places)
        write_csv("facts.csv", FACT_COLS, facts)
        write_manifest(MANIFEST, ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))
        return
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    write_manifest(dict(
        key=KEY, division="rajshahi", kind="district_transport", name="District & upazila portals (Rajshahi Division) — bus terminals/stands and stations named on transport pages",
        organization="Deputy Commissioner / Upazila Nirbahi offices (national portal framework)", source_type="government_portal",
        trust_level=4, urls=list(PAGES.values()), accessed=__import__("datetime").date.today().isoformat(), publication_date=None,
        license=None, license_url=None, attribution="District/upazila portals (*.gov.bd, Bangladesh National Portal)",
        notes="No licence stated. No portal publishes a bus-terminal register; these are names explicitly given in 'যোগাযোগ ব্যবস্থা' "
              "pages. Rajshahi district portal names no terminal; Pabna, Bogura and Chapainawabganj pages name only Dhaka-side "
              "terminals or bus companies. raw/ keeps the extracted page text (descriptive text is not copied into the CSVs)."),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


# --- division selection (see ../DIVISIONS.md) --------------------------------------------------------------
# `python3 fetch.py` = `--division rajshahi`, output into this folder (unchanged behaviour). Other divisions write into
# their own folder (default: the sibling folder named per DIVISIONS.md) and never into the Rajshahi folder.
import argparse
DIVISION_CHOICES = ("rajshahi", "rangpur", "dhaka", "chattogram", "khulna", "barishal", "sylhet", "mymensingh")
DIVISION = "rajshahi"


def parse_division_args(folders):
    """Parse --division/--out. folders: division -> default output folder name (a sibling of this folder)."""
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    ap.add_argument("--division", default="rajshahi", choices=DIVISION_CHOICES)
    ap.add_argument("--out", help="output folder (default: this folder for rajshahi, ../<division folder> otherwise)")
    a = ap.parse_args()
    if a.division not in folders:
        raise SystemExit("this collector has no table for division %r yet (see DIVISIONS.md)" % a.division)
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.abspath(a.out or os.path.join(here, "..", folders[a.division]))
    if a.division != "rajshahi" and os.path.realpath(out) == os.path.realpath(here):
        raise SystemExit("refusing to write %s output into the Rajshahi folder %s" % (a.division, here))
    os.makedirs(out, exist_ok=True)
    return a.division, out


def write_division_manifest(out, meta):
    """SOURCE.json for a non-default division run: meta + sha256 of every data file in the output folder."""
    import hashlib as _h, json as _j
    files = {}
    for root, _, names in os.walk(out):
        for n in sorted(names):
            full = os.path.join(root, n)
            rel = os.path.relpath(full, out).replace(os.sep, "/")
            if rel in ("SOURCE.json", "fetch.py", "REPORT.md") or "__pycache__" in rel:
                continue
            files[rel] = _h.sha256(open(full, "rb").read()).hexdigest()
    m = dict(meta)
    m["files"] = dict(sorted(files.items()))
    with open(os.path.join(out, "SOURCE.json"), "w", encoding="utf-8") as f:
        f.write(_j.dumps(m, ensure_ascii=False, indent=2) + "\n")


# --- DISTRICT_PORTALS_TRANSPORT_RANG_2026 (Rangpur Division) ---------------------------------------------------------
RANG_KEY = "DISTRICT_PORTALS_TRANSPORT_RANG_2026"
RANG_PAGES = {
    "rangpur": "https://rangpur.gov.bd/pages/static-pages/6977698ec4774958d7c22b10",
    "panchagarh": "https://panchagarh.gov.bd/pages/static-pages/6977395fc4774958d7c1128c",
    "dinajpur": "https://dinajpur.gov.bd/pages/static-pages/69772ba3c4774958d7c0b6fb",
    "lalmonirhat": "https://lalmonirhat.gov.bd/pages/static-pages/69772b7ec4774958d7c0a564",
    "nilphamari": "https://nilphamari.gov.bd/pages/static-pages/6977240bc4774958d7c08fab",
    "gaibandha": "https://gaibandha.gov.bd/pages/static-pages/69775360c4774958d7c1bbb4",
    "kurigram": "https://kurigram.gov.bd/pages/static-pages/69774bbac4774958d7c15f85",
    "badarganj": "https://badargonj.rangpur.gov.bd/pages/static-pages/69770c53c4774958d7c00afe",
    "gangachara": "https://gangachara.rangpur.gov.bd/pages/static-pages/69773757c4774958d7c0eadc",
    "kaunia": "https://kaunia.rangpur.gov.bd/pages/static-pages/6977374bc4774958d7c0e500",
    "pirganj": "https://pirgonj.rangpur.gov.bd/pages/static-pages/69773dd8c4774958d7c12f41",
    "taraganj": "https://taragonj.rangpur.gov.bd/pages/static-pages/697759f7c4774958d7c1e6fd",
    "rpcc": "https://rpcc.gov.bd/pages/static-pages/6922dd53933eb65569e14850",   # এক নজরে রংপুর সিটি কর্পোরেশন, item ১৩
}
_GB = "Gaibandha district portal 'যোগাযোগ ব্যবস্থা' lists it among 'গাইবান্ধা জেলার রেলস্টেশনগুলি' (a largely historical text; the list may be dated)."
_RS = " Name composed as '<listed name> রেলস্টেশন'."
RANG_ENTRIES = [
    (["panchagarh"], "দিনাজপুর স্টেশনে", "দিনাজপুর স্টেশন", "transport.railway_station", "Dinajpur", "",
     "Panchagarh district portal: Dhaka intercity trains to Dinajpur stop here; travellers to Panchagarh continue by bus. Name as written ('দিনাজপুর স্টেশনে')."),
    (["panchagarh"], "কেন্দ্রিয় বাস টার্মিনালে", "দিনাজপুর কেন্দ্রিয় বাস টার্মিনাল", "transport.bus_terminal", "Dinajpur", "",
     "Panchagarh district portal: reached by rickshaw from Dinajpur station; buses to Panchagarh leave here. 'দিনাজপুর' added from the context."),
    (["lalmonirhat"], "লালমনিরহাট ষ্টেশন", "লালমনিরহাট ষ্টেশন", "transport.railway_station", "Lalmonirhat", "",
     "Lalmonirhat district portal train timetables: departure station of trains to Burimari, Parbatipur/Dinajpur, Santahar and Dhaka."),
    (["lalmonirhat"], "বুড়িমারী", "বুড়িমারী ষ্টেশন", "transport.railway_station", "Lalmonirhat", "",
     "Lalmonirhat district portal train timetables: terminus in the 'গন্তব্য ষ্টেশন' column (Burimari commuter/Karatoya Express). Name composed; upazila not stated."),
] + [(["gaibandha"], ph, nm, "transport.railway_station", "Gaibandha", "", _GB + (_RS if comp else "")) for ph, nm, comp in [
    ("হচ্ছেঃ বামনডাঙ্গা,", "বামনডাঙ্গা রেলস্টেশন", True), ("বামনডাঙ্গা, নলডাঙ্গা,", "নলডাঙ্গা রেলস্টেশন", True),
    ("নলডাঙ্গা, কামারপাড়া,", "কামারপাড়া রেলস্টেশন", True), ("কামারপাড়া, কুপতলা,", "কুপতলা রেলস্টেশন", True),
    ("কুপতলা, গাইবান্ধা,", "গাইবান্ধা রেলস্টেশন", True), ("গাইবান্ধা, ত্রিমোহিনী,", "ত্রিমোহিনী রেলস্টেশন", True),
    ("বালাসীঘাট রেলওয়ে ফেরী স্টেশন", "বালাসীঘাট রেলওয়ে ফেরী স্টেশন", False), ("স্টেশন, বাদিয়াখালী,", "বাদিয়াখালী রেলস্টেশন", True),
    ("বোনারপাড়া জংশন", "বোনারপাড়া জংশন", False), ("জংশন, মহিমাগঞ্জ,", "মহিমাগঞ্জ রেলস্টেশন", True),
    ("মহিমাগঞ্জ, ভরতখালী,", "ভরতখালী রেলস্টেশন", True), ("ভরতখালী, ফুলছড়ি,", "ফুলছড়ি রেলস্টেশন", True),
    ("তিস্তামুখ ঘাট রেলওয়ে স্টেশন", "তিস্তামুখ ঘাট রেলওয়ে স্টেশন", False)]] + [
    (["gangachara"], "কাউনিয়া রেলওয়ে জংশন", "কাউনিয়া রেলওয়ে জংশন", "transport.railway_station", "Rangpur", "",
     "Gangachara upazila portal: nearest station to Gangachara (about 8–10 km); upazila of the station not stated."),
    (["gangachara"], "রংপুর রেলস্টেশন", "রংপুর রেলস্টেশন", "transport.railway_station", "Rangpur", "",
     "Gangachara upazila portal: second-nearest station (about 12 km)."),
    (["badarganj"], "স্টেশন মাস্টার, বদরগঞ্জ", "বদরগঞ্জ রেলস্টেশন", "transport.railway_station", "Rangpur", "Badarganj",
     "Badarganj upazila portal lists the Badarganj station master among its transport contacts; name composed (the number is a malformed mobile and is not copied)."),
    (["rpcc"], "ঢাকা কোচ স্টান্ড", "ঢাকা কোচ স্টান্ড", "transport.bus_terminal", "Rangpur", "",
     "Rangpur City Corporation 'এক নজরে': one of its 4 coach/bus/truck stands (inside the city corporation)."),
    (["rpcc"], "কেন্দ্রীয় বাস টার্মিনাল", "রংপুর কেন্দ্রীয় বাস টার্মিনাল", "transport.bus_terminal", "Rangpur", "",
     "Rangpur City Corporation 'এক নজরে': 'কেন্দ্রীয় বাস টার্মিনাল' (also has an RPCC public toilet and pond); 'রংপুর' added."),
    (["rpcc"], "পীরগাছা বাস স্টান্ড", "পীরগাছা বাস স্টান্ড", "transport.bus_terminal", "Rangpur", "",
     "Rangpur City Corporation 'এক নজরে': one of its 4 coach/bus/truck stands (in Rangpur city, for buses to Pirgachha; not in Pirgachha upazila)."),
]
RANG_MANIFEST = dict(
    key=RANG_KEY, division="rangpur", kind="district_transport",
    name="District & upazila portals (Rangpur Division) — bus terminals/stands and stations named on transport pages",
    organization="Deputy Commissioner / Upazila Nirbahi offices and Rangpur City Corporation (national portal framework)",
    source_type="government_portal", trust_level=4, urls=list(RANG_PAGES.values()), accessed=None, publication_date=None,
    license=None, license_url=None, attribution="District/upazila portals and rpcc.gov.bd (*.gov.bd, Bangladesh National Portal)",
    notes="No licence stated. No portal publishes a bus-terminal register; rows are names explicitly given on 'যোগাযোগ ব্যবস্থা' pages "
          "(district: Panchagarh, Lalmonirhat, Gaibandha; upazila: Badarganj, Gangachara) and in the Rangpur City Corporation "
          "'এক নজরে' page. Rangpur, Dinajpur, Nilphamari and Kurigram district pages and the Kaunia, Pirganj and Taraganj upazila "
          "pages name no terminal or station (only road lengths, timetables or bus companies); Thakurgaon has no such page. raw/ "
          "keeps the extracted page text (descriptive text is not copied into the CSVs).")
SITES = {"rajshahi": dict(folder="district_portals_transport_raj_2026"),
         "rangpur": dict(folder="district_portals_transport_rang_2026", key=RANG_KEY, pages=RANG_PAGES, entries=RANG_ENTRIES,
                         manifest=RANG_MANIFEST, note_suffix=" Named on a portal page, not a registry entry; no address/coordinates/contact.")}
MANIFEST = None


def configure():
    global DIVISION, HERE, RAW, KEY, PAGES, ENTRIES, MANIFEST, NOTE_SUFFIX
    DIVISION, out = parse_division_args({k: v["folder"] for k, v in SITES.items()})
    HERE = Path(out)
    RAW = HERE / "raw"
    if DIVISION != "rajshahi":
        t = SITES[DIVISION]
        KEY, PAGES, ENTRIES, NOTE_SUFFIX = t["key"], t["pages"], t["entries"], t["note_suffix"]
        MANIFEST = dict(t["manifest"], accessed=__import__("datetime").date.today().isoformat())


if __name__ == "__main__":
    main()
