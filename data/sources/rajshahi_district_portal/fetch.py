#!/usr/bin/env python3
"""Rajshahi District Administration portal (rajshahi.gov.bd): union list, pourashava list, district at-a-glance.

Usage: python3 -I fetch.py [--cache DIR]
Writes areas.csv, facts.csv, raw/*.txt (text of the pages used) and refreshes SOURCE.json file hashes.

Other divisions: python3 -I fetch.py --division <rangpur|...> [--out DIR] [--cache DIR]
  runs the generic division mode (block 'Division mode' below) and writes to the division's own folder
  (default data/sources/<division>_district_portal); the Rajshahi outputs in this folder are never touched. With no arguments
  (= --division rajshahi) the script behaves exactly as before; --out DIR redirects the Rajshahi outputs.
"""
# ---------------------------------------------------------------------------
# shared helpers (identical block in each Rajshahi portal fetch.py)
# ---------------------------------------------------------------------------
import argparse, csv, hashlib, html, json, os, re, ssl, sys, tempfile, time, unicodedata
import urllib.robotparser
from urllib.parse import urljoin, urlparse
import requests

UA = "Elaka360-data-pipeline (research; contact via repository)"
HERE = os.path.dirname(os.path.abspath(__file__))
ACCESSED = time.strftime("%Y-%m-%d")
# Many *.gov.bd servers do not send the Sectigo intermediate certificate. We fetch it from the
# certificate's AIA URL and add it to the normal CA store; verification is never switched off.
AIA_INTERMEDIATES = ["http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt"]
_session = requests.Session()
_session.headers["User-Agent"] = UA
_last = {}
_robots = {}
_bundle = None
CACHE = None


def ca_bundle():
    global _bundle
    if _bundle:
        return _bundle
    try:
        import certifi
        base = certifi.where()
    except ImportError:
        base = ssl.get_default_verify_paths().cafile or "/etc/ssl/certs/ca-certificates.crt"
    pem = open(base, encoding="utf-8").read()
    for u in AIA_INTERMEDIATES:
        r = requests.get(u, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
        pem += "\n" + (r.text if r.content.startswith(b"-----BEGIN") else ssl.DER_cert_to_PEM_cert(r.content))
    f = tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False)
    f.write(pem)
    f.close()
    _bundle = f.name
    return _bundle


def _polite(host):
    dt = time.time() - _last.get(host, 0)
    if dt < 1.2:
        time.sleep(1.2 - dt)
    _last[host] = time.time()


def allowed(url):
    p = urlparse(url)
    root = f"{p.scheme}://{p.netloc}"
    if root not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            _polite(p.netloc)
            r = _session.get(root + "/robots.txt", timeout=30, verify=ca_bundle())
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        except requests.RequestException:
            rp.parse([])
        _robots[root] = rp
    return _robots[root].can_fetch(UA, url)


def get(url, timeout=45):
    """GET with on-disk cache (optional), politeness and robots.txt. Returns text or raises."""
    key = hashlib.sha1(url.encode()).hexdigest()
    if CACHE:
        p = os.path.join(CACHE, key)
        if os.path.exists(p):
            return open(p, encoding="utf-8", errors="replace").read()
    if not allowed(url):
        raise RuntimeError(f"robots.txt disallows {url}")
    _polite(urlparse(url).netloc)
    r = _session.get(url, timeout=timeout, verify=ca_bundle())
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code} {url}")
    t = r.content.decode("utf-8", "replace")
    if CACHE:
        os.makedirs(CACHE, exist_ok=True)
        open(os.path.join(CACHE, key), "w", encoding="utf-8").write(t)
    return t


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


def text(fragment):
    s = re.sub(r"<script.*?</script>|<style.*?</style>", "", fragment, flags=re.S)
    s = re.sub(r"<br\s*/?>|</p>|</tr>|</li>|</h\d>|</div>", "\n", s)
    s = re.sub(r"</td>|</th>", " | ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ").replace("‌", "")
    return nfc("\n".join(re.sub(r"[ \t]+", " ", l).strip() for l in s.split("\n") if l.strip()))


BN = "০১২৩৪৫৬৭৮৯"
BN_MONTHS = {"জানুয়ারি": 1, "জানুয়ারী": 1, "ফেব্রুয়ারি": 2, "ফেব্রুয়ারী": 2, "মার্চ": 3, "এপ্রিল": 4, "মে": 5,
             "জুন": 6, "জুলাই": 7, "আগস্ট": 8, "সেপ্টেম্বর": 9, "অক্টোবর": 10, "নভেম্বর": 11, "ডিসেম্বর": 12}


def asc(s):
    return "".join(str(BN.index(c)) if c in BN else c for c in (s or ""))


def page_date(upd):
    """'কনটেন্টটি শেষ হাল-নাগাদ করা হয়েছে: সোমবার, ৯ জুলাই, ২০১৮ এ ...' -> '2018-07-09'"""
    m = re.search(r"([০-৯0-9]{1,2})\s+(\S+),\s*([০-৯0-9]{4})", nfc(upd or ""))
    if not m:
        return ""
    d, mon, y = asc(m.group(1)), nfc(m.group(2)), asc(m.group(3))
    mon = {nfc(k): v for k, v in BN_MONTHS.items()}.get(mon)
    if not (d.isdigit() and y.isdigit() and mon):
        return ""
    return f"{int(y):04d}-{mon:02d}-{int(d):02d}"


def content(t):
    """Main content of an a2i National Portal page: dict(updated, date, title, html, text) or None."""
    i = t.find('data-widget_name="ContentViewerWidget"')
    if i < 0:
        return None
    seg = t[i:]
    j = seg.find("এই কনটেন্টটি শেয়ার")
    if j > 0:
        seg = seg[:j]
    m = re.search(r'content-update-block">\s*<p>\s*(.*?)</p>', seg, re.S)
    upd = nfc(html.unescape(m.group(1)).strip()) if m else ""
    m = re.search(r"<h2>(.*?)</h2>", seg, re.S)
    title = text(m.group(1)) if m else ""
    seg = re.sub(r'encoded-content="[^"]*"', "", seg)
    seg = seg[seg.find(">") + 1:]
    return dict(updated=upd, date=page_date(upd), title=title, html=seg, text=text(seg))


def links(fragment, base=""):
    out = []
    for h, x in re.findall(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', fragment, flags=re.S):
        h = html.unescape(h).strip()
        out.append((urljoin(base, h) if base else h, text(x)))
    return out


def clean_url(u):
    u = (u or "").strip().replace("http://http://", "http://").replace("https://http://", "http://")
    if not u:
        return ""
    p = urlparse(u if "://" in u else "http://" + u)
    return f"https://{p.netloc.lower()}/" if p.netloc else ""


def table_rows(fragment):
    rows = []
    for tr in re.findall(r"<tr.*?</tr>", fragment, flags=re.S):
        cells = [text(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S)]
        rows.append(([c for c in cells], tr))
    return rows


def first_number(s, dot_thousands=True):
    """First number in s (Bangla or ASCII digits); returns (value_str, note)."""
    s = asc(s)
    m = re.search(r"\d[\d,\.]*", s)
    if not m:
        return "", ""
    raw = m.group(0).rstrip(".,")
    note = ""
    if not dot_thousands and re.fullmatch(r"\d+,\d{2}", raw):     # '৫৭,৪৯' / '18,73' = decimal comma
        return raw.replace(",", "."), f"'{raw}' read as decimal comma"
    if dot_thousands and re.fullmatch(r"\d{1,3}(\.\d{3})+", raw):          # '২২.৩২৯ জন' = 22,329 (dot used as thousands separator)
        note = f"'{raw}' read as thousands separator"
        raw = raw.replace(".", "")
    raw = raw.replace(",", "")
    return raw, note


def kv_pairs(c):
    """(label, value) pairs from tables and 'label : value' lines of a content block."""
    pairs = []
    for cells, _ in table_rows(c["html"]):
        cells = [x.strip(" |") for x in cells if x.strip(" |")]
        while cells and re.fullmatch(r"[০-৯0-9\.\)\(।]+", cells[0]):
            cells = cells[1:]                                  # drop serial-number cells
        if len(cells) >= 2:
            pairs.append((cells[0], " ".join(cells[1:])))
    for line in c["text"].split("\n"):
        m = re.match(r"^\s*(?:[০-৯0-9]+\s*[।\.\)]\s*)?([^:ঃ|=]{2,60}?)\s*[:ঃ=]\s*(.+)$", line)
        if m:
            pairs.append((m.group(1).strip(" -•"), m.group(2).strip()))
    return pairs


FACT_LABELS = [  # (fact, include regex on label, exclude regex on label, unit)
    ("area_km2", r"আয়তন", r"পৌর|পৌরসভা|জমি", "km2"),
    ("population", r"জনসংখ্যা|লোকসংখ্যা|লোক সংখ্যা|জনসংখ্যা", r"ঘনত্ব|বৃদ্ধি|হার|পুরুষ|মহিলা|ভোটার|পৌর|শিক্ষিত|উপজাতী|আদিবাসী|গ্রাম ভিত্তিক", "persons"),
    ("mouza_count", r"মৌজা", r"পৌর|নাম", "count"),
    ("village_count", r"গ্রাম", r"গুচ্ছ|আদর্শ|ভিত্তিক|পৌর|নাম|সংসদ|গ্রামীণ|গ্রাম পুলিশ|চৌকিদার", "count"),
    ("ward_count", r"ওয়ার্ড|ওযার্ড|ওয়াড|ওয়ার্ড", r"সদস্য|মেম্বার|কাউন্সিলর|নাম|পৌর|নং|ভিত্তিক", "count"),
    ("union_count", r"ইউনিয়ন", r"ভূমি|অফিস|পরিষদ ভবন|নাম|ডিজিটাল|তথ্য|কমপ্লেক্স", "count"),
    ("pourashava_count", r"পৌরসভা", r"ওয়ার্ড|মৌজা|নাম|আয়তন|জনসংখ্যা|হোল্ডিং", "count"),
    ("household_count", r"পরিবার সংখ্যা|পরিবারের সংখ্যা|মোট পরিবার|খানার সংখ্যা|খানা সংখ্যা|^\W*খানা\W*$|মোট খানা",
     r"পায়খানা|এতিম|ইয়াতিম|কসাই|কোষাই|আদিবাসী|কৃষক|পরিকল্পনা|কল্যাণ|উপজাতি", "households"),
]


def extract_facts(c):
    """Generic label matcher; returns list of dict(fact, value, unit, year, label, raw, note)."""
    out, seen = [], set()
    for label, value in kv_pairs(c):
        lab = nfc(label)
        for fact, inc, exc, unit in FACT_LABELS:
            if fact in seen or not re.search(inc, lab) or re.search(exc, lab):
                continue
            v, note = first_number(value, dot_thousands=(fact != "area_km2"))
            if not v:
                continue
            y = re.search(r"(?<![\d.,])(19|20)\d\d(?![\d.,])", asc(value))
            year = y.group(0) if y else ""
            if fact == "population" and re.search(r"মোট\s*(জনসংখ্যা|লোকসংখ্যা)?[\s:ঃ\-–\.]*[০-৯0-9]", value):
                tail = re.split(r"মোট\s*(?:জনসংখ্যা|লোকসংখ্যা)?[\s:ঃ\-–\.]*(?=[০-৯0-9])", value)[-1]
                v, note = first_number(tail)
                note = (note + "; " if note else "") + "took the figure after 'মোট' (total)"
            if fact == "area_km2":
                after = asc(value)[re.search(r"\d", asc(value)).start():][:40]
                if re.search(r"^[\d,\.\s]*(বর্গ\s*)?মাইল|^[\d,\.\s]*sq\.?\s*mile", after, re.I):
                    unit = "sq_miles"
                elif re.search(r"^[\d,\.\s]*(বর্গ\s*)?একর", after):
                    unit = "acres"
                elif re.search(r"^[\d,\.\s]*হেক্টর", after):
                    unit = "hectares"
                elif not re.search(r"^[\d,\.\s\(\)]*(বর্গ\s*কি|বগ\s*কি|বঃ\s*কি|ব\s*[:\.]\s*কি|ব\.কি|বর্গকি|কিঃ|কি\.\s*মি|কিলো|km|sq\s*km|SQKM|কিমি)", after, re.I):
                    unit = "unstated"
            seen.add(fact)
            out.append(dict(fact=fact, value=v, unit=unit, year=year, label=lab, raw=nfc(value)[:160], note=note))
    return out


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})


AREAS_H = ["level", "name_en", "name_bn", "parent_level", "parent_name_en", "parent_name_bn", "district_en", "upazila_en",
           "code", "code_scheme", "website", "lat", "lon", "source_key", "source_url", "notes"]
FACTS_H = ["entity_level", "entity_name_en", "district_en", "upazila_en", "code", "fact", "value", "unit", "basis", "year",
           "source_key", "source_url", "notes"]


def redact(s):
    """Remove phone numbers and e-mail addresses (many pages list officials' personal mobiles)."""
    s = re.sub(r"(?:\+?৮৮|\+?88)?[০0][১1][৩-৯3-9](?:[\s\-]?[০-৯0-9]){8}", "[phone]", s)
    s = re.sub(r"[\w.\-]+@[\w.\-]+\.\w+", "[email]", s)
    return s


def save_raw(name, url, c):
    os.makedirs(os.path.join(HERE, "raw"), exist_ok=True)
    with open(os.path.join(HERE, "raw", name), "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\nUPDATED: {c['updated']}\nTITLE: {c['title']}\nACCESSED: {ACCESSED}\n\n{redact(c['text'])}\n")


def squash(s):
    return re.sub(r"[\s|]+", "", nfc(s))


def on_page(quote, c):
    return squash(quote) in squash(c["text"])


