#!/usr/bin/env python3
"""Fetch the head district's police thanas & numbers (default Rajshahi District Police, police.rajshahi.gov.bd, RAJSHAHI_POLICE_2026).

Usage: python3 fetch.py [--division rangpur|dhaka|chattogram|khulna|barishal|sylhet|mymensingh] [--out DIR]."""
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
# Dhaka Division names: Bangla -> English (HDX COD-AB v03 spellings). District hosts verified by page title (Nov 2026);
# upazila portal subdomains verified by their home-page titles ("হোম | <upazila> উপজেলা").
DHAKA_DISTRICTS = {"ঢাকা": "Dhaka", "নরসিংদী": "Narsingdi", "গাজীপুর": "Gazipur", "শরীয়তপুর": "Shariatpur",
                   "নারায়ণগঞ্জ": "Narayanganj", "টাঙ্গাইল": "Tangail", "কিশোরগঞ্জ": "Kishoreganj", "মানিকগঞ্জ": "Manikganj",
                   "মুন্সীগঞ্জ": "Munshiganj", "রাজবাড়ী": "Rajbari", "মাদারীপুর": "Madaripur", "গোপালগঞ্জ": "Gopalganj",
                   "ফরিদপুর": "Faridpur"}
DHAKA_DISTRICT_HOSTS = {en: "%s.gov.bd" % en.lower() for en in DHAKA_DISTRICTS.values()}
DHAKA_UPAZILAS = {  # district -> [(english, bangla names/aliases..., portal subdomain)]
    "Dhaka": [("Dhamrai", ["ধামরাই"], "dhamrai"), ("Dohar", ["দোহার"], "dohar"),
              ("Keraniganj", ["কেরাণীগঞ্জ", "কেরানীগঞ্জ"], "keraniganj"), ("Nawabganj", ["নবাবগঞ্জ"], "nawabganj"),
              ("Savar", ["সাভার"], "savar")],
    "Narsingdi": [("Belabo", ["বেলাবো", "বেলাব"], "belabo"), ("Manohardi", ["মনোহরদী", "মনোহরদি"], "monohardi"),
                  ("Narsingdi Sadar", ["নরসিংদী সদর"], "narsingdisadar"), ("Palash", ["পলাশ"], "palash"),
                  ("Raipura", ["রায়পুরা"], "raipura"), ("Shibpur", ["শিবপুর"], "shibpur")],
    "Gazipur": [("Gazipur Sadar", ["গাজীপুর সদর"], "sadar"), ("Kaliakair", ["কালিয়াকৈর"], "kaliakair"),
                ("Kaliganj", ["কালীগঞ্জ"], "kaliganj"), ("Kapasia", ["কাপাসিয়া"], "kapasia"), ("Sreepur", ["শ্রীপুর"], "sreepur")],
    "Shariatpur": [("Bhedarganj", ["ভেদরগঞ্জ"], "bhedarganj"), ("Damudya", ["ডামুড্যা"], "damudya"),
                   ("Gosairhat", ["গোসাইরহাট"], "gosairhat"), ("Naria", ["নড়িয়া"], "naria"),
                   ("Shariatpur Sadar", ["শরীয়তপুর সদর", "শরিয়তপুর সদর"], "sadar"), ("Zajira", ["জাজিরা"], "zajira")],
    "Narayanganj": [("Araihazar", ["আড়াইহাজার"], "araihazar"), ("Bandar", ["বন্দর"], "bandar"),
                    ("Narayanganj Sadar", ["নারায়ণগঞ্জ সদর", "নারায়নগঞ্জ সদর"], "narayanganjsadar"),
                    ("Rupganj", ["রূপগঞ্জ"], "rupganj"), ("Sonargaon", ["সোনারগাঁও", "সোনারগাঁ"], "sonargaon")],
    "Tangail": [("Basail", ["বাসাইল"], "basail"), ("Bhuanpur", ["ভূঞাপুর", "ভুয়াপুর", "ভূয়াপুর"], "bhuapur"),
                ("Delduar", ["দেলদুয়ার"], "delduar"), ("Dhanbari", ["ধনবাড়ী", "ধনবাড়ি"], "dhanbari"),
                ("Ghatail", ["ঘাটাইল"], "ghatail"), ("Gopalpur", ["গোপালপুর"], "gopalpur"), ("Kalihati", ["কালিহাতী"], "kalihati"),
                ("Madhupur", ["মধুপুর"], "madhupur"), ("Mirzapur", ["মির্জাপুর"], "mirzapur"), ("Nagarpur", ["নাগরপুর"], "nagarpur"),
                ("Sakhipur", ["সখিপুর", "সখীপুর"], "sakhipur"), ("Tangail Sadar", ["টাঙ্গাইল সদর"], "tangailsadar")],
    "Kishoreganj": [("Austagram", ["অষ্টগ্রাম"], "austagram"), ("Bajitpur", ["বাজিতপুর"], "bajitpur"), ("Bhairab", ["ভৈরব"], "bhairab"),
                    ("Hossainpur", ["হোসেনপুর"], "hossainpur"), ("Itna", ["ইটনা"], "itna"), ("Karimganj", ["করিমগঞ্জ"], "karimgonj"),
                    ("Katiadi", ["কটিয়াদী", "কটিয়াদি"], "katiadi"), ("Kishoreganj Sadar", ["কিশোরগঞ্জ সদর"], "kishoreganjsadar"),
                    ("Kuliarchar", ["কুলিয়ারচর"], "kuliarchar"), ("Mithamain", ["মিঠামইন"], "mithamoin"), ("Nikli", ["নিকলী", "নিকলি"], "nikli"),
                    ("Pakundia", ["পাকুন্দিয়া"], "pakundia"), ("Tarail", ["তাড়াইল"], "tarail")],
    "Manikganj": [("Daulatpur", ["দৌলতপুর"], "daulatpur"), ("Ghior", ["ঘিওর"], "gior"), ("Harirampur", ["হরিরামপুর"], "harirampur"),
                  ("Manikganj Sadar", ["মানিকগঞ্জ সদর"], "sadar"), ("Saturia", ["সাটুরিয়া"], "saturia"),
                  ("Shibalay", ["শিবালয়"], "shibaloy"), ("Singair", ["সিংগাইর", "সিঙ্গাইর"], "singair")],
    "Munshiganj": [("Gazaria", ["গজারিয়া"], "gajaria"), ("Louhajang", ["লৌহজং"], "louhajanj"),
                   ("Munshiganj Sadar", ["মুন্সীগঞ্জ সদর", "মুন্সিগঞ্জ সদর"], "sadar"), ("Sirajdikhan", ["সিরাজদিখান"], "sirajdikhan"),
                   ("Sreenagar", ["শ্রীনগর"], "sreenagar"), ("Tongibari", ["টংগিবাড়ী", "টংগীবাড়ি", "টঙ্গিবাড়ী", "টংগীবাড়ী"], "tongibari")],
    "Rajbari": [("Baliakandi", ["বালিয়াকান্দি"], "baliakandi"), ("Goalanda", ["গোয়ালন্দ"], "goalanda"),
                ("Kalukhali", ["কালুখালী", "কালুখালি"], "kalukhali"), ("Pangsha", ["পাংশা"], "pangsa"),
                ("Rajbari Sadar", ["রাজবাড়ী সদর"], "sadar")],
    "Madaripur": [("Dasar", ["ডাসার"], "dasar"), ("Kalkini", ["কালকিনি"], "kalkini"), ("Madaripur Sadar", ["মাদারীপুর সদর"], "sadar"),
                  ("Rajoir", ["রাজৈর"], "rajoir"), ("Shibchar", ["শিবচর"], "shibchar")],
    "Gopalganj": [("Gopalganj Sadar", ["গোপালগঞ্জ সদর"], "sadar"), ("Kashiani", ["কাশিয়ানী"], "kashiani"),
                  ("Kotalipara", ["কোটালীপাড়া"], "kotalipara"), ("Muksudpur", ["মুকসুদপুর"], "muksudpur"),
                  ("Tungipara", ["টুঙ্গিপাড়া", "টুংগীপাড়া"], "tungipara")],
    "Faridpur": [("Alfadanga", ["আলফাডাঙ্গা"], "alfadanga"), ("Bhanga", ["ভাঙ্গা"], "bhanga"), ("Boalmari", ["বোয়ালমারী"], "boalmari"),
                 ("Char Bhadrasan", ["চরভদ্রাসন"], "charbhadrasan"), ("Faridpur Sadar", ["ফরিদপুর সদর"], "sadar"),
                 ("Madhukhali", ["মধুখালী"], "madhukhali"), ("Nagarkanda", ["নগরকান্দা"], "nagarkanda"), ("Sadarpur", ["সদরপুর"], "sadarpur"),
                 ("Saltha", ["সালথা"], "saltha")],
}
# Dhaka Metropolitan Police thanas (Dhaka DC portal 'এক নজরে' list + Khilkhet from dmp.gov.bd), English names as DMP spells
# them where it lists them (normalised spacing). Longer names first so 'তেজগাঁও শিল্পাঞ্চল' wins over 'তেজগাঁও'.
DHAKA_CITY_THANAS = {
    "তেজগাঁও শিল্পাঞ্চল": "Tejgaon Industrial Area", "শেরেবাংলা নগর": "Sher-e-Bangla Nagar", "কামরাঙ্গীরচর": "Kamrangirchar",
    "উত্তরা পশ্চিম": "Uttara West", "উত্তরা পূর্ব": "Uttara East", "দারুস সালাম": "Darus Salam", "শাহজাহানপুর": "Shahjahanpur",
    "কোতোয়ালী": "Kotwali", "সূত্রাপুর": "Sutrapur", "বংশাল": "Bangshal", "চকবাজার": "Chawkbazar", "লালবাগ": "Lalbagh",
    "ওয়ারী": "Wari", "গেন্ডারিয়া": "Gandaria", "খিলগাঁও": "Khilgaon", "রামপুরা": "Rampura", "মতিঝিল": "Motijheel",
    "সবুজবাগ": "Sabujbagh", "মুগদা": "Mugda", "যাত্রাবাড়ী": "Jatrabari", "ডেমরা": "Demra", "শ্যামপুর": "Shyampur",
    "কদমতলী": "Kadamtali", "পল্টন": "Paltan", "শাহবাগ": "Shahbagh", "রমনা": "Ramna", "ধানমন্ডি": "Dhanmondi",
    "নিউমার্কেট": "New Market", "কলাবাগান": "Kalabagan", "হাজারীবাগ": "Hazaribagh", "মোহাম্মদপুর": "Mohammadpur",
    "আদাবর": "Adabor", "তেজগাঁও": "Tejgaon", "ভাষানটেক": "Bhashantek", "কাফরুল": "Kafrul", "মিরপুর": "Mirpur",
    "পল্লবী": "Pallabi", "শাহআলী": "Shah Ali", "রূপনগর": "Rupnagar", "বাড্ডা": "Badda", "ভাটারা": "Bhatara",
    "বনানী": "Banani", "গুলশান": "Gulshan", "ক্যান্টনমেন্ট": "Cantonment", "তুরাগ": "Turag", "উত্তরখান": "Uttar Khan",
    "দক্ষিণখান": "Dakshinkhan", "হাতিরঝিল": "Hatirjheel", "বিমানবন্দর": "Biman Bandar", "খিলক্ষেত": "Khilkhet"}


