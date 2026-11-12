#!/usr/bin/env python3
"""Rajshahi District upazila portals (<upazila>.rajshahi.gov.bd): union lists, এক নজরে facts, pourashava এক নজরে pages.

Usage: python3 -I fetch.py [--cache DIR]
Writes areas.csv, facts.csv, raw/*.txt (text of each page used) and refreshes SOURCE.json file hashes.
Union lists are parsed from the pages. Figures are hand-transcribed in F (below) together with the exact printed
text; every run checks that text is still on the live page and drops (with a warning) any figure whose text is gone.
Phone numbers and e-mail addresses are redacted from raw/*.txt.
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


def main():
    global CACHE
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache")
    CACHE = ap.parse_args().cache
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


if __name__ == "__main__":
    main()