def update_manifest():
    p = os.path.join(HERE, "SOURCE.json")
    m = json.load(open(p, encoding="utf-8"))
    files = {}
    for root, _, fs in os.walk(HERE):
        for f in sorted(fs):
            rel = os.path.relpath(os.path.join(root, f), HERE)
            if rel in ("SOURCE.json", "fetch.py", "REPORT.md") or rel.startswith("__pycache__"):
                continue
            files[rel] = hashlib.sha256(open(os.path.join(root, f), "rb").read()).hexdigest()
    m["files"] = dict(sorted(files.items()))
    m["accessed"] = ACCESSED
    json.dump(m, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(p, "a").write("\n")


UPAZILAS = [  # (subdomain, name_en, name_bn) — subdomains as linked from rajshahi.gov.bd
    ("bagha", "Bagha", "বাঘা"), ("bagmara", "Bagmara", "বাগমারা"), ("charghat", "Charghat", "চারঘাট"),
    ("durgapur", "Durgapur", "দুর্গাপুর"), ("godagari", "Godagari", "গোদাগাড়ী"), ("mohonpur", "Mohanpur", "মোহনপুর"),
    ("paba", "Paba", "পবা"), ("puthia", "Puthia", "পুঠিয়া"), ("tanore", "Tanore", "তানোর"),
]
UPZ_BN = {nfc(b): e for _, e, b in UPAZILAS}
UPZ_BN.update({nfc("দূর্গাপুর"): "Durgapur", nfc("গোদাগাড়ি"): "Godagari"})
# ---------------------------------------------------------------------------

KEY = "RAJSHAHI_DC_PORTAL_2026"
BASE = "https://rajshahi.gov.bd"
P_UNIONS = BASE + "/pages/static-pages/697f79bb35ce18e1c06b5300"      # রাজশাহী জেলার উপজেলা ও ইউনিয়ন সমূহ
P_GLANCE = BASE + "/pages/static-pages/697fb2f635ce18e1c06c9335"      # এক নজরে জেলা
P_POURA = BASE + "/pages/static-pages/6a706a5b3a58d2277e320df7"       # পৌরসভা সমূহের তালিকা
P_UPZ = BASE + "/pages/static-pages/6a576e8a5adca3a8fa9671c8"         # উপজেলা পরিষদের তালিকা

# Figures transcribed from the এক নজরে page. Each quote must still appear in the page text (checked below).
GLANCE = [
    ("area_km2", "2407.01", "km2", "as stated", "", "আয়তন | ২৪০৭.০১ বর্গকিলোমিটার", ""),
    ("population", "3023216", "persons", "estimate (projected, March 2020)", "2020",
     "৩০,২৩,২১৬ জন (মার্চ, ২০২০ প্রাক্কলিত জনসংখ্যা)", "page calls it প্রাক্কলিত (projected), not a census count"),
    ("population_male", "1526302", "persons", "estimate (projected, March 2020)", "2020", "পুরুষ | ১৫,২৬,৩০২", ""),
    ("population_female", "1496914", "persons", "estimate (projected, March 2020)", "2020", "মহিলা | ১৪,৯৬,৯১৪", ""),
    ("city_corporation_count", "1", "count", "as stated", "", "সিটি কর্পোরেশন | ১টি", ""),
    ("upazila_count", "9", "count", "as stated", "", "উপজেলা | ৯টি", ""),
    ("thana_count", "13", "count", "as stated", "", "থানা | ১৩ টি (মেট্রোপলিটন এলাকায় ৪ টি)",
     "page: 13 thanas, 4 of them in the metropolitan area (RMP now lists 12 metropolitan thanas; page text is older)"),
    ("union_count", "72", "count", "as stated", "", "ইউনিয়নের সংখ্যা | ৭২ টি", "headline table"),
    ("union_count", "71", "count", "as stated (older section)", "", "ইউনিয়নের সংখ্যা | : ৭১ টি",
     "same page, সমাজসেবা বিভাগ section, next to 'ওয়ার্ডের সংখ্যা ৬৩৯' (=71x9); stale figure from before Chakrajapur"),
    ("union_ward_count", "639", "count", "as stated (older section)", "", "ওয়ার্ডের সংখ্যা | : ৬৩৯ টি", "71 unions x 9 wards"),
    ("pourashava_count", "14", "count", "as stated", "", "পৌরসভার সংখ্যা | ১৪ টি", ""),
    ("mouza_count", "1718", "count", "as stated", "", "মৌজার সংখ্যা | ১,৭১৮ টি", "BBS 2022 prints 1,678"),
    ("village_count", "1914", "count", "as stated", "", "গ্রামের সংখ্যা | ১,৯১৪ টি", ""),
]



# ===========================================================================
# Division mode: generic a2i National Portal collector used by `--division <name>` for divisions other than
# Rajshahi. Identical block in rajshahi_district_portal, division_district_portals, rajshahi_upazila_portals,
# rajshahi_union_portals and rajshahi_divisional_portal fetch.py. Pages are found through the portals' own menus
# and links (no hard-coded page ids); names, counts and figures are parsed from the pages, never typed in.
# English names of districts/upazilas are the project's keys (data/seed), not printed on the pages.
# ===========================================================================
import argparse, csv, hashlib, html, json, os, re, ssl, sys, tempfile, time, unicodedata  # noqa: E401,F811
import concurrent.futures as _dv_cf
import threading as _dv_threading
import urllib.robotparser as _dv_robotparser
from urllib.parse import urljoin, urlparse  # noqa: F811

import requests  # noqa: F811

DV_UA = "Elaka360-data-pipeline (research; contact via repository)"
DV_GAP = 1.2  # seconds between two requests to the same host
# intermediate certificates some portals do not send (fetched from the CAs' own AIA addresses; TLS stays verified):
# Sectigo DV R36, and Let's Encrypt YR1 (sylhet.gov.bd serves its Let's Encrypt leaf with a Sectigo chain)
DV_AIA = ("http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt", "http://yr1.i.lencr.org/")
DV_AREAS_H = ["level", "name_en", "name_bn", "parent_level", "parent_name_en", "parent_name_bn", "district_en",
              "upazila_en", "code", "code_scheme", "website", "lat", "lon", "source_key", "source_url", "notes"]
DV_FACTS_H = ["entity_level", "entity_name_en", "district_en", "upazila_en", "code", "fact", "value", "unit", "basis",
              "year", "source_key", "source_url", "notes"]

# name_en, name_bn, DC portal host, upazilas [(name_en, name_bn, portal subdomain, other spellings seen on portals)];
# a spelling starting with '~' is an evident misprint (matched, and flagged DOUBT where it is printed)
DV_DIVISIONS = {
    "rangpur": dict(
        code="rang", name_en="Rangpur", name_bn="রংপুর", portal="rangpurdiv.gov.bd", head="Rangpur",
        districts=[
            ("Rangpur", "রংপুর", "rangpur.gov.bd", [
                ("Rangpur Sadar", "রংপুর সদর", "rangpursadar", []), ("Gangachara", "গংগাচড়া", "gangachara", []),
                ("Taragonj", "তারাগঞ্জ", "taragonj", []), ("Badargonj", "বদরগঞ্জ", "badargonj", []),
                ("Mithapukur", "মিঠাপুকুর", "mithapukur", []), ("Pirgonj", "পীরগঞ্জ", "pirgonj", []),
                ("Kaunia", "কাউনিয়া", "kaunia", []), ("Pirgacha", "পীরগাছা", "pirgacha", [])]),
            ("Panchagarh", "পঞ্চগড়", "panchagarh.gov.bd", [
                ("Panchagarh Sadar", "পঞ্চগড় সদর", "panchagarhsadar", []), ("Debiganj", "দেবীগঞ্জ", "debiganj", []),
                ("Boda", "বোদা", "boda", []), ("Atwari", "আটোয়ারী", "atwari", []),
                ("Tetulia", "তেতুলিয়া", "tetulia", [])]),
            ("Dinajpur", "দিনাজপুর", "dinajpur.gov.bd", [
                ("Nawabganj", "নবাবগঞ্জ", "nawabganj", ["~নাবাবগঞ্জ"]), ("Birganj", "বীরগঞ্জ", "birganj", []),
                ("Ghoraghat", "ঘোড়াঘাট", "ghoraghat", []), ("Birampur", "বিরামপুর", "birampur", []),
                ("Parbatipur", "পার্বতীপুর", "parbatipur", []), ("Bochaganj", "বোচাগঞ্জ", "bochaganj", []),
                ("Kaharol", "কাহারোল", "kaharol", []), ("Fulbari", "ফুলবাড়ী", "fulbari", []),
                ("Dinajpur Sadar", "দিনাজপুর সদর", "dinajpursadar", []), ("Hakimpur", "হাকিমপুর", "hakimpur", ["হিলি"]),
                ("Khansama", "খানসামা", "khansama", []), ("Birol", "বিরল", "birol", []),
                ("Chirirbandar", "চিরিরবন্দর", "chirirbandar", [])]),
            ("Lalmonirhat", "লালমনিরহাট", "lalmonirhat.gov.bd", [
                ("Lalmonirhat Sadar", "লালমনিরহাট সদর", "sadar", []), ("Kaliganj", "কালীগঞ্জ", "kaliganj", []),
                ("Hatibandha", "হাতীবান্ধা", "hatibandha", []), ("Patgram", "পাটগ্রাম", "patgram", []),
                ("Aditmari", "আদিতমারী", "aditmari", ["~আতিদমারী"])]),
            ("Nilphamari", "নীলফামারী", "nilphamari.gov.bd", [
                ("Syedpur", "সৈয়দপুর", "syedpur", ["সৈদপুর"]), ("Domar", "ডোমার", "domar", []),
                ("Dimla", "ডিমলা", "dimla", []), ("Jaldhaka", "জলঢাকা", "jaldhaka", []),
                ("Kishorganj", "কিশোরগঞ্জ", "kishorganj", ["কিশোরীগঞ্জ"]),
                ("Nilphamari Sadar", "নীলফামারী সদর", "nilphamarisadar", [])]),
            ("Gaibandha", "গাইবান্ধা", "gaibandha.gov.bd", [
                ("Sadullapur", "সাদুল্লাপুর", "sadullapur", ["সাদুল্যাপুর"]),
                ("Gaibandha Sadar", "গাইবান্ধা সদর", "gaibandhasadar", []),
                ("Palashbari", "পলাশবাড়ী", "palashbari", []), ("Saghata", "সাঘাটা", "saghata", []),
                ("Gobindaganj", "গোবিন্দগঞ্জ", "gobindaganj", []), ("Sundarganj", "সুন্দরগঞ্জ", "sundarganj", []),
                ("Phulchari", "ফুলছড়ি", "phulchari", [])]),
            ("Thakurgaon", "ঠাকুরগাঁও", "thakurgaon.gov.bd", [
                ("Thakurgaon Sadar", "ঠাকুরগাঁও সদর", "thakurgaonsadar", []), ("Pirganj", "পীরগঞ্জ", "pirganj", []),
                ("Ranisankail", "রাণীশংকৈল", "ranisankail", []), ("Haripur", "হরিপুর", "haripur", []),
                ("Baliadangi", "বালিয়াডাঙ্গী", "baliadangi", ["~বালয়িাডাঙ্গী"]),
                ("Ruhia", "রুহিয়া", "ruhia", []), ("Bhulli", "ভূল্লী", "bhulli", [])]),
            ("Kurigram", "কুড়িগ্রাম", "kurigram.gov.bd", [
                ("Kurigram Sadar", "কুড়িগ্রাম সদর", "kurigramsadar", []),
                ("Nageshwari", "নাগেশ্বরী", "nageshwari", []), ("Bhurungamari", "ভুরুঙ্গামারী", "bhurungamari", []),
                ("Phulbari", "ফুলবাড়ী", "phulbari", []), ("Rajarhat", "রাজারহাট", "rajarhat", []),
                ("Ulipur", "উলিপুর", "ulipur", []), ("Chilmari", "চিলমারী", "chilmari", []),
                ("Rowmari", "রৌমারী", "rowmari", []), ("Charrajibpur", "চর রাজিবপুর", "charrajibpur", ["রাজিবপুর"])]),
        ]),
    # Dhaka: DC hosts from the divisional portal's menu (dhakadiv.gov.bd), upazila subdomains from the national portal's
    # office registry (bangladesh.gov.bd/views/union-list); Bangla names as on dhakadiv.gov.bd "জেলা ও উপজেলা".
    # The city itself is under the Dhaka North/South City Corporations (not upazilas or unions).
    "dhaka": dict(
        code="dhk", name_en="Dhaka", name_bn="ঢাকা", portal="dhakadiv.gov.bd", head="Dhaka",
        districts=[
            ("Narsingdi", "নরসিংদী", "narsingdi.gov.bd", [
                ("Belabo", "বেলাবো", "belabo", ["বেলাব"]), ("Monohardi", "মনোহরদী", "monohardi", []),
                ("Narsingdi Sadar", "নরসিংদী সদর", "narsingdisadar", []), ("Palash", "পলাশ", "palash", []),
                ("Raipura", "রায়পুরা", "raipura", []), ("Shibpur", "শিবপুর", "shibpur", [])]),
            ("Gazipur", "গাজীপুর", "gazipur.gov.bd", [
                ("Kaliganj", "কালীগঞ্জ", "kaliganj", []), ("Kaliakair", "কালিয়াকৈর", "kaliakair", []),
                ("Kapasia", "কাপাসিয়া", "kapasia", []), ("Gazipur Sadar", "গাজীপুর সদর", "sadar", []),
                ("Sreepur", "শ্রীপুর", "sreepur", [])]),
            ("Shariatpur", "শরীয়তপুর", "shariatpur.gov.bd", [
                ("Shariatpur Sadar", "শরিয়তপুর সদর", "sadar", ["শরীয়তপুর সদর"]), ("Naria", "নড়িয়া", "naria", []),
                ("Zajira", "জাজিরা", "zajira", []), ("Gosairhat", "গোসাইরহাট", "gosairhat", []),
                ("Bhedarganj", "ভেদরগঞ্জ", "bhedarganj", []), ("Damudya", "ডামুড্যা", "damudya", [])]),
            ("Narayanganj", "নারায়ণগঞ্জ", "narayanganj.gov.bd", [
                ("Araihazar", "আড়াইহাজার", "araihazar", []), ("Bandar", "বন্দর", "bandar", []),
                ("Narayanganj Sadar", "নারায়নগঞ্জ সদর", "narayanganjsadar", []), ("Rupganj", "রূপগঞ্জ", "rupganj", []),
                ("Sonargaon", "সোনারগাঁ", "sonargaon", ["সোনারগাঁও"])]),
            ("Tangail", "টাঙ্গাইল", "tangail.gov.bd", [
                ("Basail", "বাসাইল", "basail", []), ("Bhuapur", "ভুয়াপুর", "bhuapur", ["ভূঞাপুর", "ভুঞাপুর"]),
                ("Delduar", "দেলদুয়ার", "delduar", []), ("Ghatail", "ঘাটাইল", "ghatail", []),
                ("Gopalpur", "গোপালপুর", "gopalpur", []), ("Madhupur", "মধুপুর", "madhupur", []),
                ("Mirzapur", "মির্জাপুর", "mirzapur", []), ("Nagarpur", "নাগরপুর", "nagarpur", []),
                ("Sakhipur", "সখিপুর", "sakhipur", []), ("Tangail Sadar", "টাঙ্গাইল সদর", "tangailsadar", []),
                ("Kalihati", "কালিহাতী", "kalihati", []), ("Dhanbari", "ধনবাড়ী", "dhanbari", [])]),
            ("Kishoreganj", "কিশোরগঞ্জ", "kishoreganj.gov.bd", [
                ("Itna", "ইটনা", "itna", []), ("Katiadi", "কটিয়াদী", "katiadi", []), ("Bhairab", "ভৈরব", "bhairab", []),
                ("Tarail", "তাড়াইল", "tarail", []), ("Hossainpur", "হোসেনপুর", "hossainpur", []),
                ("Pakundia", "পাকুন্দিয়া", "pakundia", []), ("Kuliarchar", "কুলিয়ারচর", "kuliarchar", []),
                ("Kishoreganj Sadar", "কিশোরগঞ্জ সদর", "kishoreganjsadar", []),
                ("Karimgonj", "করিমগঞ্জ", "karimgonj", []), ("Bajitpur", "বাজিতপুর", "bajitpur", []),
                ("Austagram", "অষ্টগ্রাম", "austagram", []), ("Mithamoin", "মিঠামইন", "mithamoin", []),
                ("Nikli", "নিকলী", "nikli", [])]),
            ("Manikganj", "মানিকগঞ্জ", "manikganj.gov.bd", [
                ("Harirampur", "হরিরামপুর", "harirampur", []), ("Saturia", "সাটুরিয়া", "saturia", ["~সাটুরিযা"]),
                ("Manikganj Sadar", "মানিকগঞ্জ সদর", "sadar", []), ("Gior", "ঘিওর", "gior", []),
                ("Shibaloy", "শিবালয়", "shibaloy", []), ("Doulatpur", "দৌলতপুর", "daulatpur", []),
                ("Singiar", "সিংগাইর", "singair", [])]),
            ("Dhaka", "ঢাকা", "dhaka.gov.bd", [
                ("Savar", "সাভার", "savar", []), ("Dhamrai", "ধামরাই", "dhamrai", []),
                ("Keraniganj", "কেরাণীগঞ্জ", "keraniganj", []), ("Nawabganj", "নবাবগঞ্জ", "nawabganj", []),
                ("Dohar", "দোহার", "dohar", [])]),
            ("Munshiganj", "মুন্সীগঞ্জ", "munshiganj.gov.bd", [
                ("Munshiganj Sadar", "মুন্সিগঞ্জ সদর", "sadar", []), ("Sreenagar", "শ্রীনগর", "sreenagar", []),
                ("Sirajdikhan", "সিরাজদিখান", "sirajdikhan", []), ("Louhajanj", "লৌহজং", "louhajanj", []),
                ("Gajaria", "গজারিয়া", "gajaria", []), ("Tongibari", "টংগীবাড়ি", "tongibari", [])]),
            ("Rajbari", "রাজবাড়ী", "rajbari.gov.bd", [
                ("Rajbari Sadar", "রাজবাড়ী সদর", "sadar", []), ("Goalanda", "গোয়ালন্দ", "goalanda", []),
                ("Pangsa", "পাংশা", "pangsa", []), ("Baliakandi", "বালিয়াকান্দি", "baliakandi", []),
                ("Kalukhali", "কালুখালী", "kalukhali", [])]),
            ("Madaripur", "মাদারীপুর", "madaripur.gov.bd", [
                ("Madaripur Sadar", "মাদারীপুর সদর", "sadar", []), ("Shibchar", "শিবচর", "shibchar", []),
                ("Kalkini", "কালকিনি", "kalkini", []), ("Rajoir", "রাজৈর", "rajoir", []), ("Dasar", "ডাসার", "dasar", [])]),
            ("Gopalganj", "গোপালগঞ্জ", "gopalganj.gov.bd", [
                ("Gopalganj Sadar", "গোপালগঞ্জ সদর", "sadar", []), ("Kashiani", "কাশিয়ানী", "kashiani", []),
                ("Tungipara", "টুংগীপাড়া", "tungipara", []), ("Kotalipara", "কোটালীপাড়া", "kotalipara", []),
                ("Muksudpur", "মুকসুদপুর", "muksudpur", [])]),
            ("Faridpur", "ফরিদপুর", "faridpur.gov.bd", [
                ("Faridpur Sadar", "ফরিদপুর সদর", "sadar", []), ("Alfadanga", "আলফাডাঙ্গা", "alfadanga", []),
                ("Boalmari", "বোয়ালমারী", "boalmari", []), ("Sadarpur", "সদরপুর", "sadarpur", []),
                ("Nagarkanda", "নগরকান্দা", "nagarkanda", []), ("Bhanga", "ভাঙ্গা", "bhanga", []),
                ("Charbhadrasan", "চরভদ্রাসন", "charbhadrasan", []), ("Madhukhali", "মধুখালী", "madhukhali", []),
                ("Saltha", "সালথা", "saltha", [])]),
        ]),
    # Chattogram: DC hosts verified by home-page title and by the national portal's office registry
    # (bangladesh.gov.bd/views/union-list), which also gives the upazila subdomains. The divisional portal
    # (chittagongdiv.gov.bd) does not link the DC portals. 'aliases': other hosts serving the same DC site, used in
    # links on the portals (chittagong.gov.bd = chattogram.gov.bd; the new Bangara upazila is on cumilla.gov.bd).
    # A subdomain containing a dot is a full host.
    "chattogram": dict(
        code="ctg", name_en="Chattogram", name_bn="চট্টগ্রাম", portal="chittagongdiv.gov.bd", head="Chattogram",
        aliases={"chattogram.gov.bd": ["chittagong.gov.bd"], "comilla.gov.bd": ["cumilla.gov.bd"]},
        districts=[
            ("Cumilla", "কুমিল্লা", "comilla.gov.bd", [
                ("Debidwar", "দেবিদ্বার", "debidwar", []), ("Barura", "বরুড়া", "barura", []),
                ("Brahmanpara", "ব্রাহ্মণপাড়া", "brahmanpara", []), ("Chandina", "চান্দিনা", "chandina", []),
                ("Chauddagram", "চৌদ্দগ্রাম", "chauddagram", []), ("Daudkandi", "দাউদকান্দি", "daudkandi", []),
                ("Homna", "হোমনা", "homna", []), ("Laksam", "লাকসাম", "laksam", []),
                ("Muradnagar", "মুরাদনগর", "muradnagar", []), ("Nangalkot", "নাঙ্গলকোট", "nangalkot", []),
                ("Comilla Sadar", "কুমিল্লা সদর", "comillasadar", ["আদর্শ সদর", "কুমিল্লা আদর্শ সদর", "~আর্দশ সদর"]),
                ("Meghna", "মেঘনা", "meghna", []), ("Monohargonj", "মনোহরগঞ্জ", "monohargonj", []),
                ("Sadarsouth", "সদর দক্ষিণ", "sadarsouth", ["কুমিল্লা সদর দক্ষিণ"]), ("Titas", "তিতাস", "titas", []),
                ("Burichang", "বুড়িচং", "burichang", []), ("Lalmai", "লালমাই", "lalmai", []),
                ("Bangara", "বাঙ্গরা", "bangara.cumilla.gov.bd", [])]),
            ("Feni", "ফেনী", "feni.gov.bd", [
                ("Chhagalnaiya", "ছাগলনাইয়া", "chhagalnaiya", []), ("Feni Sadar", "ফেনী সদর", "sadar", []),
                ("Sonagazi", "সোনাগাজী", "sonagazi", []), ("Fulgazi", "ফুলগাজী", "fulgazi", []),
                ("Parshuram", "পরশুরাম", "parshuram", []),
                ("Daganbhuiyan", "দাগনভূঞা", "daganbhuiyan", ["দাগনভূইঞা"])]),
            ("Brahmanbaria", "ব্রাহ্মণবাড়িয়া", "brahmanbaria.gov.bd", [
                ("Brahmanbaria Sadar", "ব্রাহ্মণবাড়িয়া সদর", "sadar", []), ("Kasba", "কসবা", "kasba", []),
                ("Nasirnagar", "নাসিরনগর", "nasirnagar", []), ("Sarail", "সরাইল", "sarail", []),
                ("Ashuganj", "আশুগঞ্জ", "ashuganj", []), ("Akhaura", "আখাউড়া", "akhaura", []),
                ("Nabinagar", "নবীনগর", "nabinagar", []), ("Bancharampur", "বাঞ্ছারামপুর", "bancharampur", []),
                ("Bijoynagar", "বিজয়নগর", "bijoynagar", [])]),
            ("Rangamati", "রাঙ্গামাটি", "rangamati.gov.bd", [
                ("Rangamati Sadar", "রাঙ্গামাটি সদর", "sadar", []), ("Kaptai", "কাপ্তাই", "kaptai", []),
                ("Kawkhali", "কাউখালী", "kawkhali", []), ("Baghaichari", "বাঘাইছড়ি", "baghaichari", []),
                ("Barkal", "বরকল", "barkal", []), ("Langadu", "লংগদু", "langadu", []),
                ("Rajasthali", "রাজস্থলী", "rajasthali", []), ("Belaichari", "বিলাইছড়ি", "belaichari", []),
                ("Juraichari", "জুরাছড়ি", "juraichari", []), ("Naniarchar", "নানিয়ারচর", "naniarchar", [])]),
            ("Noakhali", "নোয়াখালী", "noakhali.gov.bd", [
                ("Noakhali Sadar", "নোয়াখালী সদর", "sadar", []), ("Companiganj", "কোম্পানীগঞ্জ", "companiganj", []),
                ("Begumganj", "বেগমগঞ্জ", "begumganj", []), ("Hatia", "হাতিয়া", "hatia", []),
                ("Subarnachar", "সুবর্ণচর", "subarnachar", []), ("Kabirhat", "কবিরহাট", "kabirhat", []),
                ("Senbug", "সেনবাগ", "senbug", []), ("Chatkhil", "চাটখিল", "chatkhil", []),
                ("Sonaimori", "সোনাইমুড়ী", "sonaimuri", [])]),
            ("Chandpur", "চাঁদপুর", "chandpur.gov.bd", [
                ("Haimchar", "হাইমচর", "haimchar", []), ("Kachua", "কচুয়া", "kachua", []),
                ("Shahrasti", "শাহরাস্তি", "shahrasti", []), ("Chandpur Sadar", "চাঁদপুর সদর", "sadar", []),
                ("Matlab South", "মতলব দক্ষিণ", "matlabsouth", []), ("Hajiganj", "হাজীগঞ্জ", "hajiganj", []),
                ("Matlab North", "মতলব উত্তর", "matlabnorth", []), ("Faridgonj", "ফরিদগঞ্জ", "faridgonj", [])]),
            ("Lakshmipur", "লক্ষ্মীপুর", "lakshmipur.gov.bd", [
                ("Lakshmipur Sadar", "লক্ষ্মীপুর সদর", "sadar", []), ("Kamalnagar", "কমলনগর", "kamalnagar", []),
                ("Raipur", "রায়পুর", "raipur", []), ("Ramgati", "রামগতি", "ramgati", []),
                ("Ramganj", "রামগঞ্জ", "ramganj", []), ("Chandraganj", "চন্দ্রগঞ্জ", "chandraganj", [])]),
            ("Chattogram", "চট্টগ্রাম", "chattogram.gov.bd", [
                ("Rangunia", "রাঙ্গুনিয়া", "rangunia", []), ("Sitakunda", "সীতাকুন্ড", "sitakunda", []),
                ("Mirsharai", "মীরসরাই", "mirsharai", []), ("Patiya", "পটিয়া", "patiya", []),
                ("Sandwip", "সন্দ্বীপ", "sandwip", []), ("Banshkhali", "বাঁশখালী", "banshkhali", []),
                ("Boalkhali", "বোয়ালখালী", "boalkhali", []), ("Anwara", "আনোয়ারা", "anwara", []),
                ("Chandanaish", "চন্দনাইশ", "chandanaish", []), ("Satkania", "সাতকানিয়া", "satkania", []),
                ("Lohagara", "লোহাগাড়া", "lohagara", ["লোহাগড়া"]), ("Hathazari", "হাটহাজারী", "hathazari", []),
                ("Fatikchhari", "ফটিকছড়ি", "fatikchhari", []), ("Raozan", "রাউজান", "raozan", []),
                ("Karnafuli", "কর্ণফুলী", "karnafuli", []),
                ("Fatikchhari Uttar", "ফটিকছড়ি উত্তর", "fatikchhariuttar", [])]),
            ("Cox's Bazar", "কক্সবাজার", "coxsbazar.gov.bd", [
                ("Coxsbazar Sadar", "কক্সবাজার সদর", "sadar", []), ("Chakaria", "চকরিয়া", "chakaria", ["চকোরিয়া"]),
                ("Kutubdia", "কুতুবদিয়া", "kutubdia", []), ("Ukhiya", "উখিয়া", "ukhiya", []),
                ("Moheshkhali", "মহেশখালী", "moheshkhali", []), ("Pekua", "পেকুয়া", "pekua", []),
                ("Ramu", "রামু", "ramu", []), ("Teknaf", "টেকনাফ", "teknaf", []), ("Eidgaon", "ঈদগাঁও", "eidgaon", [])]),
            ("Khagrachhari", "খাগড়াছড়ি", "khagrachhari.gov.bd", [
                ("Khagrachhari Sadar", "খাগড়াছড়ি সদর", "sadar", []), ("Dighinala", "দিঘীনালা", "dighinala", []),
                ("Panchari", "পানছড়ি", "panchari", []), ("Laxmichhari", "লক্ষীছড়ি", "laxmichhari", ["লক্ষ্মীছড়ি"]),
                ("Mohalchari", "মহালছড়ি", "mohalchari", []), ("Manikchari", "মানিকছড়ি", "manikchari", []),
                ("Ramgarh", "রামগড়", "ramgarh", []), ("Matiranga", "মাটিরাঙ্গা", "matiranga", []),
                ("Guimara", "গুইমারা", "guimara", ["~গু্ইমারা"])]),
            ("Bandarban", "বান্দরবান", "bandarban.gov.bd", [
                ("Bandarban Sadar", "বান্দরবান সদর", "sadar", []), ("Alikadam", "আলীকদম", "alikadam", []),
                ("Naikhongchhari", "নাইক্ষ্যংছড়ি", "naikhongchhari", ["~নাইক্ষ্যংড়ি"]), ("Rowangchhari", "রোয়াংছড়ি", "rowangchhari", []),
                ("Lama", "লামা", "lama", []), ("Ruma", "রুমা", "ruma", []), ("Thanchi", "থানচি", "thanchi", [])]),
        ]),
    # Khulna: DC hosts verified by home-page title ("হোম | <জেলা> জেলা") and by the national portal's office registry
    # (bangladesh.gov.bd/views/union-list), which also gives the upazila subdomains (Kushtia's Mirpur is 'mirpur', the
    # seed's mirpurkushtia answers "Site is not available"; Khulna's Dakop is 'dacope', dakop.khulna.gov.bd serves the
    # same portal). The registry uses jashore.gov.bd; jessore.gov.bd serves the same DC site (same title, own canonical).
    "khulna": dict(
        code="khl", name_en="Khulna", name_bn="খুলনা", portal="khulnadiv.gov.bd", head="Khulna",
        aliases={"jashore.gov.bd": ["jessore.gov.bd"]},
        districts=[
            ("Khulna", "খুলনা", "khulna.gov.bd", [
                ("Paikgasa", "পাইকগাছা", "paikgasa", []), ("Fultola", "ফুলতলা", "fultola", []),
                ("Digholia", "দিঘলিয়া", "digholia", []), ("Rupsha", "রূপসা", "rupsha", []),
                ("Terokhada", "তেরখাদা", "terokhada", []), ("Dumuria", "ডুমুরিয়া", "dumuria", []),
                ("Botiaghata", "বটিয়াঘাটা", "botiaghata", []), ("Dakop", "দাকোপ", "dacope", []),
                ("Koyra", "কয়রা", "koyra", [])]),
            ("Jashore", "যশোর", "jashore.gov.bd", [
                ("Manirampur", "মণিরামপুর", "manirampur", []), ("Abhaynagar", "অভয়নগর", "abhaynagar", []),
                ("Bagherpara", "বাঘারপাড়া", "bagherpara", ["বাঘেরপাড়া"]), ("Chougachha", "চৌগাছা", "chougachha", []),
                ("Jhikargacha", "ঝিকরগাছা", "jhikargacha", []), ("Keshabpur", "কেশবপুর", "keshabpur", []),
                ("Jessore Sadar", "যশোর সদর", "sadar", []), ("Sharsha", "শার্শা", "sharsha", [])]),
            ("Satkhira", "সাতক্ষীরা", "satkhira.gov.bd", [
                ("Assasuni", "আশাশুনি", "assasuni", []), ("Debhata", "দেবহাটা", "debhata", []),
                ("Kalaroa", "কলারোয়া", "kalaroa", []), ("Satkhira Sadar", "সাতক্ষীরা সদর", "satkhirasadar", []),
                ("Shyamnagar", "শ্যামনগর", "shyamnagar", []), ("Tala", "তালা", "tala", []),
                ("Kaliganj", "কালিগঞ্জ", "kaliganj", [])]),
            ("Meherpur", "মেহেরপুর", "meherpur.gov.bd", [
                ("Mujibnagar", "মুজিবনগর", "mujibnagar", []), ("Meherpur Sadar", "মেহেরপুর সদর", "meherpursadar", []),
                ("Gangni", "গাংনী", "gangni", [])]),
            ("Narail", "নড়াইল", "narail.gov.bd", [
                ("Narail Sadar", "নড়াইল সদর", "narailsadar", []), ("Lohagara", "লোহাগড়া", "lohagara", []),
                ("Kalia", "কালিয়া", "kalia", [])]),
            ("Chuadanga", "চুয়াডাঙ্গা", "chuadanga.gov.bd", [
                ("Chuadanga Sadar", "চুয়াডাঙ্গা সদর", "chuadangasadar", []), ("Alamdanga", "আলমডাঙ্গা", "alamdanga", []),
                ("Damurhuda", "দামুড়হুদা", "damurhuda", []), ("Jibannagar", "জীবননগর", "jibannagar", [])]),
            ("Kushtia", "কুষ্টিয়া", "kushtia.gov.bd", [
                ("Kushtia Sadar", "কুষ্টিয়া সদর", "kushtiasadar", []), ("Kumarkhali", "কুমারখালী", "kumarkhali", []),
                ("Khoksa", "খোকসা", "khoksa", []), ("Mirpur", "মিরপুর", "mirpur", []),
                ("Daulatpur", "দৌলতপুর", "daulatpur", []), ("Bheramara", "ভেড়ামারা", "bheramara", [])]),
            ("Magura", "মাগুরা", "magura.gov.bd", [
                ("Shalikha", "শালিখা", "shalikha", []), ("Sreepur", "শ্রীপুর", "sreepur", []),
                ("Magura Sadar", "মাগুরা সদর", "magurasadar", []), ("Mohammadpur", "মহম্মদপুর", "mohammadpur", ["মোহাম্মদপুর", "মহাম্মদপুর"])]),
            ("Bagerhat", "বাগেরহাট", "bagerhat.gov.bd", [
                ("Fakirhat", "ফকিরহাট", "fakirhat", []), ("Bagerhat Sadar", "বাগেরহাট সদর", "sadar", []),
                ("Mollahat", "মোল্লাহাট", "mollahat", []), ("Sarankhola", "শরণখোলা", "sarankhola", []),
                ("Rampal", "রামপাল", "rampal", []), ("Morrelganj", "মোড়েলগঞ্জ", "morrelganj", ["মোরেলগঞ্জ"]),
                ("Kachua", "কচুয়া", "kachua", []), ("Mongla", "মোংলা", "mongla", []),
                ("Chitalmari", "চিতলমারী", "chitalmari", [])]),
            ("Jhenaidah", "ঝিনাইদহ", "jhenaidah.gov.bd", [
                ("Jhenaidah Sadar", "ঝিনাইদহ সদর", "sadar", []), ("Shailkupa", "শৈলকুপা", "shailkupa", []),
                ("Harinakundu", "হরিণাকুন্ডু", "harinakundu", []), ("Kaliganj", "কালীগঞ্জ", "kaliganj", []),
                ("Kotchandpur", "কোটচাঁদপুর", "kotchandpur", []), ("Moheshpur", "মহেশপুর", "moheshpur", [])]),
        ]),
    # Barishal: DC hosts verified by home-page title ("হোম | <জেলা> জেলা") and by the national portal's office registry
    # (bangladesh.gov.bd/views/union-list), which gives the upazila subdomains. The divisional portal links the DC portal
    # as barishal.gov.bd; barisal.gov.bd serves the same site (same title), and the registry has the Barishal upazila
    # portals on barisal.gov.bd (full hosts below). Jhalokathi's DC portal is jhalakathi.gov.bd (jhalokathi.gov.bd does
    # not resolve). Zianagar's portal calls the upazila ইন্দুরকানী in its own menu ("এক নজরে ইন্দুরকানী").
    "barishal": dict(
        code="bar", name_en="Barishal", name_bn="বরিশাল", portal="barishaldiv.gov.bd", head="Barishal",
        aliases={"barishal.gov.bd": ["barisal.gov.bd"]},
        districts=[
            ("Barishal", "বরিশাল", "barishal.gov.bd", [
                ("Barisal Sadar", "বরিশাল সদর", "barisalsadar.barisal.gov.bd", []),
                ("Bakerganj", "বাকেরগঞ্জ", "bakerganj.barisal.gov.bd", []),
                ("Babuganj", "বাবুগঞ্জ", "babuganj.barisal.gov.bd", []),
                ("Wazirpur", "উজিরপুর", "wazirpur.barisal.gov.bd", []),
                ("Banaripara", "বানারীপাড়া", "banaripara.barisal.gov.bd", []),
                ("Gournadi", "গৌরনদী", "gournadi.barisal.gov.bd", []),
                ("Agailjhara", "আগৈলঝাড়া", "agailjhara.barisal.gov.bd", ["~আগৈলঝড়া"]),
                ("Mehendiganj", "মেহেন্দিগঞ্জ", "mehendiganj.barisal.gov.bd", []),
                ("Muladi", "মুলাদী", "muladi.barisal.gov.bd", []), ("Hizla", "হিজলা", "hizla.barisal.gov.bd", [])]),
            ("Jhalokathi", "ঝালকাঠি", "jhalakathi.gov.bd", [
                ("Jhalakathi Sadar", "ঝালকাঠি সদর", "sadar", []), ("Kathalia", "কাঠালিয়া", "kathalia", []),
                ("Nalchity", "নলছিটি", "nalchity", []), ("Rajapur", "রাজাপুর", "rajapur", [])]),
            ("Patuakhali", "পটুয়াখালী", "patuakhali.gov.bd", [
                ("Bauphal", "বাউফল", "bauphal", []), ("Patuakhali Sadar", "পটুয়াখালী সদর", "sadar", []),
                ("Dumki", "দুমকি", "dumki", []), ("Dashmina", "দশমিনা", "dashmina", []),
                ("Kalapara", "কলাপাড়া", "kalapara", []), ("Mirzaganj", "মির্জাগঞ্জ", "mirzaganj", []),
                ("Galachipa", "গলাচিপা", "galachipa", []), ("Rangabali", "রাঙ্গাবালী", "rangabali", [])]),
            ("Pirojpur", "পিরোজপুর", "pirojpur.gov.bd", [
                ("Pirojpur Sadar", "পিরোজপুর সদর", "sadar", []), ("Nazirpur", "নাজিরপুর", "nazirpur", []),
                ("Kawkhali", "কাউখালী", "kawkhali", []), ("Zianagar", "জিয়ানগর", "zianagar", ["ইন্দুরকানী"]),
                ("Bhandaria", "ভান্ডারিয়া", "bhandaria", []), ("Mathbaria", "মঠবাড়ীয়া", "mathbaria", []),
                ("Nesarabad", "নেছারাবাদ", "nesarabad", ["নেছারাবাদ (স্বরূপকাঠি)"])]),
            ("Bhola", "ভোলা", "bhola.gov.bd", [
                ("Bhola Sadar", "ভোলা সদর", "sadar", []), ("Borhan Sddin", "বোরহানউদ্দিন", "borhanuddin", []),
                ("Charfesson", "চরফ্যাশন", "charfesson", []), ("Doulatkhan", "দৌলতখান", "doulatkhan", []),
                ("Monpura", "মনপুরা", "monpura", []), ("Tazumuddin", "তজুমদ্দিন", "tazumuddin", ["তজমুদ্দিন"]),
                ("Lalmohan", "লালমোহন", "lalmohan", [])]),
            ("Barguna", "বরগুনা", "barguna.gov.bd", [
                ("Amtali", "আমতলী", "amtali", []), ("Barguna Sadar", "বরগুনা সদর", "sadar", []),
                ("Betagi", "বেতাগী", "betagi", []), ("Bamna", "বামনা", "bamna", []),
                ("Pathorghata", "পাথরঘাটা", "pathorghata", []), ("Taltali", "তালতলী", "taltali", [])]),
        ]),
    # Sylhet: divisional portal sylhetdiv.gov.bd ("হোম | সিলেট বিভাগ"); DC hosts verified by home-page title ("হোম | <জেলা>
    # জেলা") and the 41 upazila subdomains by the national portal's office registry (bangladesh.gov.bd/views/union-list)
    # and each portal's title ("হোম | <উপজেলা> উপজেলা"). sylhet.gov.bd sends its Let's Encrypt certificate with a Sectigo
    # chain (see DV_AIA). South Sunamganj (seed key, দক্ষিণ সুনামগঞ্জ) is শান্তিগঞ্জ on the registry and on its portal
    # shantiganj.sunamganj.gov.bd; southsunamganj.sunamganj.gov.bd answers "Site is not available".
    "sylhet": dict(
        code="syl", name_en="Sylhet", name_bn="সিলেট", portal="sylhetdiv.gov.bd", head="Sylhet",
        districts=[
            ("Sylhet", "সিলেট", "sylhet.gov.bd", [
                ("Sylhet Sadar", "সিলেট সদর", "sylhetsadar", []), ("Balaganj", "বালাগঞ্জ", "balaganj", []),
                ("Beanibazar", "বিয়ানীবাজার", "beanibazar", []), ("Bishwanath", "বিশ্বনাথ", "bishwanath", []),
                ("Companiganj", "কোম্পানীগঞ্জ", "companiganj", []), ("Fenchuganj", "ফেঞ্চুগঞ্জ", "fenchuganj", []),
                ("Golapganj", "গোলাপগঞ্জ", "golapganj", []), ("Gowainghat", "গোয়াইনঘাট", "gowainghat", []),
                ("Jaintiapur", "জৈন্তাপুর", "jaintiapur", []), ("Kanaighat", "কানাইঘাট", "kanaighat", []),
                ("Zakiganj", "জকিগঞ্জ", "zakiganj", []), ("Dakshinsurma", "দক্ষিণ সুরমা", "dakshinsurma", []),
                ("Osmaninagar", "ওসমানী নগর", "osmaninagar", [])]),
            ("Moulvibazar", "মৌলভীবাজার", "moulvibazar.gov.bd", [
                ("Moulvibazar Sadar", "মৌলভীবাজার সদর", "moulvibazarsadar", []), ("Barlekha", "বড়লেখা", "barlekha", []),
                ("Juri", "জুড়ী", "juri", []), ("Kamolganj", "কমলগঞ্জ", "kamolganj", []),
                ("Kulaura", "কুলাউড়া", "kulaura", []), ("Rajnagar", "রাজনগর", "rajnagar", []),
                ("Sreemangal", "শ্রীমঙ্গল", "sreemangal", [])]),
            ("Habiganj", "হবিগঞ্জ", "habiganj.gov.bd", [
                ("Habiganj Sadar", "হবিগঞ্জ সদর", "habiganjsadar", []), ("Nabiganj", "নবীগঞ্জ", "nabiganj", []),
                ("Bahubal", "বাহুবল", "bahubal", []), ("Ajmiriganj", "আজমিরীগঞ্জ", "ajmiriganj", []),
                ("Baniachong", "বানিয়াচং", "baniachong", []), ("Lakhai", "লাখাই", "lakhai", []),
                ("Chunarughat", "চুনারুঘাট", "chunarughat", []), ("Madhabpur", "মাধবপুর", "madhabpur", []),
                ("Shayestaganj", "শায়েস্তাগঞ্জ", "shayestaganj", [])]),
            ("Sunamganj", "সুনামগঞ্জ", "sunamganj.gov.bd", [
                ("Sunamganj Sadar", "সুনামগঞ্জ সদর", "sadar", []),
                ("South Sunamganj", "দক্ষিণ সুনামগঞ্জ", "shantiganj", ["শান্তিগঞ্জ"]),
                ("Bishwambarpur", "বিশ্বম্ভরপুর", "bishwambarpur", []), ("Chhatak", "ছাতক", "chhatak", []),
                ("Jagannathpur", "জগন্নাথপুর", "jagannathpur", []), ("Dowarabazar", "দোয়ারাবাজার", "dowarabazar", []),
                ("Tahirpur", "তাহিরপুর", "tahirpur", []), ("Dharmapasha", "ধর্মপাশা", "dharmapasha", []),
                ("Jamalganj", "জামালগঞ্জ", "jamalganj", []), ("Shalla", "শাল্লা", "shalla", []),
                ("Derai", "দিরাই", "derai", []), ("Madhyanagar", "মধ্যনগর", "madhyanagar", [])]),
        ]),
    # Mymensingh: divisional portal mymensinghdiv.gov.bd ("হোম | ময়মনসিংহ বিভাগ"); DC hosts verified by home-page title
    # ("হোম | <জেলা> জেলা") and the 35 upazila subdomains by the national portal's office registry
    # (bangladesh.gov.bd/views/union-list), which also has southgafargaon.mymensingh.gov.bd ("দক্ষিণ গফরগাঁও উপজেলা")
    # without any union portal; it is not a seed upazila and not configured here.
    "mymensingh": dict(
        code="mym", name_en="Mymensingh", name_bn="ময়মনসিংহ", portal="mymensinghdiv.gov.bd", head="Mymensingh",
        districts=[
            ("Mymensingh", "ময়মনসিংহ", "mymensingh.gov.bd", [
                ("Mymensingh Sadar", "ময়মনসিংহ সদর", "mymensinghsadar", ["~ময়নসিংহ সদর"]), ("Muktagacha", "মুক্তাগাছা", "muktagacha", []),
                ("Fulbaria", "ফুলবাড়ীয়া", "fulbaria", []), ("Trishal", "ত্রিশাল", "trishal", []),
                ("Bhaluka", "ভালুকা", "bhaluka", []), ("Gafargaon", "গফরগাঁও", "gafargaon", []),
                ("Nandail", "নান্দাইল", "nandail", []), ("Iswarganj", "ঈশ্বরগঞ্জ", "iswarganj", []),
                ("Gouripur", "গৌরীপুর", "gouripur", []), ("Phulpur", "ফুলপুর", "phulpur", []),
                ("Haluaghat", "হালুয়াঘাট", "haluaghat", []), ("Dhobaura", "ধোবাউড়া", "dhobaura", []),
                ("Tarakanda", "তারাকান্দা", "tarakanda", [])]),
            ("Jamalpur", "জামালপুর", "jamalpur.gov.bd", [
                ("Jamalpur Sadar", "জামালপুর সদর", "jamalpursadar", []), ("Melandah", "মেলান্দহ", "melandah", []),
                ("Islampur", "ইসলামপুর", "islampur", []), ("Dewangonj", "দেওয়ানগঞ্জ", "dewangonj", []),
                ("Sarishabari", "সরিষাবাড়ী", "sarishabari", []), ("Madarganj", "মাদারগঞ্জ", "madarganj", []),
                ("Bokshiganj", "বকশীগঞ্জ", "bokshiganj", ["বক্সীগঞ্জ"])]),
            ("Sherpur", "শেরপুর", "sherpur.gov.bd", [
                ("Sherpur Sadar", "শেরপুর সদর", "sherpursadar", []), ("Nalitabari", "নালিতাবাড়ী", "nalitabari", []),
                ("Sreebordi", "শ্রীবরদী", "sreebordi", ["~শ্রীবদী"]), ("Nokla", "নকলা", "nokla", []),
                ("Jhenaigati", "ঝিনাইগাতী", "jhenaigati", [])]),
            ("Netrokona", "নেত্রকোণা", "netrokona.gov.bd", [
                ("Netrokona Sadar", "নেত্রকোণা সদর", "netrokonasadar", []), ("Barhatta", "বারহাট্টা", "barhatta", []),
                ("Durgapur", "দুর্গাপুর", "durgapur", []), ("Kendua", "কেন্দুয়া", "kendua", []),
                ("Atpara", "আটপাড়া", "atpara", []), ("Madan", "মদন", "madan", []),
                ("Khaliajuri", "খালিয়াজুরী", "khaliajuri", []), ("Kalmakanda", "কলমাকান্দা", "kalmakanda", []),
                ("Mohongonj", "মোহনগঞ্জ", "mohongonj", []), ("Purbadhala", "পূর্বধলা", "purbadhala", ["~পূ্র্বধলা"])]),
        ]),
}

# Upazilas listed on the portals in 2026 that the project seed does not have yet: English key is a transliteration
# of the portal subdomain, not printed on the pages.
DV_NEW_UPAZILAS = {("rangpur", "Ruhia"), ("rangpur", "Bhulli"), ("chattogram", "Bangara"), ("chattogram", "Chandraganj"),
                   ("chattogram", "Fatikchhari Uttar")}
DV_BN = "০১২৩৪৫৬৭৮৯"
DV_MONTHS = {"জানুয়ারি": 1, "জানুয়ারী": 1, "ফেব্রুয়ারি": 2, "ফেব্রুয়ারী": 2, "মার্চ": 3, "এপ্রিল": 4, "মে": 5,
             "জুন": 6, "জুলাই": 7, "আগস্ট": 8, "আগষ্ট": 8, "সেপ্টেম্বর": 9, "অক্টোবর": 10, "নভেম্বর": 11,
             "ডিসেম্বর": 12}


def dv_nfc(s):
    return unicodedata.normalize("NFC", s or "")


def dv_asc(s):
    return "".join(str(DV_BN.index(c)) if c in DV_BN else c for c in (s or ""))


class DvFetcher:
    """GET with optional on-disk cache, robots.txt, >= DV_GAP s per host, TLS always verified."""

    def __init__(self, cache=None):
        self.cache = cache
        self.s = requests.Session()
        self.s.headers["User-Agent"] = DV_UA
        self.lock = _dv_threading.Lock()
        self.host_locks, self.last, self.robots = {}, {}, {}
        self.bundle = None
        self.errors = {}
        self.requests = 0

    def _bundle(self):
        with self.lock:
            if self.bundle:
                return self.bundle
            try:
                import certifi
                base = certifi.where()
            except ImportError:
                base = ssl.get_default_verify_paths().cafile or "/etc/ssl/certs/ca-certificates.crt"
            pem = open(base, encoding="utf-8").read()
            for aia in DV_AIA:
                r = requests.get(aia, headers={"User-Agent": DV_UA}, timeout=30)
                r.raise_for_status()
                pem += "\n" + (r.text if r.content.startswith(b"-----BEGIN") else ssl.DER_cert_to_PEM_cert(r.content))
            f = tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False)
            f.write(pem)
            f.close()
            self.bundle = f.name
            return self.bundle

    def _raw(self, url, timeout):
        host = urlparse(url).netloc.lower()
        with self.lock:
            hl = self.host_locks.setdefault(host, _dv_threading.Lock())
        with hl:
            dt = time.time() - self.last.get(host, 0)
            if dt < DV_GAP:
                time.sleep(DV_GAP - dt)
            try:
                self.requests += 1
                return self.s.get(url, timeout=timeout, verify=self._bundle())
            finally:
                self.last[host] = time.time()

    def allowed(self, url):
        p = urlparse(url)
        root = f"{p.scheme}://{p.netloc.lower()}"
        if root not in self.robots:
            rp = _dv_robotparser.RobotFileParser()
            try:
                r = self._raw(root + "/robots.txt", 30)
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            except requests.RequestException:
                rp.parse([])
            self.robots[root] = rp
        return self.robots[root].can_fetch(DV_UA, url)

    def get(self, url, timeout=45):
        """Page text, or None (reason in self.errors[url])."""
        key = hashlib.sha1(url.encode()).hexdigest()
        if self.cache:
            p = os.path.join(self.cache, key)
            if os.path.exists(p):
                return open(p, encoding="utf-8", errors="replace").read()
        try:
            if not self.allowed(url):
                self.errors[url] = "robots.txt disallows"
                return None
            r = self._raw(url, timeout)
        except requests.exceptions.SSLError as e:
            self.errors[url] = f"TLS error: {str(e)[:120]}"
            return None
        except requests.RequestException as e:
            self.errors[url] = f"{type(e).__name__}: {str(e)[:120]}"
            return None
        if r.status_code != 200:
            self.errors[url] = f"HTTP {r.status_code}"
            return None
        t = r.content.decode("utf-8", "replace")
        if self.cache:
            os.makedirs(self.cache, exist_ok=True)
            open(os.path.join(self.cache, key), "w", encoding="utf-8").write(t)
        return t