# Chattogram Division names: Bangla -> English (HDX COD-AB v03 spellings). District hosts verified by page title (Nov 2026;
# comilla.gov.bd / chittagong.gov.bd are the hosts the portals' own menus use, cumilla.gov.bd / chattogram.gov.bd serve the
# same sites); upazila portal subdomains verified by their home-page titles ("হোম | <upazila> উপজেলা").
CHATTOGRAM_DISTRICTS = {"চট্টগ্রাম": "Chattogram", "কুমিল্লা": "Cumilla", "ফেনী": "Feni", "ব্রাহ্মণবাড়িয়া": "Brahmanbaria",
                        "রাঙ্গামাটি": "Rangamati", "নোয়াখালী": "Noakhali", "চাঁদপুর": "Chandpur", "লক্ষ্মীপুর": "Lakshmipur",
                        "কক্সবাজার": "Cox's Bazar", "খাগড়াছড়ি": "Khagrachhari", "বান্দরবান": "Bandarban"}
CHATTOGRAM_DISTRICT_HOSTS = {"Chattogram": "chittagong.gov.bd", "Cumilla": "comilla.gov.bd", "Feni": "feni.gov.bd",
                             "Brahmanbaria": "brahmanbaria.gov.bd", "Rangamati": "rangamati.gov.bd", "Noakhali": "noakhali.gov.bd",
                             "Chandpur": "chandpur.gov.bd", "Lakshmipur": "lakshmipur.gov.bd", "Cox's Bazar": "coxsbazar.gov.bd",
                             "Khagrachhari": "khagrachhari.gov.bd", "Bandarban": "bandarban.gov.bd"}
CHATTOGRAM_UPAZILAS = {  # district -> [(english, bangla names/aliases..., portal subdomain)]
    "Chattogram": [("Anwara", ["আনোয়ারা"], "anwara"), ("Banshkhali", ["বাঁশখালী", "বাশখালী"], "banshkhali"),
                   ("Boalkhali", ["বোয়ালখালী"], "boalkhali"), ("Chandanaish", ["চন্দনাইশ"], "chandanaish"),
                   ("Fatikchhari", ["ফটিকছড়ি"], "fatikchhari"), ("Hathazari", ["হাটহাজারী"], "hathazari"),
                   ("Karnaphuli", ["কর্ণফুলী", "কর্ণফুলি"], "karnafuli"), ("Lohagara", ["লোহাগাড়া"], "lohagara"),
                   ("Mirsarai", ["মীরসরাই", "মিরসরাই"], "mirsharai"), ("Patiya", ["পটিয়া"], "patiya"),
                   ("Rangunia", ["রাঙ্গুনিয়া", "রাংগুনিয়া"], "rangunia"), ("Raozan", ["রাউজান"], "raozan"),
                   ("Sandwip", ["সন্দ্বীপ"], "sandwip"), ("Satkania", ["সাতকানিয়া"], "satkania"),
                   ("Sitakunda", ["সীতাকুন্ড", "সীতাকুণ্ড"], "sitakunda")],
    "Cumilla": [("Sadar Dakkhin", ["সদর দক্ষিণ", "কুমিল্লা সদর দক্ষিণ"], "sadarsouth"),
                ("Adarsha Sadar", ["আদর্শ সদর", "কুমিল্লা আদর্শ সদর", "কুমিল্লা সদর"], "comillasadar"),
                ("Barura", ["বরুড়া"], "barura"), ("Brahmanpara", ["ব্রাহ্মণপাড়া"], "brahmanpara"),
                ("Burichang", ["বুড়িচং"], "burichang"), ("Chandina", ["চান্দিনা"], "chandina"),
                ("Chauddagram", ["চৌদ্দগ্রাম"], "chauddagram"), ("Daudkandi", ["দাউদকান্দি"], "daudkandi"),
                ("Debidwar", ["দেবিদ্বার"], "debidwar"), ("Homna", ["হোমনা"], "homna"), ("Laksam", ["লাকসাম"], "laksam"),
                ("Lalmai", ["লালমাই"], "lalmai"), ("Manoharganj", ["মনোহরগঞ্জ"], "monohargonj"), ("Meghna", ["মেঘনা"], "meghna"),
                ("Muradnagar", ["মুরাদনগর"], "muradnagar"), ("Nangalkot", ["নাঙ্গলকোট"], "nangalkot"), ("Titas", ["তিতাস"], "titas")],
    "Feni": [("Chhagalnaiya", ["ছাগলনাইয়া"], "chhagalnaiya"), ("Daganbhuiyan", ["দাগনভূঞা", "দাগনভুঞা"], "daganbhuiyan"),
             ("Feni Sadar", ["ফেনী সদর"], "sadar"), ("Fulgazi", ["ফুলগাজী"], "fulgazi"), ("Parashuram", ["পরশুরাম"], "parshuram"),
             ("Sonagazi", ["সোনাগাজী"], "sonagazi")],
    "Brahmanbaria": [("Akhaura", ["আখাউড়া"], "akhaura"), ("Ashuganj", ["আশুগঞ্জ"], "ashuganj"),
                     ("Banchharampur", ["বাঞ্ছারামপুর"], "bancharampur"), ("Bijoynagar", ["বিজয়নগর"], "bijoynagar"),
                     ("Brahmanbaria Sadar", ["ব্রাহ্মণবাড়িয়া সদর"], "sadar"), ("Kasba", ["কসবা"], "kasba"),
                     ("Nabinagar", ["নবীনগর"], "nabinagar"), ("Nasirnagar", ["নাসিরনগর", "নাছিরনগর"], "nasirnagar"),
                     ("Sarail", ["সরাইল"], "sarail")],
    "Rangamati": [("Baghaichhari", ["বাঘাইছড়ি"], "baghaichari"), ("Barkal", ["বরকল"], "barkal"),
                  ("Belaichhari", ["বিলাইছড়ি"], "belaichari"), ("Jurachhari", ["জুরাছড়ি"], "juraichari"),
                  ("Kaptai", ["কাপ্তাই"], "kaptai"), ("Kawkhali", ["কাউখালী"], "kawkhali"), ("Langadu", ["লংগদু"], "langadu"),
                  ("Naniarchar", ["নানিয়ারচর"], "naniarchar"), ("Rajasthali", ["রাজস্থলী"], "rajasthali"),
                  ("Rangamati Sadar", ["রাঙ্গামাটি সদর"], "sadar")],
    "Noakhali": [("Begumganj", ["বেগমগঞ্জ"], "begumganj"), ("Chatkhil", ["চাটখিল"], "chatkhil"),
                 ("Companiganj", ["কোম্পানীগঞ্জ", "কোম্পানিগঞ্জ"], "companiganj"), ("Hatiya", ["হাতিয়া"], "hatia"),
                 ("Kabirhat", ["কবিরহাট"], "kabirhat"), ("Noakhali Sadar", ["নোয়াখালী সদর"], "sadar"), ("Senbag", ["সেনবাগ"], "senbug"),
                 ("Sonaimuri", ["সোনাইমুড়ী", "সোনাইমুড়ি"], "sonaimuri"), ("Subarnachar", ["সুবর্ণচর"], "subarnachar")],
    "Chandpur": [("Chandpur Sadar", ["চাঁদপুর সদর"], "sadar"), ("Faridganj", ["ফরিদগঞ্জ"], "faridgonj"),
                 ("Haimchar", ["হাইমচর"], "haimchar"), ("Hajiganj", ["হাজীগঞ্জ"], "hajiganj"), ("Kachua", ["কচুয়া"], "kachua"),
                 ("Matlab Dakkhin", ["মতলব দক্ষিণ"], "matlabsouth"), ("Matlab Uttar", ["মতলব উত্তর"], "matlabnorth"),
                 ("Shahrasti", ["শাহরাস্তি"], "shahrasti")],
    "Lakshmipur": [("Kamalnagar", ["কমলনগর"], "kamalnagar"), ("Lakshmipur Sadar", ["লক্ষ্মীপুর সদর"], "sadar"),
                   ("Raipur", ["রায়পুর"], "raipur"), ("Ramganj", ["রামগঞ্জ"], "ramganj"), ("Ramgati", ["রামগতি"], "ramgati")],
    "Cox's Bazar": [("Chakaria", ["চকরিয়া"], "chakaria"), ("Coxs Bazar Sadar", ["কক্সবাজার সদর"], "sadar"),
                    ("Eidgaon", ["ঈদগাঁও", "ঈদগাও"], "eidgaon"), ("Kutubdia", ["কুতুবদিয়া"], "kutubdia"),
                    ("Maheshkhali", ["মহেশখালী", "মহেশখালি"], "moheshkhali"), ("Pekua", ["পেকুয়া"], "pekua"), ("Ramu", ["রামু"], "ramu"),
                    ("Teknaf", ["টেকনাফ"], "teknaf"), ("Ukhia", ["উখিয়া"], "ukhiya")],
    "Khagrachhari": [("Dighinala", ["দীঘিনালা", "দিঘীনালা"], "dighinala"), ("Guimara", ["গুইমারা"], "guimara"),
                     ("Khagrachhari Sadar", ["খাগড়াছড়ি সদর"], "sadar"), ("Lakkhichhari", ["লক্ষ্মীছড়ি", "লক্ষীছড়ি"], "laxmichhari"),
                     ("Mahalchhari", ["মহালছড়ি"], "mohalchari"), ("Manikchhari", ["মানিকছড়ি"], "manikchari"),
                     ("Matiranga", ["মাটিরাঙ্গা", "মাটিরাংগা"], "matiranga"), ("Panchhari", ["পানছড়ি"], "panchari"),
                     ("Ramgarh", ["রামগড়"], "ramgarh")],
    "Bandarban": [("Alikadam", ["আলীকদম"], "alikadam"), ("Bandarban Sadar", ["বান্দরবান সদর"], "sadar"), ("Lama", ["লামা"], "lama"),
                  ("Naikkhongchhari", ["নাইক্ষ্যংছড়ি"], "naikhongchhari"), ("Rowangchhari", ["রোয়াংছড়ি"], "rowangchhari"),
                  ("Ruma", ["রুমা"], "ruma"), ("Thanchi", ["থানচি"], "thanchi")],
}
# Chattogram Metropolitan Police thanas (CMP 'এক নজরে' on police.chittagongdiv.gov.bd), English transliterations. 'বন্দর',
# 'ইপিজেড' and 'কর্ণফুলী' are left out here: as words they name the port, export zones and the river far more often than the thanas.
CHATTOGRAM_CITY_THANAS = {"কোতোয়ালী": "Kotwali", "বাকলিয়া": "Bakalia", "চকবাজার": "Chawkbazar", "পাঁচলাইশ": "Panchlaish",
                          "খুলশী": "Khulshi", "বায়েজিদ বোস্তামী": "Bayezid Bostami", "চান্দগাঁও": "Chandgaon", "পতেঙ্গা": "Patenga",
                          "হালিশহর": "Halishahar", "পাহাড়তলী": "Pahartali", "আকবরশাহ": "Akbarshah", "ডবলমুরিং": "Double Mooring",
                          "সদরঘাট": "Sadarghat"}
