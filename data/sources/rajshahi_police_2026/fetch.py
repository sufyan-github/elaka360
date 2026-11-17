#!/usr/bin/env python3
"""Fetch the head district's police thanas & numbers (default Rajshahi District Police, police.rajshahi.gov.bd, RAJSHAHI_POLICE_2026).

Usage: python3 fetch.py [--division rangpur] [--out DIR]."""
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

# --- RAJSHAHI_POLICE_2026 -----------------------------------------------------------------------------
KEY = "RAJSHAHI_POLICE_2026"
URL_CONTACT = "https://police.rajshahi.gov.bd/pages/static-pages/697f6dd335ce18e1c06b1c47"   # যোগাযোগ (thana OC/duty numbers)
URL_CIRCLES = "https://police.rajshahi.gov.bd/pages/static-pages/697f79bd35ce18e1c06b53d5"   # সার্কেল/থানাসমূহ
UPAZILA_EN = {"গোদাগাড়ী": "Godagari", "গোদগাড়ী": "Godagari", "তানোর": "Tanore", "মোহনপুর": "Mohanpur", "পুঠিয়া": "Puthia",
              "বাগমারা": "Bagmara", "দূর্গাপুর": "Durgapur", "দুর্গাপুর": "Durgapur", "চারঘাট": "Charghat", "বাঘা": "Bagha"}


def main():
    configure()
    if DIVISION != "rajshahi":
        return HEADS[DIVISION]["run"]()
    places, facts = [], []
    circle_of = {}
    r = get(URL_CIRCLES)
    if r is not None and r.ok:
        save_raw("rajshahi_police_circles.txt", "\n".join(content_text(r.text)))
        cur = ""
        for t in tables(r.text):
            for row in t:
                cells = [c for c in row if c]
                for c in cells:
                    if c.endswith("সার্কেল"):
                        cur = c
                # thana name = first cell after serial / circle that is an upazila name
                for c in cells:
                    if c in UPAZILA_EN and cur:
                        circle_of.setdefault(c, cur)
        circles = sorted(set(circle_of.values()))
        if circles:
            facts.append(dict(entity_level="district", entity_name_en="Rajshahi", district_en="Rajshahi", fact="police_circles",
                              value=len(circles), unit="circles", basis="listed", year=2026, source_key=KEY, source_url=URL_CIRCLES,
                              notes="Circles: " + ", ".join(circles) + " (district police, excludes RMP)"))
            facts.append(dict(entity_level="district", entity_name_en="Rajshahi", district_en="Rajshahi", fact="police_stations",
                              value=len(circle_of), unit="thanas", basis="listed", year=2026, source_key=KEY, source_url=URL_CIRCLES,
                              notes="Thanas of Rajshahi District Police (outside RMP jurisdiction)"))
    r = get(URL_CONTACT)
    if r is not None and r.ok:
        save_raw("rajshahi_police_contact.txt", "\n".join(content_text(r.text)))
        for t in tables(r.text):
            for row in t:
                if len(row) < 3 or not re.match(r"^[0-9০-৯]+\.?$", row[0]):
                    continue
                name = row[1]
                cells = row[2:]
                phones = [phone_norm(c) for c in cells if phone_norm(c)]
                email = next((c for c in cells if "@" in c), "")
                if name.endswith("থানা"):
                    base = name.replace(" থানা", "").strip()
                    up = UPAZILA_EN.get(base, "")
                    places.append(dict(
                        source_key=KEY, source_id=f"rajpol-{up.lower() or base}", name_bn=name, name_en="",
                        category_key="emergency.police_station", district_en="Rajshahi", upazila_en=up,
                        phone="; ".join(phones), email=email, operator="রাজশাহী জেলা পুলিশ", ownership="public",
                        extra_json=xj({"oc_mobile": phones[0] if phones else "", "duty_officer_mobile": phones[1] if len(phones) > 1 else "",
                                       "circle_bn": circle_of.get(base, "") or circle_of.get(UPAZILA_EN and next((k for k, v in UPAZILA_EN.items() if v == up and k in circle_of), ""), "")}),
                        source_url=URL_CONTACT,
                        notes="phone = OC official mobile; duty-officer mobile (both as published by Rajshahi District Police)" +
                              ("; source spells the thana 'গোদগাড়ী' (circle page: 'গোদাগাড়ী')" if base == "গোদগাড়ী" else "")))
                elif "পুলিশ সুপারের কার্যালয়" in name:
                    places.append(dict(
                        source_key=KEY, source_id="rajpol-sp-office", name_bn="পুলিশ সুপারের কার্যালয়, রাজশাহী", name_en="",
                        category_key="government.sp_office", district_en="Rajshahi", phone="; ".join(phones), email=email,
                        operator="রাজশাহী জেলা পুলিশ", ownership="public", source_url=URL_CONTACT,
                        notes="Listed as 'পুলিশ সুপারের কার্যালয়' (district name added from the portal); no phone given on this page"))
                elif "কন্ট্রোল রুম" in name:
                    txt = asc(" ".join(content_text(r.text)))
                    hot = re.search(r"হট লাইন-\s*([0-9\-]+)", txt)
                    places.append(dict(
                        source_key=KEY, source_id="rajpol-control-room", name_bn="রাজশাহী জেলা পুলিশ কন্ট্রোল রুম", name_en="",
                        category_key="emergency", district_en="Rajshahi",
                        phone="; ".join(phones + ([hot.group(1)] if hot else [])), email=email, operator="রাজশাহী জেলা পুলিশ",
                        ownership="public", extra_json=xj({"label_in_source": name, "hotline": hot.group(1) if hot else ""}),
                        source_url=URL_CONTACT, notes="Name composed from 'কন্ট্রোল রুম' row and the page text 'রাজশাহী জেলা পুলিশ কন্ট্রোলরুম'"))
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    write_manifest(dict(
        key=KEY, division="rajshahi", kind="district_police", name="Rajshahi District Police — thanas, SP office and control room numbers", organization="Rajshahi District Police (Bangladesh Police)",
        source_type="government_portal", trust_level=4, urls=[URL_CONTACT, URL_CIRCLES],
        accessed=__import__("datetime").date.today().isoformat(), publication_date=None, license=None, license_url=None,
        attribution="Office of the Superintendent of Police, Rajshahi (police.rajshahi.gov.bd)",
        notes="No licence stated. Institutional numbers only (OC and duty-officer official mobiles, official e-mails); no officer names. "
              "The portal's map link for the SP office is a Google Maps search URL, not a published coordinate, so no lat/lon."),
        ["places.csv", "facts.csv", "raw/rajshahi_police_contact.txt", "raw/rajshahi_police_circles.txt"])


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