def dv_text(fragment):
    s = re.sub(r"<script.*?</script>|<style.*?</style>", "", fragment, flags=re.S)
    s = re.sub(r"<br\s*/?>|</p>|</tr>|</li>|</h\d>|</div>", "\n", s)
    s = re.sub(r"</td>|</th>", " | ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ").replace("‌", "").replace("‍", "")
    return dv_nfc("\n".join(re.sub(r"[ \t]+", " ", l).strip() for l in s.split("\n") if l.strip()))


def dv_date(upd):
    m = re.search(r"([০-৯0-9]{1,2})\s+(\S+),\s*([০-৯0-9]{4})", dv_nfc(upd or ""))
    if not m:
        return ""
    mon = {dv_nfc(k): v for k, v in DV_MONTHS.items()}.get(dv_nfc(m.group(2)))
    d, y = dv_asc(m.group(1)), dv_asc(m.group(3))
    return f"{int(y):04d}-{mon:02d}-{int(d):02d}" if mon else ""


def dv_content(t):
    """Main content block of an a2i portal page: dict(updated, date, title, html, text) or None."""
    if not t:
        return None
    i = t.find('data-widget_name="ContentViewerWidget"')
    if i < 0:
        return None
    seg = t[i:]
    j = seg.find("এই কনটেন্টটি শেয়ার")
    if j > 0:
        seg = seg[:j]
    m = re.search(r'content-update-block">\s*<p>\s*(.*?)</p>', seg, re.S)
    upd = dv_nfc(html.unescape(m.group(1)).strip()) if m else ""
    m = re.search(r"<h2>(.*?)</h2>", seg, re.S)
    title = dv_text(m.group(1)) if m else ""
    seg = re.sub(r'encoded-content="[^"]*"', "", seg)
    seg = seg[seg.find(">") + 1:]
    k = seg.find("</h2>")
    body = seg[k + 5:] if k > 0 else seg
    return dict(updated=upd, date=dv_date(upd), title=title, html=body, text=dv_text(body))


def dv_links(fragment, base=""):
    out = []
    for h, x in re.findall(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', fragment or "", flags=re.S):
        h = html.unescape(h).strip()
        out.append((urljoin(base, h) if base else h, dv_text(x)))
    return out


def dv_site(u):
    """Normalise a website (link or printed domain) to https://host/ ; '' if none."""
    u = (u or "").strip().strip("|").strip().replace("http://http://", "http://").replace("https://http://", "http://")
    if not u or u in ("-", "#"):
        return ""
    p = urlparse(u if "://" in u else "http://" + u)
    host = p.netloc.lower().strip(".")
    return f"https://{host}/" if host and "." in host else ""


def dv_redact(s):
    s = re.sub(r"(?:\+?৮৮|\+?88)?[০0][১1][৩-৯3-9](?:[\s\-]?[০-৯0-9]){8}", "[phone]", s)
    return re.sub(r"[\w.\-]+@[\w.\-]+\.\w+", "[email]", s)


def dv_loose(s):
    """Spelling-tolerant key for matching district/upazila names (never used for output)."""
    s = dv_nfc(s)
    s = re.sub(r"উপজেলা(র)?|পরিষদ|জেলা(র)?|[\s:ঃ\-–.,।()]", "", s)
    for a, b in (("ঁ", ""), ("ী", "ি"), ("ূ", "ু"), ("ণ", "ন"), ("ঙ্গ", "ংগ"), ("ঙ", "ং"), ("ৈ", "ৈ"), ("য়", "য়")):
        s = s.replace(a, b)
    return s


class DvDivision:
    def __init__(self, name):
        if name not in DV_DIVISIONS:
            raise SystemExit(f"unknown division {name!r}; configured: {', '.join(sorted(DV_DIVISIONS))}")
        self.key = name
        self.cfg = c = DV_DIVISIONS[name]
        self.code, self.name_en, self.name_bn, self.head = c["code"], c["name_en"], c["name_bn"], c["head"]
        self.districts = {d: dict(name_en=d, name_bn=bn, host=h, upazilas=u) for d, bn, h, u in c["districts"]}
        self.d_key = {dv_loose(v["name_bn"]): d for d, v in self.districts.items()}
        self.u_key, self.misprints = {}, set()
        for d, v in self.districts.items():
            m = self.u_key[d] = {}
            for en, bn, sub, alt in v["upazilas"]:
                for s in [bn] + alt:
                    m[dv_loose(s.lstrip("~"))] = en
                    if s.startswith("~"):
                        self.misprints.add(dv_nfc(s[1:]))
            sadar = [en for en, bn, _, _ in v["upazilas"] if bn.endswith("সদর")]
            if sadar:
                m[dv_loose("সদর")] = sadar[0]

    def district(self, s):
        return self.d_key.get(dv_loose(s))

    def upazila(self, d, s):
        return self.u_key.get(d, {}).get(dv_loose(s))

    def upz_bn(self, d, en):
        return next((bn for e, bn, _, _ in self.districts[d]["upazilas"] if e == en), "")

    def upz_names(self, d, en):
        """Bangla name and the other spellings configured for an upazila."""
        return [x.lstrip("~") for e, bn, _, al in self.districts[d]["upazilas"] if e == en for x in [bn] + al]

    def upz_sub(self, d, en):
        return next((s for e, _, s, _ in self.districts[d]["upazilas"] if e == en), "")

    def upz_site(self, d, en):
        """Upazila portal address: <sub>.<DC host>, or the subdomain itself when it is a full host."""
        sub = self.upz_sub(d, en)
        if not sub:
            return ""
        return f"https://{sub}/" if "." in sub else f"https://{sub}.{self.districts[d]['host']}/"

    def hosts(self, d):
        """The DC host and the other hosts serving the same DC site (config 'aliases')."""
        h = self.districts[d]["host"]
        return [h] + self.cfg.get("aliases", {}).get(h, [])

    def under(self, d, url):
        """True when url is on a subdomain of the district's DC host (or one of its aliases)."""
        n = urlparse(url if "://" in url else "http://" + url).netloc.lower()
        return any(n.endswith("." + h) for h in self.hosts(d))


DV_SERIAL = r"^[(.]?(?:[০-৯0-9]{1,4}|[ক-হ])\s*[.।)\]:]*\s*$"
DV_HEADER = r"(নাম|নম্বর|ক্রম|ওয়েবসাইট|লিংক|লিঙ্ক)\s*$|^(জেলা|উপজেলা|ইউনিয়ন|ইউিনয়ন|নং|ক্রমিক)$|^ক্র(মিক|ঃ|:|\.)?\s*(নং|নম্বর|ন\.?)$"
DV_UNION_SUFFIX = r"\s*(ইউ\S{0,5}ন্?\s*পরিষ\S{0,2}|ইউ\S{0,5}ন্?|উনিয়ন|ইউপি|ইউ\.?\s*পি\.?|ইউ\s*/\s*পি|ইউঃ\s*পরিষদ|ইউঃ)\s*[।.,:ঃ]*\s*$"


DV_PERSON = r"মোঃ|মো:|মো\.|জনাব|মোছাঃ|মোসাঃ|বেগম|আলহাজ্ব|চেয়ারম্যান"
DV_HONORIFIC = r"^\s*(জনাব|জনাবা|মোঃ|মো:|মো\.\s|মোছাঃ|মোসাঃ|মোসাম্মৎ|আলহাজ্ব|বেগম\s)"


def dv_clean_union(s):
    """'০১। ১ নং চওড়া বড়গাছা ইউনিয়ন' -> ('চওড়া বড়গাছা', '01')."""
    s = dv_nfc(s).strip(" |।,.;:-")
    s = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", s)                                 # '\x84পোড়াগাঁও' (sherpur.gov.bd)
    s = re.sub(r"^[*•●▪◆■]+\s*", "", s)                                     # '* ১নং তারাকান্দা' (a bullet)
    s = re.sub(r"\s*\(?\s*(https?://)?[\w.-]+\.gov\.bd/?[^\s)]*\)?", "", s)   # printed portal address, '(https://…)'
    s = re.sub(r"\s*\(\s*[A-Za-z][A-Za-z .,'\-]*\)\s*$", "", s)                 # '(১)কাড়াপাড়া (Karapara)'
    s = re.sub(r"\s*[-–]?\s*[0-9]{0,2}\s*[A-Za-z][^ঀ-৿]*$", "", s)             # '... ইউপি- Bhomradaha', '... 1no: Hadira'
    s = s.strip(" |।,.;:-")
    s = re.sub(r"^[(]?[০-৯0-9]{1,3}\s*[.।)]\s*", "", s)              # list serial '০১।'
    no = ""
    m = re.match(r"^([০-৯0-9]{1,2})\s*(\([ক-হ]\))?\s*(?:নং|নম্বর|no\.?|ন(?=\s))\s*(.*)$", s)
    if m:                                        # '১(ক)নং জুলধা' -> no '01(ক)'
        no, s = dv_asc(m.group(1)).zfill(2) + (m.group(2) or ""), m.group(3)
    else:
        s = re.sub(r"^[০-৯0-9]{1,3}\s*(?=[ঀ-৥ৰ-৿])", "", s)                # bare serial '৫ ধর্মপাল', '১২আজমপুর'
    if not re.match(r"^(?:[ঀ-৿]{1,2}\s*,\s*)+[ঀ-৿]", s):                      # not 'জি,এম, হাট' (initials)
        s = re.split(r"\s*[।;,]\s*", s)[0]                      # 'X ইউনিয়ন। এ ইউনিয়নের বিস্তারিত ...'
    s = re.sub(r"\s*ইউ\S{0,5}ন\s*(?:পরিষদ\S{0,2})?\s*[:ঃ]\s*(?=\S).*$", "", s)  # 'X ইউনিয়ন পরিষদঃ উপজেলা সদর থেকে ...'
    m = re.match(r"^(.*?)\s*(?:ইউ\S{0,5}ন|ই্উনিয়ন)\s*(" + DV_QUAL + r")\s*[।.,]*$", s)
    if m:                                                                   # 'ভারেল্লা ইউনিয়ন (উত্তর)' -> 'ভারেল্লা (উত্তর)'
        s = f"{m.group(1)} {m.group(2)}"
    s = re.split(r"\s+ইউনিয়ন(?:\s+পরিষদ)?\s+(?=[ঀ-৿])", s)[0]          # 'কাকড়াজান ইউনিয়ন চকচকিয়া ...'
    s = re.sub(r"\s*ই্উ\S{0,5}ন\s*$", "", s)                                  # 'মজিদপুর ই্উনিয়ন' (stray hasant)
    s = re.sub(DV_UNION_SUFFIX, "", s)
    s = re.sub(r"\s+(ও|এবং)$", "", s)                                       # last-but-one item of 'a, b ও'
    s = re.sub(r"(?<=[ঀ-৿])\s+[০-৯0-9]{1,3}$", "", s)          # 'আমাদি ০৫' (a 'নাম ও জিও কোড' column, koyra)
    return re.sub(r"\s+", " ", s).strip(" |।,.;:-"), no


# a parenthesised part of a union name: '(উত্তর)', '(দ:)', '(পূর্ব)', '(২)'
DV_QUAL = r"\(\s*(?:উত্তর|দক্ষিণ|দক্ষিন|পূর্ব|পুর্ব|পশ্চিম|মধ্য|উঃ|দঃ|উ:|দ:|পূঃ|পঃ|[০-৯0-9]{1,2})\s*\)"
DV_JUNK = (r"(?<![ঀ-৿])(মোট|হলো|হলোঃ|যথা|যথাঃ|শূন্য|ভাড়া)(?![ঀ-৿])|উপজেলা|সমূহ|সমুহ|তালিকা|রয়েছে|নিম্নরূপ|বিস্তারিত|"
           r"উল্লেখ্য|যোগাযোগ|কন্টেন্ট|ডাউনলোড|ফাইল|[()]|"
           r"ইউনিয়েনর নাম|ইউনিয়নের নাম|পরিষদের নাম|এখানে|ক্লিক|অন্তর্ভুক্ত|পৌরসভা|সর্বমোট|মানচিত্র|"
           r"(?<![ঀ-৿])(পুরুষ|মহিলা|নারী|মেয়র|জনাব)(?![ঀ-৿])|"
           r"মৌজা|দেখুন|সিটিজেন|কার্যাবলি|আদালত|জনসংখ্যা|দূরত্ব|দুরত্ব|যাতায়াত|পিতা|সাং-|পো[:ঃ]|^ইউনিয়ন|"
           r"^(?:ও|এবং)$")                       # a line holding only 'ও' between two items (mohongonj.netrokona.gov.bd)


def dv_junk(name):
    """True when a parsed 'union name' is prose or a heading; '(উত্তর)'-style parts of a name are allowed."""
    return bool(re.search(DV_JUNK, re.sub(DV_QUAL, "", name)))


DV_ITEM = ("#dv-list-item", "")   # marks a row split out of a list cell: always a union, never a heading


def dv_comma_items(t):
    """Items of a comma-separated list; initials stay one item ('এস,বি,কে, ফতেপুর' -> ['এস,বি,কে', 'ফতেপুর'])."""
    out = []
    for x in [x.strip() for x in re.split(r"\s*,\s*", t.strip(" ,।")) if x.strip()]:
        if out and len(x) <= 2 and len(out[-1].split(",")[-1]) <= 2 and re.fullmatch(r"[ঀ-৿]+", x):
            out[-1] += "," + x
        else:
            out.append(x)
    return out or [t]


def dv_numbered_items(t, n=3):
    """Items of a numbered list run together in one paragraph or cell ('… নিম্নে দেওয়া হলো: ১। ক ২। খ ৩। গ',
    patuakhali.gov.bd; '১। ভিটাবাড়িয়া ২। নদমুলা-শিয়ালকাঠী …', pirojpur.gov.bd). [] unless the serials run 1, 2, 3, …
    (at least n items); text before the first serial is dropped."""
    ms = list(re.finditer(r"(?<![^\s:ঃ।])([০-৯0-9]{1,2})\s*[।.)]\s*(?=[ঀ-৥ৰ-৿])", t or ""))
    if len(ms) < n or [int(dv_asc(m.group(1))) for m in ms] != list(range(1, len(ms) + 1)):
        return []
    return [t[m.end():(ms[k + 1].start() if k + 1 < len(ms) else len(t))].strip(" ,;।|") for k, m in enumerate(ms)]


def dv_expand_inline(rows, lists=True):
    """'... যথাঃ ১ নং ধর্মগড় ২ নং নেকমরদ ... ও ৮ নং নন্দুয়ার' -> one row per item."""
    out = []
    for cells in rows:
        # '… ইউনিয়নগুলোর নাম হলো- আমখোলা, গোলখালী, …, গজলিয়া,ও কলাগাছিয়া এবং পৌরসভার নাম হল গলাচিপা।' (a paragraph,
        # galachipa.patuakhali.gov.bd): one row per item
        # 'নেত্রকোণা সদর উপজেলার ইউনিয়ন সমূহ মৌগাতী, মেদনী, …' (a heading and the list in one line,
        # netrokonasadar.netrokona.gov.bd): the same
        m = re.search(r"ইউনিয়ন\S*\s*(?:এর\s*)?নাম\s*(?:হলো|হল|হচ্ছে)\s*[-–:ঃ]+\s*([^।]+)|"
                      r"উপজেলার\s+ইউনিয়ন\s*(?:সমূহ|সমুহ)\s*[-–:ঃ]*\s+([^।]+)", cells[0][0]) if len(cells) == 1 else None
        if m:
            items = [re.sub(r"^(?:ও|এবং)\s+", "", x).strip()
                     for x in dv_comma_items(re.split(r"\s+এবং\s+পৌরসভা", m.group(1) or m.group(2))[0])]
            if len(items) >= 3 and all(len(x.split()) <= 3 for x in items):
                out += [[(x, [DV_ITEM])] for x in items]
                continue
        # 'ইউনিয়ন সমূহ | … ইউনিয়নসমূহ নিম্নে ছকে দেওয়া হলোঃ ১. লক্ষণশ্রী ২. মোহনপুর …' (a heading cell, then prose and a
        # numbered list in one cell; sadar.sunamganj.gov.bd): one row per item
        if len(cells) == 2 and re.fullmatch(r"ইউনিয়ন\s*(?:সমূহ|সমুহ|পরিষদ\s*সমূহ)?", cells[0][0].strip()) and \
                len(items := dv_numbered_items(cells[1][0])) >= 3 and all(len(x.split()) <= 4 for x in items):
            out += [[(x, [DV_ITEM])] for x in items]
            continue
        # '১। ভিটাবাড়িয়া ২। নদমুলা-শিয়ালকাঠী ৩। তেলিখালী …' in one cell (pirojpur.gov.bd): one row per item
        if len(cells) == 1 and re.match(r"^\s*[০0]?[১1]\s*[।.)]", cells[0][0]) and \
                len(items := dv_numbered_items(cells[0][0])) >= 3 and all(len(x.split()) <= 4 for x in items):
            out += [[(x, [DV_ITEM])] for x in items]
            continue
        if len(cells) == 1 and len(re.findall(r"[০-৯0-9]{1,2}\s*নং", cells[0][0])) >= 3:
            t = cells[0][0]
            m = re.search(r"([০-৯0-9]+)\s*টি\s*ইউনিয়ন", t)
            if m:
                out.append([(f"{m.group(1)}টি", [])])
            for no, nm in re.findall(r"([০-৯0-9]{1,2})\s*নং\s*(.+?)(?=\s*(?:,|ও)?\s*[০-৯0-9]{1,2}\s*নং|[।]|$)", t):
                out.append([(f"{no} নং {nm}", [])])
            continue
        texts = [t for t, _ in cells if t and t.strip(" |")]
        # a cell with one union per paragraph (dv_cell_lines): the row keeps the first line, every further line
        # becomes a row of its own, with that line's links
        k = next((i for i, (_, ls) in enumerate(cells) if any(h == "#dv-lines" for h, _ in ls)), None)
        if k is not None:
            items = json.loads(next(x for h, x in cells[k][1] if h == "#dv-lines"))
            out.append(cells[:k] + [(items[0][0], [tuple(l) for l in items[0][1]])] + cells[k + 1:])
            out += [[(x, [tuple(l) for l in ls] + [DV_ITEM])] for x, ls in items[1:]]
            continue
        # 'তালা | ০১. ধানদিয়া০২. নগরঘাটা০৩. সরুলিয়া...' (satkhira.gov.bd): numbered items run together in one cell;
        # the row keeps the first item, every further item becomes a row of its own
        k = next((i for i, (t, _) in enumerate(cells) if len(cells) >= 2 and "," not in t and "নং" not in t and
                  len(re.findall(r"[০-৯0-9]{1,2}\s*[.।)]?\s*[ঀ-৥ৰ-৿]", t)) >= 3 and
                  re.fullmatch(r"(?:\s*[০-৯0-9]{1,2}\s*[.।)]?\s*[ঀ-৥ৰ-৿][^০-৯0-9]*)+", t)), None)
        if k is not None:
            items = [x.strip() for x in re.findall(r"[০-৯0-9]{1,2}\s*[.।)]?\s*[^০-৯0-9]+", cells[k][0])]
            out.append(cells[:k] + [(items[0], [])] + cells[k + 1:])
            out += [[(x, [DV_ITEM])] for x in items[1:]]
            continue
        # 'ক্রমিক | উপজেলা | ইউনিয়নের সংখ্যা | ক, খ, গ, ...' (a table cell holding a comma-separated list): the row
        # keeps the first item, every further item becomes a row of its own
        k = next((i for i, (t, _) in enumerate(cells) if lists and len(cells) >= 2 and t.count(",") >= 2 and
                  all(re.search(r"[ঀ-৿]", x) and len(x.split()) <= 4 and len(x.replace(" ", "")) >= 3
                      for x in dv_comma_items(t))),
                 None)
        if k is not None:
            items = dv_comma_items(cells[k][0])
            out.append(cells[:k] + [(items[0], [])] + cells[k + 1:])
            out += [[(x, [DV_ITEM])] for x in items[1:]]
        # '১. শিলই ইউনিয়ন। | ২. আধারা ইউনিয়ন ।' (two numbered items per row): one row per item
        elif len(texts) >= 2 and (all(re.match(r"^[(]?[০-৯0-9]{1,3}\s*[.)।]\s*[ঀ-৿]", t) for t in texts) or all(
                re.search(r"[ঀ-৿]", t) and len(t.split()) <= 4 and (re.search(r"ইউনিয়ন\s*$", t) or
                                                                     any(re.search(r"up\d*\.", h) for h, _ in ls))
                for t, ls in cells if t and t.strip(" |"))):
            # '১. শিলই ইউনিয়ন। | ২. আধারা ইউনিয়ন ।' or 'বাল্লা ইউনিয়ন | গোপীনাথপুর ইউনিয়ন' (two items per row)
            out += [[(c[0], c[1] + [DV_ITEM])] for c in cells if c[0] and c[0].strip(" |")]
        else:
            out.append(cells)
    return out


# Legacy Bijoy (SutonnyMJ) ASCII encoding, still printed on some list pages (e.g. 'wkevjq' = শিবালয়). Converted to
# Unicode only on pages where several cells look like Bijoy; the printed text is kept on the cell as a pseudo-link
# ("#dv-bijoy", printed) so rows can say so in their notes.
_DV_BJ_MAP = sorted({
    "Av": "আ", "A": "অ", "B": "ই", "C": "ঈ", "D": "উ", "E": "ঊ", "F": "ঋ", "G": "এ", "H": "ঐ", "I": "ও", "J": "ঔ",
    "K": "ক", "L": "খ", "M": "গ", "N": "ঘ", "O": "ঙ", "P": "চ", "Q": "ছ", "R": "জ", "S": "ঝ", "T": "ঞ", "U": "ট",
    "V": "ঠ", "W": "ড", "X": "ঢ", "Y": "ণ", "Z": "ত", "_": "থ", "`": "দ", "a": "ধ", "b": "ন", "c": "প", "d": "ফ",
    "e": "ব", "f": "ভ", "g": "ম", "h": "য", "i": "র", "j": "ল", "k": "শ", "l": "ষ", "m": "স", "n": "হ", "o": "ড়",
    "p": "ঢ়", "q": "য়", "r": "ৎ", "s": "ং", "t": "ঃ", "u": "ঁ", "v": "া", "x": "ী", "y": "ু", "z": "ু", "~": "ূ",
    "„": "ৃ", "…": "ৃ", "Š": "ৗ", "ª": "্র", "«": "্র", "Ö": "্র", "¨": "্য", "¦": "্ব", "ø": "্ল", "¯": "স্",
    "Í": "ত", "Î": "ক্ষ", "¶": "ক্ষ", "ÿ": "ক্ষ", "Ä": "ঞ্জ", "Â": "ঞ্চ", "Ã": "ঞ্ছ", "Á": "ঞ্চ", "›": "ন্", "ò": "ষ্ণ",
    "ï": "শু", "æ": "ু", "ê": "জ্ঞ", "Ç": "ক্স", "ÿ¿": "ক্ষ", "¸": "ক্ত", "³": "ক্ত", "ß": "ম্প", "®": "ষ্", "¤": "ম্",
    "Ü": "দ্দ", "Ø": "দ্ধ", "¢": "ঙ্গ", "½": "ন্ধ", "¾": "ন্ড", "š": "ন্", "Ë": "গ্ধ", "Ý": "দ্ব", "Ð": "চ্ছ", "¹": "ক্ট",
    "±": "ক্ক", "º": "খ্যা", "Ú": "দ্দ", "Ò": "চ্চ", "Ó": "জ্জ", "Ø©": "র্দ্ধ", "ˆ": "ৈ", "&": "্", "|": "।",
    "0": "০", "1": "১", "2": "২", "3": "৩", "4": "৪", "5": "৫", "6": "৬", "7": "৭", "8": "৮", "9": "৯",
}.items(), key=lambda kv: -len(kv[0]))
_DV_BJ_PRE = {"w": "ি", "‡": "ে", "†": "ে", "‰": "ৈ"}
_DV_BJ_SIGNS = r"[‡†‰Š©ª«¨¯ÄÂæøïò¦Ö›…„`~]|(?:^|\s)w[A-Za-z]|[A-Z]v|[a-z][A-Z]"


def dv_is_bijoy(s):
    return bool(s) and not re.search(r"[ঀ-৿]|https?://|\.gov\.bd|www\.|@", s) and bool(re.search(_DV_BJ_SIGNS, s))


def dv_bijoy(s):
    """Bijoy ASCII -> Unicode Bangla: map tokens, then put each pre-base kar (w ‡ † ‰) after the consonant cluster
    that follows it (‡..v -> ো, ‡..Š -> ৌ) and each reph (©) before the cluster that precedes it."""
    cons = "কখগঘঙচছজঝঞটঠডঢণতথদধনপফবভমযরলশষসহড়ঢ়য়ৎ"
    flat, i = [], 0
    while i < len(s):
        ch = s[i]
        if ch in _DV_BJ_PRE or ch == "©":
            flat.append(("PRE", _DV_BJ_PRE[ch]) if ch != "©" else ("REPH", ""))
            i += 1
            continue
        for k, v in _DV_BJ_MAP:
            if s.startswith(k, i):
                flat += [("T", x) for x in v]
                i += len(k)
                break
        else:
            flat.append(("T", ch))
            i += 1
    out, pre, i, n = "", [], 0, len(flat)
    while i < n:
        kind, v = flat[i]
        if kind == "PRE":
            pre.append(v)
            i += 1
        elif kind == "REPH":
            m = re.search("([" + cons + "]়?(?:্[" + cons + "]়?)*)[ািীুূৃেৈোৌ]?$", out)
            out = out[:m.start()] + "র্" + out[m.start():] if m else out + "র্"
            i += 1
        elif pre and v in cons:
            cl, i = v, i + 1
            while i < n and (flat[i] == ("T", "়") or (i + 1 < n and flat[i] == ("T", "্") and
                                                            flat[i + 1][1] in cons)):
                if flat[i][1] == "়":
                    cl, i = cl + "়", i + 1
                else:
                    cl, i = cl + "্" + flat[i + 1][1], i + 2
            kar, pre = "".join(pre), []
            if kar == "ে" and i < n and flat[i] == ("T", "া"):
                kar, i = "ো", i + 1
            elif kar == "ে" and i < n and flat[i] == ("T", "ৗ"):
                kar, i = "ৌ", i + 1
            out += cl + kar
        else:
            out += v
            i += 1
    return dv_nfc(out + "".join(pre)).replace("অা", "আ")


def dv_cell_lines(x):
    """A table cell holding one union per paragraph/line ('<p>সুবিল ইউনিয়ন</p><p>রসুলপুর ইউনিয়ন</p>...'): returns
    [("#dv-lines", json [[line, links], ...])] so dv_expand_inline can give each line a row; [] otherwise."""
    lines = []
    for blk in re.split(r"<br\s*/?>|</p>|</li>|</div>", x):
        t = dv_text(blk).replace("\n", " ").strip(" |")
        if t:
            lines.append([t, dv_links(blk)])
    if len(lines) >= 3 and all(re.search(r"[ঀ-৿]", t) and len(t.split()) <= 6 for t, _ in lines) and \
            sum(bool(re.search(r"ই্?উ\S{0,5}ন", t)) for t, _ in lines) >= len(lines) - 1:
        return [("#dv-lines", json.dumps(lines, ensure_ascii=False))]
    # '<ol><li><p>আওনা</p></li><li><p>ভাতারা</p></li>…</ol>' (jamalpur.gov.bd): a cell that is only a list of bare names
    lis = [dv_text(b).replace("\n", " ").strip(" |") for b in re.findall(r"<li[^>]*>(.*?)</li>", x, flags=re.S)]
    if len(lis) >= 3 and len(lis) == len(lines) and all(re.fullmatch(r"[ঀ-৿]+(?:[ -][ঀ-৿]+){0,3}", t) for t in lis):
        return [("#dv-lines", json.dumps(lines, ensure_ascii=False))]
    return []


def dv_side_by_side(tb):
    """A table whose header row repeats 'উপজেলার নাম' (two upazila/union lists printed side by side)."""
    tr = re.search(r"<tr.*?</tr>", tb, flags=re.S)
    hdr = [dv_text(x).strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr.group(0), flags=re.S)] if tr else []
    return len(hdr) >= 4 and len(hdr) % 2 == 0 and sum(bool(re.search(r"^উপজেলার নাম$", h)) for h in hdr) == 2 and \
        hdr[:len(hdr) // 2] == hdr[len(hdr) // 2:]


def dv_halves(tb):
    """Rows of a side-by-side table: the grid is rebuilt with rowspan/colspan (a spanned position is an empty cell),
    then all rows of the left half, followed by all rows of the right half."""
    grid, carry = [], {}
    for tr in re.findall(r"<tr.*?</tr>", tb, flags=re.S):
        row, col = [], 0
        for attrs, x in re.findall(r"<t[dh]([^>]*)>(.*?)</t[dh]>", tr, flags=re.S):
            while carry.get(col, 0) > 0:
                carry[col] -= 1
                row.append(("", []))
                col += 1
            rs = int((re.search(r'rowspan="?(\d+)', attrs) or [0, 1])[1])
            cs = int((re.search(r'colspan="?(\d+)', attrs) or [0, 1])[1])
            for k in range(cs):
                row.append((dv_text(x).replace("\n", " ").strip(), dv_links(x)) if k == 0 else ("", []))
                if rs > 1:
                    carry[col] = rs - 1
                col += 1
        while carry.get(col, 0) > 0:
            carry[col] -= 1
            row.append(("", []))
            col += 1
        grid.append(row)
    w = len(grid[0]) // 2
    return [r[:w] for r in grid] + [r[w:2 * w] for r in grid[1:]]


DV_ROWSPAN = "#dv-rowspan"   # link marker on a cell spanning several rows: (DV_ROWSPAN, "<rowspan>")


def dv_rows(c):
    """Rows of a list page: table rows (cells + links) or, without tables, one row per text line."""
    rows = []
    trs = re.findall(r"<tr.*?</tr>", c["html"], flags=re.S)
    tables = re.findall(r"<table.*?</table>", c["html"], flags=re.S)
    if trs and any(dv_side_by_side(x) for x in tables):     # two lists printed side by side: read each half in turn
        for tb in tables:
            rows += dv_halves(tb) if dv_side_by_side(tb) else [
                [(dv_text(x).replace("\n", " ").strip(), dv_links(x) + dv_cell_lines(x))
                 for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S)]
                for tr in re.findall(r"<tr.*?</tr>", tb, flags=re.S)]
    elif trs:
        for tr in trs:
            cells = re.findall(r"<t[dh]([^>]*)>(.*?)</t[dh]>", tr, flags=re.S)
            rows.append([(dv_text(x).replace("\n", " ").strip(), dv_links(x) + dv_cell_lines(x) + (
                [(DV_ROWSPAN, rs.group(1))] if (rs := re.search(r'rowspan="?(\d+)', a)) and int(rs.group(1)) > 1 else []))
                for a, x in cells])
    if trs:
        if sum(dv_is_bijoy(t) for r in rows for t, _ in r) >= 3:           # a Bijoy page: convert every Bijoy-like cell
            for r in rows:
                for k, (t, ls) in enumerate(r):
                    if t and len(t) <= 40 and not re.search(r"[ঀ-৿]|https?://|\.gov\.bd|www\.|@", t) and \
                            re.fullmatch(r"[A-Za-z`~_\s\x80-\xff‡†‰Š…„›&|-]+", t) and re.search(r"[A-Za-z]", t):
                        r[k] = (dv_bijoy(t), ls + [("#dv-bijoy", t)])   # the printed text travels with the cell
    else:
        frag = re.sub(r"<br\s*/?>", "</p><p>", c["html"])
        for blk in re.split(r"</p>|</li>|</div>|</h\d>", frag):
            t = dv_text(blk).replace("\n", " ").strip()
            if t and not re.match(r"^(কন্টেন্ট|কনটেন্টটি)", t):
                rows.append([(t, dv_links(blk))])
    return rows