# Khulna Division names: Bangla -> English (HDX COD-AB v03 spellings). District hosts verified by page title (Nov 2026; jessore.gov.bd
# is the host the Jashore DC portal's own upazila list uses, jashore.gov.bd serves the same site); upazila portal subdomains
# verified by their home-page titles ("হোম | <upazila> উপজেলা").
KHULNA_DISTRICTS = {"খুলনা": "Khulna", "যশোর": "Jashore", "সাতক্ষীরা": "Satkhira", "মেহেরপুর": "Meherpur", "নড়াইল": "Narail",
                    "চুয়াডাঙ্গা": "Chuadanga", "কুষ্টিয়া": "Kushtia", "মাগুরা": "Magura", "বাগেরহাট": "Bagerhat", "ঝিনাইদহ": "Jhenaidah"}
KHULNA_DISTRICT_HOSTS = {"Khulna": "khulna.gov.bd", "Jashore": "jessore.gov.bd", "Satkhira": "satkhira.gov.bd", "Meherpur": "meherpur.gov.bd",
                         "Narail": "narail.gov.bd", "Chuadanga": "chuadanga.gov.bd", "Kushtia": "kushtia.gov.bd", "Magura": "magura.gov.bd",
                         "Bagerhat": "bagerhat.gov.bd", "Jhenaidah": "jhenaidah.gov.bd"}
KHULNA_UPAZILAS = {  # district -> [(english, bangla names/aliases..., portal subdomain)]
    "Khulna": [("Batiaghata", ["বটিয়াঘাটা"], "botiaghata"), ("Dacope", ["দাকোপ"], "dakop"), ("Dumuria", ["ডুমুরিয়া"], "dumuria"),
               ("Dighalia", ["দিঘলিয়া"], "digholia"), ("Koyra", ["কয়রা"], "koyra"), ("Paikgachha", ["পাইকগাছা"], "paikgasa"),
               ("Phultala", ["ফুলতলা"], "fultola"), ("Rupsa", ["রূপসা", "রুপসা"], "rupsha"), ("Terokhada", ["তেরখাদা"], "terokhada")],
    "Jashore": [("Abhaynagar", ["অভয়নগর"], "abhaynagar"), ("Bagharpara", ["বাঘারপাড়া"], "bagherpara"),
                ("Chaugachha", ["চৌগাছা"], "chougachha"), ("Jhikargachha", ["ঝিকরগাছা"], "jhikargacha"),
                ("Keshabpur", ["কেশবপুর"], "keshabpur"), ("Jashore Sadar", ["যশোর সদর"], "sadar"),
                ("Manirampur", ["মণিরামপুর", "মনিরামপুর"], "manirampur"), ("Sharsha", ["শার্শা"], "sharsha")],
    "Satkhira": [("Ashashuni", ["আশাশুনি"], "assasuni"), ("Debhata", ["দেবহাটা"], "debhata"), ("Kalaroa", ["কলারোয়া"], "kalaroa"),
                 ("Kaliganj", ["কালিগঞ্জ", "কালীগঞ্জ"], "kaliganj"), ("Satkhira Sadar", ["সাতক্ষীরা সদর"], "satkhirasadar"),
                 ("Shyamnagar", ["শ্যামনগর"], "shyamnagar"), ("Tala", ["তালা"], "tala")],
    "Meherpur": [("Gangni", ["গাংনী"], "gangni"), ("Mujibnagar", ["মুজিবনগর"], "mujibnagar"),
                 ("Meherpur Sadar", ["মেহেরপুর সদর"], "meherpursadar")],
    "Narail": [("Kalia", ["কালিয়া"], "kalia"), ("Lohagara", ["লোহাগড়া"], "lohagara"), ("Narail Sadar", ["নড়াইল সদর"], "narailsadar")],
    "Chuadanga": [("Alamdanga", ["আলমডাঙ্গা", "আলমডাঙা"], "alamdanga"), ("Chuadanga Sadar", ["চুয়াডাঙ্গা সদর"], "chuadangasadar"),
                  ("Damurhuda", ["দামুড়হুদা", "দামূড়হুদা"], "damurhuda"), ("Jibannagar", ["জীবননগর"], "jibannagar")],
    "Kushtia": [("Bheramara", ["ভেড়ামারা"], "bheramara"), ("Daulatpur", ["দৌলতপুর"], "daulatpur"), ("Khoksa", ["খোকসা"], "khoksa"),
                ("Kumarkhali", ["কুমারখালী", "কুমারখালি"], "kumarkhali"), ("Kushtia Sadar", ["কুষ্টিয়া সদর"], "kushtiasadar"),
                ("Mirpur", ["মিরপুর"], "mirpur")],
    "Magura": [("Magura Sadar", ["মাগুরা সদর"], "magurasadar"), ("Mohammadpur", ["মহম্মদপুর", "মোহাম্মদপুর"], "mohammadpur"),
               ("Shalikha", ["শালিখা"], "shalikha"), ("Sreepur", ["শ্রীপুর"], "sreepur")],
    "Bagerhat": [("Bagerhat Sadar", ["বাগেরহাট সদর"], "sadar"), ("Chitalmari", ["চিতলমারী"], "chitalmari"), ("Fakirhat", ["ফকিরহাট"], "fakirhat"),
                 ("Kachua", ["কচুয়া"], "kachua"), ("Mollahat", ["মোল্লাহাট"], "mollahat"), ("Mongla", ["মোংলা", "মংলা"], "mongla"),
                 ("Morelganj", ["মোড়েলগঞ্জ", "মোরেলগঞ্জ"], "morrelganj"), ("Rampal", ["রামপাল"], "rampal"),
                 ("Sharankhola", ["শরণখোলা"], "sarankhola")],
    "Jhenaidah": [("Harinakundu", ["হরিণাকুন্ডু", "হরিণাকুণ্ডু"], "harinakundu"), ("Jhenaidah Sadar", ["ঝিনাইদহ সদর"], "sadar"),
                  ("Kaliganj", ["কালীগঞ্জ", "কালিগঞ্জ"], "kaliganj"), ("Kotchandpur", ["কোটচাঁদপুর"], "kotchandpur"),
                  ("Maheshpur", ["মহেশপুর"], "moheshpur"), ("Shailkupa", ["শৈলকুপা"], "shailkupa")],
}
# Khulna Metropolitan Police thanas (Khulna DC portal 'ভৌগলিক পরিচিতি' list of 8 'মেট্রোপলিটন থানা'), English: HDX COD-AB spellings
# where HDX has the thana (Daulatpur, Khalishpur, Khan Jahan Ali, Khulna Sadar, Sonadanga), else a transliteration. The DC portal
# calls Khulna Sadar 'কোতয়ালী থানা' (KMP: 'খুলনা থানা'); 'খুলনা' itself is not matched.
KHULNA_CITY_THANAS = {"দৌলতপুর": "Daulatpur", "খালিশপুর": "Khalishpur", "খানজাহান আলী": "Khan Jahan Ali", "খানজাহানআলী": "Khan Jahan Ali",
                      "সোনাডাঙ্গা": "Sonadanga", "কোতয়ালী": "Khulna Sadar", "আড়ংঘাটা": "Aranghata", "হরিণটানা": "Harintana",
                      "হড়িণটানা": "Harintana", "লবণচরা": "Labanchara", "লবনচড়া": "Labanchara"}

# Barishal Division names: Bangla -> English (district names as in the seed; upazila names in common BBS/HDX-style spelling, the
# importer matches them by similarity). District hosts verified by page title (Nov 2026): barisal.gov.bd is the host the Barishal
# DC portal's own upazila list uses (barishal.gov.bd serves the same site); jhalakathi.gov.bd is the Jhalokathi DC portal
# (jhalokathi.gov.bd does not resolve). Upazila portal subdomains verified by their home-page titles ("হোম | <upazila> উপজেলা").
BARISHAL_DISTRICTS = {"বরিশাল": "Barishal", "ঝালকাঠি": "Jhalokathi", "পটুয়াখালী": "Patuakhali", "পিরোজপুর": "Pirojpur", "ভোলা": "Bhola",
                      "বরগুনা": "Barguna"}
BARISHAL_DISTRICT_HOSTS = {"Barishal": "barisal.gov.bd", "Jhalokathi": "jhalakathi.gov.bd", "Patuakhali": "patuakhali.gov.bd",
                           "Pirojpur": "pirojpur.gov.bd", "Bhola": "bhola.gov.bd", "Barguna": "barguna.gov.bd"}
BARISHAL_UPAZILAS = {  # district -> [(english, bangla names/aliases..., portal subdomain)]
    "Barishal": [("Barishal Sadar", ["বরিশাল সদর"], "barisalsadar"), ("Bakerganj", ["বাকেরগঞ্জ"], "bakerganj"),
                 ("Babuganj", ["বাবুগঞ্জ"], "babuganj"), ("Wazirpur", ["উজিরপুর"], "wazirpur"),
                 ("Banaripara", ["বানারীপাড়া", "বানারিপাড়া"], "banaripara"), ("Gaurnadi", ["গৌরনদী", "গৌরনদি"], "gournadi"),
                 ("Agailjhara", ["আগৈলঝাড়া"], "agailjhara"), ("Mehendiganj", ["মেহেন্দিগঞ্জ"], "mehendiganj"),
                 ("Muladi", ["মুলাদী", "মুলাদি"], "muladi"), ("Hizla", ["হিজলা"], "hizla")],
    "Jhalokathi": [("Jhalokathi Sadar", ["ঝালকাঠি সদর"], "sadar"), ("Kathalia", ["কাঠালিয়া", "কাঁঠালিয়া"], "kathalia"),
                   ("Nalchity", ["নলছিটি"], "nalchity"), ("Rajapur", ["রাজাপুর"], "rajapur")],
    "Patuakhali": [("Patuakhali Sadar", ["পটুয়াখালী সদর"], "sadar"), ("Bauphal", ["বাউফল"], "bauphal"), ("Dumki", ["দুমকী", "দুমকি"], "dumki"),
                   ("Dashmina", ["দশমিনা"], "dashmina"), ("Kalapara", ["কলাপাড়া"], "kalapara"), ("Mirzaganj", ["মির্জাগঞ্জ"], "mirzaganj"),
                   ("Galachipa", ["গলাচিপা"], "galachipa"), ("Rangabali", ["রাঙ্গাবালী", "রাঙাবালী", "রাঙ্গাবালি"], "rangabali")],
    "Pirojpur": [("Pirojpur Sadar", ["পিরোজপুর সদর"], "sadar"), ("Nazirpur", ["নাজিরপুর"], "nazirpur"), ("Kawkhali", ["কাউখালী", "কাউখালি"], "kawkhali"),
                 ("Zianagar", ["জিয়ানগর", "ইন্দুরকানী"], "zianagar"), ("Bhandaria", ["ভান্ডারিয়া", "ভাণ্ডারিয়া"], "bhandaria"),
                 ("Mathbaria", ["মঠবাড়ীয়া", "মঠবাড়িয়া"], "mathbaria"), ("Nesarabad", ["নেছারাবাদ", "স্বরূপকাঠি"], "nesarabad")],
    "Bhola": [("Bhola Sadar", ["ভোলা সদর"], "sadar"), ("Burhanuddin", ["বোরহানউদ্দিন", "বোরহান উদ্দিন"], "borhanuddin"),
              ("Char Fasson", ["চরফ্যাশন"], "charfesson"), ("Daulatkhan", ["দৌলতখান"], "doulatkhan"), ("Manpura", ["মনপুরা"], "monpura"),
              ("Tazumuddin", ["তজুমদ্দিন"], "tazumuddin"), ("Lalmohan", ["লালমোহন"], "lalmohan")],
    "Barguna": [("Barguna Sadar", ["বরগুনা সদর"], "sadar"), ("Amtali", ["আমতলী", "আমতলি"], "amtali"), ("Betagi", ["বেতাগী", "বেতাগি"], "betagi"),
                ("Bamna", ["বামনা"], "bamna"), ("Patharghata", ["পাথরঘাটা"], "pathorghata"), ("Taltali", ["তালতলী", "তালতলি"], "taltali")],
}
# Barishal Metropolitan Police thanas (bmp.police.gov.bd thana pages: Kotwali Model, Bandar, Kaunia, Airport). Only the unambiguous
# names are matched in office names: 'বন্দর' (also 'নদী বন্দর', river port) and 'এয়ারপোর্ট' are not.
BARISHAL_CITY_THANAS = {"কোতয়ালী": "Kotwali", "কোতোয়ালী": "Kotwali", "কোতোয়ালি": "Kotwali", "কাউনিয়া": "Kaunia"}
# Sylhet Division names: Bangla -> English (district names as in the seed; upazila names as the seed spells them, the importer
# matches them by similarity). District hosts verified by page title (Nov 2026: 'হোম | <জেলা> জেলা'). Upazila portal subdomains
# from the national portal's office registry (bangladesh.gov.bd/views/union-list), verified by their home-page titles. The new
# Shantiganj upazila (শান্তিগঞ্জ, formerly দক্ষিণ সুনামগঞ্জ) is the seed's South Sunamganj; Madhyanagar is new (2022).
SYLHET_DISTRICTS = {"সিলেট": "Sylhet", "মৌলভীবাজার": "Moulvibazar", "হবিগঞ্জ": "Habiganj", "সুনামগঞ্জ": "Sunamganj"}
SYLHET_DISTRICT_HOSTS = {"Sylhet": "sylhet.gov.bd", "Moulvibazar": "moulvibazar.gov.bd", "Habiganj": "habiganj.gov.bd",
                         "Sunamganj": "sunamganj.gov.bd"}