# Rangpur Division names: Bangla -> English (HDX COD-AB spellings). District hosts verified by page title (Nov 2026);
# upazila portal subdomains verified by their home-page titles ("হোম | <upazila> উপজেলা").
RANGPUR_DISTRICTS = {"রংপুর": "Rangpur", "পঞ্চগড়": "Panchagarh", "দিনাজপুর": "Dinajpur", "লালমনিরহাট": "Lalmonirhat",
                     "নীলফামারী": "Nilphamari", "গাইবান্ধা": "Gaibandha", "ঠাকুরগাঁও": "Thakurgaon", "কুড়িগ্রাম": "Kurigram"}
RANGPUR_DISTRICT_HOSTS = {"Rangpur": "rangpur.gov.bd", "Panchagarh": "panchagarh.gov.bd", "Dinajpur": "dinajpur.gov.bd",
                          "Lalmonirhat": "lalmonirhat.gov.bd", "Nilphamari": "nilphamari.gov.bd", "Gaibandha": "gaibandha.gov.bd",
                          "Thakurgaon": "thakurgaon.gov.bd", "Kurigram": "kurigram.gov.bd"}
RANGPUR_UPAZILAS = {  # district -> [(english, bangla names/aliases..., portal subdomain)]
    "Rangpur": [("Badarganj", ["বদরগঞ্জ"], "badargonj"), ("Gangachara", ["গংগাচড়া", "গঙ্গাচড়া"], "gangachara"),
                ("Kaunia", ["কাউনিয়া"], "kaunia"), ("Rangpur Sadar", ["রংপুর সদর"], "rangpursadar"),
                ("Mithapukur", ["মিঠাপুকুর"], "mithapukur"), ("Pirgachha", ["পীরগাছা"], "pirgacha"),
                ("Pirganj", ["পীরগঞ্জ"], "pirgonj"), ("Taraganj", ["তারাগঞ্জ"], "taragonj")],
    "Panchagarh": [("Atowari", ["আটোয়ারী"], "atwari"), ("Boda", ["বোদা"], "boda"), ("Debiganj", ["দেবীগঞ্জ"], "debiganj"),
                   ("Panchagarh Sadar", ["পঞ্চগড় সদর"], "panchagarhsadar"), ("Tentulia", ["তেঁতুলিয়া", "তেতুলিয়া"], "tetulia")],
    "Thakurgaon": [("Baliadangi", ["বালিয়াডাঙ্গী", "বালিয়াডাংগী"], "baliadangi"), ("Haripur", ["হরিপুর"], "haripur"),
                   ("Pirganj", ["পীরগঞ্জ"], "pirganj"), ("Ranishankail", ["রাণীশংকৈল", "রানীশংকৈল"], "ranisankail"),
                   ("Thakurgaon Sadar", ["ঠাকুরগাঁও সদর"], "thakurgaonsadar")],
    "Nilphamari": [("Dimla", ["ডিমলা"], "dimla"), ("Domar", ["ডোমার"], "domar"), ("Jaldhaka", ["জলঢাকা"], "jaldhaka"),
                   ("Kishoreganj", ["কিশোরগঞ্জ"], "kishorganj"), ("Nilphamari Sadar", ["নীলফামারী সদর"], "nilphamarisadar"),
                   ("Saidpur", ["সৈয়দপুর"], "syedpur")],
    "Lalmonirhat": [("Aditmari", ["আদিতমারী"], "aditmari"), ("Hatibandha", ["হাতীবান্ধা"], "hatibandha"),
                    ("Kaliganj", ["কালীগঞ্জ"], "kaliganj"), ("Lalmonirhat Sadar", ["লালমনিরহাট সদর"], "sadar"),
                    ("Patgram", ["পাটগ্রাম"], "patgram")],
    "Gaibandha": [("Fulchhari", ["ফুলছড়ি"], "phulchari"), ("Gaibandha Sadar", ["গাইবান্ধা সদর"], "gaibandhasadar"),
                  ("Gobindaganj", ["গোবিন্দগঞ্জ"], "gobindaganj"), ("Palashbari", ["পলাশবাড়ী", "পলাশবাড়ি"], "palashbari"),
                  ("Sadullapur", ["সাদুল্লাপুর", "সাদুল্যাপুর"], "sadullapur"), ("Saghata", ["সাঘাটা"], "saghata"),
                  ("Sundarganj", ["সুন্দরগঞ্জ"], "sundarganj")],
    "Kurigram": [("Bhurungamari", ["ভূরুঙ্গামারী", "ভুরুঙ্গামারী"], "bhurungamari"), ("Rajibpur", ["রাজিবপুর", "রাজীবপুর"], "charrajibpur"),
                 ("Chilmari", ["চিলমারী"], "chilmari"), ("Phulbari", ["ফুলবাড়ী"], "phulbari"),
                 ("Kurigram Sadar", ["কুড়িগ্রাম সদর"], "kurigramsadar"), ("Nageshwari", ["নাগেশ্বরী"], "nageshwari"),
                 ("Rajarhat", ["রাজারহাট"], "rajarhat"), ("Roumari", ["রৌমারী"], "rowmari"), ("Ulipur", ["উলিপুর"], "ulipur")],
    "Dinajpur": [("Birampur", ["বিরামপুর"], "birampur"), ("Birganj", ["বীরগঞ্জ"], "birganj"), ("Birol", ["বিরল"], "birol"),
                 ("Bochaganj", ["বোচাগঞ্জ"], "bochaganj"), ("Chirirbandar", ["চিরিরবন্দর"], "chirirbandar"),
                 ("Fulbari", ["ফুলবাড়ী"], "fulbari"), ("Ghoraghat", ["ঘোড়াঘাট"], "ghoraghat"), ("Hakimpur", ["হাকিমপুর"], "hakimpur"),
                 ("Kaharole", ["কাহারোল"], "kaharol"), ("Khansama", ["খানসামা"], "khansama"),
                 ("Dinajpur Sadar", ["দিনাজপুর সদর"], "dinajpursadar"), ("Nababganj", ["নবাবগঞ্জ"], "nawabganj"),
                 ("Parbatipur", ["পার্বতীপুর"], "parbatipur")],
}
# Rangpur Metropolitan Police thanas (rpmp.gov.bd), English transliterations
RANGPUR_CITY_THANAS = {"কোতয়ালী": "Kotwali", "তাজহাট": "Tajhat", "মাহিগঞ্জ": "Mahiganj", "হারাগাছ": "Haragach",
                       "পরশুরাম": "Parshuram", "হাজিরহাট": "Hajirhat"}