def dv_headed_rows(c, div, d):
    """Rows of a page where each upazila is a heading above its own table ('<h4>রূপসা উপজেলা</h4><table>…',
    khulna.gov.bd; '<p>চুয়াডাঙ্গা সদরঃ</p><table>…', chuadanga.gov.bd): a heading row before the table's rows. A
    cell holding one union per line ('<h5>১।আইচগাতি</h5><h5>২।শ্রীফলতলা</h5>…') gives one row per line."""
    parts = re.split(r"(<table.*?</table>)", c["html"], flags=re.S)
    rows, headed = [], 0
    for i in range(1, len(parts), 2):
        before = [dv_text(b).replace("\n", " ").strip() for b in re.split(r"</p>|</h\d>|</div>|<br\s*/?>", parts[i - 1])]
        head = next((b for b in reversed(before) if b), "")
        if head and div.upazila(d, re.sub(r"\s*উপজেলা.*$", "", head.strip(" :ঃ"))):
            rows.append([(head, [])])
            headed += 1
        for tr in re.findall(r"<tr.*?</tr>", parts[i], flags=re.S):
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S)
            lines = [[(dv_text(b).replace("\n", " ").strip(), dv_links(b))
                      for b in re.split(r"</p>|</h\d>|<br\s*/?>|</li>|</div>", x)] for x in cells]
            lines = [[x for x in ls if re.search(r"[ঀ-৿]", x[0])] for ls in lines]
            multi = [ls for ls in lines if len(ls) >= 2]
            if len(multi) == 1 and sum(bool(ls) for ls in lines) == 1:
                rows += [[(t, ls + [DV_ITEM])] for t, ls in multi[0]]
            else:
                rows.append([(dv_text(x).replace("\n", " ").strip(), dv_links(x)) for x in cells])
    return rows if headed >= 2 else []


def dv_district_headed_rows(c, div):
    """Rows of a page where each district is a heading above its own table ('<p><strong>জেলা: সিলেট</strong></p><table>…',
    sylhetdiv.gov.bd): a marked district row before the table's rows; [] unless at least two tables are headed so."""
    parts = re.split(r"(<table.*?</table>)", c["html"], flags=re.S)
    rows, headed = [], 0
    for i in range(1, len(parts), 2):
        before = [dv_text(b).replace("\n", " ").strip() for b in re.split(r"</p>|</h\d>|</div>|<br\s*/?>", parts[i - 1])]
        head = next((b for b in reversed(before) if b), "")
        # 'ময়মনসিংহ জেলা' / 'ময়মনসিংহ জেলার ইউনিয়ন পরিষদের নামসমূহ' above each table (mymensinghdiv.gov.bd)
        m = re.fullmatch(r"জেলা\s*[:ঃ]\s*(\S+)", head) or \
            re.fullmatch(r"(\S+)\s+জেলা(?:র\s+ইউনিয়ন\s*পরিষদের\s+নাম\s*সমূহ)?\s*[:ঃ]?", head)
        if m and div.district(m.group(1)):
            rows.append([(head, [("#dv-district", div.district(m.group(1)))])])
            headed += 1
        for tr in re.findall(r"<tr.*?</tr>", parts[i], flags=re.S):
            rows.append([(dv_text(x).replace("\n", " ").strip(), dv_links(x) + dv_cell_lines(x))
                         for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S)])
    return rows if headed >= 2 else []


def dv_en_note(r):
    return "; English name as printed on the list" if r.get("name_en") else "; English name not printed"


def dv_link_label(t, ls):
    """A cell that only says 'ওয়েব সাইট লিংক' (or similar) and links somewhere: a link column, not a header or a name."""
    return bool(re.fullmatch(r"(?:ওয়েব\s*সাইট|ওয়েবসাইট)(?:\s*(?:লিংক|লিঙ্ক))?|লিংক|লিঙ্ক", (t or "").strip())) and \
        any(h.startswith("http") for h, _ in ls)


def dv_union_list(c, div, district=None, upazila=None, rows=None):
    """Parse a union list page. district/upazila fix the context when the page has no such column.
    Returns (rows, stated) — rows: dict(district_en, upazila_en, upazila_printed, name_bn, printed, no, website);
    stated: {(district_en, upazila_en): (count, printed)} for per-upazila counts printed in the list.
    rows: pre-built page rows (dv_headed_rows) instead of dv_rows(c)."""
    out, stated = [], {}
    cur_d, cur_u, cur_u_printed = district, upazila, div.upz_bn(district, upazila) if district and upazila else ""
    poura_section = dcol = False
    span = None                                  # [rows the current upazila cell spans, rows seen under it]
    skip = None                                  # (row width, columns to leave out) after a header row
    for cells in dv_expand_inline(dv_rows(c) if rows is None else rows, lists=upazila is None):   # comma lists: district-wide pages only
        texts = [t for t, _ in cells]
        one = [x for x in texts if x and x.strip(" |")]
        dh = next((x for _, ls in cells for h, x in ls if h == "#dv-district"), None)
        if dh and not district:                  # a district heading above its table (dv_district_headed_rows)
            cur_d, cur_u, cur_u_printed = dh, None, ""
            continue
        if len(one) == 1 and re.fullmatch(r"পৌরসভা\s*(সমূহ|সমুহ)?\s*[:ঃ]?", one[0].strip()):
            poura_section = True                 # 'পৌরসভা / ১। আড়াইহাজার / ... / ইউনিয়ন / ১। সাতগ্রাম'
            continue
        if len(one) == 1 and re.fullmatch(r"ইউনিয়ন\s*(সমূহ|সমুহ|পরিষদ)?\s*[:ঃ]?", one[0].strip()):
            poura_section = False
            continue
        if poura_section:
            continue
        if one and re.match(r"^সর্ব\s*মোট", one[0].strip()):
            continue                             # 'সর্বমোট (১০টি উপজেলা) | ৮৮ | মোট ইউনিয়ন সংখ্যা' (a total row)
        if any(re.search(DV_HEADER, t) for t, ls in cells if t and not dv_link_label(t, ls)):
            # 'উপজেলার নাম | পৌরসভার নাম | ইউনিয়ন সংখ্যা' (mymensinghdiv.gov.bd): the pourashava column is not a union
            skip = {i for i, (t, _) in enumerate(cells) if re.search(r"পৌর\S*\s*নাম", t or "")}
            skip = (len(cells), skip) if skip else None
            continue
        if skip and len(cells) == skip[0]:
            cells = [x for i, x in enumerate(cells) if i not in skip[1]]
            texts = [t for t, _ in cells]
            one = [x for x in texts if x and x.strip(" |")]
        if len(texts) == 1 and (m := re.search(r"মোট\s*([০-৯0-9]{1,3})\s*টি\s*ইউনিয়ন|([০-৯0-9]{1,3})\s*টি\s*ইউনিয়ন", texts[0])) \
                and cur_u and upazila:
            stated[(cur_d, cur_u)] = (str(int(dv_asc(m.group(1) or m.group(2)))), m.group(0), cur_u_printed)
        names, site, count, cell_no, ditto, name_en = [], "", None, "", False, ""
        for t, ls in cells:
            if not t or re.fullmatch(r"[:ঃ\-|–]+", t):
                continue
            if re.fullmatch(r"ঐ|ঐ|〃|\"|”", t.strip()):
                ditto = True                     # 'ঐ' (ditto) in the upazila column: the upazila of the row above
                continue
            if re.fullmatch(DV_SERIAL, t):
                continue
            if (mn := re.fullmatch(r"([০-৯0-9]{1,2})\s*নং\.?", t)):
                cell_no = dv_asc(mn.group(1)).zfill(2)                     # '১ নং' in a column of its own
                continue
            m = re.fullmatch(r"([০-৯0-9]{1,3})\s*(টি|টি।)?\s*(\(.*\))?", t)
            if m and m.group(2):
                count = (dv_asc(m.group(1)), t)
                continue
            if re.search(r"\.gov\.bd|https?://|www\.", t, re.I) and not re.search(r"[ঀ-৿]", t):
                site = dv_site(t)
                continue
            if dv_link_label(t, ls):             # 'ওয়েব সাইট লিংক' linked to the union portal (netrokona.gov.bd)
                site = site or next((dv_site(h) for h, _ in ls if re.search(r"\.gov\.bd", h)), "")
                continue
            if re.fullmatch(r"[A-Za-z][A-Za-z .'()\-]{1,40}", t.strip()) and not re.search(r"www|\.(gov|com|org|net)", t, re.I) \
                    and not any(h == "#dv-bijoy" for h, _ in ls):
                name_en = t.strip()              # 'কাংশা | Kangsha': the English name in a column of its own (sherpur.gov.bd)
                continue
            if not re.search(r"[ঀ-৿]", t) or re.fullmatch(r"[০-৯0-9.,\s()%]+", t):
                continue                                                    # figures in extra columns
            if (m := re.search(r"মোট\s*ইউনিয়ন\S*\s*(?:পরিষদ\S*\s*)?সংখ্যা\s*[:ঃ=-]?\s*([০-৯0-9]{1,3})\s*টি", t)):
                count = (dv_asc(m.group(1)), m.group(0))                   # 'মোট ইউনিয়ন সংখ্যাঃ ১২ টি' in a column
                continue
            names.append((t, ls))
        if len(names) >= 2:                      # drop a chairman/secretary column ('জনাব ...', 'মোঃ ...')
            names = [n for n in names if not re.match(DV_HONORIFIC, n[0])] or names
        if any(DV_ITEM in ls for _, ls in cells):                         # split out of a list cell: a union
            names = [(t, [x for x in ls if x != DV_ITEM]) for t, ls in names]
            if not names or cur_d is None or cur_u is None:
                continue
            printed, ls = names[0]
            name, no = dv_clean_union(printed)
            if name and not dv_junk(name) and len(name.split()) <= 4:
                prev = next((r for r in out if r.get("item") and r.get("upazila_en") == cur_u and
                             r.get("district_en") == cur_d and r["name_bn"] == name and r["no"] == no), None)
                if prev:                         # 'পূর্ব আলীরগাঁও ইউনিয়ন, পূর্ব আলীরগাঁও ইউনিয়ন' (sylhetdiv.gov.bd)
                    prev["dup"] = prev.get("dup", 1) + 1
                    continue
                out.append(dict(district_en=cur_d, upazila_en=cur_u, upazila_printed=cur_u_printed, name_bn=name,
                                printed=dv_nfc(printed), no=no, item=True,
                                website=next((dv_site(h) for h, _ in ls if re.search(r"\.gov\.bd", h)), "")))
            continue
        if len(names) >= 3 and dv_loose(names[0][0]) == dv_loose(div.name_bn) and div.district(names[1][0]):
            names = names[1:]                    # 'খুলনা | যশোর | অভয়নগর | বাঘুটিয়া': a division column first
        sadar = next((e for e, b, _, _ in div.districts[district]["upazilas"] if b.endswith("সদর")), None) \
            if district and not upazila else None
        if sadar and not dcol and len(names) >= 2 and div.district(names[0][0]) == district and \
                not div.upazila(district, names[1][0]) and not div.district(names[1][0]) and \
                not any(r.get("upazila_en") == sadar for r in out):
            # 'মৌলভীবাজার | ১২ | ০১ নং খলিলপুর …' (moulvibazar.gov.bd), 'সুনামগঞ্জ | আপ্তাবনগর' (sunamganj.gov.bd): on a
            # page with no district column, the district's name in the upazila column stands for its Sadar upazila
            cur_u, cur_u_printed = sadar, dv_nfc(names[0][0]).strip(" :ঃ-")
            if count:
                stated[(cur_d, cur_u)] = (str(int(count[0])), count[1], cur_u_printed)
            names = names[1:]
        if names:
            nd = div.district(names[0][0])
            if nd and (district is None or nd == district) and (len(names) >= 2 or cur_d is None) \
                    and not (nd == cur_d and len(names) == 1):
                if nd != cur_d:
                    cur_d, cur_u = nd, upazila
                names = names[1:]
                dcol = True
        if not names or cur_d is None:
            continue
        first = names[0][0]
        first_key = re.sub(r"\s*[-–]\s*[০-৯0-9]{1,3}\s*$", "", first)            # 'করিমগঞ্জ-৪২' (with upazila code)
        if (mc := re.match(r"^(.*?)\s*\(\s*([০-৯0-9]{1,3})\s*টি\s*ইউনিয়ন\s*\)\s*$", first_key)):
            first_key, count = mc.group(1), (dv_asc(mc.group(2)), mc.group(0).strip())   # 'লামা (৭ টি ইউনিয়ন)'
        if (mc := re.match(r"^(.*?উপজেলা)\s*(মোট\s*ইউনিয়ন\S*\s*[:ঃ]?\s*([০-৯0-9]{1,3})\s*টি.*)$", first_key)):
            first_key, count = mc.group(1), (dv_asc(mc.group(3)), mc.group(2).strip())   # 'কাউখালী উপজেলা মোট ইউনিয়নঃ ৫টি'
        fu = div.upazila(cur_d, re.sub(r"\s*উপজেলা.*$", "", first_key))
        head = fu and not ditto and (len(names) >= 2 or "উপজেলা" in first or (fu != cur_u and not upazila))
        if head and upazila and "উপজেলা" not in first and (
                dv_nfc(first).strip() not in {dv_nfc(x.lstrip("~")) for e, b, _, al in div.districts[cur_d]["upazilas"]
                                              if e == upazila for x in [b] + al}
                or any(re.search(DV_PERSON, t) for t, _ in names[1:2])):
            head = False                         # a union named like its upazila, followed by other columns
        if head and upazila and "উপজেলা" not in first and any(re.fullmatch(DV_SERIAL, x) for x in texts if x):
            head = False                         # a numbered row on an upazila page is a union row
        # 'তারাকান্দা' spanning 10 rows (rowspan) and followed by 19 union rows before the next upazila cell
        # (mymensingh.gov.bd): the rows after the 10th have no upazila on the page (in a browser their names stand in the
        # upazila column) and are not used. A heading spanning more rows than it has is harmless.
        if not head and not upazila and cur_u and span and span[1] >= span[0]:
            out.append(dict(warning=f"'{dv_nfc(names[-1][0])}' printed after the {span[0]} rows that the cell "
                                    f"'{cur_u_printed}' ({cur_u}) spans; the page gives no upazila for it, not used"))
            continue
        if span and not head:
            span[1] += 1
        if head:
            rs = next((int(x) for t, ls in cells if dv_nfc(t) == dv_nfc(first) for h, x in ls if h == DV_ROWSPAN), 0)
            span = [rs, 1] if rs > 1 and not upazila else None
            cur_u, cur_u_printed = fu, re.sub(r"\s*উপজেলা.*$", "", dv_nfc(first_key)).strip(" :ঃ-")
            if count:
                stated[(cur_d, cur_u)] = (str(int(count[0])), count[1], cur_u_printed)
            names = names[1:]
            if not names:
                continue
        elif upazila and "উপজেলা" in first and len(names) == 1:
            continue                                                        # heading / prose on an upazila page
        elif re.search(r"উপজেলা\s*[:ঃ]?$", first) or ("উপজেলা" in first and len(names) == 1) or \
                (len(names) >= 2 and not upazila):
            out.append(dict(warning=f"unknown upazila heading {first!r}"))
            cur_u = None
            continue
        if cur_u is None:
            out.append(dict(warning=f"union before any upazila heading: {first!r}"))
            continue
        if upazila and len(names) == 1 and first.count(",") >= 4 and (
                re.search(r"[০-৯0-9]+\s*টি\s*গ্রাম", first) or
                re.search(r"[:ঃ]\s*$", next((r["printed"] for r in reversed(out) if "printed" in r), ""))):
            continue                             # 'আটলিয়া, শ্রীচন্দপুর, … মোট ১৬টি গ্রাম' under 'X ইউনিয়নঃ': villages
        printed, ls = names[0] if upazila else names[-1]       # upazila pages: extra columns (chairman, notes) follow
        # 'রায়পাশা-কড়াপুর ইউপি বরিশাল সদর, বরিশাল।' (barisalsadar.barisal.gov.bd): the union's upazila after the suffix
        where = "|".join(re.escape(x) for x in div.upz_names(cur_d, cur_u))
        name, no = dv_clean_union(re.sub(r"\s*(ইউপি|ইউনিয়ন(?:\s*পরিষদ)?)\s*,?\s*(?:" + where + r")(?:\s*উপজেলা)?"
                                         r"(?:\s*,\s*" + re.escape(div.districts[cur_d]["name_bn"]) + r")?\s*[।.,]?\s*$",
                                         r" \1", dv_nfc(printed)) if where else printed)
        no = no or cell_no
        if not name or dv_junk(name) or len(name.split()) > 4:
            continue
        if not site and not any(re.search(r"\.gov\.bd", h) for h, _ in ls) and \
                (mp := re.search(r"(?:https?://)?((?:[\w-]+\.)+gov\.bd)", printed)):
            site = dv_site(mp.group(1))          # '০৩। রাজানগর ইউনিয়ন (https://rajanagarup.sunamganj.gov.bd)', not linked
        if not site:
            for h, _ in ls:
                if re.search(r"\.gov\.bd", h) and dv_site(h) and not dv_site(h).startswith("https://www."):
                    site = dv_site(h)
        bad = upz_link = ""
        if site and not div.under(cur_d, site):
            bad, site = site, ""                 # e.g. a Tangail union linked to gajariaup.munshiganj.gov.bd
        elif site and site in {div.upz_site(cur_d, e) for e, *_ in div.districts[cur_d]["upazilas"]}:
            upz_link, site = site, ""            # 'বরগুনা সদর' linked to sadar.barguna.gov.bd, the upazila portal
        prev = next((r for r in out if r.get("upazila_en") == cur_u and r.get("district_en") == cur_d
                     and r["name_bn"] == name and (r["no"] == no or not r["no"] or not no)), None)
        if prev:                                 # the same union printed twice (e.g. two tables on one page)
            prev["dup"] = prev.get("dup", 1) + 1
            prev["no"] = prev["no"] or no
            prev["website"] = prev["website"] or site
            continue
        flags = []
        if re.search(r"[া-ৌ]{2}", name):
            flags.append("DOUBT: the printed name has two vowel signs in a row (malformed)")
        bj = next((x for h, x in ls if h == "#dv-bijoy"), None)
        if bj:
            flags.append(f"printed in the legacy Bijoy (SutonnyMJ) ASCII encoding as '{bj}', converted to Unicode by "
                         f"the collector")
        if bad:
            flags.append(f"linked to {bad} (not a portal under {div.districts[cur_d]['host']}, not used)")
        if upz_link:
            flags.append(f"linked to {upz_link}, an upazila portal (not used)")
        out.append(dict(district_en=cur_d, upazila_en=cur_u, upazila_printed=cur_u_printed, name_bn=name,
                        printed=dv_nfc(printed), no=no, website=site, flags="".join("; " + x for x in flags),
                        name_en=name_en))
    # '… মীরপুর ইউনিয়ন, জগন্নাথপুর, চিলাউড়া-হলদিপুর ইউনিয়ন, …' (sylhetdiv.gov.bd): in a list of 'X ইউনিয়ন' items, the
    # upazila's own name without 'ইউনিয়ন' is not a union (the page's count leaves it out)
    for k in {(r["district_en"], r["upazila_en"]) for r in out if r.get("item")}:
        grp = [r for r in out if r.get("item") and (r.get("district_en"), r.get("upazila_en")) == k]
        bare = [r for r in grp if not re.search(r"ইউনিয়ন\S*\s*[।.]?$", r["printed"])]
        if len(bare) == 1 and len(grp) >= 4 and dv_nfc(bare[0]["printed"]).strip(" ।.,") in \
                {dv_nfc(x) for x in div.upz_names(k[0], k[1])}:
            out[out.index(bare[0])] = dict(warning=f"'{bare[0]['printed']}' (the upazila's name, without 'ইউনিয়ন', in a "
                                                   f"list of {k[1]}'s unions) not taken as a union")
    for r in out:
        r.pop("item", None)
    us = [r for r in out if "warning" not in r]
    if upazila and len(us) >= 4 and not us[-1]["no"] and all(r["no"] for r in us[:-1]) and \
            dv_nfc(us[-1]["printed"]).strip(" ।.") in {dv_nfc(x) for x in div.upz_names(cur_d, upazila)}:
        out[out.index(us[-1])] = dict(warning=f"unnumbered last line '{us[-1]['printed']}' (the upazila's name, after a "
                                              f"numbered list) not taken as a union")   # baniachong.habiganj.gov.bd
    shared = {}                                  # one link given for several unions (e.g. every union of a page
    for r in out:                                # linked to the same upazila portal; umorpurup.sylhet.gov.bd printed
        if r.get("website"):                     # for both উমরপুর and পশ্চিম পৈলনপুর) is not a union website
            shared[r["website"]] = shared.get(r["website"], 0) + 1
    for r in out:
        if shared.get(r.get("website"), 0) >= 2:
            r["flags"] = r.get("flags", "") + f"; linked to {r['website']}, which the list gives for " \
                                              f"{shared[r['website']]} unions (not used)"
            r["website"] = ""
    # upazila headings outside the tables (dv_headed_rows): tried only when unions came before any heading
    if rows is None and district and not upazila and \
            any(r.get("warning", "").startswith("union before any upazila heading") for r in out):
        hr = dv_headed_rows(c, div, district)
        if hr:
            out2, stated2 = dv_union_list(c, div, district, upazila, rows=hr)
            if sum("warning" not in r for r in out2) > sum("warning" not in r for r in out):
                return out2, stated2
    return out, stated