SYLHET_UPAZILAS = {  # district -> [(english, bangla names/aliases..., portal subdomain)]
    "Sylhet": [("Sylhet Sadar", ["সিলেট সদর"], "sylhetsadar"), ("Beanibazar", ["বিয়ানীবাজার"], "beanibazar"),
               ("Bishwanath", ["বিশ্বনাথ"], "bishwanath"), ("Companiganj", ["কোম্পানীগঞ্জ", "কোম্পানিগঞ্জ"], "companiganj"),
               ("Fenchuganj", ["ফেঞ্চুগঞ্জ"], "fenchuganj"), ("Golapganj", ["গোলাপগঞ্জ"], "golapganj"),
               ("Gowainghat", ["গোয়াইনঘাট"], "gowainghat"), ("Jaintiapur", ["জৈন্তাপুর"], "jaintiapur"),
               ("Kanaighat", ["কানাইঘাট"], "kanaighat"), ("Zakiganj", ["জকিগঞ্জ"], "zakiganj"), ("Balaganj", ["বালাগঞ্জ"], "balaganj"),
               ("Dakshinsurma", ["দক্ষিণ সুরমা"], "dakshinsurma"), ("Osmaninagar", ["ওসমানী নগর", "ওসমানীনগর"], "osmaninagar")],
    "Moulvibazar": [("Moulvibazar Sadar", ["মৌলভীবাজার সদর"], "moulvibazarsadar"), ("Barlekha", ["বড়লেখা"], "barlekha"),
                    ("Juri", ["জুড়ী", "জুড়ি"], "juri"), ("Kamolganj", ["কমলগঞ্জ"], "kamolganj"), ("Kulaura", ["কুলাউড়া"], "kulaura"),
                    ("Rajnagar", ["রাজনগর"], "rajnagar"), ("Sreemangal", ["শ্রীমঙ্গল", "শ্রীমংগল"], "sreemangal")],
    "Habiganj": [("Habiganj Sadar", ["হবিগঞ্জ সদর"], "habiganjsadar"), ("Ajmiriganj", ["আজমিরীগঞ্জ"], "ajmiriganj"),
                 ("Bahubal", ["বাহুবল"], "bahubal"), ("Baniachong", ["বানিয়াচং"], "baniachong"), ("Chunarughat", ["চুনারুঘাট"], "chunarughat"),
                 ("Lakhai", ["লাখাই"], "lakhai"), ("Madhabpur", ["মাধবপুর"], "madhabpur"), ("Nabiganj", ["নবীগঞ্জ"], "nabiganj"),
                 ("Shayestaganj", ["শায়েস্তাগঞ্জ"], "shayestaganj")],
    "Sunamganj": [("Sunamganj Sadar", ["সুনামগঞ্জ সদর"], "sadar"), ("South Sunamganj", ["শান্তিগঞ্জ", "দক্ষিণ সুনামগঞ্জ"], "shantiganj"),
                  ("Bishwambarpur", ["বিশ্বম্ভরপুর"], "bishwambarpur"), ("Chhatak", ["ছাতক"], "chhatak"), ("Derai", ["দিরাই"], "derai"),
                  ("Dharmapasha", ["ধর্মপাশা"], "dharmapasha"), ("Dowarabazar", ["দোয়ারাবাজার"], "dowarabazar"),
                  ("Jagannathpur", ["জগন্নাথপুর"], "jagannathpur"), ("Jamalganj", ["জামালগঞ্জ"], "jamalganj"), ("Shalla", ["শাল্লা"], "shalla"),
                  ("Tahirpur", ["তাহিরপুর"], "tahirpur"), ("Madhyanagar", ["মধ্যনগর"], "madhyanagar")],
}
# Sylhet Metropolitan Police thanas (smp.police.gov.bd: Kotwali Model, Jalalabad, Airport, Moglabazar, Shahparan, Dakshin Surma).
# Only Kotwali is matched in office names: জালালাবাদ and মোগলাবাজার are also union names (and Jalalabad Gas), শাহপরান names
# shrines and institutions, দক্ষিণ সুরমা is also the upazila, and 'এয়ারপোর্ট' the airport.
SYLHET_CITY_THANAS = {"কোতয়ালী": "Kotwali", "কোতোয়ালী": "Kotwali", "কোতোয়ালি": "Kotwali"}
# The Sylhet DC portal (sylhet.gov.bd and its *.sylhet.gov.bd sub-sites) sends only its leaf certificate (Let's Encrypt YR1).
# As for the Sectigo intermediates above, the CA-published intermediates (AIA 'CA Issuers' URLs: YR1, and Root YR cross-signed by
# ISRG Root X1) are added to the bundle for Sylhet runs; TLS verification stays on. Rajshahi runs keep the original bundle.
SYLHET_INTERMEDIATES = ["http://yr1.i.lencr.org/", "http://yr.i.lencr.org/"]
# Mymensingh Division names: Bangla -> English (district and upazila names as the seed spells them: Nokla, Sreebordi, Bokshiganj,
# Dewangonj, Mohongonj, Tarakanda …). District hosts verified by page title (Nov 2026: 'হোম | <জেলা> জেলা'); the 35 upazila portal
# subdomains are the seed's and were verified by their home-page titles ('হোম | <উপজেলা> উপজেলা'). The Bangla names are NFC-normalised
# here (ড়/য় are composition exclusions). The certificates of these hosts are Sectigo DV R36, whose intermediate is already above.
_MYM_UPAZILAS = {  # district -> [(english, bangla names/aliases..., portal subdomain)]
    "Mymensingh": [("Mymensingh Sadar", ["ময়মনসিংহ সদর"], "mymensinghsadar"), ("Muktagacha", ["মুক্তাগাছা"], "muktagacha"),
                   ("Fulbaria", ["ফুলবাড়ীয়া", "ফুলবাড়িয়া", "ফুলবাড়ীয়া"], "fulbaria"), ("Trishal", ["ত্রিশাল"], "trishal"),
                   ("Bhaluka", ["ভালুকা"], "bhaluka"), ("Gafargaon", ["গফরগাঁও"], "gafargaon"), ("Nandail", ["নান্দাইল"], "nandail"),
                   ("Iswarganj", ["ঈশ্বরগঞ্জ"], "iswarganj"), ("Gouripur", ["গৌরীপুর"], "gouripur"), ("Phulpur", ["ফুলপুর"], "phulpur"),
                   ("Tarakanda", ["তারাকান্দা"], "tarakanda"), ("Haluaghat", ["হালুয়াঘাট"], "haluaghat"),
                   ("Dhobaura", ["ধোবাউড়া", "ধোবাউরা"], "dhobaura")],
    "Jamalpur": [("Jamalpur Sadar", ["জামালপুর সদর"], "jamalpursadar"), ("Melandah", ["মেলান্দহ"], "melandah"),
                 ("Islampur", ["ইসলামপুর"], "islampur"), ("Dewangonj", ["দেওয়ানগঞ্জ"], "dewangonj"),
                 ("Sarishabari", ["সরিষাবাড়ী", "সরিষাবাড়ি"], "sarishabari"), ("Madarganj", ["মাদারগঞ্জ"], "madarganj"),
                 ("Bokshiganj", ["বকশীগঞ্জ", "বকশিগঞ্জ"], "bokshiganj")],
    "Sherpur": [("Sherpur Sadar", ["শেরপুর সদর"], "sherpursadar"), ("Nalitabari", ["নালিতাবাড়ী", "নালিতাবাড়ি"], "nalitabari"),
                ("Sreebordi", ["শ্রীবরদী"], "sreebordi"), ("Nokla", ["নকলা"], "nokla"), ("Jhenaigati", ["ঝিনাইগাতী"], "jhenaigati")],
    "Netrokona": [("Netrokona Sadar", ["নেত্রকোণা সদর", "নেত্রকোনা সদর"], "netrokonasadar"), ("Barhatta", ["বারহাট্টা"], "barhatta"),
                  ("Durgapur", ["দুর্গাপুর"], "durgapur"), ("Kendua", ["কেন্দুয়া"], "kendua"), ("Atpara", ["আটপাড়া"], "atpara"),
                  ("Madan", ["মদন"], "madan"), ("Khaliajuri", ["খালিয়াজুরী", "খালিয়াজুড়ি"], "khaliajuri"),
                  ("Kalmakanda", ["কলমাকান্দা"], "kalmakanda"), ("Mohongonj", ["মোহনগঞ্জ"], "mohongonj"),
                  ("Purbadhala", ["পূর্বধলা"], "purbadhala")],
}
MYMENSINGH_UPAZILAS = {d: [(en, list(dict.fromkeys(unicodedata.normalize("NFC", b) for b in bns)), sub) for en, bns, sub in ups]
                       for d, ups in _MYM_UPAZILAS.items()}
MYMENSINGH_DISTRICTS = {unicodedata.normalize("NFC", k): v for k, v in
                        {"ময়মনসিংহ": "Mymensingh", "জামালপুর": "Jamalpur", "শেরপুর": "Sherpur", "নেত্রকোণা": "Netrokona"}.items()}