# --- national-portal police sites (Rangpur Range and later divisions) -------------------------------------
# District police portals police.<district>.gov.bd and thana portals police.<upazila>.<district>.gov.bd (2026 framework).
# Contacts kept: office landlines (fixed-line numbers), *.gov.bd e-mails and police official mobiles (01320-xxxxxx series,
# and the older 01713-37xxxx/-38xxxx police CUG series) of the office head's post. Personal e-mails (gmail etc.), other mobiles
# and officers' names are never copied.
OFFICIAL_MOBILE = re.compile(r"^(01320\d{6}|017133[78]\d{4})$")


def widget(t, name="ContentViewerWidget"):
    i = t.find('data-widget_name="%s"' % name)
    if i < 0:
        return ""
    j = t.find('data-widget_name="', i + 30)
    return t[i:j if j > 0 else len(t)]


def page_title(t):
    m = re.search(r"<title>(.*?)</title>", t, re.S)
    return clean(m.group(1)) if m else ""


def officer_cards(t):
    """Officer cards (/pages/officers) -> list of dicts of the labelled fields."""
    t = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", " ", t, flags=re.S)
    lines = [nfc(re.sub(r"\s+", " ", _html.unescape(x))) for x in re.split(r"<[^>]+>", t)]
    lines = [x for x in lines if x]
    labels = ["নাম", "পদবি", "অফিস", "ওয়েব পোর্টল", "ইমেইল", "ফোন (অফিস)", "ইন্টারকম", "কক্ষ নম্বর", "মোবাইল", "ফ্যাক্স",
              "যোগদানের তারিখ", "ব্যাচ (বিসিএস)"]
    cards, cur, key = [], None, None
    for x in lines:
        if x == "নাম":
            cur = {}
            cards.append(cur)
            key = "নাম"
            continue
        if cur is None:
            continue
        if x in labels:
            key = x
            continue
        if "ভিকার্ড" in x or x in ("•", "দেখুন"):
            key = None
            continue
        if key:
            cur[key] = (cur.get(key, "") + x) if key == "ইমেইল" else (cur.get(key, "") + " " + x).strip()
    return cards


