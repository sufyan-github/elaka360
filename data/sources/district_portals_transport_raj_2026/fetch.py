#!/usr/bin/env python3
"""Collect bus terminals/stands and stations named on a division's district/upazila portal transport pages (default Rajshahi, DISTRICT_PORTALS_TRANSPORT_RAJ_2026).

Usage: python3 fetch.py [--division rangpur|dhaka|chattogram|khulna|barishal|sylhet|mymensingh] [--out DIR]  (rangpur ->
DISTRICT_PORTALS_TRANSPORT_RANG_2026, dhaka -> DISTRICT_PORTALS_TRANSPORT_DHK_2026, chattogram -> DISTRICT_PORTALS_TRANSPORT_CTG_2026, khulna ->
DISTRICT_PORTALS_TRANSPORT_KHL_2026, barishal -> DISTRICT_PORTALS_TRANSPORT_BAR_2026, sylhet -> DISTRICT_PORTALS_TRANSPORT_SYL_2026, mymensingh ->
DISTRICT_PORTALS_TRANSPORT_MYM_2026)."""
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
        if DIVISION in ("rajshahi", "rangpur"):
            save_raw(f"{k}_transport.txt", text[k])
    for i, (keys, phrase, name, cat, dist, upa, note) in enumerate(ENTRIES, 1):
        hit = [k for k in keys if phrase in text.get(k, "")]
        if not hit:
            print("phrase not found any more:", phrase)
            continue
        places.append(dict(source_key=KEY, source_id=f"dpt-{i:02d}", name_bn=name, name_en="", category_key=cat, district_en=dist,
                           upazila_en=upa, ownership="", extra_json=xj({"phrase_on_page": phrase, "also_on": [PAGES[k] for k in hit[1:]]}),
                           source_url=PAGES[hit[0]], notes=note + NOTE_SUFFIX))
    if DIVISION not in ("rajshahi", "rangpur"):
        # raw/: only the page lines that carry a matched phrase (some pages also list bus-counter staff and their mobiles)
        used = {}
        for keys, phrase, *_ in ENTRIES:
            for k in keys:
                if phrase in text.get(k, ""):
                    used.setdefault(k, []).append(phrase)
        for k, phrases in sorted(used.items()):
            t = [l for l in text[k].split("\n") if any(ph in l for ph in phrases)]
            t = [re.sub(r"(?<![০-৯0-9])(?:\+?০?৮৮০?-?|\+?0?880?-?)?[০0][১1][৩-৯3-9][০-৯0-9]{2}-?[০-৯0-9]{6}(?![০-৯0-9])", "[mobile redacted]", l) for l in t]
            save_raw(f"{k}_transport.txt", "URL: %s\n\n" % PAGES[k] + "\n".join(dict.fromkeys(re.sub(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", "[e-mail redacted]", l) for l in t)))
    if "sirajganj" in text and re.search(r"সিরাজগঞ্জ শহরে ০২টি বাস টার্মিনাল", text["sirajganj"]):
        facts.append(dict(entity_level="pourashava", entity_name_en="Sirajganj", district_en="Sirajganj", fact="bus_terminals", value=2,
                          unit="terminals", basis="reported", year="", source_key=KEY, source_url=PAGES["sirajganj"],
                          notes="'সিরাজগঞ্জ শহরে ০২টি বাস টার্মিনাল রয়েছে' (Sirajganj town)"))
    if "rpcc" in text and re.search(r"কোচ/বাস/ট্রাক স্টান্ড[\s|]*৪ টি", text["rpcc"]):
        facts.append(dict(entity_level="city_corporation", entity_name_en="Rangpur City Corporation", district_en="Rangpur",
                          fact="coach_bus_truck_stands", value=4, unit="stands", basis="reported", year="", source_key=KEY,
                          source_url=PAGES["rpcc"], notes="'কোচ/বাস/ট্রাক স্টান্ড ৪ টি': ঢাকা কোচ স্টান্ড, কেন্দ্রীয় বাস টার্মিনাল, "
                                                          "ট্রাক স্টান্ড, পীরগাছা বাস স্টান্ড (RPCC এক নজরে)"))
    for k, pat, lvl, ent, dist, fact, unit, note in (SITES[DIVISION].get("facts", []) if DIVISION != "rajshahi" else []):
        m = re.search(pat, text.get(k, ""))
        if m:
            facts.append(dict(entity_level=lvl, entity_name_en=ent, district_en=dist, fact=fact, value=int(m.group(1).translate(_BN)),
                              unit=unit, basis="reported", year="", source_key=KEY, source_url=PAGES[k], notes=note))
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
# --- DISTRICT_PORTALS_TRANSPORT_DHK_2026 (Dhaka Division) ------------------------------------------------------------
DHK_KEY = "DISTRICT_PORTALS_TRANSPORT_DHK_2026"
DHK_PAGES = {
    "dhaka": "https://dhaka.gov.bd/pages/static-pages/communication-system-jah6tq-6a841eae9ab15f91607f8f89",
    "narsingdi": "https://narsingdi.gov.bd/pages/static-pages/6995dfcb35ce18e1c07b1d5b",
    "gazipur": "https://gazipur.gov.bd/pages/static-pages/6995dfc935ce18e1c07b1cb1",
    "shariatpur": "https://shariatpur.gov.bd/pages/static-pages/6995d1c335ce18e1c07a9d82",
    "narayanganj": "https://narayanganj.gov.bd/pages/static-pages/6995976e35ce18e1c0786f39",
    "tangail": "https://tangail.gov.bd/pages/static-pages/6995975d35ce18e1c078687e",
    "kishoreganj": "https://kishoreganj.gov.bd/pages/static-pages/6995c87b35ce18e1c07a36a7",
    "manikganj": "https://manikganj.gov.bd/pages/static-pages/6995b35d35ce18e1c079853a",
    "munshiganj": "https://munshiganj.gov.bd/pages/static-pages/6995d79435ce18e1c07ab01e",
    "rajbari": "https://rajbari.gov.bd/pages/static-pages/6995996b35ce18e1c0787f8d",
    "savar": "https://savar.dhaka.gov.bd/pages/static-pages/6995974835ce18e1c0785f06",
    "dhamrai": "https://dhamrai.dhaka.gov.bd/pages/static-pages/transportation-izf59z-6a20e5cb4bbf12a41ac4f902",
    "keraniganj": "https://keraniganj.dhaka.gov.bd/pages/static-pages/6995beb835ce18e1c079e71d",
    "nawabganj": "https://nawabganj.dhaka.gov.bd/pages/static-pages/6995949835ce18e1c0782c0b",
    "dohar": "https://dohar.dhaka.gov.bd/pages/static-pages/6995949c35ce18e1c0782d82",
    "dscc": "https://dscc.gov.bd/pages/static-pages/6922e0b0933eb65569e28300",   # ঢাকা দক্ষিণ সিটি কর্পোরেশন: বাস টার্মিনাল
    "dncc": "https://dncc.gov.bd/pages/static-pages/6922ded3933eb65569e1da8e",   # ঢাকা উত্তর সিটি কর্পোরেশন: লোকেশন ও আয়তন (ward areas)
}
_NG = ("Narayanganj district portal train timetable (Dhaka–Narayanganj commuter, stops 'ঢাকা | গেন্ডারিয়া | পাগলা | ফতুল্লা | "
       "চাষাড়া | নাঃগঞ্জ'); name composed as '<stop> রেলস্টেশন'.")
DHK_ENTRIES = [
    (["dscc"], "সায়েদাবাদ আন্ত-জেলা বাস টার্মিনাল", "সায়েদাবাদ আন্ত-জেলা বাস টার্মিনাল", "transport.bus_terminal", "Dhaka", "",
     "Dhaka South City Corporation 'বাস টার্মিনাল' page (the only terminal listed). Also named as the Dhaka departure point on the "
     "Narsingdi ('সায়েদাবাদ বাস টার্মিনাল') and Kishoreganj ('সায়েদাবাদ বাসস্ট্যান্ড') pages."),
    (["dncc"], "গাবতলী বাস টার্মিনাল", "গাবতলী বাস টার্মিনাল", "transport.bus_terminal", "Dhaka", "",
     "Dhaka North City Corporation 'লোকেশন ও আয়তন': listed among the areas of DNCC ward 9 (zone 4)."),
    (["tangail"], "মহাখালী বাসস্ট্যান্ড", "মহাখালী বাসস্ট্যান্ড", "transport.bus_terminal", "Dhaka", "",
     "Tangail district portal: Dhaka departure point of buses to Tangail upazilas (Kishoreganj's page calls it 'মহাখালী বাস ডিপো')."),
    (["nawabganj"], "গুলিস্থান বাস স্ট্যান্ডে", "গুলিস্থান বাস স্ট্যান্ড", "transport.bus_stop", "Dhaka", "",
     "Nawabganj (Dhaka) upazila portal: Dhaka end of the Bandura–Gulistan bus (fare given). Name as written ('গুলিস্থান')."),
    (["nawabganj"], "নবাবগঞ্জের বাস স্ট্যান্ডে", "নবাবগঞ্জ বাস স্ট্যান্ড", "transport.bus_stop", "Dhaka", "Nawabganj",
     "Nawabganj (Dhaka) upazila portal: bus stand of Nawabganj reached from Bandura; name composed from 'নবাবগঞ্জের বাস স্ট্যান্ডে'."),
    (["narayanganj"], "কমলাপুর রেল স্টেশন", "কমলাপুর রেল স্টেশন", "transport.railway_station", "Dhaka", "",
     "Narayanganj district portal: trains to Narayanganj leave from Kamalapur station (Narsingdi's page also names 'ঢাকার কমলাপুর স্টেশন')."),
    (["narayanganj"], "ঢাকা | গেন্ডারিয়া | পাগলা", "গেন্ডারিয়া রেলস্টেশন", "transport.railway_station", "Dhaka", "", _NG),
    (["narayanganj"], "গেন্ডারিয়া | পাগলা | ফতুল্লা", "পাগলা রেলস্টেশন", "transport.railway_station", "Narayanganj", "", _NG),
    (["narayanganj"], "পাগলা | ফতুল্লা | চাষাড়া", "ফতুল্লা রেলস্টেশন", "transport.railway_station", "Narayanganj", "", _NG),
    (["narayanganj"], "ফতুল্লা | চাষাড়া | নাঃগঞ্জ", "চাষাড়া রেলস্টেশন", "transport.railway_station", "Narayanganj", "", _NG),
    (["narayanganj"], "চাষাড়া | নাঃগঞ্জ পৌঁছে", "নারায়ণগঞ্জ রেলস্টেশন", "transport.railway_station", "Narayanganj", "",
     _NG + " The terminus is printed 'নাঃগঞ্জ' (abbreviation of নারায়ণগঞ্জ)."),
    (["tangail"], "টাঙ্গাইল নতুন বাসস্ট্যান্ড", "টাঙ্গাইল নতুন বাসস্ট্যান্ড", "transport.bus_terminal", "Tangail", "",
     "Tangail district portal: departure point in Tangail town for buses to the upazilas and Dhaka; the page heading calls it "
     "'নতুন বাস টার্মিনাল'."),
    (["kishoreganj"], "বত্রিশ বাসস্ট্যান্ড", "বত্রিশ বাসস্ট্যান্ড", "transport.bus_terminal", "Kishoreganj", "",
     "Kishoreganj district portal: Kishoreganj departure point of a bus service to Saidabad (Dhaka) ('কিশোগঞ্জের বত্রিশ বাসস্ট্যান্ড')."),
    (["manikganj"], "মানিকগঞ্জ বাসস্ট্যান্ড", "মানিকগঞ্জ বাসস্ট্যান্ড", "transport.bus_terminal", "Manikganj", "",
     "Manikganj district portal bus table: departure point of buses to Gulistan (Dhaka)."),
    (["manikganj"], "পাটুরিয়াঘাট", "পাটুরিয়াঘাট", "transport.launch_ghat", "Manikganj", "",
     "Manikganj district portal bus table: departure point of buses to Gulistan/Gabtoli; a river ghat (ferry), category launch_ghat "
     "is the closest key. Upazila not stated."),
    (["manikganj"], "আরিচাঘাট", "আরিচাঘাট", "transport.launch_ghat", "Manikganj", "",
     "Manikganj district portal bus table: departure point of buses to Gulistan/Gabtoli; a river ghat, category launch_ghat is the "
     "closest key. Upazila not stated."),
    (["shariatpur"], "শরীয়তপুর বাস স্ট্যান্ড", "শরীয়তপুর বাস স্ট্যান্ড", "transport.bus_terminal", "Shariatpur", "",
     "Shariatpur district portal 'যোগাযোগ ব্যবস্থা' (bus timetable)."),
    (["munshiganj"], "ঢাকার সদরঘাট থেকে", "সদরঘাট", "transport.launch_ghat", "Dhaka", "",
     "Munshiganj district portal: launches to Munshiganj leave Dhaka's Sadarghat all day; the Dhaka district page lists Sadarghat "
     "launch routes (সদরঘাট–বরিশাল/চাঁদপুর/ভোলা). Name as written."),
    (["munshiganj"], "কাঠপট্টি, ফতুল্লা প্রভৃতি ঘাটের", "কাঠপট্টি ঘাট", "transport.launch_ghat", "Munshiganj", "",
     "Munshiganj district portal: a launch ghat of the district served from Sadarghat; name composed as '<name> ঘাট'."),
    (["dhaka"], "শাহজালাল আন্তর্জাতিক বিমানবন্দর", "শাহজালাল আন্তর্জাতিক বিমানবন্দর", "transport.airport", "Dhaka", "",
     "Dhaka district portal 'যোগাযোগ ব্যবস্থা' (air routes); about 17–20 km from the city centre per the page."),
]
DHK_MANIFEST = dict(
    key=DHK_KEY, division="dhaka", kind="district_transport",
    name="District & upazila portals (Dhaka Division) — bus terminals/stands, stations and ghats named on transport pages",
    organization="Deputy Commissioner / Upazila Nirbahi offices and Dhaka North/South City Corporations (national portal framework)",
    source_type="government_portal", trust_level=4, urls=list(DHK_PAGES.values()), accessed=None, publication_date=None,
    license=None, license_url=None, attribution="District/upazila portals and dncc.gov.bd / dscc.gov.bd (*.gov.bd, Bangladesh National Portal)",
    notes="No licence stated. No portal publishes a bus-terminal register; rows are names explicitly given on 'যোগাযোগ ব্যবস্থা' pages "
          "(district: Dhaka, Narsingdi, Narayanganj, Tangail, Kishoreganj, Manikganj, Munshiganj, Shariatpur; Dhaka upazilas: "
          "Nawabganj) and on the DSCC 'বাস টার্মিনাল' and DNCC 'লোকেশন ও আয়তন' pages. Gazipur, Rajbari and the Savar, Dhamrai, "
          "Keraniganj and Dohar pages name no terminal or station (only routes, bus companies, owners' mobiles or UNO contacts); "
          "Madaripur's link is a DC contact card; Gopalganj and Faridpur have no such page. raw/ keeps, per page that gave a row, "
          "only the lines carrying the matched phrases (mobiles/e-mails redacted; descriptive text is not copied into the CSVs).")


# --- DISTRICT_PORTALS_TRANSPORT_CTG_2026 (Chattogram Division) -------------------------------------------------------
CTG_KEY = "DISTRICT_PORTALS_TRANSPORT_CTG_2026"
CTG_PAGES = {
    "chattogram": "https://chittagong.gov.bd/pages/static-pages/যোগাযোগ-ব্যবস্থা-603b1f-6991007d35ce18e1c0732d23",
    "feni": "https://feni.gov.bd/pages/static-pages/6990ef0035ce18e1c072ab3f",
    "brahmanbaria": "https://brahmanbaria.gov.bd/pages/static-pages/69912184516a96d4de403199",
    "rangamati": "https://rangamati.gov.bd/pages/static-pages/যোগাযোগ-ব্যবস্থা-26035b-6991008b35ce18e1c0733370",
    "noakhali": "https://noakhali.gov.bd/pages/static-pages/69910abb35ce18e1c0739032",
    "chandpur": "https://chandpur.gov.bd/pages/static-pages/6991384d516a96d4de40c3fd",
    "lakshmipur": "https://lakshmipur.gov.bd/pages/static-pages/699149ce516a96d4de417ccf",
    "coxsbazar": "https://coxsbazar.gov.bd/pages/static-pages/6991176d35ce18e1c073d33d",
    "khagrachhari": "https://khagrachhari.gov.bd/pages/static-pages/699143a5516a96d4de412736",
    "bandarban": "https://bandarban.gov.bd/pages/static-pages/69914377516a96d4de41122d",
}
CTG_ENTRIES = [
    (["chattogram"], "শাহ আমানত আন্তর্জাতিক বিমানবন্দর", "শাহ আমানত আন্তর্জাতিক বিমানবন্দর", "transport.airport", "Chattogram", "",
     "Chattogram district portal 'যোগাযোগ ব্যবস্থা' (air routes): domestic flights to Dhaka, Cox's Bazar, Sylhet, Jashore, Rajshahi, "
     "Saidpur and international flights."),
    (["feni"], "ফেনী রেল স্টেশনে", "ফেনী রেল স্টেশন", "transport.railway_station", "Feni", "",
     "Feni district portal: Dhaka, Chattogram, Chandpur and Sylhet trains arrive at and leave Feni station (timetable on the page)."),
    (["brahmanbaria"], "ব্রাহ্মণবাড়িয়া রেলওয়ে স্টেশন", "ব্রাহ্মণবাড়িয়া রেলওয়ে স্টেশন", "transport.railway_station", "Brahmanbaria", "",
     "Brahmanbaria district portal: the station's timetable and intercity/mail fare tables."),
    (["brahmanbaria"], "কাউতলী/পৈরতলা বাস স্ট্যান্ড", "কাউতলী বাস স্ট্যান্ড", "transport.bus_terminal", "Brahmanbaria", "",
     "Brahmanbaria district portal: stand in Brahmanbaria town ('শহরস্থ') from which buses leave for Kasba, Ashuganj and Bancharampur; "
     "name composed from 'কাউতলী/পৈরতলা বাস স্ট্যান্ড'."),
    (["brahmanbaria"], "কাউতলী/পৈরতলা বাস স্ট্যান্ড", "পৈরতলা বাস স্ট্যান্ড", "transport.bus_terminal", "Brahmanbaria", "",
     "Brahmanbaria district portal: stand in Brahmanbaria town ('শহরস্থ') from which buses leave for Kasba, Ashuganj and Bancharampur; "
     "name composed from 'কাউতলী/পৈরতলা বাস স্ট্যান্ড'."),
    (["brahmanbaria"], "কাউতলী/পৈরতলা/মেড্ডা বাসস্ট্যান্ড", "মেড্ডা বাসস্ট্যান্ড", "transport.bus_terminal", "Brahmanbaria", "",
     "Brahmanbaria district portal: stand in Brahmanbaria town from which buses/tempos leave for Biswaroad; name composed from "
     "'কাউতলী/পৈরতলা/মেড্ডা বাসস্ট্যান্ড'."),
    (["brahmanbaria", "chandpur"], "গোকর্ণ ঘাট হতে লঞ্চযোগে", "গোকর্ণ ঘাট", "transport.launch_ghat", "Brahmanbaria", "",
     "Brahmanbaria district portal: ghat in Brahmanbaria town ('শহরস্থ গোকর্ণ ঘাট') from which launches go to Nabinagar and "
     "Bancharampur. The Chandpur river-port page lists the route 'নবীনগর-গোকর্নঘাট' (spelled 'গোকর্ন')."),
    (["noakhali"], "নোয়াখালী স্টেশনের সময়সূচি", "নোয়াখালী রেলস্টেশন", "transport.railway_station", "Noakhali", "",
     "Noakhali district portal: 'নোয়াখালী স্টেশনের সময়সূচি' (train timetable); name composed as 'নোয়াখালী রেলস্টেশন'."),
    (["chandpur"], "চাঁদপুর লঞ্চ টার্মিনালে", "চাঁদপুর লঞ্চ টার্মিনাল", "transport.launch_ghat", "Chandpur", "",
     "Chandpur district portal (river port section): about 16,46,331 passengers a year use the launch terminal (2010-2011 figure "
     "as printed); category launch_ghat."),
    (["lakshmipur"], "লক্ষ্মীপুর বাস টার্মিনাল", "লক্ষ্মীপুর বাস টার্মিনাল", "transport.bus_terminal", "Lakshmipur", "",
     "Lakshmipur district portal bus tables: departure point of the Dhaka bus services (spelled 'লক্ষ্মীপর' once on the page)."),
    (["lakshmipur"], "মজু চৌধুরী ঘাট হতে যাত্রার সময়", "মজু চৌধুরী ঘাট", "transport.launch_ghat", "Lakshmipur", "",
     "Lakshmipur district portal: ghat of the launches/ferries to Ilisha (Bhola) and Barishal. The page also places "
     "'মজু চৌধুরীর হাট' in Lakshmipur Sadar ('লক্ষ্মীপুর সদরস্থ'); upazila not set because the ghat itself is not placed."),
    (["lakshmipur"], "অলংকার বাস স্ট্যান্ড", "অলংকার বাস স্ট্যান্ড", "transport.bus_stop", "Chattogram", "",
     "Lakshmipur district portal bus table: the Chattogram stand of buses to Lakshmipur (Alankar, Chattogram city); district from "
     "the table's Chattogram row."),
    (["bandarban"], "বান্দরবান বাস স্টেশন", "বান্দরবান বাস স্টেশন", "transport.bus_terminal", "Bandarban", "",
     "Bandarban district portal: the counters of the Dhaka/Chattogram bus services are at Bandarban bus station."),
]
CTG_MANIFEST = dict(
    key=CTG_KEY, division="chattogram", kind="district_transport",
    name="District portals (Chattogram Division) — bus terminals/stands, stations, ghats and airport named on transport pages",
    organization="Deputy Commissioner's offices (national portal framework)", source_type="government_portal", trust_level=4,
    urls=list(CTG_PAGES.values()), accessed=None, publication_date=None, license=None, license_url=None,
    attribution="District portals (*.gov.bd, Bangladesh National Portal)",
    notes="No licence stated. No portal publishes a bus-terminal register; rows are names explicitly given on the district "
          "'যোগাযোগ ব্যবস্থা' pages (Chattogram, Feni, Brahmanbaria, Noakhali, Chandpur, Lakshmipur, Bandarban). Rangamati, Cox's "
          "Bazar and Khagrachhari pages name no terminal or station (routes, distances, bus companies and counter mobiles); Cumilla's "
          "portal has no such page; the divisional portal's general page is not used. raw/ keeps, per page that gave a row, only the "
          "lines carrying the matched phrases (mobiles/e-mails redacted; descriptive text is not copied into the CSVs).")
# --- DISTRICT_PORTALS_TRANSPORT_KHL_2026 (Khulna Division) ---------------------------------------------------------------
KHL_KEY = "DISTRICT_PORTALS_TRANSPORT_KHL_2026"
KHL_PAGES = {   # the 'যোগাযোগ ব্যবস্থা' pages linked from the DC portals' menus (Narail and Magura link none)
    "khulna": "https://khulna.gov.bd/pages/static-pages/69812047a31054345f1e0ba0",
    "jashore": "https://jessore.gov.bd/pages/static-pages/6981417735ce18e1c0701fd1",
    "satkhira": "https://satkhira.gov.bd/pages/static-pages/69811b2ea31054345f1df271",
    "meherpur": "https://meherpur.gov.bd/pages/static-pages/6981333735ce18e1c06faf3a",
    "chuadanga": "https://chuadanga.gov.bd/pages/static-pages/6980fbffa31054345f1d25e7",
    "kushtia": "https://kushtia.gov.bd/pages/static-pages/6980f6bba31054345f1d05c5",
    "bagerhat": "https://bagerhat.gov.bd/pages/static-pages/6981333935ce18e1c06fb049",
    "jhenaidah": "https://jhenaidah.gov.bd/pages/static-pages/69812dec35ce18e1c06f997c",
}
KHL_ENTRIES = [
    (["jashore"], "এই যশোর বিমানবন্দর", "যশোর বিমানবন্দর", "transport.airport", "Jashore", "",
     "Jashore district portal 'যোগাযোগ ব্যবস্থা' (বিমানবন্দর): the airport stands in the district town beside Jashore Cantonment and "
     "serves the Jashore-Dhaka route for passengers from Khulna and nearby districts; upazila not set (the page says 'জেলা সদরে'). "
     "The Kushtia and Jhenaidah pages also name it ('যশোর বিমান বন্দর') as the nearest airport for flights from Dhaka."),
    (["satkhira"], "সাতক্ষীরা কেন্দ্রীয় বাস টার্মিনাল", "সাতক্ষীরা কেন্দ্রীয় বাস টার্মিনাল", "transport.bus_terminal", "Satkhira", "",
     "Satkhira district portal 'যোগাযোগ': the central bus terminal from which the DC office is reached by van or rickshaw."),
]
KHL_MANIFEST = dict(
    key=KHL_KEY, division="khulna", kind="district_transport",
    name="District portals (Khulna Division) — bus terminals and airport named on transport pages",
    organization="Deputy Commissioner's offices (national portal framework)", source_type="government_portal", trust_level=4,
    urls=list(KHL_PAGES.values()), accessed=None, publication_date=None, license=None, license_url=None,
    attribution="District portals (*.gov.bd, Bangladesh National Portal)",
    notes="No licence stated. No portal publishes a terminal register; rows are names explicitly given on the district 'যোগাযোগ "
          "ব্যবস্থা' pages (Jashore airport; Satkhira central bus terminal). Khulna names only ticket counters' areas and train names; "
          "Meherpur, Chuadanga, Bagerhat and Jhenaidah list bus companies, timetables and counter numbers but no terminal or station by "
          "name (Chuadanga's train table says only 'From Chuadanga'); Kushtia and Jhenaidah name only Jashore airport; Narail and Magura link no transport page. raw/ keeps, per page that "
          "gave a row, only the lines carrying the matched phrases (mobiles/e-mails redacted; descriptive text is not copied into the CSVs).")
# --- DISTRICT_PORTALS_TRANSPORT_BAR_2026 (Barishal Division) -------------------------------------------------------------
BAR_KEY = "DISTRICT_PORTALS_TRANSPORT_BAR_2026"
BAR_PAGES = {   # the 'যোগাযোগ ব্যবস্থা' pages linked from the DC portals' menus (Barguna links none) and, for launch ghats and stands, the
                # upazila portals' 'যোগাযোগ' pages that name one
    "barishal": "https://barisal.gov.bd/pages/static-pages/6978a33735ce18e1c0672d0c",
    "jhalokathi": "https://jhalakathi.gov.bd/pages/static-pages/6978a31b35ce18e1c0671f5f",
    "patuakhali": "https://patuakhali.gov.bd/pages/static-pages/697894ab35ce18e1c0668dbc",
    "pirojpur": "https://pirojpur.gov.bd/pages/static-pages/697887bd35ce18e1c0662d6f",
    "bhola": "https://bhola.gov.bd/pages/static-pages/যোগাযোগ-ব্যবস্থা-53183e-69789aa335ce18e1c066baed",
    "bakerganj": "https://bakerganj.barisal.gov.bd/pages/static-pages/6978a32835ce18e1c06725a1",
    "banaripara": "https://banaripara.barisal.gov.bd/pages/static-pages/69789ae635ce18e1c066db96",
    "gaurnadi": "https://gournadi.barisal.gov.bd/pages/static-pages/69788e5235ce18e1c06662f0",
    "agailjhara": "https://agailjhara.barisal.gov.bd/pages/static-pages/69789b6f35ce18e1c066e1dd",
    "kathalia": "https://kathalia.jhalakathi.gov.bd/pages/static-pages/6978a32035ce18e1c0672195",
    "bauphal": "https://bauphal.patuakhali.gov.bd/pages/static-pages/6978947635ce18e1c066762c",
    "bhandaria": "https://bhandaria.pirojpur.gov.bd/pages/static-pages/69788e4c35ce18e1c0666000",
    "bholasadar": "https://sadar.bhola.gov.bd/pages/static-pages/69788e2835ce18e1c0664edc",
    "tazumuddin": "https://tazumuddin.bhola.gov.bd/pages/static-pages/69787674c4774958d7c420ad",
}
BAR_ENTRIES = [
    (["barishal"], "নথুল্লাবাদ বাসস্ট্যান্ড", "নথুল্লাবাদ বাসস্ট্যান্ড", "transport.bus_terminal", "Barishal", "",
     "Barishal district portal 'যোগাযোগ ব্যবস্থা': the Barishal arrival point of the Dhaka (Gabtali) buses ('নথুল্লাবাদ বাসস্ট্যান্ড, বরিশাল'); upazila not stated."),
    (["bakerganj"], "বাস স্টেশন (রূপাতলী, বরিশাল)", "রূপাতলী বাস স্টেশন", "transport.bus_terminal", "Barishal", "",
     "Bakerganj upazila portal 'যোগাযোগ': the Barishal bus station at Rupatali from which buses run on the Barishal-Patuakhali highway; "
     "name composed from 'বাস স্টেশন (রূপাতলী, বরিশাল)'; upazila not stated."),
    (["bakerganj"], "বাকেরগঞ্জ বাসষ্ট্যান্ড", "বাকেরগঞ্জ বাসষ্ট্যান্ড", "transport.bus_stop", "Barishal", "Bakerganj",
     "Bakerganj upazila portal 'যোগাযোগ': the stand where the Barishal buses stop, 20 km from Barishal, from which the upazila parishad is reached."),
    (["banaripara"], "বানারীপাড়া বাস স্ট্যান্ড", "বানারীপাড়া বাস স্ট্যান্ড", "transport.bus_terminal", "Barishal", "Banaripara",
     "Banaripara upazila portal 'যোগাযোগ ব্যবস্থা': the stand where the Dhaka buses arrive."),
    (["gaurnadi", "agailjhara"], "গৌরনদী বাসস্ট্যান্ড", "গৌরনদী বাসস্ট্যান্ড", "transport.bus_terminal", "Barishal", "Gaurnadi",
     "Gaurnadi upazila portal 'যোগাযোগ ব্যবস্থা' (also Agailjhara's): arrival point of the Dhaka buses ('গৌরনদী বাসস্ট্যান্ড, বরিশাল')."),
    (["barishal"], "বরিশাল বিমানবন্দর", "বরিশাল বিমানবন্দর", "transport.airport", "Barishal", "",
     "Barishal district portal 'যোগাযোগ ব্যবস্থা' (flight tables: 'হযরত শাহজালাল আন্তর্জাতিক বিমানবন্দর, ঢাকা ও বরিশাল বিমানবন্দর'); upazila not stated."),
    (["bholasadar"], "বরিশাল লঞ্চঘাট", "বরিশাল লঞ্চঘাট", "transport.launch_ghat", "Barishal", "",
     "Bhola Sadar upazila portal 'যোগাযোগ': launches to Bhola leave from Barishal launch ghat (via Bheduria). The Gaurnadi page names the "
     "arrival point of the Dhaka launches as 'লঞ্চঘাট, বরিশাল'. Upazila not stated."),
    (["kathalia"], "আমুয়া নদী বন্দর", "আমুয়া নদী বন্দর", "transport.launch_ghat", "Jhalokathi", "Kathalia",
     "Kathalia upazila portal 'যোগাযোগ ব্যবস্থা': river port at Amua with the Amua-Barishal-Dhaka launches; boats from Amua reach "
     "Patikelghata union. Upazila from the page (Amua is one of Kathalia's unions in the same page's table)."),
    (["bauphal"], "বগা লঞ্চঘাট", "বগা লঞ্চঘাট", "transport.launch_ghat", "Patuakhali", "",
     "Bauphal upazila portal 'যোগাযোগ ব্যবস্থা': launch ghat on the Dhaka-Patuakhali route from which Bauphal upazila HQ is reached by road; "
     "the page does not say in which upazila the ghat lies."),
    (["pirojpur", "bhandaria"], "হুলারহাট লঞ্চ ঘাট", "হুলারহাট লঞ্চ ঘাট", "transport.launch_ghat", "Pirojpur", "",
     "Pirojpur district portal 'যোগাযোগ ব্যবস্থা' (also Bhandaria's): 11 launches run from 'পিরোজপুর- হুলারহাট লঞ্চ ঘাট' to Dhaka "
     "Sadarghat; 7 small launches serve internal routes from Hularhat, and the rocket/steamer to Dhaka and to Khulna/Morrelganj leaves "
     "from Hularhat. Upazila not stated."),
    (["bhola"], "ভোলা খেয়াঘাট", "ভোলা খেয়াঘাট", "transport.launch_ghat", "Bhola", "",
     "Bhola district portal 'যোগাযোগ ব্যবস্থা': heading 'ভোলা খেয়াঘাট- ঢাকা' of one of the five Bhola-Dhaka launch tables (the other "
     "headings name routes only: ইলিশা-ঢাকা, লালমোহন-ঢাকা, বেতুয়া-ঢাকা, হাতিয়া-মনপুরা-ইলিশা-ঢাকা). Upazila not stated."),
    (["bholasadar"], "ভেদুরিয়া লঞ্চঘাট", "ভেদুরিয়া লঞ্চঘাট", "transport.launch_ghat", "Bhola", "",
     "Bhola Sadar upazila portal 'যোগাযোগ': the Barishal launches reach Bhola town via Bheduria launch ghat; upazila not stated."),
    (["tazumuddin"], "ভোলা লঞ্চ ঘাট", "ভোলা লঞ্চ ঘাট", "transport.launch_ghat", "Bhola", "",
     "Tazumuddin upazila portal 'যোগাযোগ': the Dhaka launches arrive at 'ভোলা লঞ্চ ঘাট' (possibly the same ghat as another Bhola row); "
     "upazila not stated."),
    (["tazumuddin"], "ভোলা লঞ্চ ঘাট থেকে কেন্দ্রিয় বাস ষ্টেশন", "ভোলা কেন্দ্রিয় বাস ষ্টেশন", "transport.bus_terminal", "Bhola", "",
     "Tazumuddin upazila portal 'যোগাযোগ': the central bus station reached from the Bhola launch ghat, where the Char Fasson buses leave; "
     "name composed ('ভোলা' added; spelling as printed)."),
    (["tazumuddin"], "তজুমদ্দিন টেম্পু ষ্টেশন", "তজুমদ্দিন টেম্পু ষ্টেশন", "transport", "Bhola", "Tazumuddin",
     "Tazumuddin upazila portal 'যোগাযোগ': tempo stand from which the upazila office is reached by rickshaw."),
]
BAR_FACTS = [   # (page key, regex on the page text, entity_level, entity_name_en, district, fact, unit, note)
    ("barishal", r"বরিশাল-ঢাকা-বরিশাল\s*\(([০-৯0-9]+)টি নৌ-যান\)", "district", "Barishal", "Barishal", "dhaka_launch_route_vessels", "vessels",
     "Barishal district portal launch table 'বরিশাল-ঢাকা-বরিশাল (২২টি নৌ-যান)' (vessels on the Barishal-Dhaka route)"),
    ("pirojpur", r"হুলারহাট লঞ্চ ঘাট থেকে ঢাকা-সদরঘাট পর্যন্ত\s*([০-৯0-9]+)\s*টি লঞ্চ", "district", "Pirojpur", "Pirojpur",
     "dhaka_launch_route_vessels", "launches", "Pirojpur district portal: launches from Hularhat launch ghat to Dhaka Sadarghat"),
]
BAR_MANIFEST = dict(
    key=BAR_KEY, division="barishal", kind="district_transport",
    name="District and upazila portals (Barishal Division) — launch ghats, bus stands and airport named on transport pages",
    organization="Deputy Commissioner / Upazila Nirbahi offices (national portal framework)", source_type="government_portal", trust_level=4,
    urls=list(BAR_PAGES.values()), accessed=None, publication_date=None, license=None, license_url=None,
    attribution="District and upazila portals (*.gov.bd, Bangladesh National Portal)",
    notes="No licence stated. No portal publishes a terminal or ghat register; rows are names explicitly given on the district 'যোগাযোগ "
          "ব্যবস্থা' pages (Barishal, Jhalokathi, Patuakhali, Pirojpur, Bhola; Barguna links none) and on the 'যোগাযোগ' pages of the "
          "division's 42 upazila portals that name a ghat or stand. Route headings that name no ghat (e.g. 'ইলিশা-ঢাকা নৌ-পথ'), "
          "Dhaka-side terminals (Sadarghat, Gabtali, Sayedabad) and launch/bus company counters are not rows. raw/ keeps, per page that "
          "gave a row, only the lines carrying the matched phrases (mobiles/e-mails redacted; descriptive text is not copied into the CSVs).")
# --- DISTRICT_PORTALS_TRANSPORT_SYL_2026 (Sylhet Division) -------------------------------------------------------------
SYL_KEY = "DISTRICT_PORTALS_TRANSPORT_SYL_2026"
SYL_PAGES = {   # the 'যোগাযোগ ব্যবস্থা' / 'যাতায়াত ব্যবস্থা' / 'যোগাযোগ' pages of the DC and upazila portals that name a terminal, station or
                # ghat (the Sylhet DC portal links no transport page; its 'এক নজরে' gives the district's railway-station count)
    "sylhetsadar": "https://sylhetsadar.sylhet.gov.bd/pages/static-pages/696cb360c4774958d7ba05b3",
    "beanibazar": "https://beanibazar.sylhet.gov.bd/pages/static-pages/696cb399c4774958d7ba1db2",
    "bishwanath": "https://bishwanath.sylhet.gov.bd/pages/static-pages/696cafa3c4774958d7b9dccb",
    "fenchuganj": "https://fenchuganj.sylhet.gov.bd/pages/static-pages/696cb9bac4774958d7ba95fe",
    "zakiganj": "https://zakiganj.sylhet.gov.bd/pages/static-pages/696cb3f2c4774958d7ba2449",
    "dakshinsurma": "https://dakshinsurma.sylhet.gov.bd/pages/static-pages/696cafc6c4774958d7b9ecc5",
    "moulvibazar": "https://moulvibazar.gov.bd/pages/static-pages/696cb3a2c4774958d7ba21fa",
    "juri": "https://juri.moulvibazar.gov.bd/pages/static-pages/696cb389c4774958d7ba1697",
    "habiganj": "https://habiganj.gov.bd/pages/static-pages/696cb96bc4774958d7ba7341",
    "shayestaganj": "https://shayestaganj.habiganj.gov.bd/pages/static-pages/696cafe1c4774958d7b9f8b5",
    "chhatak": "https://chhatak.sunamganj.gov.bd/pages/static-pages/696cb971c4774958d7ba75ee",
    "derai": "https://derai.sunamganj.gov.bd/pages/static-pages/696cb3f4c4774958d7ba258f",
    "dowarabazar": "https://dowarabazar.sunamganj.gov.bd/pages/static-pages/696ca787c4774958d7b99779",
    "shalla": "https://shalla.sunamganj.gov.bd/pages/static-pages/696cb98cc4774958d7ba81cf",
    "sylhet_glance": "https://sylhet.gov.bd/pages/static-pages/696cb362c4774958d7ba0691",
}
SYL_ENTRIES = [
    (["bishwanath", "dakshinsurma", "sylhetsadar", "zakiganj", "derai", "habiganj"], "কদমতলী বাস", "কদমতলী বাস টার্মিনাল",
     "transport.bus_terminal", "Sylhet", "",
     "Name as on the Bishwanath and Dakshin Surma upazila portals ('কদমতলী বাস টার্মিনাল'; Bishwanath: beside Sylhet railway station); "
     "the Sylhet Sadar page lists the Dhaka bus companies' counters at 'কদমতলী বাসস্টান্ড', Zakiganj and Derai say 'কদমতলী বাসষ্ট্যান্ড', "
     "the Habiganj DC page 'সিলেটের কদমতলী বাস স্টেশন'. Upazila not stated."),
    (["bishwanath", "dakshinsurma"], "সিলেট রেল", "সিলেট রেলওয়ে স্টেশন", "transport.railway_station", "Sylhet", "",
     "Bishwanath upazila portal ('সিলেট রেল ষ্টেশনের পার্শ্বে কদমতলী বাস টার্মিনাল') and Dakshin Surma's ('সিলেট রেলওয়ে স্ট্রেশন', "
     "'সিলেট রেল স্টেশন'); name normalised to 'সিলেট রেলওয়ে স্টেশন'. Upazila not stated."),
    (["sylhetsadar"], "এম এ জি ওসমাণী", "এম এ জি ওসমাণী আন্তর্জাতিক বিমানবন্দর", "transport.airport", "Sylhet", "Sylhet Sadar",
     "Sylhet Sadar upazila portal: 'সিলেট এম এ জি ওসমাণী একটি আর্ন্তজাতিক মানের বিমানবন্দর' with domestic and international services; "
     "the same page places the division's only airport in Khadimnagar union of the upazila (calling it 'হযরত শাহাজালাল আন্তর্জাতিক "
     "বিমানবন্দর', the name of Dhaka's airport). Name composed. Also in the CAAB source."),
    (["bishwanath"], "খাজাঞ্চী ইউনিয়নে রেলস্টেশন", "খাজাঞ্চী রেলস্টেশন", "transport.railway_station", "Sylhet", "Bishwanath",
     "Bishwanath upazila portal: Bishwanath's only railway station is in Khajanchi union, on the Sylhet-Chhatak line. Name composed from "
     "that sentence."),
    (["fenchuganj"], "ফেঞ্চুগঞ্জ ষ্টেশন", "ফেঞ্চুগঞ্জ ষ্টেশন", "transport.railway_station", "Sylhet", "",
     "Fenchuganj upazila portal: by rail from Sylhet station via 'ফেঞ্চুগঞ্জ ষ্টেশন' and 'মাইজগাও ষ্টেশন' to the upazila. Upazila of the "
     "station not stated."),
    (["fenchuganj"], "মাইজগাও ষ্টেশন", "মাইজগাও ষ্টেশন", "transport.railway_station", "Sylhet", "",
     "Fenchuganj upazila portal (see 'ফেঞ্চুগঞ্জ ষ্টেশন'). Upazila of the station not stated."),
    (["beanibazar"], "বিয়ানীবাজার বাসস্ট্যান্ড", "বিয়ানীবাজার বাসস্ট্যান্ড", "transport.bus_terminal", "Sylhet", "Beanibazar",
     "Beanibazar upazila portal 'যোগাযোগ': the upazila parishad gate is 200 yards west of the Beanibazar bus stand."),
    (["moulvibazar"], "স্টেশন মাষ্টার, শ্রীমঙ্গল", "শ্রীমঙ্গল রেলস্টেশন", "transport.railway_station", "Moulvibazar", "Sreemangal",
     "Moulvibazar district portal 'যাতায়াত ব্যবস্থা': from Dhaka by rail to Sreemangal, then by road; the train table cites 'স্টেশন "
     "মাষ্টার, শ্রীমঙ্গল'. Name composed."),
    (["juri"], "কুলাউড়া ষ্টেশন", "কুলাউড়া ষ্টেশন", "transport.railway_station", "Moulvibazar", "",
     "Juri upazila portal: Dhaka and Chattogram trains to 'কুলাউড়া ষ্টেশন', then by bus to Juri. Upazila of the station not stated."),
    (["shayestaganj"], "শায়েস্তাগঞ্জ স্টেশন", "শায়েস্তাগঞ্জ রেলস্টেশন", "transport.railway_station", "Habiganj", "Shayestaganj",
     "Shayestaganj upazila portal: 'শায়েস্তাগঞ্জ স্টেশন', one of the main railway entry points of Sylhet Division on the Dhaka-Sylhet and "
     "Chattogram-Sylhet line through the town; the Nabiganj portal also names 'শায়েস্তাগঞ্জ রেলস্টেশন' (name as there)."),
    (["chhatak"], "ছাতক উপজেলায় রেল স্টেশন", "ছাতক রেলস্টেশন", "transport.railway_station", "Sunamganj", "Chhatak",
     "Chhatak upazila portal 'যোগাযোগ': the upazila parishad is a little east of the railway station of Chhatak upazila. Name composed."),
    (["dowarabazar"], "ছাতক ফেরী ঘাট", "ছাতক ফেরী ঘাট", "transport.launch_ghat", "Sunamganj", "",
     "Dowarabazar upazila portal 'যোগাযোগ ব্যবস্থা': Dowarabazar is reached from Chhatak by ferry and then 12 km by road. Upazila not stated."),
    (["dowarabazar"], "আজমপুর/দোহালিয়া নৌকাঘাট", "আজমপুর নৌকাঘাট", "transport.launch_ghat", "Sunamganj", "",
     "Dowarabazar upazila portal: from Sunamganj by launch/trawler or road to 'আজমপুর/দোহালিয়া নৌকাঘাট', then by boat to the upazila. "
     "Name composed (two boat ghats in one phrase). Upazila not stated."),
    (["dowarabazar"], "আজমপুর/দোহালিয়া নৌকাঘাট", "দোহালিয়া নৌকাঘাট", "transport.launch_ghat", "Sunamganj", "",
     "Dowarabazar upazila portal (see 'আজমপুর নৌকাঘাট'). Name composed. Upazila not stated."),
    (["shalla"], "দিরাই বাসস্ট্যান্ড", "দিরাই বাসস্ট্যান্ড", "transport.bus_terminal", "Sunamganj", "",
     "Shalla upazila portal 'যোগাযোগ ব্যবস্থা': Shalla is reached from the Derai bus stand by motorcycle, leguna or CNG. Upazila not stated."),
    (["shalla"], "নেয়ামতপুর নৌকাঘাট", "নেয়ামতপুর নৌকাঘাট", "transport.launch_ghat", "Sunamganj", "",
     "Shalla upazila portal: a boat crossing on the Derai-Shalla route ('নেয়ামতপুর নৌকাঘাট পার হয়ে'). Upazila not stated."),
]
SYL_FACTS = [   # (page key, regex on the page text, entity_level, entity_name_en, district, fact, unit, note)
    ("sylhet_glance", r"রেল স্টেশন\s*\|\s*([০-৯0-9]+)\s*টি", "district", "Sylhet", "Sylhet", "railway_stations", "stations",
     "Sylhet DC portal 'এক নজরে সিলেট জেলা': 'রেল স্টেশন ০৬ টি' (stations not named)"),
]
SYL_MANIFEST = dict(
    key=SYL_KEY, division="sylhet", kind="district_transport",
    name="District and upazila portals (Sylhet Division) — bus terminals, railway stations, ghats and airport named on transport pages",
    organization="Deputy Commissioner / Upazila Nirbahi offices (national portal framework)", source_type="government_portal", trust_level=4,
    urls=list(SYL_PAGES.values()), accessed=None, publication_date=None, license=None, license_url=None,
    attribution="District and upazila portals (*.gov.bd, Bangladesh National Portal)",
    notes="No licence stated. No portal publishes a terminal, station or ghat register; rows are names explicitly given on the 'যোগাযোগ "
          "ব্যবস্থা' / 'যাতায়াত ব্যবস্থা' / 'যোগাযোগ' pages of the Moulvibazar and Habiganj DC portals and of the upazila portals that name "
          "one (the Sylhet and Sunamganj DC portals name none; Sylhet links no such page). Dhaka-side terminals (Sayedabad, Mohakhali, "
          "Kamalapur), bus company counters (Sobhanighat, Humayun Chattar) and route descriptions without a named stop are not rows. "
          "raw/ keeps, per page that gave a row, only the lines carrying the matched phrases (mobiles/e-mails redacted; descriptive text "
          "is not copied into the CSVs). sylhet.gov.bd sends only its leaf certificate: the Let's Encrypt intermediates are added from the "
          "CA's AIA URLs, TLS verification stays on.")
SYL_INTERMEDIATES = ["http://yr1.i.lencr.org/", "http://yr.i.lencr.org/"]
# --- DISTRICT_PORTALS_TRANSPORT_MYM_2026 (Mymensingh Division) ---------------------------------------------------------
MYM_KEY = "DISTRICT_PORTALS_TRANSPORT_MYM_2026"
MYM_PAGES = {   # the 'যোগাযোগ ব্যবস্থা' / 'যোগাযোগ' pages of the DC and upazila portals that name a terminal, station or stand (all 4 DC and
                # 35 upazila portals were scanned; the Sherpur and Netrokona DC pages and most upazila pages name none)
    "jamalpur": "https://jamalpur.gov.bd/pages/static-pages/6970926ca31054345f15e8e6",
    "fulbaria": "https://fulbaria.mymensingh.gov.bd/pages/static-pages/69709db9a31054345f1606f4",
    "muktagacha": "https://muktagacha.mymensingh.gov.bd/pages/static-pages/69709db9a31054345f160730",
    "iswarganj": "https://iswarganj.mymensingh.gov.bd/pages/static-pages/6970764da31054345f1517e1",
    "phulpur": "https://phulpur.mymensingh.gov.bd/pages/static-pages/69707667a31054345f152420",
    "tarakanda": "https://tarakanda.mymensingh.gov.bd/pages/static-pages/6970764da31054345f151798",
    "dewangonj": "https://dewangonj.jamalpur.gov.bd/pages/static-pages/6970764fa31054345f151844",
    "bokshiganj": "https://bokshiganj.jamalpur.gov.bd/pages/static-pages/6973bc83c4774958d7bbf3a3",
    "nalitabari": "https://nalitabari.sherpur.gov.bd/pages/static-pages/6970816ba31054345f1545a7",
    "mcc_bus": "https://mcc.gov.bd/pages/static-pages/6922dc66933eb65569e1024c",   # Mymensingh City Corporation 'বাস টার্মিনাল'
}
MYM_ENTRIES = [
    (["fulbaria"], "ময়মনসিং রেলওয়ে জংসন", "ময়মনসিংহ রেলওয়ে জংশন", "transport.railway_station", "Mymensingh", "",
     "Fulbaria upazila portal 'যোগাযোগ': by rail from Kamalapur to 'ময়মনসিং রেলওয়ে জংসন', then by road; the Muktagacha portal says "
     "'ময়মনসিংহ স্টেশন'. Name normalised. Upazila not stated."),
    (["bokshiganj"], "জামালপুর রেল স্টেশন", "জামালপুর রেল স্টেশন", "transport.railway_station", "Jamalpur", "",
     "Bokshiganj upazila portal: intercity trains from Dhaka to 'জামালপুর রেল স্টেশন', then by road; the Jamalpur DC portal's timetable "
     "lists the station as 'জামালপুর জং' (its station-master and GRP thana numbers are not copied). Upazila not stated."),
    (["jamalpur"], "(বিশ্ব রোড়)", "বাসটার্মিনাল (বিশ্ব রোড়), জামালপুর", "transport.bus_terminal", "Jamalpur", "",
     "Jamalpur DC portal 'যোগাযোগ ব্যবস্থা': bus table, departure place 'বাসটার্মিনাল (বিশ্ব রোড়)' (Dhaka-bound buses). Name composed "
     "(', জামালপুর' added). Upazila not stated."),
    (["jamalpur"], "(ছনকান্দা)", "বাসটার্মিনাল (ছনকান্দা), জামালপুর", "transport.bus_terminal", "Jamalpur", "",
     "Jamalpur DC portal 'যোগাযোগ ব্যবস্থা': bus table, departure place 'বাসটার্মিনাল (ছনকান্দা)' (Dhaka-bound buses). Name composed "
     "(', জামালপুর' added). Upazila not stated."),
    (["dewangonj"], "দেওয়ানগঞ্জ রেলওয়ে স্টেশন", "দেওয়ানগঞ্জ রেলওয়ে স্টেশন", "transport.railway_station", "Jamalpur", "Dewangonj",
     "Dewangonj upazila portal 'যোগাযোগ ব্যবস্থা': departure place of the intercity, commuter and local trains from the upazila."),
    (["dewangonj"], "দেওয়ানগঞ্জ বাস স্যান্ড", "দেওয়ানগঞ্জ বাসস্ট্যান্ড", "transport.bus_terminal", "Jamalpur", "Dewangonj",
     "Dewangonj upazila portal: departure place of the buses from the upazila to Jamalpur, printed 'দেওয়ানগঞ্জ বাস স্যান্ড'. Name "
     "normalised."),
    (["mcc_bus", "iswarganj"], "মাসকান্দা", "মাসকান্দা আন্তঃজেলা বাস টার্মিনাল", "transport.bus_terminal", "Mymensingh", "",
     "Mymensingh City Corporation 'বাস টার্মিনাল' page: 'মাসকান্দা আন্তঃজেলা বাসর্টামিনাল' (name normalised from the printed "
     "'বাসর্টামিনাল'); the Iswarganj upazila portal calls it 'মাসকান্দা বাসস্টান্ড' (buses towards Kishoreganj and Bhairab) and the "
     "Mymensingh DC portal's bus table lists মাসকান্দা as a departure place. In the city corporation; upazila not stated."),
    (["mcc_bus"], "টাঙ্গাইল আন্তঃজেলা বাসর্টামিনাল", "টাঙ্গাইল আন্তঃজেলা বাস টার্মিনাল", "transport.bus_terminal", "Mymensingh", "",
     "Mymensingh City Corporation 'বাস টার্মিনাল' page (a terminal in the city for the Tangail route; name normalised from the "
     "printed 'বাসর্টামিনাল'). Upazila not stated."),
    (["mcc_bus"], "শম্ভগঞ্জ আন্তঃজেলা বাসর্টামিনাল", "শম্ভগঞ্জ আন্তঃজেলা বাস টার্মিনাল", "transport.bus_terminal", "Mymensingh", "",
     "Mymensingh City Corporation 'বাস টার্মিনাল' page (name normalised from the printed 'বাসর্টামিনাল'). Upazila not stated."),
    (["phulpur"], "হালুয়াঘাট বাসস্ট্যান্ড", "হালুয়াঘাট বাসস্ট্যান্ড", "transport.bus_terminal", "Mymensingh", "",
     "Phulpur upazila portal 'যোগাযোগ ব্যবস্থা': Dhaka-bound buses listed at 'হালুয়াঘাট বাসস্ট্যান্ড/ মহাখালী বাসস্ট্যান্ড' (their "
     "counter numbers are not copied). Upazila not stated."),
    (["tarakanda"], "বিসকা ইউনিয়নে আন্তঃজেলা রেল স্টেশন", "বিসকা রেলস্টেশন", "transport.railway_station", "Mymensingh", "Tarakanda",
     "Tarakanda upazila portal 'যোগাযোগ': 'বিসকা ইউনিয়নে আন্তঃজেলা রেল স্টেশন রয়েছে'. Name composed from the union name; the "
     "station's own name is not given."),
    (["nalitabari"], "নালিতাবাড়ী বাসস্টেশন", "নালিতাবাড়ী বাসস্টেশন", "transport.bus_terminal", "Sherpur", "Nalitabari",
     "Nalitabari upazila portal 'যোগাযোগ': from anywhere in the country to the Nalitabari bus station of the upazila, then by rickshaw "
     "to the upazila parishad."),
]
MYM_FACTS = [   # (page key, regex on the page text, entity_level, entity_name_en, district, fact, unit, note)
    ("iswarganj", r"রেল স্টেশন\s*-+\s*:\s*([০-৯0-9]+)\s*টি", "upazila", "Iswarganj", "Mymensingh", "railway_stations", "stations",
     "Iswarganj upazila portal 'যোগাযোগ ব্যবস্থা': 'রেল স্টেশন : ৩ টি' (stations not named)"),
]
MYM_MANIFEST = dict(
    key=MYM_KEY, division="mymensingh", kind="district_transport",
    name="District and upazila portals (Mymensingh Division) — bus terminals, stands and railway stations named on transport pages",
    organization="Deputy Commissioner / Upazila Nirbahi offices (national portal framework)", source_type="government_portal", trust_level=4,
    urls=list(MYM_PAGES.values()), accessed=None, publication_date=None, license=None, license_url=None,
    attribution="District and upazila portals (*.gov.bd, Bangladesh National Portal)",
    notes="No licence stated. No portal publishes a terminal, station or ghat register; rows are names explicitly given on the 'যোগাযোগ "
          "ব্যবস্থা' / 'যোগাযোগ' pages of the Jamalpur DC portal and of the upazila portals that name one, and on the Mymensingh City "
          "Corporation's 'বাস টার্মিনাল' page (the Mymensingh DC page gives "
          "a 2019 train timetable and bus routes by departure place; the Sherpur and Netrokona DC pages name none). Dhaka-side terminals "
          "(Mohakhali, Kamalapur), stations outside the division (Kaoraid, on the Bhaluka page), bus company counters, departure places "
          "not called a stand or terminal, and route descriptions without a named stop are not rows. raw/ keeps, per page that gave a "
          "row, only the lines carrying the matched phrases (mobiles/e-mails redacted; descriptive text is not copied into the CSVs).")
SITES = {"rajshahi": dict(folder="district_portals_transport_raj_2026"),
         "dhaka": dict(folder="district_portals_transport_dhk_2026", key=DHK_KEY, pages=DHK_PAGES, entries=DHK_ENTRIES,
                       manifest=DHK_MANIFEST, note_suffix=" Named on a portal page, not a registry entry; no address/coordinates/contact."),
         "rangpur": dict(folder="district_portals_transport_rang_2026", key=RANG_KEY, pages=RANG_PAGES, entries=RANG_ENTRIES,
                         manifest=RANG_MANIFEST, note_suffix=" Named on a portal page, not a registry entry; no address/coordinates/contact."),
         "chattogram": dict(folder="district_portals_transport_ctg_2026", key=CTG_KEY, pages=CTG_PAGES, entries=CTG_ENTRIES,
                            manifest=CTG_MANIFEST, note_suffix=" Named on a portal page, not a registry entry; no address/coordinates/contact."),
         "khulna": dict(folder="district_portals_transport_khl_2026", key=KHL_KEY, pages=KHL_PAGES, entries=KHL_ENTRIES,
                        manifest=KHL_MANIFEST, note_suffix=" Named on a portal page, not a registry entry; no address/coordinates/contact."),
         "barishal": dict(folder="district_portals_transport_bar_2026", key=BAR_KEY, pages=BAR_PAGES, entries=BAR_ENTRIES,
                          manifest=BAR_MANIFEST, facts=BAR_FACTS,
                          note_suffix=" Named on a portal page, not a registry entry; no address/coordinates/contact."),
         "sylhet": dict(folder="district_portals_transport_syl_2026", key=SYL_KEY, pages=SYL_PAGES, entries=SYL_ENTRIES,
                        manifest=SYL_MANIFEST, facts=SYL_FACTS, intermediates=SYL_INTERMEDIATES,
                        note_suffix=" Named on a portal page, not a registry entry; no address/coordinates/contact."),
         "mymensingh": dict(folder="district_portals_transport_mym_2026", key=MYM_KEY, pages=MYM_PAGES, entries=MYM_ENTRIES,
                            manifest=MYM_MANIFEST, facts=MYM_FACTS,
                            note_suffix=" Named on a portal page, not a registry entry; no address/coordinates/contact.")}
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
        INTERMEDIATES.extend(u for u in t.get("intermediates", []) if u not in INTERMEDIATES)   # before the first request


if __name__ == "__main__":
    main()
