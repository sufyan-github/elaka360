#!/usr/bin/env python3
"""Rajshahi District upazila portals (<upazila>.rajshahi.gov.bd): union lists, এক নজরে facts, pourashava এক নজরে pages.

Usage: python3 -I fetch.py [--cache DIR]
Writes areas.csv, facts.csv, raw/*.txt (text of each page used) and refreshes SOURCE.json file hashes.
Union lists are parsed from the pages. Figures are hand-transcribed in F (below) together with the exact printed
text; every run checks that text is still on the live page and drops (with a warning) any figure whose text is gone.
Phone numbers and e-mail addresses are redacted from raw/*.txt.

Other divisions: python3 -I fetch.py --division <rangpur|...> [--out DIR] [--cache DIR]
  runs the generic division mode (block 'Division mode' below) and writes to the division's own folder
  (default data/sources/<division>_upazila_portals); the Rajshahi outputs in this folder are never touched. With no arguments
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

KEY = "RAJSHAHI_UPAZILA_PORTALS_2026"
SP = "/pages/static-pages/"
# (subdomain, kind, page id, pourashava Bangla name, pourashava English key)
PAGES = [
    ("bagha", "glance", "697f803135ce18e1c06b7528", None, None),
    ("bagha", "unions", "697fc1d835ce18e1c06ce18c", None, None),     # মানচিত্রে বাঘা: area, counts and the union list
    ("bagha", "poura", "697ff45635ce18e1c06de1e6", "বাঘা পৌরসভা", "Bagha"),
    ("bagmara", "glance", "at-a-glance-8238b9-697f805635ce18e1c06b8582", None, None),
    ("bagmara", "unions", "697fd8b835ce18e1c06d5dff", None, None),
    ("bagmara", "poura", "697fdce135ce18e1c06d893e", "তাহেরপুর পৌরসভা", "Taherpur"),
    ("charghat", "glance", "697fbb3e35ce18e1c06cd291", None, None),
    ("charghat", "unions", "697ff43135ce18e1c06dd0a3", None, None),
    ("charghat", "poura", "697fe56f35ce18e1c06dae25", "চারঘাট পৌরসভা", "Charghat"),
    ("durgapur", "glance", "697ffd4f35ce18e1c06df206", None, None),
    ("durgapur", "unions", "697ffd4f35ce18e1c06df22d", None, None),
    ("durgapur", "poura", "697ffd5135ce18e1c06df33b", "দুর্গাপুর পৌরসভা", "Durgapur"),
    ("godagari", "glance", "697f803535ce18e1c06b772a", None, None),
    ("godagari", "geo", "697f99fa35ce18e1c06c2174", None, None),
    ("godagari", "unions", "697faa7835ce18e1c06c8c25", None, None),
    ("godagari", "poura", "697fbb4535ce18e1c06cd676", "গোদাগাড়ী পৌরসভা", "Godagari"),
    ("godagari", "poura", "697fc88f35ce18e1c06d10a2", "কাকনহাট পৌরসভা", "Kakanhat"),
    ("mohonpur", "glance", "697f79de35ce18e1c06b62e3", None, None),
    ("mohonpur", "unions", "697f79db35ce18e1c06b6197", None, None),
    ("mohonpur", "poura", "697f93d335ce18e1c06bf218", "কেশরহাট পৌরসভা", "Kesharhat"),
    ("paba", "glance", "697f801d35ce18e1c06b6bfd", None, None),
    ("paba", "unions", "697f802d35ce18e1c06b738d", None, None),
    ("paba", "poura", "697fbb5735ce18e1c06cddcf", "কাটাখালী পৌরসভা", "Katakhali"),
    ("puthia", "glance", "697fbb2835ce18e1c06cc87b", None, None),
    ("puthia", "unions", "697f6dc135ce18e1c06b10a0", None, None),
    ("puthia", "poura", "697faa5335ce18e1c06c7ae1", "পুঠিয়া পৌরসভা", "Puthia"),
    ("tanore", "glance", "697fb33c35ce18e1c06cb43b", None, None),
    ("tanore", "unions", "697f93bf35ce18e1c06be895", None, None),
    ("tanore", "poura", "697f93ff35ce18e1c06c0642", "তানোর পৌরসভা", "Tanore"),
    ("tanore", "poura", "697fe57235ce18e1c06daf84", "মুন্ডুমালা পৌরসভা", "Mundumala"),
]

C11 = "census 2011 (as quoted by the page)"
# Hand-transcribed figures. page id -> [(entity_level, entity_en, fact, value, unit, basis, year, quote, note)].
# entity_en None = the upazila (or the page's pourashava). Each quote is checked against the live page text
# (whitespace and table bars ignored); a quote that has vanished produces a warning and no row.
F = {
    "697f803135ce18e1c06b7528": [
        ("upazila", None, "area_km2", "185.16", "km2", "as stated", "", "আয়তন | ১৮৫.১৬বর্গ কিঃ মিঃ", "the map page of the same portal says 184.25"),
        ("upazila", None, "population", "184183", "persons", C11, "2011", "১৮৪১৮৩ (২০১১ সনের আদম শুমারী অনুযায়ী)", ""),
        ("upazila", None, "households", "46711", "households", C11, "2011", "৪৬৭১১ টি (২০১১ সনের আদম শুমারী অনুযায়ী)", ""),
        ("upazila", None, "pourashava_count", "2", "count", "as stated", "", "পৌরসভা | ০২ টি (বাঘা, আড়ানী)", "Bagha, Arani"),
        ("upazila", None, "union_count", "7", "count", "as stated", "", "ইউনিয়ন | ০৭ টি", ""),
        ("upazila", None, "mouza_count", "99", "count", "as stated", "", "মৌজা | ৯৯ টি", ""),
        ("upazila", None, "village_count", "126", "count", "as stated", "", "গ্রামের সংখ্যা | ১২৬ টি", ""),
        ("upazila", None, "established", "1983-09-14", "date", "as stated", "1983", "উপজেলা প্রতিষ্ঠার তারিখ | ১৪ সেপ্টেম্বর ১৯৮৩", "thana 1983-03-23"),
    ],
    "697fc1d835ce18e1c06ce18c": [
        ("upazila", None, "area_km2", "184.25", "km2", "as stated", "", "আয়তন: ১৮৪.২৫ বর্গ কিমি", ""),
        ("upazila", None, "union_count", "7", "count", "as stated", "", "পৌরসভা ০২টি, ইউনিয়ন ০৭টি, মৌজা ৯৯ টি, গ্রামের সংখ্যা ১২৬ টি", "7 unions listed incl. চকরাজাপুর"),
    ],
    "697ff45635ce18e1c06de1e6": [
        ("pourashava", None, "established", "1999-06-24", "date", "as stated", "1999", "পৌরসভা প্রতিষ্ঠা | ২৪ শে জুন, ১৯৯৯ ইং", ""),
        ("pourashava", None, "class", "ক", "class", "as stated", "2017", "“ক” শ্রেণী", "খ on 2011-01-27, ক on 2017-07-02"),
        ("pourashava", None, "ward_count", "9", "count", "as stated", "", "ওয়ার্ডের সংখ্যা | ০৯ (নয়) টি", "the portal's older 'ওয়ার্ড সমূহ' page (2018-07-09) lists 10 ward rows"),
        ("pourashava", None, "area_km2", "15.78", "km2", "as stated", "2017", "আয়তন | ১৫.৭৮ বর্গ কি.মি.", "area enlarged for the 2017-12-28 election"),
        ("pourashava", None, "mouza_count", "17", "count", "as stated", "", "মৌজার সংখ্যা | ১৭ (সতের) টি", ""),
        ("pourashava", None, "mahalla_count", "20", "count", "as stated", "", "মহল্লার সংখ্যা | ২০ (বিশ) টি", ""),
        ("pourashava", None, "population", "39288", "persons", "census (year not stated)", "", "লোকসংখ্যা (আদমগুমারী অনুযায়ী) | ৩৯,২৮৮ জন", "same figure repeated as the pourashava's own count dated 2023-02-13; equals the BBS 2022 C-01 enumerated count (39,288)"),
    ],
    "at-a-glance-8238b9-697f805635ce18e1c06b8582": [
        ("upazila", None, "area_km2", "366.30", "km2", "as stated", "", "আয়তন ঃ ৩৬৬.৩০ বর্গ কিলোমিটার", ""),
        ("upazila", None, "mouza_count", "292", "count", "as stated", "", "মোট মৌজা ঃ ২৯২টি", ""),
        ("upazila", None, "village_count", "369", "count", "as stated", "", "মোট গ্র্রাম ঃ ৩৬৯টি", ""),
        ("upazila", None, "union_count", "16", "count", "as stated", "", "মোট ইউনিয়ন ঃ ১৬টি", ""),
        ("upazila", None, "pourashava_count", "2", "count", "as stated", "", "মোট পৌরসভা ঃ ০২টি (তাহেরপুর ও ভবানীগঞ্জ)", "Taherpur, Bhabaniganj"),
        ("upazila", None, "population", "352969", "persons", C11, "2011", "মোট জনসংখ্যা ঃ ৩৫২৯৬৯ (২০১১ আদমশুমারী অনুযায়ী)", ""),
    ],
    "697fdce135ce18e1c06d893e": [
        ("pourashava", None, "established", "1998-12-01", "date", "as stated", "1998", "০১ ডিসেম্বর ১৯৯৮ তারিখে শহর এলাকা", "declared by gazette SRO 266-আইন/98; 9 wards by gazette of 13.05.1999"),
        ("pourashava", None, "ward_count", "9", "count", "as stated", "", "ওযার্ড সমূহ ঃ ০৯ টি", ""),
    ],
    "697fbb3e35ce18e1c06cd291": [
        ("upazila", None, "area_km2", "164.52", "km2", "as stated", "", "আয়তন | ১৬৪.৫২ বর্গ কিঃমিঃ", ""),
        ("upazila", None, "population", "183921", "persons", C11, "2011", "মোট | ৯৪,৯৮৬ জন | ৮৮,৯৩৫ জন | ১,৮৩,৯২১ জন", "table 'জনসংখ্যা (২০১১ সালের আদম শুমারী অনুযায়ী)'"),
        ("union", "Yusufpur", "population", "29750", "persons", C11, "2011", "ইউসুফপুর | ১৫,২২৮ জন | ১৪,৫২২ জন | ২৯,৭৫০ জন", "page name ইউসুফপুর; English key from BBS 2022"),
        ("union", "Shalua", "population", "26167", "persons", C11, "2011", "শলুয়া | ১৩,৪৫৫ জন | ১২,৭১২ জন | ২৬,১৬৭ জন", "page name শলুয়া"),
        ("union", "Sardah", "population", "17448", "persons", C11, "2011", "সরদহ | ৮,৮১৩ জন | ৮,৬৩৫ জন | ১৭,৪৪৮ জন", "page name সরদহ"),
        ("union", "Nimpara", "population", "31278", "persons", C11, "2011", "নিমপাড়া | ১৬,০৬৪ জন | ১৫,২১৪ জন | ৩১,২৭৮ জন", "page name নিমপাড়া"),
        ("union", "Charghat", "population", "18925", "persons", C11, "2011", "চারঘাট | ৯,৭০৭ জন | ৯,২১৮ জন | ১৮,৯২৫ জন", "page name চারঘাট (union)"),
        ("union", "Bhaya Lakkhipur", "population", "25541", "persons", C11, "2011", "ভায়ালক্ষিপুর | ১৩,৩৭৩ জন | ১২,১৬৮ জন | ২৫,৫৪১ জন", "page name ভায়ালক্ষিপুর"),
        ("pourashava", "Charghat", "population", "34812", "persons", C11, "2011", "চারঘাট পৌরসভা | ১৮,৩৪৬ জন | ১৬,৪৬৬ জন | ৩৪,৮১২ জন", "চারঘাট পৌরসভা"),
        ("upazila", None, "mouza_count", "93", "count", "as stated", "", "মোট মৌজা | ৯৩টি", ""),
        ("pourashava", "Charghat", "mouza_count", "10", "count", "as stated", "", "পৌরসভার মৌজার সংখ্যা | ১০টি", "চারঘাট পৌরসভা"),
    ],
    "697fe56f35ce18e1c06dae25": [
        ("pourashava", None, "established", "1998", "year", "as stated", "1998", "প্রতিষ্ঠার: 1998", "page text is a garbled machine translation"),
        ("pourashava", None, "class", "খ", "class", "as stated (garbled)", "2011", "\" বি\" বিষয়শ্রেণীতেঅন্তর্ভুক্ত• প্রতিষ্ঠার: 2011", "page: 'সি' (গ) from 1998, 'বি' (খ) from 2011"),
        ("pourashava", None, "area_km2", "18.73", "km2", "as stated", "", "এলাকা: 18,73 SQKM/4629 একর", "printed with a decimal comma"),
        ("pourashava", None, "population", "38409", "persons", "as stated (year not stated)", "", "মোটজনসংখ্যা: 38.409", "printed '38.409' (dot as thousands separator); male 19860 + female 18549 = 38409"),
        ("pourashava", None, "ward_count", "9", "count", "as stated (garbled)", "", "কোন.09: ওয়ার্ড", "garbled 'No. 09: ward'"),
    ],
    "697ffd4f35ce18e1c06df206": [
        ("upazila", None, "area_km2", "195.03", "km2", "as stated", "", "আয়তন ১৯৫.০৩ বর্গ কিলোমিটার", ""),
        ("upazila", None, "pourashava_count", "1", "count", "as stated", "", "পৌরসভা ০১ টি (পৌর ওয়ার্ড -০৯ টি)", ""),
        ("upazila", None, "union_count", "7", "count", "as stated", "", "ইউনিয়ন ০৭ টি", ""),
        ("upazila", None, "union_ward_count", "63", "count", "as stated", "", "ইউ. পি. ওয়ার্ড ৬৩ টি", "7 unions x 9 wards"),
        ("upazila", None, "village_count", "123", "count", "as stated", "", "গ্রাম ১২৩ টি", ""),
        ("upazila", None, "mouza_count", "114", "count", "as stated", "", "মৌজা ১১৪ টি", ""),
        ("upazila", None, "population", "197693", "persons", "census 2022 (as quoted by the page)", "2022", "লোক সংখ্যা ১,৯৭,৬৯৩ জন (২০২২ সালের জনশুমারী ও গৃহগণনা অনুযায়ী)", "male 98,415, female 99,278; BBS 2022 C-01 enumerated total is 197,713"),
    ],
    "697ffd5135ce18e1c06df33b": [
        ("pourashava", None, "established", "2002-12-23", "date", "as stated", "2002", "প্রতিষ্ঠাকাল : ২৩/১২/২০০২ ইং", ""),
        ("pourashava", None, "area_km2", "25.60", "km2", "as stated", "", "পৌরসভার আয়তন : ২৫.৬০ বর্গ কিঃমিঃ", ""),
        ("pourashava", None, "class", "গ", "class", "as stated (garbled)", "", "পৌরসভার শ্রেণী : গুচ শ্রেণী", "printed 'গুচ শ্রেণী', read as গ"),
        ("pourashava", None, "population", "29182", "persons", "as stated (year not stated)", "", "মোট জনসংখ্যা : ২৯,১৮২ জন", ""),
        ("pourashava", None, "ward_count", "9", "count", "as stated", "", "ওয়ার্ড সংখ্যা", "value on page: '০৯ (নয়) টি'"),
    ],
    "697f803535ce18e1c06b772a": [
        ("upazila", None, "area_km2", "475.26", "km2", "as stated", "", "উপজেলার মোট আয়তন | : ৪৭৫.২৬ বর্গ কিলোমিটার", ""),
        ("upazila", None, "union_count", "9", "count", "as stated", "", "ইউনিয়নের সংখ্যা | : ০৯ (নয়) টি", ""),
        ("upazila", None, "pourashava_count", "2", "count", "as stated", "", "পৌরসভার সংখ্যা | : ০২ (দুই) টি", ""),
        ("upazila", None, "mouza_count", "392", "count", "as stated", "", "মৌজার সংখ্যা | : ৩৯২ টি", ""),
        ("upazila", None, "village_count", "415", "count", "as stated", "", "গ্রামের সংখ্যা | : ৪১৫ টি", ""),
        ("upazila", None, "population", "330924", "persons", "as stated (year not stated)", "", "উপজেলার মোট জনসংখ্যা | : ৩,৩০,৯২৪ জন", "BBS 2022 enumerated count is 376,386, so this figure predates 2022"),
        ("upazila", None, "households", "72280", "households", "as stated (year not stated)", "", "খানা/পরিবারের সংখ্যা | : ৭২,২৮০ টি", ""),
    ],
    "697f99fa35ce18e1c06c2174": [
        ("upazila", None, "area_km2", "475.26", "km2", "as stated", "", "গোদাগাড়ী উপজেলার আয়তন ৪৭৫.২৬ বর্গ কিঃ মিঃ", ""),
    ],
    "697fbb4535ce18e1c06cd676": [
        ("pourashava", None, "established", "1995", "year", "as stated", "1995", "স্থাপিত | : | ১৯৯৫", ""),
        ("pourashava", None, "class", "ক", "class", "as stated", "", "শ্রেণী | : | ক", ""),
        ("pourashava", None, "area_km2", "14.27", "km2", "as stated", "", "আয়তন | : | ১৪.২৭ বর্গ কিঃ মিঃ", ""),
        ("pourashava", None, "ward_count", "9", "count", "as stated", "", "ওয়ার্ড সংখ্যা | : | ৯ টি", ""),
        ("pourashava", None, "population", "42241", "persons", "as stated (year not stated)", "", "জনসংখ্যা | : | ৪২,২৪১ জন", ""),
    ],
    "697fc88f35ce18e1c06d10a2": [
        ("pourashava", None, "established", "2002-11-14", "date", "as stated", "2002", "(গ) শ্রেণীর প্রতিষ্ঠার তারিখ | : | ১৪-১১-২০০২ ইং", "গ class from 2002-11-14"),
        ("pourashava", None, "class", "খ", "class", "as stated", "2011", "(খ) শ্রেণীর প্রতিষ্ঠার তারিখ | : | ১৯-০১-২০১১ ইং", ""),
        ("pourashava", None, "ward_count", "9", "count", "as stated", "", "ওয়ার্ড | : | ৯ টি", ""),
        ("pourashava", None, "area_km2", "20.05", "km2", "as stated", "", "আয়তন | : | ২০.০৫ বর্গ কিলোমিটার", ""),
        ("pourashava", None, "mouza_count", "15", "count", "as stated", "", "মৌজার সংখ্যা | : | ১৫ টি", ""),
        ("pourashava", None, "village_count", "16", "count", "as stated", "", "গ্রামের সংখ্যা | : | ১৬ টি", ""),
        ("pourashava", None, "population", "18515", "persons", "as stated (year not stated)", "", "মোট জনসংখ্যা | : | ১৮,৫১৫ জন", ""),
    ],
    "697f79de35ce18e1c06b62e3": [
        ("upazila", None, "area_km2", "162.65", "km2", "as stated", "", "আয়তন | ১৬২.৬৫ বর্গ কিলোমিটার", ""),
        ("upazila", None, "population", "170021", "persons", "approximate (year not stated)", "", "জনসংখ্যা | ১৭০০২১ জন প্রায়", "page says প্রায় (approximately)"),
        ("upazila", None, "households", "43984", "households", "as stated (year not stated)", "", "মোট পরিবার (খানা) | ৪৩,৯৮৪ টি", ""),
        ("upazila", None, "village_count", "138", "count", "as stated", "", "গ্রাম | ১৩৮ টি", ""),
        ("upazila", None, "mouza_count", "137", "count", "as stated", "", "মৌজা | ১৩৭ টি", ""),
        ("upazila", None, "union_count", "6", "count", "as stated", "", "ইউনিয়ন | ০৬ টি", ""),
        ("upazila", None, "pourashava_count", "1", "count", "as stated", "", "পৌরসভা | ০১ টি", "Keshorhat"),
    ],
    "697f93d335ce18e1c06bf218": [
        ("pourashava", None, "established", "2002-12-22", "date", "as stated", "2002", "স্থাপিত | : | ২২-১২-২০০২", ""),
        ("pourashava", None, "class", "খ", "class", "as stated", "", "শ্রেণী | : | খ", ""),
        ("pourashava", None, "ward_count", "9", "count", "as stated", "", "ওয়ার্ড সংখ্যা | : | 9", ""),
        ("pourashava", None, "population", "20342", "persons", "as stated (year not stated)", "", "জনসংখ্যা | : | 20342", "the page's 2011 census row gives male 9852 + female 9793 = 19645; area printed '১৬২১ বর্গ কিঃ মিঃ' (implausible, not recorded)"),
    ],
    "697f801d35ce18e1c06b6bfd": [
        ("upazila", None, "area_km2", "339", "km2", "as stated (incl. pourashavas)", "", "আয়তন | ৩৩৯ ব.কি.(পৌরসভা সহ)", "the union-list page says ২৮০.৪২০ বর্গ কিঃ মিঃ"),
        ("upazila", None, "population", "314196", "persons", C11, "2011", "৩,১৪,১৯৬ জন (২০১১ সালের আদমশুমারী)", ""),
        ("upazila", None, "households", "76622", "households", "as stated (year not stated)", "", "মোট পরিবার | ৭৬,৬২২ টি", ""),
        ("upazila", None, "village_count", "211", "count", "as stated", "", "গ্রাম | ২১১ টি, মহাল্লা-৫৮", "plus 58 mahallas"),
        ("upazila", None, "mouza_count", "191", "count", "as stated", "", "মৌজা | ১৯১ টি", ""),
        ("upazila", None, "union_count", "8", "count", "as stated", "", "ইউনিয়ন | ৮ টি", ""),
        ("upazila", None, "pourashava_count", "2", "count", "as stated", "", "পৌরসভা | ২ টি", "Katakhali, Naohata"),
    ],
    "697f802d35ce18e1c06b738d": [
        ("upazila", None, "area_km2", "280.420", "km2", "as stated", "", "০৮ টি ইউনিয়ন ও ২টি পৌরসভা সমন্বয়ে গঠিত যার আয়তন ২৮০.৪২০ বর্গ কিঃ মিঃ", "the এক নজরে page says 339 incl. pourashavas"),
    ],
    "697fbb5735ce18e1c06cddcf": [
        ("pourashava", None, "established", "2002-12-15", "date", "as stated", "2002", "স্থাপিত | : | ১৫ ডিসেম্বর ২০০২", ""),
        ("pourashava", None, "class", "খ", "class", "as stated", "", "“খ” শ্রেণী", ""),
        ("pourashava", None, "ward_count", "9", "count", "as stated", "", "পৌরসভার ওয়ার্ড সংখ্যা | : | ০৯ টি", ""),
        ("pourashava", None, "area_km2", "24.50", "km2", "as stated", "", "পৌরসভার আয়তন | : | ২৪.৫০ বর্গ কিলোমিটার", ""),
        ("pourashava", None, "mouza_count", "6", "count", "as stated", "", "মৌজার সংখ্যা | : | ০৬ টি", ""),
        ("pourashava", None, "population", "47041", "persons", "as stated (year not stated)", "", "মোট= | : | ৪৭,০৪১ জন", "male 24,130, female 22,911"),
    ],
    "697fbb2835ce18e1c06cc87b": [
        ("upazila", None, "area_km2", "192.64", "km2", "as stated", "", "উপজেলার মোট আয়তন | : ১৯২.৬৪ ( বর্গ কিঃমিঃ )", ""),
        ("upazila", None, "pourashava_count", "1", "count", "as stated", "", "পৌরসভা | : ১ টি", ""),
        ("upazila", None, "union_count", "6", "count", "as stated", "", "ইউনিয়ন | : ৬ টি", ""),
        ("upazila", None, "mouza_count", "128", "count", "as stated", "", "মৌজা | : ১২৮ টি", ""),
        ("upazila", None, "village_count", "183", "count", "as stated", "", "গ্রাম | : ১৮৩ টি", ""),
        ("upazila", None, "population", "207490", "persons", C11, "2011", "২,০৭,৪৯০ জন (২০১১ সালের আদম শুমারী )", ""),
    ],
    "697faa5335ce18e1c06c7ae1": [
        ("pourashava", None, "established", "2001-01-24", "date", "as stated", "2001", "পৌরসভা স্থাপিতঃ | ২৪/০১/২০০১ খ্রিঃ", ""),
        ("pourashava", None, "class", "খ", "class", "as stated", "", "পৌরসভার শ্রেণীঃ | ‘‘খ’’ শ্রেণী", ""),
        ("pourashava", None, "area_km2", "13.51", "km2", "as stated", "", "পৌরসভার আয়তনঃ | ১৩.৫১ বর্গ কিলোমিটার", ""),
        ("pourashava", None, "ward_count", "9", "count", "as stated", "", "ওয়ার্ড সংখ্যাঃ | ০৯ (নয়) টি", ""),
        ("pourashava", None, "mouza_count", "14", "count", "as stated", "", "মৌজাঃ | ১৪ টি", ""),
        ("pourashava", None, "population", "24208", "persons", "census (page says 2021; no census was held in 2021)", "", "২৪২০৮ [২০২১ সনের আদমশুমারী অনুযায়ী)", "year as printed is impossible; probably 2011"),
    ],
    "697fb33c35ce18e1c06cb43b": [
        ("upazila", None, "area_km2", "295.39", "km2", "as stated", "", "১১৪.০৫ বর্গ মাইল বা ২৯৫.৩৯ বর্গ কিলোমিটার", ""),
        ("upazila", None, "pourashava_count", "2", "count", "as stated", "", "০২টি (তানোর পৌরসভা, মুন্ডুমালা পৌরসভা)", ""),
        ("upazila", None, "union_count", "7", "count", "as stated", "", "ইউনিয়ন | : | ০৭টি (কলমা ইউনিয়ন", ""),
        ("upazila", None, "village_count", "210", "count", "as stated", "", "গ্রাম সংখ্যা | : | ২১০ টি", "the union-list page says 169"),
        ("upazila", None, "mouza_count", "212", "count", "as stated", "", "২১২ টি (জনবসতিপূর্ণ মৌজা ২০৬ টি এবং জনবসতিহীন মৌজা সংখ্যা ০৬ টি)", "206 populated + 6 unpopulated; the union-list page says 211"),
        ("upazila", None, "population", "191330", "persons", "as stated (2011 per the portal's ভৌগলিক পরিচিতি page)", "2011", "১,৯১,৩৩০ জন(পুরুষঃ৯৪,০৪১ জন,মহিলাঃ৯৭,২৮৯জন)", ""),
        ("upazila", None, "households", "47425", "households", "as stated (year not stated)", "", "মোট পরিবার | : | ৪৭,৪২৫টি", ""),
    ],
    "697f93bf35ce18e1c06be895": [
        ("upazila", None, "mouza_count", "211", "count", "as stated", "", "মোট ২ টি পৌরসভা, ৭ টি ইউনিয়ন, মৌজা ২১১ এবং ১৬৯ টি গ্রাম", "the এক নজরে page says 212 mouzas / 210 villages"),
        ("upazila", None, "village_count", "169", "count", "as stated", "", "মৌজা ২১১ এবং ১৬৯ টি গ্রাম", ""),
    ],
    "697f93ff35ce18e1c06c0642": [
        ("pourashava", None, "class", "গ", "class", "as stated", "", "পৌরসভার শ্রেণী ঃ | ‘‘গ’’", ""),
        ("pourashava", None, "ward_count", "9", "count", "as stated", "", "ওয়ার্ড সংখ্যাঃ | ৯টি", ""),
        ("pourashava", None, "area_km2", "27.43", "km2", "as stated", "", "আয়তনঃ | ২৭.৪৩০ বর্গকিঃমিঃ", ""),
        ("pourashava", None, "mouza_count", "22", "count", "as stated", "", "মৌজার সংখ্যা ঃ | ২২টি", ""),
        ("pourashava", None, "village_count", "26", "count", "as stated", "", "গ্রামের সংখ্যা ঃ | ২৬টি", ""),
        ("pourashava", None, "population", "28250", "persons", "as stated (year not stated)", "", "মোট লোক সংখ্যা ঃ | ২৮২৫০ জন", "same page also gives 50,930 for 2001 (inconsistent)"),
        ("pourashava", None, "established", "1995-12-01", "date", "as stated", "1995", "পৌরসভা স্থাপিতঃ | ০১/১২/১৯৯৫ ইং", ""),
    ],
    "697fe57235ce18e1c06daf84": [
        ("pourashava", None, "established", "2002-11-14", "date", "as stated", "2002", "স্থাপিত | ১৪ ই নভেম্বর ২০০২ ইং", ""),
        ("pourashava", None, "class", "খ", "class", "as stated", "", "শ্রেণী | ‘খ’ (দ্বিতীয়)", ""),
        ("pourashava", None, "ward_count", "9", "count", "as stated", "", "ওয়ার্ড সংখ্যা | ০৯ টি", ""),
        ("pourashava", None, "area_km2", "31.72", "km2", "as stated", "", "এরিয়া (৩১.৭২ বর্গ কিঃমিঃ)", "ward-wise areas also printed"),
        ("pourashava", None, "population", "31443", "persons", "pourashava's own count", "2023", "মোট = | ১৫৬৩০ | ১৫০১৫ | ৩০৬৪৫ | ১৬০৩৩ | ১৫৪১০ | ৩১৪৪৩", "2023 total; same table gives 30,645 for 2022"),
        ("pourashava", None, "population", "30645", "persons", "pourashava's own count", "2022", "মোট = | ১৫৬৩০ | ১৫০১৫ | ৩০৬৪৫", "not the BBS census figure"),
    ],
}


def clean_union(s):
    raw = nfc(s).strip()
    s = re.sub(r"^[০-৯0-9]+\s*[।\.]\s*", "", raw)
    m = re.match(r"^([০-৯0-9]+)\s*নং\s*", s)
    no = asc(m.group(1)) if m else ""
    s = re.sub(r"^[০-৯0-9]+\s*নং\s*", "", s)
    s = re.sub(r"\s*(ইউনিয়ন|ইউনয়ন)\s*(পরিষদ)?\s*$", "", s).strip(" ,।")
    return s, no, raw


UNION_RE = r"ইউনিয়ন|ইউনয়ন"


def unions_from(c):
    """[(name, number, printed, website, area_cell)] from a union-list page (tables, then links, then numbered lines)."""
    out, area_col = [], None
    for cells, tr in table_rows(c["html"]):
        if any("আয়তন" in x for x in cells):
            area_col = [i for i, x in enumerate(cells) if "আয়তন" in x][0]
        names = [x for x in cells if re.search(UNION_RE, x) and not re.search(r"পরিষদ$|^ইউনিয়ন$|নাম", x.strip())]
        if not names:
            continue
        sites = [clean_url(h) for h in re.findall(r'href="([^"]*)"', tr) if re.search(r"up\d*\.rajshahi", h)]
        sites = sites or [clean_url(x) for x in cells if re.search(r"up\d*\.rajshahi\.gov\.bd", x)]
        n, no, raw = clean_union(names[0].split("\n")[0])
        serial = asc(cells[0]).strip() if cells and re.fullmatch(r"[০-৯0-9]+", cells[0].strip()) else ""
        area = cells[area_col].strip() if area_col is not None and area_col < len(cells) else ""
        out.append((n, no or serial, raw, sites[0] if sites else "", area))
    if out:
        return out
    for h, x in links(c["html"]):
        if re.search(UNION_RE, x):
            n, no, raw = clean_union(x)
            out.append((n, no, raw, clean_url(h), ""))
    if out:
        return out
    for line in c["text"].split("\n"):
        if re.match(r"^\s*[০-৯0-9]+\s*[।\.]\s*[০-৯0-9]+\s*নং", line):
            n, no, raw = clean_union(line)
            out.append((n, no, raw, "", ""))
    return out



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
DV_AIA = "http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt"
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
}

# Upazilas listed on the portals in 2026 that the project seed does not have yet: English key is a transliteration
# of the portal subdomain, not printed on the pages.
DV_NEW_UPAZILAS = {("rangpur", "Ruhia"), ("rangpur", "Bhulli")}
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
            r = requests.get(DV_AIA, headers={"User-Agent": DV_UA}, timeout=30)
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

    def upz_sub(self, d, en):
        return next((s for e, _, s, _ in self.districts[d]["upazilas"] if e == en), "")


DV_SERIAL = r"^[(.]?(?:[০-৯0-9]{1,4}|[ক-হ])\s*[.।)\]:]*\s*$"
DV_HEADER = r"(নাম|নম্বর|ক্রম|ওয়েবসাইট|লিংক|লিঙ্ক)\s*$|^(জেলা|উপজেলা|ইউনিয়ন|ইউিনয়ন|নং|ক্রমিক)$|^ক্র(মিক|ঃ|:|\.)?\s*(নং|নম্বর)$"
DV_UNION_SUFFIX = r"\s*(ইউ\S{0,5}ন\s*পরিষ\S?|ইউ\S{0,5}ন|উনিয়ন|ইউপি|ইউ\.?\s*পি\.?)\s*[।.,]*\s*$"


DV_PERSON = r"মোঃ|মো:|মো\.|জনাব|মোছাঃ|মোসাঃ|বেগম|আলহাজ্ব|চেয়ারম্যান"


def dv_clean_union(s):
    """'০১। ১ নং চওড়া বড়গাছা ইউনিয়ন' -> ('চওড়া বড়গাছা', '01')."""
    s = dv_nfc(s).strip(" |।,.;:-")
    s = re.sub(r"\s*(https?://)?[\w.-]+\.gov\.bd/?\S*", "", s)              # printed portal address
    s = re.sub(r"\s*[-–]?\s*[A-Za-z][A-Za-z .()'-]*$", "", s)                 # 'ভোমরাদহ ইউপি- Bhomradaha'
    s = s.strip(" |।,.;:-")
    s = re.sub(r"^[(]?[০-৯0-9]{1,3}\s*[.।)]\s*", "", s)              # list serial '০১।'
    no = ""
    m = re.match(r"^([০-৯0-9]{1,2})\s*(?:নং|নম্বর|no\.?|ন(?=\s))\s*(.*)$", s)
    if m:
        no, s = dv_asc(m.group(1)).zfill(2), m.group(2)
    s = re.split(r"\s*[।;,]\s*", s)[0]                          # 'X ইউনিয়ন। এ ইউনিয়নের বিস্তারিত ...'
    s = re.sub(DV_UNION_SUFFIX, "", s)
    s = re.sub(r"\s+ও$", "", s)                                       # last-but-one item of 'a, b ও'
    return re.sub(r"\s+", " ", s).strip(" |।,.;:-"), no


DV_JUNK = (r"(?<![ঀ-৿])(মোট|হলো|হলোঃ|যথা|যথাঃ|শূন্য|ভাড়া)(?![ঀ-৿])|উপজেলা|সমূহ|সমুহ|তালিকা|রয়েছে|নিম্নরূপ|বিস্তারিত|"
           r"উল্লেখ্য|যোগাযোগ|কন্টেন্ট|ডাউনলোড|ফাইল|[()]|"
           r"ইউনিয়েনর নাম|ইউনিয়নের নাম|পরিষদের নাম|এখানে|ক্লিক|অন্তর্ভুক্ত|পৌরসভা|সর্বমোট")


def dv_expand_inline(rows):
    """'... যথাঃ ১ নং ধর্মগড় ২ নং নেকমরদ ... ও ৮ নং নন্দুয়ার' -> one row per item."""
    out = []
    for cells in rows:
        if len(cells) == 1 and len(re.findall(r"[০-৯0-9]{1,2}\s*নং", cells[0][0])) >= 3:
            t = cells[0][0]
            m = re.search(r"([০-৯0-9]+)\s*টি\s*ইউনিয়ন", t)
            if m:
                out.append([(f"{m.group(1)}টি", [])])
            for no, nm in re.findall(r"([০-৯0-9]{1,2})\s*নং\s*(.+?)(?=\s*(?:,|ও)?\s*[০-৯0-9]{1,2}\s*নং|[।]|$)", t):
                out.append([(f"{no} নং {nm}", [])])
        else:
            out.append(cells)
    return out


def dv_rows(c):
    """Rows of a list page: table rows (cells + links) or, without tables, one row per text line."""
    rows = []
    trs = re.findall(r"<tr.*?</tr>", c["html"], flags=re.S)
    if trs:
        for tr in trs:
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S)
            rows.append([(dv_text(x).replace("\n", " ").strip(), dv_links(x)) for x in cells])
    else:
        frag = re.sub(r"<br\s*/?>", "</p><p>", c["html"])
        for blk in re.split(r"</p>|</li>|</div>|</h\d>", frag):
            t = dv_text(blk).replace("\n", " ").strip()
            if t and not re.match(r"^(কন্টেন্ট|কনটেন্টটি)", t):
                rows.append([(t, dv_links(blk))])
    return rows


def dv_union_list(c, div, district=None, upazila=None):
    """Parse a union list page. district/upazila fix the context when the page has no such column.
    Returns (rows, stated) — rows: dict(district_en, upazila_en, upazila_printed, name_bn, printed, no, website);
    stated: {(district_en, upazila_en): (count, printed)} for per-upazila counts printed in the list."""
    out, stated = [], {}
    cur_d, cur_u, cur_u_printed = district, upazila, div.upz_bn(district, upazila) if district and upazila else ""
    for cells in dv_expand_inline(dv_rows(c)):
        texts = [t for t, _ in cells]
        if any(re.search(DV_HEADER, t) for t in texts if t):
            continue
        if len(texts) == 1 and (m := re.search(r"মোট\s*([০-৯0-9]{1,3})\s*টি\s*ইউনিয়ন|([০-৯0-9]{1,3})\s*টি\s*ইউনিয়ন", texts[0])) \
                and cur_u and upazila:
            stated[(cur_d, cur_u)] = (str(int(dv_asc(m.group(1) or m.group(2)))), m.group(0))
        names, site, count = [], "", None
        for t, ls in cells:
            if not t or re.fullmatch(r"[:ঃ\-|–]+", t):
                continue
            if re.fullmatch(DV_SERIAL, t):
                continue
            m = re.fullmatch(r"([০-৯0-9]{1,3})\s*(টি|টি।)?\s*(\(.*\))?", t)
            if m and m.group(2):
                count = (dv_asc(m.group(1)), t)
                continue
            if re.search(r"\.gov\.bd|https?://|www\.", t, re.I) and not re.search(r"[ঀ-৿]", t):
                site = dv_site(t)
                continue
            if not re.search(r"[ঀ-৿]", t) or re.fullmatch(r"[০-৯0-9.,\s()%]+", t):
                continue                                                    # figures in extra columns
            names.append((t, ls))
        if names:
            nd = div.district(names[0][0])
            if nd and (district is None or nd == district) and (len(names) >= 2 or cur_d is None) \
                    and not (nd == cur_d and len(names) == 1):
                if nd != cur_d:
                    cur_d, cur_u = nd, upazila
                names = names[1:]
        if not names or cur_d is None:
            continue
        first = names[0][0]
        fu = div.upazila(cur_d, re.sub(r"\s*উপজেলা.*$", "", first))
        head = fu and (len(names) >= 2 or "উপজেলা" in first or (fu != cur_u and not upazila))
        if head and upazila and "উপজেলা" not in first and (
                dv_nfc(first).strip() not in {dv_nfc(x.lstrip("~")) for e, b, _, al in div.districts[cur_d]["upazilas"]
                                              if e == upazila for x in [b] + al}
                or any(re.search(DV_PERSON, t) for t, _ in names[1:2])):
            head = False                         # a union named like its upazila, followed by other columns
        if head:
            cur_u, cur_u_printed = fu, re.sub(r"\s*উপজেলা.*$", "", dv_nfc(first)).strip(" :ঃ")
            if count:
                stated[(cur_d, cur_u)] = (str(int(count[0])), count[1])
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
        printed, ls = names[0] if upazila else names[-1]       # upazila pages: extra columns (chairman, notes) follow
        name, no = dv_clean_union(printed)
        if not name or re.search(DV_JUNK, name) or len(name.split()) > 4:
            continue
        if not site:
            for h, _ in ls:
                if re.search(r"\.gov\.bd", h) and dv_site(h).split("/")[2].split(".")[0] not in ("www",):
                    site = dv_site(h)
        prev = next((r for r in out if r.get("upazila_en") == cur_u and r.get("district_en") == cur_d
                     and r["name_bn"] == name and r["no"] == no), None)
        if prev:
            prev["dup"] = prev.get("dup", 1) + 1
            continue
        out.append(dict(district_en=cur_d, upazila_en=cur_u, upazila_printed=cur_u_printed, name_bn=name,
                        printed=dv_nfc(printed), no=no, website=site))
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
                (host is None or urlparse(h).netloc.lower() == host) and "/pages/static-pages/" in h:
            return x, h
    return None


DV_FACT_LABELS = [  # (fact, include regex on label, exclude regex on label, unit)
    ("area_km2", r"আয়তন", r"পৌর|জমি|ভূমি|বন|অবস্থান", "km2"),
    ("population", r"জনসংখ্যা|লোকসংখ্যা|লোক সংখ্যা", r"ঘনত্ব|বৃদ্ধি|হার|পুরুষ|মহিলা|ভোটার|পৌর|শিক্ষিত|উপজাতী|আদিবাসী|ভিত্তিক|পেশা|ধর্ম", "persons"),
    ("upazila_count", r"উপজেলা", r"ভূমি|অফিস|স্বাস্থ্য|দূরত্ব|দুরত্ব|নির্বাহী|পরিষদ|নাম|হেড|সদর|কমপ্লেক্স", "count"),
    ("thana_count", r"থানা", r"নাম|পুলিশ|দূরত্ব|দুরত্ব", "count"),
    ("city_corporation_count", r"সিটি\s*কর্পোরেশন", r"ওয়ার্ড|নাম", "count"),
    ("pourashava_count", r"পৌরসভা|পৌর সভা", r"ওয়ার্ড|মৌজা|নাম|আয়তন|জনসংখ্যা|হোল্ডিং", "count"),
    ("union_count", r"ইউনিয়ন", r"ভূমি|অফিস|ভবন|নাম|ডিজিটাল|তথ্য|কমপ্লেক্স|ওয়ার্ড|দূরত্ব|দুরত্ব|স্বাস্থ্য|কেন্দ্র|কল্যাণ|সাব|ক্লিনিক|উদ্যোক্তা|সচিব|চেয়ারম্যান|সদস্য", "count"),
    ("ward_count", r"ওয়ার্ড|ওয়ার্ড|ওযার্ড|ওয়াড", r"সদস্য|মেম্বার|কাউন্সিলর|নাম|পৌর|নং|ভিত্তিক|সিটি", "count"),
    ("mouza_count", r"মৌজা", r"পৌর|নাম", "count"),
    ("village_count", r"গ্রাম", r"গুচ্ছ|আদর্শ|ভিত্তিক|পৌর|নাম|সংসদ|গ্রামীণ|পুলিশ|চৌকিদার|আশ্রয়|রক্ষা", "count"),
    ("household_count", r"পরিবার সংখ্যা|পরিবারের সংখ্যা|মোট পরিবার|খানার সংখ্যা|খানা সংখ্যা|^\W*খানা\W*$|মোট খানা",
     r"পায়খানা|এতিম|কৃষক|পরিকল্পনা|কল্যাণ|উপজাতি|আদিবাসী", "households"),
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
    if dot_thousands and re.fullmatch(r"\d{1,3}(\.\d{3})+", raw):
        note, raw = f"'{raw}' read as thousands separator", raw.replace(".", "")
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
    return pairs


DV_BOUNDS = {  # plausible ranges per level; counts outside are dropped, areas/populations get a DOUBT note
    "division": dict(area_km2=(1000, 40000), population=(1e6, 1e8), upazila_count=(5, 200), thana_count=(5, 200),
                     union_count=(50, 2000), pourashava_count=(1, 200), mouza_count=(100, 30000),
                     village_count=(100, 40000), city_corporation_count=(0, 10), ward_count=(0, 1e5),
                     household_count=(1e5, 2e7)),
    "district": dict(area_km2=(300, 10000), population=(2e5, 2e7), upazila_count=(2, 20), thana_count=(2, 40),
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
        for fact, inc, exc, unit in DV_FACT_LABELS:
            if (wanted and fact not in wanted) or fact in seen or not re.search(inc, lab) or re.search(exc, lab):
                continue
            if len(lab) > 45:
                continue
            v, note = dv_number(value, dot_thousands=(fact != "area_km2"), skip_year=(fact == "population"))
            if not v:
                continue
            y = re.search(r"(?<![\d.,])(19|20)\d\d(?![\d.,])", dv_asc(value))
            year = y.group(0) if y else ""
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
                elif not re.search(r"^[\d,\.\s\(\)]*(বর্গ\s*কি|বগ\s*কি|বঃ\s*কি|ব\s*[:\.]\s*কি|ব\.কি|বর্গকি|কিঃ|কি\.\s*মি|কিলো|km|sq\s*km|কিমি)", after, re.I):
                    u = "unstated"
            if u in ("count", "persons", "households"):
                if not re.fullmatch(r"\d+", v):
                    continue
                v = str(int(v))
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


def dv_save_raw(out, name, url, c):
    if not out:
        return
    os.makedirs(os.path.join(out, "raw"), exist_ok=True)
    with open(os.path.join(out, "raw", name), "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\nUPDATED: {c['updated']}\nTITLE: {c['title']}\nACCESSED: {time.strftime('%Y-%m-%d')}\n\n"
                f"{dv_redact(c['text'])}\n")


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
    ul = dv_pick(menu, r"উপজেলার তালিকা|উপজেলা পরিষদের তালিকা|উপজেলা পরিষদসমূহ", r"নির্বাহী|ভূমি", host)
    if ul:
        c = page("upazilas", ul[1])
        if c:
            n = 0
            for cells in dv_rows(c):
                for t, ls in cells:
                    u = div.upazila(d, re.sub(r"^[০-৯0-9]+\s*[.।)]?\s*|\s*উপজেলা.*$", "", t))
                    if u and u not in upz:
                        n += 1
                        site = next((dv_site(h) for h, _ in ls if f".{host}" in h), "")
                        upz[u] = dict(printed=re.sub(r"^[০-৯0-9]+\s*[.।)]?\s*|\s*উপজেলা.*$", "", t).strip(),
                                      website=site, url=ul[1], note=dv_upd(c))
            facts.append(dict(entity_level="district", entity_name_en=d, district_en=d, fact="upazila_count_listed",
                              value=str(n), unit="count", basis="count of upazilas listed", source_key=key,
                              source_url=ul[1], notes=dv_upd(c)))
    # unions
    un = dv_pick(menu, r"ইউনিয়নের তালিকা|ইউনিয়ন পরিষদের তালিকা|উপজেলা ও ইউনিয়ন|ইউনিয়ন পরিষদসমূহ",
                 r"চেয়ারম্যান|সচিব|উদ্যোক্তা|কাজি|জনপ্রতিনিধি|তথ্য ও সেবা", host)
    cands = [un] + [x for x in menu if x != un and re.search(r"উপজেলা ও ইউনিয়ন|ইউনিয়ন পরিষদসমূহ|ইউনিয়নের তালিকা", x[0])
                    and "/pages/" in x[1] and urlparse(x[1]).netloc.lower() == host] if un else []
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
        for w in warns:
            log(f"{d} union list: {w}")
        per = {}
        for r in rows:
            per.setdefault(r["upazila_en"], []).append(r)
            upz.setdefault(r["upazila_en"], dict(printed=r["upazila_printed"], website="", url=url, note=dv_upd(c)))
            areas.append(dict(level="union", name_bn=r["name_bn"], parent_level="upazila", parent_name_en=r["upazila_en"],
                              parent_name_bn=r["upazila_printed"], district_en=d, upazila_en=r["upazila_en"], code=r["no"],
                              code_scheme="UNION_NO_IN_UPAZILA" if r["no"] else "", website=r["website"], source_key=key,
                              source_url=url, notes=f"printed '{r['printed']}'" + (f"; row printed {r['dup']} times on the page"
                              if r.get("dup") else "") + f"; {dv_upd(c)}; English name not printed"))
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
        facts.append(dict(entity_level="district", entity_name_en=d, district_en=d, fact="union_count_listed",
                          value=str(len(rows)), unit="count", basis="count of unions listed", source_key=key,
                          source_url=url, notes=dv_upd(c)))
        m = re.search(r"মোট ইউনিয়ন\s*[:ঃ]?\s*([০-৯0-9]+)|([০-৯0-9]+)\s*টি ইউনিয়ন", c["text"])
        if m:
            facts.append(dict(entity_level="district", entity_name_en=d, district_en=d, fact="union_count",
                              value=str(int(dv_asc(m.group(1) or m.group(2)))), unit="count", basis="as stated",
                              source_key=key, source_url=url, notes=f"printed '{m.group(0)}'; {dv_upd(c)}"))
    else:
        log(f"{d}: no union list page found")
    for u, r in sorted(upz.items()):
        if not r["website"] and div.upz_sub(d, u):
            site = f"https://{div.upz_sub(d, u)}.{host}/"
            t = F.get(site)
            m = re.search(r"<title>(.*?)</title>", t or "", re.S)
            if m and dv_loose(div.upz_bn(d, u)) in dv_loose(m.group(1)) and "উপজেলা" in m.group(1):
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
        if not nm or re.search(r"তালিকা|সংখ্যা|নাম$|এক নজরে|একনজরে", nm):
            return 0
        full = nm if nm.endswith("পৌরসভা") else nm + " পৌরসভা"
        if full not in poura:
            poura[full] = dict(printed=nm, url=url, notes=[note], website=site)
        else:
            poura[full]["notes"].append(note)
            poura[full]["website"] = poura[full]["website"] or site
        return 1

    pl = dv_pick(menu, r"পৌরসভার তালিকা|পৌরসভা সমূহ|পৌরসভাসমূহ", None, host)
    if pl:
        c = page("pourashavas", pl[1])
        if c:
            n = 0
            for cells in dv_rows(c):
                nm, site = "", ""
                for t, ls in cells:
                    if not t or re.fullmatch(DV_SERIAL, t) or re.search(DV_HEADER, t) or t in ("-", "–"):
                        continue
                    if re.search(r"\.gov\.bd|https?://|\.com|www\.", t) and not re.search(r"[ঀ-৿]", t):
                        site = dv_site(t)
                    elif not nm and re.search(r"[ঀ-৿]", t):
                        nm = t
                        site = site or next((dv_site(h) for h, _ in ls if re.search(r"pourashava|paurashava|pourosova|municipality|ps\.", h, re.I)), "")
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
    if res["glance"]:
        gu, c = res["glance"]
        m = re.search(r"পৌরসভা\s*[-–:ঃ]?\s*([০-৯0-9]+)\s*(?:টি)?\s*\(([^)]*)\)", c["text"])
        if m:
            for nm in re.split(r",|\s+এবং\s+|\s+ও\s+", m.group(2)):
                nm = nm.strip()
                if nm and re.fullmatch(r"[ঀ-৿ ]+", nm):
                    add_p(nm, gu, f"named in এক নজরে ('{m.group(0)}', {dv_upd(c)})")
    for full, p in poura.items():
        base_nm = re.sub(r"\s*পৌরসভা$", "", full)
        u = div.upazila(d, base_nm) or div.upazila(d, base_nm + " সদর")
        if not u and dv_loose(base_nm) == dv_loose(info["name_bn"]):
            u = div.upazila(d, "সদর")
        note = "; ".join(dict.fromkeys(p["notes"]))
        note += "; parent upazila inferred from the same-named upazila" if u else "; parent upazila not stated"
        if p["printed"] != full:
            note += f"; printed '{p['printed']}'"
        areas.append(dict(level="pourashava", name_bn=full, parent_level="upazila" if u else "district",
                          parent_name_en=u or d, parent_name_bn=div.upz_bn(d, u) if u else info["name_bn"], district_en=d,
                          upazila_en=u or "", website=p["website"], source_key=key, source_url=p["url"], notes=note))
    res["pourashavas"] = list(poura)
    return res


# ---------------------------------------------------------------------------------------- divisional portal
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
        for f in dv_facts(c, div=div, level="division"):
            facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact=f["fact"], value=f["value"],
                              unit=f["unit"], basis="as stated", year=f["year"], source_key=key, source_url=g[1],
                              notes=f"label '{f['label']}' value '{f['raw']}'" + (f"; {f['note']}" if f["note"] else "")
                              + f"; {dv_upd(c)}"))
    dl = dv_pick(menu, r"জেলার তালিকা|জেলাসমূহ|জেলা সমূহ", None, host)
    if dl and (c := page("districts", dl[1])):
        for cells in dv_rows(c):
            for t, _ in cells:
                d = div.district(re.sub(r"^[০-৯0-9]+\s*[.।)]?\s*|\s*জেলা$", "", t))
                if d and d not in res["districts"]:
                    res["districts"].append(d)
                    areas.append(dict(level="district", name_en=d, name_bn=dv_nfc(t).strip(), parent_level="division",
                                      parent_name_en=div.name_en, parent_name_bn=div.name_bn, district_en=d,
                                      code=str(len(res["districts"])).zfill(2), code_scheme=f"{div.code.upper()}DIV_LIST_SERIAL",
                                      website=f"https://{div.districts[d]['host']}/", source_key=key, source_url=dl[1],
                                      notes=f"{dv_upd(c)}; name_en is the project's key (not printed); website is the DC "
                                            f"portal (not linked from this page)"))
        facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact="district_count_listed",
                          value=str(len(res["districts"])), unit="count", basis="count of districts listed",
                          source_key=key, source_url=dl[1], notes=dv_upd(c)))
    ul = dv_pick(menu, r"উপজেলার তালিকা|উপজেলাসমূহ|উপজেলা সমূহ", None, host)
    if ul and (c := page("upazilas", ul[1])):
        cur_d, n = None, 0
        for cells in dv_rows(c):
            names = [t for t, _ in cells if t and not re.fullmatch(DV_SERIAL, t) and not re.search(DV_HEADER, t)]
            if not names:
                continue
            if len(names) >= 2 and div.district(names[0]):
                cur_d, names = div.district(names[0]), names[1:]
            elif cur_d is None and div.district(names[0]):
                cur_d, names = div.district(names[0]), names[1:]
            serial = next((dv_asc(t).strip(" .।") for t, _ in cells if re.fullmatch(DV_SERIAL, t or "x")), "")
            for t in names:
                u = div.upazila(cur_d, t) if cur_d else None
                if not u:
                    log(f"divisional upazila list: unknown upazila {t!r} (district {cur_d})")
                    continue
                n += 1
                res["upazilas"][(cur_d, u)] = t
                areas.append(dict(level="upazila", name_en=u, name_bn=dv_nfc(t), parent_level="district",
                                  parent_name_en=cur_d, parent_name_bn=div.districts[cur_d]["name_bn"], district_en=cur_d,
                                  upazila_en=u, code=serial.zfill(2), code_scheme=f"{div.code.upper()}DIV_LIST_SERIAL",
                                  source_key=key, source_url=ul[1],
                                  notes=f"{dv_upd(c)}; name_en is the project's key (not printed)"
                                        + ("; DOUBT: printed spelling looks like a misprint" if dv_nfc(t) in div.misprints
                                           else "")))
        m = re.search(r"মোট\s*([০-৯0-9]+)\s*টি", c["text"])
        facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact="upazila_count_listed", value=str(n),
                          unit="count", basis="count of upazilas listed", source_key=key, source_url=ul[1], notes=dv_upd(c)))
        if m:
            facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact="upazila_count",
                              value=str(int(dv_asc(m.group(1)))), unit="count", basis="as stated", source_key=key,
                              source_url=ul[1], notes=f"printed '{m.group(0)}' in the list heading; {dv_upd(c)}"))
    nl = dv_pick(menu, r"ইউনিয়নের তালিকা|ইউনিয়নসমূহ|ইউনিয়ন সমূহ", None, host)
    if nl and (c := page("unions", nl[1])):
        rows, stated = dv_union_list(c, div)
        for r in rows:
            if "warning" in r:
                log(f"divisional union list: {r['warning']}")
        rows = [r for r in rows if "warning" not in r]
        res["unions"] = rows
        per = {}
        for r in rows:
            per.setdefault((r["district_en"], r["upazila_en"]), []).append(r)
            note = f"printed '{r['printed']}'; upazila printed '{r['upazila_printed']}'"
            if r.get("dup"):
                note += f"; row printed {r['dup']} times"
            areas.append(dict(level="union", name_bn=r["name_bn"], parent_level="upazila", parent_name_en=r["upazila_en"],
                              parent_name_bn=r["upazila_printed"], district_en=r["district_en"], upazila_en=r["upazila_en"],
                              code=r["no"], code_scheme="UNION_NO_IN_UPAZILA" if r["no"] else "", website=r["website"],
                              source_key=key, source_url=nl[1], notes=f"{note}; {dv_upd(c)}; English name not printed"))
        for (d, u), rs in sorted(per.items()):
            facts.append(dict(entity_level="upazila", entity_name_en=u, district_en=d, upazila_en=u, fact="union_count",
                              value=str(len(rs)), unit="count", basis="count of unions listed", source_key=key,
                              source_url=nl[1], notes=dv_upd(c)))
        facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact="union_count_listed",
                          value=str(len(rows)), unit="count", basis="count of unions listed", source_key=key,
                          source_url=nl[1], notes=dv_upd(c)))
        m = re.search(r"তালিকা\s*[:ঃ]\s*([০-৯0-9]+)\s*টি", c["text"])
        if m:
            facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact="union_count",
                              value=str(int(dv_asc(m.group(1)))), unit="count", basis="as stated", source_key=key,
                              source_url=nl[1], notes=f"printed '{m.group(0)}' in the list heading; {dv_upd(c)}"))
    return res


# ---------------------------------------------------------------------------------------- upazila portals
DV_UNION_MENU_EX = r"কমিটি|বাল্যবিবাহ|শ্রমিক|ইজিপিপি|কর্মসূচ|তথ্য ও সেবা|চেয়ারম্যান|সচিব|উদ্যোক্তা|কাজি|জনপ্রতিনিধি|ভূমি|ডিজিটাল|কার্যালয়|সদস্য|নির্বাচন|বাজেট|প্রকল্প|হট ?লাইন"


def dv_title(t):
    m = re.search(r"<title>(.*?)</title>", t or "", re.S)
    return dv_nfc(html.unescape(m.group(1))).strip() if m else ""


def dv_collect_upazila(F, div, d, u, key, out, site=None):
    """One upazila portal: union list, এক নজরে facts, pourashava pages."""
    host_d = div.districts[d]["host"]
    site = site or (f"https://{div.upz_sub(d, u)}.{host_d}/" if div.upz_sub(d, u) else "")
    u_bn = div.upz_bn(d, u)
    res = dict(areas=[], facts=[], pages=[], unions=[], log=[], site=site, ok=False)
    if not site:
        res["pages"].append(dict(district_en=d, upazila_en=u, kind="home", url="", status="no portal address known"))
        return res
    home = F.get(site)
    title = dv_title(home)
    if not home or dv_loose(u_bn) not in dv_loose(title):
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
        if c:
            dv_save_raw(out, f"{d.lower()}_{sub}_{kind}.txt", url, c)
        return c

    def fact(level, name, f, url, c, extra=""):
        res["facts"].append(dict(entity_level=level, entity_name_en=name, district_en=d, upazila_en=u, fact=f["fact"],
                                 value=f["value"], unit=f["unit"], basis="as stated", year=f["year"], source_key=key,
                                 source_url=url, notes=dv_redact(f"{extra}label '{f['label']}' value '{f['raw']}'" +
                                                                 (f"; {f['note']}" if f["note"] else "") + f"; {dv_upd(c)}")))

    un = dv_pick(menu, r"ইউনিয়ন\s*(সমূহ|সমুহ|পরিষদ\s*সমূহ|পরিষদসমূহ|তালিকা|এর তালিকা|পরিষদের তালিকা)|ইউনিয়নসমূহ",
                 DV_UNION_MENU_EX, host) or dv_pick(menu, r"ইউনিয়ন", DV_UNION_MENU_EX, host)
    if un and (c := page("unions", un[1])):
        rows, stated = dv_union_list(c, div, district=d, upazila=u)
        res["log"] += [f"{d}/{u}: {r['warning']}" for r in rows if "warning" in r]
        rows = [r for r in rows if "warning" not in r and r["upazila_en"] == u]
        res["unions"] = rows
        for r in rows:
            res["areas"].append(dict(level="union", name_bn=r["name_bn"], parent_level="upazila", parent_name_en=u,
                                     parent_name_bn=u_bn, district_en=d, upazila_en=u, code=r["no"],
                                     code_scheme="UNION_NO_IN_UPAZILA" if r["no"] else "", website=r["website"],
                                     source_key=key, source_url=un[1],
                                     notes=f"printed '{r['printed']}'" + (f"; row printed {r['dup']} times" if r.get("dup") else "")
                                     + f"; {dv_upd(c)}; English name not printed"))
        res["facts"].append(dict(entity_level="upazila", entity_name_en=u, district_en=d, upazila_en=u, fact="union_count",
                                 value=str(len(rows)), unit="count", basis="count of unions listed", source_key=key,
                                 source_url=un[1], notes=f"unions listed on '{c['title']}'; {dv_upd(c)}"))
        if not rows:
            res["log"].append(f"{d}/{u}: no union rows parsed from {un[1]}")
    else:
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
        if p_host == host and "/pages/static-pages/" in h:
            c = page("poura", h)
            if not c:
                continue
            if not nm:                                   # 'এক নজরে পৌরসভা': name from the page title / text
                cands = [x for x in re.findall(r"([ঀ-৿]+) পৌরসভা(?![ঀ-৿])", c["text"][:600])
                         if not re.match(r"নজর|এক|একনজর|শ্রেণী|উক্ত|এই|প্রথম|মোট|নং", x)] if "নজরে" in c["title"] else []
                nm = cands[0] if cands else ""
            if not nm:
                res["log"].append(f"{d}/{u}: pourashava page without a name: {h}")
                continue
            nm = dv_nfc(nm) + " পৌরসভা"
            row = poura.setdefault(nm, dict(level="pourashava", name_bn=nm, parent_level="upazila", parent_name_en=u,
                                            parent_name_bn=u_bn, district_en=d, upazila_en=u, website="", source_key=key,
                                            source_url=h, notes=""))
            row["source_url"] = h
            row["notes"] = f"menu item '{x}' on the {u_bn} upazila portal; {dv_upd(c)}" + row["notes"]
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
    dv_save_raw(out, f"{host.split('.')[0]}_glance.txt", url, c)
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
            dv_save_district_raw(out, r, d.lower())
            for p in r["pages"]:
                if p["status"] == "ok" and p["kind"] in ("upazilas", "pourashavas"):
                    c = dv_content(F.get(p["url"]))
                    dv_save_raw(out, f"{d.lower()}_{p['kind']}.txt", p["url"], c)
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
        dv_pages_csv(out, pages)
    elif kind == "union_portals":
        unions = []
        for d in div.districts:
            r = dv_collect_district(F, div, d, key, log)
            urls += [r["union_url"]] if r["union_url"] else []
            for u in r["unions"]:
                unions.append(dict(u, list_url=r["union_url"]))
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
            note = f"printed '{u['printed']}' on the district union list"
            if u["website"] and reached:
                note += "; portal reached" + (f" (title '{row.get('portal_title', '')}')" if row.get("portal_title") else "")
                if u.get("site_from"):
                    note += f"; portal link from {u['site_from']}"
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
                              source_url=row.get("url") or u.get("list_url", ""),
                              notes=note + "; English name not printed"))
        dv_write_csv(os.path.join(out, "raw", "coverage.csv"),
                     ["district_en", "upazila_en", "union_no", "union_bn", "portal", "portal_link_from", "portal_title",
                      "list_url", "url", "status", "updated", "title", "facts"], cov)
        pages = cov
    elif kind == "divisional_portal":
        r = dv_collect_division(F, div, key, log)
        areas, facts, pages = r["areas"], r["facts"], r["pages"]
        urls = [p["url"] for p in pages if p["status"] == "ok"]
        for k, (u, c) in r["raw"].items():
            dv_save_raw(out, f"{k}.txt", u, c)
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
    areas, facts, pages, missing = [], [], [], 0
    for sub, kind, pid, p_bn, p_en in PAGES:
        upz_en = [e for s, e, _ in UPAZILAS if s == sub][0]
        upz_bn = [b for s, _, b in UPAZILAS if s == sub][0]
        url = f"https://{sub}.rajshahi.gov.bd{SP}{pid}"
        try:
            c = content(get(url))
        except Exception as e:  # noqa: BLE001 - record and continue
            print(f"WARNING {url}: {e}", file=sys.stderr)
            pages.append(dict(url=url, kind=kind, status=f"error: {e}"))
            continue
        if not c:
            pages.append(dict(url=url, kind=kind, status="no content block"))
            continue
        save_raw(f"{sub}_{kind}_{pid[-8:]}.txt", url, c)
        pages.append(dict(url=url, kind=kind, status="ok", updated=c["date"], title=c["title"]))
        dated = f"page updated {c['date'] or 'n/a'}"
        if kind == "unions":
            us = unions_from(c)
            for n, no, raw, site, area in us:
                areas.append(dict(level="union", name_bn=n, parent_level="upazila", parent_name_en=upz_en, parent_name_bn=upz_bn,
                                  district_en="Rajshahi", upazila_en=upz_en, code=no, code_scheme="UNION_NO_IN_UPAZILA" if no else "",
                                  website=site, source_key=KEY, source_url=url,
                                  notes=f"printed '{raw}'; {dated}; English name not printed"))
                if area and first_number(area)[0]:
                    facts.append(dict(entity_level="union", entity_name_en="", district_en="Rajshahi", upazila_en=upz_en, code=no,
                                      fact="area", value=first_number(area)[0], unit="unstated (probably hectares)",
                                      basis="as stated", source_key=KEY, source_url=url,
                                      notes=f"union {n}; column 'আয়তন' without unit; values sum to ~330 so hectares is likely "
                                            f"(upazila 366.30 km2); {dated}"))
            facts.append(dict(entity_level="upazila", entity_name_en=upz_en, district_en="Rajshahi", upazila_en=upz_en,
                              fact="union_count", value=str(len(us)), unit="count", basis="rows listed", source_key=KEY,
                              source_url=url, notes=f"unions listed on '{c['title']}'; {dated}"))
        if kind == "poura":
            areas.append(dict(level="pourashava", name_bn=nfc(p_bn), parent_level="upazila", parent_name_en=upz_en,
                              parent_name_bn=upz_bn, district_en="Rajshahi", upazila_en=upz_en, source_key=KEY, source_url=url,
                              notes=f"from '{c['title']}' on the {upz_bn} upazila portal; {dated}"))
        for lvl, ent, fact, val, unit, basis, year, quote, note in F.get(pid, []):
            if not on_page(quote, c):
                print(f"WARNING quote not found on {url}: {quote}", file=sys.stderr)
                missing += 1
                continue
            if lvl == "upazila":
                name = upz_en
            elif lvl == "pourashava":
                name = f"{ent or p_en} Pourashava"
            else:
                name = ent
            facts.append(dict(entity_level=lvl, entity_name_en=name, district_en="Rajshahi", upazila_en=upz_en, fact=fact,
                              value=val, unit=unit, basis=basis, year=year, source_key=KEY, source_url=url,
                              notes=f"'{quote}'" + (f"; {note}" if note else "") + f"; {dated}"
                                    + ("; English key from BBS 2022 spelling (page is Bangla only)" if lvl != "upazila" else "")))
    write_csv(os.path.join(HERE, "areas.csv"), AREAS_H, areas)
    write_csv(os.path.join(HERE, "facts.csv"), FACTS_H, facts)
    write_csv(os.path.join(HERE, "raw", "pages.csv"), ["url", "kind", "status", "updated", "title"], pages)
    update_manifest()
    print(f"areas {len(areas)}, facts {len(facts)}, pages {len(pages)}, quotes missing {missing}")


KIND = "upazila_portals"


def main():
    global HERE
    ap = argparse.ArgumentParser(description="Upazila portals collector")
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