def _digits(s):
    return re.sub(r"^\+?880", "0", re.sub(r"[^\d+]", "", asc(s or "")))


def landlines(*vals):
    out = []
    for v in vals:
        for p in re.split(r"[,/;]|\s{2,}", asc(v or "")):
            d = _digits(p)
            if re.match(r"^0[2-9]\d{5,}$", d):  # fixed line: 0 + area code; drops mobiles (01...) and dummies (000...)
                out.append(d)
    return list(dict.fromkeys(out))


def official_mobiles(*vals):
    out = []
    for v in vals:
        for p in re.split(r"[,/;]", asc(v or "")):
            d = _digits(p)
            if OFFICIAL_MOBILE.match(d):
                out.append(d)
    return list(dict.fromkeys(out))


def gov_emails(*vals):
    out = []
    for v in vals:
        s = (v or "").replace(" ", "").replace("[at]", "@").lower()
        out += [m for m in re.findall(r"[a-z0-9._-]+@[a-z0-9.-]+\.[a-z]{2,}", s) if m.endswith(".gov.bd")]
    return list(dict.fromkeys(out))


def fetch_html(url):
    r = get(url)
    if r is None or r.status_code != 200:
        print("  unavailable:", url, getattr(r, "status_code", "no response"))
        return ""
    r.encoding = r.encoding or "utf-8"
    return r.text


def head_cards(base, home):
    """Officer cards of a portal: the PersonCard (office head) link on the home page, else /pages/officers."""
    m = re.search(r'data-widget_name="PersonCardWidget".*?href="(/pages/officers/[^"]+)"', home, re.S)
    url = base.rstrip("/") + (m.group(1) if m else "/pages/officers")
    t = fetch_html(url)
    cards = officer_cards(widget(t) or widget(t, "HybridBrowseWidget") or t)
    if not cards and m:  # stale PersonCard link -> officer list
        url = base.rstrip("/") + "/pages/officers"
        t = fetch_html(url)
        cards = officer_cards(widget(t) or widget(t, "HybridBrowseWidget") or t)
    return cards, url