def dv_menu(home, base):
    seen, out = set(), []
    for h, x in dv_links(home, base):
        if (h, x) not in seen and x:
            seen.add((h, x))
            out.append((dv_nfc(x).strip(" ■•"), h))
    return out


def dv_pick(menu, include, exclude=None, host=None):
    for x, h in menu:
        if re.search(include, x) and not (exclude and re.search(exclude, x)) and \
                (host is None or urlparse(h).netloc.lower() == host) and \
                ("/pages/static-pages/" in h or re.search(r"/pages/union/[0-9a-f]{24}$", h)):   # lalmohan.bhola.gov.bd
            return x, h
    return None


DV_FACT_LABELS = [  # (fact, include regex on label, exclude regex on label, unit)
    ("area_km2", r"আয়তন", r"পৌর|জমি|ভূমি|বন|অবস্থান", "km2"),
    ("population", r"জনসংখ্যা|লোকসংখ্যা|লোক সংখ্যা", r"ঘনত্ব|বৃদ্ধি|হার|পুরুষ|মহিলা|ভোটার|পৌর|শিক্ষিত|উপজাতী|আদিবাসী|ভিত্তিক|পেশা|ধর্ম|প্রতি|সিটি", "persons"),
    ("upazila_count", r"উপজেলা", r"ভূমি|অফিস|স্বাস্থ্য|দূরত্ব|দুরত্ব|নির্বাহী|পরিষদ|নাম|হেড|সদর|কমপ্লেক্স|উপকূল|সীমান্ত", "count"),
    ("thana_count", r"থানা", r"নাম|পুলিশ|দূরত্ব|দুরত্ব", "count"),
    ("city_corporation_count", r"সিটি\s*কর্পোরেশন", r"ওয়ার্ড|নাম", "count"),
    ("pourashava_count", r"পৌরসভা|পৌর সভা", r"ওয়ার্ড|মৌজা|নাম|আয়তন|জনসংখ্যা|হোল্ডিং", "count"),
    ("union_count", r"ইউনিয়ন", r"ভূমি|অফিস|ভবন|নাম|ডিজিটাল|তথ্য|কমপ্লেক্স|ওয়ার্ড|দূরত্ব|দুরত্ব|স্বাস্থ্য|কেন্দ্র|কল্যাণ|সাব|ক্লিনিক|উদ্যোক্তা|সচিব|চেয়ারম্যান|সদস্য|সড়ক|রাস্তা|সদর", "count"),
    ("ward_count", r"ওয়ার্ড|ওয়ার্ড|ওযার্ড|ওয়াড", r"সদস্য|মেম্বার|কাউন্সিলর|নাম|পৌর|নং|ভিত্তিক|সিটি", "count"),
    ("mouza_count", r"মৌজা", r"পৌর|নাম", "count"),
    ("village_count", r"গ্রাম", r"গুচ্ছ|আদর্শ|ভিত্তিক|পৌর|নাম|সংসদ|গ্রামীণ|পুলিশ|চৌকিদার|আশ্রয়|রক্ষা", "count"),
    ("household_count", r"পরিবার সংখ্যা|পরিবারের সংখ্যা|মোট পরিবার|খানার সংখ্যা|খানা সংখ্যা|^\W*খানা\W*$|মোট খানা",
     r"পায়খানা|এতিম|কৃষক|পরিকল্পনা|কল্যাণ|উপজাতি|আদিবাসী|উপকৃত", "households"),
]


def dv_number(s, dot_thousands=True, skip_year=False):
    s = dv_asc(s)
    ms = [m.group(0).rstrip(".,") for m in re.finditer(r"\d[\d,\.]*", s)]
    if skip_year:                       # '(২০২২ সালের আদমশুমারি) ১,২৩,৪৫৬' -> skip the year
        while ms and re.fullmatch(r"(19|20)\d\d", ms[0]):
            ms = ms[1:]                 # a lone year is not a figure
    if not ms:
        return "", ""
    raw = ms[0]
    note = ""
    w = re.match(r"\s*((?:\d+(?:\.\d+)?\s*(?:কোটি|লক্ষ|লাখ|হাজার)\s*)+\d*)", s[s.find(raw):])
    if w and re.search(r"কোটি|লক্ষ|লাখ", w.group(1)):                  # '১ কোটি ৪৭ লক্ষ ৩৪ হাজার ৭০১ জন'
        mult = {"কোটি": 10 ** 7, "লক্ষ": 10 ** 5, "লাখ": 10 ** 5, "হাজার": 1000}
        total = 0
        for num, unit in re.findall(r"(\d+(?:\.\d+)?)\s*(কোটি|লক্ষ|লাখ|হাজার)?", w.group(1)):
            total += round(float(num) * mult.get(unit, 1))
        return str(total), f"written in words '{w.group(1).strip()}', converted"
    if dot_thousands and re.fullmatch(r"\d{1,3}(\.\d{3})+", raw):
        note, raw = f"'{raw}' read as thousands separator", raw.replace(".", "")
    if re.fullmatch(r"\d{1,3}", raw) and (sp := re.match(r"\d{1,3}(?:,\s?\d{2,3})*,\s?\d{3}(?![\d,.])", s[s.find(raw):])) \
            and re.search(r"\s", sp.group(0)):
        v = re.sub(r"\D", "", sp.group(0))       # '২, ১৫, ২৬০ জন', '১৬, ৫৫৫ জন' (sylhet.gov.bd portals): spaces after commas
        return v, f"printed '{sp.group(0)}' (spaces after the commas), read as {v}"
    if re.fullmatch(r"\d+", raw) and (sp := re.match(r"\d+\. (\d{1,2})(?=\s*(?:বর্গ|কি\.?\s*মি|একর|হেক্টর))", s[s.find(raw):])):
        return f"{raw}.{sp.group(1)}", f"printed '{sp.group(0)}' (a space after the decimal point), read as " \
                                      f"{raw}.{sp.group(1)}"     # '২৬৩৬. ৫৮ বর্গকিলোমিটার' (habiganj.gov.bd)
    return raw.replace(",", ""), note


def dv_kv_pairs(c):
    pairs = []
    for cells in dv_rows(c):
        cs = [t.strip(" |") for t, _ in cells]
        cs = [t for t in cs if t and not re.fullmatch(r"[:ঃ=\-–]+", t)]
        while cs and re.fullmatch(DV_SERIAL, cs[0]):
            cs = cs[1:]
        if len(cs) >= 2:
            pairs.append((cs[0], cs[1]))
    for line in c["text"].split("\n"):
        m = re.match(r"^\s*(?:[(]?[০-৯0-9ক-হ]{1,2}\s*[।\.\)]\s*)?([^:ঃ|=]{2,60}?)\s*[:ঃ=]\s*(.+)$", line)
        if m:
            pairs.append((m.group(1).strip(" -•"), m.group(2).strip()))
        # prose without a separator: 'মোট জনসংখ্যা ৫৮,৯৯,০৫২', 'আয়তন ৪৩৬৩.৪৮ বর্গ কিলোমিটার। এটি …' (mymensingh.gov.bd)
        elif (m := re.match(r"^\s*(?:[(]?[০-৯0-9]{1,2}\s*[।\.\)]\s*)?([ঀ-৿][ঀ-৿ ]{1,30}?)\s+([০-৯0-9][০-৯0-9,.]*"
                            r"\s*(?:জন|টি|বর্গ\s*কিলোমিটার|বর্গ\s*কি\.?\s*মি\.?)?)\s*(?:।|$)", line)):
            pairs.append((m.group(1).strip(), m.group(2).strip()))
    # a row of labels followed by a row of figures ('উপজেলার সংখ্যা | থানার সংখ্যা' / '০৭ টি | ০৭টি'): column-wise
    rows = [[t.strip(" |") for t, _ in cells if t.strip(" |")] for cells in dv_rows(c)]
    for r1, r2 in zip(rows, rows[1:]):
        if len(r1) >= 2 and len(r1) == len(r2) and all(not re.search(r"[০-৯0-9]", x) for x in r1) and \
                all(re.match(r"^[০-৯0-9]", x) and not re.match(r"^[০-৯0-9]{1,3}\s*[.।)]\s*[^\d০-৯]", x) for x in r2):
            pairs += list(zip(r1, r2))
    return pairs


DV_BOUNDS = {  # plausible ranges per level; counts outside are dropped, areas/populations get a DOUBT note
    "division": dict(area_km2=(1000, 40000), population=(1e6, 1e8), upazila_count=(5, 200), thana_count=(5, 200),
                     union_count=(50, 2000), pourashava_count=(1, 200), mouza_count=(100, 30000),
                     village_count=(100, 40000), city_corporation_count=(0, 10), ward_count=(0, 1e5),
                     household_count=(1e5, 2e7)),
    "district": dict(area_km2=(300, 10000), population=(2e5, 2e7), upazila_count=(2, 20), thana_count=(2, 80),
                     union_count=(10, 250), pourashava_count=(1, 20), mouza_count=(50, 5000), village_count=(50, 10000),
                     household_count=(1e4, 5e6), city_corporation_count=(0, 3)),
    "upazila": dict(area_km2=(10, 1500), population=(5000, 2e6), union_count=(2, 25), pourashava_count=(0, 3),
                    mouza_count=(5, 1000), village_count=(5, 1500), household_count=(1000, 5e5)),
    "union": dict(area_km2=(0.5, 200), population=(1000, 2e5), mouza_count=(1, 150), village_count=(1, 200),
                  ward_count=(3, 15), household_count=(100, 5e4)),
    "pourashava": dict(area_km2=(1, 200), population=(1000, 1e6), ward_count=(3, 30), mouza_count=(1, 100),
                       household_count=(100, 2e5)),
}


def dv_facts(c, wanted=None, div=None, own=(), level=None):
    """Label matcher: [dict(fact, value, unit, year, label, raw, note)], first match per fact. Count labels that name
    a place of the division (e.g. 'পীরগঞ্জ উপজেলা | ১০টি' in a per-upazila table) are skipped."""
    out, seen = [], set()
    places = set()
    if div:
        places = {k for m in div.u_key.values() for k in m if len(k) > 3} | {k for k in div.d_key if len(k) > 3}
        places -= {dv_loose(x) for x in own}
    for label, value in dv_kv_pairs(c):
        lab = re.sub(r"^\s*[(]?[০-৯0-9ক-হ]{1,2}\s*[।\.\)]\s*", "", dv_nfc(label))
        lab = re.sub(r"সংখ্যা\s*ও\s*নাম", "সংখ্যা", lab)                     # 'পৌরসভার সংখ্যা ও নাম' 
        for fact, inc, exc, unit in DV_FACT_LABELS:
            if (wanted and fact not in wanted) or fact in seen or not re.search(inc, lab) or re.search(exc, lab):
                continue
            if len(lab) > 45:
                continue
            # the figure is in the label ('আয়তন ২৭ বর্গ কি' | 'মি:,মৌজা-৭টি, …'), or the value starts with a union number
            # ('আয়তন ও গঠন' | '১০ নং সিধলা ইউনিয়নের মোট আয়তন …'): label and value are misaligned
            if re.search(r"[০-৯0-9][০-৯0-9.,]*\s*\(?\s*(?:বর্গ|ব(?:$|[:ঃ.\s])|একর|কি|মাইল|হেক্টর)", lab) or \
                    re.match(r"^\D{0,3}[০-৯0-9]{1,2}\s*নং", value):
                continue
            v, note = dv_number(value, dot_thousands=(fact != "area_km2"), skip_year=(fact == "population"))
            if not v:
                continue
            y = re.search(r"(?<![\d.,])(19|20)\d\d(?![\d.,])", dv_asc(value))
            year = y.group(0) if y and y.group(0) != v else ""                 # '১৯৯৯টি' is a count, not a year
            if fact == "population" and re.match(r"^\W*(\([কখ]\))?\s*(পুরুষ|নারী|মহিলা)", value) and "মোট" not in value:
                continue
            if fact.endswith("_count") and places and any(p in dv_loose(lab) for p in places):
                continue
            if fact == "population" and re.search(r"মোট\s*(জনসংখ্যা|লোকসংখ্যা)?[\s:ঃ\-–\.]*[০-৯0-9]", value):
                tail = re.split(r"মোট\s*(?:জনসংখ্যা|লোকসংখ্যা)?[\s:ঃ\-–\.]*(?=[০-৯0-9])", value)[-1]
                v, note = dv_number(tail)
                note = (note + "; " if note else "") + "took the figure after 'মোট' (total)"
            u = unit
            if fact == "area_km2":
                after = dv_asc(value)[re.search(r"\d", dv_asc(value)).start():][:40]
                if re.search(r"^[\d,\.\s]*(বর্গ\s*)?মাইল|^[\d,\.\s]*sq\.?\s*mile", after, re.I):
                    u = "sq_miles"
                elif re.search(r"^[\d,\.\s]*(বর্গ\s*)?একর", after):
                    u = "acres"
                elif re.search(r"^[\d,\.\s]*হেক্টর", after):
                    u = "hectares"
                elif not re.search(r"^[\d,\.\s\(\)]*(বর্গ\.?\s*কি|বগ\s*কি|বঃ\s*কি|ব\s*[:\.]\s*কি|ব\.কি|বর্গকি|কিঃ|কি\.\s*মি|কিলো|km|sq\s*km|কিমি)", after, re.I):
                    u = "unstated"
            if u in ("count", "persons", "households"):
                if not re.fullmatch(r"\d+", v):
                    continue
                if u == "count" and re.search(r"কিলোমিটার|কিঃ\s*মিঃ|কি\.\s*মি|কিমি|\bkm\b", value):
                    continue                                        # a distance, not a count
                v = str(int(v))
            if not re.fullmatch(r"\d+(\.\d+)?", v):
                continue                                            # '8.56.99': not one number
            if level and fact in DV_BOUNDS.get(level, {}) and not (fact == "area_km2" and u != "km2"):
                lo, hi = DV_BOUNDS[level][fact]
                if not lo <= float(v) <= hi:
                    if u in ("count", "households"):
                        continue                                    # label/value misaligned: drop
                    note = (note + "; " if note else "") + f"DOUBT: {v} is implausible for a {level}"
            elif level and fact not in DV_BOUNDS.get(level, {fact: 0}):
                continue
            seen.add(fact)
            out.append(dict(fact=fact if not (fact == "area_km2" and u != "km2") else "area", value=v, unit=u,
                            year=year, label=lab, raw=dv_nfc(value)[:160], note=note))
    # 'এটি ১৩টি উপজেলা, ১ টি সিটি করপোরেশন , ১৪টি থানা, ১০ টি পৌরসভা (…), ১৪৫ টি ইউনিয়ন, ২২০১টি মৌজা, ২৭০৯টি গ্রাম নিয়ে
    # গঠিত' (mymensingh.gov.bd): the counts in a sentence saying what the unit is made of
    for sent in re.findall(r"[^।\n]*নিয়ে\s*গঠিত", c["text"]):
        for mm in re.finditer(r"(?<![০-৯0-9.,])([০-৯0-9]{1,5})\s*টি\s*(উপজেলা|থানা|পৌরসভা|ইউনিয়ন|মৌজা|গ্রাম|"
                              r"সিটি\s*কর্?পোরেশন)(?![ঀ-৿])", sent):
            num, noun = mm.groups()
            fact = {"উপজেলা": "upazila_count", "থানা": "thana_count", "পৌরসভা": "pourashava_count",
                    "ইউনিয়ন": "union_count", "মৌজা": "mouza_count", "গ্রাম": "village_count"}.get(noun,
                                                                                         "city_corporation_count")
            v = int(dv_asc(num))
            if fact in seen or (wanted and fact not in wanted) or (level and fact not in DV_BOUNDS.get(level, {})) or \
                    (level and not DV_BOUNDS[level][fact][0] <= v <= DV_BOUNDS[level][fact][1]):
                continue
            seen.add(fact)
            out.append(dict(fact=fact, value=str(v), unit="count", year="", label=noun, raw=mm.group(0),
                            note="in the sentence '… নিয়ে গঠিত' (what the unit is made of)"))
    # inline 'উপজেলা ও থানা - ০৮, ... পৌরসভা -৩ (...), ইউনিয়ন-৭৬' inside a longer cell
    for fact, rx in (("upazila_count", r"উপজেলা(?: ও থানা)?"), ("union_count", r"ইউনিয়ন"),
                     ("pourashava_count", r"পৌরসভা"), ("mouza_count", r"মৌজা")):
        if fact in seen or (wanted and fact not in wanted):
            continue
        m = re.search(r"(?<![ঀ-৿])(" + rx + r")\s*[-–]\s*([০-৯0-9]{1,4})(?![০-৯0-9.,])", c["text"])
        if m and level and fact in DV_BOUNDS.get(level, {}) and not \
                DV_BOUNDS[level][fact][0] <= int(dv_asc(m.group(2))) <= DV_BOUNDS[level][fact][1]:
            continue
        if m and (not level or fact in DV_BOUNDS.get(level, {})):
            seen.add(fact)
            out.append(dict(fact=fact, value=str(int(dv_asc(m.group(2)))), unit="count", year="", label=m.group(1),
                            raw=m.group(0), note="inline in a longer cell"))
    return out


def dv_write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})


def dv_slug(s):
    """File-name form of an English name ('Cox's Bazar' -> 'coxsbazar')."""
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def dv_save_raw(out, name, url, c):
    """Save the page text (phones and e-mails redacted). A page that also names people (dv_lists_persons: members or
    chairmen with mobiles, lists of persons) is not saved: returns False (True when saved, None without out)."""
    if not out:
        return None
    if dv_lists_persons(c):
        return False
    os.makedirs(os.path.join(out, "raw"), exist_ok=True)
    with open(os.path.join(out, "raw", name), "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\nUPDATED: {c['updated']}\nTITLE: {c['title']}\nACCESSED: {time.strftime('%Y-%m-%d')}\n\n"
                f"{dv_redact(c['text'])}\n")
    return True


