#!/usr/bin/env python3
"""Rajshahi District Administration portal (rajshahi.gov.bd): union list, pourashava list, district at-a-glance.

Usage: python3 -I fetch.py [--cache DIR]
Writes areas.csv, facts.csv, raw/*.txt (text of the pages used) and refreshes SOURCE.json file hashes.
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


def main():
    global CACHE
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache")
    CACHE = ap.parse_args().cache
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


if __name__ == "__main__":
    main()