def is_head(card, words):
    return any(w in (card.get("পদবি") or "") for w in words)


OC_WORDS = ("ইনচার্জ", "ইন-চার্জ", "ইন চার্জ")


def sp_office_row(key, dist, dist_bn, sid):
    """SP office from the office head's officer card on police.<district>.gov.bd."""
    base = "https://police.%s.gov.bd/" % dist.lower()
    home = fetch_html(base)
    if not home:
        return None
    cards, curl = head_cards(base, home)
    card = next((c for c in cards if is_head(c, ("পুলিশ সুপার",)) and "অতিরিক্ত" not in c.get("পদবি", "")), {})
    lls = landlines(card.get("ফোন (অফিস)"))
    mob = official_mobiles(card.get("মোবাইল"), card.get("ফোন (অফিস)"))
    em = gov_emails(card.get("ইমেইল"))
    fax = landlines(card.get("ফ্যাক্স"))
    return dict(source_key=key, source_id=sid, name_bn="পুলিশ সুপারের কার্যালয়, %s" % dist_bn, name_en="",
                category_key="government.sp_office", district_en=dist, phone="; ".join(lls + mob), website=base,
                email="; ".join(em), operator="%s জেলা পুলিশ" % dist_bn, ownership="public",
                extra_json=xj({"portal_title": page_title(home).replace("হোম | ", ""), "head_designation": card.get("পদবি"),
                               "sp_official_mobile": "; ".join(mob), "fax": "; ".join(fax)}),
                source_url=curl, notes="Contacts from the Superintendent of Police's officer card (office landline, police official mobile, "
                                       "official e-mail); officer's name not copied.")


def thana_name(title, upa_bn, dist_bn):
    """'হোম | মিঠাপুকুর থানা, রংপুর' -> 'মিঠাপুকুর থানা'; 'থানা, তেতুলিয়া, পঞ্চগড়' -> 'তেতুলিয়া থানা'."""
    t = re.sub(r"^হোম\s*\|\s*", "", title).strip(" ।")
    parts = [p.strip(" ।") for p in re.split(r"\s*,\s*", t) if p.strip(" ।")]
    name = None
    if len(parts) >= 2 and parts[0] == "থানা":
        name = parts[1] + " থানা"
    elif len(parts) >= 2 and parts[1] == "থানা":
        name = parts[0] + " থানা"
    elif parts and "থানা" in parts[0]:
        name = parts[0]
    if name and name.startswith("সদর "):
        name = dist_bn + " " + name
    return nfc(name) if name else None


def thana_row_from_portal(key, dist, dist_bn, upa_en, upa_bn, host, sid, listed_on=None):
    base = "https://%s/" % host
    home = fetch_html(base)
    if not home:
        return None, "portal %s did not respond" % host
    title = page_title(home)
    name = thana_name(title, upa_bn, dist_bn)
    notes = []
    if not name:
        name = "%s থানা" % upa_bn
        notes.append("portal title %r carries no thana name; name composed from the upazila" % title)
    cards, curl = head_cards(base, home)
    oc = next((c for c in cards if is_head(c, OC_WORDS)), None)
    lls = []
    for c in ([oc] if oc else []) + cards:
        lls = landlines(c.get("ফোন (অফিস)"))
        if lls:
            break
    mob = official_mobiles(oc.get("মোবাইল"), oc.get("ফোন (অফিস)")) if oc else []
    em = gov_emails(*[c.get("ইমেইল") for c in ([oc] if oc else cards[:1])])
    if not oc:
        notes.append("no officer-in-charge card on the thana portal; phone = office landline only")
    notes.append("Contacts from the thana portal's officer cards (office landline, OC's police official mobile, *.gov.bd e-mail); "
                 "cards may be outdated; officers' names, personal e-mails and other mobiles not copied")
    return dict(source_key=key, source_id=sid, name_bn=name, name_en="", category_key="emergency.police_station", district_en=dist,
                upazila_en=upa_en or "", phone="; ".join(lls + mob[:1]), website=base, email="; ".join(em),
                operator="%s জেলা পুলিশ" % dist_bn, ownership="public",
                extra_json=xj({"portal_title": re.sub(r"^হোম\s*\|\s*", "", title), "oc_official_mobile": mob[0] if mob else "",
                               "office_landline": "; ".join(lls), "card_designation": oc.get("পদবি") if oc else "",
                               "listed_on": listed_on}),
                source_url=curl if cards else base, notes="; ".join(notes)), None