def dv_manifest(out, template):
    """Write SOURCE.json: template fields (kept from an existing manifest if present) + file checksums."""
    p = os.path.join(out, "SOURCE.json")
    m = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    for k, v in template.items():
        if k not in m or k in ("urls", "division", "kind"):
            m[k] = v
    files = {}
    for root, _, fs in os.walk(out):
        for f in sorted(fs):
            rel = os.path.relpath(os.path.join(root, f), out).replace(os.sep, "/")
            if rel in ("SOURCE.json", "fetch.py", "REPORT.md") or "__pycache__" in rel:
                continue
            files[rel] = hashlib.sha256(open(os.path.join(root, f), "rb").read()).hexdigest()
    m["files"] = dict(sorted(files.items()))
    m["accessed"] = time.strftime("%Y-%m-%d")
    order = ["key", "name", "organization", "source_type", "trust_level", "division", "kind", "urls", "accessed",
             "publication_date", "license", "license_url", "attribution", "files", "notes"]
    m = {k: m[k] for k in order if k in m} | {k: v for k, v in m.items() if k not in order}
    with open(p, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
        f.write("\n")


def dv_upd(c):
    return f"page updated {c['date']}" if c and c.get("date") else "page update date not shown"


# ---------------------------------------------------------------------------------------- district portal
def dv_collect_district(F, div, d, key, log):
    """One DC portal: district row, upazilas, unions, pourashavas, এক নজরে facts. Returns dict of lists."""
    info = div.districts[d]
    base = f"https://{info['host']}/"
    areas, facts, pages = [], [], []
    res = dict(areas=areas, facts=facts, pages=pages, unions=[], stated={}, glance=None, union_url="")

    def page(kind, url):
        c = dv_content(F.get(url))
        pages.append(dict(district_en=d, kind=kind, url=url, status="ok" if c else (F.errors.get(url) or "no content block"),
                          updated=c["date"] if c else "", title=c["title"] if c else ""))
        return c

    home = F.get(base)
    if not home or dv_nfc(info["name_bn"]) not in dv_nfc(re.search(r"<title>(.*?)</title>", home, re.S).group(1) if
                                                       re.search(r"<title>(.*?)</title>", home, re.S) else ""):
        pages.append(dict(district_en=d, kind="home", url=base, status=F.errors.get(base) or "title does not name the district"))
        log(f"{d}: portal {base} unavailable")
        return res
    title = dv_nfc(re.search(r"<title>(.*?)</title>", home, re.S).group(1)).strip()
    pages.append(dict(district_en=d, kind="home", url=base, status="ok", title=title))
    menu = dv_menu(home, base)
    host = info["host"]
    areas.append(dict(level="district", name_en=d, name_bn=info["name_bn"], parent_level="division",
                      parent_name_en=div.name_en, parent_name_bn=div.name_bn, district_en=d, website=base,
                      source_url=base, source_key=key,
                      notes=f"portal title '{title}'; name_en is the project's key (not printed)"))

    # এক নজরে
    g = dv_pick(menu, r"নজরে", r"আশ্রয়|পৌরসভা|প্রকল্প|ভূমি|কৃষি|সদর হাসপাতাল", host)
    if g:
        c = page("glance", g[1])
        if c:
            res["glance"] = (g[1], c)
            for f in dv_facts(c, div=div, level="district"):
                facts.append(dict(entity_level="district", entity_name_en=d, district_en=d, fact=f["fact"],
                                  value=f["value"], unit=f["unit"], basis="as stated", year=f["year"], source_key=key,
                                  source_url=g[1], notes=dv_redact(f"label '{f['label']}' value '{f['raw']}'" +
                                                                   (f"; {f['note']}" if f["note"] else "") + f"; {dv_upd(c)}")))
    # upazilas: rows come from the union list (and the upazila list page where there is one)
    upz = {}
    ul = dv_pick(menu, r"উপজেলার তালিকা|উপজেলা পরিষদের তালিকা|উপজেলা পরিষদসমূহ|^উপজেলা তালিকা$|^উপজেলা\s*(?:সমূহ|সমুহ)$",
                 r"নির্বাহী|ভূমি", host) \
        or dv_pick(menu, r"^উপজেলা পরিষদ\s*(?:,|$)", r"নির্বাহী|ভূমি", host)    # 'উপজেলা পরিষদ, চট্টগ্রাম'
    ul_c = None
    if ul:
        c = ul_c = page("upazilas", ul[1])
        if c:
            n = 0
            rows_ = dv_rows(c)
            if len(rows_) <= 3 and all(len(r) == 1 for r in rows_) and \
                    (its := [x for r in rows_ for x in dv_numbered_items(r[0][0])]):
                rows_ = [[(x, [])] for x in its]   # prose with the list run together (patuakhali.gov.bd)
            for cells in rows_:
                for t, ls in cells:
                    t0 = re.sub(r"^[০-৯0-9]+\s*[.।)]?\s*|\s*উপজেলা.*$", "", t)
                    t1 = re.sub(r"\s*[,.]\s*" + re.escape(info["name_bn"]) + r"\s*[।.]?$", "", t0)  # 'ভোলা সদর, ভোলা।'
                    u = div.upazila(d, t1)
                    if u and u not in upz:
                        n += 1
                        site = next((dv_site(h) for h, _ in ls if div.under(d, h)), "")
                        row_sites = {dv_site(h) for _, ls2 in cells for h, _ in ls2 if div.under(d, h)}
                        if not site and len(row_sites) == 1:               # the link in another column of the row
                            site = row_sites.pop()
                        upz[u] = dict(printed=t1.strip(), website=site, url=ul[1],
                                      note=dv_upd(c) + (f"; printed '{t.strip()}'" if t1 != t0 else "") +
                                      ("; DOUBT: printed spelling looks like a misprint" if t1.strip() in div.misprints
                                       else ""))
            facts.append(dict(entity_level="district", entity_name_en=d, district_en=d, fact="upazila_count_listed",
                              value=str(n), unit="count", basis="count of upazilas listed", source_key=key,
                              source_url=ul[1], notes=dv_upd(c)))
    # unions
    un = dv_pick(menu, r"ইউনিয়নের তালিকা|ইউনিয়ন পরিষদের তালিকা|উপজেলা ও ইউনিয়ন|ইউনিয়ন পরিষদসমূহ|^ইউনিয়ন পরিষদ$|"
                       r"^ইউনিয়ন\s*(?:সমূহ|সমুহ)$",                    # 'ইউনিয়ন সমূহ' (netrokona.gov.bd)
                 r"চেয়ারম্যান|সচিব|উদ্যোক্তা|কাজি|জনপ্রতিনিধি|তথ্য ও সেবা", host)
    cands = [un] + [x for x in menu if x != un and re.search(r"উপজেলা ও ইউনিয়ন|ইউনিয়ন পরিষদসমূহ|ইউনিয়নের তালিকা", x[0])
                    and "/pages/" in x[1] and urlparse(x[1]).netloc.lower() == host] if un else []
    if not un and ul and ul_c and "ইউনিয়ন" in ul_c["text"]:
        cands = [ul]                             # the upazila list also names the unions (pirojpur.gov.bd)
    best = None
    for x in cands:
        c = page("unions", x[1])
        if not c:
            continue
        rows, stated = dv_union_list(c, div, district=d)
        good = [r for r in rows if "warning" not in r]
        if best is None or len(good) > len(best[1]):
            best = (x[1], good, stated, c, [r["warning"] for r in rows if "warning" in r])
    if best:
        url, rows, stated, c, warns = best
        res.update(unions=rows, stated=stated, union_url=url, union_page=c)
        for (d2, u), st in sorted(stated.items()):          # upazilas named with a count but no union names
            if d2 == d and not any(r["upazila_en"] == u for r in rows):
                upz.setdefault(u, dict(printed=st[2] or div.upz_bn(d, u), website="", url=url,
                                       note=dv_upd(c) + "; named on the union page with a union count only"))
                facts.append(dict(entity_level="upazila", entity_name_en=u, district_en=d, upazila_en=u,
                                  fact="union_count_stated", value=st[0], unit="count", basis="as stated",
                                  source_key=key, source_url=url, notes=f"printed '{st[1]}'; union names not listed; {dv_upd(c)}"))
        if not rows:
            log(f"{d}: union page {url} names no unions")
        for w in warns:
            log(f"{d} union list: {w}")
        per = {}
        for r in rows:
            per.setdefault(r["upazila_en"], []).append(r)
            if dv_loose(r["upazila_printed"]) == dv_loose(info["name_bn"]):     # the district's name as the heading
                r["flags"] = r.get("flags", "") + f"; listed under '{r['upazila_printed']}' (the district's name in " \
                                                  f"the upazila column), read as {r['upazila_en']}"
            upz.setdefault(r["upazila_en"], dict(printed=r["upazila_printed"], website="", url=url, note=dv_upd(c) + (
                f"; printed '{r['upazila_printed']}' (the district's name) as the heading of the unions of "
                f"{r['upazila_en']}" if dv_loose(r["upazila_printed"]) == dv_loose(info["name_bn"]) else "")))
            areas.append(dict(level="union", name_bn=r["name_bn"], parent_level="upazila", parent_name_en=r["upazila_en"],
                              parent_name_bn=r["upazila_printed"], district_en=d, upazila_en=r["upazila_en"], code=r["no"],
                              code_scheme="UNION_NO_IN_UPAZILA" if r["no"] else "", website=r["website"], source_key=key,
                              source_url=url, name_en=r.get("name_en", ""),
                              notes=f"printed '{r['printed']}'" + (f"; row printed {r['dup']} times on the page"
                              if r.get("dup") else "") + r.get("flags", "") + f"; {dv_upd(c)}{dv_en_note(r)}"))
        for u, rs in per.items():
            note = dv_upd(c)
            dup = [f"{r['name_bn']} ({r['dup']}x)" for r in rs if r.get("dup")]
            if dup:
                note += f"; counted once although printed more than once: {', '.join(dup)}"
            facts.append(dict(entity_level="upazila", entity_name_en=u, district_en=d, upazila_en=u, fact="union_count",
                              value=str(len(rs)), unit="count", basis="count of unions listed", source_key=key,
                              source_url=url, notes=note))
            if (d, u) in stated:
                facts.append(dict(entity_level="upazila", entity_name_en=u, district_en=d, upazila_en=u,
                                  fact="union_count_stated", value=stated[(d, u)][0], unit="count", basis="as stated",
                                  source_key=key, source_url=url, notes=f"printed '{stated[(d, u)][1]}'; {dv_upd(c)}"))
        if rows:
            facts.append(dict(entity_level="district", entity_name_en=d, district_en=d, fact="union_count_listed",
                              value=str(len(rows)), unit="count", basis="count of unions listed", source_key=key,
                              source_url=url, notes=dv_upd(c)))
        m = re.search(r"মোট ইউনিয়ন\s*[:ঃ\-–]?\s*([০-৯0-9]+)|([০-৯0-9]+)\s*টি ইউনিয়ন", c["text"])
        if m and rows:
            facts.append(dict(entity_level="district", entity_name_en=d, district_en=d, fact="union_count",
                              value=str(int(dv_asc(m.group(1) or m.group(2)))), unit="count", basis="as stated",
                              source_key=key, source_url=url, notes=f"printed '{m.group(0)}'; {dv_upd(c)}"))
    else:
        log(f"{d}: no union list page found")
    for u, r in sorted(upz.items()):
        if not r["website"] and div.upz_sub(d, u):
            site = div.upz_site(d, u)
            t = F.get(site)
            m = re.search(r"<title>(.*?)</title>", t or "", re.S)
            if m and any(dv_loose(x) in dv_loose(m.group(1)) for x in div.upz_names(d, u)) and "উপজেলা" in m.group(1):
                r["website"] = site
                r["note"] += f"; website not linked from the list, verified by fetching it (title '{dv_nfc(m.group(1)).strip()}')"
        if (div.key, u) in DV_NEW_UPAZILAS:
            r["note"] += "; upazila not in the project seed yet; name_en transliterated from the portal subdomain"
        areas.append(dict(level="upazila", name_en=u, name_bn=r["printed"], parent_level="district", parent_name_en=d,
                          parent_name_bn=info["name_bn"], district_en=d, upazila_en=u, website=r["website"],
                          source_key=key, source_url=r["url"],
                          notes=f"{r['note']}; name_en is the project's key (not printed)"))

    # pourashavas: list page, menu links named '<x> পৌরসভা', এক নজরে text
    poura = {}

    def add_p(printed, url, note, site=""):
        nm = dv_nfc(printed).strip(" |।,.")
        nm = re.sub(r"^[০-৯0-9]+\s*[.।)]?\s*", "", nm)
        nm = re.sub(r"\s*(পৌরসভার ওয়েবসাইট|এর ওয়েবসাইট|ওয়েবসাইট)$", "", nm)
        upz_ = None
        # 'বেনাপোলপৌরসভা, শার্শা' / 'জেলা পৌরসভা, মাগুরা' (jashore.gov.bd, magura.gov.bd): the pourashava, then its
        # upazila (or the district, for the district town's pourashava)
        pm = re.fullmatch(r"([ঀ-৿ ]+?)\s*পৌরসভা\s*,\s*([ঀ-৿ ]+)", nm)
        if pm:
            a, b = pm.group(1).strip(), pm.group(2).strip()
            to_d = dv_loose(b) == dv_loose(info["name_bn"])
            ub = div.upazila(d, b) or (div.upazila(d, "সদর") if to_d else None)
            if ub and (a != "জেলা" or to_d):
                upz_ = (ub, b)
                note += f"; printed '{nm}'" + ("" if a != "জেলা" else ", read as the district town's pourashava")
                nm = (b if a == "জেলা" else a) + " পৌরসভা"
        if not nm or re.search(r"তালিকা|সংখ্যা|নাম$|এক নজরে|একনজরে|আয়তন|ঠিকানা|যোগাযোগ|মেয়র|ওয়ার্ড|শ্রেণ|^বিস্তারিত$|"
                               r"^(এক|দুই|তিন|চার|পাঁচ|ছয়|সাত|আট|নয়|দশ|এগার|বার)$", nm):
            return 0
        full = nm if nm.endswith("পৌরসভা") else nm + " পৌরসভা"
        # 'চুয়াডাঙ্গা সদর পৌরসভা' (এক নজরে) is 'চুয়াডাঙ্গা পৌরসভা' (menu link): one row
        full = next((k for k in poura if k.replace(" সদর পৌরসভা", " পৌরসভা") == full.replace(" সদর পৌরসভা", " পৌরসভা")),
                    full)
        if full not in poura:
            poura[full] = dict(printed=nm, url=url, notes=[note], website=site, upazila=upz_)
            return 1
        if note not in poura[full]["notes"]:
            poura[full]["notes"].append(note)
        poura[full]["website"] = poura[full]["website"] or site
        return 0

    pl = dv_pick(menu, r"পৌরসভার তালিকা|পৌরসভা সমূহ|পৌরসভাসমূহ", None, host)
    if pl:
        c = page("pourashavas", pl[1])
        if c:
            n = 0
            rows_ = dv_rows(c)
            num = [r for r in rows_ if len(r) == 1 and re.match(r"^[০-৯0-9]{1,2}\s*[.।)]\s*[ঀ-৿]", r[0][0])]
            if num and not re.search(r"<tr", c["html"]):     # prose and a numbered list: the numbered lines only
                rows_ = num                                  # (magura.gov.bd)
            if len(rows_) <= 3 and all(len(r) == 1 for r in rows_) and \
                    (its := [x for r in rows_ for x in dv_numbered_items(r[0][0], 2)]):
                rows_ = [[(x, [])] for x in its]     # 'মোট ৫টি পৌরসভা আছে। …: ১। পটুয়াখালী পৌরসভা, পটুয়াখালী সদর ২। …'
            for cells in rows_:
                nm, site = "", ""
                for t, ls in cells:
                    if not t or re.fullmatch(DV_SERIAL, t) or re.search(DV_HEADER, t) or t in ("-", "–"):
                        continue
                    if re.search(r"\.gov\.bd|https?://|\.com|www\.", t) and not re.search(r"[ঀ-৿]", t):
                        site = dv_site(t)
                    elif not nm and re.search(r"[ঀ-৿]", t):
                        nm = t
                        site = site or next((dv_site(h) for h, _ in ls if re.search(r"pourashava|paurashava|pourosova|municipality|ps\.", h, re.I)), "")
                if nm and (re.match(DV_HONORIFIC, nm) or re.search(r"প্রশাসক|মেয়র", nm)):
                    mp = re.search(r"(?:প্রশাসক|মেয়র)\S*\s+([^,।]+?পৌরসভা)", nm)   # 'জনাব .. প্রশাসক রায়পুর পৌরসভা, ..'
                    nm = mp.group(1) if mp else ""
                if nm and not re.search(r"পৌরসভার তালিকা|জেলার", nm):
                    n += add_p(nm, pl[1], f"listed on '{c['title']}' ({dv_upd(c)})", site)
            facts.append(dict(entity_level="district", entity_name_en=d, district_en=d, fact="pourashava_count_listed",
                              value=str(n), unit="count", basis="count of pourashavas listed", source_key=key,
                              source_url=pl[1], notes=dv_upd(c)))
    for x, h in menu:
        if re.fullmatch(r"[ঀ-৿ ]+ পৌরসভা(র ওয়েবসাইট)?", x) and h.startswith("http") \
                and urlparse(h).netloc.lower() != host:
            if "/pages/" in h:
                add_p(x, base, f"menu link '{x}' on the district portal points to {h}")
            else:
                add_p(x, base, f"menu link '{x}' on the district portal", dv_site(h))
        elif (mp := re.fullmatch(r"পৌরসভা\s*,\s*([ঀ-৿ ]+?)\s*[।.]?", x)) and h.startswith("http") \
                and urlparse(h).netloc.lower() != host and "/pages/" not in h:
            add_p(mp.group(1) + " পৌরসভা", base, f"menu link '{x}' on the district portal", dv_site(h))  # bhola.gov.bd
    if res["glance"]:
        gu, c = res["glance"]
        # 'পৌরসভা -৩ (বদরগঞ্জ, হারাগাছ এবং পীরগঞ্জ)', 'পৌরসভার সংখ্যা ও নাম | ৩টি। যথা: দোহার, ধামরাই ও সাভার পৌরসভা',
        # 'পৌরসভা সংখ্যা | ৫ (পাচ) টি। ফরিদপুর, বোয়ালমারী, ...': names are used only when they add up to the count
        for m in re.finditer(r"পৌরসভা\S*(?:\s*সংখ্যা)?(?:\s*ও\s*নাম)?(?:\s*[|\-–:ঃ])*\s*([০-৯0-9]{1,2})(?![০-৯0-9.,])\s*"
                             r"(?:\(([^)]*)\))?\s*(?:টি)?\s*[।,:ঃ|]?\s*(?:যথা\s*[:ঃ]?)?\s*\(?([^|\n)]*)", c["text"]):
            parts = []
            for part in (m.group(2) or "", m.group(3) or ""):
                parts.append([])
                for nm in re.split(r"\s*(?:,|।|\s+এবং\s+|\s+ও\s+)\s*", part):
                    nm = re.sub(r"^[০-৯0-9]+\s*[.।)]\s*|\s*পৌরসভা\S*$", "", nm.strip(" ্"))
                    # 'গোলাপগঞ্জ-‘ক’শ্রেণী', 'বিশ্বনাথ- ‘গ’ শ্রেণী' (sylhet.gov.bd): the pourashava's class follows the name
                    nm = re.sub(r"\s*[-–]\s*[‘'\"]?[কখগ][’'\"]?\s*শ্রেণী$", "", nm)
                    if nm and re.fullmatch(r"[ঀ-৿]+(?: [ঀ-৿]+){0,2}", nm) and not re.fullmatch(
                            r"এক|দুই|তিন|চার|পাঁচ|পাচ|ছয়|সাত|আট|নয়|দশ|এগার|বার|টি", nm):
                        parts[-1].append(nm)
            names, shown = parts[0] + parts[1], m.group(0)
            if len(parts[0]) == int(dv_asc(m.group(1))):
                names = parts[0]         # 'পৌরসভা | ৪ (শেরপুর, নকলা, নালিতাবাড়ি, শ্রীবরদী) |' (sherpur.gov.bd): the brackets
                shown = m.group(0)[:m.end(2) + 1 - m.start(0)]
            if names and len(names) == int(dv_asc(m.group(1))):
                for nm in names:
                    add_p(nm, gu, f"named in এক নজরে ('{shown.strip()}', {dv_upd(c)})")
                break
    shared = {s for s in [p["website"] for p in poura.values()] if s and
              sum(q["website"] == s for q in poura.values()) > 1}         # e.g. one link to paurainfo.gov.bd for all
    upz_sites = {div.upz_site(d, e) for e, *_ in info["upazilas"]}
    for full, p in poura.items():
        if p["website"] in shared:
            p["notes"].append(f"linked to {p['website']}, which the list gives for several pourashavas (not used)")
            p["website"] = ""
        elif p["website"].replace("://www.", "://") in upz_sites:   # 'মেলান্দহ পৌরসভা | https://melandah.jamalpur.gov.bd'
            p["notes"].append(f"printed address {p['website']} is the upazila portal, not the pourashava's (not used)")
            p["website"] = ""
        base_nm = re.sub(r"\s*পৌরসভা$", "", full)
        u = div.upazila(d, base_nm) or div.upazila(d, base_nm + " সদর")
        if not u and dv_loose(base_nm) == dv_loose(info["name_bn"]):
            u = div.upazila(d, "সদর")
        note = "; ".join(dict.fromkeys(p["notes"]))
        if p.get("upazila"):
            u = p["upazila"][0]
            note += f"; parent upazila as printed ('{p['upazila'][1]}')"
        else:
            note += "; parent upazila inferred from the same-named upazila" if u else "; parent upazila not stated"
        if p["printed"] != full:
            note += f"; printed '{p['printed']}'"
        areas.append(dict(level="pourashava", name_bn=full, parent_level="upazila" if u else "district",
                          parent_name_en=u or d, parent_name_bn=div.upz_bn(d, u) if u else info["name_bn"], district_en=d,
                          upazila_en=u or "", website=p["website"], source_key=key, source_url=p["url"], notes=note))
    res["pourashavas"] = list(poura)
    return res


# ---------------------------------------------------------------------------------------- national office registry
DV_NATIONAL_UNIONS = "https://bangladesh.gov.bd/views/union-list"   # linked as "ইউনিয়নের তালিকা" (e.g. dhakadiv.gov.bd)


def dv_national(F, div, url=DV_NATIONAL_UNIONS):
    """National portal's list of union (and upazila) portals, filtered to the division. Returns dict(url, upazilas=
    {(district_en, upazila_en): row}, unions=[row], unmatched=[...]) or None. A row: district_en, upazila_en, name_bn,
    printed, geo_name_bn, website, bbs (district-upazila-union codes as given)."""
    t = F.get(url)
    i = (t or "").find("const __lists = {")
    if i < 0:
        return None
    s, dec, lists = t[i:], json.JSONDecoder(), {}
    for k in ("upazilas", "unions"):
        j = s.find(k + ": [")
        if j < 0:
            return None
        lists[k] = dec.raw_decode(s[j + len(k) + 2:])[0]
    by_host = {h: d for d in div.districts for h in div.hosts(d)}
    res, office = dict(url=url, upazilas={}, unions=[], unmatched=[]), {}
    for x in lists["upazilas"]:
        full = (x.get("subdomain") or "").lower()
        host = full.partition(".")[2]
        d = by_host.get(host)
        u = next((e for e, *_ in div.districts[d]["upazilas"] if urlparse(div.upz_site(d, e)).netloc == full),
                 None) if d else None
        if d and u:
            office[x.get("office_id")] = (d, u)
            res["upazilas"][(d, u)] = dict(district_en=d, upazila_en=u, printed=dv_nfc(x.get("title_bn", "")).strip(),
                                           website=dv_site(x["subdomain"]),
                                           bbs=f"{(x.get('district') or {}).get('bbs_code', '')}-"
                                               f"{(x.get('upazila') or {}).get('bbs_code') or ''}")
        elif host in by_host:
            res["unmatched"].append(f"upazila portal {x.get('subdomain')} ({x.get('title_bn')}) not in the configuration")
    for x in lists["unions"]:
        if (x.get("division") or {}).get("title_bn") != div.name_bn and not office.get(x.get("parent_id")):
            continue
        du = office.get(x.get("parent_id"))
        if not du:
            res["unmatched"].append(f"union portal {x.get('subdomain')} ({x.get('title_bn')}): parent upazila portal unknown")
            continue
        printed = dv_nfc(x.get("title_bn", "")).strip()
        geo = dv_nfc((x.get("union") or {}).get("title_bn", "")).strip()
        name, no = dv_clean_union(re.split(r"\s*,\s*", printed)[0])
        note = ""
        if not re.search(r"[ঀ-৿]", name):
            name, note = geo, "portal title not in Bangla; name from the registry's geo record"
        if not name:
            res["unmatched"].append(f"union portal {x.get('subdomain')} ({printed}): no Bangla name")
            continue
        res["unions"].append(dict(district_en=du[0], upazila_en=du[1], name_bn=name, printed=printed, geo_name_bn=geo,
                                  no=no, website=dv_site(x["subdomain"]), note=note,
                                  bbs=f"{(x.get('district') or {}).get('bbs_code', '')}-"
                                      f"{(x.get('upazila') or {}).get('bbs_code') or ''}-"
                                      f"{(x.get('union') or {}).get('bbs_code') or ''}"))
    return res


def dv_registry_doubt(nat, d, u, name):
    """DOUBT note when the national list of union portals has a union of this name in another upazila of the district."""
    if not nat:
        return ""
    k = dv_loose(name)
    where = sorted({x["upazila_en"] for x in nat["unions"] if x["district_en"] == d and
                    k in (dv_loose(x["name_bn"]), dv_loose(x["geo_name_bn"]))})
    if where and u not in where:
        return f"DOUBT: the national list of union portals ({nat['url']}) has this union under {', '.join(where)}"
    return ""


def dv_registry_fill(a, nat):
    """Fill an area row's union portal address from the national list of union portals (same district and upazila,
    same name up to dv_loose); the note says where it came from. Nothing when the list has no such union."""
    k = dv_loose(a["name_bn"])
    w = next((x["website"] for x in nat["unions"] if x["district_en"] == a["district_en"] and
              x["upazila_en"] == a.get("upazila_en") and k in (dv_loose(x["name_bn"]), dv_loose(x["geo_name_bn"]))),
             "") if nat and k else ""
    if w:
        a["website"] = w
        a["notes"] += f"; website from the national portal's list of union portals ({nat['url']}), not linked from this page"
    return w


def dv_national_csv(out, nat):
    rows = [dict(level="upazila", **{k: v for k, v in r.items()}) for r in nat["upazilas"].values()] + \
           [dict(level="union", **r) for r in nat["unions"]]
    dv_write_csv(os.path.join(out, "raw", "national_portal_list.csv"),
                 ["level", "district_en", "upazila_en", "name_bn", "printed", "geo_name_bn", "website", "bbs"], rows)


# ---------------------------------------------------------------------------------------- divisional portal
def dv_district_table_facts(c, div):
    """'জেলা | আয়তন (ব:কি:মি:) | উপজেলা | … | জনসংখ্যা | …' with one row per district and a 'সর্বমোট' row (এক নজরে,
    mymensinghdiv.gov.bd): [dict(district (None for the total row), fact, value, unit, label, row, raw, note)]."""
    rows = [[x.strip() for x, _ in cells] for cells in dv_rows(c)]
    out = []
    for i, hdr in enumerate(rows):
        if len(hdr) < 4 or hdr[0] != "জেলা":
            continue
        cols = {}
        for j, lab in enumerate(hdr[1:], 1):
            for fact, inc, exc, unit in DV_FACT_LABELS:
                if re.search(inc, lab) and not re.search(exc, lab) and not re.search(r"সিটি|ভোটার|আসন", lab) and \
                        fact not in [v[0] for v in cols.values()]:
                    cols[j] = (fact, unit, lab)
                    break
        for r in rows[i + 1:]:
            if len(r) != len(hdr):
                break
            d = div.district(r[0])
            if not d and not re.fullmatch(r"সর্ব\s*মোট|মোট", r[0]):
                break
            for j, (fact, unit, lab) in cols.items():
                v, note = dv_number(r[j], dot_thousands=(fact != "area_km2"))
                if not v or not re.fullmatch(r"\d+(\.\d+)?", v):
                    continue
                if fact == "area_km2" and not re.search(r"ব\s*[:ঃ.]?\s*কি|বর্গ\s*কি|কি\.?\s*মি", lab):
                    fact, unit = "area", "unstated"
                if unit in ("count", "persons", "households"):
                    if not re.fullmatch(r"\d+", v):
                        continue
                    v = str(int(v))
                    if re.fullmatch(r"\d[\d,]*", dv_asc(r[j])) and "," in r[j] and not re.fullmatch(
                            r"\d{1,3}(,\d{3})+|\d{1,2}(,\d{2})*,\d{3}", dv_asc(r[j])):
                        note = f"DOUBT: digit grouping '{r[j]}' is irregular, read as {v}"
                lv = "district" if d else "division"
                if fact in DV_BOUNDS[lv] and not DV_BOUNDS[lv][fact][0] <= float(v) <= DV_BOUNDS[lv][fact][1]:
                    continue
                out.append(dict(district=d, fact=fact, value=v, unit=unit, label=lab, row=r[0], raw=r[j], note=note))
        break
    return out


def dv_collect_division(F, div, key, log):
    """Divisional Commissioner portal: district list, upazila list, union list, এক নজরে facts."""
    base = f"https://{div.cfg['portal']}/"
    areas, facts, pages = [], [], []
    res = dict(areas=areas, facts=facts, pages=pages, unions=[], upazilas={}, districts=[], raw={})

    def page(kind, url):
        c = dv_content(F.get(url))
        pages.append(dict(kind=kind, url=url, status="ok" if c else (F.errors.get(url) or "no content block"),
                          updated=c["date"] if c else "", title=c["title"] if c else ""))
        if c:
            res["raw"][kind] = (url, c)
        return c

    home = F.get(base)
    m = re.search(r"<title>(.*?)</title>", home or "", re.S)
    if not m or dv_nfc(div.name_bn) not in dv_nfc(m.group(1)):
        log(f"divisional portal {base} unavailable: {F.errors.get(base)}")
        pages.append(dict(kind="home", url=base, status=F.errors.get(base) or "title does not name the division"))
        return res
    pages.append(dict(kind="home", url=base, status="ok", title=dv_nfc(m.group(1)).strip()))
    menu = dv_menu(home, base)
    host = div.cfg["portal"]
    g = dv_pick(menu, r"নজরে", r"আশ্রয়|প্রকল্প", host)
    if g and (c := page("glance", g[1])):
        got = dv_district_table_facts(c, div)
        for f in dv_facts(c, div=div, level="division"):
            if any(x["fact"] == f["fact"] and not x["district"] for x in got):
                continue                         # the total row of the district table gives it
            facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact=f["fact"], value=f["value"],
                              unit=f["unit"], basis="as stated", year=f["year"], source_key=key, source_url=g[1],
                              notes=f"label '{f['label']}' value '{f['raw']}'" + (f"; {f['note']}" if f["note"] else "")
                              + f"; {dv_upd(c)}"))
        for x in got:
            d = x["district"]
            facts.append(dict(entity_level="district" if d else "division", entity_name_en=d or div.name_en,
                              district_en=d or "", fact=x["fact"], value=x["value"], unit=x["unit"], basis="as stated",
                              source_key=key, source_url=g[1],
                              notes=f"column '{x['label']}', row '{x['row']}', value '{x['raw']}' in the table of districts"
                                    + (f"; {x['note']}" if x["note"] else "") + f"; {dv_upd(c)}"))
    # 'উপজেলার তালিকা' contains 'জেলার তালিকা': not a district list. 'আওতাধীন জেলা প্রশাসন' (barishaldiv.gov.bd, whose
    # 'জেলার তালিকা' links an old national portal page) lists 'জেলা প্রশাসকের কার্যালয়, <জেলা>' with the DC portal links
    dl = dv_pick(menu, r"(?<!উপ)জেলার তালিকা|(?<!উপ)জেলাসমূহ|(?<!উপ)জেলা সমূহ", None, host) or \
        dv_pick(menu, r"^জেলা ও উপজেলা$", None, host) or dv_pick(menu, r"^আওতাধীন জেলা প্রশাসন$", None, host)
    if dl and (c := page("districts", dl[1])):
        cells_ = [(t, ls) for cells in dv_rows(c) for t, ls in cells]
        # 'জেলার সংখ্যাঃ ১১টি- চট্টগ্রাম, কুমিল্লা, ...' (chittagongdiv.gov.bd): one item per district
        pl = next((m for t, _ in cells_ if (m := re.match(r"^জেলার সংখ্যা\s*[:ঃ]?\s*([০-৯0-9]+)\s*টি\s*[-–:ঃ]?\s*(.+)$", t))),
                  None)
        if pl and not any(div.district(re.sub(r"^[০-৯0-9]+\s*[.।)]?\s*|\s*জেলা$", "", t)) for t, _ in cells_):
            cells_ = [(x.strip(" ।"), "") for x in pl.group(2).split(",") if x.strip(" ।")]
            facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact="district_count",
                              value=str(int(dv_asc(pl.group(1)))), unit="count", basis="as stated", source_key=key,
                              source_url=dl[1], notes=f"printed 'জেলার সংখ্যাঃ {pl.group(1)}টি'; {dv_upd(c)}"))
        for cells in [cells_]:
            for t, ls in cells:
                dn = re.sub(r"^জেলা প্রশাসকের কার্যালয়\s*,\s*", "", t)   # 'জেলা প্রশাসকের কার্যালয়, বরিশাল'
                d = div.district(re.sub(r"^[০-৯0-9]+\s*[.।)]?\s*|\s*জেলা$", "", dn))
                if d and d not in res["districts"]:
                    res["districts"].append(d)
                    lk = next((h for h, _ in ls or [] if urlparse(h).netloc.lower().removeprefix("www.") in div.hosts(d)), "")
                    areas.append(dict(level="district", name_en=d, name_bn=dv_nfc(dn).strip(), parent_level="division",
                                      parent_name_en=div.name_en, parent_name_bn=div.name_bn, district_en=d,
                                      code=str(len(res["districts"])).zfill(2), code_scheme=f"{div.code.upper()}DIV_LIST_SERIAL",
                                      website=f"https://{div.districts[d]['host']}/", source_key=key, source_url=dl[1],
                                      notes=f"{dv_upd(c)}; name_en is the project's key (not printed); website is the DC "
                                            + (f"portal (linked from this page as {lk})" if lk else
                                               "portal (not linked from this page)")
                                            + (f"; printed '{dv_nfc(t).strip()}'" if dn != t else "")))
        facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact="district_count_listed",
                          value=str(len(res["districts"])), unit="count", basis="count of districts listed",
                          source_key=key, source_url=dl[1], notes=dv_upd(c)))
    ul = dv_pick(menu, r"উপজেলার তালিকা|উপজেলাসমূহ|উপজেলা সমূহ", None, host)
    if ul and (c := page("upazilas", ul[1])):
        cur_d, n, lined = None, 0, False
        rows_ = dv_rows(c)
        # one column per district: 'ক্রমিক | সিলেট জেলা | সুনামগঞ্জ জেলা | …', then '০১ | বালাগঞ্জ | বিশ্বম্ভরপুর | …' and
        # 'মোট | ১৩টি | ১২টি | …' (sylhetdiv.gov.bd): each cell is an upazila of its column's district
        col = next(((i, [div.district(re.sub(r"\s*জেলা$", "", x.strip())) for x, _ in cells]) for i, cells in enumerate(rows_)
                    if sum(bool(div.district(re.sub(r"\s*জেলা$", "", x.strip()))) for x, _ in cells) >= 2), None)
        if col:
            hi, cds = col
            for cells in rows_[hi + 1:]:
                tot = bool(cells) and re.fullmatch(r"মোট\s*[:ঃ]?", cells[0][0].strip()) is not None
                for j, (x, _) in enumerate(cells):
                    x = x.strip()
                    if j >= len(cds) or not cds[j] or not x:
                        continue
                    if tot and (mc := re.fullmatch(r"([০-৯0-9]{1,2})\s*টি", x)):
                        facts.append(dict(entity_level="district", entity_name_en=cds[j], district_en=cds[j],
                                          fact="upazila_count", value=str(int(dv_asc(mc.group(1)))), unit="count",
                                          basis="as stated", source_key=key, source_url=ul[1],
                                          notes=f"printed 'মোট … {x}' in the {div.districts[cds[j]]['name_bn']} জেলা "
                                                f"column; {dv_upd(c)}"))
                        continue
                    u = div.upazila(cds[j], x)
                    if not u:
                        log(f"divisional upazila list: unknown upazila {x!r} (district {cds[j]} column)")
                        continue
                    n += 1
                    res["upazilas"][(cds[j], u)] = x
                    areas.append(dict(level="upazila", name_en=u, name_bn=dv_nfc(x), parent_level="district",
                                      parent_name_en=cds[j], parent_name_bn=div.districts[cds[j]]["name_bn"],
                                      district_en=cds[j], upazila_en=u, source_key=key, source_url=ul[1],
                                      notes=f"{dv_upd(c)}; name_en is the project's key (not printed); listed in the "
                                            f"'{div.districts[cds[j]]['name_bn']} জেলা' column (the row serial is "
                                            f"shared by the districts' columns, not used as a code)"
                                            + ("; DOUBT: printed spelling looks like a misprint" if dv_nfc(x) in div.misprints
                                               else "")))
            rows_ = []
        for cells in rows_:
            names = [t for t, _ in cells if t and not re.fullmatch(DV_SERIAL, t) and not re.search(DV_HEADER, t)]
            if not names:
                continue
            # a line naming the district above its upazilas, one per line (barishaldiv.gov.bd): 'বরিশাল জেলার
            # উপজেলাগুলি হল-', 'পটুয়াখালী জেলায় ৮টি উপজেলা রয়েছেঃ', 'পিরোজপুর জেলা ৭টি উপজেলায় বিভক্ত; এগুলো হলোঃ'
            lm = re.match(r"^(\S+)\s+জেলা\S*\s+(?:([০-৯0-9]{1,2})\s*টি\s+)?উপজেলা", names[0]) \
                if len(names) == 1 and len(names[0].split()) <= 9 and re.search(r"[-–:ঃ]\s*$", names[0]) else None
            if lm and div.district(lm.group(1)):
                cur_d, lined = div.district(lm.group(1)), True
                if lm.group(2):
                    facts.append(dict(entity_level="district", entity_name_en=cur_d, district_en=cur_d,
                                      fact="upazila_count", value=str(int(dv_asc(lm.group(2)))), unit="count",
                                      basis="as stated", source_key=key, source_url=ul[1],
                                      notes=f"printed '{names[0]}'; {dv_upd(c)}"))
                continue
            if len(names) >= 2 and div.district(names[0]):
                cur_d, names = div.district(names[0]), names[1:]
            elif cur_d is None and div.district(names[0]):
                cur_d, names = div.district(names[0]), names[1:]
            serial = next((dv_asc(t).strip(" .।") for t, _ in cells if re.fullmatch(DV_SERIAL, t or "x")), "")
            ch = {}
            # 'ময়মনসিংহ | ১৩টি | ময়মনসিংহ সদর, ত্রিশাল, … হালুয়াঘাটও ধোবাউড়া।' (mymensinghdiv.gov.bd): the district's
            # count, then its upazilas in one comma list; the items get no row serial
            if cur_d and len(names) >= 2 and (mc := re.fullmatch(r"([০-৯0-9]{1,2})\s*টি", names[0].strip())) and \
                    names[1].count(",") >= 2:
                facts.append(dict(entity_level="district", entity_name_en=cur_d, district_en=cur_d, fact="upazila_count",
                                  value=str(int(dv_asc(mc.group(1)))), unit="count", basis="as stated", source_key=key,
                                  source_url=ul[1], notes=f"printed '{names[0].strip()}' in the district's row; {dv_upd(c)}"))
                items = [x.strip(" ।.") for x in re.split(r"\s*,\s*|\s+ও\s+", names[1]) if x.strip(" ।.")]
                if items and not div.upazila(cur_d, items[-1]) and (mo := re.fullmatch(r"(\S+)ও\s+(\S+)", items[-1])) \
                        and div.upazila(cur_d, mo.group(1)) and div.upazila(cur_d, mo.group(2)):
                    ch = {mo.group(1): f"printed '{items[-1]}' ('ও' written onto the name)"}
                    items[-1:] = [mo.group(1), mo.group(2)]
                names = items
                ch = {x: ch.get(x, "listed in the district's comma-separated list") for x in items}
            # one cell per district: a heading 'খুলনা জেলার উপজেলা সমূহ', then one 'কয়রা উপজেলা' per line
            # (khulnadiv.gov.bd); each item is an upazila, its row serial is the district's
            heads = {}
            hm = re.match(r"^(\S+)\s+জেলার\s+উপজেলা\s*সমূহ\s+(.+)$", names[-1]) if cur_d and names else None
            if hm and div.district(hm.group(1)) == cur_d:
                items = [x.strip() for x in re.findall(r"(\S.*?)\s*উপজেলা(?=\s|$)", hm.group(2))]
                names = names[:-1] + items
                heads = {x: f"printed '{x} উপজেলা' under the heading '{hm.group(1)} জেলার উপজেলা সমূহ'" for x in items}
            heads.update(ch)
            for t in names:
                u = div.upazila(cur_d, t) if cur_d else None
                if not u:
                    log(f"divisional upazila list: unknown upazila {t!r} (district {cur_d})")
                    continue
                n += 1
                nm = re.sub(r"\s*উপজেলা\s*[।.]?$", "", t) if lined else t      # one per line: 'হিজলা উপজেলা'
                res["upazilas"][(cur_d, u)] = nm
                areas.append(dict(level="upazila", name_en=u, name_bn=dv_nfc(nm), parent_level="district",
                                  parent_name_en=cur_d, parent_name_bn=div.districts[cur_d]["name_bn"], district_en=cur_d,
                                  upazila_en=u, code="" if heads or lined else serial.zfill(2),
                                  code_scheme="" if heads or lined else f"{div.code.upper()}DIV_LIST_SERIAL",
                                  source_key=key, source_url=ul[1],
                                  notes=f"{dv_upd(c)}; name_en is the project's key (not printed)"
                                        + (f"; {heads[t]} (row serial {serial} is the district's)" if t in heads else "")
                                        + (f"; printed '{t}' on a line of its own under the district's heading line"
                                           if lined else "")
                                        + ("; DOUBT: printed spelling looks like a misprint" if dv_nfc(nm) in div.misprints
                                           else "")))
        m = re.search(r"মোট\s*([০-৯0-9]+)\s*টি", c["text"]) or \
            re.search(r"উপজেলার সংখ্যা\s*[:ঃ]?\s*([০-৯0-9]+)\s*টি", c["text"])          # sylhetdiv.gov.bd
        facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact="upazila_count_listed", value=str(n),
                          unit="count", basis="count of upazilas listed", source_key=key, source_url=ul[1], notes=dv_upd(c)))
        if m:
            facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact="upazila_count",
                              value=str(int(dv_asc(m.group(1)))), unit="count", basis="as stated", source_key=key,
                              source_url=ul[1], notes=f"printed '{m.group(0)}' in the list heading; {dv_upd(c)}"))
    if not res["upazilas"] and "districts" in res["raw"]:     # 'নরসিংদী | বেলাবো, মনোহরদী, ...' (dhakadiv.gov.bd)
        url, c = res["raw"]["districts"]
        n = 0
        for cells in dv_rows(c):
            texts = [t for t, _ in cells if t and t.strip(" |")]
            d = div.district(re.sub(r"\s*জেলা$", "", texts[0])) if len(texts) >= 2 and "," in texts[1] else None
            # '১. চট্টগ্রাম- (মোট ১৫টি) মীরসরাই, সীতাকুণ্ড, ...' (chittagongdiv.gov.bd): one line per district
            pm = re.match(r"^[০-৯0-9]{1,2}\s*[.।)]\s*([^\s(\-–]+)\s*[-–]?\s*\(\s*মোট\s*([০-৯0-9]+)\s*টি\s*\)\s*[-–]?\s*(.+)$",
                          texts[0]) if len(texts) == 1 else None
            if pm and div.district(pm.group(1)):
                d, texts = div.district(pm.group(1)), [pm.group(1), pm.group(3)]
                facts.append(dict(entity_level="district", entity_name_en=d, district_en=d, fact="upazila_count",
                                  value=str(int(dv_asc(pm.group(2)))), unit="count", basis="as stated", source_key=key,
                                  source_url=url, notes=f"printed '(মোট {pm.group(2)}টি)'; {dv_upd(c)}"))
            if not d:
                continue
            for t in [x.strip(" ।") for x in texts[1].split(",") if x.strip(" ।")]:
                u, extra = div.upazila(d, t), ""
                if u and dv_loose(t) == dv_loose("সদর"):
                    extra = "; printed 'সদর' only, read as the district's Sadar upazila"
                if not u and dv_loose(t) == dv_loose(div.districts[d]["name_bn"]):
                    u, extra = div.upazila(d, "সদর"), "; printed with the district name only (no 'সদর'), read as the Sadar upazila"
                if not u:
                    log(f"divisional district/upazila table: unknown upazila {t!r} (district {d})")
                    continue
                n += 1
                res["upazilas"][(d, u)] = t
                areas.append(dict(level="upazila", name_en=u, name_bn=dv_nfc(t), parent_level="district", parent_name_en=d,
                                  parent_name_bn=div.districts[d]["name_bn"], district_en=d, upazila_en=u, source_key=key,
                                  source_url=url, notes=f"listed on '{c['title']}' ({dv_upd(c)}){extra}; "
                                                        f"name_en is the project's key (not printed)"))
        facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact="upazila_count_listed", value=str(n),
                          unit="count", basis="count of upazilas listed", source_key=key, source_url=url, notes=dv_upd(c)))
        m = re.search(r"উপজেলার সংখ্যা\s*[:ঃ]?\s*([০-৯0-9]+)\s*টি", c["text"])
        if m:
            facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact="upazila_count",
                              value=str(int(dv_asc(m.group(1)))), unit="count", basis="as stated", source_key=key,
                              source_url=url, notes=f"printed '{m.group(0)}'; {dv_upd(c)}"))
    nl = dv_pick(menu, r"ইউনিয়নের তালিকা|ইউনিয়নসমূহ|ইউনিয়ন সমূহ", None, host)
    ext = next((h for x, h in menu if re.search(r"ইউনিয়নের তালিকা", x) and h.rstrip("/") == DV_NATIONAL_UNIONS), None)
    partial = lined = False
    if nl and (c := page("unions", nl[1])):
        rows, stated = dv_union_list(c, div)
        hr = dv_district_headed_rows(c, div)
        if hr and (any("warning" in r for r in rows) or not rows):   # 'জেলা: সুনামগঞ্জ' above each table (sylhetdiv.gov.bd)
            rows2, stated2 = dv_union_list(c, div, rows=hr)
            if sum("warning" not in r for r in rows2) > sum("warning" not in r for r in rows):
                rows, stated = rows2, stated2
        if not any("warning" not in r for r in rows):   # a page of lines, not a table (barishaldiv.gov.bd)
            lr, stated, lw = dv_lined_union_list(c, div)
            rows, lined = lr + [dict(warning=w) for w in lw], True
        for r in rows:
            if "warning" in r:
                log(f"divisional union list: {r['warning']}")
        rows = [r for r in rows if "warning" not in r]
        res["unions"] = rows
        partial = bool(rows) and {r["district_en"] for r in rows} != set(div.districts)
        per = {}
        for r in rows:
            per.setdefault((r["district_en"], r["upazila_en"]), []).append(r)
            note = f"printed '{r['printed']}'; upazila printed '{r['upazila_printed']}'" + r.get("flags", "")
            if r.get("dup"):
                note += f"; row printed {r['dup']} times"
            areas.append(dict(level="union", name_bn=r["name_bn"], parent_level="upazila", parent_name_en=r["upazila_en"],
                              parent_name_bn=r["upazila_printed"], district_en=r["district_en"], upazila_en=r["upazila_en"],
                              code=r["no"], code_scheme="UNION_NO_IN_UPAZILA" if r["no"] else "", website=r["website"],
                              source_key=key, source_url=nl[1], name_en=r.get("name_en", ""),
                              notes=f"{note}; {dv_upd(c)}{dv_en_note(r)}"))
        for (d, u), rs in sorted(per.items()):
            facts.append(dict(entity_level="upazila", entity_name_en=u, district_en=d, upazila_en=u, fact="union_count",
                              value=str(len(rs)), unit="count", basis="count of unions listed", source_key=key,
                              source_url=nl[1], notes=dv_upd(c)))
        for (d, u), st in sorted(stated.items(), key=lambda kv: (kv[0][0], kv[0][1] or "")):
            if not lined and u and len(st) == 3:  # 'হালুয়াঘাট | - | ১২টি' (a count column; mymensinghdiv.gov.bd)
                facts.append(dict(entity_level="upazila", entity_name_en=u, district_en=d, upazila_en=u,
                                  fact="union_count_stated", value=st[0], unit="count", basis="as stated",
                                  source_key=key, source_url=nl[1], notes=f"printed '{st[2]} … {st[1]}'; {dv_upd(c)}"))
            if lined:                            # stated counts of the line layout (dv_lined_union_list)
                facts.append(dict(entity_level="upazila" if u else "district", entity_name_en=u or d, district_en=d,
                                  upazila_en=u or "", fact="union_count_stated" if u else "union_count", value=st[0],
                                  unit="count", basis="as stated", source_key=key, source_url=nl[1],
                                  notes=f"printed '{st[1]}'; {dv_upd(c)}"))
        cur = None                               # 'মোট: ১৩টি | ১০টি | ১৪৫ টি' under 'ময়মনসিংহ জেলা' (mymensinghdiv.gov.bd)
        for cells in hr or []:
            cur = next((x for _, ls in cells for h, x in ls if h == "#dv-district"), cur)
            ts = [x.strip() for x, _ in cells]
            mt = re.fullmatch(r"মোট\s*[:ঃ]\s*([০-৯0-9]{1,2})\s*টি", ts[0]) if cur and len(ts) == 3 else None
            mu = re.fullmatch(r"([০-৯0-9]{1,3})\s*টি", ts[2]) if mt else None
            if mu:
                for fact, v in (("upazila_count", mt.group(1)), ("union_count", mu.group(1))):
                    facts.append(dict(entity_level="district", entity_name_en=cur, district_en=cur, fact=fact,
                                      value=str(int(dv_asc(v))), unit="count", basis="as stated", source_key=key,
                                      source_url=nl[1], notes=f"printed '{' | '.join(ts)}' (total row of the "
                                                              f"{div.districts[cur]['name_bn']} জেলা table); {dv_upd(c)}"))
        facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact="union_count_listed",
                          value=str(len(rows)), unit="count", basis="count of unions listed", source_key=key,
                          source_url=nl[1], notes=dv_upd(c) + (f"; the page lists unions of {len({r['district_en'] for r in rows})} "
                                                               f"of the {len(div.districts)} districts only" if partial else "")))
        m = re.search(r"তালিকা\s*[:ঃ]\s*([০-৯0-9]+)\s*টি", c["text"]) or \
            re.search(r"মোট ইউনিয়ন সংখ্যা\s*[:ঃ]\s*([০-৯0-9]+)\s*টি", c["text"])         # mymensinghdiv.gov.bd
        if m:
            facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact="union_count",
                              value=str(int(dv_asc(m.group(1)))), unit="count", basis="as stated", source_key=key,
                              source_url=nl[1], notes=f"printed '{m.group(0)}' in the list heading; {dv_upd(c)}"))
        else:       # '০১ | সিলেট | ১০৬ টি', 'সিলেট জেলায় মোট ইউনিয়ন: | ১০৬ টি', '০৪টি জেলায় মোট ইউনিয়ন | ৩৩৯ টি'
            seen_d = set()
            for cells in dv_rows(c):
                ts = [x.strip() for x, _ in cells if x and x.strip(" |") and not re.fullmatch(DV_SERIAL, x)]
                mc = re.fullmatch(r"([০-৯0-9]{1,4})\s*টি", ts[1]) if len(ts) == 2 else None
                if not mc:
                    continue
                d = div.district(re.sub(r"\s*জেলায়\s*মোট\s*ইউনিয়ন\S*(?:\s*সংখ্যা)?\s*[:ঃ]?$", "", ts[0]))
                if d and d not in seen_d:
                    seen_d.add(d)
                    facts.append(dict(entity_level="district", entity_name_en=d, district_en=d, fact="union_count",
                                      value=str(int(dv_asc(mc.group(1)))), unit="count", basis="as stated",
                                      source_key=key, source_url=nl[1], notes=f"printed '{ts[0]} | {ts[1]}'; {dv_upd(c)}"))
                elif not d and re.search(r"জেলায়\s*মোট\s*ইউনিয়ন", ts[0]):
                    facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact="union_count",
                                      value=str(int(dv_asc(mc.group(1)))), unit="count", basis="as stated",
                                      source_key=key, source_url=nl[1], notes=f"printed '{ts[0]} | {ts[1]}'; {dv_upd(c)}"))
    # the national list: unions only where the menu links it; otherwise just the upazila portal addresses (also when
    # the portal's own union list leaves out districts)
    # a portal list covering every district (sylhetdiv.gov.bd): the registry gives the upazila portal addresses and the
    # union portal addresses where the names match; its own union rows are not added
    fill = bool(nl) and not partial and bool(res["upazilas"])
    ext = None if fill else ext
    nat = dv_national(F, div) if (not nl and (ext or res["upazilas"])) or (partial and res["upazilas"]) or fill else None
    if (not nl and (ext or nat)) or (partial and nat) or (fill and nat):
        pages.append(dict(kind="unions" if ext else "national_registry", url=ext or DV_NATIONAL_UNIONS,
                          status="ok" if nat else (F.errors.get(ext) or "no list data"),
                          title="ইউনিয়নসমূহ | বাংলাদেশ জাতীয় তথ্য বাতায়ন" + (" (linked from the menu)" if ext else
                                                                         " (not linked from this portal)")))
    if nat:
        res["national"] = nat if ext else dict(nat, unions=[])
        for m_ in nat["unmatched"] if ext else []:
            log(f"national list: {m_}")
        for a in areas:                                    # upazila websites from the registry
            r = nat["upazilas"].get((a["district_en"], a.get("upazila_en"))) if a["level"] == "upazila" else None
            if r and not a.get("website"):
                a["website"] = r["website"]
                a["notes"] += (f"; website from the national portal's list ({ext}), registry title '{r['printed']}'" if ext
                               else f"; website from the national portal's office registry ({DV_NATIONAL_UNIONS}, not "
                                    f"linked from this portal), registry title '{r['printed']}'")
            if (partial or fill) and a["level"] == "union" and not a.get("website"):   # the portal's own list
                dv_registry_fill(a, nat)
        per = {}
        for r in nat["unions"] if ext else []:
            per.setdefault((r["district_en"], r["upazila_en"]), []).append(r)
            note = f"union portal listed as '{r['printed']}'"
            if r["geo_name_bn"] and dv_loose(r["geo_name_bn"]) != dv_loose(r["name_bn"]):
                note += f"; registry geo name '{r['geo_name_bn']}'"
            if r["note"]:
                note += "; " + r["note"]
            areas.append(dict(level="union", name_bn=r["name_bn"], parent_level="upazila", parent_name_en=r["upazila_en"],
                              parent_name_bn=dv_nfc(res["upazilas"].get((r["district_en"], r["upazila_en"])) or
                                                    div.upz_bn(r["district_en"], r["upazila_en"])),
                              district_en=r["district_en"], upazila_en=r["upazila_en"], code=r["no"],
                              code_scheme="UNION_NO_IN_UPAZILA" if r["no"] else "", website=r["website"],
                              source_key=key, source_url=ext,
                              notes=f"{note}; national portal list of union portals (linked from the divisional "
                                    f"portal menu as 'ইউনিয়নের তালিকা'); BBS codes as given {r['bbs']}; English name not printed"))
        for (d, u), rs in sorted(per.items()):
            facts.append(dict(entity_level="upazila", entity_name_en=u, district_en=d, upazila_en=u, fact="union_portal_count",
                              value=str(len(rs)), unit="count", basis="count of union portals listed", source_key=key,
                              source_url=ext, notes="national portal list of union portals"))
        if ext:
            facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact="union_portal_count",
                              value=str(len(nat["unions"])), unit="count", basis="count of union portals listed",
                              source_key=key, source_url=ext, notes="national portal list of union portals"))
    return res