MYMENSINGH_DISTRICT_HOSTS = {"Mymensingh": "mymensingh.gov.bd", "Jamalpur": "jamalpur.gov.bd", "Sherpur": "sherpur.gov.bd",
                             "Netrokona": "netrokona.gov.bd"}
# No Mymensingh Metropolitan Police: police.gov.bd lists eight metropolitan units (DMP, CMP, BMP, KMP, RMP, SMP, RPMP, GMP) and its
# Mymensingh Range page counts Kotwali among Mymensingh District's police stations. No office name is mapped to a metro thana.
MYMENSINGH_CITY_THANAS = {}

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


def sp_office_row(key, dist, dist_bn, sid, host=None):
    """SP office from the office head's officer card on police.<district>.gov.bd (or the given host)."""
    base = "https://%s/" % (host or "police.%s.gov.bd" % dist.lower())
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
    if len(parts) >= 2 and parts[0] in ("থানা", "উপজেলা থানা"):   # 'উপজেলা থানা, নগরকান্দা, ফরিদপুর' (Dhaka Division)
        name = parts[1] + " থানা"
    elif len(parts) >= 2 and parts[1] == "থানা":
        name = parts[0] + " থানা"
    elif parts and "থানা" in parts[0] and parts[0] not in ("থানা", "Thana"):   # a bare 'থানা' title carries no name
        name = parts[0]
    elif any(p.endswith("থানা") for p in parts[1:]):            # 'বাংলাদেশ পুলিশ, গজারিয়া থানা'
        name = next(p for p in parts[1:] if p.endswith("থানা"))
    if name and name.startswith("সদর "):
        name = dist_bn + " " + name
    return nfc(name) if name else None


def thana_row_from_portal(key, dist, dist_bn, upa_en, upa_bn, host, sid, listed_on=None):
    base = "https://%s/" % host
    home = fetch_html(base)
    if not home:
        return None, "portal %s did not respond" % host
    title = page_title(home)
    if title.startswith("Site is not available"):   # framework placeholder for a portal that is not set up
        return None, "portal %s: %r" % (host, title)
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


# --- Dhaka District Police (police.dhaka.gov.bd; Dhaka city is policed by DMP, see DHAKA_METRO_POLICE_THANAS_2026) ----
DP_KEY = "DHAKA_POLICE_2026"
DP_CONTACT = "https://police.dhaka.gov.bd/pages/static-pages/6995a2a635ce18e1c078e851"     # যোগাযোগ (SP office address)
DP_DC_GLANCE = "https://dhaka.gov.bd/pages/static-pages/6995bedb35ce18e1c079f6b8"          # DC portal 'এক নজরে ঢাকা জেলা' (থানার সংখ্যা)


def main_dhaka():
    places, facts, missing = [], [], []
    sp = sp_office_row(DP_KEY, "Dhaka", "ঢাকা", "dhkpol-sp-office")
    t = fetch_html(DP_CONTACT)
    if sp and t:
        txt = " ".join(content_text(t))
        save_raw("dhaka_police_contact.txt", "\n".join(content_text(t)))
        m = re.search(r"পুলিশ সুপারের কার্যালয়, ঢাকা\s*\|?\s*([০-৯0-9]+, জনসন রোড)", txt)
        ph = re.search(r"ফোন-\s*([০-৯0-9\-]+)", txt)
        if m:
            sp["address"] = m.group(1)
        ex = json.loads(sp["extra_json"] or "{}")
        if ph:
            ex["contact_page_phone"] = asc(ph.group(1)).rstrip("-")
        ex["address_source"] = DP_CONTACT if m else None
        sp["extra_json"] = xj(ex)
        sp["notes"] += " Address and a second (older-format) office number from the portal's 'যোগাযোগ' page."
    if sp:
        places.append(sp)
    else:
        missing.append("police.dhaka.gov.bd")
    t = fetch_html(DP_DC_GLANCE)
    if t:
        txt = " ".join(content_text(t))
        m = re.search(r"মোট\s*([০-৯0-9]+)টি\s*\(([০-৯0-9]+)টি সিটি কর্পোরেশন এলাকায়,\s*([০-৯0-9]+)টি উপজেলা এলাকায়\)", txt)
        if m:
            save_raw("dhaka_dc_glance_thanas.txt", "URL: %s\n\n%s" % (DP_DC_GLANCE, m.group(0)))
            facts.append(dict(entity_level="district", entity_name_en="Dhaka", district_en="Dhaka", fact="police_stations",
                              value=int(asc(m.group(3))), unit="thanas", basis="reported", year=2026, source_key=DP_KEY,
                              source_url=DP_DC_GLANCE, notes="DC portal 'এক নজরে ঢাকা জেলা': %s — thanas in the upazila area "
                              "(Dhaka District Police); the %s city-corporation-area thanas are DMP's." % (m.group(0), asc(m.group(2)))))
    for en, bns, sub in DHAKA_UPAZILAS["Dhaka"]:
        rec, err = thana_row_from_portal(DP_KEY, "Dhaka", "ঢাকা", en, bns[0], "police.%s.dhaka.gov.bd" % sub,
                                         "dhkpol-%s" % en.lower().replace(" ", "-"))
        if rec:
            places.append(rec)
        else:
            missing.append(err)
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    if missing:
        print("unavailable:", missing)
    write_manifest(dict(
        key=DP_KEY, division="dhaka", kind="district_police",
        name="Dhaka District Police — SP office and thanas", organization="Dhaka District Police (Bangladesh Police)",
        source_type="government_portal", trust_level=4,
        urls=["https://police.dhaka.gov.bd/", DP_CONTACT, DP_DC_GLANCE, "https://police.<upazila>.dhaka.gov.bd/"],
        accessed=__import__("datetime").date.today().isoformat(), publication_date=None, license=None, license_url=None,
        attribution="Office of the Superintendent of Police, Dhaka (police.dhaka.gov.bd), the thana portals and the Dhaka DC portal",
        notes="No licence stated. police.dhaka.gov.bd publishes no thana list or contact table; SP office from the Superintendent's "
              "officer card (+ address from 'যোগাযোগ'), thanas from the 5 upazila thana portals' officer cards (office landline, OC's "
              "police official mobile, *.gov.bd e-mail). Personal e-mails, other mobiles and officers' names are not copied. The DC "
              "portal gives 7 thanas in the upazila area; Ashulia and South Keraniganj thana portals (police.ashulia.dhaka.gov.bd, "
              "police.southkeraniganj.dhaka.gov.bd) failed TLS verification and are not included."
              + (" Unavailable this run: " + "; ".join(missing) if missing else "")),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))

# --- Chattogram District Police (police.chittagong.gov.bd + chattogramdistrict.police.gov.bd; Chattogram city is policed by CMP,
# see CHATTOGRAM_METRO_POLICE_THANAS_2026) -------------------------------------------------------------------------------------
CP_KEY = "CHATTOGRAM_POLICE_2026"
CP_PORTAL = "police.chittagong.gov.bd"            # national-portal site of the SP office (police.chattogram.gov.bd serves the same)
CP_CONTACT = "https://police.chittagong.gov.bd/pages/static-pages/699149ac516a96d4de416ce6"   # যোগাযোগ (SP office address)
CP_SITE = "https://chattogramdistrict.police.gov.bd"   # Bangladesh Police site of the district: one page per thana
CP_THANA_PAGES = range(255, 271)                       # /content/255.html … /content/270.html (the 16 thanas of the menu)
CP_DC_GLANCE = "https://chittagong.gov.bd/pages/static-pages/6990c75635ce18e1c07176a0"   # DC portal 'এক নজরে চট্টগ্রাম' (thana lists)


def police_site_page(url):
    """chattogramdistrict.police.gov.bd page -> (heading, lines of the page body)."""
    t = fetch_html(url)
    if not t:
        return None, []
    lines = content_text(t)
    try:   # the body follows the last menu item 'যোগাযোগ' and ends before the footer links
        a = max(i for i, l in enumerate(lines) if l == "যোগাযোগ")
        b = next(i for i, l in enumerate(lines) if l.startswith("All Cadre"))
        lines = lines[a + 1:b]
    except (ValueError, StopIteration):
        pass
    return (lines[0] if lines else None), lines