# --- Rangpur District Police (police.rangpur.gov.bd; Rangpur city is policed by RpMP, see RANGPUR_METRO_POLICE_THANAS_2026) ---
RP_KEY = "RANGPUR_POLICE_2026"
RP_GLANCE = "https://police.rangpur.gov.bd/pages/static-pages/6977394fc4774958d7c10b45"  # এক নজরে
# police.rangpursadar.rangpur.gov.bd is titled 'কোতয়ালী থানা, সদর, রংপুর' (Kotwali, now an RpMP thana) -> not a district thana
RP_SKIP = {"Rangpur Sadar"}


def main_rangpur():
    places, facts, missing = [], [], []
    sp = sp_office_row(RP_KEY, "Rangpur", "রংপুর", "rangpol-sp-office")
    if sp:
        places.append(sp)
    t = fetch_html(RP_GLANCE)
    if t:
        lines = content_text(t)
        intro = "\n".join(lines)
        intro = intro.split("এক নজরে রংপুর জেলা পুলিশ")[0]  # officer name list not kept
        save_raw("rangpur_police_glance.txt", intro)
        txt = " ".join(lines)
        circles = list(dict.fromkeys(re.findall(r"\(([^()]*সার্কেল)\)", txt)))
        for pat, fact, unit, extra in ((r"([০-৯0-9]+)টি থানা", "police_stations", "thanas", "Rangpur District Police (outside RpMP)"),
                                       (r"([০-৯0-9]+)টি সার্কেল", "police_circles", "circles", "Circles: " + ", ".join(circles)),
                                       (r"([০-৯0-9]+)টি তদন্ত কেন্দ্র", "police_investigation_centres", "centres", "")):
            m = re.search(pat, txt)
            if m:
                facts.append(dict(entity_level="district", entity_name_en="Rangpur", district_en="Rangpur", fact=fact,
                                  value=int(asc(m.group(1))), unit=unit, basis="reported", year=2026, source_key=RP_KEY,
                                  source_url=RP_GLANCE, notes="; ".join(x for x in ["'এক নজরে': " + m.group(0), extra] if x)))
    for en, bns, sub in RANGPUR_UPAZILAS["Rangpur"]:
        if en in RP_SKIP:
            continue
        rec, err = thana_row_from_portal(RP_KEY, "Rangpur", "রংপুর", en, bns[0], "police.%s.rangpur.gov.bd" % sub,
                                         "rangpol-%s" % en.lower().replace(" ", "-"))
        if rec:
            places.append(rec)
        else:
            missing.append(err)
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    if missing:
        print("unavailable:", missing)
    write_manifest(dict(
        key=RP_KEY, division="rangpur", kind="district_police",
        name="Rangpur District Police — SP office and thanas", organization="Rangpur District Police (Bangladesh Police)",
        source_type="government_portal", trust_level=4,
        urls=["https://police.rangpur.gov.bd/", RP_GLANCE, "https://police.<upazila>.rangpur.gov.bd/"],
        accessed=__import__("datetime").date.today().isoformat(), publication_date=None, license=None, license_url=None,
        attribution="Office of the Superintendent of Police, Rangpur (police.rangpur.gov.bd) and the thana portals",
        notes="No licence stated. police.rangpur.gov.bd publishes no contact table; SP office from the Superintendent's officer card, "
              "thanas from each thana's portal officer cards (office landline, OC's police official mobile, *.gov.bd e-mail). "
              "Personal e-mails, other mobiles and officers' names are not copied. The 'এক নজরে' page gives 8 thanas; only the "
              "7 upazila thana portals were found (police.rangpursadar.rangpur.gov.bd is the old Kotwali thana, now RpMP)."
              + (" Unavailable this run: " + "; ".join(missing) if missing else "")),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


HEADS = {"rajshahi": dict(folder="rajshahi_police_2026"), "rangpur": dict(folder="rangpur_police_2026", run=main_rangpur)}


def configure():
    global DIVISION, HERE, RAW
    DIVISION, out = parse_division_args({k: v["folder"] for k, v in HEADS.items()})
    HERE = Path(out)
    RAW = HERE / "raw"


if __name__ == "__main__":
    main()