def dv_lined_union_list(c, div):
    """A divisional union page written as lines (barishaldiv.gov.bd 'ইউনিয়নের তালিকা'): district headings ('ভোলা জেলা :',
    'বরিশাল জেলায় মোট ১০ টি উপজেলা রয়েছে। …'), upazila headings ('উপজেলা : গৌরনদী', 'ভান্ডারিয়া উপজেলা', or a line
    naming the upazila above a comma list), then one union per line, numbered lines or a comma list. Returns (rows,
    stated, warnings); rows as dv_union_list; stated {(district_en, upazila_en or None): (count, printed)}."""
    lines = [x.strip(" |") for x in c["text"].split("\n")]
    lines = [x for x in lines if x and not re.match(r"^(কন্টেন্ট|কনটেন্টটি)", x)]
    out, stated, warns = [], {}, []
    cur_d = cur_u = None
    cur_u_printed = ""
    for i, ln in enumerate(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        m = re.match(r"^(\S+)\s*(?:জেলা\S*)?\s*[:ঃ]\s*$", ln) or re.match(r"^(\S+)\s+জেলা\S*\s+মোট", ln)
        if m and div.district(m.group(1)):
            cur_d, cur_u = div.district(m.group(1)), None
            mt = re.search(r"ইউনিয়নের সংখ্যা\s*([০-৯0-9]+)\s*টি", ln)
            if mt:
                stated[(cur_d, None)] = (str(int(dv_asc(mt.group(1)))), mt.group(0))
            continue
        if cur_d is None or div.district(ln) == cur_d:          # 'পিরোজপুর' below 'পিরোজপুর জেলা :'
            continue
        mt = re.match(r"^মোট উপজেলা\s*[:ঃ]\s*[০-৯0-9]+\s*,\s*মোট ইউনিয়ন\s*[:ঃ]\s*([০-৯0-9]+)", ln)
        if mt:
            stated[(cur_d, None)] = (str(int(dv_asc(mt.group(1)))), mt.group(0))
            continue
        mt = re.match(r"^মোট ইউনিয়ন\S*\s*[:ঃ]\s*([০-৯0-9]+)\s*টি", ln)
        if mt and cur_u:
            stated[(cur_d, cur_u)] = (str(int(dv_asc(mt.group(1)))), mt.group(0))
            continue
        if re.search(DV_HEADER, ln) or re.fullmatch(r"উপজেলা(র)?\s*(ও ইউনিয়ন|তালিকা)", ln):
            continue
        mu = re.match(r"^উপজেলা\s*[:ঃ]\s*(.+)$", ln) or re.match(r"^(?:[০-৯0-9]{1,2}\s*[.।)]\s*)?(.+?)\s*উপজেলা\s*[।.]?$", ln)
        u = div.upazila(cur_d, mu.group(1)) if mu else None
        if not u and (nxt.count(",") >= 2 or re.match(r"^মোট ইউনিয়ন", nxt)):
            u = div.upazila(cur_d, ln)                          # 'বোরহান উদ্দিন' above its comma list
        if u:
            cur_u, cur_u_printed = u, (mu.group(1) if mu and div.upazila(cur_d, mu.group(1)) else ln).strip()
            continue
        if mu or "উপজেলা" in ln:
            warns.append(f"unknown upazila heading {ln!r}")
            cur_u = None
            continue
        if cur_u is None:
            warns.append(f"union before any upazila heading: {ln!r}")
            continue
        items = dv_numbered_items(ln, 2) or (dv_comma_items(ln) if ln.count(",") >= 2 else [ln])  # '২। নদমুলা-শিয়ালকাঠী'
        for x in items:
            name, no = dv_clean_union(x)
            if name and not dv_junk(name) and len(name.split()) <= 4:
                out.append(dict(district_en=cur_d, upazila_en=cur_u, upazila_printed=cur_u_printed, name_bn=name,
                                printed=dv_nfc(x).strip(), no=no, website=""))
    return out, stated, warns


# ---------------------------------------------------------------------------------------- upazila portals
DV_UNION_MENU_EX = r"বিদ্যালয়|মাধ্যমিক|কলেজ|মাদ্রাসা|স্বাস্থ্য|জাদুঘর|লাইব্রের|কমিটি|বাল্যবিবাহ|শ্রমিক|ইজিপিপি|কর্মসূচ|তথ্য ও সেবা|চেয়ারম্যান|সচিব|উদ্যোক্তা|কাজি|জনপ্রতিনিধি|ভূমি|ডিজিটাল|কার্যালয়|সদস্য|নির্বাচন|বাজেট|প্রকল্প|হট ?লাইন"


def dv_title(t):
    m = re.search(r"<title>(.*?)</title>", t or "", re.S)
    return dv_nfc(html.unescape(m.group(1))).strip() if m else ""


def dv_lists_persons(c):
    """A list page that names people: a column of chairmen, secretaries, members or UDC entrepreneurs (often with
    mobiles), or several names with honorifics. Such pages are not used and their text is not saved."""
    t = c["text"]
    return bool(re.search(r"(চেয়ার\S*|চেয়ায়\S*|সচিব\S*|উদ্যোক্তা\S*|সদস্য\S*)\s*(নাম|ও মোবাইল)|নাম ও মোবাইল|"
                          r"মোবাইল\s*(নম্বর|নং)", t)) or \
        len(re.findall(r"(?<![ঀ-৿])(মোঃ|মো:|মোছাঃ|মোসাঃ|জনাব)", t)) >= 3


def dv_collect_upazila(F, div, d, u, key, out, site=None):
    """One upazila portal: union list, এক নজরে facts, pourashava pages."""
    site = site or div.upz_site(d, u)
    u_bn = div.upz_bn(d, u)
    res = dict(areas=[], facts=[], pages=[], unions=[], log=[], site=site, ok=False)
    if not site:
        res["pages"].append(dict(district_en=d, upazila_en=u, kind="home", url="", status="no portal address known"))
        return res
    home = F.get(site)
    title = dv_title(home)
    if not home or not any(dv_loose(x) in dv_loose(title) for x in div.upz_names(d, u)):
        res["pages"].append(dict(district_en=d, upazila_en=u, kind="home", url=site,
                                 status=F.errors.get(site) or f"title '{title}' does not name the upazila"))
        return res
    res["ok"] = True
    res["pages"].append(dict(district_en=d, upazila_en=u, kind="home", url=site, status="ok", title=title))
    host = urlparse(site).netloc.lower()
    menu = dv_menu(home, site)
    sub = host.split(".")[0]

    def page(kind, url):
        c = dv_content(F.get(url))
        res["pages"].append(dict(district_en=d, upazila_en=u, kind=kind, url=url,
                                 status="ok" if c else (F.errors.get(url) or "no content block"),
                                 updated=c["date"] if c else "", title=c["title"] if c else ""))
        if c and dv_save_raw(out, f"{dv_slug(d)}_{sub}_{kind}.txt", url, c) is False:
            res["log"].append(f"{d}/{u}: raw text of '{c['title']}' ({url}) not saved: the page also names people")
        return c

    def fact(level, name, f, url, c, extra=""):
        res["facts"].append(dict(entity_level=level, entity_name_en=name, district_en=d, upazila_en=u, fact=f["fact"],
                                 value=f["value"], unit=f["unit"], basis="as stated", year=f["year"], source_key=key,
                                 source_url=url, notes=dv_redact(f"{extra}label '{f['label']}' value '{f['raw']}'" +
                                                                 (f"; {f['note']}" if f["note"] else "") + f"; {dv_upd(c)}")))

    un = dv_pick(menu, r"ইউনিয়ন\s*(সমূহ|সমুহ|পরিষদ\s*সমূহ|পরিষদসমূহ|তালিকা|এর তালিকা|পরিষদের তালিকা)|ইউনিয়নসমূহ",
                 DV_UNION_MENU_EX, host) or dv_pick(menu, r"ইউনিয়ন", DV_UNION_MENU_EX, host)
    c = dv_content(F.get(un[1])) if un else None
    if c and re.search(DV_UNION_MENU_EX + r"|গ্রাম পুলিশ|চৌকিদার|দফাদার", c["title"]):
        res["log"].append(f"{d}/{u}: menu item '{un[0]}' leads to '{c['title']}', not a union list (not used)")
        res["pages"].append(dict(district_en=d, upazila_en=u, kind="unions", url=un[1], status="not a union list",
                                 updated=c["date"], title=c["title"]))
        un = None
    elif c and dv_lists_persons(c):
        res["log"].append(f"{d}/{u}: union page '{c['title']}' ({un[1]}) also names people (chairmen, secretaries or "
                          f"UDC entrepreneurs); not used, raw text not saved")
        res["pages"].append(dict(district_en=d, upazila_en=u, kind="unions", url=un[1], status="lists persons (not used)",
                                 updated=c["date"], title=c["title"]))
        un = None
    elif un:
        res["pages"].append(dict(district_en=d, upazila_en=u, kind="unions", url=un[1],
                                 status="ok" if c else (F.errors.get(un[1]) or "no content block"),
                                 updated=c["date"] if c else "", title=c["title"] if c else ""))
        if c:
            dv_save_raw(out, f"{dv_slug(d)}_{sub}_unions.txt", un[1], c)
    if un and c:
        rows, stated = dv_union_list(c, div, district=d, upazila=u)
        res["log"] += [f"{d}/{u}: {r['warning']}" for r in rows if "warning" in r]
        rows = [r for r in rows if "warning" not in r and r["upazila_en"] == u]
        res["unions"] = rows
        for r in rows:
            res["areas"].append(dict(level="union", name_bn=r["name_bn"], parent_level="upazila", parent_name_en=u,
                                     parent_name_bn=u_bn, district_en=d, upazila_en=u, code=r["no"],
                                     code_scheme="UNION_NO_IN_UPAZILA" if r["no"] else "", website=r["website"],
                                     source_key=key, source_url=un[1], name_en=r.get("name_en", ""),
                                     notes=f"printed '{r['printed']}'" + (f"; row printed {r['dup']} times" if r.get("dup") else "")
                                     + r.get("flags", "")
                                     + f"; {dv_upd(c)}{dv_en_note(r)}"))
        res["facts"].append(dict(entity_level="upazila", entity_name_en=u, district_en=d, upazila_en=u, fact="union_count",
                                 value=str(len(rows)), unit="count", basis="count of unions listed", source_key=key,
                                 source_url=un[1], notes=f"unions listed on '{c['title']}'; {dv_upd(c)}"))
        if not rows:
            res["log"].append(f"{d}/{u}: no union rows parsed from {un[1]}")
    elif not any(p["kind"] == "unions" for p in res["pages"]):
        res["log"].append(f"{d}/{u}: no union list menu item")
    g = dv_pick(menu, r"নজরে", r"আশ্রয়|পৌরসভা|প্রকল্প|ভূমি|ইউনিয়ন", host)
    if g and (c := page("glance", g[1])):
        for f in dv_facts(c, div=div, own=[u_bn] + [a.lstrip("~") for e, b, _, al in div.districts[d]["upazilas"]
                                                     if e == u for a in al], level="upazila"):
            fact("upazila", u, f, g[1], c)
    poura = {}                                  # name -> area row
    for x, h in menu:
        m = re.fullmatch(r"(?:এক ?নজরে\s*)?([ঀ-৿]+(?: [ঀ-৿]+)?)?\s*পৌরসভা(?:র ওয়েবসাইট| কার্যালয়| পোর্টাল| ওয়েবসাইট)?", x)
        if not m:
            continue
        p_host = urlparse(h).netloc.lower()
        nm = m.group(1)
        if nm and re.search(r"মেয়র|হয়েছে|প্রশাসক|কাউন্সিলর|সচিব|নির্বাচন|উক্ত|^এই|^মোট|শ্রেণ|ম্যাপ|মানচিত্র", nm):
            continue                                     # 'মেয়র নরসিংদী পৌরসভা' (a page about the mayor)
        if re.search(r"wikipedia|facebook|youtube|google\.", p_host):
            continue
        if p_host == host and "/pages/static-pages/" in h:
            c = page("poura", h)
            if not c:
                continue
            how = ""
            if not nm:       # 'এক নজরে ঝালকাঠী পৌরসভা' (page title); '| পৌরসভার নাম | : | গলাচিপা |', '| পৌরসভা | পিরোজপুর। |'
                tm = re.search(r"নজরে\s+([ঀ-৿]+)\s+পৌরসভা", c["title"])
                lm = re.search(r"(?:^|\|)\s*পৌরসভা(?:র নাম)?\s*[|:ঃ\s]+([ঀ-৥ৰ-৿]+)[।\s]*\|", c["text"][:600])
                if tm or lm:
                    nm, how = (tm or lm).group(1), ("; name from the page title" if tm else
                                                    f"; name from the page's row '{dv_nfc(re.sub(r'\s+', ' ', lm.group(0))).strip(' |')}'")
                    if re.search(r"[া-ৌ]{2}", nm):
                        how += "; DOUBT: the printed name has two vowel signs in a row (malformed)"
            if not nm:                                   # 'এক নজরে পৌরসভা': name from the page title / text
                cands = [x for x in re.findall(r"([ঀ-৿]+) পৌরসভা(?![ঀ-৿])", c["text"][:600])
                         if not re.match(r"নজর|এক|একনজর|শ্রে[ণন]ী|উক্ত|এই|প্রথম|মোট|নং|হয়েছে|হয়|করা|গঠিত|মেয়র|ও$|সাথে|সঙ্গে|কর্তৃক|থেকে|হতে|জন্য", x)] if "নজরে" in c["title"] else []
                nm = cands[0] if cands else ""
            if not nm:
                res["log"].append(f"{d}/{u}: pourashava page without a name: {h}")
                continue
            nm = dv_nfc(nm) + " পৌরসভা"
            row = poura.setdefault(nm, dict(level="pourashava", name_bn=nm, parent_level="upazila", parent_name_en=u,
                                            parent_name_bn=u_bn, district_en=d, upazila_en=u, website="", source_key=key,
                                            source_url=h, notes=""))
            row["source_url"] = h
            row["notes"] = f"menu item '{x}' on the {u_bn} upazila portal; {dv_upd(c)}{how}" + row["notes"]
            for f in dv_facts(c, level="pourashava"):
                fact("pourashava", nm, f, h, c, "entity_name_en holds the Bangla name (no English on page); ")
        elif nm and h.startswith("http") and p_host != host and "/pages/" not in h:
            nm = dv_nfc(nm) + " পৌরসভা"
            row = poura.setdefault(nm, dict(level="pourashava", name_bn=nm, parent_level="upazila", parent_name_en=u,
                                            parent_name_bn=u_bn, district_en=d, upazila_en=u, website="", source_key=key,
                                            source_url=site, notes=""))
            row["website"] = row["website"] or dv_site(h)
            row["notes"] += f"; website from menu link '{x}'"
    for row in poura.values():
        row["notes"] = row["notes"].lstrip("; ")
        res["areas"].append(row)
    return res


# ---------------------------------------------------------------------------------------- union portals
DV_UNION_FACTS = {"area_km2", "population", "mouza_count", "village_count", "ward_count", "household_count"}


def dv_collect_union(F, div, u, key, out):
    """One union portal: menu item 'এক নজরে' -> facts. u: dict(district_en, upazila_en, name_bn, no, website, list_url)."""
    row = dict(district_en=u["district_en"], upazila_en=u["upazila_en"], union_no=u["no"], union_bn=u["name_bn"],
               portal=u["website"], list_url=u.get("list_url", ""))
    facts = []
    if not u["website"]:
        return dict(row, status="no portal link found"), facts
    home = F.get(u["website"])
    if not home:
        return dict(row, status=f"portal error: {F.errors.get(u['website'])}"), facts
    title = dv_title(home)
    row["portal_title"] = title
    check = "" if dv_loose(u["name_bn"])[:4] in dv_loose(title) else f"; portal title '{title}' does not repeat the union name"
    host = urlparse(u["website"]).netloc.lower()
    cands = [(x, h) for x, h in dv_menu(home, u["website"])
             if "নজরে" in x and "ভূমি" not in x and "/pages/" in h and urlparse(h).netloc.lower() == host]
    if not cands:
        return dict(row, status="no এক নজরে menu item" + check), facts
    url = cands[0][1]
    c = dv_content(F.get(url))
    if not c or len(c["text"]) < 80:
        return dict(row, url=url, status=("page error: " + F.errors[url]) if url in F.errors else "empty page"), facts
    if dv_save_raw(out, f"{host.rsplit('.gov.bd', 1)[0].replace('.', '_')}_glance.txt", url, c) is False:  # unique per host
        row["raw"] = "not saved: the page also names people"
    got = dv_facts(c, wanted=DV_UNION_FACTS, level="union")
    for f in got:
        facts.append(dict(entity_level="union", entity_name_en="", district_en=u["district_en"], upazila_en=u["upazila_en"],
                          code=u["no"], fact=f["fact"], value=f["value"], unit=f["unit"], basis="as stated", year=f["year"],
                          source_key=key, source_url=url,
                          notes=dv_redact(f"union {u['name_bn']}" + (f" (no. {u['no']})" if u["no"] else "") +
                                          f"; label '{f['label']}' value '{f['raw']}'" + (f"; {f['note']}" if f["note"] else "")
                                          + check + f"; {dv_upd(c)}")))
    return dict(row, url=url, status="ok" + check, updated=c["date"], title=c["title"], facts=len(got)), facts


def dv_parallel(fn, items, workers=6):
    with _dv_cf.ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(fn, items))