def main_chattogram():
    places, facts, missing = [], [], []
    sp = sp_office_row(CP_KEY, "Chattogram", "চট্টগ্রাম", "ctgpol-sp-office", host=CP_PORTAL)
    t = fetch_html(CP_CONTACT)
    if sp and t:
        lines = content_text(t)
        save_raw("chattogram_police_contact.txt", "URL: %s\n\n%s" % (CP_CONTACT, "\n".join(lines)))
        m = re.search(r"([০-৯0-9]+ পূর্ব নাসিরাবাদ, ২ নং গেইট চট্টগ্রাম)", " ".join(lines))
        if m:
            sp["address"] = m.group(1)
            ex = json.loads(sp["extra_json"] or "{}")
            ex["address_source"] = CP_CONTACT
            sp["extra_json"] = xj(ex)
            sp["notes"] += " Address from the portal's 'যোগাযোগ' page."
    if sp:
        places.append(sp)
    else:
        missing.append(CP_PORTAL)
    t = fetch_html(CP_DC_GLANCE)
    if t:
        txt = " ".join(content_text(t))
        m1 = re.search(r"উপজেলা পর্যায়ে-\s*([০-৯0-9]+)টি\s*\|?\s*([^|]+?)।", txt)
        m2 = re.search(r"মহানগর-\s*([০-৯0-9]+)টি\s*\|?\s*([^|]+?)।", txt)
        save_raw("chattogram_dc_glance_thanas.txt", "URL: %s\n\n%s\n%s" % (CP_DC_GLANCE, m1.group(0) if m1 else "", m2.group(0) if m2 else ""))
        if m1:
            facts.append(dict(entity_level="district", entity_name_en="Chattogram", district_en="Chattogram", fact="police_stations",
                              value=int(asc(m1.group(1))), unit="thanas", basis="reported", year=2026, source_key=CP_KEY,
                              source_url=CP_DC_GLANCE, notes="DC portal 'এক নজরে চট্টগ্রাম', থানা উপজেলা পর্যায়ে: %s (Chattogram District "
                              "Police). %s" % (m1.group(2).strip(), ("The %s metropolitan thanas (মহানগর) are CMP's." % asc(m2.group(1))) if m2 else "")))
    up_of = {bn: en for en, bns, sub in CHATTOGRAM_UPAZILAS["Chattogram"] for bn in bns}
    up_of.update({"সীতাকুণ্ড": "Sitakunda", "রাংগুনিয়া": "Rangunia"})
    sub_of = {en: sub for en, bns, sub in CHATTOGRAM_UPAZILAS["Chattogram"]}
    raw, n = [], 0
    for p in CP_THANA_PAGES:
        url = "%s/content/%d.html" % (CP_SITE, p)
        head, lines = police_site_page(url)
        if not head or not head.endswith("থানা"):
            missing.append(url)
            continue
        n += 1
        name = nfc(head)
        base = re.sub(r"\s*(মডেল )?থানা$", "", name).strip()
        up = up_of.get(base, "")
        oc = []
        for i, l in enumerate(lines):
            if l.startswith("অফিসার ইনচার্জ") or l.startswith("অফিসার ইন-চার্জ"):
                oc = official_mobiles(*lines[i + 1:i + 4]) or official_mobiles(l)
                break
        raw.append("%s | %s | OC official mobile: %s" % (url, name, "; ".join(oc) or "-"))
        rec = dict(source_key=CP_KEY, source_id="ctgpol-%s" % (up.lower().replace(" ", "-") or "page-%d" % p), name_bn=name, name_en="",
                   category_key="emergency.police_station", district_en="Chattogram", upazila_en=up, phone="; ".join(oc[:1]),
                   operator="চট্টগ্রাম জেলা পুলিশ", ownership="public",
                   extra_json=xj({"oc_official_mobile": oc[0] if oc else "", "police_site_page": url}), source_url=url,
                   notes="Thana page of the Chattogram District Police site (chattogramdistrict.police.gov.bd): the officer-in-charge's "
                         "police official mobile; officers' names and other numbers not copied" +
                         ("" if up else "; thana is not an upazila (upazila_en empty)") + ("" if oc else "; no OC number on the page"))
        if up:   # the upazila's thana portal: office landline and *.gov.bd e-mail
            prow, err = thana_row_from_portal(CP_KEY, "Chattogram", "চট্টগ্রাম", up, base, "police.%s.chittagong.gov.bd" % sub_of[up], rec["source_id"])
            if prow:
                ex = json.loads(rec["extra_json"] or "{}")
                pex = json.loads(prow["extra_json"] or "{}")
                ex.update({"thana_portal": prow["website"], "portal_title": pex.get("portal_title"), "office_landline": pex.get("office_landline"),
                           "portal_oc_official_mobile": pex.get("oc_official_mobile") if pex.get("oc_official_mobile") not in oc else None})
                rec["extra_json"] = xj(ex)
                rec["website"] = prow["website"]
                rec["email"] = prow["email"]
                lls = [x for x in (pex.get("office_landline") or "").split("; ") if x]
                bad = [x for x in lls if OFFICIAL_MOBILE.match("01" + x[1:])]   # '0320107605': an official mobile missing its '1'
                lls = [x for x in lls if x not in bad]
                ex["office_landline"] = "; ".join(lls) or None
                rec["extra_json"] = xj(ex)
                if bad:
                    ex["portal_number_not_used"] = "; ".join(bad)
                    rec["extra_json"] = xj(ex)
                    rec["notes"] += "; the portal's 'office' number %s looks like a mistyped police mobile and is not used" % ", ".join(bad)
                rec["phone"] = "; ".join(x for x in dict.fromkeys(oc[:1] + lls) if x)
                if not oc and pex.get("oc_official_mobile"):
                    rec["phone"] = "; ".join(x for x in [rec["phone"], pex["oc_official_mobile"]] if x)
                rec["notes"] += "; office landline and e-mail from the thana portal %s (cards may be outdated)" % prow["website"]
            else:
                missing.append(err)
        places.append(rec)
    save_raw("chattogram_police_thana_pages.txt", "\n".join(raw))
    if n:
        facts.append(dict(entity_level="district", entity_name_en="Chattogram", district_en="Chattogram", fact="police_stations", value=n,
                          unit="thanas", basis="listed", year=2026, source_key=CP_KEY, source_url=CP_SITE + "/",
                          notes="Thana pages in the 'জেলা পুলিশ' menu of chattogramdistrict.police.gov.bd"))
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    if missing:
        print("unavailable:", missing)
    write_manifest(dict(
        key=CP_KEY, division="chattogram", kind="district_police",
        name="Chattogram District Police — SP office and thanas", organization="Chattogram District Police (Bangladesh Police)",
        source_type="government_portal", trust_level=4,
        urls=["https://%s/" % CP_PORTAL, CP_CONTACT, CP_SITE + "/", CP_SITE + "/content/<255-270>.html", CP_DC_GLANCE,
              "https://police.<upazila>.chittagong.gov.bd/"],
        accessed=__import__("datetime").date.today().isoformat(), publication_date=None, license=None, license_url=None,
        attribution="Office of the Superintendent of Police, Chattogram (police.chittagong.gov.bd, chattogramdistrict.police.gov.bd), "
                    "the thana portals and the Chattogram DC portal",
        notes="No licence stated. SP office from the Superintendent's officer card on police.chittagong.gov.bd (+ address from "
              "'যোগাযোগ'); the 16 district thanas from the Bangladesh Police site chattogramdistrict.police.gov.bd (one page per thana "
              "with the OC's police official mobile), enriched with the office landline and *.gov.bd e-mail of the upazila thana "
              "portals police.<upazila>.chittagong.gov.bd. Personal e-mails, other mobiles and officers' names are not copied. "
              "Chattogram city is policed by CMP (CHATTOGRAM_METRO_POLICE_THANAS_2026); police.karnafuli.chittagong.gov.bd belongs to "
              "CMP's Karnaphuli thana and is not used here." + (" Unavailable this run: " + "; ".join(missing) if missing else "")),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


# --- Khulna District Police (police.khulna.gov.bd; Khulna city is policed by KMP, see KHULNA_METRO_POLICE_THANAS_2026) ---------
KP_KEY = "KHULNA_POLICE_2026"
KP_GLANCE = "https://police.khulna.gov.bd/pages/static-pages/69810d9ea31054345f1dd4bb"   # এক নজরে (office description only)
# thana portal subdomain where it differs from the UNO portal's: police.dakop.khulna.gov.bd fails the TLS handshake,
# police.dacope.khulna.gov.bd is titled 'দাকোপ থানা, খুলনা' (the DC portal's land-office link also uses 'dacope')
KP_POLICE_SUB = {"Dacope": "dacope"}


def main_khulna():
    places, facts, missing = [], [], []
    sp = sp_office_row(KP_KEY, "Khulna", "খুলনা", "khlpol-sp-office")
    if sp:
        places.append(sp)
    else:
        missing.append("police.khulna.gov.bd")
    for en, bns, sub in KHULNA_UPAZILAS["Khulna"]:
        rec, err = thana_row_from_portal(KP_KEY, "Khulna", "খুলনা", en, bns[0], "police.%s.khulna.gov.bd" % KP_POLICE_SUB.get(en, sub),
                                         "khlpol-%s" % en.lower().replace(" ", "-"))
        if rec:
            if rec["name_bn"] in ("মডেল থানা", "থানা"):
                rec["name_bn"] = "%s %s" % (bns[0], rec["name_bn"])
                rec["notes"] += "; portal title names no thana; name composed from the upazila"
            places.append(rec)
        else:
            missing.append(err)
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    if missing:
        print("unavailable:", missing)
    write_manifest(dict(
        key=KP_KEY, division="khulna", kind="district_police",
        name="Khulna District Police — SP office and thanas", organization="Khulna District Police (Bangladesh Police)",
        source_type="government_portal", trust_level=4,
        urls=["https://police.khulna.gov.bd/", KP_GLANCE, "https://police.<upazila>.khulna.gov.bd/"],
        accessed=__import__("datetime").date.today().isoformat(), publication_date=None, license=None, license_url=None,
        attribution="Office of the Superintendent of Police, Khulna (police.khulna.gov.bd) and the thana portals",
        notes="No licence stated. police.khulna.gov.bd publishes no thana list, thana count or contact table (its 'এক নজরে' describes "
              "the office building; 'ডাক যোগাযোগ' gives no street address); SP office from the Superintendent's officer card, thanas "
              "from the 9 upazila thana portals' officer cards (office landline, OC's police official mobile, *.gov.bd e-mail). "
              "Personal e-mails, other mobiles and officers' names are not copied. Dacope's thana portal is police.dacope.khulna.gov.bd "
              "(police.dakop.khulna.gov.bd fails the TLS handshake). Khulna city is policed by KMP (KHULNA_METRO_POLICE_THANAS_2026)." + (" Unavailable this run: " + "; ".join(missing) if missing else "")),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


# --- Barishal District Police (police.barisal.gov.bd; Barishal city is policed by BMP, see BARISHAL_METRO_POLICE_THANAS_2026) -----
BP_KEY = "BARISHAL_POLICE_2026"
BP_CONTACT = "https://police.barisal.gov.bd/pages/static-pages/69789ba035ce18e1c066f78a"   # যোগাযোগ (contact table, updated 2018)
BP_POSTAL = "https://police.barisal.gov.bd/pages/static-pages/postal-communication-42cfb0-6978a32735ce18e1c067253e"  # ডাক যোগাযোগ
# 'OC (<thana> PS)' rows of the contact table -> upazila (None: a thana that is not an upazila)
BP_TABLE_THANAS = {"bakergonj": "Bakerganj", "babugonj": "Babuganj", "banaarypara": "Banaripara", "uzirpur": "Wazirpur",
                   "gouranadi": "Gaurnadi", "agoiljhara": "Agailjhara", "hijla": "Hizla", "muladi": "Muladi",
                   "mahendigonj": "Mehendiganj", "kazirhat": None}
# police.barisalsadar.barisal.gov.bd is titled 'বরিশাল সদর থানা' but carries no officer card or content, and the SP's contact table
# lists no such thana -> not a district thana here
BP_SKIP = {"Barishal Sadar"}


def bp_contact_table():
    """police.barisal.gov.bd 'যোগাযোগ': Designation | Phone | Mobile | E-mail. Returns (rows by thana key, sp row, control room row,
    page-updated text). Only office landlines, police official mobiles and *.gov.bd e-mails are kept."""
    t = fetch_html(BP_CONTACT)
    if not t:
        return {}, None, None, ""
    upd = re.search(r"হাল-নাগাদ করা হয়েছে:\s*([^<]+?)\s*<", nfc(t))
    thanas, sp, ctrl, keep = {}, None, None, []
    for tb in tables(t):
        for row in tb:
            if len(row) < 4:
                continue
            des, ph, mob, em = row[:4]
            rec = {"designation": des, "landline": "; ".join(landlines(*ph.split())), "mobile": "; ".join(official_mobiles(mob)),
                   "email": "; ".join(gov_emails(em))}
            m = re.match(r"^OC\s*[,(]\s*([A-Za-z]+)\s+PS\)?$", des)
            if m and m.group(1).lower() in BP_TABLE_THANAS:
                thanas[m.group(1).lower()] = rec
            elif des == "SP":
                sp = rec
            elif des == "Control Room":
                ctrl = dict(rec, mobile="")   # its mobile is not in the police official series
            else:
                continue
            keep.append(" | ".join([des, rec["landline"], rec["mobile"] if des != "Control Room" else "", rec["email"]]))
    save_raw("barishal_police_contact.txt", "Source: %s (content updated: %s)\nDesignation | landline | official mobile | e-mail "
             "(rows used here only)\n" % (BP_CONTACT, upd.group(1).strip() if upd else "?") + "\n".join(keep) + "\n")
    return thanas, sp, ctrl, (upd.group(1).strip() if upd else "")


BP_PORTAL = "https://police.barisal.gov.bd/"
BP_OFFICERS = BP_PORTAL + "pages/officers"   # SP portal officer list (also carries the 10 thana OCs' cards)
BP_MAIL = {"Bakerganj": "ocbar.bak", "Babuganj": "ocbar.bab", "Banaripara": "ocbar.ban", "Wazirpur": "ocbar.uzi", "Gaurnadi": "ocbar.gou",
           "Agailjhara": "ocbar.ago", "Hizla": "ocbar.hij", "Muladi": "ocbar.mul", "Mehendiganj": "ocbar.mah", None: "ocbar.kaz"}


def host_of(u):
    return urllib.parse.urlsplit(u).netloc.lower().split(":")[0]


def bp_menu_thanas():
    """SP portal menu 'থানা / অন্যান্ন কার্যালয়সমূহ': [(thana name as listed, link)]."""
    t = fetch_html(BP_PORTAL)
    out = re.findall(r'<a title="\s*([^"]*থানা)" class="menu-sub-sub-child-link" href="([^"]+)"', t)
    return [(nfc(_html.unescape(n)), h) for n, h in dict.fromkeys(out)]


def bp_oc_card(cards, names_bn, en):
    """First Bangla OC card naming the thana (names_bn); e-mail kept only if it is that thana's mailbox, and a mobile only if no OC card
    of another thana carries the same number (the list mixes them up: Bakerganj's and Babuganj's cards share one mobile)."""
    oc_cards = [c for c in cards if "অফিসার ইনচার্জ" in nfc(c.get("পদবি", ""))]
    for c in cards:
        d = nfc(c.get("পদবি", ""))
        if "অফিসার ইনচার্জ" in d and any(n in d for n in names_bn):
            em = [e for e in gov_emails(c.get("ইমেইল")) if e.split("@")[0] == BP_MAIL.get(en)]
            mob = official_mobiles(c.get("মোবাইল"), c.get("ফোন (অফিস)"))[:1]
            if mob and any(o is not c and mob[0] in official_mobiles(o.get("মোবাইল"), o.get("ফোন (অফিস)"))
                           and not any(n in nfc(o.get("পদবি", "")) for n in names_bn) for o in oc_cards):
                mob = []
            return {"designation": d.rstrip("।"), "landline": "; ".join(landlines(c.get("ফোন (অফিস)"))),
                    "mobile": "; ".join(mob), "email": "; ".join(em)}
    return None


def main_barishal():
    places, facts, missing = [], [], []
    table, sp_t, ctrl_t, upd = bp_contact_table()
    menu = bp_menu_thanas()
    ht = fetch_html(BP_OFFICERS)
    cards = officer_cards(widget(ht) or widget(ht, "HybridBrowseWidget") or ht)
    lnote = "the thana OC's card on the SP portal officer list (%s)" % BP_OFFICERS
    tnote = "contact table on police.barisal.gov.bd 'যোগাযোগ' (content updated %s)" % (upd or "?")
    postal = fetch_html(BP_POSTAL)
    addr = ""
    if postal:
        lines = content_text(postal)
        i = next((k for k, l in enumerate(lines) if l.startswith("পুলিশ সুপারের কার্যালয়")), None)
        if i is not None:
            addr = nfc(" ".join(lines[i:i + 3]).replace(" ,", ","))
            addr = re.sub(r"^পুলিশ সুপারের কার্যালয়,\s*", "", addr).strip()
    sp = sp_office_row(BP_KEY, "Barishal", "বরিশাল", "barpol-sp-office", host="police.barisal.gov.bd")
    if sp:
        if sp_t and not sp["phone"]:
            sp["phone"] = "; ".join(x for x in (sp_t["landline"], sp_t["mobile"]) if x)
            sp["notes"] += " Phone from the %s (no number on the officer card)." % tnote
        if sp_t and not sp["email"]:
            sp["email"] = sp_t["email"]
            sp["notes"] += " E-mail from the %s." % tnote
        if addr:
            sp["address"] = addr
            sp["notes"] += " Address from 'ডাক যোগাযোগ' (%s)." % BP_POSTAL
        places.append(sp)
    else:
        missing.append("police.barisal.gov.bd")
    used = set()
    for en, bns, sub in BARISHAL_UPAZILAS["Barishal"]:
        if en in BP_SKIP:
            continue
        rec, err = thana_row_from_portal(BP_KEY, "Barishal", "বরিশাল", en, bns[0], "police.%s.barisal.gov.bd" % sub,
                                         "barpol-%s" % en.lower().replace(" ", "-"))
        tk = next((k for k, v in BP_TABLE_THANAS.items() if v == en), None)
        tr = table.get(tk) if tk else None
        listed = [n for n, h in menu if host_of(h) == "police.%s.barisal.gov.bd" % sub]
        oc = bp_oc_card(cards, [bns[0]] + [n.replace(" থানা", "") for n in listed], en)
        if rec:
            if rec["name_bn"] in ("মডেল থানা", "থানা"):
                rec["name_bn"] = listed[0] if listed else "%s %s" % (bns[0], rec["name_bn"])
                rec["notes"] += ("; portal title names no thana; name as listed in the SP portal menu" if listed else
                                 "; portal title names no thana; name composed from the upazila")
            ex = json.loads(rec["extra_json"] or "{}")
            if listed:
                ex["listed_on"] = BP_PORTAL + " (menu 'থানা / অন্যান্ন কার্যালয়সমূহ')"
            if oc:
                ex["sp_portal_oc_card"] = {k: v for k, v in oc.items() if v}
                if not rec["phone"] and (oc["landline"] or oc["mobile"]):
                    rec["phone"] = "; ".join(x for x in (oc["landline"], oc["mobile"]) if x)
                    rec["notes"] += "; phone from %s (no number on the thana portal)" % lnote
                if not rec["email"] and oc["email"]:
                    rec["email"] = oc["email"]
                    rec["notes"] += "; e-mail from %s" % lnote
            rec["extra_json"] = xj(ex)
            if tr:
                used.add(tk)
                ex = json.loads(rec["extra_json"] or "{}")
                ex["sp_contact_table"] = {k: v for k, v in tr.items() if v}
                rec["extra_json"] = xj(ex)
                if not rec["phone"]:
                    rec["phone"] = "; ".join(x for x in (tr["landline"], tr["mobile"]) if x)
                    rec["notes"] += "; phone from the %s (no number on the thana portal)" % tnote
                if not rec["email"] and tr["email"]:
                    rec["email"] = tr["email"]
                    rec["notes"] += "; e-mail from the %s" % tnote
            places.append(rec)
        else:
            missing.append(err)
    for tk, tr in table.items():   # thanas of the contact table without an upazila portal (Kazirhat)
        if tk in used:
            continue
        up = BP_TABLE_THANAS[tk]
        if up is not None and any(p.get("upazila_en") == up for p in places):
            continue
        listed = [(n, h) for n, h in menu if tk in ("kazirhat",) and n.startswith("কাজিরহাট")]
        if not listed:
            continue
        name_bn, link = listed[0]
        oc = bp_oc_card(cards, [name_bn.replace(" থানা", "")], up)
        phone = "; ".join(x for x in ((oc["landline"], oc["mobile"]) if oc else ()) if x)
        places.append(dict(source_key=BP_KEY, source_id="barpol-%s" % tk, name_bn=name_bn, name_en="",
                           category_key="emergency.police_station", district_en="Barishal", upazila_en=up or "",
                           phone=phone or "; ".join(x for x in (tr["landline"], tr["mobile"]) if x),
                           email=(oc and oc["email"]) or tr["email"], website=link,
                           operator="বরিশাল জেলা পুলিশ", ownership="public",
                           extra_json=xj({"listed_on": BP_PORTAL + " (menu 'থানা / অন্যান্ন কার্যালয়সমূহ')",
                                          "sp_portal_oc_card": {k: v for k, v in oc.items() if v} if oc else None,
                                          "sp_contact_table": {k: v for k, v in tr.items() if v}}),
                           source_url=BP_OFFICERS if oc else BP_CONTACT,
                           notes="Thana listed in the SP portal menu (link: %s, not opened) and as '%s' on the %s; contacts from %s; "
                                 "not an upazila thana and the sources do not name its upazila" % (link, tr["designation"], tnote, lnote)))
    if ctrl_t:
        places.append(dict(source_key=BP_KEY, source_id="barpol-control-room", name_bn="বরিশাল জেলা পুলিশ কন্ট্রোল রুম", name_en="",
                           category_key="emergency", district_en="Barishal", phone=ctrl_t["landline"], operator="বরিশাল জেলা পুলিশ",
                           ownership="public", extra_json=xj({"label_in_source": "Control Room"}), source_url=BP_CONTACT,
                           notes="Name composed from the 'Control Room' row of the %s; only the landline is kept (the mobile is not in the "
                                 "police official series)" % tnote))
    if menu:
        save_raw("barishal_police_menu_thanas.txt", "Source: %s menu 'থানা / অন্যান্ন কার্যালয়সমূহ'\n" % BP_PORTAL
                 + "\n".join("%s | %s" % (n, h) for n, h in menu) + "\n")
        facts.append(dict(entity_level="district", entity_name_en="Barishal", district_en="Barishal", fact="police_stations",
                          value=len(menu), unit="thanas", basis="listed", year=2026, source_key=BP_KEY, source_url=BP_PORTAL,
                          notes="Thanas in the SP portal menu 'থানা / অন্যান্ন কার্যালয়সমূহ': %s (Barishal District Police, outside BMP). "
                                "The %s has the same %d thanas as 'OC (<thana> PS)' rows." % (", ".join(n for n, _ in menu), tnote, len(table))))
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    if missing:
        print("unavailable:", missing)
    write_manifest(dict(
        key=BP_KEY, division="barishal", kind="district_police",
        name="Barishal District Police — SP office, thanas and control room", organization="Barishal District Police (Bangladesh Police)",
        source_type="government_portal", trust_level=4,
        urls=[BP_PORTAL, BP_OFFICERS, BP_CONTACT, BP_POSTAL, "https://police.<upazila>.barisal.gov.bd/"],
        accessed=__import__("datetime").date.today().isoformat(), publication_date=None, license=None, license_url=None,
        attribution="Office of the Superintendent of Police, Barishal (police.barisal.gov.bd) and the thana portals",
        notes="No licence stated. SP office from the Superintendent's officer card and 'ডাক যোগাযোগ' (address); thanas from the 9 "
              "upazila thana portals' officer cards (office landline, OC's police official mobile, *.gov.bd e-mail); thana list (10, "
              "incl. Kazirhat, which has no upazila portal) from the SP portal menu; gaps filled from the thana OCs' cards on the SP "
              "portal officer list, then from the SP portal's 'যোগাযোগ' contact table (content updated %s; designations and numbers, "
              "no names), which also gives the control room. Personal e-mails, other mobiles and officers' names are not copied. "
              "police.barisalsadar.barisal.gov.bd ('বরিশাল সদর থানা') has no content and is not in the SP portal's thana menu or "
              "contact table, so it is not a row. Barishal city is policed by BMP (BARISHAL_METRO_POLICE_THANAS_2026)." % (upd or "?")
              + (" Unavailable this run: " + "; ".join(missing) if missing else "")),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


# --- Sylhet District Police (police.sylhet.gov.bd; Sylhet city is policed by SMP, see SYLHET_METRO_POLICE_THANAS_2026) -------------
SP_KEY = "SYLHET_POLICE_2026"
SP_PORTAL = "https://police.sylhet.gov.bd/"
SP_GLANCE = SP_PORTAL + "pages/static-pages/696cafe6c4774958d7b9fb06"   # একনজরে (district profile table incl. 'থানা : ১৭ টি')
# The SP portal's thana menu ('সার্কেল ও থানার কর্মরত কর্মকর্তাগণ') and contact pages ('ডাক যোগাযোগ', 'অনলাইন যোগাযোগ') are empty
# links ('#'). The thana portals police.<upazila>.sylhet.gov.bd exist (DNS) but serve the *.sylhet.gov.bd certificate, which does
# not cover a second-level name: TLS fails (hostname mismatch), so they are skipped and recorded, not fetched without verification.


def main_sylhet():
    INTERMEDIATES.extend(u for u in SYLHET_INTERMEDIATES if u not in INTERMEDIATES)   # before the first request
    places, facts, missing = [], [], []
    sp = sp_office_row(SP_KEY, "Sylhet", "সিলেট", "sylpol-sp-office", host="police.sylhet.gov.bd")
    if sp:
        places.append(sp)
    else:
        missing.append("police.sylhet.gov.bd")
    t = fetch_html(SP_GLANCE)
    if t:
        rows = {r[0]: r[-1] for tb in tables(t) for r in tb if len(r) >= 3}
        keep = ["উপজেলা", "থানা", "ইউনিয়ন", "সিটি কর্পোরেশন", "পৌরসভা"]
        save_raw("sylhet_police_glance.txt", "Source: %s ('একনজরে', rows used here only)\n" % SP_GLANCE
                 + "\n".join("%s : %s" % (k, rows[k]) for k in keep if k in rows) + "\n")
        m = re.match(r"^([০-৯0-9]+)\s*টি$", rows.get("থানা", ""))
        if m:
            facts.append(dict(entity_level="district", entity_name_en="Sylhet", district_en="Sylhet", fact="police_stations",
                              value=int(asc(m.group(1))), unit="thanas", basis="reported", year=2026, source_key=SP_KEY,
                              source_url=SP_GLANCE, notes="SP portal 'একনজরে': 'থানা : %s' (district profile next to 'উপজেলা : %s'). "
                              "The page does not say whether SMP's metropolitan thanas are included." % (rows["থানা"], rows.get("উপজেলা", "?"))))
    for en, bns, sub in SYLHET_UPAZILAS["Sylhet"]:
        rec, err = thana_row_from_portal(SP_KEY, "Sylhet", "সিলেট", en, bns[0], "police.%s.sylhet.gov.bd" % sub,
                                         "sylpol-%s" % en.lower().replace(" ", "-"))
        if rec:
            places.append(rec)
        else:
            missing.append(err)
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    if missing:
        print("unavailable:", missing)
    nthana = sum(1 for p in places if p["category_key"] == "emergency.police_station")
    write_manifest(dict(
        key=SP_KEY, division="sylhet", kind="district_police",
        name="Sylhet District Police — SP office and thanas", organization="Sylhet District Police (Bangladesh Police)",
        source_type="government_portal", trust_level=4,
        urls=[SP_PORTAL, SP_PORTAL + "pages/officers", SP_GLANCE, "https://police.<upazila>.sylhet.gov.bd/"],
        accessed=__import__("datetime").date.today().isoformat(), publication_date=None, license=None, license_url=None,
        attribution="Office of the Superintendent of Police, Sylhet (police.sylhet.gov.bd)",
        notes="No licence stated. SP office from the Superintendent's officer card (office landline, police official mobile, fax in "
              "extra_json, police.gov.bd e-mail); officers' names are not copied. The SP portal's thana and contact menu entries are "
              "empty links; its 'একনজরে' gives the district's thana count. Thana rows: %d of the 13 upazila thana portals "
              "police.<upazila>.sylhet.gov.bd answered; the others did not respond (Nov 2026: all serve the *.sylhet.gov.bd certificate, which does not cover a second-level "
              "name - TLS hostname mismatch - so they were skipped, not fetched without verification). sylhet.gov.bd "
              "sends only its leaf certificate: the Let's Encrypt intermediates are added from the CA's AIA URLs, TLS verification "
              "stays on. Sylhet city is policed by SMP (SYLHET_METRO_POLICE_THANAS_2026)." % nthana
              + (" Unavailable this run: " + "; ".join(missing) if missing else "")),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


# --- Mymensingh District Police (police.mymensingh.gov.bd; there is no metropolitan police in Mymensingh) -------------------------
MP_KEY = "MYMENSINGH_POLICE_2026"
MP_PORTAL = "https://police.mymensingh.gov.bd/"
# The SP portal's home-page person card links no officer page with content; the officer list (/pages/officers) has the SP card. Its
# contact menu entries ('ডাক যোগাযোগ', 'অনলাইন যোগাযোগ') are empty links and its 'সাংগঠনিক কাঠামো' page is empty. Bangladesh Police
# HQ's Mymensingh Range page gives the district's police stations (14, incl. Kotwali and Pagla, which have no upazila thana portal).
MP_PHQ_RANGE = "https://www.police.gov.bd/en/mymensingh_range"
MP_PHQ_PAT = (r"Mymensingh District:.*?a total of (\d+) police circles and (\d+) police stations: ([^.]*?) in Mymensingh\. Support is "
              r"provided by (\d+) police outposts and local investigation is carried out by (\d+) investigation centers")


def main_mymensingh():
    places, facts, missing = [], [], []
    sp = sp_office_row(MP_KEY, "Mymensingh", "ময়মনসিংহ", "mympol-sp-office", host="police.mymensingh.gov.bd")
    if sp and not sp["phone"] and not sp["email"]:   # home-page person card has no content: use the officer list
        url = MP_PORTAL + "pages/officers"
        ht = fetch_html(url)
        cards = officer_cards(widget(ht) or widget(ht, "HybridBrowseWidget") or ht)
        card = next((c for c in cards if is_head(c, ("পুলিশ সুপার",)) and "অতিঃ" not in c.get("পদবি", "")
                     and "অতিরিক্ত" not in c.get("পদবি", "") and "সহকারী" not in c.get("পদবি", "")), None)
        if card:
            mob = official_mobiles(card.get("মোবাইল"), card.get("ফোন (অফিস)"))
            ex = json.loads(sp["extra_json"] or "{}")
            ex.update({"head_designation": card.get("পদবি"), "sp_official_mobile": "; ".join(mob),
                       "fax": "; ".join(landlines(card.get("ফ্যাক্স")))})
            sp.update(phone="; ".join(landlines(card.get("ফোন (অফিস)")) + mob), email="; ".join(gov_emails(card.get("ইমেইল"))),
                      source_url=url, extra_json=xj(ex))
            sp["notes"] += " The home page's person card has no content; the SP card was taken from the officer list."
    if sp:
        places.append(sp)
    else:
        missing.append("police.mymensingh.gov.bd")
    t = fetch_html(MP_PHQ_RANGE)
    x = re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?s)<script.*?</script>|<style.*?</style>", " ", t or ""))))
    m = re.search(MP_PHQ_PAT, x)
    if m:
        save_raw("police_gov_bd_mymensingh_district.txt", "Source: %s (figures used; the descriptive prose is not kept)\n"
                 "Mymensingh District: %s police circles; %s police stations: %s; %s police outposts; %s investigation centers\n"
                 % (MP_PHQ_RANGE, m.group(1), m.group(2), m.group(3).strip(), m.group(4), m.group(5)))
        base = dict(entity_level="district", entity_name_en="Mymensingh", district_en="Mymensingh", basis="reported", year="",
                    source_key=MP_KEY, source_url=MP_PHQ_RANGE)
        names = m.group(3).strip()
        for fact, val, unit, note in (
                ("police_stations", m.group(2), "thanas", "police.gov.bd Mymensingh Range page (undated): %s police stations: %s. "
                 "Kotwali and Pagla have no upazila thana portal and are not rows here." % (m.group(2), names)),
                ("police_circles", m.group(1), "circles", "police.gov.bd Mymensingh Range page (undated)"),
                ("police_outposts", m.group(4), "outposts", "police.gov.bd Mymensingh Range page (undated)"),
                ("police_investigation_centres", m.group(5), "centres", "police.gov.bd Mymensingh Range page (undated)")):
            facts.append(dict(base, fact=fact, value=int(val), unit=unit, notes=note))
    else:
        print("police.gov.bd: Mymensingh District sentence not found")
    for en, bns, sub in MYMENSINGH_UPAZILAS["Mymensingh"]:
        rec, err = thana_row_from_portal(MP_KEY, "Mymensingh", "ময়মনসিংহ", en, bns[0], "police.%s.mymensingh.gov.bd" % sub,
                                         "mympol-%s" % en.lower().replace(" ", "-"))
        if not rec:
            missing.append(err)
            continue
        if en == "Mymensingh Sadar" and rec["name_bn"] == "ময়মনসিংহ সদর থানা":
            rec["notes"] += ("; police.gov.bd's station list for the district names Kotwali and no 'Sadar' thana; the composed name "
                             "is kept as the portal gives no other")
        places.append(rec)
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    if missing:
        print("unavailable:", missing)
    nthana = sum(1 for p in places if p["category_key"] == "emergency.police_station")
    write_manifest(dict(
        key=MP_KEY, division="mymensingh", kind="district_police",
        name="Mymensingh District Police — SP office and thanas", organization="Mymensingh District Police (Bangladesh Police)",
        source_type="government_portal", trust_level=4,
        urls=[MP_PORTAL, MP_PORTAL + "pages/officers", "https://police.<upazila>.mymensingh.gov.bd/", MP_PHQ_RANGE],
        accessed=__import__("datetime").date.today().isoformat(), publication_date=None, license=None, license_url=None,
        attribution="Office of the Superintendent of Police, Mymensingh (police.mymensingh.gov.bd); Bangladesh Police (police.gov.bd)",
        notes="No licence stated. SP office from the Superintendent's officer card on the SP portal's officer list (police official "
              "mobile, police.gov.bd e-mail); officers' names are not copied, nor the other officers' cards (several give gmail "
              "addresses). Thana rows: %d of the 13 upazila thana portals police.<upazila>.mymensingh.gov.bd (officer cards: office "
              "landline, OC's police official mobile, *.gov.bd e-mail); most portals are titled only 'থানা', so names are composed "
              "from the upazila (noted per row). Counts (14 police stations incl. Kotwali and Pagla, which have no upazila portal; "
              "4 circles; 2 outposts; 4 investigation centres) from police.gov.bd's Mymensingh Range page (undated). The SP portal's "
              "contact entries are empty links. There is no metropolitan police in Mymensingh (police.gov.bd lists eight "
              "metropolitan units, none for Mymensingh)." % nthana
              + (" Unavailable this run: " + "; ".join(missing) if missing else "")),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


HEADS = {"rajshahi": dict(folder="rajshahi_police_2026"), "rangpur": dict(folder="rangpur_police_2026", run=main_rangpur),
         "dhaka": dict(folder="dhaka_police_2026", run=main_dhaka),
         "chattogram": dict(folder="chattogram_police_2026", run=main_chattogram),
         "khulna": dict(folder="khulna_police_2026", run=main_khulna),
         "barishal": dict(folder="barishal_police_2026", run=main_barishal),
         "sylhet": dict(folder="sylhet_police_2026", run=main_sylhet),
         "mymensingh": dict(folder="mymensingh_police_2026", run=main_mymensingh)}


def configure():
    global DIVISION, HERE, RAW
    DIVISION, out = parse_division_args({k: v["folder"] for k, v in HEADS.items()})
    HERE = Path(out)
    RAW = HERE / "raw"


if __name__ == "__main__":
    main()