# ---------------------------------------------------------------------------------------- runners
DV_YEAR = "2026"  # collection campaign in the source keys (Rajshahi keys carry 2026 too)
DV_KINDS = {  # kind: (Rajshahi folder, folder/key pattern for other divisions)
    "district_portal_main": ("rajshahi_district_portal", "{div}_district_portal", "{DIV}_DC_PORTAL_{Y}"),
    "district_portals": ("division_district_portals", "division_district_portals_{div}", "{CODE}DIV_DISTRICT_PORTALS_{Y}"),
    "upazila_portals": ("rajshahi_upazila_portals", "{div}_upazila_portals", "{DIV}_UPAZILA_PORTALS_{Y}"),
    "union_portals": ("rajshahi_union_portals", "{div}_union_portals", "{DIV}_UNION_PORTALS_{Y}"),
    "divisional_portal": ("rajshahi_divisional_portal", "{div}_divisional_portal", "{CODE}DIV_PORTAL_{Y}"),
}


def dv_names(kind, div):
    _, folder, key = DV_KINDS[kind]
    f = dict(div=div.key, DIV=div.key.upper(), CODE=div.code.upper(), Y=DV_YEAR)
    return folder.format(**f), key.format(**f)


def dv_template(kind, div, key, urls):
    head = div.head
    hb = div.districts[head]["name_bn"]
    others = [d for d in div.districts if d != head]
    t = {
        "district_portal_main": (
            f"{head} District Administration portal — upazila/union list, pourashavas, district at-a-glance",
            f"Office of the Deputy Commissioner, {head} (Government of Bangladesh, a2i National Portal)",
            f"{hb} জেলা প্রশাসন, জাতীয় তথ্য বাতায়ন ({div.districts[head]['host']})"),
        "district_portals": (
            f"District administration portals — {', '.join(others)}",
            "Deputy Commissioner's offices, Government of Bangladesh (a2i National Portal)",
            f"জেলা প্রশাসন, {div.name_bn} বিভাগ — জাতীয় তথ্য বাতায়ন (<district>.gov.bd)"),
        "upazila_portals": (
            f"Upazila Administration portals of {div.name_en} Division — union lists, এক নজরে, pourashava pages",
            f"Upazila Nirbahi Officers' offices, {div.name_en} Division (Government of Bangladesh, a2i National Portal)",
            f"উপজেলা প্রশাসন, {div.name_bn} বিভাগ — জাতীয় তথ্য বাতায়ন (<upazila>.<district>.gov.bd)"),
        "union_portals": (
            f"Union Parishad portals of {div.name_en} Division — এক নজরে (at-a-glance) pages",
            f"Union Parishads of {div.name_en} Division (Government of Bangladesh, a2i National Portal)",
            f"ইউনিয়ন পরিষদ পোর্টাল, {div.name_bn} বিভাগ — জাতীয় তথ্য বাতায়ন (<union>.<district>.gov.bd)"),
        "divisional_portal": (
            f"{div.name_en} Divisional Commissioner portal ({div.cfg['portal']})",
            f"Office of the Divisional Commissioner, {div.name_en}",
            f"Office of the Divisional Commissioner, {div.name_en} ({div.cfg['portal']}), Bangladesh National Portal"),
    }[kind]
    return {"key": key, "name": t[0], "organization": t[1], "source_type": "government_portal", "trust_level": 4,
            "division": div.key, "kind": kind, "urls": urls, "publication_date": None, "license": None,
            "license_url": None, "attribution": t[2],
            "notes": "Collected by the generic division mode of the a2i portal collectors (pages found through the "
                     "portals' menus, names and figures parsed from the pages). No licence stated; only facts (names, "
                     "counts, figures) are extracted. English district/upazila names are the project's keys, not printed."}


def dv_pages_csv(out, pages, cols=("district_en", "upazila_en", "kind", "url", "status", "updated", "title")):
    seen, rows = set(), []
    for p in pages:
        k = (p.get("kind"), p.get("url"))
        if k not in seen:
            seen.add(k)
            rows.append(p)
    dv_write_csv(os.path.join(out, "raw", "pages.csv"), list(cols), rows)


def dv_save_district_raw(out, r, prefix):
    if r.get("glance"):
        dv_save_raw(out, f"{prefix}_glance.txt", r["glance"][0], r["glance"][1])
    if r.get("union_page"):
        dv_save_raw(out, f"{prefix}_unions.txt", r["union_url"], r["union_page"])


def dv_run(kind, division, out=None, cache=None, here="."):
    div = DvDivision(division)
    folder, key = dv_names(kind, div)
    out = os.path.abspath(out or os.path.join(os.path.dirname(os.path.abspath(here)), folder))
    os.makedirs(os.path.join(out, "raw"), exist_ok=True)
    F = DvFetcher(cache)
    logs = []
    log = lambda m: (logs.append(m), print("WARNING:", m, file=sys.stderr))
    areas, facts, pages, urls = [], [], [], []
    t0 = time.time()
    if kind in ("district_portal_main", "district_portals"):
        ds = [div.head] if kind == "district_portal_main" else [d for d in div.districts if d != div.head]
        for d in ds:
            r = dv_collect_district(F, div, d, key, log)
            areas += r["areas"]
            facts += r["facts"]
            pages += r["pages"]
            urls += [p["url"] for p in r["pages"] if p["status"] == "ok"]
            dv_save_district_raw(out, r, dv_slug(d))
            for p in r["pages"]:
                if p["status"] == "ok" and p["kind"] in ("upazilas", "pourashavas"):
                    c = dv_content(F.get(p["url"]))
                    dv_save_raw(out, f"{dv_slug(d)}_{p['kind']}.txt", p["url"], c)
        nat = dv_national(F, div)                 # cross-check the parent upazila of each listed union
        if nat:
            urls.append(nat["url"])
            for a in areas:
                n = dv_registry_doubt(nat, a["district_en"], a.get("upazila_en"), a["name_bn"]) if a["level"] == "union" else ""
                if n:
                    a["notes"] += "; " + n
                if a["level"] == "union" and not a["website"]:
                    dv_registry_fill(a, nat)
        dv_pages_csv(out, pages)
    elif kind == "upazila_portals":
        items = [(d, u) for d in div.districts for u, *_ in div.districts[d]["upazilas"]]
        rs = dv_parallel(lambda x: dv_collect_upazila(F, div, x[0], x[1], key, out), items, 6)
        for r in rs:
            areas += r["areas"]
            facts += r["facts"]
            pages += r["pages"]
            for m in r["log"]:
                log(m)
            urls += [r["site"]] if r["ok"] else []
        nat = dv_national(F, div) if any(a["level"] == "union" and not a["website"] for a in areas) else None
        if nat:                                   # union portal addresses the upazila pages do not link
            if any([dv_registry_fill(a, nat) for a in areas if a["level"] == "union" and not a["website"]]):
                urls.append(nat["url"])
        dv_pages_csv(out, pages)
    elif kind == "union_portals":
        unions = []
        for d in div.districts:
            r = dv_collect_district(F, div, d, key, log)
            urls += [r["union_url"]] if r["union_url"] else []
            for u in r["unions"]:
                unions.append(dict(u, list_url=r["union_url"]))
        # national portal list of union portals: links for unions the DC lists do not link, and the union list itself
        # for upazilas the DC portals do not list at all
        nat = dv_national(F, div)
        if nat:
            urls.append(nat["url"])
            have = {(u["district_en"], u["upazila_en"]) for u in unions}
            sites = {}
            for x in nat["unions"]:
                sites.setdefault((x["district_en"], x["upazila_en"], dv_loose(x["name_bn"])), x["website"])
                if x["geo_name_bn"]:
                    sites.setdefault((x["district_en"], x["upazila_en"], dv_loose(x["geo_name_bn"])), x["website"])
            for u in unions:
                w = sites.get((u["district_en"], u["upazila_en"], dv_loose(u["name_bn"])))
                if w and not u["website"]:
                    u["website"], u["site_from"] = w, nat["url"]
                n = dv_registry_doubt(nat, u["district_en"], u["upazila_en"], u["name_bn"])
                if n:
                    u["flags"] = u.get("flags", "") + "; " + n
            # an incomplete DC list (fewer unions in the district than the national list): an upazila for which it
            # names fewer unions than the national list is taken from the national list; a DC row that the national
            # list places in such an upazila (and names there) is dropped, so it is not counted twice
            nc, dc = {}, {}
            for x in nat["unions"]:
                nc[(x["district_en"], x["upazila_en"])] = nc.get((x["district_en"], x["upazila_en"]), 0) + 1
            names = {(x["district_en"], x["upazila_en"], k) for x in nat["unions"]
                     for k in (dv_loose(x["name_bn"]), dv_loose(x["geo_name_bn"])) if k}
            # an upazila the DC lists do not name at all is taken from the national list as a whole (below); a DC row
            # that the national list places there (and not in the DC row's upazila) is dropped first (জুগলী, printed
            # under Tarakanda on mymensingh.gov.bd, is a Haluaghat union on the national list)
            absent = {k for k in nc if k not in have}
            keep = []
            for u in unions:
                k = (u["district_en"], u["upazila_en"])
                moved = [w for w in sorted(absent) if w[0] == k[0] and (w[0], w[1], dv_loose(u["name_bn"])) in names
                         and (k[0], k[1], dv_loose(u["name_bn"])) not in names]
                if moved:
                    log(f"{k[0]}/{k[1]}: '{u['printed']}' dropped: the national list has it under {moved[0][1]}, which "
                        f"the DC list does not name and which is taken from the national list")
                else:
                    keep.append(u)
            unions = keep
            for u in unions:
                dc[(u["district_en"], u["upazila_en"])] = dc.get((u["district_en"], u["upazila_en"]), 0) + 1
            short = {}
            # an upazila the national list gives no unions (a new one, e.g. Madhyanagar, split from Dharmapasha in
            # Sunamganj): the national list still has its unions under the old upazila, so that upazila's shortfall up to
            # the new one's DC count is not a gap in the DC list
            empty = {k: v for k, v in dc.items() if not nc.get(k)}
            for d in div.districts:
                if sum(v for k, v in dc.items() if k[0] == d) < sum(v for k, v in nc.items() if k[0] == d):
                    spare = sum(v for k, v in empty.items() if k[0] == d)
                    new = ", ".join(e[1] for e in empty if e[0] == d)
                    for k, v in sorted(((k, v) for k, v in dc.items() if k[0] == d and v < nc.get(k, 0)),
                                       key=lambda x: x[1] - nc[x[0]]):           # largest shortfall first
                        if nc[k] - v > spare:
                            short[k] = v
                        else:
                            log(f"{k[0]}/{k[1]}: DC list names {v} unions, the national list {nc[k]}; DC list kept (the "
                                f"national list gives no unions for {new}, which the DC list names with {spare})")
                            spare -= nc[k] - v
            if short:
                keep, said = [], set()
                for u in unions:
                    k = (u["district_en"], u["upazila_en"])
                    moved = [w for w in short if w[0] == k[0] and w != k and (w[0], w[1], dv_loose(u["name_bn"])) in names
                             and (k[0], k[1], dv_loose(u["name_bn"])) not in names]
                    if k in short:
                        if k not in said:
                            said.add(k)
                            log(f"{k[0]}/{k[1]}: DC list names {short[k]} unions, the national list {nc[k]}; national list used")
                    elif moved:
                        log(f"{k[0]}/{k[1]}: '{u['printed']}' dropped: the national list has it under {moved[0][1]}, "
                            f"which is taken from the national list")
                    else:
                        keep.append(u)
                unions = keep
                have = {(u["district_en"], u["upazila_en"]) for u in unions}
            for x in nat["unions"]:
                if (x["district_en"], x["upazila_en"]) not in have:
                    unions.append(dict(x, upazila_printed=div.upz_bn(x["district_en"], x["upazila_en"]),
                                       list_url=nat["url"], from_national=True,
                                       dc_count=short.get((x["district_en"], x["upazila_en"]), 0)))
        missing = sorted({(u["district_en"], u["upazila_en"]) for u in unions if not u["website"]})
        if missing:   # look for the portal links on the upazila portals' union pages
            rs = dv_parallel(lambda x: dv_collect_upazila(F, div, x[0], x[1], key, None), missing, 6)
            for (d, up), r in zip(missing, rs):
                sites = {dv_loose(x["name_bn"]): x["website"] for x in r["unions"] if x["website"]}
                for u in unions:
                    if u["district_en"] == d and u["upazila_en"] == up and not u["website"]:
                        w = sites.get(dv_loose(u["name_bn"]))
                        if w:
                            u["website"], u["site_from"] = w, next(p["url"] for p in r["pages"] if p["kind"] == "unions")
        rs = dv_parallel(lambda u: dv_collect_union(F, div, u, key, out), unions, 8)
        cov = []
        for u, (row, fs) in zip(unions, rs):
            if u.get("site_from"):
                row["portal_link_from"] = u["site_from"]
            cov.append(row)
            facts += fs
            # one area row per union in the DC portal list; website only when the portal answered
            st = row["status"]
            reached = st.startswith(("ok", "no এক নজরে", "empty page")) and "Site is not available" not in st
            note = (f"listed as '{u['printed']}' on the national portal list of union portals (the DC portal lists "
                    + (f"only {u['dc_count']} of them" if u.get("dc_count") else "no unions") + " for this upazila)"
                    if u.get("from_national") else f"printed '{u['printed']}' on the district union list"
                    + u.get("flags", ""))
            if u["website"] and reached:
                note += "; portal reached" + (f" (title '{row.get('portal_title', '')}')" if row.get("portal_title") else "")
                if u.get("site_from"):
                    note += f"; portal link from {u['site_from']}"
            elif u["website"] and u.get("site_from") and st.startswith("portal error"):
                note += f"; portal {u['website']} (link from {u['site_from']}) not usable ({st.split(';')[0]})"
            elif u["website"]:
                note += f"; portal {u['website']} not usable ({st.split(';')[0]})"
            else:
                note += "; no portal link found on the district or upazila portal"
            if "does not repeat" in st:
                note += "; DOUBT: " + st.split("; ", 1)[1]
            areas.append(dict(level="union", name_bn=u["name_bn"], parent_level="upazila", parent_name_en=u["upazila_en"],
                              parent_name_bn=u["upazila_printed"], district_en=u["district_en"],
                              upazila_en=u["upazila_en"], code=u["no"],
                              code_scheme="UNION_NO_IN_UPAZILA" if u["no"] else "",
                              website=u["website"] if reached else "", source_key=key,
                              source_url=row.get("url") or u.get("list_url", ""), name_en=u.get("name_en", ""),
                              notes=note + (f"; English name as printed on the district list" if u.get("name_en") and
                                            not u.get("from_national") else "; English name not printed")))
        dv_write_csv(os.path.join(out, "raw", "coverage.csv"),
                     ["district_en", "upazila_en", "union_no", "union_bn", "portal", "portal_link_from", "portal_title",
                      "list_url", "url", "status", "updated", "title", "facts", "raw"], cov)
        pages = cov
    elif kind == "divisional_portal":
        r = dv_collect_division(F, div, key, log)
        areas, facts, pages = r["areas"], r["facts"], r["pages"]
        urls = [p["url"] for p in pages if p["status"] == "ok"]
        for k, (u, c) in r["raw"].items():
            dv_save_raw(out, f"{k}.txt", u, c)
        if r.get("national"):
            dv_national_csv(out, r["national"])
        dv_write_csv(os.path.join(out, "raw", "pages.csv"), ["kind", "url", "status", "updated", "title"], pages)
    else:
        raise SystemExit(f"unknown kind {kind}")
    dv_write_csv(os.path.join(out, "areas.csv"), DV_AREAS_H, areas)
    dv_write_csv(os.path.join(out, "facts.csv"), DV_FACTS_H, facts)
    if logs:
        with open(os.path.join(out, "raw", "warnings.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(logs) + "\n")
    dv_manifest(out, dv_template(kind, div, key, list(dict.fromkeys(urls))))
    lv = {}
    for a in areas:
        lv[a["level"]] = lv.get(a["level"], 0) + 1
    print(f"{kind} {division} -> {out}: areas {lv}, facts {len(facts)}, pages {len(pages)}, "
          f"requests {F.requests}, failed {len(F.errors)}, {time.time() - t0:.0f}s")
    return out



def main_rajshahi(args):
    global CACHE
    CACHE = args.cache
    areas, facts = [], []
    area = lambda **k: areas.append(dict(source_key=KEY, **k))
    fact = lambda **k: facts.append(dict(source_key=KEY, **k))

    area(level="district", name_en="Rajshahi", name_bn="রাজশাহী", parent_level="division", parent_name_en="Rajshahi",
         parent_name_bn="রাজশাহী", district_en="Rajshahi", website=BASE + "/", source_url=BASE + "/")

    # --- upazila parishad list ---
    c = content(get(P_UPZ)); save_raw("upazila_parishad_list.txt", P_UPZ, c)
    for cells, _ in table_rows(c["html"]):
        if len(cells) >= 4 and nfc(cells[2]) in UPZ_BN:
            en = UPZ_BN[nfc(cells[2])]
            sub = [s for s, e, _ in UPAZILAS if e == en][0]
            area(level="upazila", name_en="", name_bn=nfc(cells[2]), parent_level="district", parent_name_en="Rajshahi",
                 parent_name_bn="রাজশাহী", district_en="Rajshahi", upazila_en=en, website=f"https://{sub}.rajshahi.gov.bd/",
                 source_url=P_UPZ, notes=f"listed as '{nfc(cells[3])}'; page updated {c['date']}; name_en is the project's key, not printed")

    # --- union list ---
    c = content(get(P_UNIONS)); save_raw("upazila_union_list.txt", P_UNIONS, c)
    m = re.search(r"মোট উপজেলাঃ\s*(\S+)", c["text"]); fact(entity_level="district", entity_name_en="Rajshahi", district_en="Rajshahi",
        fact="upazila_count", value=asc(m.group(1)), unit="count", basis="as stated", source_url=P_UNIONS,
        notes=f"'মোট উপজেলাঃ {m.group(1)} টি'; page updated {c['date']}")
    m = re.search(r"মোট ইউনিয়নঃ\s*(\S+)", c["text"]); total = int(asc(m.group(1)))
    fact(entity_level="district", entity_name_en="Rajshahi", district_en="Rajshahi", fact="union_count", value=str(total),
         unit="count", basis="as stated", source_url=P_UNIONS, notes=f"'মোট ইউনিয়নঃ {m.group(1)} টি'; page updated {c['date']}")
    upz, listed, stated = None, {}, {}
    for cells, tr in table_rows(c["html"]):
        cells = [x for x in cells if x.strip()]
        if len(cells) >= 3 and nfc(cells[0]) in UPZ_BN:
            upz = UPZ_BN[nfc(cells[0])]
            stated[upz] = (asc(cells[1]).split()[0], nfc(cells[0]))
            cells = cells[2:]
        m = re.match(r"^([০-৯]+)\s*নং\s*(.+)$", nfc(cells[0])) if cells else None
        if not (m and upz):
            continue
        hrefs = [h for h in re.findall(r'href="([^"]*)"', tr) if "up." in h or "up" in urlparse(clean_url(h)).netloc.split(".")[0]]
        site = clean_url(hrefs[-1]) if hrefs else ""
        listed[upz] = listed.get(upz, 0) + 1
        area(level="union", name_en="", name_bn=m.group(2).strip(), parent_level="upazila", parent_name_en=upz,
             parent_name_bn=stated[upz][1], district_en="Rajshahi", upazila_en=upz, code=asc(m.group(1)),
             code_scheme="UNION_NO_IN_UPAZILA", website=site, source_url=P_UNIONS,
             notes=f"printed '{nfc(cells[0])}'; page updated {c['date']}; English name not printed")
    for upz, (n, bn) in stated.items():
        fact(entity_level="upazila", entity_name_en=upz, district_en="Rajshahi", upazila_en=upz, fact="union_count", value=n,
             unit="count", basis="as stated", source_url=P_UNIONS,
             notes=f"stated '{n} টি', rows listed {listed.get(upz, 0)}; page updated {c['date']}")
    assert sum(listed.values()) == total, (listed, total)

    # --- pourashava list ---
    c = content(get(P_POURA)); save_raw("pourashava_list.txt", P_POURA, c)
    n = 0
    for cells, _ in table_rows(c["html"]):
        cells = [x for x in cells if x.strip()]
        if len(cells) >= 4 and nfc(cells[2]) in UPZ_BN and "পৌরসভা" in cells[3]:
            n += 1
            upz = UPZ_BN[nfc(cells[2])]
            note = f"serial {asc(cells[0])}; page updated {c['date']}"
            if nfc(cells[3]) in (nfc("মুন্ডুমালা পৌরসভা"), nfc("কাকনহাট পৌরসভা")):
                note += ("; DOUBT: this page puts মুন্ডুমালা under গোদাগাড়ী and কাকনহাট under তানোর, BBS Census 2022 "
                         "(geocodes 50-81-34-55 Kakanhat/Godagari, 50-81-94-70 Mundumala/Tanore) puts them the other way round")
            area(level="pourashava", name_en="", name_bn=nfc(cells[3]), parent_level="upazila", parent_name_en=upz,
                 parent_name_bn=nfc(cells[2]), district_en="Rajshahi", upazila_en=upz, source_url=P_POURA, notes=note)
    fact(entity_level="district", entity_name_en="Rajshahi", district_en="Rajshahi", fact="pourashava_count", value=str(n),
         unit="count", basis="rows listed", source_url=P_POURA, notes=f"14 rows in 'রাজশাহী জেলার পৌরসভার তালিকা'; page updated {c['date']}")
    for h, x in links(get(BASE + "/"), BASE + "/"):
        if "পৌরসভা" in x and "static-pages" not in h and h.startswith("http") and clean_url(h) != BASE + "/":
            for a in areas:
                if a["level"] == "pourashava" and a["name_bn"] == nfc(x):
                    a["website"] = clean_url(h)

    # --- এক নজরে জেলা ---
    c = content(get(P_GLANCE)); save_raw("district_at_a_glance.txt", P_GLANCE, c)
    flat = re.sub(r"\s+", " ", c["text"])
    for f, v, unit, basis, year, quote, note in GLANCE:
        if re.sub(r"\s+", " ", nfc(quote)) not in flat:
            print(f"WARNING: quote no longer on page: {quote}", file=sys.stderr)
            continue
        fact(entity_level="district", entity_name_en="Rajshahi", district_en="Rajshahi", fact=f, value=v, unit=unit,
             basis=basis, year=year, source_url=P_GLANCE,
             notes=f"'{quote}'" + (f"; {note}" if note else "") + f"; page updated {c['date']}")

    write_csv(os.path.join(HERE, "areas.csv"), AREAS_H, areas)
    write_csv(os.path.join(HERE, "facts.csv"), FACTS_H, facts)
    update_manifest()
    print(f"areas {len(areas)}, facts {len(facts)}; unions {sum(listed.values())} {listed}")


KIND = "district_portal_main"


def main():
    global HERE
    ap = argparse.ArgumentParser(description="Head district DC portal collector")
    ap.add_argument("--division", default="rajshahi", help="division to collect (default rajshahi)")
    ap.add_argument("--out", help="output folder (default: this folder for rajshahi, the division's own folder otherwise)")
    ap.add_argument("--cache", default=None, help="reuse/keep downloaded pages in this folder")
    a = ap.parse_args()
    if a.division != "rajshahi":
        dv_run(KIND, a.division, a.out, a.cache, HERE)
        return
    if a.out and os.path.abspath(a.out) != HERE:
        out = os.path.abspath(a.out)
        os.makedirs(out, exist_ok=True)
        if not os.path.exists(os.path.join(out, "SOURCE.json")):
            with open(os.path.join(HERE, "SOURCE.json"), encoding="utf-8") as f, \
                    open(os.path.join(out, "SOURCE.json"), "w", encoding="utf-8") as g:
                g.write(f.read())
        HERE = out
    main_rajshahi(a)


if __name__ == "__main__":
    main()
